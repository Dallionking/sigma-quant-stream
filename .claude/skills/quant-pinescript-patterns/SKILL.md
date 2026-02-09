---
name: quant-pinescript-patterns
description: "PineScript to Python translation patterns for converting TradingView strategies"
version: "1.0.0"
triggers:
  - "when converting PineScript to Python"
  - "when importing TradingView strategies"
  - "when translating indicator code"
  - "when parsing Pine syntax"
---

# Quant PineScript Patterns

## Purpose

Provides comprehensive patterns for translating PineScript (TradingView) code to Python for use in Sigma-Quant's backtesting and live trading systems. Covers function mappings, variable handling, plotting conversion, and common pitfalls.

## When to Use

- Converting community strategies from TradingView
- Importing paid indicators for validation
- Translating custom PineScript indicators
- Building Python equivalents of Pine built-ins
- Validating Pine strategy results in Python

## Key Concepts

### PineScript vs Python Paradigms

| Aspect | PineScript | Python |
|--------|------------|--------|
| **Execution** | Bar-by-bar | Vectorized (preferred) |
| **State** | Automatic persistence | Explicit management |
| **Series** | Native series type | pandas Series/numpy |
| **NA Handling** | Built-in na type | np.nan / pd.NA |
| **Indexing** | [0]=current, [1]=prev | df.shift(1) for prev |
| **Plotting** | Built-in plot() | Matplotlib/Plotly |

### Critical Translation Rules

1. **Pine [N] = Python .shift(N)**
2. **Pine na = Python np.nan**
3. **Pine var = Python class attribute**
4. **Pine barstate.* = Python custom logic**
5. **Pine security() = Python separate data fetch**

## Patterns & Templates

### Built-in Function Mappings

```python
"""
PineScript to Python function mappings.
"""
import numpy as np
import pandas as pd
from typing import Union

Series = Union[pd.Series, np.ndarray]

# ============================================================
# MATH FUNCTIONS
# ============================================================

def pine_abs(x: Series) -> Series:
    """abs(x) -> absolute value"""
    return np.abs(x)

def pine_max(a: Series, b: Series) -> Series:
    """max(a, b) -> element-wise maximum"""
    return np.maximum(a, b)

def pine_min(a: Series, b: Series) -> Series:
    """min(a, b) -> element-wise minimum"""
    return np.minimum(a, b)

def pine_pow(base: Series, exp: float) -> Series:
    """pow(base, exp) -> power"""
    return np.power(base, exp)

def pine_sqrt(x: Series) -> Series:
    """sqrt(x) -> square root"""
    return np.sqrt(x)

def pine_log(x: Series) -> Series:
    """log(x) -> natural log"""
    return np.log(x)

def pine_exp(x: Series) -> Series:
    """exp(x) -> e^x"""
    return np.exp(x)

def pine_round(x: Series, precision: int = 0) -> Series:
    """round(x, precision) -> round to precision"""
    return np.round(x, precision)

def pine_floor(x: Series) -> Series:
    """floor(x) -> floor"""
    return np.floor(x)

def pine_ceil(x: Series) -> Series:
    """ceil(x) -> ceiling"""
    return np.ceil(x)

def pine_sign(x: Series) -> Series:
    """sign(x) -> -1, 0, or 1"""
    return np.sign(x)

# ============================================================
# SERIES FUNCTIONS
# ============================================================

def pine_nz(x: Series, replacement: float = 0) -> Series:
    """nz(x, y) -> replace NaN with y (default 0)"""
    return pd.Series(x).fillna(replacement).values

def pine_na(x: Series) -> Series:
    """na(x) -> True where x is NaN"""
    return pd.isna(x)

def pine_fixnan(x: Series) -> Series:
    """fixnan(x) -> forward fill NaN values"""
    return pd.Series(x).ffill().values

def pine_highest(src: Series, length: int) -> Series:
    """highest(src, length) -> rolling max"""
    return pd.Series(src).rolling(length).max().values

def pine_lowest(src: Series, length: int) -> Series:
    """lowest(src, length) -> rolling min"""
    return pd.Series(src).rolling(length).min().values

def pine_sum(src: Series, length: int) -> Series:
    """sum(src, length) -> rolling sum"""
    return pd.Series(src).rolling(length).sum().values

def pine_cum(src: Series) -> Series:
    """cum(src) -> cumulative sum"""
    return pd.Series(src).cumsum().values

def pine_change(src: Series, length: int = 1) -> Series:
    """change(src, length) -> difference from length bars ago"""
    return pd.Series(src).diff(length).values

def pine_rising(src: Series, length: int) -> Series:
    """rising(src, length) -> True if rising for length bars"""
    s = pd.Series(src)
    return (s.diff() > 0).rolling(length).sum() == length

def pine_falling(src: Series, length: int) -> Series:
    """falling(src, length) -> True if falling for length bars"""
    s = pd.Series(src)
    return (s.diff() < 0).rolling(length).sum() == length

def pine_cross(a: Series, b: Series) -> Series:
    """cross(a, b) -> True when a crosses b (either direction)"""
    return pine_crossover(a, b) | pine_crossunder(a, b)

def pine_crossover(a: Series, b: Series) -> Series:
    """crossover(a, b) -> True when a crosses above b"""
    a_s = pd.Series(a)
    b_s = pd.Series(b)
    return (a_s > b_s) & (a_s.shift(1) <= b_s.shift(1))

def pine_crossunder(a: Series, b: Series) -> Series:
    """crossunder(a, b) -> True when a crosses below b"""
    a_s = pd.Series(a)
    b_s = pd.Series(b)
    return (a_s < b_s) & (a_s.shift(1) >= b_s.shift(1))

def pine_valuewhen(condition: Series, src: Series, occurrence: int = 0) -> Series:
    """valuewhen(cond, src, occurrence) -> value of src when condition was true"""
    s = pd.Series(src)
    c = pd.Series(condition)

    # Get indices where condition is True
    true_indices = c[c].index.tolist()

    result = pd.Series(index=s.index, dtype=float)

    for i in range(len(s)):
        # Find the nth occurrence before current bar
        past_true = [idx for idx in true_indices if idx < i]
        if len(past_true) > occurrence:
            target_idx = past_true[-(occurrence + 1)]
            result.iloc[i] = s.iloc[target_idx]
        else:
            result.iloc[i] = np.nan

    return result.values

def pine_barssince(condition: Series) -> Series:
    """barssince(cond) -> bars since condition was True"""
    c = pd.Series(condition)

    # Create groups where each True starts a new group
    groups = c.cumsum()

    # Count within each group
    result = c.groupby(groups).cumcount()

    # Set to NaN where condition was never True
    first_true = c.idxmax() if c.any() else len(c)
    result[:first_true] = np.nan

    return result.values

# ============================================================
# MOVING AVERAGES
# ============================================================

def pine_sma(src: Series, length: int) -> Series:
    """sma(src, length) -> Simple Moving Average"""
    return pd.Series(src).rolling(length).mean().values

def pine_ema(src: Series, length: int) -> Series:
    """ema(src, length) -> Exponential Moving Average"""
    return pd.Series(src).ewm(span=length, adjust=False).mean().values

def pine_wma(src: Series, length: int) -> Series:
    """wma(src, length) -> Weighted Moving Average"""
    weights = np.arange(1, length + 1)
    return pd.Series(src).rolling(length).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    ).values

def pine_vwma(src: Series, volume: Series, length: int) -> Series:
    """vwma(src, volume, length) -> Volume Weighted Moving Average"""
    s = pd.Series(src)
    v = pd.Series(volume)
    return (s * v).rolling(length).sum() / v.rolling(length).sum()

def pine_rma(src: Series, length: int) -> Series:
    """rma(src, length) -> RSI-style Moving Average (Wilder's)"""
    alpha = 1.0 / length
    return pd.Series(src).ewm(alpha=alpha, adjust=False).mean().values

def pine_hma(src: Series, length: int) -> Series:
    """hma(src, length) -> Hull Moving Average"""
    half_length = int(length / 2)
    sqrt_length = int(np.sqrt(length))

    wma_half = pine_wma(src, half_length)
    wma_full = pine_wma(src, length)
    raw_hma = 2 * wma_half - wma_full

    return pine_wma(raw_hma, sqrt_length)

def pine_alma(src: Series, length: int, offset: float = 0.85, sigma: float = 6) -> Series:
    """alma(src, length, offset, sigma) -> Arnaud Legoux Moving Average"""
    m = offset * (length - 1)
    s = length / sigma

    weights = np.exp(-((np.arange(length) - m) ** 2) / (2 * s * s))
    weights = weights / weights.sum()

    return pd.Series(src).rolling(length).apply(
        lambda x: np.dot(x, weights), raw=True
    ).values

# ============================================================
# INDICATORS
# ============================================================

def pine_rsi(src: Series, length: int) -> Series:
    """rsi(src, length) -> Relative Strength Index"""
    s = pd.Series(src)
    delta = s.diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = pine_rma(gain, length)
    avg_loss = pine_rma(loss, length)

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def pine_macd(src: Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """macd(src, fast, slow, signal) -> (macd_line, signal_line, histogram)"""
    fast_ema = pine_ema(src, fast)
    slow_ema = pine_ema(src, slow)

    macd_line = fast_ema - slow_ema
    signal_line = pine_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram

def pine_stoch(high: Series, low: Series, close: Series, k_length: int,
               k_smooth: int = 1, d_smooth: int = 3) -> tuple:
    """stoch(high, low, close, k, k_smooth, d) -> (k_line, d_line)"""
    lowest_low = pine_lowest(low, k_length)
    highest_high = pine_highest(high, k_length)

    stoch = 100 * (close - lowest_low) / (highest_high - lowest_low)
    k_line = pine_sma(stoch, k_smooth)
    d_line = pine_sma(k_line, d_smooth)

    return k_line, d_line

def pine_bb(src: Series, length: int, mult: float = 2.0) -> tuple:
    """bb(src, length, mult) -> (middle, upper, lower)"""
    middle = pine_sma(src, length)
    std = pd.Series(src).rolling(length).std().values

    upper = middle + mult * std
    lower = middle - mult * std

    return middle, upper, lower

def pine_atr(high: Series, low: Series, close: Series, length: int) -> Series:
    """atr(high, low, close, length) -> Average True Range"""
    tr = pine_tr(high, low, close)
    return pine_rma(tr, length)

def pine_tr(high: Series, low: Series, close: Series) -> Series:
    """tr(high, low, close) -> True Range"""
    h = pd.Series(high)
    l = pd.Series(low)
    c = pd.Series(close)

    tr1 = h - l
    tr2 = np.abs(h - c.shift(1))
    tr3 = np.abs(l - c.shift(1))

    return np.maximum(np.maximum(tr1, tr2), tr3)

def pine_cci(high: Series, low: Series, close: Series, length: int) -> Series:
    """cci(high, low, close, length) -> Commodity Channel Index"""
    tp = (high + low + close) / 3
    sma_tp = pine_sma(tp, length)
    mean_dev = pd.Series(tp).rolling(length).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    ).values

    return (tp - sma_tp) / (0.015 * mean_dev)

def pine_mfi(high: Series, low: Series, close: Series, volume: Series, length: int) -> Series:
    """mfi(high, low, close, volume, length) -> Money Flow Index"""
    tp = (high + low + close) / 3
    mf = tp * volume

    tp_s = pd.Series(tp)
    change = tp_s.diff()

    pos_mf = pd.Series(np.where(change > 0, mf, 0))
    neg_mf = pd.Series(np.where(change < 0, mf, 0))

    pos_sum = pos_mf.rolling(length).sum()
    neg_sum = neg_mf.rolling(length).sum()

    mfi = 100 - (100 / (1 + pos_sum / neg_sum))
    return mfi.values

def pine_adx(high: Series, low: Series, close: Series, length: int) -> tuple:
    """adx(high, low, close, length) -> (adx, plus_di, minus_di)"""
    h = pd.Series(high)
    l = pd.Series(low)

    up = h.diff()
    down = -l.diff()

    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)

    tr = pine_tr(high, low, close)
    atr = pine_rma(tr, length)

    plus_di = 100 * pine_rma(plus_dm, length) / atr
    minus_di = 100 * pine_rma(minus_dm, length) / atr

    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = pine_rma(dx, length)

    return adx, plus_di, minus_di

# ============================================================
# PIVOT / SUPPORT / RESISTANCE
# ============================================================

def pine_pivothigh(src: Series, left: int, right: int) -> Series:
    """pivothigh(src, left, right) -> pivot high values (NaN otherwise)"""
    s = pd.Series(src)
    result = pd.Series(index=s.index, dtype=float)

    for i in range(left, len(s) - right):
        window_left = s.iloc[i-left:i]
        window_right = s.iloc[i+1:i+right+1]
        current = s.iloc[i]

        if (current >= window_left.max()) and (current >= window_right.max()):
            result.iloc[i + right] = current  # Confirmed after right bars

    return result.values

def pine_pivotlow(src: Series, left: int, right: int) -> Series:
    """pivotlow(src, left, right) -> pivot low values (NaN otherwise)"""
    s = pd.Series(src)
    result = pd.Series(index=s.index, dtype=float)

    for i in range(left, len(s) - right):
        window_left = s.iloc[i-left:i]
        window_right = s.iloc[i+1:i+right+1]
        current = s.iloc[i]

        if (current <= window_left.min()) and (current <= window_right.min()):
            result.iloc[i + right] = current

    return result.values
```

### Variable Handling Patterns

```python
"""
PineScript variable patterns translated to Python.
"""

# ============================================================
# var KEYWORD (Persistent Variables)
# ============================================================

# Pine:
# var int count = 0
# if condition
#     count := count + 1

# Python (Class-based):
class StrategyState:
    def __init__(self):
        self.count = 0

    def update(self, condition: bool):
        if condition:
            self.count += 1

# Python (Functional with closure):
def create_counter():
    count = [0]  # List to allow mutation in closure

    def update(condition: bool) -> int:
        if condition:
            count[0] += 1
        return count[0]

    return update

# ============================================================
# varip KEYWORD (Intrabar Persistent)
# ============================================================

# Pine:
# varip float highest_intrabar = na
# if high > nz(highest_intrabar)
#     highest_intrabar := high

# Python (Only relevant for live trading, not backtesting):
class IntrabarState:
    def __init__(self):
        self.highest_intrabar = np.nan
        self._last_bar_index = -1

    def update(self, bar_index: int, high: float):
        if bar_index != self._last_bar_index:
            # New bar, reset
            self.highest_intrabar = np.nan
            self._last_bar_index = bar_index

        if np.isnan(self.highest_intrabar) or high > self.highest_intrabar:
            self.highest_intrabar = high

# ============================================================
# Series Referencing [N]
# ============================================================

# Pine:
# prev_close = close[1]
# two_bars_ago = close[2]
# prev_high_above_close = high[1] > close[1]

# Python:
def translate_series_reference(df: pd.DataFrame):
    # close[1] -> shift(1)
    df['prev_close'] = df['close'].shift(1)

    # close[2] -> shift(2)
    df['two_bars_ago'] = df['close'].shift(2)

    # high[1] > close[1]
    df['prev_high_above_close'] = df['high'].shift(1) > df['close'].shift(1)

# ============================================================
# Ternary / Conditional
# ============================================================

# Pine:
# result = condition ? value_if_true : value_if_false

# Python:
def pine_ternary(condition, true_val, false_val):
    return np.where(condition, true_val, false_val)

# ============================================================
# := Assignment Operator
# ============================================================

# Pine:
# x := x + 1  // Modify existing variable

# Python - use regular assignment:
# x = x + 1
```

### Strategy Entry/Exit Translation

```python
"""
PineScript strategy entry/exit patterns.
"""

# ============================================================
# strategy.entry() / strategy.exit()
# ============================================================

# Pine:
# strategy.entry("Long", strategy.long, when=buy_signal)
# strategy.exit("Exit Long", "Long", stop=stop_price, limit=take_profit)

# Python (Backtesting format):
class PineStrategyTranslator:
    """
    Translates Pine strategy commands to Python signals.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df['signal'] = 0
        self.df['stop_loss'] = np.nan
        self.df['take_profit'] = np.nan

    def entry(self, name: str, direction: str, when: pd.Series,
              stop: pd.Series = None, limit: pd.Series = None):
        """
        strategy.entry() equivalent.
        direction: 'long' or 'short'
        """
        signal_value = 1 if direction == 'long' else -1
        self.df.loc[when, 'signal'] = signal_value

        if stop is not None:
            self.df.loc[when, 'stop_loss'] = stop
        if limit is not None:
            self.df.loc[when, 'take_profit'] = limit

    def exit(self, name: str, from_entry: str,
             stop: pd.Series = None, limit: pd.Series = None,
             when: pd.Series = None):
        """
        strategy.exit() equivalent.
        """
        if when is not None:
            self.df.loc[when, 'signal'] = 0  # Close position

        # Stop and limit are tracked for backtester
        if stop is not None:
            self.df['exit_stop'] = stop
        if limit is not None:
            self.df['exit_limit'] = limit

    def close(self, name: str, when: pd.Series):
        """
        strategy.close() equivalent.
        """
        self.df.loc[when, 'signal'] = 0

    def get_signals(self) -> pd.DataFrame:
        return self.df[['signal', 'stop_loss', 'take_profit']]


# Example translation:
def translate_pine_strategy(df: pd.DataFrame):
    """
    Original Pine:

    //@version=5
    strategy("MA Cross", overlay=true)

    fast = ta.sma(close, 9)
    slow = ta.sma(close, 21)

    buy = ta.crossover(fast, slow)
    sell = ta.crossunder(fast, slow)

    strategy.entry("Long", strategy.long, when=buy)
    strategy.exit("Exit", "Long", stop=close - 2*ta.atr(14), limit=close + 4*ta.atr(14))
    strategy.close("Long", when=sell)
    """

    # Calculate indicators
    df['fast_ma'] = pine_sma(df['close'], 9)
    df['slow_ma'] = pine_sma(df['close'], 21)
    df['atr'] = pine_atr(df['high'], df['low'], df['close'], 14)

    # Generate signals
    df['buy'] = pine_crossover(df['fast_ma'], df['slow_ma'])
    df['sell'] = pine_crossunder(df['fast_ma'], df['slow_ma'])

    # Create strategy translator
    strategy = PineStrategyTranslator(df)

    # Translate entries/exits
    strategy.entry(
        "Long", "long",
        when=df['buy'],
        stop=df['close'] - 2 * df['atr'],
        limit=df['close'] + 4 * df['atr']
    )
    strategy.close("Long", when=df['sell'])

    return strategy.get_signals()
```

### Plotting Conversion

```python
"""
PineScript plotting to Python visualization.
"""
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# plot() Function
# ============================================================

# Pine:
# plot(sma_20, color=color.blue, linewidth=2, title="SMA 20")
# plot(rsi, color=rsi > 70 ? color.red : color.green)

# Python (Matplotlib):
def pine_plot_matplotlib(df: pd.DataFrame, configs: list[dict]):
    """
    configs: [{"column": "sma_20", "color": "blue", "linewidth": 2, "title": "SMA 20"}]
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    for config in configs:
        ax.plot(
            df.index,
            df[config["column"]],
            color=config.get("color", "blue"),
            linewidth=config.get("linewidth", 1),
            label=config.get("title", config["column"])
        )

    ax.legend()
    return fig

# Python (Plotly - Interactive):
def pine_plot_plotly(df: pd.DataFrame, configs: list[dict]):
    fig = go.Figure()

    for config in configs:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[config["column"]],
            mode='lines',
            name=config.get("title", config["column"]),
            line=dict(
                color=config.get("color", "blue"),
                width=config.get("linewidth", 1)
            )
        ))

    return fig

# ============================================================
# plotshape() / plotchar()
# ============================================================

# Pine:
# plotshape(buy_signal, style=shape.triangleup, location=location.belowbar, color=color.green)

# Python (Plotly):
def pine_plotshape(fig, df: pd.DataFrame, condition_col: str,
                   price_col: str = 'low', shape: str = 'triangle-up',
                   color: str = 'green', offset: float = 0.001):
    """
    Add shape markers to chart.
    """
    mask = df[condition_col] == True

    fig.add_trace(go.Scatter(
        x=df[mask].index,
        y=df.loc[mask, price_col] * (1 - offset),  # Below bar
        mode='markers',
        marker=dict(
            symbol=shape,
            size=12,
            color=color
        ),
        name=condition_col
    ))

    return fig

# ============================================================
# hline() / fill()
# ============================================================

# Pine:
# h1 = hline(70, "Overbought", color=color.red)
# h2 = hline(30, "Oversold", color=color.green)
# fill(h1, h2, color=color.new(color.purple, 90))

# Python (Plotly):
def pine_hline_fill(fig, upper: float, lower: float,
                    upper_color: str = 'red', lower_color: str = 'green',
                    fill_color: str = 'rgba(128, 0, 128, 0.1)'):
    """
    Add horizontal lines with fill.
    """
    fig.add_hline(y=upper, line_color=upper_color, line_dash="dash",
                  annotation_text="Overbought")
    fig.add_hline(y=lower, line_color=lower_color, line_dash="dash",
                  annotation_text="Oversold")

    fig.add_hrect(y0=lower, y1=upper, fillcolor=fill_color,
                  line_width=0, layer="below")

    return fig
```

## Examples

### Example 1: Complete Strategy Translation

```python
"""
Translate a complete Pine strategy to Python.

Original Pine:
//@version=5
strategy("RSI Mean Reversion", overlay=false)

// Inputs
rsi_length = input.int(14, "RSI Length")
overbought = input.float(70, "Overbought")
oversold = input.float(30, "Oversold")
atr_mult = input.float(2.0, "ATR Multiplier")

// Indicators
rsi = ta.rsi(close, rsi_length)
atr = ta.atr(14)

// Signals
buy_signal = ta.crossover(rsi, oversold)
sell_signal = ta.crossunder(rsi, overbought)

// Strategy
if buy_signal
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=close - atr_mult * atr, limit=close + atr_mult * 2 * atr)

if sell_signal
    strategy.close("Long")

// Plot
plot(rsi, color=color.blue)
hline(overbought, color=color.red)
hline(oversold, color=color.green)
plotshape(buy_signal, style=shape.triangleup, location=location.bottom, color=color.green)
"""

import pandas as pd
import numpy as np

class RSIMeanReversionStrategy:
    """
    Python translation of RSI Mean Reversion strategy.
    """

    def __init__(
        self,
        rsi_length: int = 14,
        overbought: float = 70,
        oversold: float = 30,
        atr_mult: float = 2.0
    ):
        self.rsi_length = rsi_length
        self.overbought = overbought
        self.oversold = oversold
        self.atr_mult = atr_mult

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI and ATR."""
        df = df.copy()

        # RSI
        df['rsi'] = pine_rsi(df['close'], self.rsi_length)

        # ATR
        df['atr'] = pine_atr(df['high'], df['low'], df['close'], 14)

        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate buy/sell signals."""
        df = self.calculate_indicators(df)

        # Buy signal: RSI crosses above oversold
        df['buy_signal'] = pine_crossover(df['rsi'], self.oversold)

        # Sell signal: RSI crosses below overbought
        df['sell_signal'] = pine_crossunder(df['rsi'], self.overbought)

        # Position signals
        df['signal'] = 0
        df.loc[df['buy_signal'], 'signal'] = 1
        df.loc[df['sell_signal'], 'signal'] = -1  # Close signal

        # Stop loss and take profit levels
        df['stop_loss'] = df['close'] - self.atr_mult * df['atr']
        df['take_profit'] = df['close'] + self.atr_mult * 2 * df['atr']

        return df

    def plot(self, df: pd.DataFrame):
        """Create Pine-style chart."""
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           vertical_spacing=0.03,
                           row_heights=[0.7, 0.3])

        # Price chart
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'], high=df['high'],
            low=df['low'], close=df['close'],
            name='Price'
        ), row=1, col=1)

        # RSI
        fig.add_trace(go.Scatter(
            x=df.index, y=df['rsi'],
            mode='lines', name='RSI',
            line=dict(color='blue')
        ), row=2, col=1)

        # RSI levels
        fig.add_hline(y=self.overbought, line_color='red',
                     line_dash='dash', row=2, col=1)
        fig.add_hline(y=self.oversold, line_color='green',
                     line_dash='dash', row=2, col=1)

        # Buy signals
        buy_mask = df['buy_signal']
        fig.add_trace(go.Scatter(
            x=df[buy_mask].index,
            y=df.loc[buy_mask, 'low'] * 0.998,
            mode='markers',
            marker=dict(symbol='triangle-up', size=12, color='green'),
            name='Buy'
        ), row=1, col=1)

        return fig


# Usage
strategy = RSIMeanReversionStrategy(rsi_length=14, oversold=30, overbought=70)
df = strategy.generate_signals(price_data)
fig = strategy.plot(df)
```

## Common Mistakes

### 1. Incorrect Indexing Direction

```python
# WRONG: Pine [1] = previous bar, not Python index
prev_close = df['close'][1]  # This gets the second row, not previous bar!

# RIGHT: Use shift() for previous bars
prev_close = df['close'].shift(1)  # Previous bar's close
```

### 2. Missing NA Handling

```python
# WRONG: Not handling NA values
rsi_signal = df['rsi'] < 30  # May have NaN at start

# RIGHT: Handle NA explicitly
rsi_signal = (df['rsi'] < 30) & (~df['rsi'].isna())
```

### 3. Wrong EMA Calculation

```python
# WRONG: Using wrong alpha
ema = df['close'].ewm(alpha=1/length).mean()  # Wrong!

# RIGHT: Use span parameter for Pine-equivalent EMA
ema = df['close'].ewm(span=length, adjust=False).mean()
```

### 4. Forgetting adjust=False

```python
# WRONG: Default adjust=True gives different results than Pine
ema = df['close'].ewm(span=14).mean()

# RIGHT: Pine uses adjust=False equivalent
ema = df['close'].ewm(span=14, adjust=False).mean()
```

### 5. Vectorized vs Bar-by-Bar

```python
# WRONG: Trying to use bar-by-bar logic in vectorized context
for i in range(len(df)):
    if df['rsi'].iloc[i] < 30:
        df['signal'].iloc[i] = 1

# RIGHT: Vectorized operations
df['signal'] = np.where(df['rsi'] < 30, 1, 0)
```
