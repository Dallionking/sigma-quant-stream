# What Fails - Documented Failures & Pitfalls

> Pattern file for approaches that don't work, common mistakes, and pitfalls.
> Learn from failures to avoid repeating them.

---

## Format

Each entry MUST include the `market_type` field. Existing entries without it are assumed `market_type: futures`.

```
### [TIMESTAMP] Entry Title
**Source**: [Session/File where discovered]
**Type**: Overfitting/DataLeak/Regime-Dependent/Curve-Fit/Other
**Market Type**: futures | crypto_cex | crypto_dex
**Instruments**: ES, NQ, YM, GC, BTC-PERP, ETH-PERP, etc.

Why it failed and what to avoid.

**Symptoms**:
- Symptom 1
- Symptom 2

**In-Sample**: Sharpe X.XX, WR XX%
**Out-of-Sample**: Sharpe X.XX, WR XX%
**Decay**: XX%

**Lesson**: What to do instead
```

---

## Anti-Patterns

### Overfitting Indicators
- Sharpe ratio > 3.0 in backtest → likely overfitted
- Win rate > 80% → suspicious, check for data leakage
- Perfect equity curve → too good to be true

### Data Leakage Signs
- Using future data in calculations
- Look-ahead bias in indicator logic
- Train/test data contamination

---

## Entries

<!-- New entries are prepended below this line -->

### [2026-01-26] Fine-Grid RSI Optimization (Seed Entry)
**Source**: Documentation (seed entry to illustrate failure pattern)
**Type**: Overfitting
**Market Type**: futures
**Instruments**: ES

Tested RSI periods with too-fine grid [10, 11, 12, 13, 14, 15, 16]. Found "best" period of 13 which is arbitrary and not economically meaningful.

**Symptoms**:
- 7 parameter values tested in narrow range
- Best parameter at non-standard value
- Massive OOS decay

**In-Sample**: Sharpe 3.80, WR 72%
**Out-of-Sample**: Sharpe 1.10, WR 51%
**Decay**: 71%

**Lesson**: Use coarse grid only [7, 10, 14, 21, 28]. Fine grids guarantee overfitting.

---

### [2026-01-26] Perfect Equity Curve Momentum (Seed Entry)
**Source**: Documentation (seed entry to illustrate failure pattern)
**Type**: Curve Fitting
**Market Type**: futures
**Instruments**: NQ

Strategy showed no losing months in 2-year backtest with 84% win rate. Only 45 trades total - insufficient sample masked curve fitting.

**Symptoms**:
- No losing months in 2-year backtest
- Win rate: 84%
- Profit factor: 4.2
- Only 45 trades total (< 100 minimum)

**In-Sample**: Sharpe 4.20, WR 84%
**Out-of-Sample**: Sharpe 0.45, WR 42%
**Decay**: 89%

**Lesson**: Any strategy with WR > 80% or no losing months is curve-fit. Reject immediately. Require 100+ trades minimum.

---

### [2026-01-26] Future-Peeking ATR (Seed Entry)
**Source**: Documentation (seed entry to illustrate failure pattern)
**Type**: Data Leakage
**Market Type**: futures
**Instruments**: ES

ATR was calculated including current bar's high/low, causing look-ahead bias. Entries were impossibly accurate in backtest.

**Symptoms**:
- Entries at perfect reversal points
- Real-time results completely different
- ATR calculated with current bar data

**In-Sample**: Sharpe 2.50, WR 68%
**Out-of-Sample**: Sharpe 0.20, WR 48%
**Decay**: 92%

**Lesson**: Always verify indicators use only past data. Shift calculations by 1 bar if uncertain. Test with live paper trading before trusting backtest.

---

## Red Flags Checklist

Before accepting any strategy, check these warning signs:

- [ ] Sharpe > 3.0 → Almost certainly overfit (REJECT)
- [ ] Win rate > 80% → Curve fitting (REJECT)
- [ ] No losing months → Impossible (REJECT)
- [ ] < 100 trades → Insufficient sample (REJECT)
- [ ] OOS decay > 50% → Doesn't generalize (REJECT)
- [ ] Parameter at edge of range → Likely overfit to data quirk
- [ ] Works only on one symbol → Lacks robustness
- [ ] Requires precise entry timing → Unrealistic execution

---

*Last Updated: 2026-01-26 (Seeded)*
*Next distillation will add actual failures*
