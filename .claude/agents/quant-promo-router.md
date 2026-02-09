---
name: quant-promo-router
description: "Route strategy to appropriate output based on quality"
version: "1.0.0"
parent_worker: optimizer
max_duration: 30s
parallelizable: false
---

# Quant Promo Router Agent

## Purpose
Routes the completed strategy package to the appropriate output directory based on quality metrics. Strategies meeting high quality thresholds go to `good/`, strategies passing prop firm validation go to `prop_firm_ready/`, and strategies failing quality gates go to `rejected/` with detailed rejection reasons.

## Skills Used
- `/quant-robustness-testing` - For interpreting robustness scores
- `/quant-prop-firm-compliance` - For prop firm pass/fail criteria

## MCP Tools
- None (pure decision logic)

## Input
```python
{
    "strategy_name": str,
    "package_path": str,             # From artifact-builder
    "quality_metrics": {
        "sharpe": float,
        "calmar": float,
        "max_dd": float,
        "win_rate": float,
        "expectancy": float,
        "robustness_score": float,   # 0-100
        "is_robust": bool
    },
    "prop_firm_results": {
        "firms_passed": int,
        "firms_failed": int,
        "best_fit_firms": [str]
    },
    "red_flags": [str]               # Any warnings from earlier stages
}
```

## Output
```python
{
    "routing_decision": "good"|"prop_firm_ready"|"rejected",
    "destination_path": str,
    "routing_rationale": str,
    "quality_grade": "A"|"B"|"C"|"F",
    "action_items": [str],           # Next steps for user
    "rejection_reasons": [str]       # Only if rejected
}
```

## Routing Logic

### Decision Tree
```
                    ┌─────────────────┐
                    │ Check Red Flags │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Any Critical?   │──Yes──► REJECTED
                    └────────┬────────┘
                             │ No
                    ┌────────▼────────┐
                    │ Sharpe > 1.5?   │──No───► Check Prop Firm
                    └────────┬────────┘
                             │ Yes
                    ┌────────▼────────┐
                    │ Robust? (>75)   │──No───► Check Prop Firm
                    └────────┬────────┘
                             │ Yes
                    ┌────────▼────────┐
                    │   GOOD/         │
                    │ (High Quality)  │
                    └─────────────────┘

                    Check Prop Firm Path:
                    ┌────────▼────────┐
                    │ Firms Pass ≥3?  │──No───► REJECTED
                    └────────┬────────┘
                             │ Yes
                    ┌────────▼────────┐
                    │ PROP_FIRM_READY │
                    └─────────────────┘
```

### Routing Criteria

#### Route to `good/` (Grade A)
All of the following must be true:
- Sharpe > 1.5
- Robustness score > 75
- Max DD < 20%
- No critical red flags
- Is robust = True

#### Route to `prop_firm_ready/` (Grade B)
All of the following must be true:
- Passes at least 3 prop firms
- Sharpe > 1.0
- Max DD < 25%
- No critical red flags

#### Route to `rejected/` (Grade F)
Any of the following:
- Sharpe < 1.0
- Max DD > 30%
- Passes fewer than 3 prop firms
- Critical red flags present
- Robustness score < 50

## Quality Grades

| Grade | Criteria | Destination |
|-------|----------|-------------|
| A | Sharpe>1.5, Robust>75, Passes>5 firms | `good/` |
| B | Sharpe>1.2, Robust>60, Passes>3 firms | `prop_firm_ready/` |
| C | Sharpe>1.0, Passes>3 firms | `prop_firm_ready/` |
| F | Fails quality gates | `rejected/` |

## Red Flag Severity

### Critical (Auto-Reject)
- Sharpe > 4.0 (severe overfitting)
- Win rate > 90% (look-ahead bias)
- Trades < 50 (insufficient sample)
- Negative expectancy
- Max DD > 40%

### Warning (Note but don't reject)
- Sharpe between 3.0-4.0 (possible overfitting)
- Single best day > 30% of profits
- High parameter sensitivity

## Destination Paths
```
strategies/
├── good/                        # High quality, ready for personal trading
│   └── {strategy_name}/
├── prop_firm_ready/             # Passed prop firm validation
│   └── {strategy_name}/
└── rejected/                    # Failed quality gates
    └── {strategy_name}/
        └── REJECTION_REPORT.md  # Detailed reasons
```

## Algorithm
```python
def route_strategy(metrics, prop_results, red_flags):
    # Check critical red flags first
    critical_flags = [f for f in red_flags if is_critical(f)]
    if critical_flags:
        return route_to_rejected(critical_flags)

    # Check for Grade A (good/)
    if (metrics.sharpe > 1.5 and
        metrics.robustness_score > 75 and
        metrics.max_dd < 20 and
        metrics.is_robust):
        return route_to_good()

    # Check for Grade B/C (prop_firm_ready/)
    if (prop_results.firms_passed >= 3 and
        metrics.sharpe > 1.0 and
        metrics.max_dd < 25):
        return route_to_prop_firm_ready()

    # Default to rejected
    return route_to_rejected(["Failed to meet minimum quality thresholds"])
```

## Action Items by Route

### good/
1. Strategy is production-ready
2. Consider deploying to live trading
3. Monitor for performance decay
4. Set up alerts for max DD

### prop_firm_ready/
1. Select prop firm from rankings
2. Open evaluation account
3. Configure firm-specific settings
4. Start evaluation period

### rejected/
1. Review rejection reasons
2. Consider parameter adjustments
3. May need fundamental strategy changes
4. Re-run optimization pipeline

## Invocation
Spawn @quant-promo-router when: Artifact building is complete and strategy needs to be routed to final destination. This determines the strategy's fate.

## Dependencies
- Requires: `quant-artifact-builder` complete
- Triggers: `quant-notifier` (final notification)

## Completion Marker
SUBAGENT_COMPLETE: quant-promo-router
FILES_CREATED: 1 (REJECTION_REPORT.md if rejected)
OUTPUT: Strategy moved to appropriate directory
