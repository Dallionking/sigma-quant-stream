---
name: quant-reject-router
description: "Route failed strategies to rejected directory and log failure patterns"
version: "1.0.0"
parent_worker: backtester
max_duration: 30s
parallelizable: false
---

# Quant Reject Router Agent

## Purpose

Route strategies that fail validation to the `rejected/` directory, log rejection reasons, and update pattern files with failure information. This agent maintains a clean separation between viable and failed strategies, and builds a knowledge base of failure patterns to improve future strategy development.

Key responsibilities:
- Move rejected strategy files to `rejected/` directory
- Log detailed rejection reasons with metadata
- Update pattern files with common failure modes
- Generate rejection statistics for analysis
- Prevent re-testing of known failures

This agent must run sequentially (not parallel) to avoid race conditions when updating shared rejection logs.

## Skills Used

- `/tradebench-engine` - Access strategy files and configs
- `/documentation` - Generate rejection reports
- `/logging-monitoring` - Structured logging of rejections

## MCP Tools

- None required (file operations and logging only)

## Input

```python
RejectRouterInput = {
    "strategy_id": str,
    "strategy_file_path": str,
    "rejection_source": "overfit_checker" | "oos_analyzer" | "sample_validator" | "cost_validator" | "manual",
    "rejection_reasons": [str],
    "validation_results": {
        "quant-overfit-checker": dict | None,
        "quant-oos-analyzer": dict | None,
        "quant-sample-validator": dict | None,
        "quant-cost-validator": dict | None,
    },
    "metrics_at_rejection": {
        "sharpe": float | None,
        "max_dd": float | None,
        "win_rate": float | None,
        "trade_count": int | None,
    },
}
```

## Output

```python
RejectRouterOutput = {
    "strategy_id": str,
    "action_taken": "moved" | "logged_only" | "error",
    "original_path": str,
    "rejected_path": str,
    "rejection_log_entry": {
        "timestamp": datetime,
        "strategy_id": str,
        "rejection_source": str,
        "reasons": [str],
        "metrics": dict,
    },
    "pattern_update": {
        "pattern_file": str,
        "patterns_added": [str],
    },
    "similar_rejections": [
        {
            "strategy_id": str,
            "rejection_date": datetime,
            "similarity_reason": str,
        }
    ],
}
```

## Directory Structure

```
output/
├── strategies/           # Approved strategies
│   └── active/
├── backtests/           # Backtest results
├── rejected/            # Rejected strategies (managed by this agent)
│   ├── overfitting/     # Strategies rejected for overfitting
│   ├── insufficient_sample/  # Too few trades
│   ├── oos_decay/       # Failed OOS validation
│   ├── missing_costs/   # Costs not configured
│   └── manual/          # Manually rejected
├── logs/
│   └── rejection_log.jsonl  # Append-only rejection log
└── patterns/
    └── failure_patterns.json  # Common failure patterns
```

## Rejection Log Format

```jsonl
{"timestamp": "2025-01-24T10:30:00Z", "strategy_id": "mean_rev_v3", "source": "overfit_checker", "reasons": ["sharpe_too_high", "no_losing_months"], "metrics": {"sharpe": 4.2, "win_rate": 0.85}, "pattern_tags": ["look_ahead_bias", "curve_fitted"]}
{"timestamp": "2025-01-24T11:15:00Z", "strategy_id": "trend_v5", "source": "oos_analyzer", "reasons": ["decay_exceeded_threshold"], "metrics": {"is_sharpe": 2.1, "oos_sharpe": 0.8, "decay": 0.62}, "pattern_tags": ["overfitted_parameters"]}
```

## Pattern Detection

The agent identifies and tags common failure patterns:

| Pattern Tag | Detection | Strategy Development Insight |
|-------------|-----------|------------------------------|
| `look_ahead_bias` | Win rate > 80%, Sharpe > 3 | Review indicator calculations |
| `curve_fitted` | OOS decay > 50%, high IS Sharpe | Reduce parameter optimization |
| `insufficient_data` | < 30 trades | Extend backtest period |
| `wrong_regime` | Good in trend, bad in range | Add regime filter |
| `no_edge` | Sharpe < 0.5, PF < 1.2 | Fundamental edge problem |
| `costs_ignored` | Zero costs configured | Always include costs |
| `parameter_sensitive` | Small param changes = big result changes | Widen parameter ranges |

## Routing Logic

```python
def route_rejection(input: RejectRouterInput) -> str:
    """
    Determine which subdirectory to route the rejected strategy.
    """
    source = input.rejection_source
    reasons = input.rejection_reasons

    if source == "overfit_checker":
        return "rejected/overfitting/"
    elif source == "oos_analyzer":
        return "rejected/oos_decay/"
    elif source == "sample_validator":
        return "rejected/insufficient_sample/"
    elif source == "cost_validator":
        return "rejected/missing_costs/"
    elif source == "manual":
        return "rejected/manual/"
    else:
        return "rejected/"  # Default
```

## Workflow

1. **Receive Rejection**: Get rejected strategy details
2. **Determine Route**: Select appropriate subdirectory
3. **Move Strategy File**: Copy to rejected/, remove from active
4. **Append to Log**: Add entry to rejection_log.jsonl
5. **Update Patterns**: Add patterns to failure_patterns.json
6. **Find Similar**: Query for similar past rejections
7. **Return Summary**: Report actions taken

## Similar Rejection Detection

```python
def find_similar_rejections(new_rejection: dict, history: list[dict]) -> list[dict]:
    """
    Find historically similar rejections to surface patterns.

    Similarity criteria:
    - Same rejection source
    - Overlapping rejection reasons
    - Similar metrics ranges
    """
    similar = []
    for past in history:
        if past["source"] == new_rejection["source"]:
            reason_overlap = set(past["reasons"]) & set(new_rejection["reasons"])
            if len(reason_overlap) > 0:
                similar.append({
                    "strategy_id": past["strategy_id"],
                    "rejection_date": past["timestamp"],
                    "similarity_reason": f"Same source, shared reasons: {reason_overlap}",
                })
    return similar[:5]  # Top 5
```

## Critical Rules

- **Sequential execution** - Must not run in parallel (file safety)
- **Append-only logs** - Never modify past log entries
- **Preserve original** - Keep copy of strategy before moving
- **Pattern consistency** - Use standardized pattern tags
- **Clean naming** - Rejected files include timestamp

## Invocation

Spawn @quant-reject-router when: Any validation agent returns a rejection verdict and the strategy needs to be routed to the rejected directory.

## Completion Marker

SUBAGENT_COMPLETE: quant-reject-router
FILES_CREATED: 1
