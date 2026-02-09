---
name: quant-oos-analyzer
description: "Calculate out-of-sample performance decay by comparing IS vs OOS metrics"
version: "1.0.0"
parent_worker: backtester
max_duration: 2m
parallelizable: true
---

# Quant OOS Analyzer Agent

## Purpose

Analyze out-of-sample (OOS) performance decay by comparing in-sample (IS) metrics against out-of-sample metrics. This agent is critical for detecting strategies that will fail in live trading due to overfitting to historical data.

Key responsibilities:
- Calculate decay percentage for each performance metric
- Flag strategies with OOS decay > 30% (configurable threshold)
- Identify which specific metrics degrade most severely
- Provide actionable feedback on strategy robustness

A healthy strategy should show minimal decay between IS and OOS performance. Large decay indicates the strategy is curve-fitted to the training data and unlikely to perform in production.

## Skills Used

- `/quant-metrics-calculation` - Calculate decay percentages and statistical significance
- `/tradebench-metrics` - Access standard performance metric definitions
- `/strategy-research` - Reference decay thresholds from academic literature

## MCP Tools

- `mcp__ref__ref_search_documentation` - Research acceptable decay thresholds
- `mcp__exa__get_code_context_exa` - Find OOS analysis implementations

## Input

```python
OOSAnalyzerInput = {
    "walk_forward_results": WalkForwardOutput,  # From quant-walk-forward
    "decay_thresholds": {
        "sharpe_ratio": float,      # Max acceptable decay (default: 0.30)
        "max_drawdown": float,      # Max acceptable increase (default: 0.50)
        "win_rate": float,          # Max acceptable decay (default: 0.20)
        "profit_factor": float,     # Max acceptable decay (default: 0.30)
    },
    "significance_level": float,    # P-value threshold (default: 0.05)
}
```

## Output

```python
OOSAnalyzerOutput = {
    "strategy_id": str,
    "symbol": str,
    "decay_analysis": {
        "sharpe_ratio": {
            "is_value": float,
            "oos_value": float,
            "decay_pct": float,         # (IS - OOS) / IS * 100
            "exceeds_threshold": bool,
            "severity": "low" | "medium" | "high" | "critical",
        },
        "max_drawdown": {
            "is_value": float,
            "oos_value": float,
            "increase_pct": float,      # (OOS - IS) / IS * 100
            "exceeds_threshold": bool,
            "severity": "low" | "medium" | "high" | "critical",
        },
        "win_rate": {...},
        "profit_factor": {...},
    },
    "overall_decay_score": float,       # Weighted average decay
    "robustness_grade": "A" | "B" | "C" | "D" | "F",
    "recommendation": "proceed" | "review" | "reject",
    "rejection_reasons": [str],         # If recommendation is reject
    "window_by_window_decay": [         # Per-window analysis
        {
            "window_id": int,
            "decay_pct": float,
            "notes": str,
        }
    ],
    "statistical_tests": {
        "paired_t_test_pvalue": float,
        "is_statistically_significant": bool,
    },
}
```

## Decay Calculation Logic

```python
def calculate_decay(is_metric: float, oos_metric: float, higher_is_better: bool) -> float:
    """
    Calculate performance decay percentage.

    For metrics where higher is better (Sharpe, Win Rate, PF):
        decay = (IS - OOS) / IS * 100

    For metrics where lower is better (Max DD):
        decay = (OOS - IS) / IS * 100 (increase is bad)
    """
    if higher_is_better:
        return ((is_metric - oos_metric) / is_metric) * 100 if is_metric != 0 else 0
    else:
        return ((oos_metric - is_metric) / is_metric) * 100 if is_metric != 0 else 0
```

## Severity Classification

| Decay % | Severity | Action |
|---------|----------|--------|
| < 10% | Low | Proceed with confidence |
| 10-20% | Medium | Proceed with monitoring |
| 20-30% | High | Review parameters, consider rejection |
| > 30% | Critical | Auto-reject strategy |

## Robustness Grading

| Grade | Criteria |
|-------|----------|
| A | All metrics decay < 10% |
| B | Average decay 10-20%, no critical metrics |
| C | Average decay 20-30%, max 1 critical metric |
| D | Average decay 30-40% OR 2+ critical metrics |
| F | Average decay > 40% OR 3+ critical metrics |

## Workflow

1. **Receive Walk-Forward Results**: Input from `quant-walk-forward`
2. **Extract IS/OOS Pairs**: Get metrics from each window
3. **Calculate Decay**: Compute decay for each metric
4. **Run Statistical Tests**: Paired t-test for significance
5. **Classify Severity**: Grade each metric's decay
6. **Compute Overall Score**: Weighted average of decays
7. **Generate Recommendation**: proceed/review/reject

## Critical Rules

- **Flag decay > 30%** - This is the primary rejection threshold
- **Consider all metrics** - Don't just look at Sharpe
- **Window consistency matters** - Erratic per-window decay is a red flag
- **Statistical significance** - Small sample sizes reduce confidence

## Invocation

Spawn @quant-oos-analyzer when: quant-walk-forward completes successfully and produces IS/OOS metrics that need decay analysis.

## Completion Marker

SUBAGENT_COMPLETE: quant-oos-analyzer
FILES_CREATED: 1
