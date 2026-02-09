"""Cross-exchange arbitrage detection -- basis, price, funding rate, CEX-DEX.

Identifies profitable arbitrage opportunities across crypto exchanges by
comparing spot/perp basis, cross-exchange price differentials, and funding
rate divergences.  The ``ArbitrageDetector`` requires an async exchange
client (``UnifiedCryptoClient``) for live price fetching.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from .exchange_adapters import (
    CryptoExchangeAdapter,
    HyperliquidAdapter,
    TickerData,
    UnifiedCryptoClient,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

DEFAULT_EXCHANGES: list[str] = ["binance", "bybit", "okx", "hyperliquid"]
DEFAULT_SYMBOLS: list[str] = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
]

# Minimum thresholds (basis points) for an opportunity to be flagged
BASIS_ARB_THRESHOLD_BPS: float = 30.0
CROSS_EXCHANGE_ARB_THRESHOLD_BPS: float = 15.0
FUNDING_ARB_THRESHOLD_BPS: float = 20.0

# Default assumptions for cost estimation
DEFAULT_SLIPPAGE_BPS: float = 5.0
DEFAULT_WITHDRAWAL_FEE_USD: float = 0.0
DEFAULT_GAS_FEE_USD: float = 0.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ArbOpportunity:
    """A detected arbitrage opportunity with profitability and risk info."""

    type: str  # "basis", "cross_exchange", "funding", "cex_dex"
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_bps: float
    estimated_costs_bps: float
    net_profit_bps: float
    profit_usd_at_size: float
    execution_window_seconds: int
    risk_factors: list[str] = field(default_factory=list)
    feasibility: str = "medium"  # "high", "medium", "low"


# ---------------------------------------------------------------------------
# ArbitrageDetector
# ---------------------------------------------------------------------------


class ArbitrageDetector:
    """Detects profitable arbitrage across crypto exchanges.

    Args:
        exchange_client: A ``UnifiedCryptoClient`` instance with configured
            exchange adapters.
        default_size_usd: Position size used for profit estimation when not
            specified per-call.
    """

    def __init__(
        self,
        exchange_client: UnifiedCryptoClient,
        default_size_usd: float = 10_000.0,
    ) -> None:
        self.client = exchange_client
        self.default_size_usd = default_size_usd

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_fee_adjusted_profit(
        gross_spread_bps: float,
        buy_fee_bps: float,
        sell_fee_bps: float,
        withdrawal_fee_usd: float = DEFAULT_WITHDRAWAL_FEE_USD,
        gas_fee_usd: float = DEFAULT_GAS_FEE_USD,
        slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
        size_usd: float = 10_000.0,
    ) -> tuple[float, float]:
        """Calculate net profit after all costs.

        Returns:
            ``(net_profit_bps, net_profit_usd)``
        """
        total_fee_bps = buy_fee_bps + sell_fee_bps + slippage_bps
        # Convert fixed-dollar costs to bps equivalent
        fixed_cost_bps = ((withdrawal_fee_usd + gas_fee_usd) / size_usd) * 10_000 if size_usd > 0 else 0.0
        total_costs_bps = total_fee_bps + fixed_cost_bps
        net_bps = gross_spread_bps - total_costs_bps
        net_usd = (net_bps / 10_000) * size_usd
        return round(net_bps, 2), round(net_usd, 2)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_tickers(
        self,
        symbol: str,
        exchanges: list[str] | None = None,
    ) -> dict[str, TickerData]:
        """Fetch tickers from the relevant exchanges, ignoring failures."""
        target_exchanges = exchanges or list(self.client.exchanges.keys())
        results: dict[str, TickerData] = {}
        for name in target_exchanges:
            adapter = self.client.exchanges.get(name)
            if adapter is None:
                continue
            try:
                results[name] = await adapter.get_ticker(symbol)
            except Exception:
                logger.debug("Ticker fetch failed for %s on %s", symbol, name, exc_info=True)
        return results

    @staticmethod
    def _fee_bps_for_exchange(exchange: str) -> float:
        """Return a conservative taker fee estimate in bps for an exchange."""
        # Import locally to avoid circular dependency at module level
        from .exchange_validator import EXCHANGE_SPECS

        specs = EXCHANGE_SPECS.get(exchange, {})
        tier_0 = specs.get("fees", {}).get(0, {})
        return tier_0.get("taker", 0.0005) * 10_000  # convert to bps

    @staticmethod
    def _assess_feasibility(net_bps: float, risk_count: int) -> str:
        """Assign a feasibility grade based on net bps and risk count."""
        if net_bps >= 20 and risk_count <= 1:
            return "high"
        if net_bps >= 5:
            return "medium"
        return "low"

    # ------------------------------------------------------------------
    # Basis arb (spot vs perp)
    # ------------------------------------------------------------------

    async def detect_basis_arb(
        self,
        symbol: str,
        exchanges: list[str] | None = None,
    ) -> Optional[ArbOpportunity]:
        """Spot-perp basis arbitrage.  Threshold: >30 bps after fees.

        This method compares the perpetual prices across exchanges and
        identifies basis spread opportunities.  In a full implementation
        it would also compare against the spot price on the same exchange.
        Here we approximate by comparing the highest bid against the
        lowest ask across exchanges as a proxy for basis divergence.
        """
        tickers = await self._get_tickers(symbol, exchanges)
        if len(tickers) < 2:
            return None

        # Find highest bid (potential sell) and lowest ask (potential buy)
        best_bid_ex = max(tickers, key=lambda n: tickers[n].bid)
        best_ask_ex = min(
            tickers,
            key=lambda n: tickers[n].ask if tickers[n].ask > 0 else float("inf"),
        )

        bid_price = tickers[best_bid_ex].bid
        ask_price = tickers[best_ask_ex].ask
        if ask_price <= 0 or bid_price <= 0:
            return None

        mid = (bid_price + ask_price) / 2.0
        gross_bps = ((bid_price - ask_price) / mid) * 10_000

        if gross_bps <= 0:
            return None

        buy_fee = self._fee_bps_for_exchange(best_ask_ex)
        sell_fee = self._fee_bps_for_exchange(best_bid_ex)
        net_bps, net_usd = self.calculate_fee_adjusted_profit(
            gross_bps, buy_fee, sell_fee, size_usd=self.default_size_usd,
        )

        if net_bps < BASIS_ARB_THRESHOLD_BPS:
            return None

        risk_factors = self._basis_risk_factors(best_ask_ex, best_bid_ex)
        return ArbOpportunity(
            type="basis",
            symbol=symbol,
            buy_exchange=best_ask_ex,
            sell_exchange=best_bid_ex,
            buy_price=ask_price,
            sell_price=bid_price,
            spread_bps=round(gross_bps, 2),
            estimated_costs_bps=round(gross_bps - net_bps, 2),
            net_profit_bps=net_bps,
            profit_usd_at_size=net_usd,
            execution_window_seconds=60,
            risk_factors=risk_factors,
            feasibility=self._assess_feasibility(net_bps, len(risk_factors)),
        )

    @staticmethod
    def _basis_risk_factors(buy_ex: str, sell_ex: str) -> list[str]:
        """Return risk factors specific to basis arb."""
        risks: list[str] = []
        if buy_ex != sell_ex:
            risks.append("Cross-exchange transfer latency")
        risks.append("Funding rate may invert during hold")
        return risks

    # ------------------------------------------------------------------
    # Cross-exchange price arb
    # ------------------------------------------------------------------

    async def detect_cross_exchange_arb(
        self,
        symbol: str,
        exchanges: list[str] | None = None,
    ) -> Optional[ArbOpportunity]:
        """Price difference between exchanges.  Threshold: >15 bps after costs."""
        tickers = await self._get_tickers(symbol, exchanges)
        if len(tickers) < 2:
            return None

        best_bid_ex = max(tickers, key=lambda n: tickers[n].bid)
        best_ask_ex = min(
            tickers,
            key=lambda n: tickers[n].ask if tickers[n].ask > 0 else float("inf"),
        )

        if best_bid_ex == best_ask_ex:
            return None  # Same exchange -- no cross-exchange arb.

        bid = tickers[best_bid_ex].bid
        ask = tickers[best_ask_ex].ask
        if ask <= 0 or bid <= ask:
            return None

        mid = (bid + ask) / 2.0
        gross_bps = ((bid - ask) / mid) * 10_000

        buy_fee = self._fee_bps_for_exchange(best_ask_ex)
        sell_fee = self._fee_bps_for_exchange(best_bid_ex)
        net_bps, net_usd = self.calculate_fee_adjusted_profit(
            gross_bps, buy_fee, sell_fee, size_usd=self.default_size_usd,
        )

        if net_bps < CROSS_EXCHANGE_ARB_THRESHOLD_BPS:
            return None

        risk_factors = [
            "Cross-exchange settlement delay",
            "Withdrawal limits may constrain size",
            "Price may converge before execution completes",
        ]
        # DEX adds gas risk
        if "hyperliquid" in (best_ask_ex, best_bid_ex):
            risk_factors.append("On-chain gas costs for DEX leg")

        return ArbOpportunity(
            type="cross_exchange",
            symbol=symbol,
            buy_exchange=best_ask_ex,
            sell_exchange=best_bid_ex,
            buy_price=ask,
            sell_price=bid,
            spread_bps=round(gross_bps, 2),
            estimated_costs_bps=round(gross_bps - net_bps, 2),
            net_profit_bps=net_bps,
            profit_usd_at_size=net_usd,
            execution_window_seconds=30,
            risk_factors=risk_factors,
            feasibility=self._assess_feasibility(net_bps, len(risk_factors)),
        )

    # ------------------------------------------------------------------
    # Funding rate arb
    # ------------------------------------------------------------------

    async def detect_funding_arb(
        self,
        symbol: str,
        exchanges: list[str] | None = None,
    ) -> Optional[ArbOpportunity]:
        """Funding rate differential between exchanges.

        Strategy: go long on the exchange paying funding (negative rate)
        and short on the exchange receiving funding (positive rate).
        The net funding differential is the gross profit.
        """
        funding: dict[str, float] = {}
        target_exchanges = exchanges or list(self.client.exchanges.keys())

        for name in target_exchanges:
            adapter = self.client.exchanges.get(name)
            if adapter is None:
                continue
            try:
                fr = await adapter.get_funding_rate(symbol)
                funding[name] = fr.rate_8h
            except Exception:
                logger.debug("Funding fetch failed for %s on %s", symbol, name, exc_info=True)

        if len(funding) < 2:
            return None

        # Find the exchange pair with the largest funding differential
        sorted_by_rate = sorted(funding.items(), key=lambda kv: kv[1])
        lowest_name, lowest_rate = sorted_by_rate[0]
        highest_name, highest_rate = sorted_by_rate[-1]

        diff = highest_rate - lowest_rate
        diff_bps = diff * 10_000  # funding rates are already fractional

        if diff_bps < FUNDING_ARB_THRESHOLD_BPS:
            return None

        # Annualised funding profit (3 settlements/day * 365 days)
        annual_bps = diff_bps * 3 * 365

        # For profit estimation, use 8h payout scaled to default size
        net_usd_per_8h = (diff / 1.0) * self.default_size_usd  # diff is fractional

        risk_factors = [
            "Funding rates are variable and may converge",
            "Requires maintaining hedged positions on two exchanges",
            "Margin requirements on both sides",
        ]

        return ArbOpportunity(
            type="funding",
            symbol=symbol,
            buy_exchange=lowest_name,   # go long where funding is lowest
            sell_exchange=highest_name,  # go short where funding is highest
            buy_price=0.0,  # price not the driver for funding arb
            sell_price=0.0,
            spread_bps=round(diff_bps, 2),
            estimated_costs_bps=0.0,  # funding arb has minimal execution cost
            net_profit_bps=round(diff_bps, 2),
            profit_usd_at_size=round(net_usd_per_8h, 2),
            execution_window_seconds=28800,  # 8 hours between settlements
            risk_factors=risk_factors,
            feasibility=self._assess_feasibility(diff_bps, len(risk_factors)),
        )

    # ------------------------------------------------------------------
    # Scan all
    # ------------------------------------------------------------------

    async def scan_all(
        self,
        symbols: list[str] | None = None,
        exchanges: list[str] | None = None,
    ) -> list[ArbOpportunity]:
        """Run all arb detection types and return profitable opportunities.

        Iterates over all symbols and runs basis, cross-exchange, and
        funding arb detection in parallel.
        """
        target_symbols = symbols or DEFAULT_SYMBOLS
        all_opps: list[ArbOpportunity] = []

        for symbol in target_symbols:
            # Run all three detection types concurrently per symbol
            results = await asyncio.gather(
                self.detect_basis_arb(symbol, exchanges),
                self.detect_cross_exchange_arb(symbol, exchanges),
                self.detect_funding_arb(symbol, exchanges),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, ArbOpportunity):
                    all_opps.append(result)
                elif isinstance(result, Exception):
                    logger.warning(
                        "Arb detection error for %s: %s", symbol, result,
                    )

        # Sort by net profit descending
        all_opps.sort(key=lambda o: o.net_profit_bps, reverse=True)
        logger.info(
            "Arbitrage scan complete: %d opportunities across %d symbols",
            len(all_opps),
            len(target_symbols),
        )
        return all_opps
