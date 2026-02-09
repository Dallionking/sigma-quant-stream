---
name: renaissance-quant-principles
description: "Jim Simons / Renaissance Technologies inspired quantitative principles for strategy development and validation"
version: "1.0.0"
triggers:
  - "when developing new strategies"
  - "when evaluating strategy statistical validity"
  - "when running probability analysis"
  - "when reviewing backtest robustness"
  - "when assessing signal quality"
---

# Renaissance Quant Principles

## Purpose

Encodes the quantitative philosophy of Jim Simons and Renaissance Technologies into actionable principles for Sigma-Quant strategy development. Every strategy passes through this lens: find tiny, consistent edges and validate them with extreme statistical rigor before risking capital.

## When to Use

- New strategy development (before writing any code)
- Strategy evaluation and review (after backtest)
- Backtest analysis and statistical validation
- Probability and conditional probability work
- Signal quality assessment
- Position sizing decisions via Kelly Criterion

## Core Principles

### 1. Tiny Edge, Massive Scale (50.75%+ Consistency)

Renaissance never sought home runs. A 50.75% win rate with consistent execution and proper sizing compounds into extraordinary returns. Sigma-Quant strategies target the same: small, reliable edges applied at scale.

```python
# In ProbabilityEngine: validate edge consistency
# File: lib/metrics/probability_engine.py

def validate_edge_consistency(self, trades: pd.DataFrame) -> dict:
    """
    Renaissance principle: Edge must persist across regimes.
    A 50.75% win rate over 10,000 trades is more valuable
    than 65% over 200 trades.
    """
    win_rate = (trades['pnl'] > 0).mean()
    n_trades = len(trades)

    # Statistical significance of edge
    # H0: win_rate = 0.50 (no edge)
    z_score = (win_rate - 0.50) / np.sqrt(0.50 * 0.50 / n_trades)
    p_value = 1 - stats.norm.cdf(z_score)

    return {
        'win_rate': win_rate,
        'n_trades': n_trades,
        'z_score': z_score,
        'p_value': p_value,
        'edge_significant': p_value < 0.05,
        'ren_grade': 'pass' if win_rate > 0.5075 and p_value < 0.05 else 'fail'
    }
```

**Rule**: Reject any strategy where the win rate edge is not statistically significant (p < 0.05) over at least 200 trades.

### 2. Unified Signal Model

Never trade on a single indicator. Combine orthogonal signals (price, volume, volatility, sentiment) into a unified probability score. Each signal contributes conditional probability, not a binary yes/no.

```python
# Feature extractors feed the probability engine
# File: lib/metrics/feature_extractors.py

class UnifiedSignalExtractor:
    """
    Extracts orthogonal feature groups for probability estimation.
    Renaissance principle: signals must be independent.
    """
    FEATURE_GROUPS = {
        'momentum': ['rsi_14', 'macd_signal', 'roc_10'],
        'volatility': ['atr_14', 'bb_width', 'historical_vol'],
        'volume': ['vwap_deviation', 'volume_ratio', 'obv_slope'],
        'microstructure': ['bid_ask_imbalance', 'trade_flow', 'tick_direction'],
    }

    def extract(self, bars: pd.DataFrame) -> dict:
        features = {}
        for group, indicators in self.FEATURE_GROUPS.items():
            features[group] = self._compute_group(bars, indicators)
        return features
```

**Rule**: Every strategy must use features from at least 2 orthogonal groups.

### 3. Conditional Probability > Indicators

Raw indicators (RSI > 70 = overbought) are amateur hour. Renaissance thinks in conditional probabilities: P(price_up | RSI > 70 AND volume_declining AND regime = trending). The ProbabilityEngine implements this.

```python
# ProbabilityEngine conditional probability estimation
# File: lib/metrics/probability_engine.py

def conditional_probability(
    self,
    trades: pd.DataFrame,
    conditions: dict[str, callable]
) -> dict:
    """
    Calculate P(profit | conditions).

    Usage:
        engine.conditional_probability(trades, {
            'rsi_high': lambda t: t['rsi'] > 70,
            'vol_declining': lambda t: t['volume_ma_ratio'] < 0.8,
            'trending': lambda t: t['adx'] > 25,
        })
    """
    mask = pd.Series(True, index=trades.index)
    for name, condition in conditions.items():
        mask &= condition(trades)

    filtered = trades[mask]
    if len(filtered) < 30:
        return {'error': 'insufficient_sample', 'n': len(filtered)}

    return {
        'p_profit': (filtered['pnl'] > 0).mean(),
        'n_trades': len(filtered),
        'avg_pnl': filtered['pnl'].mean(),
        'conditions_applied': list(conditions.keys()),
    }
```

**Rule**: Never use indicator thresholds as binary signals. Always compute conditional probabilities.

### 4. Mandatory Validation Stack

Every strategy must pass ALL of these before promotion:

| Check | Tool | Threshold |
|-------|------|-----------|
| Statistical significance | ProbabilityEngine.validate_edge_consistency | p < 0.05 |
| Walk-forward OOS | quant-walk-forward | OOS decay < 30% |
| PBO (Probability of Backtest Overfitting) | De Prado DSR/PBO | PBO < 0.40 |
| Robustness | quant-robustness-testing | Survives +/-20% params |
| Cost inclusion | quant-cost-modeling | Profitable after costs |
| Prop firm compliance | quant-prop-firm-compliance | Passes target firm |
| Monte Carlo | ProbabilityEngine.monte_carlo_stress | 95th pct DD acceptable |

```python
# Probability report runs the full validation stack
# File: lib/metrics/probability_report.py

def run_full_validation(strategy_results: pd.DataFrame, config: dict) -> dict:
    """
    Run the complete Renaissance validation stack.
    A strategy must pass ALL checks to be promoted.
    """
    engine = ProbabilityEngine()
    results = {
        'edge': engine.validate_edge_consistency(strategy_results),
        'conditional': engine.conditional_probability(
            strategy_results, config.get('conditions', {})
        ),
        'monte_carlo': engine.monte_carlo_stress(
            strategy_results, n_simulations=10000
        ),
        'regime_stability': engine.regime_stability(strategy_results),
    }

    # All must pass
    results['all_passed'] = all([
        results['edge']['edge_significant'],
        results['monte_carlo']['95th_pct_dd'] < config.get('max_dd', 0.15),
        results['regime_stability']['stable_across_regimes'],
    ])
    return results
```

### 5. Data Quality Supremacy

Bad data kills strategies. Renaissance spent more on data cleaning than on model development. Sigma-Quant enforces:

- **Databento only** -- no scraped, delayed, or vendor-questionable data
- **Bar count, not dates** -- `bars=N` parameter prevents lookahead bias
- **Gap handling** -- overnight gaps, holiday gaps, contract rolls must be explicit
- **Survivorship bias** -- never backtest on data that excludes delistings

```python
# Data quality checks before any analysis
def validate_data_quality(bars: pd.DataFrame) -> dict:
    """Pre-analysis data quality gate."""
    issues = []

    # Check for gaps
    time_diffs = bars['timestamp'].diff()
    median_diff = time_diffs.median()
    gaps = time_diffs[time_diffs > median_diff * 3]
    if len(gaps) > 0:
        issues.append(f'{len(gaps)} time gaps detected')

    # Check for zero volume
    zero_vol = (bars['volume'] == 0).sum()
    if zero_vol > 0:
        issues.append(f'{zero_vol} zero-volume bars')

    # Check for identical OHLC (stale data)
    stale = (bars['high'] == bars['low']).sum()
    if stale > len(bars) * 0.01:
        issues.append(f'{stale} stale bars (high == low)')

    return {
        'passed': len(issues) == 0,
        'issues': issues,
        'n_bars': len(bars),
        'date_range': f"{bars['timestamp'].min()} to {bars['timestamp'].max()}"
    }
```

**Rule**: Never skip data validation. A strategy on bad data is worse than no strategy.

### 6. Non-Financial Pattern Recognition

Renaissance hired mathematicians, physicists, and linguists -- not traders. Their edge came from applying pattern recognition from other fields. Sigma-Quant's feature extractors should draw from:

- **Signal processing**: Fourier transforms for cycle detection
- **Information theory**: Entropy of price returns for regime detection
- **Statistical physics**: Mean-reversion as particles returning to equilibrium
- **NLP**: Sentiment as a probability modifier, not a trading signal

## Frameworks

### Statistical Arbitrage

Find mean-reverting pairs or spreads, then trade the deviation:

```python
def stat_arb_score(spread: pd.Series, lookback: int = 60) -> dict:
    """Calculate z-score of spread for stat arb entry."""
    mean = spread.rolling(lookback).mean()
    std = spread.rolling(lookback).std()
    z = (spread - mean) / std

    return {
        'z_score': z.iloc[-1],
        'half_life': calculate_half_life(spread),
        'hurst': calculate_hurst_exponent(spread),
        'mean_reverting': calculate_hurst_exponent(spread) < 0.5,
    }
```

### De Prado DSR/PBO (Already Implemented)

Deflated Sharpe Ratio and Probability of Backtest Overfitting are already in the Sigma-Quant pipeline. These correct for multiple testing bias -- the more strategies you test, the more likely a random one looks good.

**Integration point**: `quant-metrics-calculation` and `quant-overfitting-detection` skills.

### Kelly Criterion for Position Sizing from Probability

Use the ProbabilityEngine's output directly for position sizing:

```python
def kelly_from_probability(
    p_win: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 0.25  # Quarter Kelly for safety
) -> float:
    """
    Kelly fraction from probability engine output.
    Renaissance used fractional Kelly (never full Kelly).

    f* = (p * b - q) / b
    where b = avg_win / avg_loss, p = win prob, q = 1 - p
    """
    if avg_loss == 0:
        return 0.0

    b = abs(avg_win / avg_loss)
    q = 1 - p_win
    full_kelly = (p_win * b - q) / b

    # Fractional Kelly (0.25 = quarter Kelly)
    return max(0.0, full_kelly * fraction)
```

**Rule**: Never use full Kelly. Quarter Kelly (0.25x) is the maximum for live trading.

### HMM Regime Transitions

Hidden Markov Models detect regime changes (trending vs ranging vs volatile). Strategy parameters should adapt to regime, not stay static.

```python
# Regime-aware probability adjustment
def adjust_probability_for_regime(
    base_probability: float,
    current_regime: str,
    regime_performance: dict
) -> float:
    """
    Adjust trade probability based on regime performance.
    If strategy performs poorly in 'volatile' regime,
    reduce probability (and thus position size).
    """
    regime_factor = regime_performance.get(current_regime, {}).get('win_rate', 0.5)
    base_factor = regime_performance.get('overall', {}).get('win_rate', 0.5)

    if base_factor == 0:
        return base_probability

    adjustment = regime_factor / base_factor
    return min(1.0, base_probability * adjustment)
```

### Bayesian Updating for Live Probability Refinement

Prior probability from backtest + live trade evidence = posterior probability. As live data accumulates, the probability estimate gets more accurate.

```python
def bayesian_update(
    prior_win_rate: float,
    prior_n: int,
    live_wins: int,
    live_total: int
) -> dict:
    """
    Beta-Binomial Bayesian update of win rate.
    Prior: Beta(alpha, beta) from backtest
    Likelihood: Binomial from live trades
    Posterior: Beta(alpha + wins, beta + losses)
    """
    alpha_prior = prior_win_rate * prior_n
    beta_prior = (1 - prior_win_rate) * prior_n

    alpha_post = alpha_prior + live_wins
    beta_post = beta_prior + (live_total - live_wins)

    posterior_mean = alpha_post / (alpha_post + beta_post)
    # 95% credible interval
    ci_low = stats.beta.ppf(0.025, alpha_post, beta_post)
    ci_high = stats.beta.ppf(0.975, alpha_post, beta_post)

    return {
        'prior_win_rate': prior_win_rate,
        'posterior_win_rate': posterior_mean,
        'credible_interval': (ci_low, ci_high),
        'live_evidence': f'{live_wins}/{live_total}',
        'confidence': 'high' if live_total > 100 else 'low',
    }
```

### Monte Carlo Stress Testing

Simulate thousands of equity curves by resampling trades. If the 95th percentile max drawdown exceeds your limit, the strategy is too risky.

```python
# ProbabilityEngine Monte Carlo method
# File: lib/metrics/probability_engine.py

def monte_carlo_stress(
    self,
    trades: pd.DataFrame,
    n_simulations: int = 10000,
    confidence: float = 0.95
) -> dict:
    """
    Monte Carlo simulation of equity curves.
    Renaissance ran millions of simulations per strategy.
    """
    pnls = trades['pnl'].values
    results = []

    for _ in range(n_simulations):
        shuffled = np.random.choice(pnls, size=len(pnls), replace=True)
        equity = np.cumsum(shuffled)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / np.where(peak > 0, peak, 1)
        results.append({
            'max_dd': drawdown.max(),
            'final_equity': equity[-1],
            'sharpe': shuffled.mean() / (shuffled.std() + 1e-8) * np.sqrt(252),
        })

    dd_series = [r['max_dd'] for r in results]
    pct_idx = int(confidence * n_simulations)

    return {
        'median_max_dd': np.median(dd_series),
        f'{int(confidence*100)}th_pct_dd': sorted(dd_series)[pct_idx],
        'worst_case_dd': max(dd_series),
        'median_sharpe': np.median([r['sharpe'] for r in results]),
        'ruin_probability': sum(1 for r in results if r['final_equity'] < 0) / n_simulations,
    }
```

## File References

| Component | Path |
|-----------|------|
| ProbabilityEngine | `lib/metrics/probability_engine.py` |
| Feature Extractors | `lib/metrics/feature_extractors.py` |
| Probability Report | `lib/metrics/probability_report.py` |
| Base Hit Optimizer | `quant-research-agents/scripts/base_hit_optimizer.py` |
| Walk-Forward Skill | `.claude/skills/stream-quant/quant-walk-forward-validation/SKILL.md` |
| Overfitting Detection | `.claude/skills/stream-quant/quant-overfitting-detection/SKILL.md` |

## Anti-Patterns (What Renaissance Would Never Do)

| Anti-Pattern | Why It Fails |
|-------------|-------------|
| Optimizing on full dataset | Guaranteed overfitting |
| Single indicator signals | No edge in modern markets |
| Ignoring transaction costs | Most edges disappear after costs |
| Using full Kelly sizing | Ruin probability too high |
| Trading without regime awareness | Static params fail in regime shifts |
| Trusting in-sample Sharpe > 3.0 | Almost certainly curve-fitted |
| Fewer than 100 trades in validation | Statistically meaningless |

## Related Skills

- `quant-base-hit-analysis` -- MFE analysis and cash exit optimization
- `quant-overfitting-detection` -- PBO and overfitting red flags
- `quant-metrics-calculation` -- Sharpe, Sortino, DSR calculation
- `quant-walk-forward-validation` -- Out-of-sample walk-forward testing
- `quant-robustness-testing` -- Parameter perturbation testing
- `quant-cost-modeling` -- Transaction cost inclusion
- `quant-prop-firm-compliance` -- Prop firm rule validation
