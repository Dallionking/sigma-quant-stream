---
name: quant-robustness-testing
description: "Parameter perturbation and stability testing for strategy robustness"
version: "1.0.0"
triggers:
  - "when validating parameter stability"
  - "when testing strategy robustness"
  - "before promoting strategies"
---

# Quant Robustness Testing

## Purpose

Tests whether strategy performance is stable under parameter perturbation. Robust strategies maintain profitability when parameters change slightly.

## When to Use

- After parameter optimization
- Before promoting to `good/` or `prop_firm_ready/`
- When validating strategy stability

## Core Concept

A robust strategy should survive ±20% parameter changes:

```
Optimal RSI = 14
Test with RSI = 11.2, 12.6, 14.0, 15.4, 16.8 (±20%)
All should be profitable!
```

## Robustness Criteria

| Metric | Robust | Marginal | Fragile |
|--------|--------|----------|---------|
| Range Ratio | < 0.20 | 0.20-0.30 | > 0.30 |
| Min Sharpe | > 0.5 | 0.0-0.5 | < 0.0 |
| All Profitable | Yes | 4 of 5 | < 4 of 5 |

## Implementation

```python
from dataclasses import dataclass
import numpy as np

@dataclass
class RobustnessResult:
    """Result of robustness testing."""
    is_robust: bool
    range_ratio: float
    min_sharpe: float
    max_sharpe: float
    mean_sharpe: float
    all_profitable: bool
    details: list

def test_robustness(
    df: pd.DataFrame,
    strategy_class,
    optimal_params: dict,
    perturbation: float = 0.20,
    n_tests: int = 5
) -> RobustnessResult:
    """
    Test parameter robustness with perturbation.

    Args:
        df: Market data
        strategy_class: Strategy class to test
        optimal_params: Optimal parameters to perturb
        perturbation: Perturbation range (0.20 = ±20%)
        n_tests: Number of test points per parameter
    """
    results = []

    # Generate perturbation multipliers
    multipliers = np.linspace(1 - perturbation, 1 + perturbation, n_tests)

    for param, base_value in optimal_params.items():
        for mult in multipliers:
            # Create perturbed params
            test_params = optimal_params.copy()
            perturbed = base_value * mult

            # Keep integers as integers
            if isinstance(base_value, int):
                perturbed = max(1, int(perturbed))

            test_params[param] = perturbed

            # Run backtest
            metrics = backtest(df, strategy_class(**test_params))

            results.append({
                'param': param,
                'base_value': base_value,
                'test_value': perturbed,
                'multiplier': mult,
                'sharpe': metrics['sharpe'],
                'win_rate': metrics['win_rate']
            })

    # Calculate aggregate metrics
    sharpes = [r['sharpe'] for r in results]

    range_ratio = (max(sharpes) - min(sharpes)) / np.mean(sharpes) if np.mean(sharpes) > 0 else float('inf')
    all_profitable = all(s > 0 for s in sharpes)

    return RobustnessResult(
        is_robust=range_ratio < 0.30 and all_profitable,
        range_ratio=range_ratio,
        min_sharpe=min(sharpes),
        max_sharpe=max(sharpes),
        mean_sharpe=np.mean(sharpes),
        all_profitable=all_profitable,
        details=results
    )
```

## Multi-Parameter Robustness

```python
def monte_carlo_robustness(
    df: pd.DataFrame,
    strategy_class,
    optimal_params: dict,
    n_simulations: int = 100,
    noise_std: float = 0.10
) -> dict:
    """
    Monte Carlo robustness testing.

    Randomly perturb all parameters simultaneously.
    """
    results = []

    for _ in range(n_simulations):
        # Perturb all params with random noise
        test_params = {}
        for param, value in optimal_params.items():
            noise = 1 + np.random.normal(0, noise_std)
            if isinstance(value, int):
                test_params[param] = max(1, int(value * noise))
            else:
                test_params[param] = value * noise

        metrics = backtest(df, strategy_class(**test_params))
        results.append(metrics['sharpe'])

    return {
        'mean_sharpe': np.mean(results),
        'std_sharpe': np.std(results),
        'pct_profitable': sum(1 for r in results if r > 0) / len(results),
        '5th_percentile': np.percentile(results, 5),
        'is_robust': np.percentile(results, 5) > 0  # 95% of variations profitable
    }
```

## Interpretation

| Result | Interpretation | Action |
|--------|----------------|--------|
| Range ratio < 0.20 | Very robust | ✅ Promote |
| Range ratio 0.20-0.30 | Marginally robust | Review carefully |
| Range ratio > 0.30 | Fragile | ❌ REJECT |
| Any Sharpe < 0 | Knife-edge | ❌ REJECT |

## Related Skills

- `quant-parameter-optimization` - Coarse grid search
- `quant-overfitting-detection` - Red flag detection
