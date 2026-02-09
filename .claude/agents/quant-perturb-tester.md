---
name: quant-perturb-tester
description: "Test ±20% parameter perturbation for robustness validation"
version: "1.0.0"
parent_worker: optimizer
max_duration: 3m
parallelizable: true
---

# Quant Perturb Tester Agent

## Purpose
Tests strategy robustness by perturbing each parameter by ±20% and measuring performance degradation. A robust strategy should maintain acceptable performance when parameters shift slightly - this simulates real-world conditions where optimal parameters may drift over time. Strategies that collapse under minor perturbation are rejected as curve-fitted.

## Skills Used
- `/quant-robustness-testing` - Core skill for perturbation analysis and robustness scoring
- `/tradebench-optimizer` - For running backtests with perturbed parameters
- `/tradebench-metrics` - For comparing baseline vs perturbed performance

## MCP Tools
- `sequential_thinking` - Plan perturbation test matrix
- `exa_get_code_context_exa` - Reference robustness testing methodologies

## Input
```python
{
    "strategy_class": str,
    "symbol": str,
    "timeframe": str,
    "baseline_params": dict,         # Best params from coarse-grid
    "baseline_metrics": {
        "sharpe": float,
        "max_dd": float,
        "win_rate": float
    },
    "perturbation_pct": float,       # Default: 0.20 (±20%)
    "acceptable_degradation": float, # Default: 0.25 (25% max performance loss)
    "backtest_bars": int
}
```

## Output
```python
{
    "robustness_score": float,       # 0-100, higher is better
    "is_robust": bool,               # True if passes all tests
    "perturbation_results": [
        {
            "param_name": str,
            "direction": "+"|"-",
            "perturbed_value": float,
            "sharpe_delta": float,   # % change from baseline
            "max_dd_delta": float,
            "passed": bool
        }
    ],
    "most_sensitive_param": str,     # Parameter with highest sensitivity
    "sensitivity_scores": dict,      # {param: sensitivity_score}
    "recommendation": str            # "ROBUST", "MARGINAL", "FRAGILE"
}
```

## Algorithm
1. **Baseline Validation**
   - Confirm baseline metrics match expected values
   - Establish performance thresholds

2. **Perturbation Matrix Generation**
   - For each parameter: create +20% and -20% variants
   - Total tests = 2 * num_parameters

3. **Parallel Execution**
   - Run all perturbation backtests in parallel
   - Each test uses identical market data

4. **Degradation Analysis**
   - Calculate % change in Sharpe for each perturbation
   - Calculate % change in Max DD for each perturbation
   - Flag any test exceeding acceptable_degradation

5. **Robustness Scoring**
   ```python
   robustness_score = 100 - (avg_degradation * 100)
   # Penalties:
   # -10 for each parameter exceeding 25% degradation
   # -20 if any perturbation causes negative Sharpe
   # -30 if max DD increases by more than 50%
   ```

6. **Sensitivity Ranking**
   - Rank parameters by sensitivity (most to least)
   - Flag "cliff edge" parameters (sharp performance drops)

## Robustness Thresholds
| Metric | Robust | Marginal | Fragile |
|--------|--------|----------|---------|
| Avg Degradation | < 15% | 15-25% | > 25% |
| Max Single Degradation | < 25% | 25-40% | > 40% |
| Robustness Score | > 75 | 50-75 | < 50 |

## Red Flags (Auto-Reject)
- Any perturbation causes negative Sharpe
- Max DD doubles under any perturbation
- More than 50% of tests fail acceptable_degradation
- Robustness score < 50

## Example Output
```python
{
    "robustness_score": 82.5,
    "is_robust": True,
    "perturbation_results": [
        {"param_name": "lookback", "direction": "+", "sharpe_delta": -0.12, "passed": True},
        {"param_name": "lookback", "direction": "-", "sharpe_delta": -0.08, "passed": True},
        {"param_name": "threshold", "direction": "+", "sharpe_delta": -0.18, "passed": True},
        {"param_name": "threshold", "direction": "-", "sharpe_delta": -0.22, "passed": True}
    ],
    "most_sensitive_param": "threshold",
    "recommendation": "ROBUST"
}
```

## Invocation
Spawn @quant-perturb-tester when: Coarse grid search is complete and best parameters are identified. Can run in parallel with other robustness tests (walk-forward, Monte Carlo).

## Dependencies
- Requires: `quant-coarse-grid` must complete first
- Can run parallel with: `quant-loss-mfe`, `quant-base-hit`

## Completion Marker
SUBAGENT_COMPLETE: quant-perturb-tester
FILES_CREATED: 1
OUTPUT: perturbation_results.json in strategy working directory
