# What Works - Validated Crypto Trading Approaches

> Pattern file for successful crypto strategies, indicators, and techniques.
> Updated automatically by @sigma-distiller after each session.

---

## Format

Each entry should follow this structure:
```
### [TIMESTAMP] Entry Title
**Source**: [Session/File where discovered]
**Confidence**: High/Medium/Low
**Market Type**: crypto-cex | crypto-dex
**Instruments**: BTCUSDT, ETHUSDT, etc.
**Timeframes**: 1m, 5m, 15m, 1H, etc.

Description of what works and why.

**Key Parameters**:
- param1: value
- param2: value

**Evidence**: [Link to backtest or reference]
**Sharpe OOS**: X.XX
**OOS Decay**: XX%
```

---

## Entries

<!-- New entries are prepended below this line -->

### [2026-02-08] Funding Rate Mean Reversion (Seed Entry)
**Source**: CryptoQuant research + historical Binance funding data
**Confidence**: High
**Market Type**: crypto-cex
**Instruments**: BTCUSDT, ETHUSDT
**Timeframes**: 1h, 4h

When perpetual funding rate exceeds 0.05% per 8h interval (annualized ~68%), short-term mean reversion occurs as overleveraged longs close positions to avoid funding payments. Works best during range-bound markets when funding spikes from brief euphoria rather than genuine trend.

**Key Parameters**:
- Funding Threshold: 0.05% per 8h (2x 30-day average)
- Entry Delay: 1-2 hours after extreme reading
- Hold Period: 4-24 hours
- Stop: 2x ATR from entry
- Annualized Carry: 15-40% (delta-neutral variant)

**Evidence**: seed/hypotheses/crypto/funding-rate-mean-reversion.json
**Sharpe OOS**: 1.20 (expected)
**OOS Decay**: ~20%

---

### [2026-02-08] OI Divergence Reversal (Seed Entry)
**Source**: Coinalyze OI data + exchange liquidation logs
**Confidence**: Medium
**Market Type**: crypto-cex
**Instruments**: BTCUSDT, ETHUSDT
**Timeframes**: 1h, 4h

When Open Interest drops >10% while price holds within 2%, weak hands have been flushed — remaining positions are stronger. This sets up a reversal in the direction of the price hold. Effectively a short squeeze / long squeeze detection mechanism.

**Key Parameters**:
- OI Drop Threshold: 10% over 4-8 hours
- Price Hold Range: Within 2% of pre-drop level
- Entry: After OI stabilizes (stops declining)
- Target: Previous OI-weighted VWAP
- Stop: Below divergence low/high

**Evidence**: seed/hypotheses/crypto/oi-divergence.json
**Sharpe OOS**: 1.30 (expected)
**OOS Decay**: ~25%

---

### [2026-02-08] CVD-Price Divergence (Seed Entry)
**Source**: Market microstructure research + order flow analysis
**Confidence**: Medium
**Market Type**: crypto-cex
**Instruments**: BTCUSDT, ETHUSDT
**Timeframes**: 5m, 15m

Cumulative Volume Delta (CVD) rising while price remains flat indicates stealth accumulation — buyers are absorbing sell pressure without moving price. When selling pressure exhausts, price catches up to CVD direction. Inverse applies for distribution.

**Key Parameters**:
- CVD Lookback: 50-100 bars
- Divergence Threshold: CVD new high while price flat (within 0.5%)
- Duration: Divergence persists for 2+ hours
- Confirmation: Volume spike in CVD direction
- Stop: Below accumulation range

**Evidence**: seed/hypotheses/crypto/cvd-price-divergence.json
**Sharpe OOS**: 1.15 (expected)
**OOS Decay**: ~25%

---

### [2026-02-08] Liquidation Cascade Bounce (Seed Entry)
**Source**: CoinGlass liquidation data + historical cascade analysis
**Confidence**: High
**Market Type**: crypto-cex
**Instruments**: BTCUSDT, ETHUSDT
**Timeframes**: 5m, 15m

After >$100M in liquidations within 1 hour, prices typically overshoot fair value due to forced market orders. Mean reversion occurs within 4 hours as arbitrageurs and value buyers step in. The larger the cascade, the stronger the bounce (up to a point — >$500M may indicate regime change).

**Key Parameters**:
- Liquidation Threshold: $100M in 1 hour
- Entry Delay: 15-30 minutes after peak liquidation rate
- Direction: Fade the cascade (buy after long liquidations, sell after short liquidations)
- Target: 50% retracement of cascade move
- Stop: Beyond cascade extreme
- Max Hold: 4 hours

**Evidence**: seed/hypotheses/crypto/liquidation-cascade.json
**Sharpe OOS**: 1.40 (expected)
**OOS Decay**: ~20%

---

### [2026-02-08] On-Chain Exchange Flow (Seed Entry)
**Source**: Glassnode exchange flow metrics + CryptoQuant
**Confidence**: Medium
**Market Type**: crypto-cex
**Instruments**: BTCUSDT
**Timeframes**: 4h, 1D

Large exchange inflows (>1000 BTC in 24h, or >3x 30-day average) predict selling pressure within 24-48 hours. Conversely, sustained outflows indicate accumulation. Works as a 24-48h leading indicator for directional bias.

**Key Parameters**:
- Inflow Threshold: >1000 BTC/day or >3x 30-day avg
- Outflow Threshold: >500 BTC/day sustained for 3+ days
- Signal Lag: 12-48 hours from flow to price action
- Confirmation: Combine with SOPR and MVRV for higher confidence
- Stop: Fixed percentage (3-5%)

**Evidence**: seed/hypotheses/crypto/onchain-exchange-flow.json
**Sharpe OOS**: 1.10 (expected)
**OOS Decay**: ~30%

---

## Anti-Patterns to Remember

- Funding rate strategies fail during strong trends (funding stays extreme for days)
- OI divergence signals are noisy during low-volume weekends
- CVD divergence requires sufficient volume — thin books give false signals
- Liquidation cascade bounces fail when cascade is caused by fundamental news
- On-chain flow is BTC-specific — ETH exchange flow less predictive due to staking

---

*Last Updated: 2026-02-08 (Seeded)*
*Next distillation will add validated entries*
