---
name: quant-parameter-optimization
description: "Coarse grid parameter optimization to prevent overfitting"
version: "1.0.0"
triggers:
  - "when optimizing strategy parameters"
  - "when running grid search"
  - "when selecting parameter values"
---

# Quant Parameter Optimization

## Purpose

Implements coarse-grid parameter optimization to find robust parameters without overfitting. Fine grids guarantee overfitting - coarse grids don't.

## When to Use

- When optimizing any strategy parameters
- After initial strategy validation
- When preparing for production deployment

## Core Principle: COARSE GRIDS ONLY

```python
# ❌ WRONG - Fine grid (OVERFITTING GUARANTEED)
RSI_PERIODS = [10, 11, 12, 13, 14, 15, 16]  # Too fine!

# ✅ CORRECT - Coarse grid (economically meaningful values)
RSI_PERIODS = [7, 10, 14, 21, 28]  # Standard periods only
```

## Standard Coarse Grids

| Parameter | Coarse Grid | Rationale |
|-----------|-------------|-----------|
| RSI Period | [7, 10, 14, 21, 28] | Standard TA values |
| EMA Period | [5, 10, 20, 50, 200] | Fibonacci/standard |
| ATR Multiplier | [1.0, 1.5, 2.0, 2.5, 3.0] | Meaningful risk levels |
| Lookback | [5, 10, 20, 50] | Trading weeks/days |
| Threshold | [0.5, 1.0, 1.5, 2.0] | Standard deviations |

## Implementation

```python
from itertools import product
from dataclasses import dataclass

@dataclass
class GridSearchConfig:
    """Configuration for coarse grid search."""
    param_grids: dict
    objective: str = 'sharpe'  # What to optimize
    min_trades: int = 100      # Minimum trades required

def coarse_grid_search(
    df: pd.DataFrame,
    strategy_class,
    config: GridSearchConfig
) -> dict:
    """
    Run coarse grid parameter search.

    Returns best parameters and all results.
    """
    results = []

    # Generate all combinations
    param_names = list(config.param_grids.keys())
    param_values = list(config.param_grids.values())

    for values in product(*param_values):
        params = dict(zip(param_names, values))

        # Run backtest
        strategy = strategy_class(**params)
        metrics = backtest(df, strategy)

        # Skip if insufficient trades
        if metrics['trades'] < config.min_trades:
            continue

        results.append({
            'params': params,
            'objective': metrics[config.objective],
            'metrics': metrics
        })

    # Find best
    if not results:
        raise ValueError("No valid parameter combinations found")

    best = max(results, key=lambda x: x['objective'])

    return {
        'best_params': best['params'],
        'best_objective': best['objective'],
        'all_results': results,
        'grid_size': len(results)
    }
```

## Anti-Overfitting Rules

1. **Maximum 5 values per parameter**
2. **Use economically meaningful values** (standard periods, round numbers)
3. **Never use consecutive integers** (10,11,12 is forbidden)
4. **Test robustness after** (±20% perturbation)

## Robustness Check

```python
def check_parameter_robustness(
    df: pd.DataFrame,
    strategy_class,
    optimal_params: dict,
    perturbation: float = 0.20
) -> dict:
    """
    Check if optimal parameters are robust to perturbation.

    ±20% change should not destroy profitability.
    """
    results = []

    for param, value in optimal_params.items():
        # Test -20%, 0%, +20%
        for mult in [1 - perturbation, 1.0, 1 + perturbation]:
            test_params = optimal_params.copy()
            test_params[param] = int(value * mult) if isinstance(value, int) else value * mult

            metrics = backtest(df, strategy_class(**test_params))
            results.append({
                'param': param,
                'multiplier': mult,
                'sharpe': metrics['sharpe']
            })

    # Calculate range ratio
    sharpes = [r['sharpe'] for r in results]
    range_ratio = (max(sharpes) - min(sharpes)) / np.mean(sharpes)

    return {
        'range_ratio': range_ratio,
        'is_robust': range_ratio < 0.30,  # <30% variation is robust
        'results': results
    }
```

## Red Flags

| Flag | Meaning | Action |
|------|---------|--------|
| Optimal at grid edge | True optimum outside range | Expand grid |
| Range ratio > 0.30 | Knife-edge optimum | REJECT |
| Single dominant param | Fragile strategy | Simplify |

## Related Skills

- `quant-robustness-testing` - ±20% perturbation testing
- `quant-overfitting-detection` - Red flag detection
