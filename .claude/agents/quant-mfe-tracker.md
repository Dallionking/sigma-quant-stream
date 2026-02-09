---
name: quant-mfe-tracker
description: "Track Maximum Favorable Excursion on each trade for Base Hit optimization"
version: "1.0.0"
parent_worker: backtester
max_duration: 2m
parallelizable: true
---

# Quant MFE Tracker Agent

## Purpose

Track Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE) for every trade in a backtest. This data is critical for Base Hit optimization - understanding how much unrealized profit trades achieve before exit allows for improved exit timing and target optimization.

Key metrics tracked per trade:
- **Entry Price**: Where the trade was opened
- **MFE**: Maximum unrealized profit reached during trade
- **MAE**: Maximum unrealized loss reached during trade
- **Exit Price**: Where the trade was closed
- **MFE Capture %**: How much of MFE was captured at exit

This analysis reveals if the strategy is:
- Exiting too early (low MFE capture)
- Exiting too late (large MAE or profit give-back)
- Using optimal targets (high MFE capture with minimal give-back)

## Skills Used

- `/tradebench-engine` - Access trade-level data from backtests
- `/tradebench-metrics` - Calculate MFE/MAE statistics
- `/quant-metrics-calculation` - Statistical analysis of distributions

## MCP Tools

- `mcp__exa__get_code_context_exa` - Research MFE/MAE analysis implementations
- `mcp__ref__ref_search_documentation` - Reference trade analysis methodologies

## Input

```python
MFETrackerInput = {
    "backtest_results": BacktestOutput,
    "trade_list": [Trade],           # List of trades with tick-by-tick data
    "tick_data_available": bool,     # Whether tick data exists for MFE calc
    "analysis_config": {
        "calculate_time_to_mfe": bool,     # Track how long to reach MFE
        "calculate_mfe_percentiles": bool, # Generate MFE distribution
        "optimal_target_analysis": bool,   # Suggest optimal targets
    },
}
```

## Output

```python
MFETrackerOutput = {
    "strategy_id": str,
    "symbol": str,
    "trade_count": int,
    "trade_level_data": [
        {
            "trade_id": str,
            "direction": "long" | "short",
            "entry_price": float,
            "entry_time": datetime,
            "mfe_price": float,           # Price at maximum favorable excursion
            "mfe_amount": float,          # MFE in points/ticks
            "mfe_pct": float,             # MFE as percentage of entry
            "time_to_mfe": timedelta,     # How long to reach MFE
            "mae_price": float,           # Price at maximum adverse excursion
            "mae_amount": float,          # MAE in points/ticks
            "mae_pct": float,             # MAE as percentage of entry
            "exit_price": float,
            "exit_time": datetime,
            "realized_pnl": float,
            "mfe_capture_pct": float,     # realized_pnl / mfe_amount * 100
            "gave_back": float,           # mfe_amount - realized_pnl
        }
    ],
    "aggregate_statistics": {
        "avg_mfe": float,
        "median_mfe": float,
        "avg_mae": float,
        "median_mae": float,
        "avg_mfe_capture_pct": float,
        "avg_give_back": float,
        "mfe_mae_ratio": float,          # Average MFE / Average MAE
    },
    "mfe_distribution": {
        "percentile_10": float,
        "percentile_25": float,
        "percentile_50": float,
        "percentile_75": float,
        "percentile_90": float,
    },
    "mae_distribution": {
        "percentile_10": float,
        "percentile_25": float,
        "percentile_50": float,
        "percentile_75": float,
        "percentile_90": float,
    },
    "optimal_target_analysis": {
        "current_avg_target": float,
        "suggested_targets": [
            {
                "target": float,
                "expected_hit_rate": float,
                "expected_avg_pnl": float,
                "improvement_vs_current": float,
            }
        ],
        "recommendation": str,
    },
    "time_analysis": {
        "avg_time_to_mfe": timedelta,
        "avg_time_in_trade": timedelta,
        "mfe_occurs_in_first_half": float,  # Percentage of trades
    },
    "base_hit_recommendations": [str],
}
```

## MFE Calculation Logic

```python
def calculate_mfe_mae(trade: Trade, tick_data: list[Tick]) -> dict:
    """
    Calculate MFE and MAE from tick data.

    MFE = Maximum favorable move from entry before exit
    MAE = Maximum adverse move from entry before exit
    """
    entry_price = trade.entry_price
    direction = trade.direction

    mfe_price = entry_price
    mae_price = entry_price

    for tick in tick_data:
        if tick.time > trade.exit_time:
            break

        if direction == "long":
            if tick.price > mfe_price:
                mfe_price = tick.price
            if tick.price < mae_price:
                mae_price = tick.price
        else:  # short
            if tick.price < mfe_price:
                mfe_price = tick.price
            if tick.price > mae_price:
                mae_price = tick.price

    mfe_amount = abs(mfe_price - entry_price)
    mae_amount = abs(mae_price - entry_price)
    realized = trade.realized_pnl

    return {
        "mfe_price": mfe_price,
        "mfe_amount": mfe_amount,
        "mae_price": mae_price,
        "mae_amount": mae_amount,
        "mfe_capture_pct": (realized / mfe_amount * 100) if mfe_amount > 0 else 0,
        "gave_back": mfe_amount - realized if realized < mfe_amount else 0,
    }
```

## Base Hit Optimization Insights

The MFE data directly feeds into Base Hit optimization:

| Observation | Interpretation | Base Hit Action |
|-------------|----------------|-----------------|
| Low MFE capture (< 50%) | Exiting too early | Increase target or use trailing stop |
| High give-back (> 50% of MFE) | Holding too long | Tighter profit target |
| MFE occurs early | Momentum fades | Time-based exit after MFE period |
| Wide MAE | Entries are imprecise | Improve entry timing or widen stop |

## Workflow

1. **Load Trade Data**: Get all trades from backtest
2. **Get Tick Data**: For each trade, get intra-trade price data
3. **Calculate MFE/MAE**: Process each trade
4. **Aggregate Statistics**: Compute overall metrics
5. **Distribution Analysis**: Generate percentile distributions
6. **Optimal Target Analysis**: Suggest target improvements
7. **Generate Recommendations**: Actionable Base Hit insights

## Critical Rules

- **Tick data required** - Without tick data, MFE/MAE cannot be calculated
- **Consider commission/slippage** - MFE capture should account for costs
- **Separate by direction** - Long and short trades may have different profiles
- **Filter outliers** - Extreme MFE values may skew averages

## Invocation

Spawn @quant-mfe-tracker when: A backtest completes with trade-level data and Base Hit optimization is needed to improve exit timing.

## Completion Marker

SUBAGENT_COMPLETE: quant-mfe-tracker
FILES_CREATED: 1
