"""
QuantStream Strategy Template for Freqtrade.

This template maps QuantStream-discovered signals into the Freqtrade IStrategy
interface so that any strategy validated by the Quant Research Team can be
paper-traded (dry-run) or live-traded via Freqtrade.

Usage:
    1. Copy this file and rename it to your strategy name.
    2. Fill in the indicator logic inside ``populate_indicators``.
    3. Define entry/exit conditions in the ``populate_*_trend`` methods.
    4. Adjust ``custom_stoploss``, ``leverage``, and ``custom_stake_amount``
       to match the risk profile exported by the prop-firm validator.
    5. Run: ``freqtrade trade --strategy YourStrategyName --config config-paper.json``
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import pandas_ta as ta  # noqa: F401 — used dynamically in indicator logic
from freqtrade.persistence import Trade
from freqtrade.strategy import (
    DecimalParameter,
    IStrategy,
    IntParameter,
)


class QuantStreamStrategy(IStrategy):
    """Base IStrategy implementation for QuantStream-discovered strategies.

    Subclass this or modify in-place after copying the template.  Every
    ``# QUANTSTREAM:`` comment marks an integration point where values
    from the QuantStream pipeline (backtest results, optimised params,
    prop-firm constraints) should be injected.
    """

    # ------------------------------------------------------------------
    # Freqtrade meta
    # ------------------------------------------------------------------
    INTERFACE_VERSION: int = 3

    # QUANTSTREAM: Override from profile timeframe
    timeframe: str = "5m"

    # QUANTSTREAM: Set from optimizer output (minimal_roi curve)
    minimal_roi: dict[str, float] = {
        "0": 0.10,
        "30": 0.05,
        "60": 0.02,
        "120": 0.01,
    }

    # QUANTSTREAM: Set from risk profile
    stoploss: float = -0.05

    trailing_stop: bool = True
    trailing_stop_positive: float = 0.01
    trailing_stop_positive_offset: float = 0.02
    trailing_only_offset_is_reached: bool = True

    # QUANTSTREAM: Warm-up period required by the longest indicator
    startup_candle_count: int = 200

    # ------------------------------------------------------------------
    # Hyper-optimisable parameters
    # ------------------------------------------------------------------
    # QUANTSTREAM: Replace defaults with optimizer best-fit values
    rsi_period = IntParameter(7, 25, default=14, space="buy")
    rsi_oversold = IntParameter(20, 40, default=30, space="buy")
    rsi_overbought = IntParameter(60, 80, default=70, space="sell")
    atr_multiplier = DecimalParameter(1.0, 4.0, default=2.0, decimals=1, space="stoploss")

    # ------------------------------------------------------------------
    # Indicators
    # ------------------------------------------------------------------

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Calculate technical indicators used by entry/exit logic.

        QUANTSTREAM: Replace or extend these with the indicators discovered
        by the researcher and validated by the backtester.

        Args:
            dataframe: OHLCV dataframe from the exchange.
            metadata: Pair metadata (symbol, etc.).

        Returns:
            The dataframe with new indicator columns appended.
        """
        # --- Trend indicators ---
        dataframe["ema_fast"] = ta.ema(dataframe["close"], length=9)
        dataframe["ema_slow"] = ta.ema(dataframe["close"], length=21)
        dataframe["ema_200"] = ta.ema(dataframe["close"], length=200)

        # --- Momentum indicators ---
        dataframe["rsi"] = ta.rsi(dataframe["close"], length=self.rsi_period.value)
        macd = ta.macd(dataframe["close"], fast=12, slow=26, signal=9)
        if macd is not None:
            dataframe["macd"] = macd.iloc[:, 0]
            dataframe["macd_signal"] = macd.iloc[:, 1]
            dataframe["macd_hist"] = macd.iloc[:, 2]

        # --- Volatility indicators ---
        atr = ta.atr(dataframe["high"], dataframe["low"], dataframe["close"], length=14)
        if atr is not None:
            dataframe["atr"] = atr

        bbands = ta.bbands(dataframe["close"], length=20, std=2.0)
        if bbands is not None:
            dataframe["bb_upper"] = bbands.iloc[:, 2]
            dataframe["bb_mid"] = bbands.iloc[:, 1]
            dataframe["bb_lower"] = bbands.iloc[:, 0]

        # --- Volume indicators ---
        dataframe["volume_sma"] = ta.sma(dataframe["volume"], length=20)

        # QUANTSTREAM: Add custom indicators from the converter output here
        # Example: dataframe["custom_signal"] = custom_indicator(dataframe)

        return dataframe

    # ------------------------------------------------------------------
    # Entry logic
    # ------------------------------------------------------------------

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Define long and short entry conditions.

        QUANTSTREAM: Replace these placeholder conditions with the signal
        logic exported by the QuantStream backtester.

        Args:
            dataframe: Indicator-enriched OHLCV dataframe.
            metadata: Pair metadata.

        Returns:
            The dataframe with ``enter_long`` and ``enter_short`` columns.
        """
        # --- Long entries ---
        dataframe.loc[
            (
                (dataframe["ema_fast"] > dataframe["ema_slow"])
                & (dataframe["rsi"] < self.rsi_oversold.value)
                & (dataframe["close"] > dataframe["ema_200"])
                & (dataframe["volume"] > dataframe["volume_sma"])
            ),
            "enter_long",
        ] = 1

        # --- Short entries ---
        dataframe.loc[
            (
                (dataframe["ema_fast"] < dataframe["ema_slow"])
                & (dataframe["rsi"] > self.rsi_overbought.value)
                & (dataframe["close"] < dataframe["ema_200"])
                & (dataframe["volume"] > dataframe["volume_sma"])
            ),
            "enter_short",
        ] = 1

        # QUANTSTREAM: Insert additional entry filters here
        # (e.g., session-time gates, correlation checks, news sentiment)

        return dataframe

    # ------------------------------------------------------------------
    # Exit logic
    # ------------------------------------------------------------------

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Define long and short exit conditions.

        QUANTSTREAM: Replace these placeholder conditions with the exit
        logic validated during walk-forward testing.

        Args:
            dataframe: Indicator-enriched OHLCV dataframe.
            metadata: Pair metadata.

        Returns:
            The dataframe with ``exit_long`` and ``exit_short`` columns.
        """
        # --- Long exits ---
        dataframe.loc[
            (
                (dataframe["ema_fast"] < dataframe["ema_slow"])
                | (dataframe["rsi"] > self.rsi_overbought.value)
            ),
            "exit_long",
        ] = 1

        # --- Short exits ---
        dataframe.loc[
            (
                (dataframe["ema_fast"] > dataframe["ema_slow"])
                | (dataframe["rsi"] < self.rsi_oversold.value)
            ),
            "exit_short",
        ] = 1

        # QUANTSTREAM: Insert additional exit conditions here
        # (e.g., max-hold-time, session-close flatten, drawdown circuit-breaker)

        return dataframe

    # ------------------------------------------------------------------
    # Dynamic stop-loss
    # ------------------------------------------------------------------

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: pd.Timestamp,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs: object,
    ) -> float:
        """ATR-based dynamic stop-loss.

        QUANTSTREAM: Adjust multiplier and floor from the risk profile
        generated by the prop-firm validator.

        Args:
            pair: Trading pair string.
            trade: Current Trade object.
            current_time: Current candle timestamp.
            current_rate: Current price.
            current_profit: Unrealised P&L ratio.
            after_fill: Whether this is called right after order fill.

        Returns:
            Stop-loss value as a negative ratio (e.g. -0.03 = 3% stop).
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if dataframe.empty:
            return self.stoploss

        last_candle = dataframe.iloc[-1]
        atr_value: float = last_candle.get("atr", 0.0)

        if atr_value <= 0 or current_rate <= 0:
            return self.stoploss

        # QUANTSTREAM: atr_multiplier tuned by optimizer
        atr_stop: float = -(atr_value * self.atr_multiplier.value) / current_rate

        # Never wider than the static stoploss
        return max(atr_stop, self.stoploss)

    # ------------------------------------------------------------------
    # Leverage
    # ------------------------------------------------------------------

    def leverage(
        self,
        pair: str,
        current_time: pd.Timestamp,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs: object,
    ) -> float:
        """Return leverage for this trade.

        QUANTSTREAM: Set max leverage from the prop-firm profile. Most
        prop firms cap at 10x; some crypto venues allow up to 125x.

        Args:
            pair: Trading pair string.
            current_time: Current candle timestamp.
            current_rate: Current price.
            proposed_leverage: Leverage proposed by Freqtrade config.
            max_leverage: Maximum leverage allowed by the exchange.
            entry_tag: Entry signal tag (if any).
            side: ``"long"`` or ``"short"``.

        Returns:
            Leverage multiplier (e.g. 5.0 for 5x).
        """
        # QUANTSTREAM: Replace with profile-driven leverage
        max_allowed: float = 5.0
        return min(proposed_leverage, max_leverage, max_allowed)

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    def custom_stake_amount(
        self,
        pair: str,
        current_time: pd.Timestamp,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs: object,
    ) -> float:
        """Calculate position size based on risk budget.

        Uses a fixed-fractional model: risk ``risk_per_trade`` percent of
        the wallet per trade, adjusted for the ATR-based stop distance.

        QUANTSTREAM: ``risk_per_trade`` should be set from the prop-firm
        validator's risk profile (typically 1-2% for funded accounts).

        Args:
            pair: Trading pair string.
            current_time: Current candle timestamp.
            current_rate: Current price.
            proposed_stake: Stake proposed by Freqtrade.
            min_stake: Minimum allowed stake.
            max_stake: Maximum allowed stake.
            leverage: Active leverage for this trade.
            entry_tag: Entry signal tag (if any).
            side: ``"long"`` or ``"short"``.

        Returns:
            Stake amount in stake currency.
        """
        # QUANTSTREAM: Set from prop-firm risk profile
        risk_per_trade: float = 0.02  # 2% of wallet per trade

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if dataframe.empty:
            return proposed_stake

        last_candle = dataframe.iloc[-1]
        atr_value: float = last_candle.get("atr", 0.0)

        if atr_value <= 0 or current_rate <= 0:
            return proposed_stake

        stop_distance: float = (atr_value * self.atr_multiplier.value) / current_rate
        if stop_distance <= 0:
            return proposed_stake

        wallet: float = self.wallets.get_total_stake_amount()  # type: ignore[attr-defined]
        risk_amount: float = wallet * risk_per_trade
        position_value: float = risk_amount / stop_distance

        # Clamp to exchange limits
        stake: float = min(position_value, max_stake)
        if min_stake is not None:
            stake = max(stake, min_stake)

        return stake
