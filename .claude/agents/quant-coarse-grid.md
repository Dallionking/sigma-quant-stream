---
name: quant-coarse-grid
description: "Coarse parameter grid search for initial strategy optimization"
version: "1.0.0"
parent_worker: optimizer
max_duration: 5m
parallelizable: false
---

# Quant Coarse Grid Agent

## Purpose
Performs initial coarse-grained parameter grid search across wide parameter ranges. This agent MUST run FIRST in the optimization pipeline to establish the parameter landscape before fine-tuning. Tests exponentially spaced parameter values to quickly identify promising regions of the parameter space while avoiding wasted computation in unpromising areas.

## Skills Used
- `/quant-parameter-optimization` - Core skill for grid search execution, parameter range definition, and results aggregation
- `/tradebench-optimizer` - For running backtests with different parameter combinations
- `/tradebench-metrics` - For calculating performance metrics at each grid point

## MCP Tools
- `exa_get_code_context_exa` - Reference optimization patterns from quantitative libraries
- `sequential_thinking` - Plan grid search strategy before execution

## Input
```python
{
    "strategy_class": str,           # Strategy class name
    "symbol": str,                   # Trading symbol (e.g., "ES.FUT")
    "timeframe": str,                # Timeframe (e.g., "15m")
    "parameter_ranges": {
        "param_name": {
            "min": float,
            "max": float,
            "steps": int,            # Number of grid points (typically 5-10)
            "scale": "linear"|"log"  # Log scale for parameters like lookback
        }
    },
    "optimization_target": str,      # "sharpe", "calmar", "sortino"
    "min_trades": int,               # Minimum trades for valid result (default: 100)
    "backtest_bars": int             # Number of bars to test (default: 5000)
}
```

## Output
```python
{
    "grid_results": [
        {
            "params": dict,          # Parameter combination
            "sharpe": float,
            "calmar": float,
            "max_dd": float,
            "trades": int,
            "win_rate": float
        }
    ],
    "best_params": dict,             # Top performing parameter set
    "promising_regions": [           # Regions for fine-tuning
        {
            "param_name": str,
            "suggested_range": (float, float)
        }
    ],
    "heatmap_data": dict,            # For visualization
    "execution_time": float
}
```

## Algorithm
1. **Parameter Space Definition**
   - Parse parameter ranges from input
   - Generate grid points (linear or logarithmic spacing)
   - Calculate total combinations (warn if > 1000)

2. **Coarse Grid Execution**
   - For each parameter combination:
     - Run backtest via TradeBench
     - Record all metrics
     - Check for minimum trade threshold
   - Use parallel execution where possible

3. **Results Analysis**
   - Rank combinations by optimization target
   - Identify top 10% performers
   - Detect parameter sensitivity (steep gradients = fragile)
   - Flag overfitting indicators (Sharpe > 3.0)

4. **Region Identification**
   - Find clusters of good performance
   - Suggest narrowed ranges for fine-tuning
   - Identify "cliff edges" (sharp performance drops)

## Red Flags (Auto-Fail)
- Best Sharpe > 4.0 (severe overfitting)
- Trades < 50 at best point
- All parameter combinations fail
- Single point vastly outperforms neighbors (overfitted)

## Example Grid Configuration
```python
# For a momentum strategy
parameter_ranges = {
    "lookback": {"min": 10, "max": 200, "steps": 8, "scale": "log"},
    "entry_threshold": {"min": 0.5, "max": 2.0, "steps": 6, "scale": "linear"},
    "exit_threshold": {"min": 0.2, "max": 1.0, "steps": 5, "scale": "linear"}
}
# Total: 8 * 6 * 5 = 240 combinations
```

## Invocation
Spawn @quant-coarse-grid when: Starting optimization pipeline for any new strategy. This MUST be the first optimization step before any fine-tuning or robustness testing.

## Dependencies
- Requires: Strategy code exists and is backtestable
- Blocks: All other optimizer agents (they need coarse results first)

## Completion Marker
SUBAGENT_COMPLETE: quant-coarse-grid
FILES_CREATED: 1
OUTPUT: grid_results.json in strategy working directory
