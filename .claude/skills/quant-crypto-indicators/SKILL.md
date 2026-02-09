---
name: quant-crypto-indicators
description: "Crypto-native indicators with pandas implementation patterns"
version: "1.0.0"
triggers:
  - "when implementing crypto indicators"
  - "when calculating CVD or funding rate oscillator"
  - "when working with on-chain valuation metrics"
  - "when building crypto signal features"
---

# Quant Crypto Indicators

## Purpose

Provides pandas implementation patterns for crypto-native indicators that don't exist in traditional finance. These indicators exploit unique crypto data: funding rates, on-chain flows, liquidations, and 24/7 market structure.

## When to Use

- When building crypto strategy signal features
- When analyzing crypto market microstructure
- When implementing on-chain valuation models
- When constructing crypto-specific factor models

## Indicators

### 1. CVD (Cumulative Volume Delta)

```python
import pandas as pd
import numpy as np

def calculate_cvd(df: pd.DataFrame) -> pd.Series:
    """
    Cumulative Volume Delta from OHLCV data.
    Approximation: uses close position within bar to estimate buy/sell volume.

    Args:
        df: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns

    Returns:
        Series of cumulative volume delta
    """
    # Estimate buy/sell split using close position in range
    range_size = df['high'] - df['low']
    close_position = np.where(
        range_size > 0,
        (df['close'] - df['low']) / range_size,
        0.5  # Doji bars
    )
    buy_volume = df['volume'] * close_position
    sell_volume = df['volume'] * (1 - close_position)
    delta = buy_volume - sell_volume
    return delta.cumsum()


def cvd_divergence_signal(
    price: pd.Series,
    cvd: pd.Series,
    lookback: int = 20,
    threshold: float = 0.5
) -> pd.Series:
    """
    Detect CVD divergence from price.
    Bearish: price new high, CVD declining.
    Bullish: price new low, CVD rising.
    """
    price_pct = price.pct_change(lookback)
    cvd_pct = cvd.diff(lookback) / cvd.rolling(lookback).std()

    signals = pd.Series(0, index=price.index)
    signals[(price_pct > threshold) & (cvd_pct < -threshold)] = -1  # Bearish div
    signals[(price_pct < -threshold) & (cvd_pct > threshold)] = 1   # Bullish div
    return signals
```

### 2. Funding Rate Oscillator

```python
def funding_rate_oscillator(
    funding_rates: pd.Series,
    fast_period: int = 8,   # 8 x 8h = 64h
    slow_period: int = 42,  # 42 x 8h = 14 days
) -> pd.Series:
    """
    Mean-reversion oscillator on funding rates.
    Funding rates are collected every 8h (Binance/Bybit) or 1h (Hyperliquid).

    Returns:
        Oscillator: positive = funding above mean (short bias),
                    negative = funding below mean (long bias)
    """
    fast_ma = funding_rates.ewm(span=fast_period).mean()
    slow_ma = funding_rates.ewm(span=slow_period).mean()
    oscillator = fast_ma - slow_ma

    # Normalize to z-score
    z_score = (oscillator - oscillator.rolling(slow_period).mean()) / \
              oscillator.rolling(slow_period).std()
    return z_score


def funding_rate_signal(
    z_score: pd.Series,
    entry_threshold: float = 2.0,
    exit_threshold: float = 0.5
) -> pd.Series:
    """Convert funding oscillator to trading signal."""
    signals = pd.Series(0, index=z_score.index)
    signals[z_score > entry_threshold] = -1   # Fade extreme positive funding
    signals[z_score < -entry_threshold] = 1   # Fade extreme negative funding
    # Exit when mean-reverts
    signals[(z_score.abs() < exit_threshold) & (signals.shift(1) != 0)] = 0
    return signals.ffill().fillna(0)
```

### 3. Open Interest Divergence

```python
def oi_divergence(
    price: pd.Series,
    open_interest: pd.Series,
    lookback: int = 24  # hours
) -> pd.DataFrame:
    """
    Classify market regime by price vs OI relationship.

    Returns DataFrame with columns: regime, strength
    """
    price_change = price.pct_change(lookback)
    oi_change = open_interest.pct_change(lookback)

    regimes = pd.Series("neutral", index=price.index)
    regimes[(price_change > 0.01) & (oi_change > 0.02)] = "strong_trend_up"
    regimes[(price_change > 0.01) & (oi_change < -0.02)] = "short_squeeze"
    regimes[(price_change < -0.01) & (oi_change > 0.02)] = "new_shorts"
    regimes[(price_change < -0.01) & (oi_change < -0.02)] = "long_liquidation"

    strength = (price_change.abs() + oi_change.abs()) / 2

    return pd.DataFrame({
        "regime": regimes,
        "strength": strength,
        "price_chg": price_change,
        "oi_chg": oi_change
    })
```

### 4. SOPR (Spent Output Profit Ratio)

```python
def sopr_signal(
    sopr: pd.Series,
    smoothing: int = 7
) -> pd.Series:
    """
    SOPR = realized price / paid price for moved coins.
    SOPR > 1: coins moving at profit. SOPR < 1: at loss.

    Key levels:
    - SOPR < 0.95: capitulation (buy)
    - SOPR bounces off 1.0 from above: support in bull market
    - SOPR breaks below 1.0: bear market confirmation
    """
    smoothed = sopr.rolling(smoothing).mean()
    signals = pd.Series(0, index=sopr.index)
    signals[smoothed < 0.95] = 1   # Capitulation buy
    signals[smoothed > 1.05] = -1  # Euphoria sell
    return signals
```

### 5. MVRV Z-Score (Market Value to Realized Value)

```python
def mvrv_zscore(
    market_cap: pd.Series,
    realized_cap: pd.Series,
    lookback: int = 365
) -> pd.Series:
    """
    MVRV Z-Score: (Market Cap - Realized Cap) / std(Market Cap)

    Zones:
    - Z > 7: extreme overvaluation (top signal)
    - Z > 3: overvalued
    - Z < 0: undervalued (accumulation zone)
    - Z < -0.5: extreme undervaluation (bottom signal)
    """
    mvrv = (market_cap - realized_cap) / market_cap.rolling(lookback).std()
    return mvrv
```

### 6. Exchange Flow Indicator

```python
def exchange_netflow_signal(
    inflow: pd.Series,
    outflow: pd.Series,
    smoothing: int = 24
) -> pd.Series:
    """
    Net flow = inflow - outflow.
    Positive = coins entering exchange (sell pressure).
    Negative = coins leaving exchange (accumulation).

    Args:
        inflow: Hourly exchange inflow (BTC or USD)
        outflow: Hourly exchange outflow
        smoothing: Rolling average period (hours)
    """
    netflow = inflow - outflow
    smoothed = netflow.rolling(smoothing).mean()
    z_score = (smoothed - smoothed.rolling(smoothing * 7).mean()) / \
              smoothed.rolling(smoothing * 7).std()

    signals = pd.Series(0, index=netflow.index)
    signals[z_score > 2.0] = -1   # Heavy inflows = bearish
    signals[z_score < -2.0] = 1   # Heavy outflows = bullish
    return signals
```

### 7. Whale Alert Threshold

```python
def whale_alert_signal(
    transactions: pd.DataFrame,
    price: pd.Series,
    threshold_usd: float = 10_000_000
) -> pd.Series:
    """
    Detect whale movements from large on-chain transactions.

    Args:
        transactions: DataFrame with 'timestamp', 'amount_usd', 'from_type', 'to_type'
                     Types: 'exchange', 'wallet', 'unknown'
        price: Price series for context
        threshold_usd: Minimum transaction size
    """
    large_txs = transactions[transactions['amount_usd'] >= threshold_usd]

    signals = pd.Series(0, index=price.index)
    for _, tx in large_txs.iterrows():
        ts = tx['timestamp']
        if tx['to_type'] == 'exchange':
            signals.loc[ts] -= 1  # Whale depositing to exchange = sell
        elif tx['from_type'] == 'exchange':
            signals.loc[ts] += 1  # Whale withdrawing = accumulation

    return signals.rolling(24).sum()  # Aggregate over 24h
```

### 8. Stablecoin Supply Ratio (SSR)

```python
def stablecoin_supply_ratio(
    btc_market_cap: pd.Series,
    stablecoin_supply: pd.Series,
    lookback: int = 30
) -> pd.Series:
    """
    SSR = BTC Market Cap / Total Stablecoin Supply
    Low SSR = high buying power relative to BTC (bullish)
    High SSR = low buying power relative (bearish or already deployed)

    Returns z-score of SSR for signal generation.
    """
    ssr = btc_market_cap / stablecoin_supply
    z_score = (ssr - ssr.rolling(lookback).mean()) / ssr.rolling(lookback).std()
    return z_score
```

## Combining Indicators

```python
def crypto_composite_signal(
    cvd_signal: pd.Series,
    funding_signal: pd.Series,
    oi_regime: pd.Series,
    exchange_flow_signal: pd.Series,
    weights: dict = None
) -> pd.Series:
    """
    Weighted composite of crypto indicators.
    Default weights favor funding + exchange flow (higher signal-to-noise).
    """
    w = weights or {
        "cvd": 0.2,
        "funding": 0.3,
        "oi": 0.2,
        "flow": 0.3
    }
    composite = (
        w["cvd"] * cvd_signal +
        w["funding"] * funding_signal +
        w["oi"] * oi_regime +
        w["flow"] * exchange_flow_signal
    )
    return composite
```

## Common Pitfalls

1. **Funding rate frequency varies** — Binance/Bybit = 8h, Hyperliquid = 1h, dYdX = 1h
2. **CVD from OHLCV is approximate** — True CVD needs tick-level trade data
3. **On-chain metrics lag** — Block confirmation + indexing = 10min to 1h delay
4. **SOPR/MVRV only for BTC/ETH** — Not meaningful for low-history tokens
5. **Exchange flow accuracy** — Depends on correct address labeling (Nansen/Arkham)

## Related Skills

- `quant-crypto-research` — Where to find the data
- `quant-data-abstraction` — Unified data fetching
- `quant-order-flow-analysis` — Deeper orderflow patterns
