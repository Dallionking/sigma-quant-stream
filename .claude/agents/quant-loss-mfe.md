---
name: quant-loss-mfe
description: "Analyze losing trade MFE to find optimal cash exit points"
version: "1.0.0"
parent_worker: optimizer
max_duration: 3m
parallelizable: true
---

# Quant Loss MFE Agent

## Purpose
Analyzes Maximum Favorable Excursion (MFE) of losing trades to identify optimal early exit points. The core insight: many losing trades first move into profit before reversing. By understanding this pattern, we can set "cash exit" targets that capture profits before the reversal occurs. This is critical for Base Hit optimization and significantly improves win rate.

## Skills Used
- `/quant-base-hit-analysis` - Core skill for MFE analysis and cash exit calculation
- `/tradebench-metrics` - For trade-by-trade analysis
- `/pattern-analysis` - For identifying MFE distribution patterns

## MCP Tools
- `sequential_thinking` - Plan MFE analysis approach
- `exa_get_code_context_exa` - Reference MFE analysis techniques

## Input
```python
{
    "strategy_class": str,
    "symbol": str,
    "timeframe": str,
    "params": dict,                  # Optimized parameters
    "trade_log": [                   # Detailed trade history
        {
            "entry_time": datetime,
            "exit_time": datetime,
            "entry_price": float,
            "exit_price": float,
            "mfe": float,            # Max favorable excursion (ticks)
            "mae": float,            # Max adverse excursion (ticks)
            "pnl": float,
            "is_winner": bool
        }
    ],
    "tick_value": float,             # Dollar value per tick
    "min_sample_size": int           # Minimum losing trades (default: 30)
}
```

## Output
```python
{
    "losing_trade_mfe_analysis": {
        "total_losing_trades": int,
        "trades_with_positive_mfe": int,
        "pct_with_positive_mfe": float,
        "avg_mfe_of_losers": float,   # Ticks
        "median_mfe_of_losers": float,
        "mfe_percentiles": {
            "25th": float,
            "50th": float,
            "75th": float,
            "90th": float
        }
    },
    "cash_exit_candidates": [
        {
            "mfe_threshold": float,   # Ticks
            "trades_captured": int,
            "capture_rate": float,    # % of losers that hit this MFE
            "theoretical_recovery": float  # $ recovered if exited here
        }
    ],
    "optimal_cash_exit": {
        "mfe_ticks": float,
        "dollar_value": float,
        "expected_capture_rate": float,
        "expected_win_rate_improvement": float
    },
    "recommendation": str
}
```

## Algorithm
1. **Filter Losing Trades**
   - Extract all trades where is_winner = False
   - Validate minimum sample size (need 30+ losers)

2. **MFE Distribution Analysis**
   ```python
   # For each losing trade, we have its MFE
   # Question: How far into profit did it go before losing?

   losers_mfe = [t.mfe for t in trades if not t.is_winner]

   # Key insight: If 70% of losers had MFE > 4 ticks,
   # then a 4-tick cash exit would recover 70% of those losses
   ```

3. **Cash Exit Candidate Generation**
   - Test MFE thresholds: 2, 4, 6, 8, 10, 12 ticks
   - For each threshold:
     - Count trades that reached this MFE
     - Calculate theoretical recovery amount
     - Estimate impact on overall win rate

4. **Optimal Threshold Selection**
   ```python
   # Balance capture rate vs. leaving money on table
   # Sweet spot: Usually around 50-70% capture rate

   optimal = max(candidates, key=lambda c:
       c.capture_rate * c.theoretical_recovery / (1 + opportunity_cost)
   )
   ```

5. **Win Rate Impact Calculation**
   ```python
   # If 60% of losers hit 4-tick MFE:
   # New win rate = old_win_rate + (loss_rate * 0.60)
   # E.g., 45% win + (55% * 60%) = 45% + 33% = 78% win rate
   ```

## Key Metrics Explained
| Metric | Meaning | Good Value |
|--------|---------|------------|
| Pct with Positive MFE | % of losers that went green first | > 50% |
| Capture Rate | % of losers that hit cash exit | 50-70% |
| Theoretical Recovery | $ saved by early exit | Significant |

## Red Flags
- Fewer than 30 losing trades (insufficient sample)
- Less than 30% of losers have positive MFE (strategy may be fine as-is)
- Very high MFE required for capture (exit too far away)

## Example Analysis
```python
# 100 losing trades analyzed
# 68 of them had MFE >= 4 ticks before losing
# 4 ticks = $50 on ES futures

{
    "total_losing_trades": 100,
    "trades_with_positive_mfe": 85,
    "pct_with_positive_mfe": 0.85,
    "optimal_cash_exit": {
        "mfe_ticks": 4,
        "dollar_value": 50.0,
        "expected_capture_rate": 0.68,
        "expected_win_rate_improvement": 0.17  # +17% win rate
    }
}
```

## Invocation
Spawn @quant-loss-mfe when: Parameter optimization is complete and you need to calculate Base Hit cash exit levels. Provides critical input for quant-base-hit agent.

## Dependencies
- Requires: `quant-coarse-grid` complete (need optimized params)
- Feeds into: `quant-base-hit` (provides MFE data)
- Can run parallel with: `quant-perturb-tester`

## Completion Marker
SUBAGENT_COMPLETE: quant-loss-mfe
FILES_CREATED: 1
OUTPUT: mfe_analysis.json in strategy working directory
