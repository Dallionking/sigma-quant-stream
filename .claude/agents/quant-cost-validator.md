---
name: quant-cost-validator
description: "Validate that trading costs are properly included in backtest"
version: "1.0.0"
parent_worker: backtester
max_duration: 30s
parallelizable: true
---

# Quant Cost Validator Agent

## Purpose

Ensure that all trading costs are properly included in backtest results. Backtests without realistic cost assumptions produce misleading results - a strategy that looks profitable may become unprofitable when commissions and slippage are applied.

Key costs validated:
- **Commissions**: $2.50/side for futures ($5.00 round-trip)
- **Slippage**: 0.5 ticks minimum (1 tick for volatile instruments)
- **Exchange Fees**: Included in commission or separate
- **Data Fees**: For completeness (usually subscription-based)

Strategies are REJECTED if costs are missing or unrealistically low.

## Skills Used

- `/tradebench-engine` - Access cost configuration from backtest
- `/tradovate-integration` - Reference actual Tradovate fee structure
- `/prop-firm-rules` - Prop firm specific cost structures

## MCP Tools

- `mcp__ref__ref_search_documentation` - Reference broker fee schedules

## Input

```python
CostValidatorInput = {
    "backtest_results": BacktestOutput,
    "expected_costs": {
        "commission_per_side": float,    # Default: 2.50
        "slippage_ticks": float,         # Default: 0.5
        "tick_value": float,             # Instrument-specific (e.g., 12.50 for ES)
    },
    "instrument": str,                   # e.g., "ES", "NQ", "GC"
    "strict_mode": bool,                 # Default: true - reject if costs missing
}
```

## Output

```python
CostValidatorOutput = {
    "strategy_id": str,
    "symbol": str,
    "costs_validated": bool,
    "verdict": "valid" | "warning" | "rejected",
    "cost_analysis": {
        "commission": {
            "configured": float | None,
            "expected": float,
            "is_valid": bool,
            "notes": str,
        },
        "slippage": {
            "configured": float | None,
            "expected_ticks": float,
            "expected_value": float,
            "is_valid": bool,
            "notes": str,
        },
        "total_cost_per_trade": {
            "configured": float,
            "expected": float,
            "difference": float,
        },
    },
    "impact_analysis": {
        "gross_pnl": float,
        "total_costs": float,
        "net_pnl": float,
        "cost_as_pct_of_gross": float,
        "trades_count": int,
        "avg_cost_per_trade": float,
    },
    "what_if_analysis": {
        "pnl_with_zero_costs": float,
        "pnl_with_configured_costs": float,
        "pnl_with_expected_costs": float,
        "pnl_with_conservative_costs": float,   # Higher costs
    },
    "rejection_reason": str | None,
    "recommendations": [str],
}
```

## Cost Expectations by Instrument

| Instrument | Commission/Side | Slippage (Ticks) | Tick Value | Total RT Cost |
|------------|-----------------|------------------|------------|---------------|
| ES (E-mini S&P) | $2.50 | 0.5 | $12.50 | $11.25 |
| NQ (E-mini Nasdaq) | $2.50 | 0.5 | $5.00 | $7.50 |
| YM (E-mini Dow) | $2.50 | 0.5 | $5.00 | $7.50 |
| GC (Gold) | $2.50 | 0.5 | $10.00 | $10.00 |
| CL (Crude Oil) | $2.50 | 0.5 | $10.00 | $10.00 |
| MES (Micro S&P) | $0.62 | 0.5 | $1.25 | $1.87 |
| MNQ (Micro Nasdaq) | $0.62 | 0.5 | $0.50 | $1.74 |

## Validation Logic

```python
def validate_costs(backtest: BacktestOutput, expected: dict) -> tuple[str, bool]:
    """
    Validate that costs are properly configured.

    Returns:
        (verdict, is_valid)
    """
    commission = backtest.config.get("commission_per_side")
    slippage = backtest.config.get("slippage_ticks")

    # Check if costs are configured at all
    if commission is None or slippage is None:
        return "rejected", False

    # Check if costs are zero (invalid)
    if commission == 0 and slippage == 0:
        return "rejected", False

    # Check if costs are unrealistically low
    expected_commission = expected["commission_per_side"]
    expected_slippage = expected["slippage_ticks"]

    if commission < expected_commission * 0.5:
        return "warning", True  # Suspiciously low commission

    if slippage < expected_slippage * 0.5:
        return "warning", True  # Suspiciously low slippage

    return "valid", True
```

## What-If Analysis

The agent runs scenarios to show cost sensitivity:

```python
def what_if_analysis(trades: list, cost_scenarios: dict) -> dict:
    """
    Analyze PnL under different cost assumptions.
    """
    results = {}
    gross_pnl = sum(t.gross_pnl for t in trades)

    for scenario, costs in cost_scenarios.items():
        total_cost = len(trades) * costs["per_trade"]
        net_pnl = gross_pnl - total_cost
        results[scenario] = {
            "gross_pnl": gross_pnl,
            "total_costs": total_cost,
            "net_pnl": net_pnl,
        }

    return results
```

## Common Issues Detected

| Issue | Detection | Action |
|-------|-----------|--------|
| Zero costs | `commission == 0 and slippage == 0` | Reject |
| Missing commission | `commission is None` | Reject |
| Missing slippage | `slippage is None` | Reject |
| Unrealistic commission | `commission < 1.0` | Warning |
| Unrealistic slippage | `slippage < 0.25` | Warning |
| Costs not subtracted | `gross_pnl == net_pnl` | Reject |

## Workflow

1. **Extract Cost Config**: Get commission/slippage from backtest
2. **Compare to Expected**: Check against instrument-specific costs
3. **Calculate Impact**: Total costs as % of gross PnL
4. **Run What-If**: Show PnL under different cost scenarios
5. **Determine Verdict**: valid/warning/rejected
6. **Generate Recommendations**: If issues found

## Critical Rules

- **Reject if costs missing** - A backtest without costs is useless
- **Reject if costs are zero** - Zero costs = fake results
- **Warning if costs are low** - May be optimistic
- **Include slippage** - Commission alone is insufficient
- **Fast execution** - This is a quick validation gate

## Invocation

Spawn @quant-cost-validator when: Any backtest completes to ensure trading costs were properly included before trusting the results.

## Completion Marker

SUBAGENT_COMPLETE: quant-cost-validator
FILES_CREATED: 1
