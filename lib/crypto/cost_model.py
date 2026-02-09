"""
Crypto trading cost model -- fees, funding drag, slippage, gas.

Provides accurate round-trip cost estimates for perpetual futures
across Binance, Bybit, OKX, and Hyperliquid so the quant pipeline
can factor execution costs into signal profitability.

Usage::

    from services.crypto.cost_model import calculate_round_trip_cost

    cost = calculate_round_trip_cost(
        exchange="binance",
        symbol="BTC/USDT:USDT",
        size_usd=10_000,
        hold_hours=48,
        funding_rate_8h=0.0001,
        vip_tier=0,
        is_maker=False,
    )
    print(cost.total_cost_pct, cost.total_cost_usd)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fee schedules per exchange / VIP tier
# ---------------------------------------------------------------------------

EXCHANGE_FEES: dict[str, dict[int, dict[str, float]]] = {
    "binance": {
        0: {"maker": 0.0002, "taker": 0.0005},
        1: {"maker": 0.00016, "taker": 0.0004},
        2: {"maker": 0.00014, "taker": 0.000375},
        3: {"maker": 0.00012, "taker": 0.00035},
        4: {"maker": 0.0001, "taker": 0.000325},
        5: {"maker": 0.00008, "taker": 0.0003},
        6: {"maker": 0.00006, "taker": 0.00025},
        7: {"maker": 0.00004, "taker": 0.0002},
        8: {"maker": 0.00002, "taker": 0.00018},
        9: {"maker": -0.00001, "taker": 0.00015},
    },
    "bybit": {
        0: {"maker": 0.0002, "taker": 0.00055},
        1: {"maker": 0.00018, "taker": 0.0004},
        2: {"maker": 0.00016, "taker": 0.000375},
        3: {"maker": 0.00014, "taker": 0.00035},
        4: {"maker": 0.0001, "taker": 0.00032},
        5: {"maker": -0.00005, "taker": 0.00025},
    },
    "okx": {
        0: {"maker": 0.0002, "taker": 0.0005},
        1: {"maker": 0.00016, "taker": 0.00045},
        2: {"maker": 0.00014, "taker": 0.0004},
        3: {"maker": 0.00012, "taker": 0.00035},
        4: {"maker": 0.0001, "taker": 0.0003},
        5: {"maker": 0.00008, "taker": 0.00025},
    },
    "hyperliquid": {
        # Hyperliquid has a flat schedule with minor VIP discounts
        0: {"maker": 0.0002, "taker": 0.0005},
        1: {"maker": 0.00015, "taker": 0.00045},
        2: {"maker": 0.0001, "taker": 0.0004},
    },
}

# ---------------------------------------------------------------------------
# Default slippage estimates (fraction of position value)
# ---------------------------------------------------------------------------

DEFAULT_SLIPPAGE: dict[str, float] = {
    "binance": 0.00005,      # 0.5 bps -- deepest book
    "bybit": 0.00007,        # 0.7 bps
    "okx": 0.00007,          # 0.7 bps
    "hyperliquid": 0.00015,  # 1.5 bps -- thinner on-chain book
}

# ---------------------------------------------------------------------------
# Gas / settlement fees (relevant for on-chain DEX legs)
# ---------------------------------------------------------------------------

DEFAULT_GAS_USD: dict[str, float] = {
    "binance": 0.0,
    "bybit": 0.0,
    "okx": 0.0,
    "hyperliquid": 0.05,  # negligible L1 fee per trade
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeCostBreakdown:
    """Itemised cost breakdown for a round-trip trade."""

    maker_fee: float
    taker_fee: float
    funding_drag: float
    slippage_estimate: float
    gas_fee: float  # DEX only
    total_cost_pct: float
    total_cost_usd: float


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_fee_schedule(
    exchange: str,
    vip_tier: int = 0,
) -> dict[str, float]:
    """Look up maker/taker fees for *exchange* at *vip_tier*.

    Falls back to tier 0 if the requested tier does not exist.

    Returns:
        ``{"maker": float, "taker": float}`` as fractions (e.g. 0.0005 = 5 bps).
    """
    exchange_lower = exchange.lower()
    tiers = EXCHANGE_FEES.get(exchange_lower)
    if tiers is None:
        logger.warning(
            "Unknown exchange '%s' -- defaulting to generic fee schedule",
            exchange,
        )
        return {"maker": 0.0002, "taker": 0.0005}

    schedule = tiers.get(vip_tier)
    if schedule is None:
        # Clamp to the highest known tier.
        best_tier = max(tiers.keys())
        logger.debug(
            "VIP tier %d not found for %s; falling back to tier %d",
            vip_tier,
            exchange_lower,
            best_tier,
        )
        schedule = tiers[best_tier]

    return dict(schedule)  # shallow copy


def calculate_funding_drag(
    funding_rate_8h: float,
    hold_hours: float,
) -> float:
    """Calculate cumulative funding drag as a fraction of position value.

    Funding is settled every 8 hours.  The drag equals
    ``funding_rate_8h * ceil(hold_hours / 8)``.

    Args:
        funding_rate_8h: The 8-hour funding rate (e.g. 0.0001 = 1 bp).
        hold_hours:      Expected hold duration in hours.

    Returns:
        Cumulative funding cost as a fraction of notional.
    """
    settlements = math.ceil(hold_hours / 8) if hold_hours > 0 else 0
    return funding_rate_8h * settlements


def calculate_round_trip_cost(
    exchange: str,
    symbol: str,
    size_usd: float,
    hold_hours: float = 24,
    funding_rate_8h: float = 0.0001,
    vip_tier: int = 0,
    is_maker: bool = False,
    slippage_override: float | None = None,
    gas_override: float | None = None,
) -> TradeCostBreakdown:
    """Calculate the all-in round-trip cost for a perpetual futures trade.

    This accounts for:

    * **Entry + exit fees** (maker or taker on each leg).
    * **Funding drag** while the position is held.
    * **Market-impact / slippage** estimate.
    * **Gas** (for on-chain venues like Hyperliquid).

    Args:
        exchange:          Exchange identifier (e.g. ``"binance"``).
        symbol:            Unified symbol (for logging; not used in calc).
        size_usd:          Notional position size in USD.
        hold_hours:        Expected holding period in hours.
        funding_rate_8h:   Current 8-hour funding rate (fraction).
        vip_tier:          Exchange VIP tier.
        is_maker:          If ``True`` both legs are maker; else taker.
        slippage_override: Override the default slippage fraction.
        gas_override:      Override the default gas fee in USD.

    Returns:
        A ``TradeCostBreakdown`` with itemised and total costs.
    """
    exchange_lower = exchange.lower()
    fees = get_fee_schedule(exchange_lower, vip_tier)

    maker_rate = fees["maker"]
    taker_rate = fees["taker"]

    # Entry + exit legs
    if is_maker:
        entry_fee_pct = maker_rate
        exit_fee_pct = maker_rate
    else:
        entry_fee_pct = taker_rate
        exit_fee_pct = taker_rate

    total_fee_pct = entry_fee_pct + exit_fee_pct

    # Funding drag
    funding_pct = calculate_funding_drag(funding_rate_8h, hold_hours)

    # Slippage
    slippage_pct = (
        slippage_override
        if slippage_override is not None
        else DEFAULT_SLIPPAGE.get(exchange_lower, 0.0001)
    )
    # Both legs incur slippage
    total_slippage_pct = slippage_pct * 2

    # Gas
    gas_usd = (
        gas_override
        if gas_override is not None
        else DEFAULT_GAS_USD.get(exchange_lower, 0.0)
    )
    # Two legs
    total_gas_usd = gas_usd * 2
    gas_pct = total_gas_usd / size_usd if size_usd > 0 else 0.0

    # Totals
    total_cost_pct = total_fee_pct + funding_pct + total_slippage_pct + gas_pct
    total_cost_usd = total_cost_pct * size_usd + total_gas_usd

    # For the breakdown we report the USD amounts that went to each bucket.
    maker_fee_usd = maker_rate * size_usd * 2 if is_maker else 0.0
    taker_fee_usd = taker_rate * size_usd * 2 if not is_maker else 0.0

    logger.debug(
        "Round-trip cost for %s on %s: size=$%.2f hold=%.1fh "
        "fee_pct=%.4f%% funding=%.4f%% slip=%.4f%% gas=$%.4f => total=%.4f%%/$%.2f",
        symbol,
        exchange_lower,
        size_usd,
        hold_hours,
        total_fee_pct * 100,
        funding_pct * 100,
        total_slippage_pct * 100,
        total_gas_usd,
        total_cost_pct * 100,
        total_cost_usd,
    )

    return TradeCostBreakdown(
        maker_fee=maker_fee_usd,
        taker_fee=taker_fee_usd,
        funding_drag=funding_pct * size_usd,
        slippage_estimate=total_slippage_pct * size_usd,
        gas_fee=total_gas_usd,
        total_cost_pct=total_cost_pct,
        total_cost_usd=total_cost_usd,
    )
