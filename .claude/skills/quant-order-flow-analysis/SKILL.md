---
name: quant-order-flow-analysis
description: "CVD analysis, large order detection, bid/ask imbalance, and book pressure metrics"
version: "1.0.0"
triggers:
  - "when analyzing order flow"
  - "when detecting large orders or icebergs"
  - "when calculating bid/ask imbalance"
  - "when building tape reading indicators"
---

# Quant Order Flow Analysis

## Purpose

Quantifies order flow patterns from trade data and orderbook snapshots. Order flow reveals the intentions of large participants that price alone cannot show. Adapted from institutional flow analysis for crypto's transparent orderbook data.

## When to Use

- When building flow-based entry/exit signals
- When detecting institutional activity (iceberg orders, large block trades)
- When measuring buying vs selling aggression
- When evaluating orderbook depth and resilience

## Core Metrics

### 1. CVD (Cumulative Volume Delta) — Detailed

```python
import pandas as pd
import numpy as np

def calculate_cvd_from_trades(trades: pd.DataFrame) -> pd.Series:
    """
    True CVD from individual trade data (tick-level).
    Each trade is classified as buy (taker buy) or sell (taker sell).

    Args:
        trades: DataFrame with columns ['timestamp', 'price', 'size', 'side']
                side: 'buy' = taker bought (lifted ask), 'sell' = taker sold (hit bid)
    """
    trades = trades.copy()
    trades['signed_volume'] = np.where(
        trades['side'] == 'buy',
        trades['size'],
        -trades['size']
    )
    return trades['signed_volume'].cumsum()


def calculate_cvd_from_ohlcv(df: pd.DataFrame) -> pd.Series:
    """
    Approximate CVD from OHLCV (when tick data unavailable).
    Uses close position within bar as buy/sell proxy.
    Less accurate but works with standard candle data.
    """
    bar_range = df['high'] - df['low']
    close_position = np.where(
        bar_range > 0,
        (df['close'] - df['low']) / bar_range,
        0.5
    )
    buy_vol = df['volume'] * close_position
    sell_vol = df['volume'] * (1 - close_position)
    delta = buy_vol - sell_vol
    return delta.cumsum()


def cvd_rate_of_change(cvd: pd.Series, period: int = 14) -> pd.Series:
    """CVD momentum — rate of change of volume delta."""
    return cvd.diff(period) / cvd.rolling(period).std()
```

### 2. Large Order Detection (Iceberg Inference)

```python
def detect_large_orders(
    trades: pd.DataFrame,
    size_threshold_pct: float = 95,
    time_window: str = "1min",
    cluster_threshold: int = 3
) -> pd.DataFrame:
    """
    Detect unusually large orders and potential icebergs.

    Iceberg detection: Multiple same-size fills at same price within time window
    suggests an iceberg (hidden) order being worked.

    Args:
        trades: Tick-level trade data
        size_threshold_pct: Percentile for "large" classification
        time_window: Window for clustering analysis
        cluster_threshold: Min fills to flag as potential iceberg
    """
    large_threshold = trades['size'].quantile(size_threshold_pct / 100)

    # Flag outright large orders
    trades['is_large'] = trades['size'] >= large_threshold

    # Detect iceberg patterns: same size, same price, rapid succession
    trades['rounded_size'] = trades['size'].round(2)
    trades['time_bucket'] = trades['timestamp'].dt.floor(time_window)

    icebergs = trades.groupby(
        ['time_bucket', 'rounded_size', 'side']
    ).agg(
        fill_count=('size', 'count'),
        total_volume=('size', 'sum'),
        avg_price=('price', 'mean')
    ).reset_index()

    icebergs = icebergs[icebergs['fill_count'] >= cluster_threshold]
    icebergs['is_iceberg'] = True

    return icebergs[['time_bucket', 'side', 'fill_count', 'total_volume', 'avg_price']]
```

### 3. Bid/Ask Imbalance

```python
def orderbook_imbalance(
    bids: list[list[float]],  # [[price, size], ...]
    asks: list[list[float]],
    levels: int = 5
) -> dict:
    """
    Calculate bid/ask imbalance from orderbook snapshot.

    Imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
    Range: -1 (all asks, bearish) to +1 (all bids, bullish)
    """
    bid_vol = sum(size for _, size in bids[:levels])
    ask_vol = sum(size for _, size in asks[:levels])
    total = bid_vol + ask_vol

    if total == 0:
        return {"imbalance": 0.0, "bid_vol": 0, "ask_vol": 0}

    imbalance = (bid_vol - ask_vol) / total

    return {
        "imbalance": round(imbalance, 4),
        "bid_vol": bid_vol,
        "ask_vol": ask_vol,
        "bid_depth_usd": sum(p * s for p, s in bids[:levels]),
        "ask_depth_usd": sum(p * s for p, s in asks[:levels])
    }


def rolling_imbalance(
    snapshots: list[dict],
    window: int = 20
) -> pd.Series:
    """
    Rolling average of orderbook imbalance over N snapshots.
    Smooths noise from individual snapshots.
    """
    imbalances = pd.Series([s["imbalance"] for s in snapshots])
    return imbalances.rolling(window).mean()
```

### 4. Tape Reading Quantified

```python
def aggressive_flow_ratio(
    trades: pd.DataFrame,
    window: str = "5min"
) -> pd.Series:
    """
    Ratio of aggressive (market order) volume to total volume.
    High aggression = conviction. Low aggression = hesitation.

    In crypto, all trades are aggressive (taker vs maker),
    so we measure buy aggression vs sell aggression.
    """
    grouped = trades.groupby(
        [pd.Grouper(key='timestamp', freq=window), 'side']
    )['size'].sum().unstack(fill_value=0)

    buy_aggression = grouped.get('buy', 0)
    sell_aggression = grouped.get('sell', 0)
    total = buy_aggression + sell_aggression

    ratio = np.where(total > 0, buy_aggression / total, 0.5)
    return pd.Series(ratio, index=grouped.index)


def trade_intensity(
    trades: pd.DataFrame,
    window: str = "1min"
) -> pd.Series:
    """
    Trades per time window — measures urgency.
    Spikes in intensity often precede or accompany moves.
    """
    return trades.groupby(
        pd.Grouper(key='timestamp', freq=window)
    ).size()
```

### 5. Book Pressure Metrics

```python
def book_pressure(
    bids: list[list[float]],
    asks: list[list[float]],
    mid_price: float,
    range_bps: float = 50  # Within 50bps of mid
) -> dict:
    """
    Measure resting order pressure within a price range.
    Useful for predicting short-term price direction.
    """
    range_price = mid_price * range_bps / 10000

    near_bids = sum(s for p, s in bids if mid_price - p <= range_price)
    near_asks = sum(s for p, s in asks if p - mid_price <= range_price)

    # Weighted pressure (closer orders matter more)
    weighted_bid = sum(
        s * (1 - (mid_price - p) / range_price)
        for p, s in bids
        if mid_price - p <= range_price
    )
    weighted_ask = sum(
        s * (1 - (p - mid_price) / range_price)
        for p, s in asks
        if p - mid_price <= range_price
    )

    total_weighted = weighted_bid + weighted_ask
    if total_weighted == 0:
        return {"pressure": 0.0, "bias": "neutral"}

    pressure = (weighted_bid - weighted_ask) / total_weighted

    return {
        "pressure": round(pressure, 4),
        "bias": "bullish" if pressure > 0.2 else "bearish" if pressure < -0.2 else "neutral",
        "near_bid_size": near_bids,
        "near_ask_size": near_asks,
        "weighted_bid": round(weighted_bid, 2),
        "weighted_ask": round(weighted_ask, 2)
    }
```

### 6. Composite Flow Signal

```python
def composite_flow_signal(
    cvd_change: float,
    imbalance: float,
    aggression_ratio: float,
    large_order_bias: float,
    weights: dict = None
) -> float:
    """
    Combine all flow metrics into single signal.

    Returns: -1.0 to +1.0 (bearish to bullish)
    """
    w = weights or {
        "cvd": 0.3,
        "imbalance": 0.25,
        "aggression": 0.25,
        "large_orders": 0.2
    }
    # Normalize each to [-1, 1]
    signal = (
        w["cvd"] * np.clip(cvd_change, -1, 1) +
        w["imbalance"] * np.clip(imbalance, -1, 1) +
        w["aggression"] * np.clip(2 * (aggression_ratio - 0.5), -1, 1) +
        w["large_orders"] * np.clip(large_order_bias, -1, 1)
    )
    return np.clip(signal, -1.0, 1.0)
```

## Common Pitfalls

1. **CVD from OHLCV is approximate** — True CVD needs tick-level data with side classification
2. **Orderbook spoofing** — Large resting orders may be pulled before fill (especially crypto)
3. **Latency in snapshots** — Orderbook changes sub-second; stale data misleads
4. **Exchange differences** — Binance aggregates differently than Bybit or Hyperliquid
5. **Volume units** — Check if volume is in base currency, quote currency, or contracts

## Related Skills

- `quant-crypto-indicators` — CVD and other crypto indicators
- `quant-market-making` — Flow analysis for MM positioning
- `quant-liquidation-analysis` — Liquidation as extreme flow events
