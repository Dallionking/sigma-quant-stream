---
name: quant-sample-validator
description: "Validate sufficient trade count for statistical significance"
version: "1.0.0"
parent_worker: backtester
max_duration: 30s
parallelizable: true
---

# Quant Sample Validator Agent

## Purpose

Ensure backtest results have sufficient trade count for statistical significance. A strategy with too few trades cannot be reliably evaluated - the results may be due to luck rather than edge.

Key thresholds:
- **Minimum: 100 trades** - Below this, results are unreliable
- **Good: 200+ trades** - Reasonable statistical confidence
- **Excellent: 500+ trades** - High statistical confidence
- **Reject: < 30 trades** - Automatic rejection, insufficient data

This agent is a fast validation gate that prevents wasting compute on strategies that can't be properly evaluated.

## Skills Used

- `/tradebench-metrics` - Access trade count from backtest results
- `/quant-metrics-calculation` - Calculate statistical power

## MCP Tools

- `mcp__ref__ref_search_documentation` - Research sample size requirements

## Input

```python
SampleValidatorInput = {
    "backtest_results": BacktestOutput,
    "thresholds": {
        "reject_below": int,         # Default: 30
        "minimum_acceptable": int,   # Default: 100
        "good": int,                 # Default: 200
        "excellent": int,            # Default: 500
    },
    "timeframe_context": str,        # e.g., "15m", "1H" - affects expectations
    "backtest_duration_days": int,   # How long was the backtest
}
```

## Output

```python
SampleValidatorOutput = {
    "strategy_id": str,
    "symbol": str,
    "trade_count": int,
    "verdict": "excellent" | "good" | "acceptable" | "insufficient" | "rejected",
    "passes_validation": bool,
    "statistical_analysis": {
        "trades_per_day": float,
        "trades_per_month": float,
        "expected_annual_trades": int,
        "statistical_power": float,      # 0-1, power to detect true edge
        "confidence_level": float,       # Confidence in results given sample
    },
    "recommendations": [str],
    "rejection_reason": str | None,
    "context_notes": str,               # Notes about timeframe expectations
}
```

## Validation Logic

```python
def validate_sample_size(trade_count: int, thresholds: dict) -> tuple[str, bool]:
    """
    Validate trade count against thresholds.

    Returns:
        (verdict, passes_validation)
    """
    if trade_count < thresholds["reject_below"]:
        return "rejected", False
    elif trade_count < thresholds["minimum_acceptable"]:
        return "insufficient", False
    elif trade_count < thresholds["good"]:
        return "acceptable", True
    elif trade_count < thresholds["excellent"]:
        return "good", True
    else:
        return "excellent", True
```

## Statistical Power Calculation

Statistical power measures the probability of detecting a true edge if one exists.

```python
def calculate_statistical_power(trade_count: int, expected_edge: float = 0.05) -> float:
    """
    Estimate statistical power for detecting an edge.

    Parameters:
        trade_count: Number of trades in backtest
        expected_edge: Expected win rate above 50% (e.g., 0.05 = 55% win rate)

    Returns:
        Power between 0-1
    """
    # Simplified power calculation
    # Based on binomial test for detecting deviation from 50%
    z_alpha = 1.96  # 95% confidence
    z_power = (expected_edge * np.sqrt(trade_count) - z_alpha) / 1.0
    power = scipy.stats.norm.cdf(z_power)
    return max(0, min(1, power))
```

## Trade Count Expectations by Timeframe

| Timeframe | Expected Trades/Day | 100 Trades In | 200 Trades In |
|-----------|--------------------:|---------------|---------------|
| 1m | 10-50 | 2-10 days | 4-20 days |
| 5m | 5-20 | 5-20 days | 10-40 days |
| 15m | 2-8 | 12-50 days | 25-100 days |
| 1H | 0.5-2 | 50-200 days | 100-400 days |
| 4H | 0.1-0.5 | 200-1000 days | 400-2000 days |
| 1D | 0.05-0.2 | 500-2000 days | 1000-4000 days |

## Verdict Interpretation

| Verdict | Trade Count | Interpretation | Action |
|---------|-------------|----------------|--------|
| Rejected | < 30 | Results meaningless | Auto-reject, need more data |
| Insufficient | 30-99 | Low confidence | Proceed with heavy caveats |
| Acceptable | 100-199 | Minimum viable | Proceed with monitoring |
| Good | 200-499 | Reasonable confidence | Proceed normally |
| Excellent | 500+ | High confidence | Proceed with confidence |

## Workflow

1. **Extract Trade Count**: Get total trades from backtest results
2. **Calculate Trades/Day**: Normalize by backtest duration
3. **Calculate Statistical Power**: Estimate detection capability
4. **Apply Thresholds**: Determine verdict
5. **Generate Recommendations**: If insufficient, suggest improvements

## Recommendations by Verdict

- **Rejected**: "Strategy needs longer backtest period. Current trades: {n}. Minimum required: 30. Recommend: Extend backtest to capture at least 100 trades."

- **Insufficient**: "Trade count ({n}) is below recommended minimum of 100. Results have low statistical confidence. Consider extending backtest period or adjusting strategy frequency."

- **Acceptable**: "Trade count ({n}) meets minimum threshold but is below ideal (200+). Monitor closely in paper trading."

## Critical Rules

- **Reject < 30 trades** - No exceptions, results are random
- **Be timeframe-aware** - Daily strategies naturally have fewer trades
- **Consider trade quality** - 100 high-quality trades > 500 noise trades
- **Fast execution** - This is a quick gate, don't over-analyze

## Invocation

Spawn @quant-sample-validator when: Any backtest completes and needs sample size validation before further analysis.

## Completion Marker

SUBAGENT_COMPLETE: quant-sample-validator
FILES_CREATED: 1
