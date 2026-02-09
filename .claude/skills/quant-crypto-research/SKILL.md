---
name: quant-crypto-research
description: "Crypto-specific alpha research sources, edge types, and methodology"
version: "1.0.0"
triggers:
  - "when researching crypto trading strategies"
  - "when finding crypto alpha sources"
  - "when analyzing on-chain data"
  - "when evaluating crypto edge types"
---

# Quant Crypto Research

## Purpose

Provides structured methodology for finding tradeable edges in crypto markets. Crypto alpha differs fundamentally from futures — transparency of on-chain data, 24/7 markets, and exchange-specific microstructure create unique opportunities.

## When to Use

- Before developing any crypto strategy
- When searching for new crypto alpha sources
- When evaluating on-chain vs off-chain signals
- When building a crypto research pipeline

## Research Sources

### On-Chain Analytics

| Source | Data Type | Edge |
|--------|-----------|------|
| **CryptoQuant** | Exchange flows, miner flows, fund flows | Whale accumulation/distribution |
| **Glassnode** | SOPR, MVRV, NVT, entity metrics | Macro cycle positioning |
| **Dune Analytics** | Custom SQL on blockchain data | Protocol-specific flows |
| **DeFi Llama** | TVL, protocol revenue, yields | DeFi rotation signals |
| **Nansen** | Smart money wallet labeling | Follow institutional wallets |
| **Arkham** | Entity identification | Track known fund movements |

### Exchange-Specific Data

| Source | Data Type | Edge |
|--------|-----------|------|
| **Binance** | OI, funding, liquidations | Crowded trade detection |
| **Bybit** | Long/short ratio, OI | Retail positioning |
| **Hyperliquid** | On-chain orderbook, vault PnL | Transparent MM activity |
| **Coinglass** | Aggregated OI, funding, liquidations | Cross-exchange divergence |
| **Kaiko** | Institutional-grade tick data | Microstructure analysis |

### Social/Sentiment

| Source | Signal | Reliability |
|--------|--------|-------------|
| **Santiment** | Social volume, dev activity | Medium — lagging |
| **LunarCrush** | Galaxy Score, AltRank | Low — noisy |
| **Crypto Twitter** | Narrative shifts | High — leading but manual |
| **Telegram alpha groups** | Early intel | Varies — survivorship bias |

## Crypto-Specific Edge Types

### 1. Funding Rate Arbitrage
```python
# Edge: Funding rate mean-reverts — extreme rates predict reversal
# Capacity: High (delta-neutral)
# Sharpe expectation: 1.5-2.5 annualized
def funding_rate_signal(funding_rate: float, threshold: float = 0.03) -> int:
    """Extreme funding = crowded trade, fade it."""
    if funding_rate > threshold:   # Longs paying shorts heavily
        return -1  # Short bias
    elif funding_rate < -threshold:
        return 1   # Long bias
    return 0
```

### 2. Open Interest Divergence
```python
# Edge: Price up + OI down = short squeeze (weak move)
# Price up + OI up = new longs entering (strong move)
def oi_divergence_signal(
    price_change_pct: float,
    oi_change_pct: float
) -> str:
    if price_change_pct > 0 and oi_change_pct < -0.05:
        return "short_squeeze"  # Fading opportunity
    elif price_change_pct > 0 and oi_change_pct > 0.05:
        return "strong_trend"   # Continuation
    elif price_change_pct < 0 and oi_change_pct > 0.05:
        return "new_shorts"     # Bearish
    elif price_change_pct < 0 and oi_change_pct < -0.05:
        return "long_liquidation"  # Capitulation
    return "neutral"
```

### 3. Liquidation Cascade
```python
# Edge: Cascading liquidations overshoot fair value
# When liquidation volume > 3x normal, mean-reversion edge
def liquidation_cascade_signal(
    liquidation_volume_usd: float,
    avg_liquidation_volume: float,
    threshold_multiplier: float = 3.0
) -> int:
    ratio = liquidation_volume_usd / max(avg_liquidation_volume, 1)
    if ratio > threshold_multiplier:
        return 1  # Buy the cascade (mean-reversion)
    return 0
```

### 4. CVD (Cumulative Volume Delta)
```python
# Edge: Divergence between price and CVD signals exhaustion
# Price making new high but CVD flat/declining = bearish divergence
def cvd_divergence(
    price: pd.Series,
    cvd: pd.Series,
    lookback: int = 20
) -> int:
    price_trend = price.iloc[-1] > price.iloc[-lookback]
    cvd_trend = cvd.iloc[-1] > cvd.iloc[-lookback]
    if price_trend and not cvd_trend:
        return -1  # Bearish divergence
    elif not price_trend and cvd_trend:
        return 1   # Bullish divergence
    return 0
```

### 5. Exchange Flow (On-Chain)
```python
# Edge: Large exchange inflows = potential selling pressure
# Large outflows = accumulation (bullish)
def exchange_flow_signal(
    net_flow_btc: float,
    threshold_btc: float = 5000
) -> int:
    if net_flow_btc > threshold_btc:
        return -1  # Large inflows = sell pressure
    elif net_flow_btc < -threshold_btc:
        return 1   # Large outflows = accumulation
    return 0
```

## Research Practitioners

| Person | Methodology | Key Insight |
|--------|-------------|-------------|
| **MoonDev** | Automated alpha pipelines, Hyperliquid focus | "Automate the boring, trade the interesting" |
| **CryptoCred** | Technical + orderflow on crypto | Market structure + S/R levels |
| **SmartContracter** | Wave theory + crypto | Narrative cycle timing |
| **Cobie** | Macro narrative, contrarian | "Fade the consensus" |
| **GCR** | Macro + positioning | Crowded trade identification |
| **Hsaka** | Orderflow + OI analysis | Liquidation level mapping |
| **Jump Crypto** | Systematic MM + arb | Infrastructure edge (latency) |
| **Wintermute** | Dynamic spread, cross-venue | Inventory management at scale |

## Research Pipeline Pattern

```python
CRYPTO_RESEARCH_PIPELINE = {
    "1_scan": {
        "sources": ["coinglass", "cryptoquant", "dune"],
        "signals": ["funding_extremes", "oi_divergence", "whale_flows"],
        "frequency": "4h"
    },
    "2_filter": {
        "min_volume_24h": 50_000_000,  # USD
        "min_oi": 100_000_000,
        "exchanges": ["binance", "bybit", "hyperliquid"]
    },
    "3_validate": {
        "backtest_bars": 2000,
        "min_trades": 100,
        "cost_model": "percentage",  # Not per-contract
        "oos_split": 0.3
    },
    "4_deploy": {
        "paper_first": True,
        "paper_period_days": 14,
        "max_position_usd": 10000
    }
}
```

## Common Pitfalls

1. **Survivorship bias in altcoins** — Many tokens delist; backtest only active coins
2. **Exchange manipulation** — Wash trading inflates volume on some exchanges
3. **Funding rate changes** — Exchanges modify calculation (Binance changed to 4h)
4. **On-chain latency** — Block confirmation delays vs CEX instant execution
5. **Regime dependence** — Crypto cycles (bull/bear) completely change correlations

## Related Skills

- `quant-crypto-indicators` — Implementation of crypto-native indicators
- `quant-data-abstraction` — Unified data layer for multi-provider access
- `quant-funding-rate-strategies` — Funding rate strategy specifics
