# What Works - Validated Trading Approaches

> Pattern file for successful strategies, indicators, and techniques.
> Updated automatically by @sigma-distiller after each session.

---

## Format

Each entry MUST include the `market_type` field. Existing entries without it are assumed `market_type: futures`.

```
### [TIMESTAMP] Entry Title
**Source**: [Session/File where discovered]
**Confidence**: High/Medium/Low
**Market Type**: futures | crypto_cex | crypto_dex
**Instruments**: ES, NQ, YM, GC, BTC-PERP, ETH-PERP, etc.
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

### [2026-01-26] RSI Divergence Mean Reversion (Seed Entry)
**Source**: De Prado 'Advances in Financial ML' + Wilder
**Confidence**: Medium
**Market Type**: futures
**Instruments**: ES, NQ
**Timeframes**: 5m, 15m

Bullish divergence (price makes lower low while RSI makes higher low) predicts short-term reversal. Works best during regular trading hours when momentum exhaustion is genuine, not gap-driven.

**Key Parameters**:
- RSI Period: 14 (12-21 range)
- Divergence Lookback: 5-10 bars
- Confirmation: Close above EMA(20)
- Stop: Below recent swing low

**Evidence**: seed/hypotheses/hyp-seed-001-rsi-divergence.json
**Sharpe OOS**: 1.35 (expected)
**OOS Decay**: ~20%

---

### [2026-01-26] VWAP Mean Reversion (Seed Entry)
**Source**: Almgren & Chriss + Market Microstructure
**Confidence**: High
**Market Type**: futures
**Instruments**: ES, NQ
**Timeframes**: 5m, 15m

Price tends to revert to VWAP after extreme deviations (>2 standard deviations). Works best during low-volume periods when institutions aren't actively pushing price.

**Key Parameters**:
- Deviation Threshold: 2.0 std dev (1.5-2.5 range)
- Volume Filter: Below 50th percentile
- Hold Period: 5-20 bars
- Exit: Return to VWAP or time stop

**Evidence**: seed/hypotheses/hyp-seed-004-vwap-reversion.json
**Sharpe OOS**: 1.50 (expected)
**OOS Decay**: ~15%

---

### [2026-01-26] Opening Range Breakout (Seed Entry)
**Source**: Toby Crabel + Linda Raschke
**Confidence**: Medium
**Market Type**: futures
**Instruments**: ES, NQ, YM
**Timeframes**: 5m, 15m

Breakout of first 15-30 minute range predicts intraday trend. Best on trending days (check for gap and pre-market momentum alignment).

**Key Parameters**:
- Range Period: 30 minutes (15-60 range)
- Breakout Filter: 0.5 ATR beyond range
- Stop: Range midpoint or opposite side
- Target: 1.5-2x range height

**Evidence**: seed/hypotheses/hyp-seed-005-opening-range-breakout.json
**Sharpe OOS**: 1.20 (expected)
**OOS Decay**: ~25%

---

## Anti-Patterns to Remember

- Don't use RSI divergence during gap opens (different mechanics)
- VWAP reversion fails in strong trend days (check ADX)
- ORB has lower win rate on Monday/Friday
- All mean reversion strategies need volatility filter

---

*Last Updated: 2026-01-26 (Seeded)*
*Next distillation will add validated entries*
