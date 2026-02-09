---
name: quant-freqtrade-bridge
description: "Strategy to Freqtrade IStrategy conversion, hyperopt integration, dry-run config, and CCXT exchange support"
version: "1.0.0"
tags:
  - crypto
  - freqtrade
  - istrategy
  - hyperopt
  - ccxt
  - paper-trading
triggers:
  - "when converting strategies to Freqtrade format"
  - "when setting up Freqtrade dry-run (paper trading)"
  - "when configuring Freqtrade hyperopt optimization"
  - "when deploying strategies via Freqtrade to exchanges"
---

# Quant Freqtrade Bridge

## Purpose

Converts Sigma-Quant strategies into Freqtrade's IStrategy format for live/paper execution across 100+ exchanges via CCXT. Freqtrade is the most widely-used open-source crypto trading bot, providing battle-tested execution, backtesting, and hyperopt (walk-forward parameter optimization). This bridge enables strategies developed in the Sigma-Quant research pipeline to be deployed to any CCXT-supported exchange.

## When to Use

- When deploying a validated crypto strategy to a live exchange
- When converting BaseStrategyTemplate to Freqtrade's IStrategy
- When running Freqtrade hyperopt for parameter optimization
- When setting up paper trading (dry-run mode)
- When needing multi-exchange deployment (100+ via CCXT)

## Freqtrade Architecture

```
config.json (exchange, pairs, strategy settings)
  -> IStrategy (your strategy logic)
    -> populate_indicators() -- calculate indicators
    -> populate_entry_trend() -- define entry conditions
    -> populate_exit_trend() -- define exit conditions
    -> custom_stoploss() -- dynamic stop loss
    -> custom_exit() -- custom exit logic
  -> CCXT (exchange adapter)
    -> Exchange API (Binance, Bybit, OKX, Hyperliquid, etc.)
```

## Full IStrategy Template

```python
"""
Sigma-Quant -> Freqtrade Strategy Bridge Template

Convert any Sigma-Quant BaseStrategyTemplate to Freqtrade IStrategy format.
This template covers all IStrategy lifecycle methods.
"""
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    CategoricalParameter,
    stoploss_from_open,
    stoploss_from_absolute,
)
from freqtrade.persistence import Trade
import freqtrade.vendor.qtpylib.indicators as qtpylib
import pandas_ta as ta
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


class SigmaQuantBridgeStrategy(IStrategy):
    """
    Template for Sigma-Quant strategies converted to Freqtrade.

    Methodology: Base Hit (Russian Doll Framework)
    - OUTER: Strategy TP/SL (entry model)
    - MIDDLE: Partial TPs (optional)
    - INNER: Cash Exit at loss MFE average
    """

    # ---------------------------------------------------------------
    # Strategy metadata
    # ---------------------------------------------------------------
    INTERFACE_VERSION = 3

    # Minimum ROI (time-based exit)
    # Set high to disable (let custom_exit handle exits)
    minimal_roi = {
        "0": 0.10,    # 10% ROI target
        "60": 0.05,   # 5% after 60 min
        "120": 0.02,  # 2% after 120 min
        "240": 0.01,  # 1% after 240 min
    }

    # Default stoploss (overridden by custom_stoploss)
    stoploss = -0.05  # -5% hard stop

    # Trailing stop
    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    # Timeframe
    timeframe = "5m"

    # Run on new candle only (not every tick)
    process_only_new_candles = True

    # Use exit signals
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles needed before strategy starts
    startup_candle_count = 50

    # Order types
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": True,
    }

    # ---------------------------------------------------------------
    # Hyperopt parameters (optimizable)
    # ---------------------------------------------------------------
    rsi_period = IntParameter(7, 25, default=14, space="buy", optimize=True)
    rsi_oversold = IntParameter(20, 40, default=30, space="buy", optimize=True)
    rsi_overbought = IntParameter(60, 80, default=70, space="sell", optimize=True)
    ema_fast = IntParameter(5, 20, default=9, space="buy", optimize=True)
    ema_slow = IntParameter(15, 50, default=21, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(1.0, 4.0, default=2.0, decimals=1, space="sell", optimize=True)

    # Base Hit parameters (from MFE analysis)
    cash_exit_pct = DecimalParameter(0.005, 0.03, default=0.01, decimals=3, space="sell", optimize=True)

    # ---------------------------------------------------------------
    # Indicator population
    # ---------------------------------------------------------------
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calculate all indicators needed by entry and exit logic.
        Called once per candle. Cache results in the dataframe.
        """
        # RSI
        dataframe["rsi"] = ta.rsi(dataframe["close"], length=self.rsi_period.value)

        # EMAs
        dataframe["ema_fast"] = ta.ema(dataframe["close"], length=self.ema_fast.value)
        dataframe["ema_slow"] = ta.ema(dataframe["close"], length=self.ema_slow.value)

        # ATR for dynamic stop
        dataframe["atr"] = ta.atr(
            dataframe["high"], dataframe["low"], dataframe["close"], length=14
        )

        # MACD
        macd = ta.macd(dataframe["close"], fast=12, slow=26, signal=9)
        dataframe["macd"] = macd["MACD_12_26_9"]
        dataframe["macd_signal"] = macd["MACDs_12_26_9"]
        dataframe["macd_hist"] = macd["MACDh_12_26_9"]

        # Bollinger Bands
        bbands = ta.bbands(dataframe["close"], length=20, std=2.0)
        dataframe["bb_upper"] = bbands["BBU_20_2.0"]
        dataframe["bb_lower"] = bbands["BBL_20_2.0"]
        dataframe["bb_mid"] = bbands["BBM_20_2.0"]

        # Volume SMA
        dataframe["volume_sma"] = ta.sma(dataframe["volume"], length=20)

        # EMA crossover signals (for qtpylib compatibility)
        dataframe["ema_cross_up"] = qtpylib.crossed_above(
            dataframe["ema_fast"], dataframe["ema_slow"]
        )
        dataframe["ema_cross_down"] = qtpylib.crossed_below(
            dataframe["ema_fast"], dataframe["ema_slow"]
        )

        return dataframe

    # ---------------------------------------------------------------
    # Entry conditions
    # ---------------------------------------------------------------
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define entry conditions. Sets 'enter_long' and 'enter_short' columns.
        For Freqtrade v3, use enter_long / enter_short (not buy/sell).
        """
        # Long entry conditions
        conditions_long = [
            dataframe["ema_cross_up"],
            dataframe["rsi"] < self.rsi_overbought.value,
            dataframe["rsi"] > self.rsi_oversold.value,
            dataframe["volume"] > dataframe["volume_sma"] * 1.0,
            dataframe["close"] > dataframe["bb_lower"],
        ]

        dataframe.loc[
            pd.DataFrame(conditions_long).all(axis=0),
            "enter_long"
        ] = 1

        # Short entry conditions (for futures/margin mode)
        conditions_short = [
            dataframe["ema_cross_down"],
            dataframe["rsi"] > self.rsi_oversold.value,
            dataframe["rsi"] < self.rsi_overbought.value,
            dataframe["volume"] > dataframe["volume_sma"] * 1.0,
            dataframe["close"] < dataframe["bb_upper"],
        ]

        dataframe.loc[
            pd.DataFrame(conditions_short).all(axis=0),
            "enter_short"
        ] = 1

        return dataframe

    # ---------------------------------------------------------------
    # Exit conditions
    # ---------------------------------------------------------------
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define exit conditions based on indicator signals.
        """
        # Long exit
        conditions_exit_long = [
            dataframe["ema_cross_down"],
            dataframe["rsi"] > self.rsi_overbought.value,
        ]

        dataframe.loc[
            pd.DataFrame(conditions_exit_long).any(axis=0),
            "exit_long"
        ] = 1

        # Short exit
        conditions_exit_short = [
            dataframe["ema_cross_up"],
            dataframe["rsi"] < self.rsi_oversold.value,
        ]

        dataframe.loc[
            pd.DataFrame(conditions_exit_short).any(axis=0),
            "exit_short"
        ] = 1

        return dataframe

    # ---------------------------------------------------------------
    # Custom stoploss (Base Hit methodology)
    # ---------------------------------------------------------------
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs
    ) -> Optional[float]:
        """
        Dynamic stoploss using ATR.
        Returns negative float representing distance from current_rate.
        Return -1 to keep using the previous stoploss.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if len(dataframe) < 1:
            return -1  # Keep existing stoploss

        last_candle = dataframe.iloc[-1]
        atr = last_candle.get("atr", 0)

        if atr == 0:
            return -1

        # ATR-based stop: multiplier * ATR / current_price
        atr_stop_distance = (self.atr_multiplier.value * atr) / current_rate

        return -atr_stop_distance

    # ---------------------------------------------------------------
    # Custom exit (Base Hit cash exit)
    # ---------------------------------------------------------------
    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs
    ) -> Optional[str]:
        """
        Base Hit cash exit: close at loss MFE average.
        This is the INNER layer of the Russian Doll framework.

        Returns exit reason string or None.
        """
        # Cash exit: take profit at loss MFE average
        if current_profit >= self.cash_exit_pct.value:
            return f"cash_exit_{self.cash_exit_pct.value:.3f}"

        # Time-based exit (optional)
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
        if trade_duration > 24:  # Max 24 hours
            return "time_exit_24h"

        return None

    # ---------------------------------------------------------------
    # Position sizing (leverage)
    # ---------------------------------------------------------------
    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        Custom leverage. Return desired leverage (1-max_leverage).
        Conservative default: 3x.
        """
        return min(3.0, max_leverage)

    # ---------------------------------------------------------------
    # Informative pairs (multi-timeframe)
    # ---------------------------------------------------------------
    def informative_pairs(self) -> list:
        """
        Define additional pairs/timeframes for multi-timeframe analysis.
        """
        return [
            (self.config["stake_currency"], "1h"),  # Higher timeframe for trend
        ]
```

## Freqtrade Configuration Template

### Dry-Run (Paper Trading)

```json
{
    "trading_mode": "futures",
    "margin_mode": "isolated",
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "dry_run": true,
    "dry_run_wallet": 10000,
    "cancel_open_orders_on_exit": true,

    "exchange": {
        "name": "binance",
        "key": "",
        "secret": "",
        "ccxt_config": {},
        "ccxt_async_config": {},
        "pair_whitelist": [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "SOL/USDT:USDT"
        ],
        "pair_blacklist": []
    },

    "entry_pricing": {
        "price_side": "other",
        "use_order_book": true,
        "order_book_top": 1
    },

    "exit_pricing": {
        "price_side": "other",
        "use_order_book": true,
        "order_book_top": 1
    },

    "order_types": {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": true
    },

    "pairlists": [
        {
            "method": "StaticPairList"
        }
    ],

    "telegram": {
        "enabled": false,
        "token": "",
        "chat_id": ""
    },

    "api_server": {
        "enabled": true,
        "listen_ip_address": "127.0.0.1",
        "listen_port": 8080,
        "verbosity": "error",
        "enable_openapi": true,
        "jwt_secret_key": "change-me-in-production",
        "CORS_origins": [],
        "username": "freqtrader",
        "password": "freqtrader"
    },

    "bot_name": "sigma_quant_dry_run",
    "initial_state": "running",
    "force_entry_enable": false
}
```

### Live Trading Configuration

```json
{
    "trading_mode": "futures",
    "margin_mode": "isolated",
    "dry_run": false,
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 100,

    "exchange": {
        "name": "binance",
        "key": "${BINANCE_API_KEY}",
        "secret": "${BINANCE_API_SECRET}",
        "ccxt_config": {
            "enableRateLimit": true,
            "rateLimit": 200
        },
        "pair_whitelist": [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT"
        ]
    }
}
```

## Hyperopt Integration (Walk-Forward Optimization)

### Running Hyperopt

```bash
# Basic hyperopt with Sharpe ratio loss function
freqtrade hyperopt \
    --strategy SigmaQuantBridgeStrategy \
    --hyperopt-loss SharpeHyperOptLoss \
    --spaces buy sell \
    --epochs 500 \
    --timerange 20240101-20250101 \
    -j 4  # Parallel jobs

# Walk-forward: train on 6 months, test on 2 months
freqtrade hyperopt \
    --strategy SigmaQuantBridgeStrategy \
    --hyperopt-loss SharpeHyperOptLoss \
    --spaces buy sell \
    --epochs 200 \
    --timerange 20240101-20240701 \
    -j 4

# Then validate OOS
freqtrade backtesting \
    --strategy SigmaQuantBridgeStrategy \
    --timerange 20240701-20240901
```

### Custom Hyperopt Loss (Base Hit Aware)

```python
"""
Custom hyperopt loss function that incorporates Base Hit methodology.
File: user_data/hyperopts/BaseHitHyperOptLoss.py
"""
from freqtrade.optimize.hyperopt import IHyperOptLoss
from datetime import datetime
import numpy as np


class BaseHitHyperOptLoss(IHyperOptLoss):
    """
    Optimizes for Base Hit metrics:
    1. Consistent small wins (cash exit at loss MFE)
    2. Sharpe ratio
    3. Drawdown control
    """

    @staticmethod
    def hyperopt_loss_function(
        results: dict,
        trade_count: int,
        min_date: datetime,
        max_date: datetime,
        config: dict,
        processed: dict,
        backtest_stats: dict,
        **kwargs,
    ) -> float:
        """
        Lower = better.
        """
        # Minimum trade count
        if trade_count < 50:
            return 1000.0

        # Extract metrics
        total_profit = results["profit_abs"].sum()
        win_rate = len(results[results["profit_abs"] > 0]) / trade_count
        max_drawdown = backtest_stats.get("max_drawdown_abs", 0)

        # Sharpe ratio approximation
        returns = results["profit_abs"]
        if returns.std() > 0:
            sharpe = returns.mean() / returns.std() * np.sqrt(252)
        else:
            sharpe = 0

        # Red flag: Sharpe > 3.0 is suspicious
        if sharpe > 3.0:
            sharpe = 1.0  # Penalize

        # Composite loss (lower = better)
        loss = -(
            sharpe * 0.4 +
            win_rate * 0.2 +
            (total_profit / 10000) * 0.2 +  # Normalized profit
            (1 - max_drawdown / 10000) * 0.2  # Drawdown penalty
        )

        return loss
```

## Sigma-Quant-to-Freqtrade Conversion Mapping

| Sigma-Quant (BaseStrategyTemplate) | Freqtrade (IStrategy) |
|--------------------------------|----------------------|
| `STRATEGY_NAME` | Class name |
| `STRATEGY_VERSION` | `INTERFACE_VERSION` |
| `SUPPORTED_SYMBOLS` | `pair_whitelist` in config |
| `SUPPORTED_TIMEFRAMES` | `timeframe` attribute |
| `get_parameters()` | `IntParameter`, `DecimalParameter` |
| `generate_signal()` | `populate_entry_trend()` + `populate_exit_trend()` |
| `stop_loss` | `stoploss` + `custom_stoploss()` |
| `take_profit` | `minimal_roi` + `custom_exit()` |
| Base Hit cash exit | `custom_exit()` with `cash_exit_pct` |
| Walk-forward | `freqtrade hyperopt` + timerange splits |
| Prop firm compliance | N/A (use `quant-exchange-compliance`) |

## CCXT Exchange Support (100+)

Freqtrade uses CCXT under the hood, supporting all major exchanges:

| Tier | Exchanges | Notes |
|------|-----------|-------|
| Tier 1 (best tested) | Binance, Bybit, OKX, Kraken | Full futures support |
| Tier 2 (well supported) | Gate.io, Kucoin, Bitget, MEXC | Some quirks |
| Tier 3 (community) | HTX, Phemex, BingX | May need custom config |
| DEX (via adapter) | Hyperliquid (custom) | Not native CCXT |

### Exchange-Specific Config Notes

```python
# Binance futures
exchange_config = {
    "name": "binance",
    "ccxt_config": {"options": {"defaultType": "future"}},
}

# Bybit unified trading
exchange_config = {
    "name": "bybit",
    "ccxt_config": {"options": {"defaultType": "linear"}},
}

# OKX
exchange_config = {
    "name": "okx",
    "ccxt_config": {"options": {"defaultType": "swap"}},
}
```

## Key Formulas

### Hyperopt Epochs Estimate

```
recommended_epochs = num_parameters * 100
# 6 parameters * 100 = 600 epochs minimum
```

### Walk-Forward Splits

```
total_data = 2 years
train_window = 6 months (rolling)
test_window = 2 months (out-of-sample)
folds = (total_data - train_window) / test_window = 9 folds
```

### Fee Adjustment

```python
# Freqtrade config
"exchange": {
    "name": "binance",
    "fee": {
        "maker": 0.0002,  # 2 bps
        "taker": 0.0004,  # 4 bps
    }
}
```

## Common Pitfalls

1. **populate_indicators called once per candle** -- Do not put stateful logic in indicator population. It re-runs on startup with full history.
2. **Hyperopt overfits easily** -- Always validate OOS. Use walk-forward splits, not random shuffle.
3. **Dry-run != live** -- Dry-run assumes instant fills at candle close. Live trading has slippage and partial fills.
4. **Stoploss on exchange vs local** -- `stoploss_on_exchange: true` places a real stop order. Much safer than local monitoring.
5. **CCXT rate limits** -- Each exchange has different limits. Binance is generous; Bybit is stricter. Set `enableRateLimit: true`.
6. **Futures pair format** -- Use `BTC/USDT:USDT` (not `BTC/USDT`) for futures pairs. The `:USDT` suffix indicates USDT-margined.
7. **Timeframe alignment** -- Freqtrade candles may not align exactly with exchange candles during DST changes.

## Running Freqtrade

```bash
# Install
pip install freqtrade

# Initialize user directory
freqtrade create-userdir --userdir user_data

# Download data for backtesting
freqtrade download-data \
    --exchange binance \
    --pairs BTC/USDT:USDT ETH/USDT:USDT \
    --timeframe 5m \
    --timerange 20230101-20260101 \
    --trading-mode futures

# Run backtest
freqtrade backtesting \
    --strategy SigmaQuantBridgeStrategy \
    --timerange 20240101-20250101 \
    --timeframe 5m

# Start dry-run
freqtrade trade \
    --strategy SigmaQuantBridgeStrategy \
    --config config_dry_run.json

# Start live
freqtrade trade \
    --strategy SigmaQuantBridgeStrategy \
    --config config_live.json
```

## Reference Sources

- Freqtrade documentation: `https://www.freqtrade.io/en/stable/`
- Freqtrade GitHub: `https://github.com/freqtrade/freqtrade`
- CCXT exchange list: `https://github.com/ccxt/ccxt`
- Sigma-Quant strategy base: `lib/backtest_runner.py`

## Related Skills

- `trading-strategies` -- Sigma-Quant BaseStrategyTemplate (source format)
- `quant-base-hit-analysis` -- MFE analysis feeding cash_exit_pct
- `quant-walk-forward-validation` -- Walk-forward methodology
- `quant-exchange-compliance` -- Crypto exchange risk rules
- `quant-crypto-cost-modeling` -- Fee models for cost-aware backtesting
