"""
Funding rate analysis service for crypto perpetual futures.

Feeds the @quant-funding-analyzer agent with:
- Mean reversion signals based on funding rate z-scores
- Cross-exchange carry trade opportunities
- Historical funding rate analysis
- Annualized rate calculations and funding cost estimates

Key formulas:
- Annualized rate: rate_8h * 3 * 365 (3 settlements per day)
- Funding cost: position_size * rate_8h * ceil(hold_hours / 8)
- Z-score: (current - mean_30d) / std_30d
- Signal threshold: |z_score| > 2.0
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Default exchanges to query when none specified
DEFAULT_EXCHANGES: List[str] = ["binance", "bybit", "okx"]

# Default trading fees per exchange (maker/taker in decimal, e.g. 0.0004 = 0.04%)
EXCHANGE_FEES: Dict[str, Dict[str, float]] = {
    "binance": {"maker": 0.0002, "taker": 0.0004},
    "bybit": {"maker": 0.0001, "taker": 0.0006},
    "okx": {"maker": 0.0002, "taker": 0.0005},
    "deribit": {"maker": 0.0000, "taker": 0.0005},
    "htx": {"maker": 0.0002, "taker": 0.0005},
}


@dataclass
class MeanReversionSignal:
    """Signal generated when funding rate deviates significantly from its mean."""

    symbol: str
    current_rate_8h: float
    annualized_rate: float
    z_score: float
    percentile_30d: float
    is_signal: bool
    direction: str  # "short" if funding too high, "long" if too low
    confidence: str  # "high", "medium", "low"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON responses."""
        return {
            "symbol": self.symbol,
            "current_rate_8h": self.current_rate_8h,
            "annualized_rate": self.annualized_rate,
            "z_score": self.z_score,
            "percentile_30d": self.percentile_30d,
            "is_signal": self.is_signal,
            "direction": self.direction,
            "confidence": self.confidence,
        }


@dataclass
class CarryOpportunity:
    """Delta-neutral carry trade opportunity across exchanges."""

    symbol: str
    long_exchange: str  # exchange to go long spot
    short_exchange: str  # exchange to short perp
    funding_rate_8h: float
    estimated_annual_carry_pct: float
    net_carry_after_fees: float
    is_profitable: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON responses."""
        return {
            "symbol": self.symbol,
            "long_exchange": self.long_exchange,
            "short_exchange": self.short_exchange,
            "funding_rate_8h": self.funding_rate_8h,
            "estimated_annual_carry_pct": self.estimated_annual_carry_pct,
            "net_carry_after_fees": self.net_carry_after_fees,
            "is_profitable": self.is_profitable,
        }


@dataclass
class FundingRateSnapshot:
    """Point-in-time funding rate record from an exchange."""

    symbol: str
    exchange: str
    rate_8h: float
    timestamp: datetime
    next_funding_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "rate_8h": self.rate_8h,
            "timestamp": self.timestamp.isoformat(),
            "next_funding_time": (
                self.next_funding_time.isoformat() if self.next_funding_time else None
            ),
        }


class FundingRateService:
    """Analyzes perpetual futures funding rates for trading opportunities.

    Consumes data from a UnifiedCryptoClient (exchange_adapters.py, Module 1)
    and produces actionable signals for the quant-funding-analyzer agent.
    """

    def __init__(self, exchange_client: Any) -> None:
        """Initialize with a UnifiedCryptoClient from exchange_adapters.py.

        Args:
            exchange_client: Unified crypto exchange client providing
                get_funding_rate, get_funding_rate_history, and get_ticker
                async methods.
        """
        self.client = exchange_client

    # ------------------------------------------------------------------
    # Current rates
    # ------------------------------------------------------------------

    async def get_current_rates(
        self,
        symbols: List[str],
        exchanges: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, FundingRateSnapshot]]:
        """Get current funding rates across exchanges for given symbols.

        Args:
            symbols: List of symbols (e.g. ["BTCUSDT", "ETHUSDT"]).
            exchanges: Exchanges to query. Defaults to DEFAULT_EXCHANGES.

        Returns:
            Nested dict ``{symbol: {exchange: FundingRateSnapshot}}``.
        """
        target_exchanges = exchanges or DEFAULT_EXCHANGES
        results: Dict[str, Dict[str, FundingRateSnapshot]] = {}

        for symbol in symbols:
            results[symbol] = {}
            for exchange in target_exchanges:
                try:
                    rate_data = await self.client.get_funding_rate(
                        symbol=symbol,
                        exchange=exchange,
                    )
                    if rate_data is None:
                        logger.warning(
                            "No funding rate returned for %s on %s",
                            symbol,
                            exchange,
                        )
                        continue

                    # rate_data is a FundingRateData frozen dataclass
                    # from exchange_adapters.py (not a dict).
                    snapshot = FundingRateSnapshot(
                        symbol=symbol,
                        exchange=exchange,
                        rate_8h=float(rate_data.rate_8h),
                        timestamp=datetime.now(tz=timezone.utc),
                        next_funding_time=(
                            datetime.fromtimestamp(
                                rate_data.next_settlement, tz=timezone.utc
                            )
                            if rate_data.next_settlement
                            else None
                        ),
                    )
                    results[symbol][exchange] = snapshot
                except Exception:
                    logger.exception(
                        "Failed to fetch funding rate for %s on %s",
                        symbol,
                        exchange,
                    )
        return results

    # ------------------------------------------------------------------
    # Historical rates
    # ------------------------------------------------------------------

    async def get_historical_rates(
        self,
        symbol: str,
        exchange: str,
        days: int = 30,
    ) -> List[FundingRateSnapshot]:
        """Get historical 8h funding rate data.

        Args:
            symbol: Trading pair (e.g. "BTCUSDT").
            exchange: Exchange name (e.g. "binance").
            days: Lookback window in days.

        Returns:
            Chronologically ordered list of FundingRateSnapshot.
        """
        try:
            raw_history = await self.client.get_funding_rate_history(
                symbol=symbol,
                exchange=exchange,
                start_time=datetime.now(tz=timezone.utc) - timedelta(days=days),
                end_time=datetime.now(tz=timezone.utc),
            )
        except Exception:
            logger.exception(
                "Failed to fetch historical funding rates for %s on %s",
                symbol,
                exchange,
            )
            return []

        if not raw_history:
            return []

        snapshots: List[FundingRateSnapshot] = []
        for record in raw_history:
            # record is a FundingRateData frozen dataclass from
            # exchange_adapters.py with fields: symbol, exchange,
            # rate_8h, next_settlement (unix ts), annualized.
            ts_raw = record.next_settlement
            if isinstance(ts_raw, (int, float)) and ts_raw > 0:
                ts = datetime.fromtimestamp(
                    ts_raw / 1000 if ts_raw > 1e12 else ts_raw,
                    tz=timezone.utc,
                )
            else:
                ts = datetime.now(tz=timezone.utc)

            snapshots.append(
                FundingRateSnapshot(
                    symbol=symbol,
                    exchange=exchange,
                    rate_8h=float(record.rate_8h),
                    timestamp=ts,
                )
            )

        # Ensure chronological order
        snapshots.sort(key=lambda s: s.timestamp)
        return snapshots

    # ------------------------------------------------------------------
    # Static helper formulas
    # ------------------------------------------------------------------

    @staticmethod
    def annualized_rate(rate_8h: float) -> float:
        """Convert 8-hour funding rate to annualized percentage.

        Formula: rate_8h * 3 * 365 (3 funding settlements per 24h).

        Args:
            rate_8h: The 8-hour funding rate as a decimal (e.g. 0.0001 = 0.01%).

        Returns:
            Annualized rate as a decimal (e.g. 0.1095 = 10.95%).
        """
        return rate_8h * 3 * 365

    @staticmethod
    def funding_cost_per_trade(
        position_size: float,
        rate_8h: float,
        hold_hours: float,
    ) -> float:
        """Calculate funding cost for holding a position.

        Cost accrues at each 8-hour settlement. Partial periods count
        as a full settlement (ceil).

        Args:
            position_size: Notional position size in USD.
            rate_8h: 8-hour funding rate as decimal.
            hold_hours: Expected hold duration in hours.

        Returns:
            Absolute funding cost in USD.
        """
        settlements = math.ceil(hold_hours / 8)
        return abs(position_size * rate_8h * settlements)

    # ------------------------------------------------------------------
    # Mean reversion detection
    # ------------------------------------------------------------------

    async def detect_mean_reversion(
        self,
        symbol: str,
        exchange: str = "binance",
        lookback_days: int = 30,
    ) -> MeanReversionSignal:
        """Detect funding rate mean reversion signals using z-score.

        A signal fires when the current funding rate is more than 2 standard
        deviations away from the 30-day mean. Direction is contra-funding:
        high funding -> short signal, low funding -> long signal.

        Args:
            symbol: Trading pair.
            exchange: Exchange to analyze.
            lookback_days: Lookback period for statistics.

        Returns:
            MeanReversionSignal with z-score, direction, and confidence.
        """
        history = await self.get_historical_rates(
            symbol=symbol,
            exchange=exchange,
            days=lookback_days,
        )

        if len(history) < 10:
            logger.warning(
                "Insufficient history (%d records) for %s on %s",
                len(history),
                symbol,
                exchange,
            )
            return MeanReversionSignal(
                symbol=symbol,
                current_rate_8h=0.0,
                annualized_rate=0.0,
                z_score=0.0,
                percentile_30d=50.0,
                is_signal=False,
                direction="none",
                confidence="low",
            )

        rates = np.array([s.rate_8h for s in history])
        current_rate = float(rates[-1])
        mean = float(np.mean(rates))
        std = float(np.std(rates, ddof=1))  # sample std

        # Guard against zero/near-zero std
        if std < 1e-12:
            z_score = 0.0
        else:
            z_score = float((current_rate - mean) / std)

        # Percentile within the lookback window
        percentile = float(np.sum(rates <= current_rate) / len(rates) * 100)

        # Signal fires when |z_score| > 2.0
        is_signal = bool(abs(z_score) > 2.0)

        # Direction is contra-funding
        if z_score > 2.0:
            direction = "short"  # funding too high -> longs paying shorts -> short perp
        elif z_score < -2.0:
            direction = "long"  # funding too low/negative -> shorts paying longs -> long perp
        else:
            direction = "none"

        # Confidence tiers
        abs_z = abs(z_score)
        if abs_z > 3.0:
            confidence = "high"
        elif abs_z > 2.0:
            confidence = "medium"
        else:
            confidence = "low"

        annualized = self.annualized_rate(current_rate)

        logger.info(
            "Mean reversion check for %s on %s: z=%.2f, signal=%s, dir=%s",
            symbol,
            exchange,
            z_score,
            is_signal,
            direction,
        )

        return MeanReversionSignal(
            symbol=symbol,
            current_rate_8h=current_rate,
            annualized_rate=annualized,
            z_score=round(z_score, 4),
            percentile_30d=round(percentile, 2),
            is_signal=is_signal,
            direction=direction,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Carry trade opportunities
    # ------------------------------------------------------------------

    async def find_carry_opportunities(
        self,
        symbols: List[str],
        exchanges: Optional[List[str]] = None,
    ) -> List[CarryOpportunity]:
        """Find delta-neutral carry trade opportunities across exchanges.

        For each symbol, identifies the exchange with the highest positive
        funding rate (short perp there to collect funding) and pairs it
        with the exchange having the lowest rate (or spot) for the long leg.

        Net carry = annualized funding income - round-trip trading fees.

        Args:
            symbols: Symbols to scan.
            exchanges: Exchanges to compare. Defaults to DEFAULT_EXCHANGES.

        Returns:
            List of CarryOpportunity sorted by net carry descending.
        """
        target_exchanges = exchanges or DEFAULT_EXCHANGES
        current_rates = await self.get_current_rates(symbols, target_exchanges)
        opportunities: List[CarryOpportunity] = []

        for symbol, exchange_rates in current_rates.items():
            if len(exchange_rates) < 2:
                continue

            # Sort by funding rate
            sorted_exchanges = sorted(
                exchange_rates.items(),
                key=lambda x: x[1].rate_8h,
            )

            lowest_rate_exchange, lowest_snapshot = sorted_exchanges[0]
            highest_rate_exchange, highest_snapshot = sorted_exchanges[-1]

            # Only meaningful if there is a spread
            rate_spread = highest_snapshot.rate_8h - lowest_snapshot.rate_8h
            if rate_spread <= 0:
                continue

            # Annual carry from the spread
            annual_carry_pct = self.annualized_rate(rate_spread)

            # Estimate round-trip fees (entry + exit on both legs)
            long_fees = EXCHANGE_FEES.get(lowest_rate_exchange, {"taker": 0.0005})
            short_fees = EXCHANGE_FEES.get(highest_rate_exchange, {"taker": 0.0005})
            # 2 trades per leg (entry + exit), 2 legs
            total_fee_pct = 2 * (long_fees["taker"] + short_fees["taker"])

            net_carry = annual_carry_pct - total_fee_pct

            opportunities.append(
                CarryOpportunity(
                    symbol=symbol,
                    long_exchange=lowest_rate_exchange,
                    short_exchange=highest_rate_exchange,
                    funding_rate_8h=highest_snapshot.rate_8h,
                    estimated_annual_carry_pct=round(annual_carry_pct, 6),
                    net_carry_after_fees=round(net_carry, 6),
                    is_profitable=net_carry > 0,
                )
            )

        # Sort by net carry descending
        opportunities.sort(key=lambda o: o.net_carry_after_fees, reverse=True)

        logger.info(
            "Found %d carry opportunities across %d symbols",
            len(opportunities),
            len(symbols),
        )
        return opportunities

    # ------------------------------------------------------------------
    # Cross-exchange comparison
    # ------------------------------------------------------------------

    async def compare_cross_exchange(
        self,
        symbol: str,
        exchanges: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compare funding rates for a symbol across all exchanges.

        Returns a summary dict with per-exchange rates, the spread
        (max - min), and statistical measures.

        Args:
            symbol: Trading pair to compare.
            exchanges: Exchanges to include. Defaults to DEFAULT_EXCHANGES.

        Returns:
            Dict with exchange rates, spread, mean, std, and ranking.
        """
        target_exchanges = exchanges or DEFAULT_EXCHANGES
        rates_map = await self.get_current_rates([symbol], target_exchanges)

        exchange_data = rates_map.get(symbol, {})
        if not exchange_data:
            return {
                "symbol": symbol,
                "exchanges": {},
                "spread_8h": 0.0,
                "spread_annualized": 0.0,
                "mean_rate_8h": 0.0,
                "std_rate_8h": 0.0,
                "highest_exchange": None,
                "lowest_exchange": None,
            }

        rates_by_exchange: Dict[str, Dict[str, float]] = {}
        rate_values: List[float] = []

        for ex_name, snapshot in exchange_data.items():
            annualized = self.annualized_rate(snapshot.rate_8h)
            rates_by_exchange[ex_name] = {
                "rate_8h": snapshot.rate_8h,
                "annualized": round(annualized, 6),
                "timestamp": snapshot.timestamp.isoformat(),
            }
            rate_values.append(snapshot.rate_8h)

        arr = np.array(rate_values)
        spread_8h = float(np.max(arr) - np.min(arr))
        mean_rate = float(np.mean(arr))
        std_rate = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0

        # Rankings
        sorted_exchanges = sorted(
            exchange_data.items(),
            key=lambda x: x[1].rate_8h,
            reverse=True,
        )
        highest = sorted_exchanges[0][0] if sorted_exchanges else None
        lowest = sorted_exchanges[-1][0] if sorted_exchanges else None

        return {
            "symbol": symbol,
            "exchanges": rates_by_exchange,
            "spread_8h": round(spread_8h, 8),
            "spread_annualized": round(self.annualized_rate(spread_8h), 6),
            "mean_rate_8h": round(mean_rate, 8),
            "std_rate_8h": round(std_rate, 8),
            "highest_exchange": highest,
            "lowest_exchange": lowest,
        }
