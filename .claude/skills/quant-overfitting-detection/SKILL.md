---
name: quant-overfitting-detection
description: "Red flag detection patterns for identifying overfitted and unreliable trading strategies"
version: "1.0.0"
triggers:
  - "when validating backtest results"
  - "when reviewing strategy performance"
  - "when detecting look-ahead bias"
  - "when assessing strategy quality"
---

# Quant Overfitting Detection

## Purpose

Provides systematic detection of overfitting and other statistical artifacts that make backtest results unreliable. Every strategy must pass these checks before deployment. A single red flag should trigger deep investigation.

## When to Use

- After any backtest shows promising results
- Before deploying strategies to production
- When reviewing third-party strategies
- During code review of strategy implementations
- When results seem "too good to be true"

## Key Concepts

### What is Overfitting?

Overfitting occurs when a strategy learns the noise in historical data rather than genuine patterns. The result: excellent backtest performance that disappears in live trading.

```
Overfitted Strategy:
- Backtest Sharpe: 3.5  ✓ (looks amazing!)
- Live Sharpe: 0.2      ✗ (reality hits)
- Edge: None (was fitting noise)

Robust Strategy:
- Backtest Sharpe: 1.2  ✓ (reasonable)
- Live Sharpe: 0.9      ✓ (acceptable decay)
- Edge: Real (explainable, persistent)
```

### Red Flag Categories

| Category | Detection | Risk Level |
|----------|-----------|------------|
| **Performance Anomalies** | Sharpe > 3, Win Rate > 80% | CRITICAL |
| **Statistical Artifacts** | P-hacking, multiple testing | HIGH |
| **Data Issues** | Look-ahead, survivorship bias | CRITICAL |
| **Parameter Issues** | Sensitivity, instability | MEDIUM |
| **Complexity Issues** | Too many rules/params | MEDIUM |

### The Overfitting Continuum

```
Underfitting ←────────────────────────────────→ Overfitting
     │                    │                           │
  Too Simple         Just Right                  Too Complex
     │                    │                           │
  Misses Edge         Captures Edge              Fits Noise
```

## Patterns & Templates

### Master Red Flag Checker

```python
"""
Comprehensive overfitting detection system.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RedFlag:
    """Single red flag detection result."""
    name: str
    detected: bool
    severity: RiskLevel
    value: float
    threshold: float
    description: str
    recommendation: str

@dataclass
class OverfittingReport:
    """Complete overfitting analysis report."""
    red_flags: list[RedFlag] = field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.LOW
    deployable: bool = True
    summary: str = ""

    def add_flag(self, flag: RedFlag):
        self.red_flags.append(flag)
        if flag.detected:
            if flag.severity == RiskLevel.CRITICAL:
                self.deployable = False
                self.overall_risk = RiskLevel.CRITICAL
            elif flag.severity == RiskLevel.HIGH and self.overall_risk != RiskLevel.CRITICAL:
                self.overall_risk = RiskLevel.HIGH

    def to_report(self) -> str:
        """Generate human-readable report."""
        report = """
╔══════════════════════════════════════════════════════════════════╗
║                 OVERFITTING DETECTION REPORT                      ║
╠══════════════════════════════════════════════════════════════════╣
"""
        report += f"""
Overall Risk Level: {self.overall_risk.value.upper()}
Deployable: {'YES ✓' if self.deployable else 'NO ✗'}

Red Flags Detected:
{'='*60}
"""
        for flag in self.red_flags:
            status = "🚨 DETECTED" if flag.detected else "✓ Passed"
            report += f"""
{flag.name}
  Status: {status}
  Severity: {flag.severity.value}
  Value: {flag.value:.4f} (Threshold: {flag.threshold})
  {flag.description}
  Recommendation: {flag.recommendation}
"""

        if not self.deployable:
            report += """
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️  STRATEGY SHOULD NOT BE DEPLOYED - CRITICAL FLAGS DETECTED    ║
╚══════════════════════════════════════════════════════════════════╝
"""
        return report


class OverfittingDetector:
    """
    Comprehensive overfitting detection for trading strategies.
    """

    def __init__(self):
        self.report = OverfittingReport()

    def analyze(
        self,
        returns: pd.Series,
        trades: pd.DataFrame,
        is_metrics: dict,
        oos_metrics: dict,
        params: dict,
        param_sensitivity: dict = None
    ) -> OverfittingReport:
        """
        Run all overfitting checks.

        Args:
            returns: Strategy return series
            trades: DataFrame of individual trades
            is_metrics: In-sample performance metrics
            oos_metrics: Out-of-sample performance metrics
            params: Strategy parameters
            param_sensitivity: Optional dict of param -> sensitivity score
        """
        # Reset report
        self.report = OverfittingReport()

        # Run all checks
        self._check_sharpe_too_high(is_metrics)
        self._check_win_rate_too_high(is_metrics)
        self._check_no_losing_months(returns)
        self._check_oos_decay(is_metrics, oos_metrics)
        self._check_insufficient_trades(trades)
        self._check_profit_factor_extreme(is_metrics)
        self._check_max_dd_suspicious(is_metrics)
        self._check_parameter_count(params)
        self._check_parameter_sensitivity(param_sensitivity)
        self._check_consecutive_winners(trades)
        self._check_curve_fitting_ratio(is_metrics, oos_metrics)

        # Generate summary
        self._generate_summary()

        return self.report

    def _check_sharpe_too_high(self, metrics: dict):
        """Sharpe > 3.0 is almost always overfitting."""
        sharpe = metrics.get('sharpe', 0)

        flag = RedFlag(
            name="Suspiciously High Sharpe Ratio",
            detected=sharpe > 3.0,
            severity=RiskLevel.CRITICAL,
            value=sharpe,
            threshold=3.0,
            description="Sharpe ratios above 3.0 in backtests almost never persist in live trading. "
                       "Even Renaissance Technologies averages ~1.5 after fees.",
            recommendation="Verify no look-ahead bias. Check transaction costs are realistic. "
                          "Run walk-forward validation."
        )
        self.report.add_flag(flag)

    def _check_win_rate_too_high(self, metrics: dict):
        """Win rate > 80% suggests look-ahead bias or curve fitting."""
        win_rate = metrics.get('win_rate', 0)

        flag = RedFlag(
            name="Unrealistic Win Rate",
            detected=win_rate > 0.80,
            severity=RiskLevel.CRITICAL,
            value=win_rate,
            threshold=0.80,
            description="Win rates above 80% are extremely rare in legitimate strategies. "
                       "This typically indicates look-ahead bias or severe overfitting.",
            recommendation="Check for look-ahead bias in signal generation. "
                          "Verify entry/exit timing is realistic."
        )
        self.report.add_flag(flag)

    def _check_no_losing_months(self, returns: pd.Series):
        """No losing months is highly suspicious."""
        monthly = returns.resample('M').sum()
        losing_months = (monthly < 0).sum()
        total_months = len(monthly)

        flag = RedFlag(
            name="No Losing Months",
            detected=losing_months == 0 and total_months >= 12,
            severity=RiskLevel.CRITICAL,
            value=losing_months,
            threshold=1,
            description="Having zero losing months over a year+ is statistically improbable. "
                       "Even the best funds have losing months.",
            recommendation="This is a strong indicator of look-ahead bias or "
                          "data fitting. Re-examine signal generation."
        )
        self.report.add_flag(flag)

    def _check_oos_decay(self, is_metrics: dict, oos_metrics: dict):
        """OOS performance should not decay more than 50% from IS."""
        is_sharpe = is_metrics.get('sharpe', 0)
        oos_sharpe = oos_metrics.get('sharpe', 0)

        if is_sharpe > 0:
            decay = (is_sharpe - oos_sharpe) / is_sharpe
        else:
            decay = 1.0

        flag = RedFlag(
            name="Excessive OOS Performance Decay",
            detected=decay > 0.50,
            severity=RiskLevel.HIGH,
            value=decay,
            threshold=0.50,
            description=f"Performance dropped {decay:.0%} from in-sample to out-of-sample. "
                       "Healthy strategies show <40% decay.",
            recommendation="Parameters may be overfit to training data. "
                          "Consider simpler model or different parameter values."
        )
        self.report.add_flag(flag)

    def _check_insufficient_trades(self, trades: pd.DataFrame):
        """Too few trades means results aren't statistically significant."""
        n_trades = len(trades)

        flag = RedFlag(
            name="Insufficient Trade Count",
            detected=n_trades < 100,
            severity=RiskLevel.HIGH,
            value=n_trades,
            threshold=100,
            description=f"Only {n_trades} trades - need at least 100 for basic statistical significance. "
                       "Ideally want 200+ trades.",
            recommendation="Use longer backtest period or more active timeframe. "
                          "Cannot trust statistics with so few trades."
        )
        self.report.add_flag(flag)

    def _check_profit_factor_extreme(self, metrics: dict):
        """Profit factor > 3.0 is suspicious."""
        pf = metrics.get('profit_factor', 0)

        flag = RedFlag(
            name="Unrealistic Profit Factor",
            detected=pf > 3.0,
            severity=RiskLevel.HIGH,
            value=pf,
            threshold=3.0,
            description="Profit factors above 3.0 rarely persist. "
                       "Most successful strategies have PF between 1.3-2.0.",
            recommendation="Verify losing trades are being captured correctly. "
                          "Check that slippage and commission are realistic."
        )
        self.report.add_flag(flag)

    def _check_max_dd_suspicious(self, metrics: dict):
        """Max drawdown < 5% with high returns is suspicious."""
        max_dd = abs(metrics.get('max_dd', 0))
        sharpe = metrics.get('sharpe', 0)

        # Suspicious if high Sharpe but tiny drawdown
        suspicious = sharpe > 1.5 and max_dd < 0.05

        flag = RedFlag(
            name="Suspiciously Low Drawdown",
            detected=suspicious,
            severity=RiskLevel.MEDIUM,
            value=max_dd,
            threshold=0.05,
            description="Combining high returns with tiny drawdowns is unrealistic. "
                       "Either returns are inflated or drawdown calculation is wrong.",
            recommendation="Verify drawdown calculation includes all costs. "
                          "Check that peak equity is calculated correctly."
        )
        self.report.add_flag(flag)

    def _check_parameter_count(self, params: dict):
        """Too many parameters = overfitting risk."""
        n_params = len(params)

        flag = RedFlag(
            name="Too Many Parameters",
            detected=n_params > 6,
            severity=RiskLevel.MEDIUM,
            value=n_params,
            threshold=6,
            description=f"Strategy has {n_params} parameters. Each parameter is an opportunity "
                       "to overfit. Best strategies have 2-4 parameters.",
            recommendation="Simplify strategy. Remove parameters that don't significantly "
                          "improve risk-adjusted returns."
        )
        self.report.add_flag(flag)

    def _check_parameter_sensitivity(self, sensitivity: dict):
        """Optimal params should not be at extreme values."""
        if sensitivity is None:
            return

        # Check if optimal is at edge of tested range
        at_edge = any(s.get('at_edge', False) for s in sensitivity.values())

        flag = RedFlag(
            name="Parameters at Edge of Range",
            detected=at_edge,
            severity=RiskLevel.MEDIUM,
            value=1 if at_edge else 0,
            threshold=0,
            description="Optimal parameters are at the edge of tested ranges. "
                       "This suggests the true optimum may be outside tested values, "
                       "or that performance is unstable.",
            recommendation="Expand parameter search range. If still at edge, "
                          "parameters may be meaningless."
        )
        self.report.add_flag(flag)

    def _check_consecutive_winners(self, trades: pd.DataFrame):
        """Too many consecutive winners suggests bias."""
        if 'pnl' not in trades.columns:
            return

        wins = trades['pnl'] > 0
        max_consecutive = self._max_consecutive_true(wins)

        # Statistically, > 15 consecutive wins at 60% win rate is very unlikely
        flag = RedFlag(
            name="Excessive Consecutive Winners",
            detected=max_consecutive > 15,
            severity=RiskLevel.MEDIUM,
            value=max_consecutive,
            threshold=15,
            description=f"Found {max_consecutive} consecutive winning trades. "
                       "This is statistically improbable without bias.",
            recommendation="Check trade timestamps for clustering. "
                          "Verify no duplicate trade entries."
        )
        self.report.add_flag(flag)

    def _check_curve_fitting_ratio(self, is_metrics: dict, oos_metrics: dict):
        """
        Curve Fitting Ratio: compares IS/OOS performance distributions.
        CFR > 0.5 suggests overfitting.
        """
        is_sharpe = is_metrics.get('sharpe', 0)
        oos_sharpe = oos_metrics.get('sharpe', 0)
        is_dd = abs(is_metrics.get('max_dd', 0.01))
        oos_dd = abs(oos_metrics.get('max_dd', 0.01))

        # CFR = (IS_Sharpe/OOS_Sharpe - 1) + (OOS_DD/IS_DD - 1)
        sharpe_ratio = (is_sharpe / oos_sharpe - 1) if oos_sharpe > 0 else 10
        dd_ratio = (oos_dd / is_dd - 1) if is_dd > 0 else 10
        cfr = (sharpe_ratio + dd_ratio) / 2

        flag = RedFlag(
            name="High Curve Fitting Ratio",
            detected=cfr > 0.5,
            severity=RiskLevel.HIGH,
            value=cfr,
            threshold=0.5,
            description=f"CFR of {cfr:.2f} indicates significant overfitting. "
                       "IS performance is much better than OOS.",
            recommendation="Simplify strategy. Use walk-forward optimization. "
                          "Consider out-of-sample Sharpe as true expected performance."
        )
        self.report.add_flag(flag)

    def _max_consecutive_true(self, series: pd.Series) -> int:
        """Find maximum consecutive True values."""
        groups = (series != series.shift()).cumsum()
        counts = series.groupby(groups).sum()
        return int(counts.max()) if len(counts) > 0 else 0

    def _generate_summary(self):
        """Generate summary of all findings."""
        critical = sum(1 for f in self.report.red_flags
                      if f.detected and f.severity == RiskLevel.CRITICAL)
        high = sum(1 for f in self.report.red_flags
                  if f.detected and f.severity == RiskLevel.HIGH)
        medium = sum(1 for f in self.report.red_flags
                    if f.detected and f.severity == RiskLevel.MEDIUM)

        if critical > 0:
            self.report.summary = (
                f"CRITICAL: {critical} critical red flags detected. "
                "Strategy should NOT be deployed."
            )
        elif high > 0:
            self.report.summary = (
                f"WARNING: {high} high-severity flags detected. "
                "Strategy needs significant review before deployment."
            )
        elif medium > 0:
            self.report.summary = (
                f"CAUTION: {medium} medium-severity flags detected. "
                "Consider addressing these issues."
            )
        else:
            self.report.summary = "No significant overfitting indicators detected."
```

### Look-Ahead Bias Detection

```python
"""
Specific checks for look-ahead bias - using future information in signals.
"""

class LookAheadBiasDetector:
    """
    Detects look-ahead bias in strategy implementations.
    """

    def check_signal_timing(self, df: pd.DataFrame) -> list[str]:
        """
        Check that signals don't use future data.

        Common issues:
        1. Using close price of current bar for entry on current bar
        2. Using indicators that reference future values
        3. Gap-fill detection before gap happens
        """
        issues = []

        # Check for shift issues
        if 'signal' in df.columns:
            # Correlation with future returns suggests look-ahead
            future_returns = df['close'].pct_change().shift(-1)
            signal_future_corr = df['signal'].corr(future_returns)

            if abs(signal_future_corr) > 0.3:
                issues.append(
                    f"Signal has {signal_future_corr:.2f} correlation with FUTURE returns. "
                    "This indicates look-ahead bias."
                )

        return issues

    def check_entry_exit_timing(self, trades: pd.DataFrame) -> list[str]:
        """
        Check that entries and exits use realistic prices.
        """
        issues = []

        # Check if entry price equals exact high/low
        if 'entry_price' in trades.columns and 'bar_high' in trades.columns:
            long_at_low = (
                (trades['direction'] == 1) &
                (trades['entry_price'] == trades['bar_low'])
            )
            short_at_high = (
                (trades['direction'] == -1) &
                (trades['entry_price'] == trades['bar_high'])
            )

            pct_perfect_entry = (long_at_low | short_at_high).mean()

            if pct_perfect_entry > 0.5:
                issues.append(
                    f"{pct_perfect_entry:.0%} of entries are at exact bar high/low. "
                    "This suggests unrealistic fill assumptions."
                )

        return issues

    def check_indicator_calculation(self, indicator_code: str) -> list[str]:
        """
        Static analysis of indicator code for look-ahead patterns.
        """
        issues = []

        # Check for negative shifts (future reference)
        if 'shift(-' in indicator_code:
            issues.append(
                "Code contains shift(-N) which references FUTURE data. "
                "This is look-ahead bias."
            )

        # Check for .iloc[-1] used on incomplete bar
        if '.iloc[-1]' in indicator_code and 'realtime' in indicator_code.lower():
            issues.append(
                "Using .iloc[-1] on live data may use incomplete bar. "
                "Ensure using .iloc[-2] for completed bar."
            )

        return issues


def detect_look_ahead_bias(
    df: pd.DataFrame,
    signal_col: str = 'signal',
    return_col: str = 'returns'
) -> dict:
    """
    Comprehensive look-ahead bias detection.

    Returns dict with detected issues and severity.
    """
    results = {
        'has_bias': False,
        'issues': [],
        'severity': 'none'
    }

    # Test 1: Future correlation
    future_returns = df[return_col].shift(-1)
    corr = df[signal_col].corr(future_returns)

    if abs(corr) > 0.2:
        results['issues'].append({
            'test': 'Future Correlation',
            'value': corr,
            'description': 'Signal correlated with future returns'
        })
        results['has_bias'] = True

    # Test 2: Perfect timing (signals at exact tops/bottoms)
    if 'high' in df.columns and 'low' in df.columns:
        buy_signals = df[signal_col] == 1
        sell_signals = df[signal_col] == -1

        # Buy at exact low of the day
        buy_at_low = buy_signals & (df['close'] == df['low'])
        # Sell at exact high
        sell_at_high = sell_signals & (df['close'] == df['high'])

        perfect_timing = (buy_at_low.sum() + sell_at_high.sum()) / (buy_signals.sum() + sell_signals.sum())

        if perfect_timing > 0.3:
            results['issues'].append({
                'test': 'Perfect Timing',
                'value': perfect_timing,
                'description': 'Too many signals at exact highs/lows'
            })
            results['has_bias'] = True

    # Test 3: Win rate vs theoretical limit
    win_rate = (df[signal_col].shift(1) * df[return_col] > 0).mean()

    if win_rate > 0.7:
        results['issues'].append({
            'test': 'Win Rate',
            'value': win_rate,
            'description': 'Win rate exceeds realistic bounds'
        })
        results['has_bias'] = True

    # Determine severity
    if len(results['issues']) >= 3:
        results['severity'] = 'critical'
    elif len(results['issues']) >= 2:
        results['severity'] = 'high'
    elif len(results['issues']) >= 1:
        results['severity'] = 'medium'

    return results
```

### Multiple Testing Correction

```python
"""
Corrections for multiple testing / p-hacking.
"""

def bonferroni_correction(p_values: list[float], alpha: float = 0.05) -> dict:
    """
    Bonferroni correction for multiple hypothesis testing.

    If you test N strategies, the chance of finding one that appears
    significant by chance alone is: 1 - (1 - alpha)^N

    Bonferroni corrects by using alpha/N as the threshold.
    """
    n = len(p_values)
    corrected_alpha = alpha / n

    return {
        'original_alpha': alpha,
        'corrected_alpha': corrected_alpha,
        'n_tests': n,
        'significant_before_correction': sum(p < alpha for p in p_values),
        'significant_after_correction': sum(p < corrected_alpha for p in p_values),
        'details': [
            {
                'p_value': p,
                'significant_original': p < alpha,
                'significant_corrected': p < corrected_alpha
            }
            for p in p_values
        ]
    }


def calculate_deflated_sharpe(
    sharpe_observed: float,
    n_strategies_tested: int,
    n_observations: int,
    skewness: float = 0,
    kurtosis: float = 3
) -> dict:
    """
    Calculate deflated Sharpe ratio accounting for multiple testing.

    Based on Bailey & de Prado (2014) "The Deflated Sharpe Ratio"

    Args:
        sharpe_observed: The best Sharpe ratio found
        n_strategies_tested: Number of strategies/parameters tested
        n_observations: Number of observations in backtest
        skewness: Return skewness (default 0)
        kurtosis: Return kurtosis (default 3, normal)
    """
    from scipy import stats

    # Expected max Sharpe under null hypothesis (no skill)
    e_max_sharpe = stats.norm.ppf(1 - 1/(n_strategies_tested + 1))

    # Variance of Sharpe ratio
    var_sharpe = (1 + 0.5 * sharpe_observed**2 - skewness * sharpe_observed +
                  (kurtosis - 3) / 4 * sharpe_observed**2) / n_observations

    # Deflated Sharpe
    deflated = (sharpe_observed - e_max_sharpe) / np.sqrt(var_sharpe)

    # Probability that observed Sharpe is due to chance
    p_value = 1 - stats.norm.cdf(deflated)

    return {
        'observed_sharpe': sharpe_observed,
        'expected_max_sharpe': e_max_sharpe,
        'deflated_sharpe': deflated,
        'p_value': p_value,
        'is_significant': p_value < 0.05,
        'interpretation': (
            f"After testing {n_strategies_tested} strategies, "
            f"the deflated Sharpe is {deflated:.2f} (p={p_value:.3f}). "
            f"{'Significant edge detected.' if p_value < 0.05 else 'No significant edge - likely overfitting.'}"
        )
    }
```

## Examples

### Example 1: Full Overfitting Analysis

```python
"""
Complete workflow for detecting overfitting.
"""

# 1. Run backtest
results = backtest_strategy(df, params)

# 2. Split results for IS/OOS analysis
is_returns = results['returns'].iloc[:int(len(results)*0.7)]
oos_returns = results['returns'].iloc[int(len(results)*0.7):]

is_metrics = calculate_metrics(is_returns)
oos_metrics = calculate_metrics(oos_returns)

# 3. Run overfitting detection
detector = OverfittingDetector()
report = detector.analyze(
    returns=results['returns'],
    trades=results['trades'],
    is_metrics=is_metrics,
    oos_metrics=oos_metrics,
    params={'rsi_period': 14, 'oversold': 30, 'overbought': 70},
    param_sensitivity={'rsi_period': {'cv': 0.15, 'at_edge': False}}
)

# 4. Print report
print(report.to_report())

# 5. Check if deployable
if report.deployable:
    print("Strategy passed overfitting checks!")

    # 6. Apply multiple testing correction if needed
    if num_strategies_tested > 1:
        deflated = calculate_deflated_sharpe(
            sharpe_observed=is_metrics['sharpe'],
            n_strategies_tested=num_strategies_tested,
            n_observations=len(is_returns)
        )
        print(f"Deflated Sharpe: {deflated['deflated_sharpe']:.2f}")

        if not deflated['is_significant']:
            print("WARNING: After multiple testing correction, edge is not significant!")
else:
    print("STOP: Strategy failed overfitting checks. Do not deploy.")
    for flag in report.red_flags:
        if flag.detected:
            print(f"  - {flag.name}: {flag.recommendation}")
```

## Common Mistakes

### 1. Ignoring Multiple Testing

```python
# WRONG: Testing 100 strategies, deploying the best one
best_strategy = None
best_sharpe = 0
for params in all_param_combinations:  # 100 combinations
    result = backtest(params)
    if result.sharpe > best_sharpe:
        best_sharpe = result.sharpe
        best_strategy = params
# "Found a 2.5 Sharpe strategy!" - No, you found noise

# RIGHT: Apply multiple testing correction
deflated = calculate_deflated_sharpe(
    sharpe_observed=best_sharpe,
    n_strategies_tested=100,
    n_observations=len(data)
)
if deflated['is_significant']:
    print("True edge found")
else:
    print("Likely just luck from testing 100 strategies")
```

### 2. Cherry-Picking Test Periods

```python
# WRONG: Testing multiple periods, reporting the best
for start_date in ['2020-01', '2020-04', '2020-07', '2021-01']:
    result = backtest(data[start_date:])
    if result.sharpe > 2:
        print(f"Great results from {start_date}!")  # Cherry-picked!

# RIGHT: Use one predefined test period
TEST_PERIOD = '2023-01-01'  # Decided before any testing
result = backtest(data[TEST_PERIOD:])
print(f"OOS Result: {result.sharpe}")
```

### 3. Overfitting to OOS

```python
# WRONG: Iterating until OOS looks good
while oos_sharpe < 1.0:
    params = tweak_parameters(params)
    oos_sharpe = test_on_oos(params)
# OOS is now contaminated!

# RIGHT: One-shot OOS testing
# 1. Optimize on IS
# 2. Test on OOS ONCE
# 3. Accept results as they are
optimal_params = optimize_on_is(data[:split])
oos_result = test_on_oos(data[split:], optimal_params)  # Single test!
```
