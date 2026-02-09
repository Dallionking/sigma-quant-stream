# What Fails - Documented Crypto Failures & Pitfalls

> Pattern file for crypto approaches that don't work, common mistakes, and pitfalls.
> Learn from failures to avoid repeating them.

---

## Format

Each entry should follow this structure:
```
### [TIMESTAMP] Entry Title
**Source**: [Session/File where discovered]
**Type**: Overfitting/DataLeak/Regime-Dependent/Curve-Fit/Exchange-Specific/Cost-Ignored/Other
**Market Type**: crypto-cex | crypto-dex
**Instruments**: BTCUSDT, ETHUSDT, etc.

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

## Crypto-Specific Anti-Patterns

### Overfitting Indicators
- Sharpe > 3.0 in crypto backtest → likely overfitted (even more so than traditional)
- Win rate > 75% in crypto → suspicious (crypto noise is higher)
- Perfect equity curve in crypto → impossible given volatility

### Crypto-Specific Gotchas
- Backtesting without funding rate costs
- Using spot data for perpetual futures strategy
- Ignoring liquidation risk in leveraged backtests
- Testing on BTC only and assuming it works on altcoins

---

## Entries

<!-- New entries are prepended below this line -->

### [2026-02-08] Pure Momentum in Sideways Crypto (Seed Entry)
**Source**: Historical analysis of trend-following in crypto ranges
**Type**: Regime-Dependent
**Market Type**: crypto-cex
**Instruments**: BTCUSDT, ETHUSDT

Trend-following / momentum strategies that work well in strong bull or bear markets get destroyed during sideways chop. Crypto spends ~60% of time in range-bound conditions. Momentum signals whipsaw constantly, generating fees and slippage with no edge.

**Symptoms**:
- Massive drawdowns during consolidation periods
- Win rate drops below 35% in ranges
- Equity curve has long flat/declining periods between brief wins
- Strategy only profitable during 2-3 month trend periods per year

**In-Sample**: Sharpe 2.10, WR 55% (tested during trending period)
**Out-of-Sample**: Sharpe 0.40, WR 38% (tested across full cycle)
**Decay**: 81%

**Lesson**: Always test across full market cycle including range-bound periods. Add regime filter (ADX, Bollinger Width) to disable momentum in chop. Consider mean-reversion during detected ranges.

---

### [2026-02-08] Over-Leveraged Mean Reversion (Seed Entry)
**Source**: Liquidation analysis of mean-reversion strategies
**Type**: Other (Liquidation Risk)
**Market Type**: crypto-cex
**Instruments**: BTCUSDT

Mean reversion strategies that use high leverage (>5x) to amplify small edge. Works beautifully in backtest but gets liquidated in live trading because crypto can move 10%+ against you before reverting. Backtest doesn't capture the liquidation event.

**Symptoms**:
- Beautiful backtest curve with high Sharpe
- Live trading shows sudden catastrophic losses
- Strategy gets liquidated during exactly the moves it's designed to profit from
- Recoverable drawdown in backtest = liquidation in live

**In-Sample**: Sharpe 2.80, WR 68%, Max DD 8%
**Out-of-Sample**: Liquidated at -100% on 3rd month
**Decay**: N/A (blown up)

**Lesson**: Never exceed 3x leverage for mean reversion in crypto. Use 2-3x margin buffer minimum. Model liquidation events in backtest. If strategy needs high leverage to be profitable, the edge is too small.

---

### [2026-02-08] Ignoring Funding Costs in Backtests (Seed Entry)
**Source**: Backtest vs live comparison analysis
**Type**: Cost-Ignored
**Market Type**: crypto-cex
**Instruments**: BTCUSDT, ETHUSDT

Backtesting perpetual futures strategies without modeling funding rate payments. During bull markets, funding averages 0.01-0.03% per 8h, which is 11-33% annualized drag on long positions. Strategy shows profit in backtest but slowly bleeds in live due to funding.

**Symptoms**:
- Backtest shows steady upward equity curve for long-biased strategy
- Live PnL drifts lower than backtest by ~1-3% per month
- Strategy is always long → always paying funding in bull market
- "Mystery" underperformance that compounds over time

**In-Sample**: Sharpe 1.80, WR 52%
**Out-of-Sample**: Sharpe 0.90, WR 52% (same signals, but funding eats profit)
**Decay**: 50% (hidden cost)

**Lesson**: Always include funding rate in crypto perpetual backtests. Model as: `funding_cost = position_size * funding_rate * ceil(hold_hours / 8)`. For strategies holding >8h, funding is material.

---

### [2026-02-08] Exchange-Specific Edge That Doesn't Generalize (Seed Entry)
**Source**: Cross-exchange validation failure
**Type**: Exchange-Specific
**Market Type**: crypto-cex
**Instruments**: BTCUSDT

Strategy optimized on Binance data that exploits a specific order book behavior or fee structure. When tested on Bybit or OKX, the edge disappears because the microstructure is different.

**Symptoms**:
- Excellent results on one exchange
- Fails completely on another exchange with same instrument
- Edge tied to specific API behavior, funding calc, or fee tier
- Strategy parameters are at edge of working range

**In-Sample** (Binance): Sharpe 1.60, WR 58%
**Out-of-Sample** (Bybit): Sharpe 0.30, WR 47%
**Decay**: 81% (cross-exchange)

**Lesson**: Always validate on at least 2 exchanges. If strategy only works on one exchange, the edge is likely exchange-specific noise (fee artifact, API timing, etc.). True edges should generalize across venues.

---

### [2026-02-08] Overfitting to BTC-Only Patterns (Seed Entry)
**Source**: Multi-asset backtesting failure
**Type**: Overfitting
**Market Type**: crypto-cex
**Instruments**: BTCUSDT (fails on altcoins)

Strategy developed and optimized exclusively on BTC data. BTC has unique properties (highest liquidity, most efficient, specific halving cycles). Altcoins have different dynamics: lower liquidity, higher correlation during crashes, different volume profiles, meme-driven moves.

**Symptoms**:
- Great backtest on BTC
- Complete failure on ETH, SOL, or any altcoin
- Strategy relies on BTC-specific patterns (halving, ETF flows)
- Parameters tuned to BTC volatility range

**In-Sample** (BTC): Sharpe 1.50, WR 55%
**Out-of-Sample** (ETH): Sharpe 0.60, WR 44%
**Out-of-Sample** (SOL): Sharpe 0.20, WR 40%
**Decay**: 60-87% (cross-asset)

**Lesson**: Test on at least BTC + ETH. If strategy only works on BTC, it's likely overfit to BTC-specific dynamics. For true alpha, parameters should produce positive returns on 2+ instruments (with appropriate adjustments for volatility/liquidity).

---

## Red Flags Checklist (Crypto-Specific)

Before accepting any crypto strategy, check:

- [ ] Sharpe > 3.0 → Almost certainly overfit (REJECT)
- [ ] Win rate > 75% → Curve fitting in crypto (REJECT)
- [ ] No losing months → Impossible in crypto (REJECT)
- [ ] < 100 trades → Insufficient sample (REJECT)
- [ ] OOS decay > 50% → Doesn't generalize (REJECT)
- [ ] Funding costs not modeled → Hidden drag (FIX REQUIRED)
- [ ] Only tested on one exchange → Exchange-specific (FIX REQUIRED)
- [ ] Only tested on BTC → May not generalize (FIX REQUIRED)
- [ ] Leverage > 5x → Liquidation risk (REVIEW)
- [ ] Hold time > 8h without funding model → Cost underestimate (FIX REQUIRED)

---

*Last Updated: 2026-02-08 (Seeded)*
*Next distillation will add actual failures*
