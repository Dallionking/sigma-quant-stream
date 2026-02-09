"""
Crypto Hypothesis Bridge.

Converts crypto pipeline signals into hypothesis cards for
the sigma-quant research pipeline (queues/crypto-hypotheses/).

This bridges the gap between the crypto data services and
the quantitative strategy research workflow.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Queue directory for hypothesis cards
HYPOTHESIS_QUEUE_DIR = Path("queues/crypto-hypotheses")


@dataclass(frozen=True)
class HypothesisCard:
    """
    A testable hypothesis derived from crypto market signals.

    Maps to the sigma-quant pipeline's hypothesis format.
    """

    hypothesis_id: str
    title: str
    source: str  # "mean_reversion", "cascade", "composite", "arb"
    edge_rationale: str
    counterparty: str  # Who is on the other side
    expected_sharpe: float
    expected_win_rate: float
    symbols: list[str] = field(default_factory=list)
    exchanges: list[str] = field(default_factory=list)
    timeframe: str = "8h"
    parameters: dict[str, Any] = field(default_factory=dict)
    signal_data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "pending"  # pending, accepted, rejected, backtesting

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class CryptoHypothesisProducer:
    """
    Produces hypothesis cards from crypto signal data.

    Each factory method takes service output and creates a
    structured, testable hypothesis for the quant pipeline.
    """

    def __init__(self, queue_dir: Path | None = None):
        self.queue_dir = queue_dir or HYPOTHESIS_QUEUE_DIR

    def _write_card(self, card: HypothesisCard) -> Path:
        """Write hypothesis card to queue directory."""
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.queue_dir / f"{card.hypothesis_id}.json"
        filepath.write_text(card.to_json())
        logger.info("Hypothesis card written: %s", filepath)
        return filepath

    def from_mean_reversion(
        self,
        symbol: str,
        exchange: str,
        rate_8h: float,
        z_score: float,
        mean_rate: float,
        *,
        write: bool = True,
    ) -> HypothesisCard:
        """
        Create hypothesis from funding rate mean-reversion signal.

        When funding rate Z-score exceeds +-2, the rate tends to
        revert to mean within 1-3 funding periods (8-24h).

        Edge: Positive funding -> short perp + long spot (or vice versa).
        Counterparty: Momentum traders paying extreme funding.
        """
        direction = "short" if z_score > 0 else "long"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        card = HypothesisCard(
            hypothesis_id=f"MR-{symbol.replace('/', '-')}-{ts}",
            title=f"Funding Mean Reversion: {direction} {symbol} on {exchange}",
            source="mean_reversion",
            edge_rationale=(
                f"Funding rate Z-score {z_score:.2f} exceeds +-2 threshold. "
                f"Current 8h rate: {rate_8h:.6f}, mean: {mean_rate:.6f}. "
                f"Historical reversion within 1-3 periods."
            ),
            counterparty="Momentum/retail traders paying extreme funding",
            expected_sharpe=1.2,
            expected_win_rate=0.62,
            symbols=[symbol],
            exchanges=[exchange],
            timeframe="8h",
            parameters={
                "entry_z_score": abs(z_score),
                "exit_z_score": 0.5,
                "max_hold_periods": 3,
                "direction": direction,
            },
            signal_data={
                "rate_8h": rate_8h,
                "z_score": z_score,
                "mean_rate": mean_rate,
            },
        )

        if write:
            self._write_card(card)
        return card

    def from_cascade(
        self,
        symbol: str,
        cascade_score: float,
        oi_change_pct: float,
        liquidation_volume: float,
        *,
        write: bool = True,
    ) -> HypothesisCard:
        """
        Create hypothesis from liquidation cascade signal.

        When cascade score is high, a liquidation cascade is likely.
        Strategy: Fade the cascade after exhaustion (contra-trend).

        Edge: Forced sellers create price overshoot.
        Counterparty: Leveraged traders being liquidated.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        card = HypothesisCard(
            hypothesis_id=f"LC-{symbol.replace('/', '-')}-{ts}",
            title=f"Liquidation Cascade Fade: {symbol}",
            source="cascade",
            edge_rationale=(
                f"Cascade score {cascade_score:.2f}/1.0 indicates high liquidation risk. "
                f"OI change: {oi_change_pct:+.1f}%, liq volume: ${liquidation_volume:,.0f}. "
                f"Fade after exhaustion for mean reversion."
            ),
            counterparty="Over-leveraged traders facing margin calls",
            expected_sharpe=0.9,
            expected_win_rate=0.55,
            symbols=[symbol],
            timeframe="1h",
            parameters={
                "cascade_threshold": 0.7,
                "entry_delay_minutes": 15,
                "max_position_pct": 2.0,
            },
            signal_data={
                "cascade_score": cascade_score,
                "oi_change_pct": oi_change_pct,
                "liquidation_volume": liquidation_volume,
            },
        )

        if write:
            self._write_card(card)
        return card

    def from_composite(
        self,
        asset: str,
        composite_score: float,
        components: dict[str, float],
        *,
        write: bool = True,
    ) -> HypothesisCard:
        """
        Create hypothesis from on-chain composite signal.

        Composite score aggregates SOPR, MVRV, exchange flows,
        and stablecoin supply. Extreme readings predict multi-day moves.

        Edge: On-chain data leads price by 1-5 days.
        Counterparty: Traders without on-chain visibility.
        """
        direction = "long" if composite_score > 0.6 else "short"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        card = HypothesisCard(
            hypothesis_id=f"OC-{asset}-{ts}",
            title=f"On-Chain Composite: {direction} {asset}",
            source="composite",
            edge_rationale=(
                f"On-chain composite score {composite_score:.2f} ({direction} bias). "
                f"Components: {', '.join(f'{k}={v:.2f}' for k, v in components.items())}. "
                f"On-chain data typically leads price by 1-5 days."
            ),
            counterparty="Price-only traders without on-chain data access",
            expected_sharpe=0.8,
            expected_win_rate=0.58,
            symbols=[f"{asset}/USDT:USDT"],
            timeframe="1d",
            parameters={
                "entry_composite": composite_score,
                "exit_composite": 0.5,
                "direction": direction,
                "hold_days_max": 5,
            },
            signal_data={
                "composite_score": composite_score,
                "components": components,
            },
        )

        if write:
            self._write_card(card)
        return card

    def from_arb(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        net_profit_bps: float,
        buy_price: float,
        sell_price: float,
        *,
        write: bool = True,
    ) -> HypothesisCard:
        """
        Create hypothesis from arbitrage opportunity.

        Cross-exchange arb when net profit (after fees) exceeds 10bps.
        NOTE: This is primarily a monitoring signal, not alpha -- arb
        is crowded and execution risk is high.

        Edge: Temporary price dislocation across venues.
        Counterparty: Slow arbitrageurs and market inefficiency.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        card = HypothesisCard(
            hypothesis_id=f"ARB-{symbol.replace('/', '-')}-{ts}",
            title=f"Cross-Exchange Arb: {symbol} ({buy_exchange}->{sell_exchange})",
            source="arb",
            edge_rationale=(
                f"Price dislocation: buy {buy_exchange} @ {buy_price:.2f}, "
                f"sell {sell_exchange} @ {sell_price:.2f}. "
                f"Net profit: {net_profit_bps:.1f} bps after fees. "
                f"NOTE: Monitoring signal -- execution risk is high."
            ),
            counterparty="Market inefficiency / slow arbitrageurs",
            expected_sharpe=1.5,
            expected_win_rate=0.70,
            symbols=[symbol],
            exchanges=[buy_exchange, sell_exchange],
            timeframe="spot",
            parameters={
                "min_profit_bps": 10.0,
                "max_execution_ms": 2000,
                "max_position_usd": 10000,
            },
            signal_data={
                "net_profit_bps": net_profit_bps,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "buy_exchange": buy_exchange,
                "sell_exchange": sell_exchange,
            },
        )

        if write:
            self._write_card(card)
        return card
