"""
Liquidation cascade detection and heatmap service.

Feeds the @quant-liquidation-tracker agent with:
- Liquidation cascade detection (volume + OI + price deviation)
- OI-price divergence pattern recognition
- Liquidation heatmap construction by leverage tier
- Cascade risk probability estimation

Key thresholds:
- Cascade trigger: liq_volume > $100M AND OI_drop > 10% AND price_dev > 2*ATR
- Magnitude: small (<$50M), medium ($50-200M), large (>$200M)
- Bullish divergence: OI drops >10%, price holds within 2%
- Bearish divergence: OI rises, price flat/declining
- Cascade risk: weighted combo of leverage, funding, vol, OI concentration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Default leverage tiers for heatmap construction
DEFAULT_LEVERAGE_TIERS: List[float] = [2, 3, 5, 10, 20, 25, 50, 100]

# Cascade detection thresholds
CASCADE_LIQ_VOLUME_THRESHOLD: float = 100_000_000  # $100M
CASCADE_OI_DROP_THRESHOLD: float = 0.10  # 10% OI drop
CASCADE_PRICE_DEV_ATR_MULTIPLIER: float = 2.0  # price deviation > 2 * ATR

# Component weights for cascade risk estimation
RISK_WEIGHTS: Dict[str, float] = {
    "leverage": 0.30,
    "funding": 0.20,
    "volatility": 0.25,
    "oi_concentration": 0.25,
}


@dataclass
class CascadeSignal:
    """Signal indicating a liquidation cascade event."""

    symbol: str
    detected: bool
    magnitude: str  # "small" (<$50M), "medium" ($50-200M), "large" (>$200M)
    liquidation_volume_1h: float
    oi_change_pct: float
    price_deviation_atr: float
    mean_reversion_target: Optional[float]
    confidence: str  # "high", "medium", "low"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON responses."""
        return {
            "symbol": self.symbol,
            "detected": self.detected,
            "magnitude": self.magnitude,
            "liquidation_volume_1h": self.liquidation_volume_1h,
            "oi_change_pct": self.oi_change_pct,
            "price_deviation_atr": self.price_deviation_atr,
            "mean_reversion_target": self.mean_reversion_target,
            "confidence": self.confidence,
        }


@dataclass
class OIDivergence:
    """Open interest vs price divergence pattern."""

    symbol: str
    type: str  # "bullish", "bearish", "none"
    oi_change_pct: float
    price_change_pct: float
    confidence: float  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON responses."""
        return {
            "symbol": self.symbol,
            "type": self.type,
            "oi_change_pct": self.oi_change_pct,
            "price_change_pct": self.price_change_pct,
            "confidence": self.confidence,
        }


@dataclass
class HeatmapLevel:
    """Single level in a liquidation heatmap."""

    price: float
    estimated_liq_volume: float
    direction: str  # "long" or "short"
    leverage: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON responses."""
        return {
            "price": self.price,
            "estimated_liq_volume": self.estimated_liq_volume,
            "direction": self.direction,
            "leverage": self.leverage,
        }


@dataclass
class LiquidationEvent:
    """Individual liquidation event record."""

    symbol: str
    exchange: str
    side: str  # "long" or "short"
    quantity: float
    price: float
    notional_usd: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "notional_usd": self.notional_usd,
            "timestamp": self.timestamp.isoformat(),
        }


class LiquidationService:
    """Monitors liquidation events and detects cascade patterns.

    Consumes data from a UnifiedCryptoClient (exchange_adapters.py, Module 1)
    and produces actionable cascade signals, OI divergence patterns,
    and liquidation heatmaps for the quant-liquidation-tracker agent.
    """

    def __init__(self, exchange_client: Any) -> None:
        """Initialize with a UnifiedCryptoClient from exchange_adapters.py.

        Args:
            exchange_client: Unified crypto exchange client providing
                get_liquidations, get_open_interest, get_ticker, and
                get_klines async methods.
        """
        self.client = exchange_client

    # ------------------------------------------------------------------
    # Recent liquidations
    # ------------------------------------------------------------------

    async def get_recent_liquidations(
        self,
        symbol: str,
        exchange: str,
        hours: int = 1,
    ) -> List[LiquidationEvent]:
        """Get recent liquidation events from exchange.

        Args:
            symbol: Trading pair (e.g. "BTCUSDT").
            exchange: Exchange name.
            hours: Lookback window in hours.

        Returns:
            List of LiquidationEvent sorted chronologically.
        """
        try:
            raw_liquidations = await self.client.get_liquidations(
                symbol=symbol,
                exchange=exchange,
                start_time=datetime.now(tz=timezone.utc) - timedelta(hours=hours),
                end_time=datetime.now(tz=timezone.utc),
            )
        except Exception:
            logger.exception(
                "Failed to fetch liquidations for %s on %s",
                symbol,
                exchange,
            )
            return []

        if not raw_liquidations:
            return []

        events: List[LiquidationEvent] = []
        for liq in raw_liquidations:
            ts = liq.get("timestamp")
            if isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(
                    ts / 1000 if ts > 1e12 else ts,
                    tz=timezone.utc,
                )
            elif isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            elif ts is None:
                ts = datetime.now(tz=timezone.utc)

            price = float(liq.get("price", 0))
            qty = float(liq.get("quantity", liq.get("qty", 0)))
            notional = float(liq.get("notional_usd", price * qty))

            events.append(
                LiquidationEvent(
                    symbol=symbol,
                    exchange=exchange,
                    side=liq.get("side", "unknown"),
                    quantity=qty,
                    price=price,
                    notional_usd=notional,
                    timestamp=ts,
                )
            )

        events.sort(key=lambda e: e.timestamp)
        return events

    # ------------------------------------------------------------------
    # ATR calculation helper
    # ------------------------------------------------------------------

    async def _calculate_atr(
        self,
        symbol: str,
        exchange: str,
        period: int = 14,
    ) -> float:
        """Calculate Average True Range over the specified period.

        Uses 1-hour klines. ATR = SMA of true range over ``period`` bars.

        Args:
            symbol: Trading pair.
            exchange: Exchange name.
            period: Number of bars for ATR calculation.

        Returns:
            ATR value as a float. Returns 0.0 on error.
        """
        try:
            klines = await self.client.get_klines(
                symbol=symbol,
                exchange=exchange,
                interval="1h",
                limit=period + 1,
            )
        except Exception:
            logger.exception("Failed to fetch klines for ATR: %s on %s", symbol, exchange)
            return 0.0

        if not klines or len(klines) < 2:
            return 0.0

        true_ranges: List[float] = []
        for i in range(1, len(klines)):
            high = float(klines[i].get("high", 0))
            low = float(klines[i].get("low", 0))
            prev_close = float(klines[i - 1].get("close", 0))

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            true_ranges.append(tr)

        if not true_ranges:
            return 0.0

        # Use the last ``period`` true ranges (or all if fewer)
        recent_trs = true_ranges[-period:]
        return float(np.mean(recent_trs))

    # ------------------------------------------------------------------
    # Cascade detection
    # ------------------------------------------------------------------

    @staticmethod
    def cascade_magnitude(liq_volume_usd: float) -> str:
        """Classify liquidation cascade magnitude.

        Args:
            liq_volume_usd: Total liquidation volume in USD.

        Returns:
            "small" (<$50M), "medium" ($50-200M), or "large" (>$200M).
        """
        if liq_volume_usd < 50_000_000:
            return "small"
        elif liq_volume_usd < 200_000_000:
            return "medium"
        return "large"

    async def detect_cascade(
        self,
        symbol: str,
        exchange: str = "binance",
    ) -> CascadeSignal:
        """Detect if a liquidation cascade is occurring or just occurred.

        Cascade criteria (ALL must be true):
        1. liq_volume_1h > $100M
        2. OI change < -10% (over 1h)
        3. Price deviation > 2 * ATR (14-period hourly)

        Args:
            symbol: Trading pair.
            exchange: Exchange to analyze.

        Returns:
            CascadeSignal with detection result and metadata.
        """
        # --- Fetch liquidations ---
        liquidations = await self.get_recent_liquidations(
            symbol=symbol,
            exchange=exchange,
            hours=1,
        )
        liq_volume_1h = sum(e.notional_usd for e in liquidations)

        # --- Fetch open interest (current and 1h ago) ---
        try:
            oi_data = await self.client.get_open_interest(
                symbol=symbol,
                exchange=exchange,
            )
            current_oi = float(oi_data.get("open_interest", 0)) if oi_data else 0.0
        except Exception:
            logger.exception("Failed to fetch OI for %s on %s", symbol, exchange)
            current_oi = 0.0

        try:
            oi_history = await self.client.get_open_interest_history(
                symbol=symbol,
                exchange=exchange,
                period="5m",
                limit=12,  # ~1 hour of 5m intervals
            )
            if oi_history and len(oi_history) > 0:
                past_oi = float(oi_history[0].get("open_interest", current_oi))
            else:
                past_oi = current_oi
        except Exception:
            logger.exception("Failed to fetch OI history for %s on %s", symbol, exchange)
            past_oi = current_oi

        oi_change_pct = 0.0
        if past_oi > 0:
            oi_change_pct = (current_oi - past_oi) / past_oi

        # --- Fetch current price and ATR ---
        try:
            ticker = await self.client.get_ticker(
                symbol=symbol,
                exchange=exchange,
            )
            current_price = float(ticker.get("last_price", ticker.get("price", 0))) if ticker else 0.0
        except Exception:
            logger.exception("Failed to fetch ticker for %s on %s", symbol, exchange)
            current_price = 0.0

        atr = await self._calculate_atr(symbol, exchange)

        # Price deviation from recent mean (use 24h high/low midpoint as reference)
        try:
            ticker_24h = await self.client.get_ticker(symbol=symbol, exchange=exchange)
            high_24h = float(ticker_24h.get("high_24h", ticker_24h.get("high", current_price)))
            low_24h = float(ticker_24h.get("low_24h", ticker_24h.get("low", current_price)))
            reference_price = (high_24h + low_24h) / 2
        except Exception:
            reference_price = current_price

        price_deviation = abs(current_price - reference_price)
        price_dev_atr = price_deviation / atr if atr > 0 else 0.0

        # --- Cascade detection ---
        criteria_met = (
            liq_volume_1h > CASCADE_LIQ_VOLUME_THRESHOLD
            and oi_change_pct < -CASCADE_OI_DROP_THRESHOLD
            and price_dev_atr > CASCADE_PRICE_DEV_ATR_MULTIPLIER
        )

        magnitude = self.cascade_magnitude(liq_volume_1h)

        # Mean reversion target: use the 24h VWAP or midpoint as target
        mean_reversion_target: Optional[float] = None
        if criteria_met and reference_price > 0:
            mean_reversion_target = round(reference_price, 2)

        # Confidence
        criteria_count = sum([
            liq_volume_1h > CASCADE_LIQ_VOLUME_THRESHOLD,
            oi_change_pct < -CASCADE_OI_DROP_THRESHOLD,
            price_dev_atr > CASCADE_PRICE_DEV_ATR_MULTIPLIER,
        ])
        if criteria_count == 3:
            confidence = "high"
        elif criteria_count == 2:
            confidence = "medium"
        else:
            confidence = "low"

        logger.info(
            "Cascade check for %s on %s: detected=%s, magnitude=%s, "
            "liq_vol=$%.0f, oi_change=%.2f%%, price_dev_atr=%.2f",
            symbol,
            exchange,
            criteria_met,
            magnitude,
            liq_volume_1h,
            oi_change_pct * 100,
            price_dev_atr,
        )

        return CascadeSignal(
            symbol=symbol,
            detected=criteria_met,
            magnitude=magnitude,
            liquidation_volume_1h=round(liq_volume_1h, 2),
            oi_change_pct=round(oi_change_pct, 4),
            price_deviation_atr=round(price_dev_atr, 4),
            mean_reversion_target=mean_reversion_target,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # OI-Price divergence
    # ------------------------------------------------------------------

    async def detect_oi_divergence(
        self,
        symbol: str,
        exchange: str,
        hours: int = 4,
    ) -> OIDivergence:
        """Detect OI-price divergence patterns.

        Bullish divergence: OI drops >10% but price holds within 2%.
            This signals weak hands being flushed while strong hands hold.
        Bearish divergence: OI rises but price is flat or declining.
            This signals new shorts opening or leveraged longs building
            into weakness.

        Args:
            symbol: Trading pair.
            exchange: Exchange name.
            hours: Lookback window.

        Returns:
            OIDivergence classification.
        """
        # Fetch OI history
        try:
            oi_history = await self.client.get_open_interest_history(
                symbol=symbol,
                exchange=exchange,
                period="5m",
                limit=hours * 12,  # 12 five-minute intervals per hour
            )
        except Exception:
            logger.exception("Failed to fetch OI history for divergence: %s", symbol)
            return OIDivergence(
                symbol=symbol,
                type="none",
                oi_change_pct=0.0,
                price_change_pct=0.0,
                confidence=0.0,
            )

        if not oi_history or len(oi_history) < 2:
            return OIDivergence(
                symbol=symbol,
                type="none",
                oi_change_pct=0.0,
                price_change_pct=0.0,
                confidence=0.0,
            )

        start_oi = float(oi_history[0].get("open_interest", 0))
        end_oi = float(oi_history[-1].get("open_interest", 0))

        # Fetch price change over the same window
        try:
            klines = await self.client.get_klines(
                symbol=symbol,
                exchange=exchange,
                interval="1h",
                limit=hours + 1,
            )
        except Exception:
            logger.exception("Failed to fetch klines for divergence: %s", symbol)
            klines = []

        if klines and len(klines) >= 2:
            start_price = float(klines[0].get("close", 0))
            end_price = float(klines[-1].get("close", 0))
        else:
            # Fallback to ticker
            try:
                ticker = await self.client.get_ticker(symbol=symbol, exchange=exchange)
                end_price = float(ticker.get("last_price", ticker.get("price", 0)))
                start_price = end_price  # Cannot determine change
            except Exception:
                start_price = 0.0
                end_price = 0.0

        # Calculate percentage changes
        oi_change_pct = (end_oi - start_oi) / start_oi if start_oi > 0 else 0.0
        price_change_pct = (end_price - start_price) / start_price if start_price > 0 else 0.0

        # Classify divergence
        div_type = "none"
        confidence = 0.0

        # Bullish: OI drops >10%, price holds within 2%
        if oi_change_pct < -0.10 and abs(price_change_pct) < 0.02:
            div_type = "bullish"
            # Confidence scales with OI drop magnitude and price stability
            oi_factor = min(abs(oi_change_pct) / 0.20, 1.0)  # cap at 20% drop
            price_factor = 1.0 - (abs(price_change_pct) / 0.02)  # higher when price stable
            confidence = round(0.5 * oi_factor + 0.5 * max(price_factor, 0.0), 4)

        # Bearish: OI rises >5%, price flat or declining
        elif oi_change_pct > 0.05 and price_change_pct <= 0.005:
            div_type = "bearish"
            oi_factor = min(oi_change_pct / 0.15, 1.0)  # cap at 15% rise
            # More bearish when price is actively declining
            if price_change_pct < -0.01:
                price_factor = min(abs(price_change_pct) / 0.05, 1.0)
            else:
                price_factor = 0.3  # baseline for flat price
            confidence = round(0.5 * oi_factor + 0.5 * price_factor, 4)

        logger.info(
            "OI divergence check for %s on %s: type=%s, oi_change=%.2f%%, "
            "price_change=%.2f%%, confidence=%.2f",
            symbol,
            exchange,
            div_type,
            oi_change_pct * 100,
            price_change_pct * 100,
            confidence,
        )

        return OIDivergence(
            symbol=symbol,
            type=div_type,
            oi_change_pct=round(oi_change_pct, 4),
            price_change_pct=round(price_change_pct, 4),
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Liquidation heatmap
    # ------------------------------------------------------------------

    async def build_heatmap(
        self,
        symbol: str,
        exchange: str,
    ) -> List[HeatmapLevel]:
        """Build liquidation heatmap showing where liquidation clusters exist.

        For each leverage tier, calculates the price at which long and short
        positions would be liquidated, then estimates the volume at each level
        based on OI distribution assumptions.

        Args:
            symbol: Trading pair.
            exchange: Exchange name.

        Returns:
            List of HeatmapLevel sorted by price.
        """
        # Fetch current price and OI
        try:
            ticker = await self.client.get_ticker(symbol=symbol, exchange=exchange)
            current_price = float(ticker.get("last_price", ticker.get("price", 0)))
        except Exception:
            logger.exception("Failed to fetch ticker for heatmap: %s", symbol)
            return []

        if current_price <= 0:
            return []

        try:
            oi_data = await self.client.get_open_interest(symbol=symbol, exchange=exchange)
            total_oi = float(oi_data.get("open_interest", 0)) if oi_data else 0.0
        except Exception:
            logger.exception("Failed to fetch OI for heatmap: %s", symbol)
            total_oi = 0.0

        if total_oi <= 0:
            return []

        # Estimate OI distribution across leverage tiers
        # Higher leverage = smaller share of OI (power law approximation)
        leverage_weights = self._estimate_leverage_distribution(DEFAULT_LEVERAGE_TIERS)

        levels: List[HeatmapLevel] = []

        for leverage, weight in zip(DEFAULT_LEVERAGE_TIERS, leverage_weights):
            oi_at_tier = total_oi * weight

            # Maintenance margin approximation: 0.5 / leverage
            # Long liquidation price = entry * (1 - 1/leverage + maintenance_margin_pct)
            # Short liquidation price = entry * (1 + 1/leverage - maintenance_margin_pct)
            maintenance_margin = 0.5 / leverage

            long_liq_price = current_price * (1.0 - (1.0 / leverage) + maintenance_margin)
            short_liq_price = current_price * (1.0 + (1.0 / leverage) - maintenance_margin)

            # Estimated notional USD at each level
            estimated_volume_long = oi_at_tier * current_price * 0.5  # assume 50/50 long/short
            estimated_volume_short = oi_at_tier * current_price * 0.5

            levels.append(
                HeatmapLevel(
                    price=round(long_liq_price, 2),
                    estimated_liq_volume=round(estimated_volume_long, 2),
                    direction="long",
                    leverage=leverage,
                )
            )
            levels.append(
                HeatmapLevel(
                    price=round(short_liq_price, 2),
                    estimated_liq_volume=round(estimated_volume_short, 2),
                    direction="short",
                    leverage=leverage,
                )
            )

        # Sort by price ascending
        levels.sort(key=lambda lvl: lvl.price)

        logger.info(
            "Built heatmap for %s on %s: %d levels, current_price=$%.2f, OI=%.0f",
            symbol,
            exchange,
            len(levels),
            current_price,
            total_oi,
        )
        return levels

    @staticmethod
    def _estimate_leverage_distribution(
        leverage_tiers: List[float],
    ) -> List[float]:
        """Estimate OI distribution across leverage tiers using inverse power law.

        Lower leverage tiers hold a larger share of OI. Weights are
        normalized to sum to 1.0.

        Args:
            leverage_tiers: List of leverage values.

        Returns:
            Normalized weight for each tier (same order as input).
        """
        # Inverse of leverage as raw weight (lower leverage = higher weight)
        raw_weights = [1.0 / lev for lev in leverage_tiers]
        total = sum(raw_weights)
        return [w / total for w in raw_weights]

    # ------------------------------------------------------------------
    # Cascade risk estimation
    # ------------------------------------------------------------------

    async def estimate_cascade_risk(
        self,
        symbol: str,
        exchange: str,
    ) -> float:
        """Estimate probability of an imminent liquidation cascade (0-1 scale).

        Combines four risk factors with configurable weights:
        - Leverage risk (0.30): Average effective leverage vs historical
        - Funding risk (0.20): Extreme funding rate indicates overleveraged side
        - Volatility risk (0.25): Recent realized vol vs historical
        - OI concentration risk (0.25): OI concentration changes

        Args:
            symbol: Trading pair.
            exchange: Exchange name.

        Returns:
            Probability estimate between 0.0 and 1.0.
        """
        risk_scores: Dict[str, float] = {}

        # --- Leverage risk ---
        leverage_risk = await self._calc_leverage_risk(symbol, exchange)
        risk_scores["leverage"] = leverage_risk

        # --- Funding risk ---
        funding_risk = await self._calc_funding_risk(symbol, exchange)
        risk_scores["funding"] = funding_risk

        # --- Volatility risk ---
        vol_risk = await self._calc_volatility_risk(symbol, exchange)
        risk_scores["volatility"] = vol_risk

        # --- OI concentration risk ---
        oi_risk = await self._calc_oi_concentration_risk(symbol, exchange)
        risk_scores["oi_concentration"] = oi_risk

        # Weighted combination
        cascade_risk = sum(
            risk_scores[k] * RISK_WEIGHTS[k] for k in RISK_WEIGHTS
        )
        cascade_risk = max(0.0, min(1.0, cascade_risk))

        logger.info(
            "Cascade risk for %s on %s: %.4f (leverage=%.2f, funding=%.2f, "
            "vol=%.2f, oi=%.2f)",
            symbol,
            exchange,
            cascade_risk,
            risk_scores["leverage"],
            risk_scores["funding"],
            risk_scores["volatility"],
            risk_scores["oi_concentration"],
        )

        return round(cascade_risk, 4)

    async def _calc_leverage_risk(self, symbol: str, exchange: str) -> float:
        """Calculate leverage-based risk component (0-1).

        High average leverage across the market increases cascade risk.
        Approximated from OI / volume ratio.
        """
        try:
            oi_data = await self.client.get_open_interest(symbol=symbol, exchange=exchange)
            ticker = await self.client.get_ticker(symbol=symbol, exchange=exchange)
        except Exception:
            return 0.5  # neutral on failure

        oi = float(oi_data.get("open_interest", 0)) if oi_data else 0.0
        volume_24h = float(ticker.get("volume_24h", ticker.get("volume", 1))) if ticker else 1.0

        if volume_24h <= 0:
            return 0.5

        # OI/Volume ratio > 5 is elevated, > 10 is extreme
        oi_vol_ratio = oi / volume_24h
        risk = min(oi_vol_ratio / 10.0, 1.0)
        return round(risk, 4)

    async def _calc_funding_risk(self, symbol: str, exchange: str) -> float:
        """Calculate funding-rate-based risk component (0-1).

        Extreme (positive or negative) funding rates indicate one side is
        heavily leveraged and paying the other, increasing cascade potential.
        """
        try:
            rate_data = await self.client.get_funding_rate(
                symbol=symbol,
                exchange=exchange,
            )
        except Exception:
            return 0.3  # slightly below neutral

        if not rate_data:
            return 0.3

        rate = abs(float(rate_data.get("funding_rate", 0)))
        # Baseline rate ~0.01% (0.0001). Elevated at 0.05%, extreme at 0.1%+
        risk = min(rate / 0.001, 1.0)
        return round(risk, 4)

    async def _calc_volatility_risk(self, symbol: str, exchange: str) -> float:
        """Calculate volatility-based risk component (0-1).

        Compares recent (4h) realized volatility to longer-term (24h) vol.
        Spike in short-term vol relative to baseline increases cascade risk.
        """
        try:
            klines = await self.client.get_klines(
                symbol=symbol,
                exchange=exchange,
                interval="1h",
                limit=25,  # 25 hours of data
            )
        except Exception:
            return 0.5

        if not klines or len(klines) < 5:
            return 0.5

        closes = np.array([float(k.get("close", 0)) for k in klines])
        if len(closes) < 5:
            return 0.5

        # Log returns
        returns = np.diff(np.log(closes))
        if len(returns) < 4:
            return 0.5

        recent_vol = float(np.std(returns[-4:]))  # last 4 hours
        baseline_vol = float(np.std(returns))  # full window

        if baseline_vol <= 0:
            return 0.5

        vol_ratio = recent_vol / baseline_vol
        # Risk scales: ratio of 1.0 = normal, 2.0+ = elevated
        risk = min((vol_ratio - 1.0) / 2.0, 1.0)
        risk = max(risk, 0.0)
        return round(risk, 4)

    async def _calc_oi_concentration_risk(
        self,
        symbol: str,
        exchange: str,
    ) -> float:
        """Calculate OI concentration risk component (0-1).

        Rapid OI increases suggest leveraged positions building up.
        If OI has grown significantly in a short window, cascade risk rises.
        """
        try:
            oi_history = await self.client.get_open_interest_history(
                symbol=symbol,
                exchange=exchange,
                period="5m",
                limit=48,  # ~4 hours
            )
        except Exception:
            return 0.5

        if not oi_history or len(oi_history) < 2:
            return 0.5

        oi_values = np.array([float(h.get("open_interest", 0)) for h in oi_history])
        if len(oi_values) < 2 or oi_values[0] <= 0:
            return 0.5

        # Percentage change from start to end of window
        oi_change = (oi_values[-1] - oi_values[0]) / oi_values[0]

        # Also check for rapid spikes (max OI relative to start)
        max_oi = float(np.max(oi_values))
        max_change = (max_oi - oi_values[0]) / oi_values[0]

        # Risk from magnitude of OI build-up
        # 10% increase = moderate risk, 20%+ = high risk
        change_risk = min(abs(max_change) / 0.20, 1.0)

        # Additional risk if OI is now declining from the peak (positions unwinding)
        unwind_factor = 0.0
        if max_oi > oi_values[-1] and max_change > 0.05:
            unwind_factor = 0.3  # bonus risk for unwind-in-progress

        risk = min(change_risk + unwind_factor, 1.0)
        return round(risk, 4)
