---
name: quant-overfit-checker
description: "Detect overfitting signals and auto-reject suspicious strategies"
version: "1.0.0"
parent_worker: backtester
max_duration: 1m
parallelizable: true
---

# Quant Overfit Checker Agent

## Purpose

Detect classic overfitting signals in backtest results and auto-reject strategies that exhibit suspicious performance characteristics. This agent acts as a critical gatekeeper preventing curve-fitted strategies from reaching production.

Key overfitting signals detected:
- **Sharpe Ratio > 3.0** - Unrealistically high risk-adjusted returns
- **Win Rate > 80%** - Suggests look-ahead bias or cherry-picked conditions
- **No Losing Months** - Impossibly consistent performance
- **Perfect Equity Curve** - Suspiciously smooth returns
- **Parameter Sensitivity** - Extreme sensitivity to small param changes

Any single critical signal triggers automatic rejection. Multiple warning signals combined also trigger rejection.

## Skills Used

- `/quant-overfitting-detection` - Core overfitting detection algorithms
- `/tradebench-metrics` - Access performance metrics for analysis
- `/strategy-research` - Reference academic overfitting literature

## MCP Tools

- `mcp__ref__ref_search_documentation` - Research overfitting detection methods
- `mcp__exa__get_code_context_exa` - Find academic papers on backtest overfitting

## Input

```python
OverfitCheckerInput = {
    "backtest_results": BacktestOutput,      # Full backtest results
    "walk_forward_results": WalkForwardOutput,  # Optional: WF results
    "thresholds": {
        "max_sharpe": float,            # Default: 3.0
        "max_win_rate": float,          # Default: 0.80
        "max_consecutive_wins": int,    # Default: 20
        "min_losing_months_pct": float, # Default: 0.10 (at least 10% losing months)
        "max_profit_factor": float,     # Default: 5.0
        "min_trades_per_month": int,    # Default: 3
    },
    "check_parameter_sensitivity": bool,  # Default: true
}
```

## Output

```python
OverfitCheckerOutput = {
    "strategy_id": str,
    "symbol": str,
    "verdict": "clean" | "suspicious" | "rejected",
    "confidence": float,                # 0-1 confidence in verdict
    "signals_detected": [
        {
            "signal_type": str,         # e.g., "high_sharpe", "no_losing_months"
            "severity": "warning" | "critical",
            "observed_value": float,
            "threshold": float,
            "description": str,
        }
    ],
    "auto_reject": bool,
    "rejection_reason": str | None,
    "recommendations": [str],           # How to improve if suspicious
    "detailed_analysis": {
        "sharpe_analysis": {
            "value": float,
            "is_suspicious": bool,
            "notes": str,
        },
        "win_rate_analysis": {
            "value": float,
            "is_suspicious": bool,
            "notes": str,
        },
        "monthly_returns_analysis": {
            "losing_months_pct": float,
            "max_consecutive_wins": int,
            "is_suspicious": bool,
            "notes": str,
        },
        "parameter_sensitivity": {
            "was_checked": bool,
            "sensitivity_score": float,  # 0-1, higher = more sensitive
            "is_suspicious": bool,
            "notes": str,
        },
    },
}
```

## Overfitting Detection Rules

### Critical Signals (Auto-Reject)

| Signal | Threshold | Reason |
|--------|-----------|--------|
| Sharpe Ratio > 3.0 | `sharpe > 3.0` | Unrealistic returns; likely curve-fitted |
| Win Rate > 80% | `win_rate > 0.80` | Look-ahead bias or data snooping |
| No Losing Months | `losing_months == 0` | Impossible in real markets |
| Profit Factor > 5.0 | `pf > 5.0` | Too good to be true |
| Max Consecutive Wins > 30 | `consec_wins > 30` | Suggests artificial conditions |

### Warning Signals (Review Required)

| Signal | Threshold | Notes |
|--------|-----------|-------|
| Sharpe 2.5-3.0 | `2.5 < sharpe <= 3.0` | Unusually high but possible |
| Win Rate 70-80% | `0.70 < wr <= 0.80` | High but not impossible |
| < 5% Losing Months | `losing_pct < 0.05` | Very consistent |
| Low Trade Frequency | `trades/month < 3` | May not have enough samples |
| High Parameter Sensitivity | `sensitivity > 0.7` | Results change significantly with small param changes |

## Parameter Sensitivity Check

When `check_parameter_sensitivity` is true, the agent:

1. Perturbs each parameter by +/- 10%
2. Re-runs backtest with perturbed params
3. Measures change in Sharpe ratio
4. Flags if Sharpe changes > 50% with small param changes

```python
def check_sensitivity(strategy, params, base_sharpe):
    """Check if strategy is overly sensitive to parameter changes."""
    sensitivity_scores = []

    for param, value in params.items():
        # Test +10% perturbation
        perturbed = {**params, param: value * 1.10}
        new_sharpe = backtest(strategy, perturbed)
        change = abs(new_sharpe - base_sharpe) / base_sharpe
        sensitivity_scores.append(change)

    return np.mean(sensitivity_scores)
```

## Verdict Logic

```python
def determine_verdict(signals):
    critical_count = sum(1 for s in signals if s["severity"] == "critical")
    warning_count = sum(1 for s in signals if s["severity"] == "warning")

    if critical_count >= 1:
        return "rejected", True
    elif warning_count >= 3:
        return "rejected", True  # Multiple warnings = rejection
    elif warning_count >= 1:
        return "suspicious", False
    else:
        return "clean", False
```

## Workflow

1. **Receive Backtest Results**: Input from backtesting engine
2. **Check Critical Signals**: Immediate rejection if any found
3. **Check Warning Signals**: Accumulate warning count
4. **Run Parameter Sensitivity**: Optional deep check
5. **Determine Verdict**: Apply verdict logic
6. **Generate Recommendations**: If suspicious, suggest fixes

## Critical Rules

- **Auto-reject on ANY critical signal** - No exceptions
- **3+ warnings = rejection** - Combined warnings indicate problems
- **Document rejection reason** - Clear logging for later review
- **Consider context** - HFT strategies may have different thresholds

## Invocation

Spawn @quant-overfit-checker when: Any backtest completes and needs overfitting validation before proceeding to production consideration.

## Completion Marker

SUBAGENT_COMPLETE: quant-overfit-checker
FILES_CREATED: 1
