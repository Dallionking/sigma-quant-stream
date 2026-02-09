"""Exchange compliance validation -- leverage tiers, rate limits, fee impact.

Validates crypto trading strategies against exchange-specific rules covering
leverage tier limits, liquidation buffer, rate limit headroom, fee drag, and
annualised funding rate cost.  All methods are synchronous (pure rule-checking,
no exchange API calls).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exchange specifications registry
# ---------------------------------------------------------------------------

EXCHANGE_SPECS: dict[str, dict[str, Any]] = {
    "binance": {
        "leverage_tiers": [
            {"notional_floor": 0, "notional_ceil": 50_000, "max_leverage": 125},
            {"notional_floor": 50_000, "notional_ceil": 250_000, "max_leverage": 100},
            {"notional_floor": 250_000, "notional_ceil": 1_000_000, "max_leverage": 50},
            {"notional_floor": 1_000_000, "notional_ceil": 5_000_000, "max_leverage": 20},
            {"notional_floor": 5_000_000, "notional_ceil": 50_000_000, "max_leverage": 10},
        ],
        "rate_limit_per_min": 1200,
        "funding_settlement_utc": ["00:00", "08:00", "16:00"],
        "settlement_interval_seconds": 28800,
        "fees": {
            0: {"maker": 0.0002, "taker": 0.0005},
            1: {"maker": -0.0001, "taker": 0.0004},
        },
    },
    "bybit": {
        "leverage_tiers": [
            {"notional_floor": 0, "notional_ceil": 100_000, "max_leverage": 100},
            {"notional_floor": 100_000, "notional_ceil": 500_000, "max_leverage": 50},
            {"notional_floor": 500_000, "notional_ceil": 2_000_000, "max_leverage": 25},
        ],
        "rate_limit_per_min": 1440,  # 120/5s
        "funding_settlement_utc": ["00:00", "08:00", "16:00"],
        "settlement_interval_seconds": 28800,
        "fees": {
            0: {"maker": 0.0001, "taker": 0.0006},
            2: {"maker": -0.00025, "taker": 0.0004},
        },
    },
    "okx": {
        "leverage_tiers": [
            {"notional_floor": 0, "notional_ceil": 100_000, "max_leverage": 100},
            {"notional_floor": 100_000, "notional_ceil": 500_000, "max_leverage": 50},
            {"notional_floor": 500_000, "notional_ceil": 2_000_000, "max_leverage": 20},
        ],
        "rate_limit_per_min": 1800,  # 60/2s
        "funding_settlement_utc": ["00:00", "08:00", "16:00"],
        "settlement_interval_seconds": 28800,
        "fees": {
            0: {"maker": 0.0002, "taker": 0.0005},
        },
    },
    "hyperliquid": {
        "leverage_tiers": [
            {"notional_floor": 0, "notional_ceil": 1_000_000, "max_leverage": 50},
            {"notional_floor": 1_000_000, "notional_ceil": 5_000_000, "max_leverage": 20},
        ],
        "rate_limit_per_min": 600,  # conservative estimate
        "funding_settlement_utc": [],  # continuous
        "settlement_interval_seconds": 3600,  # ~hourly
        "fees": {
            0: {"maker": 0.0002, "taker": 0.0005},
        },
    },
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ExchangeValidationResult:
    """Outcome of a full exchange compliance validation pass."""

    exchange: str
    status: str  # "pass", "fail", "warn"
    leverage_ok: bool
    max_leverage_at_size: float
    liquidation_buffer: float
    position_limit_ok: bool
    rate_limit_ok: bool
    fee_impact_pct: float
    funding_drag_annual_pct: float
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class ExchangeValidator:
    """Validates crypto strategies against exchange-specific rules.

    All methods are synchronous -- no API calls, just computation against
    the ``EXCHANGE_SPECS`` registry.
    """

    # ------------------------------------------------------------------
    # Leverage tier
    # ------------------------------------------------------------------

    def validate_leverage_tier(
        self,
        position_size_usd: float,
        leverage: float,
        exchange: str,
    ) -> tuple[bool, float]:
        """Check if *leverage* is within tier limits for *position_size_usd*.

        Returns:
            ``(ok, max_allowed_leverage)`` where *ok* is ``True`` when the
            requested leverage does not exceed the tier cap.
        """
        specs = EXCHANGE_SPECS.get(exchange)
        if specs is None:
            logger.warning("Unknown exchange '%s' -- cannot validate leverage", exchange)
            return False, 0.0

        tiers = specs["leverage_tiers"]
        max_allowed: float = 0.0

        for tier in tiers:
            if tier["notional_floor"] <= position_size_usd < tier["notional_ceil"]:
                max_allowed = float(tier["max_leverage"])
                break
        else:
            # Position size exceeds all tiers -- use the last tier's limit.
            if tiers:
                max_allowed = float(tiers[-1]["max_leverage"])

        return leverage <= max_allowed, max_allowed

    # ------------------------------------------------------------------
    # Liquidation distance
    # ------------------------------------------------------------------

    def validate_liquidation_distance(
        self,
        entry_price: float,
        leverage: float,
    ) -> float:
        """Calculate the margin buffer multiple.

        The liquidation distance as a fraction of entry is approximately
        ``1 / leverage``.  The *buffer multiple* is defined as the ratio
        of available margin to maintenance margin.  For crypto perpetuals
        a buffer >= 2.5x is considered safe.

        Returns:
            The margin buffer multiple (higher is safer).
        """
        if leverage <= 0:
            return float("inf")
        # Liquidation distance % = 1 / leverage
        # Buffer multiple = (1 / leverage) / (1 / leverage * maintenance_ratio)
        # Simplified: buffer ~= 1.0 for 100% maintenance.  We model buffer
        # as the inverse of the leverage-to-max ratio.  A practical proxy:
        # buffer = (100 / leverage) / (100 / leverage) but we want the
        # *distance-to-liquidation* in multiples of the maintenance margin.
        # Using the standard isolated-margin formula:
        #   liq_price_long = entry * (1 - 1/leverage + maintenance_rate)
        #   distance = entry / leverage
        #   buffer = distance / (entry * maintenance_rate)
        # With typical 0.4% maintenance rate for large-cap perps:
        maintenance_rate = 0.004
        distance_pct = 1.0 / leverage
        buffer = distance_pct / maintenance_rate
        return round(buffer, 2)

    # ------------------------------------------------------------------
    # Rate limits
    # ------------------------------------------------------------------

    def validate_rate_limits(
        self,
        avg_trades_per_hour: float,
        exchange: str,
    ) -> bool:
        """Check if strategy trade frequency fits within rate limits.

        Enforces 50% headroom so that bursts do not trigger throttling.
        """
        specs = EXCHANGE_SPECS.get(exchange)
        if specs is None:
            logger.warning("Unknown exchange '%s' -- cannot validate rate limits", exchange)
            return False

        rate_per_min = specs["rate_limit_per_min"]
        # Strategy trades per minute (average).
        strategy_per_min = avg_trades_per_hour / 60.0
        # Each trade may require ~3 API calls (place, check, cancel/modify).
        estimated_calls_per_min = strategy_per_min * 3.0
        # 50% headroom.
        safe_limit = rate_per_min * 0.5
        return estimated_calls_per_min <= safe_limit

    # ------------------------------------------------------------------
    # Fee impact
    # ------------------------------------------------------------------

    def estimate_fee_impact(
        self,
        size_usd: float,
        exchange: str,
        vip_tier: int = 0,
        is_maker: bool = False,
    ) -> float:
        """Estimate round-trip fee impact as a percentage of position size.

        Returns:
            Fee drag as a positive float percentage (e.g. 0.10 for 0.10%).
        """
        specs = EXCHANGE_SPECS.get(exchange)
        if specs is None:
            logger.warning("Unknown exchange '%s' -- using default 0.1%% fee estimate", exchange)
            return 0.10

        fee_schedule = specs["fees"]
        # Find the fee tier.  Fall back to tier 0 if the VIP tier is missing.
        tier_fees = fee_schedule.get(vip_tier, fee_schedule.get(0, {"maker": 0.0002, "taker": 0.0005}))
        fee_rate = tier_fees["maker"] if is_maker else tier_fees["taker"]
        # Round trip = open + close.
        round_trip_rate = abs(fee_rate) * 2
        return round(round_trip_rate * 100, 4)  # as percentage

    # ------------------------------------------------------------------
    # Funding drag
    # ------------------------------------------------------------------

    def estimate_funding_drag(
        self,
        avg_funding_8h: float,
        avg_hold_hours: float,
    ) -> float:
        """Estimate annualised funding rate drag.

        Args:
            avg_funding_8h: Average 8-hour funding rate (e.g. 0.0001 = 0.01%).
            avg_hold_hours: Average position hold time in hours.

        Returns:
            Annualised funding drag as a positive float percentage.
        """
        if avg_hold_hours <= 0:
            return 0.0
        # Number of 8h settlement windows during average hold.
        settlements_per_hold = avg_hold_hours / 8.0
        # Per-trade funding cost.
        per_trade_funding = avg_funding_8h * settlements_per_hold
        # Annualise: assume one trade cycle per hold period.
        trades_per_year = (365 * 24) / avg_hold_hours if avg_hold_hours > 0 else 0
        annual_drag = per_trade_funding * trades_per_year
        return round(abs(annual_drag) * 100, 4)  # as percentage

    # ------------------------------------------------------------------
    # Full validation
    # ------------------------------------------------------------------

    def full_validation(
        self,
        strategy_name: str,
        exchanges: list[str],
        max_leverage: float,
        avg_position_size_usd: float,
        avg_trades_per_hour: float,
        avg_hold_hours: float,
        avg_funding_rate_8h: float = 0.0001,
        vip_tier: int = 0,
    ) -> list[ExchangeValidationResult]:
        """Run all validation checks against the specified exchanges.

        Returns one ``ExchangeValidationResult`` per exchange.
        """
        results: list[ExchangeValidationResult] = []

        for exchange in exchanges:
            issues: list[str] = []
            recommendations: list[str] = []

            # Leverage tier
            leverage_ok, max_at_size = self.validate_leverage_tier(
                avg_position_size_usd, max_leverage, exchange,
            )
            if not leverage_ok:
                issues.append(
                    f"Requested leverage {max_leverage}x exceeds max {max_at_size}x "
                    f"for ${avg_position_size_usd:,.0f} notional on {exchange}"
                )
                recommendations.append(
                    f"Reduce leverage to {max_at_size}x or decrease position size"
                )

            # Liquidation buffer
            liq_buffer = self.validate_liquidation_distance(
                entry_price=1.0,  # entry price cancels out in ratio
                leverage=max_leverage,
            )
            if liq_buffer < 2.5:
                issues.append(
                    f"Liquidation buffer {liq_buffer}x is below 2.5x safety threshold"
                )
                recommendations.append(
                    "Reduce leverage to increase liquidation buffer above 2.5x"
                )

            # Position limit -- for now we check against the highest tier ceiling
            specs = EXCHANGE_SPECS.get(exchange, {})
            tiers = specs.get("leverage_tiers", [])
            max_notional = tiers[-1]["notional_ceil"] if tiers else 0
            position_limit_ok = avg_position_size_usd <= max_notional
            if not position_limit_ok:
                issues.append(
                    f"Position size ${avg_position_size_usd:,.0f} exceeds "
                    f"max tier ceiling ${max_notional:,.0f} on {exchange}"
                )

            # Rate limits
            rate_limit_ok = self.validate_rate_limits(avg_trades_per_hour, exchange)
            if not rate_limit_ok:
                issues.append(
                    f"Trade frequency {avg_trades_per_hour}/hr may exceed "
                    f"rate limits on {exchange} (with 50% headroom)"
                )
                recommendations.append(
                    "Reduce trade frequency or implement request batching"
                )

            # Fee impact
            fee_impact = self.estimate_fee_impact(
                avg_position_size_usd, exchange, vip_tier,
            )

            # Funding drag
            funding_drag = self.estimate_funding_drag(
                avg_funding_rate_8h, avg_hold_hours,
            )

            # Determine overall status
            if issues:
                # Any leverage or position-limit failure is a hard fail
                has_hard_fail = not leverage_ok or not position_limit_ok or liq_buffer < 2.5
                status = "fail" if has_hard_fail else "warn"
            else:
                status = "pass"

            logger.info(
                "Exchange validation: strategy=%s exchange=%s status=%s issues=%d",
                strategy_name,
                exchange,
                status,
                len(issues),
            )

            results.append(
                ExchangeValidationResult(
                    exchange=exchange,
                    status=status,
                    leverage_ok=leverage_ok,
                    max_leverage_at_size=max_at_size,
                    liquidation_buffer=liq_buffer,
                    position_limit_ok=position_limit_ok,
                    rate_limit_ok=rate_limit_ok,
                    fee_impact_pct=fee_impact,
                    funding_drag_annual_pct=funding_drag,
                    issues=issues,
                    recommendations=recommendations,
                )
            )

        return results
