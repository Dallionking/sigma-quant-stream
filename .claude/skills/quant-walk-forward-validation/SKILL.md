---
name: quant-walk-forward-validation
description: "Walk-Forward Optimization implementation with anchored and rolling methods for robust strategy validation"
version: "1.0.0"
triggers:
  - "when validating strategy robustness"
  - "when testing parameter stability"
  - "when implementing WFO backtesting"
  - "when avoiding overfitting"
---

# Quant Walk-Forward Validation

## Purpose

Implements Walk-Forward Optimization (WFO) methodology to validate trading strategies against overfitting. WFO tests how well optimized parameters perform on unseen data, providing realistic estimates of future performance.

## When to Use

- After initial in-sample backtesting shows promise
- Before deploying any strategy to production
- When validating parameter choices
- When comparing strategy variants
- During quarterly strategy reviews

## Key Concepts

### What is Walk-Forward Optimization?

WFO divides data into multiple optimization (in-sample) and validation (out-of-sample) periods, simulating how a strategy would be re-optimized over time.

```
Traditional Backtest (WRONG):
|------- All Data: Optimize & Test Together -------|
         (Overfitting guaranteed)

Walk-Forward (RIGHT):
|-- IS1: Optimize --|-- OOS1: Validate --|
                    |-- IS2: Optimize --|-- OOS2: Validate --|
                                        |-- IS3: Optimize --|-- OOS3: Validate --|
```

### Anchored vs Rolling WFO

| Method | In-Sample Window | Best For |
|--------|------------------|----------|
| **Anchored** | Grows over time (all data from start) | Stable markets, more data = better |
| **Rolling** | Fixed size, slides forward | Regime changes, recent data most relevant |

```
Anchored WFO:
|----IS1----|--OOS1--|
|-------IS2-------|--OOS2--|
|-----------IS3----------|--OOS3--|

Rolling WFO (Fixed 6-month IS):
|--IS1--|--OOS1--|
        |--IS2--|--OOS2--|
                |--IS3--|--OOS3--|
```

### Key Metrics

| Metric | Formula | Good Value |
|--------|---------|------------|
| **WFO Efficiency** | OOS Sharpe / IS Sharpe | > 50% |
| **Parameter Stability** | Std(optimal params) / Mean | < 30% |
| **Consistency Ratio** | Profitable OOS periods / Total | > 60% |
| **OOS Degradation** | (IS Sharpe - OOS Sharpe) / IS Sharpe | < 40% |

## Patterns & Templates

### Walk-Forward Implementation

```python
"""
Walk-Forward Optimization Framework
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Optional, Literal
from datetime import datetime, timedelta
import itertools

@dataclass
class WFOConfig:
    """Configuration for Walk-Forward Optimization."""
    # Split configuration
    is_bars: int = 252 * 2  # 2 years in-sample
    oos_bars: int = 63      # 3 months out-of-sample
    method: Literal["anchored", "rolling"] = "anchored"

    # Optimization configuration
    parameter_grid: dict = field(default_factory=dict)
    optimization_metric: str = "sharpe"  # sharpe, sortino, calmar

    # Validation thresholds
    min_trades_per_period: int = 30
    min_oos_sharpe: float = 0.5
    max_oos_degradation: float = 0.5

    # Output configuration
    save_all_results: bool = True
    output_dir: str = "wfo_results"


@dataclass
class WFOPeriodResult:
    """Results from a single WFO period."""
    period_num: int
    is_start: datetime
    is_end: datetime
    oos_start: datetime
    oos_end: datetime

    # Best parameters found
    optimal_params: dict

    # In-sample metrics
    is_sharpe: float
    is_trades: int
    is_win_rate: float
    is_max_dd: float

    # Out-of-sample metrics
    oos_sharpe: float
    oos_trades: int
    oos_win_rate: float
    oos_max_dd: float

    # Computed metrics
    @property
    def wfo_efficiency(self) -> float:
        """OOS Sharpe as percentage of IS Sharpe."""
        if self.is_sharpe == 0:
            return 0
        return self.oos_sharpe / self.is_sharpe

    @property
    def degradation(self) -> float:
        """How much performance degraded OOS."""
        if self.is_sharpe == 0:
            return 1.0
        return (self.is_sharpe - self.oos_sharpe) / abs(self.is_sharpe)


@dataclass
class WFOSummary:
    """Summary of all WFO periods."""
    periods: list[WFOPeriodResult]
    config: WFOConfig

    @property
    def total_periods(self) -> int:
        return len(self.periods)

    @property
    def profitable_periods(self) -> int:
        return sum(1 for p in self.periods if p.oos_sharpe > 0)

    @property
    def consistency_ratio(self) -> float:
        """Percentage of OOS periods that were profitable."""
        return self.profitable_periods / self.total_periods if self.total_periods > 0 else 0

    @property
    def avg_wfo_efficiency(self) -> float:
        """Average WFO efficiency across all periods."""
        efficiencies = [p.wfo_efficiency for p in self.periods if p.wfo_efficiency > 0]
        return np.mean(efficiencies) if efficiencies else 0

    @property
    def avg_oos_sharpe(self) -> float:
        """Average OOS Sharpe ratio."""
        return np.mean([p.oos_sharpe for p in self.periods])

    @property
    def parameter_stability(self) -> dict:
        """Standard deviation of optimal parameters across periods."""
        all_params = [p.optimal_params for p in self.periods]
        stability = {}

        for key in all_params[0].keys():
            values = [p[key] for p in all_params]
            stability[key] = {
                "mean": np.mean(values),
                "std": np.std(values),
                "cv": np.std(values) / np.mean(values) if np.mean(values) != 0 else float('inf')
            }

        return stability

    def is_valid(self) -> bool:
        """Check if WFO results meet validation criteria."""
        return (
            self.consistency_ratio >= 0.5 and
            self.avg_wfo_efficiency >= 0.5 and
            self.avg_oos_sharpe >= self.config.min_oos_sharpe
        )

    def to_report(self) -> str:
        """Generate human-readable report."""
        stability = self.parameter_stability

        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║               WALK-FORWARD OPTIMIZATION REPORT                    ║
╠══════════════════════════════════════════════════════════════════╣

Configuration:
  Method: {self.config.method}
  IS Period: {self.config.is_bars} bars
  OOS Period: {self.config.oos_bars} bars
  Total Periods: {self.total_periods}

Overall Results:
  Consistency Ratio: {self.consistency_ratio:.1%} ({self.profitable_periods}/{self.total_periods} profitable)
  Avg WFO Efficiency: {self.avg_wfo_efficiency:.1%}
  Avg OOS Sharpe: {self.avg_oos_sharpe:.2f}

Parameter Stability:
"""
        for param, stats in stability.items():
            report += f"  {param}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, CV={stats['cv']:.1%}\n"

        report += f"""
Per-Period Results:
{'='*60}
"""
        for p in self.periods:
            report += f"""
Period {p.period_num}:
  IS: {p.is_start.strftime('%Y-%m-%d')} to {p.is_end.strftime('%Y-%m-%d')}
  OOS: {p.oos_start.strftime('%Y-%m-%d')} to {p.oos_end.strftime('%Y-%m-%d')}
  Optimal Params: {p.optimal_params}
  IS Sharpe: {p.is_sharpe:.2f} | OOS Sharpe: {p.oos_sharpe:.2f}
  WFO Efficiency: {p.wfo_efficiency:.1%}
"""

        report += f"""
{'='*60}
VALIDATION: {'PASSED ✓' if self.is_valid() else 'FAILED ✗'}
╚══════════════════════════════════════════════════════════════════╝
"""
        return report


class WalkForwardOptimizer:
    """
    Walk-Forward Optimization engine.
    """

    def __init__(
        self,
        strategy_func: Callable,
        config: WFOConfig
    ):
        """
        Args:
            strategy_func: Function that takes (df, **params) and returns metrics dict
            config: WFO configuration
        """
        self.strategy_func = strategy_func
        self.config = config

    def run(self, df: pd.DataFrame) -> WFOSummary:
        """
        Run walk-forward optimization on data.
        """
        periods = self._generate_periods(df)
        results = []

        for i, (is_data, oos_data) in enumerate(periods):
            print(f"WFO Period {i+1}/{len(periods)}")

            # Optimize on IS data
            optimal_params, is_metrics = self._optimize(is_data)

            # Validate on OOS data
            oos_metrics = self._evaluate(oos_data, optimal_params)

            result = WFOPeriodResult(
                period_num=i + 1,
                is_start=is_data.index[0],
                is_end=is_data.index[-1],
                oos_start=oos_data.index[0],
                oos_end=oos_data.index[-1],
                optimal_params=optimal_params,
                is_sharpe=is_metrics.get('sharpe', 0),
                is_trades=is_metrics.get('trades', 0),
                is_win_rate=is_metrics.get('win_rate', 0),
                is_max_dd=is_metrics.get('max_dd', 0),
                oos_sharpe=oos_metrics.get('sharpe', 0),
                oos_trades=oos_metrics.get('trades', 0),
                oos_win_rate=oos_metrics.get('win_rate', 0),
                oos_max_dd=oos_metrics.get('max_dd', 0),
            )
            results.append(result)

        return WFOSummary(periods=results, config=self.config)

    def _generate_periods(self, df: pd.DataFrame) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """Generate IS/OOS period pairs."""
        periods = []
        n = len(df)
        is_bars = self.config.is_bars
        oos_bars = self.config.oos_bars

        if self.config.method == "anchored":
            # Anchored: IS starts from beginning, grows
            start = 0
            is_end = is_bars

            while is_end + oos_bars <= n:
                is_data = df.iloc[start:is_end]
                oos_data = df.iloc[is_end:is_end + oos_bars]
                periods.append((is_data, oos_data))

                is_end += oos_bars  # Grow IS by OOS size

        else:  # Rolling
            # Rolling: Fixed IS size, slides forward
            start = 0

            while start + is_bars + oos_bars <= n:
                is_data = df.iloc[start:start + is_bars]
                oos_data = df.iloc[start + is_bars:start + is_bars + oos_bars]
                periods.append((is_data, oos_data))

                start += oos_bars  # Slide by OOS size

        return periods

    def _optimize(self, df: pd.DataFrame) -> tuple[dict, dict]:
        """
        Find optimal parameters on in-sample data.
        Returns (optimal_params, metrics)
        """
        best_params = None
        best_metric = float('-inf')
        best_metrics = {}

        # Generate all parameter combinations
        param_names = list(self.config.parameter_grid.keys())
        param_values = list(self.config.parameter_grid.values())

        for combo in itertools.product(*param_values):
            params = dict(zip(param_names, combo))

            metrics = self.strategy_func(df, **params)

            # Check minimum trades
            if metrics.get('trades', 0) < self.config.min_trades_per_period:
                continue

            # Get optimization metric
            metric_value = metrics.get(self.config.optimization_metric, 0)

            if metric_value > best_metric:
                best_metric = metric_value
                best_params = params
                best_metrics = metrics

        return best_params or {}, best_metrics

    def _evaluate(self, df: pd.DataFrame, params: dict) -> dict:
        """Evaluate strategy with fixed parameters on OOS data."""
        if not params:
            return {}
        return self.strategy_func(df, **params)


# ============================================================
# HELPER: Strategy Function Template
# ============================================================

def strategy_template(df: pd.DataFrame, **params) -> dict:
    """
    Template for strategy function used in WFO.

    Args:
        df: OHLCV DataFrame
        **params: Strategy parameters to optimize

    Returns:
        dict with keys: sharpe, sortino, calmar, trades, win_rate, max_dd
    """
    # Example: RSI mean reversion
    rsi_period = params.get('rsi_period', 14)
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)

    # Calculate indicators
    df = df.copy()
    df['rsi'] = calculate_rsi(df['close'], rsi_period)

    # Generate signals
    df['signal'] = 0
    df.loc[df['rsi'] < oversold, 'signal'] = 1
    df.loc[df['rsi'] > overbought, 'signal'] = -1

    # Calculate returns (simplified)
    df['strategy_returns'] = df['signal'].shift(1) * df['close'].pct_change()

    # Calculate metrics
    returns = df['strategy_returns'].dropna()
    trades = (df['signal'].diff() != 0).sum()

    if len(returns) == 0 or returns.std() == 0:
        return {'sharpe': 0, 'trades': 0, 'win_rate': 0, 'max_dd': 0}

    sharpe = returns.mean() / returns.std() * np.sqrt(252)

    winning = (returns > 0).sum()
    win_rate = winning / len(returns) if len(returns) > 0 else 0

    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = abs(drawdown.min())

    return {
        'sharpe': sharpe,
        'trades': trades,
        'win_rate': win_rate,
        'max_dd': max_dd
    }
```

### Anchored Walk-Forward Pattern

```python
"""
Anchored Walk-Forward: IS period grows over time.
Best for: Stable markets where more data improves model.
"""

def anchored_walk_forward(
    df: pd.DataFrame,
    strategy_func: Callable,
    param_grid: dict,
    initial_is_bars: int = 504,  # 2 years
    oos_bars: int = 63,          # 3 months
    min_is_bars: int = 252       # Minimum 1 year
) -> WFOSummary:
    """
    Anchored WFO where in-sample always starts from beginning.

    Visualization:
    |=========IS1=========|---OOS1---|
    |=============IS2=============|---OOS2---|
    |=================IS3=================|---OOS3---|
    """
    config = WFOConfig(
        is_bars=initial_is_bars,
        oos_bars=oos_bars,
        method="anchored",
        parameter_grid=param_grid
    )

    optimizer = WalkForwardOptimizer(strategy_func, config)
    return optimizer.run(df)
```

### Rolling Walk-Forward Pattern

```python
"""
Rolling Walk-Forward: Fixed IS window slides forward.
Best for: Markets with regime changes where recent data is more relevant.
"""

def rolling_walk_forward(
    df: pd.DataFrame,
    strategy_func: Callable,
    param_grid: dict,
    is_bars: int = 252,    # 1 year
    oos_bars: int = 63,    # 3 months
    overlap_bars: int = 0  # No overlap between periods
) -> WFOSummary:
    """
    Rolling WFO where in-sample is fixed size.

    Visualization (no overlap):
    |===IS1===|---OOS1---|
              |===IS2===|---OOS2---|
                        |===IS3===|---OOS3---|
    """
    config = WFOConfig(
        is_bars=is_bars,
        oos_bars=oos_bars,
        method="rolling",
        parameter_grid=param_grid
    )

    optimizer = WalkForwardOptimizer(strategy_func, config)
    return optimizer.run(df)
```

### Combinatorial Purged Cross-Validation

```python
"""
Combinatorial Purged Cross-Validation (CPCV)
De Prado's method for more robust validation.
"""
from itertools import combinations

def combinatorial_purged_cv(
    df: pd.DataFrame,
    strategy_func: Callable,
    params: dict,
    n_splits: int = 5,
    n_test_splits: int = 2,
    purge_bars: int = 10,  # Gap between train/test
    embargo_bars: int = 5   # Gap after test
) -> dict:
    """
    CPCV: Test on multiple combinations of folds.

    Instead of single train/test split, tests all combinations
    of k folds taken n_test_splits at a time.

    Args:
        n_splits: Number of folds
        n_test_splits: Number of folds to use as test set
        purge_bars: Bars to remove between train and test (avoid leakage)
        embargo_bars: Bars to remove after test set
    """
    n = len(df)
    fold_size = n // n_splits

    # Create fold indices
    folds = []
    for i in range(n_splits):
        start = i * fold_size
        end = start + fold_size if i < n_splits - 1 else n
        folds.append((start, end))

    # Generate all test combinations
    test_combinations = list(combinations(range(n_splits), n_test_splits))

    results = []

    for test_fold_indices in test_combinations:
        # Create test mask
        test_mask = np.zeros(n, dtype=bool)
        for fold_idx in test_fold_indices:
            start, end = folds[fold_idx]
            test_mask[start:end] = True

        # Create train mask with purging and embargo
        train_mask = ~test_mask.copy()

        # Purge: remove data just before test
        for fold_idx in test_fold_indices:
            start, _ = folds[fold_idx]
            purge_start = max(0, start - purge_bars)
            train_mask[purge_start:start] = False

        # Embargo: remove data just after test
        for fold_idx in test_fold_indices:
            _, end = folds[fold_idx]
            embargo_end = min(n, end + embargo_bars)
            train_mask[end:embargo_end] = False

        # Get train and test data
        train_data = df[train_mask]
        test_data = df[test_mask]

        # Evaluate
        train_metrics = strategy_func(train_data, **params)
        test_metrics = strategy_func(test_data, **params)

        results.append({
            'test_folds': test_fold_indices,
            'train_sharpe': train_metrics.get('sharpe', 0),
            'test_sharpe': test_metrics.get('sharpe', 0),
            'train_size': len(train_data),
            'test_size': len(test_data)
        })

    # Aggregate results
    avg_test_sharpe = np.mean([r['test_sharpe'] for r in results])
    std_test_sharpe = np.std([r['test_sharpe'] for r in results])
    profitable_combos = sum(1 for r in results if r['test_sharpe'] > 0)

    return {
        'avg_test_sharpe': avg_test_sharpe,
        'std_test_sharpe': std_test_sharpe,
        'profitable_ratio': profitable_combos / len(results),
        'total_combinations': len(results),
        'all_results': results
    }
```

## Examples

### Example 1: Complete WFO Workflow

```python
"""
Full walk-forward optimization workflow for a strategy.
"""
from lib.data import DatabentoService
from lib.backtest import WalkForwardOptimizer, WFOConfig

# 1. Fetch data (LIVE DATA - never hardcoded!)
databento = DatabentoService()
df = await databento.get_historical_ohlcv(
    symbol="ES.FUT",
    timeframe="15m",
    bars=50000  # ~2 years of 15-min bars
)

# 2. Define strategy function
def rsi_mean_reversion(df: pd.DataFrame, **params) -> dict:
    rsi_period = params.get('rsi_period', 14)
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)
    hold_bars = params.get('hold_bars', 4)

    # ... strategy logic ...

    return {
        'sharpe': sharpe,
        'sortino': sortino,
        'calmar': calmar,
        'trades': trades,
        'win_rate': win_rate,
        'max_dd': max_dd,
        'profit_factor': profit_factor
    }

# 3. Configure WFO
config = WFOConfig(
    is_bars=5040,     # 6 months of 15-min bars
    oos_bars=1260,    # 6 weeks OOS
    method="anchored",
    parameter_grid={
        'rsi_period': [7, 10, 14, 21],
        'oversold': [20, 25, 30, 35],
        'overbought': [65, 70, 75, 80],
        'hold_bars': [2, 4, 6, 8]
    },
    optimization_metric="sharpe",
    min_trades_per_period=50,
    min_oos_sharpe=0.5,
    max_oos_degradation=0.5
)

# 4. Run WFO
optimizer = WalkForwardOptimizer(rsi_mean_reversion, config)
results = optimizer.run(df)

# 5. Analyze results
print(results.to_report())

if results.is_valid():
    print("Strategy PASSED walk-forward validation!")

    # 6. Check parameter stability
    stability = results.parameter_stability
    for param, stats in stability.items():
        if stats['cv'] > 0.3:  # Coefficient of variation > 30%
            print(f"WARNING: {param} is unstable (CV={stats['cv']:.1%})")

    # 7. Get consensus parameters (mode or median)
    from statistics import mode, median
    consensus_params = {}
    for param in config.parameter_grid.keys():
        values = [p.optimal_params[param] for p in results.periods]
        try:
            consensus_params[param] = mode(values)
        except:
            consensus_params[param] = median(values)

    print(f"Consensus parameters: {consensus_params}")

else:
    print("Strategy FAILED walk-forward validation")
    print(f"Consistency: {results.consistency_ratio:.1%} (need >50%)")
    print(f"WFO Efficiency: {results.avg_wfo_efficiency:.1%} (need >50%)")
```

### Example 2: Comparing Anchored vs Rolling

```python
"""
Compare anchored vs rolling WFO to determine best method.
"""

# Run both methods
anchored_results = anchored_walk_forward(
    df=df,
    strategy_func=my_strategy,
    param_grid=param_grid,
    initial_is_bars=5040,
    oos_bars=1260
)

rolling_results = rolling_walk_forward(
    df=df,
    strategy_func=my_strategy,
    param_grid=param_grid,
    is_bars=5040,
    oos_bars=1260
)

# Compare results
comparison = {
    'Method': ['Anchored', 'Rolling'],
    'Consistency': [
        anchored_results.consistency_ratio,
        rolling_results.consistency_ratio
    ],
    'Avg OOS Sharpe': [
        anchored_results.avg_oos_sharpe,
        rolling_results.avg_oos_sharpe
    ],
    'WFO Efficiency': [
        anchored_results.avg_wfo_efficiency,
        rolling_results.avg_wfo_efficiency
    ]
}

print(pd.DataFrame(comparison))

# Decision logic
if anchored_results.avg_oos_sharpe > rolling_results.avg_oos_sharpe:
    print("Recommendation: Use ANCHORED method")
    print("More data appears to improve model")
else:
    print("Recommendation: Use ROLLING method")
    print("Recent data appears more relevant (regime changes)")
```

## Common Mistakes

### 1. OOS Too Short

```python
# WRONG: OOS period too short (not statistically significant)
config = WFOConfig(
    is_bars=5040,
    oos_bars=20,  # Only 20 bars! Not enough trades
    ...
)

# RIGHT: OOS long enough for meaningful statistics
config = WFOConfig(
    is_bars=5040,
    oos_bars=1260,  # ~6 weeks at 15-min, enough for 30+ trades
    min_trades_per_period=30,  # Enforce minimum
    ...
)
```

### 2. Data Leakage in Period Generation

```python
# WRONG: OOS periods overlap with subsequent IS
periods = []
for i in range(num_periods):
    is_end = i * step_size + is_bars
    oos_end = is_end + oos_bars
    # Next IS might start before current OOS ends!

# RIGHT: Ensure no overlap with purging
periods = []
current = 0
while current + is_bars + oos_bars + purge_bars <= n:
    is_data = df.iloc[current:current + is_bars]
    oos_data = df.iloc[current + is_bars + purge_bars:
                       current + is_bars + purge_bars + oos_bars]
    periods.append((is_data, oos_data))
    current = current + is_bars + purge_bars + oos_bars
```

### 3. Optimizing for Wrong Metric

```python
# WRONG: Optimizing for win rate
config = WFOConfig(
    optimization_metric="win_rate",  # Can lead to tiny profits, big losses
    ...
)

# RIGHT: Optimize for risk-adjusted returns
config = WFOConfig(
    optimization_metric="sharpe",  # Or "sortino", "calmar"
    ...
)
```

### 4. Ignoring Parameter Stability

```python
# WRONG: Just using best params from last period
final_params = results.periods[-1].optimal_params

# RIGHT: Check stability and use consensus
stability = results.parameter_stability
for param, stats in stability.items():
    if stats['cv'] > 0.5:  # 50% coefficient of variation
        print(f"REJECT: {param} too unstable across periods")
        # Don't deploy this strategy!
```

### 5. Too Many Parameters in Grid

```python
# WRONG: Combinatorial explosion
config = WFOConfig(
    parameter_grid={
        'param1': range(5, 50, 1),      # 45 values
        'param2': range(10, 100, 1),    # 90 values
        'param3': np.arange(0.1, 1, 0.01),  # 90 values
        # 45 * 90 * 90 = 364,500 combinations!
    }
)

# RIGHT: Coarse grid, then refine
config = WFOConfig(
    parameter_grid={
        'param1': [10, 15, 20, 25, 30],  # 5 values
        'param2': [20, 40, 60, 80],      # 4 values
        'param3': [0.2, 0.4, 0.6, 0.8],  # 4 values
        # 5 * 4 * 4 = 80 combinations
    }
)
```
