---
name: quant-liquidation-analysis
description: "Liquidation cascade modeling, heatmap construction, and fat-tail analysis with EVT"
version: "1.0.0"
triggers:
  - "when modeling liquidation cascades"
  - "when building liquidation heatmaps"
  - "when analyzing fat-tail risk in crypto"
  - "when detecting cascade triggers"
---

# Quant Liquidation Analysis

## Purpose

Models liquidation cascades in crypto perpetual markets. Cascading liquidations create predictable overshoots that mean-revert, offering trading opportunities. Understanding liquidation mechanics is critical for both risk management and alpha generation.

## When to Use

- When building cascade-based mean-reversion strategies
- When constructing liquidation heatmaps for S/R levels
- When modeling tail risk for position sizing
- When setting stop-losses aware of liquidation clusters

## Core Concepts

### How Liquidation Cascades Work

```
Price drops → Overleveraged longs hit maintenance margin
  → Exchange liquidation engine market-sells
    → Selling pressure drives price lower
      → More longs hit liquidation
        → Waterfall effect until exhaustion
```

### Liquidation Price Calculation

```python
def liquidation_price(
    entry_price: float,
    leverage: int,
    side: str,  # "long" or "short"
    maintenance_margin_pct: float = 0.5  # 0.5%
) -> float:
    """
    Calculate liquidation price for a position.

    For longs: liq_price = entry * (1 - 1/leverage + maintenance_margin)
    For shorts: liq_price = entry * (1 + 1/leverage - maintenance_margin)
    """
    mm = maintenance_margin_pct / 100
    if side == "long":
        return entry_price * (1 - 1/leverage + mm)
    else:
        return entry_price * (1 + 1/leverage - mm)
```

### Liquidation Heatmap Construction

```python
import numpy as np
import pandas as pd

def build_liquidation_heatmap(
    open_interest_by_price: pd.DataFrame,
    leverage_distribution: dict[int, float],
    current_price: float,
    price_range_pct: float = 10.0,
    price_steps: int = 100
) -> pd.DataFrame:
    """
    Build a liquidation heatmap showing estimated liquidation volume
    at each price level.

    Args:
        open_interest_by_price: DataFrame with 'price', 'long_oi', 'short_oi'
        leverage_distribution: {leverage: fraction} e.g., {5: 0.3, 10: 0.4, 25: 0.2, 50: 0.1}
        current_price: Current market price
        price_range_pct: % range above/below current price
        price_steps: Number of price levels to calculate

    Returns:
        DataFrame with columns: price, long_liqs_usd, short_liqs_usd
    """
    price_min = current_price * (1 - price_range_pct / 100)
    price_max = current_price * (1 + price_range_pct / 100)
    price_levels = np.linspace(price_min, price_max, price_steps)

    long_liqs = np.zeros(price_steps)
    short_liqs = np.zeros(price_steps)

    for _, row in open_interest_by_price.iterrows():
        entry_price = row['price']
        long_oi = row['long_oi']
        short_oi = row['short_oi']

        for leverage, fraction in leverage_distribution.items():
            # Long liquidation prices (below entry)
            liq_price_long = liquidation_price(entry_price, leverage, "long")
            if price_min <= liq_price_long <= price_max:
                idx = int((liq_price_long - price_min) / (price_max - price_min) * (price_steps - 1))
                long_liqs[idx] += long_oi * fraction

            # Short liquidation prices (above entry)
            liq_price_short = liquidation_price(entry_price, leverage, "short")
            if price_min <= liq_price_short <= price_max:
                idx = int((liq_price_short - price_min) / (price_max - price_min) * (price_steps - 1))
                short_liqs[idx] += short_oi * fraction

    return pd.DataFrame({
        "price": price_levels,
        "long_liqs_usd": long_liqs,
        "short_liqs_usd": short_liqs,
        "total_liqs_usd": long_liqs + short_liqs
    })
```

### Cascade Trigger Detection

```python
def detect_cascade_trigger(
    price: pd.Series,
    liquidation_volume: pd.Series,
    oi_change: pd.Series,
    lookback: int = 24
) -> pd.DataFrame:
    """
    Detect the start of a liquidation cascade in real-time.

    Cascade signals:
    1. Liquidation volume > 3x rolling average
    2. OI dropping rapidly (positions being force-closed)
    3. Price acceleration (momentum increasing)

    Args:
        price: Hourly close prices
        liquidation_volume: Hourly liquidation volume (USD)
        oi_change: Hourly change in open interest
    """
    avg_liq = liquidation_volume.rolling(lookback).mean()
    liq_ratio = liquidation_volume / avg_liq.clip(lower=1)

    price_accel = price.pct_change().diff()  # 2nd derivative
    oi_decline = oi_change.rolling(3).sum()  # 3-bar cumulative OI change

    cascade_score = pd.Series(0.0, index=price.index)

    # Weight factors
    cascade_score += (liq_ratio > 3).astype(float) * 0.4
    cascade_score += (oi_decline < -0.03).astype(float) * 0.3
    cascade_score += (price_accel.abs() > price_accel.rolling(lookback).std() * 2).astype(float) * 0.3

    return pd.DataFrame({
        "cascade_score": cascade_score,
        "liq_ratio": liq_ratio,
        "oi_decline": oi_decline,
        "price_accel": price_accel,
        "is_cascade": cascade_score > 0.6
    })
```

### Waterfall Effect Estimation

```python
def estimate_waterfall_depth(
    heatmap: pd.DataFrame,
    current_price: float,
    direction: str,  # "down" (long liquidations) or "up" (short liquidations)
    trigger_volume_usd: float = 10_000_000
) -> dict:
    """
    Estimate how far price could move in a cascade.

    Walks through the heatmap, accumulating liquidation volume.
    Each liquidation adds selling/buying pressure that can trigger the next level.
    """
    if direction == "down":
        levels = heatmap[heatmap['price'] < current_price].sort_values('price', ascending=False)
        liq_col = 'long_liqs_usd'
    else:
        levels = heatmap[heatmap['price'] > current_price].sort_values('price', ascending=True)
        liq_col = 'short_liqs_usd'

    cumulative_volume = 0
    cascade_end_price = current_price
    levels_triggered = 0

    for _, level in levels.iterrows():
        level_liq = level[liq_col]
        if level_liq < trigger_volume_usd * 0.1:
            continue  # Skip negligible levels

        cumulative_volume += level_liq
        cascade_end_price = level['price']
        levels_triggered += 1

        # Cascade weakens as it moves further from trigger
        trigger_volume_usd *= 0.7  # Each level needs less volume to continue

        if level_liq < trigger_volume_usd * 0.05:
            break  # Cascade runs out of fuel

    price_impact_pct = abs(cascade_end_price - current_price) / current_price * 100

    return {
        "cascade_end_price": round(cascade_end_price, 2),
        "price_impact_pct": round(price_impact_pct, 2),
        "cumulative_liq_volume": round(cumulative_volume, 0),
        "levels_triggered": levels_triggered,
        "direction": direction
    }
```

### EVT (Extreme Value Theory) for Fat Tails

```python
from scipy import stats

def fit_evt_gpd(
    returns: pd.Series,
    threshold_pct: float = 95
) -> dict:
    """
    Fit Generalized Pareto Distribution to tail returns.
    EVT is the correct framework for modeling crypto tail risk
    (normal distribution severely underestimates crypto tails).

    Args:
        returns: Log returns series
        threshold_pct: Percentile threshold for tail definition
    """
    threshold = np.percentile(returns, 100 - threshold_pct)
    exceedances = returns[returns < -abs(threshold)] - (-abs(threshold))
    exceedances = -exceedances  # Make positive for GPD fitting

    if len(exceedances) < 20:
        return {"error": "Insufficient tail observations", "count": len(exceedances)}

    # Fit GPD
    shape, loc, scale = stats.genpareto.fit(exceedances)

    # VaR and CVaR at various confidence levels
    results = {}
    for confidence in [0.95, 0.99, 0.999]:
        p = 1 - confidence
        n_exceedances = len(exceedances)
        n_total = len(returns)
        exceedance_rate = n_exceedances / n_total

        var = abs(threshold) + (scale / shape) * ((p / exceedance_rate) ** (-shape) - 1)
        cvar = var / (1 - shape) + (scale - shape * abs(threshold)) / (1 - shape)

        results[f"var_{int(confidence*100)}"] = round(var * 100, 2)
        results[f"cvar_{int(confidence*100)}"] = round(cvar * 100, 2)

    results["shape_parameter"] = round(shape, 4)
    results["tail_observations"] = len(exceedances)
    results["is_heavy_tail"] = shape > 0  # shape > 0 = heavy tail

    return results
```

## Data Sources

| Source | Data | Access |
|--------|------|--------|
| **Coinglass** | Aggregated liquidations, OI | API (free tier available) |
| **CryptoQuant** | Exchange-level liquidations | API (paid) |
| **Binance** | Real-time liquidation stream | WebSocket (free) |
| **Bybit** | Liquidation data | REST + WebSocket |
| **Hyperliquid** | On-chain liquidations | `info.user_fills()` |

## Common Pitfalls

1. **Leverage distribution is estimated** — No exchange publishes exact leverage per position
2. **Insurance fund absorbs some cascades** — Binance/Bybit insurance funds dampen cascades
3. **ADL replaces cascading on some exchanges** — Auto-deleverage profitable positions instead
4. **EVT requires sufficient tail data** — Need 20+ tail events minimum; crypto has them
5. **Heatmap is a point-in-time estimate** — OI shifts constantly; heatmap stales quickly

## Related Skills

- `quant-exchange-compliance` — Liquidation buffer requirements
- `quant-crypto-indicators` — OI divergence and funding rate indicators
- `quant-funding-rate-strategies` — Strategies that benefit from cascades
