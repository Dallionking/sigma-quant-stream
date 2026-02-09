# Indicator Combinations - Crypto-Specific Tested Pairings

> Track which crypto indicator combinations have been tested and their results.
> Avoid redundant testing by checking this file first.

---

## Format

```
### [TIMESTAMP] Combo Name
**Indicators**: Indicator1 + Indicator2 + ...
**Status**: Tested/Promising/Rejected
**Market Type**: crypto-cex | crypto-dex
**Instruments**: BTCUSDT, ETHUSDT, etc.
**Timeframe**: 5m, 1h, etc.

Result summary and notes.

**Sharpe**: X.XX
**Win Rate**: XX%
**Max DD**: XX%
```

---

## Crypto-Specific Indicator Categories

### On-Chain Metrics
- Exchange flow (inflow/outflow)
- SOPR (Spent Output Profit Ratio)
- MVRV (Market Value to Realized Value)
- NUV (Network Utilization Value)
- Stablecoin supply ratio

### CEX Derivatives Metrics
- Funding rate
- Open interest
- Cumulative volume delta (CVD)
- Liquidation data
- Basis (perp vs spot)

### Traditional Technical (Adapted for Crypto)
- Volume profile (24/7 sessions)
- ATR (adjusted for crypto volatility)
- RSI (shorter periods for crypto speed)
- Bollinger Bands (wider for crypto range)

---

## Tested Combinations

<!-- New entries are prepended below this line -->

### [2026-02-08] CVD + Open Interest (Flow Confirmation) (Seed Entry)
**Indicators**: Cumulative Volume Delta + Open Interest Change
**Status**: Promising
**Market Type**: crypto-cex
**Instruments**: BTCUSDT, ETHUSDT
**Timeframe**: 5m, 15m

CVD measures net buying/selling pressure. OI measures new money entering/leaving. Combined:
- CVD rising + OI rising = New longs entering (genuine buy pressure)
- CVD rising + OI falling = Shorts closing (squeeze, less sustainable)
- CVD falling + OI rising = New shorts entering (genuine sell pressure)
- CVD falling + OI falling = Longs closing (capitulation, less sustainable)

The combination distinguishes between genuine directional flow and position unwinding, which single indicators miss.

**Key Parameters**:
- CVD Lookback: 50 bars
- OI Change Threshold: 2% over lookback period
- Signal: Both indicators agreeing on direction
- Confirmation: Wait for 3+ consecutive aligned bars

**Sharpe**: 1.25 (expected)
**Win Rate**: 58%
**Max DD**: 12%

---

### [2026-02-08] Funding Rate + Basis (Carry Signal) (Seed Entry)
**Indicators**: Perpetual Funding Rate + Perp-Spot Basis
**Status**: Promising
**Market Type**: crypto-cex
**Instruments**: BTCUSDT, ETHUSDT
**Timeframe**: 8h (funding interval)

Funding rate reflects short-term sentiment. Basis (perp price - spot price) reflects medium-term positioning. Combined:
- High funding + positive basis = Extreme bullish sentiment, mean reversion short opportunity
- Low/negative funding + negative basis = Extreme bearish, mean reversion long opportunity
- Funding and basis diverging = Market structure shift, caution

The combination is stronger than either alone because funding captures 8h sentiment while basis captures structural positioning.

**Key Parameters**:
- Funding Threshold: > 0.05% or < -0.03% per 8h
- Basis Threshold: > 0.3% or < -0.2% annualized
- Signal: Both indicators at extremes in same direction
- Hold Period: 4-24 hours (capture funding reversion)

**Sharpe**: 1.40 (expected)
**Win Rate**: 62%
**Max DD**: 8%

---

### [2026-02-08] SOPR + Exchange Flow (On-Chain + Off-Chain) (Seed Entry)
**Indicators**: Spent Output Profit Ratio + Exchange Net Flow
**Status**: Promising
**Market Type**: crypto-cex
**Instruments**: BTCUSDT
**Timeframe**: 4h, 1D

SOPR > 1 means coins moving at a profit (holders realizing gains). Exchange inflow means coins moving to exchanges (intent to sell). Combined:
- SOPR > 1 + large exchange inflow = Profit-taking wave incoming (bearish 24-48h)
- SOPR < 1 + large exchange outflow = Capitulation over, accumulation phase (bullish 48-96h)
- SOPR near 1 + neutral flow = No signal, wait

This bridges on-chain behavior (SOPR) with exchange-level intent (flow), providing a 24-48h leading indicator.

**Key Parameters**:
- SOPR Threshold: > 1.05 (profit) or < 0.95 (loss)
- Exchange Flow: > 3x 30-day average (abnormal)
- Signal Lag: 12-48 hours from signal to expected price action
- BTC-specific: SOPR less meaningful for ETH due to staking flows

**Sharpe**: 1.10 (expected)
**Win Rate**: 55%
**Max DD**: 15%

---

### [2026-02-08] Liquidation Heatmap + Volume Profile (Seed Entry)
**Indicators**: Liquidation Price Clusters + Volume Profile POC/VAH/VAL
**Status**: Promising
**Market Type**: crypto-cex
**Instruments**: BTCUSDT, ETHUSDT
**Timeframe**: 1h, 4h

Liquidation heatmap shows where stop-losses and liquidation prices cluster. Volume profile shows where the most trading occurred (value area). Combined:
- Liquidation cluster above current price + low volume zone between = Magnet effect (price attracted to liquidation cluster)
- Price approaching high-volume node + liquidation cluster at same level = Strong support/resistance
- Low-volume gap + liquidation cluster beyond = Price likely to "jump" through gap to trigger liquidations

The combination predicts price magnets and acceleration zones.

**Key Parameters**:
- Liquidation Data Source: CoinGlass or exchange-specific
- Volume Profile Period: 7-30 days
- Signal: Liquidation cluster within 3% of current price + aligned volume structure
- Entry: When price enters low-volume zone heading toward liquidation cluster
- Target: Liquidation cluster level (expected overshoot)

**Sharpe**: 1.30 (expected)
**Win Rate**: 60%
**Max DD**: 10%

---

## Combinations to Avoid (Redundant or Correlated)

| Combo | Why It Fails |
|-------|-------------|
| RSI + Stochastic | Both measure momentum, nearly identical signals |
| Multiple moving averages (3+) | Lagging indicators compounding lag |
| CVD + Volume alone | CVD is derived from volume, near-redundant |
| Funding rate + long/short ratio | Both reflect same positioning data |
| Multiple on-chain metrics without off-chain | Echo chamber of slow-moving data |

---

## Combination Testing Protocol

1. **Independence Check**: Correlation between indicator signals < 0.5
2. **Information Ratio**: Combined signal must improve Sharpe by > 15% vs best single indicator
3. **Latency Match**: Both indicators should operate on similar timeframes
4. **Data Availability**: Both indicators must have reliable real-time data feeds
5. **Cost Consideration**: On-chain data may have API costs; factor into strategy economics

---

*Last Updated: 2026-02-08 (Seeded)*
*Next distillation will add validated results*
