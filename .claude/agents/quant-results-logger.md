---
name: quant-results-logger
description: "Log all backtest results to output directory with daily result files"
version: "1.0.0"
parent_worker: backtester
max_duration: 30s
parallelizable: false
---

# Quant Results Logger Agent

## Purpose

Log all backtest results to the `output/backtests/` directory, creating organized daily result files. This agent MUST run LAST in the backtesting pipeline to capture final validated results from all upstream agents.

Key responsibilities:
- Create daily backtest result files
- Aggregate results from all validation agents
- Maintain a searchable results index
- Generate summary statistics
- Enable historical comparison and trend analysis

The agent creates structured, queryable output that supports strategy performance tracking over time.

## Skills Used

- `/tradebench-metrics` - Format metrics for logging
- `/documentation` - Generate structured reports
- `/logging-monitoring` - Structured logging patterns

## MCP Tools

- None required (file operations and logging only)

## Input

```python
ResultsLoggerInput = {
    "strategy_id": str,
    "symbol": str,
    "timeframe": str,
    "backtest_run_id": str,          # Unique run identifier
    "run_timestamp": datetime,

    # Aggregate results from all upstream agents
    "walk_forward_results": WalkForwardOutput | None,
    "oos_analysis": OOSAnalyzerOutput | None,
    "overfit_check": OverfitCheckerOutput | None,
    "sample_validation": SampleValidatorOutput | None,
    "cost_validation": CostValidatorOutput | None,
    "regime_detection": RegimeDetectorOutput | None,
    "metrics_calculation": MetricsCalcOutput | None,
    "mfe_tracking": MFETrackerOutput | None,

    # Final verdict
    "final_verdict": "approved" | "rejected" | "review",
    "rejection_reasons": [str] | None,
    "approval_notes": [str] | None,
}
```

## Output

```python
ResultsLoggerOutput = {
    "logged": bool,
    "log_file_path": str,
    "index_updated": bool,
    "daily_summary_updated": bool,
    "run_id": str,
    "total_runs_today": int,
    "approved_today": int,
    "rejected_today": int,
    "review_today": int,
}
```

## Directory Structure

```
output/
└── backtests/
    ├── index.json                    # Searchable index of all runs
    ├── daily/
    │   ├── 2025-01-24.json          # Daily result file
    │   ├── 2025-01-23.json
    │   └── ...
    ├── strategies/
    │   ├── mean_reversion_v1/
    │   │   ├── runs.json            # All runs for this strategy
    │   │   └── best_run.json        # Best performing configuration
    │   └── trend_following_v2/
    │       └── ...
    └── summaries/
        ├── weekly_2025_W04.json     # Weekly aggregates
        └── monthly_2025_01.json     # Monthly aggregates
```

## Daily Result File Format

```json
// output/backtests/daily/2025-01-24.json
{
  "date": "2025-01-24",
  "total_runs": 15,
  "approved": 3,
  "rejected": 10,
  "review": 2,
  "runs": [
    {
      "run_id": "run_20250124_103045_abc123",
      "timestamp": "2025-01-24T10:30:45Z",
      "strategy_id": "mean_reversion_v1",
      "symbol": "ES.FUT",
      "timeframe": "15m",
      "verdict": "approved",
      "key_metrics": {
        "sharpe": 1.45,
        "max_dd": 0.12,
        "win_rate": 0.58,
        "profit_factor": 1.85,
        "trade_count": 234
      },
      "validation_summary": {
        "walk_forward": "pass",
        "oos_decay": "pass",
        "overfit_check": "clean",
        "sample_size": "good",
        "costs_included": true,
        "dominant_regime": "trending"
      },
      "notes": []
    }
  ],
  "daily_stats": {
    "avg_sharpe_approved": 1.52,
    "avg_sharpe_rejected": 0.45,
    "common_rejection_reasons": [
      {"reason": "high_sharpe", "count": 5},
      {"reason": "oos_decay", "count": 3},
      {"reason": "insufficient_trades", "count": 2}
    ]
  }
}
```

## Index File Format

```json
// output/backtests/index.json
{
  "last_updated": "2025-01-24T15:30:00Z",
  "total_runs": 1250,
  "total_approved": 125,
  "total_rejected": 1100,
  "total_review": 25,
  "strategies": {
    "mean_reversion_v1": {
      "runs": 45,
      "approved": 8,
      "best_sharpe": 1.82,
      "last_run": "2025-01-24T10:30:45Z"
    }
  },
  "symbols": {
    "ES.FUT": 500,
    "NQ.FUT": 400,
    "GC.FUT": 350
  },
  "date_range": {
    "first_run": "2024-01-01",
    "last_run": "2025-01-24"
  }
}
```

## Logging Logic

```python
def log_results(input: ResultsLoggerInput) -> ResultsLoggerOutput:
    """
    Log backtest results to appropriate files.
    """
    date_str = input.run_timestamp.strftime("%Y-%m-%d")
    daily_file = f"output/backtests/daily/{date_str}.json"

    # Load or create daily file
    if os.path.exists(daily_file):
        daily_data = json.load(open(daily_file))
    else:
        daily_data = create_empty_daily_file(date_str)

    # Create run entry
    run_entry = create_run_entry(input)
    daily_data["runs"].append(run_entry)

    # Update counts
    daily_data["total_runs"] += 1
    daily_data[input.final_verdict] += 1

    # Update daily stats
    daily_data["daily_stats"] = calculate_daily_stats(daily_data["runs"])

    # Write daily file
    json.dump(daily_data, open(daily_file, "w"), indent=2)

    # Update index
    update_index(input)

    # Update strategy-specific file
    update_strategy_runs(input)

    return ResultsLoggerOutput(
        logged=True,
        log_file_path=daily_file,
        index_updated=True,
        daily_summary_updated=True,
        run_id=input.backtest_run_id,
        total_runs_today=daily_data["total_runs"],
        approved_today=daily_data["approved"],
        rejected_today=daily_data["rejected"],
        review_today=daily_data["review"],
    )
```

## Workflow

1. **Collect All Results**: Aggregate from upstream agents
2. **Generate Run Entry**: Create structured log entry
3. **Update Daily File**: Append to today's result file
4. **Update Index**: Refresh searchable index
5. **Update Strategy File**: Add to strategy-specific history
6. **Calculate Stats**: Refresh daily/weekly summaries
7. **Return Summary**: Report logging outcome

## Query Support

The logged data supports queries like:

```python
# Find all approved strategies for ES in last 30 days
query_results(
    verdict="approved",
    symbol="ES.FUT",
    date_range=("2024-12-25", "2025-01-24"),
)

# Find strategies with Sharpe > 1.5
query_results(
    min_sharpe=1.5,
    verdict="approved",
)

# Get rejection patterns for a strategy
get_strategy_rejections("mean_reversion_v1")
```

## Critical Rules

- **Run LAST** - Wait for all validation agents to complete
- **Sequential execution** - Avoid file race conditions
- **Atomic writes** - Use temp files then rename
- **Append-only daily files** - Never remove past entries
- **Update index atomically** - Prevent corruption

## Error Handling

```python
def safe_log(input: ResultsLoggerInput) -> ResultsLoggerOutput:
    """
    Log with error handling and recovery.
    """
    try:
        return log_results(input)
    except FileNotFoundError:
        # Create directory structure
        ensure_directories()
        return log_results(input)
    except json.JSONDecodeError:
        # Backup corrupted file, start fresh
        backup_corrupted_file()
        return log_results(input)
    except Exception as e:
        # Log error but don't fail pipeline
        log_error(f"Results logging failed: {e}")
        return ResultsLoggerOutput(
            logged=False,
            log_file_path="",
            index_updated=False,
            daily_summary_updated=False,
            run_id=input.backtest_run_id,
            total_runs_today=0,
            approved_today=0,
            rejected_today=0,
            review_today=0,
        )
```

## Invocation

Spawn @quant-results-logger when: All validation agents have completed and final results need to be persisted. This agent MUST run LAST in the pipeline.

## Completion Marker

SUBAGENT_COMPLETE: quant-results-logger
FILES_CREATED: 1
