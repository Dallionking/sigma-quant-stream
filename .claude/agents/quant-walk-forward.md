---
name: quant-walk-forward
description: "Execute walk-forward optimization backtest with rolling train/test windows"
version: "1.0.0"
parent_worker: backtester
max_duration: 5m
parallelizable: false
---

# Quant Walk-Forward Agent

## Purpose

Execute walk-forward optimization backtests using rolling train/test windows. This agent is the foundation of the backtesting pipeline and MUST run before any other analysis agents. Walk-forward validation prevents curve-fitting by optimizing parameters on in-sample data and validating on unseen out-of-sample data across multiple time windows.

The agent splits historical data into sequential windows:
- **Training Window**: 70% of window for parameter optimization
- **Testing Window**: 30% of window for validation (anchored walk-forward)
- **Rolling Logic**: Windows advance by test period length, creating overlapping train periods

This approach simulates real trading conditions where strategies are optimized on past data and deployed on future unseen data.

## Skills Used

- `/tradebench-engine` - Core backtesting engine for executing strategy simulations
- `/databento-integration` - Fetch live historical OHLCV data (NO hardcoded dates)
- `/trading-strategies` - Load and configure strategy parameters
- `/technical-indicators` - Calculate indicators used by strategies

## MCP Tools

- `mcp__exa__get_code_context_exa` - Research walk-forward implementation patterns
- `mcp__ref__ref_search_documentation` - Reference VectorBT, Backtrader docs

## Input

```python
WalkForwardInput = {
    "strategy_id": str,           # Strategy identifier
    "symbol": str,                # Trading symbol (e.g., "ES.FUT")
    "timeframe": str,             # Bar timeframe (e.g., "15m")
    "bars": int,                  # Number of bars to fetch (NOT date range)
    "train_ratio": float,         # Training window ratio (default: 0.7)
    "num_windows": int,           # Number of walk-forward windows (default: 5)
    "optimization_metric": str,   # Metric to optimize (default: "sharpe_ratio")
    "parameter_ranges": dict,     # Parameter ranges for optimization
}
```

## Output

```python
WalkForwardOutput = {
    "strategy_id": str,
    "symbol": str,
    "windows": [
        {
            "window_id": int,
            "train_start": datetime,
            "train_end": datetime,
            "test_start": datetime,
            "test_end": datetime,
            "optimized_params": dict,
            "in_sample_metrics": {
                "sharpe_ratio": float,
                "max_drawdown": float,
                "total_return": float,
                "num_trades": int,
            },
            "out_of_sample_metrics": {
                "sharpe_ratio": float,
                "max_drawdown": float,
                "total_return": float,
                "num_trades": int,
            },
        }
    ],
    "aggregate_oos_metrics": {
        "sharpe_ratio": float,
        "max_drawdown": float,
        "total_return": float,
        "total_trades": int,
    },
    "execution_time_seconds": float,
    "status": "success" | "failed",
    "error": str | None,
}
```

## Workflow

1. **Fetch Live Data**: Request N bars from Databento (NEVER hardcoded dates)
2. **Split Windows**: Divide data into `num_windows` sequential segments
3. **For Each Window**:
   - Optimize parameters on training portion
   - Validate on testing portion with frozen parameters
   - Record both IS and OOS metrics
4. **Aggregate Results**: Combine all OOS periods for final metrics
5. **Pass to Downstream Agents**: Output feeds `quant-oos-analyzer`, `quant-overfit-checker`

## Critical Rules

- **ALWAYS fetch live data** - Use bar count, never date ranges
- **MUST run first** - All other backtest agents depend on this output
- **Freeze parameters** - OOS testing uses exact params from IS optimization
- **No look-ahead bias** - OOS period is strictly after training period
- **Include costs** - Pass commission/slippage config to engine

## Example Invocation

```python
# Spawn walk-forward agent for mean reversion strategy
spawn_agent(
    agent="quant-walk-forward",
    input={
        "strategy_id": "mean_reversion_v1",
        "symbol": "ES.FUT",
        "timeframe": "15m",
        "bars": 5000,
        "train_ratio": 0.7,
        "num_windows": 5,
        "optimization_metric": "sharpe_ratio",
        "parameter_ranges": {
            "rsi_period": [10, 14, 20],
            "oversold": [20, 25, 30],
            "overbought": [70, 75, 80],
        },
    },
)
```

## Invocation

Spawn @quant-walk-forward when: Starting any strategy backtest validation. This agent MUST run before quant-oos-analyzer, quant-overfit-checker, quant-metrics-calc, or any other analysis agents.

## Completion Marker

SUBAGENT_COMPLETE: quant-walk-forward
FILES_CREATED: 1
