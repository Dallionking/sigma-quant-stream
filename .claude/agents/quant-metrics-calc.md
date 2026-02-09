---
name: quant-metrics-calc
description: "Calculate comprehensive performance metrics for backtest results"
version: "1.0.0"
parent_worker: backtester
max_duration: 1m
parallelizable: true
---

# Quant Metrics Calc Agent

## Purpose

Calculate all standard and advanced performance metrics from backtest results. This agent produces the comprehensive metrics report used for strategy evaluation, comparison, and monitoring.

Key metrics calculated:
- **Risk-Adjusted Returns**: Sharpe, Sortino, Calmar ratios
- **Drawdown Analysis**: Max DD, Average DD, DD Duration
- **Win/Loss Statistics**: Win Rate, Profit Factor, Payoff Ratio
- **Trade Statistics**: Trade count, Average trade, Best/Worst trade
- **Time-Based Metrics**: Monthly returns, Best/Worst months

All metrics are calculated using industry-standard formulas with proper handling of edge cases.

## Skills Used

- `/quant-metrics-calculation` - Core metrics calculation library
- `/tradebench-metrics` - Standard metric definitions
- `/strategy-research` - Reference metric benchmarks

## MCP Tools

- `mcp__ref__ref_search_documentation` - Reference quantitative finance docs

## Input

```python
MetricsCalcInput = {
    "backtest_results": BacktestOutput,
    "trades": [Trade],
    "equity_curve": list[float],
    "daily_returns": list[float],
    "risk_free_rate": float,         # Default: 0.05 (5%)
    "annualization_factor": int,     # Default: 252 (trading days)
    "include_advanced_metrics": bool, # Default: true
}
```

## Output

```python
MetricsCalcOutput = {
    "strategy_id": str,
    "symbol": str,
    "calculation_timestamp": datetime,

    # === CORE METRICS ===
    "core_metrics": {
        "total_return": float,              # Total percentage return
        "total_return_pct": float,          # As percentage
        "annualized_return": float,         # CAGR
        "sharpe_ratio": float,              # Risk-adjusted return
        "sortino_ratio": float,             # Downside-adjusted return
        "calmar_ratio": float,              # Return / Max DD
        "max_drawdown": float,              # Maximum peak-to-trough decline
        "max_drawdown_pct": float,          # As percentage
    },

    # === TRADE STATISTICS ===
    "trade_statistics": {
        "total_trades": int,
        "winning_trades": int,
        "losing_trades": int,
        "win_rate": float,                  # Winning / Total
        "profit_factor": float,             # Gross Profit / Gross Loss
        "payoff_ratio": float,              # Avg Win / Avg Loss
        "avg_trade": float,                 # Average PnL per trade
        "avg_win": float,
        "avg_loss": float,
        "largest_win": float,
        "largest_loss": float,
        "max_consecutive_wins": int,
        "max_consecutive_losses": int,
    },

    # === DRAWDOWN ANALYSIS ===
    "drawdown_analysis": {
        "max_drawdown": float,
        "max_drawdown_duration_days": int,
        "avg_drawdown": float,
        "avg_drawdown_duration_days": float,
        "recovery_factor": float,           # Total Return / Max DD
        "ulcer_index": float,               # Measure of drawdown pain
        "drawdown_events": [
            {
                "start": datetime,
                "trough": datetime,
                "end": datetime,
                "depth": float,
                "duration_days": int,
            }
        ],
    },

    # === TIME-BASED METRICS ===
    "time_metrics": {
        "trading_days": int,
        "months_traded": int,
        "profitable_months": int,
        "losing_months": int,
        "monthly_win_rate": float,
        "best_month": {
            "month": str,
            "return_pct": float,
        },
        "worst_month": {
            "month": str,
            "return_pct": float,
        },
        "avg_monthly_return": float,
        "monthly_return_std": float,
        "monthly_returns": list[float],
    },

    # === ADVANCED METRICS ===
    "advanced_metrics": {
        "omega_ratio": float,               # Probability weighted returns
        "kurtosis": float,                  # Tail risk
        "skewness": float,                  # Return asymmetry
        "var_95": float,                    # Value at Risk (95%)
        "cvar_95": float,                   # Conditional VaR (Expected Shortfall)
        "tail_ratio": float,                # Right tail / Left tail
        "common_sense_ratio": float,        # Tail Ratio * Profit Factor
        "sqn": float,                       # System Quality Number
    },

    # === RISK METRICS ===
    "risk_metrics": {
        "volatility_annual": float,
        "volatility_daily": float,
        "downside_deviation": float,
        "beta": float | None,               # If benchmark provided
        "alpha": float | None,              # If benchmark provided
        "information_ratio": float | None,  # If benchmark provided
    },

    # === SUMMARY ===
    "summary": {
        "grade": "A" | "B" | "C" | "D" | "F",
        "key_strengths": [str],
        "key_weaknesses": [str],
        "overall_score": float,             # 0-100
    },
}
```

## Metric Calculations

### Sharpe Ratio

```python
def calculate_sharpe(returns: list[float], risk_free_rate: float = 0.05) -> float:
    """
    Sharpe Ratio = (Mean Return - Risk Free Rate) / Std Dev of Returns
    Annualized using sqrt(252) for daily returns
    """
    excess_returns = np.array(returns) - (risk_free_rate / 252)
    if np.std(excess_returns) == 0:
        return 0.0
    return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
```

### Sortino Ratio

```python
def calculate_sortino(returns: list[float], risk_free_rate: float = 0.05) -> float:
    """
    Sortino Ratio = (Mean Return - Risk Free Rate) / Downside Deviation
    Only penalizes negative volatility
    """
    excess_returns = np.array(returns) - (risk_free_rate / 252)
    downside_returns = excess_returns[excess_returns < 0]
    if len(downside_returns) == 0 or np.std(downside_returns) == 0:
        return 0.0
    downside_dev = np.std(downside_returns)
    return np.mean(excess_returns) / downside_dev * np.sqrt(252)
```

### Maximum Drawdown

```python
def calculate_max_drawdown(equity_curve: list[float]) -> tuple[float, int]:
    """
    Max Drawdown = Maximum peak-to-trough decline
    Returns (max_dd, duration_bars)
    """
    peak = equity_curve[0]
    max_dd = 0
    dd_start = 0
    max_duration = 0

    for i, equity in enumerate(equity_curve):
        if equity > peak:
            peak = equity
            dd_start = i
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd
            max_duration = i - dd_start

    return max_dd, max_duration
```

### Profit Factor

```python
def calculate_profit_factor(trades: list[Trade]) -> float:
    """
    Profit Factor = Gross Profit / Gross Loss
    > 1.5 is good, > 2.0 is excellent
    """
    gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))

    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return gross_profit / gross_loss
```

## Metric Grading Criteria

| Grade | Sharpe | Max DD | Win Rate | Profit Factor |
|-------|--------|--------|----------|---------------|
| A | > 2.0 | < 10% | > 60% | > 2.5 |
| B | 1.5-2.0 | 10-15% | 55-60% | 2.0-2.5 |
| C | 1.0-1.5 | 15-20% | 50-55% | 1.5-2.0 |
| D | 0.5-1.0 | 20-25% | 45-50% | 1.0-1.5 |
| F | < 0.5 | > 25% | < 45% | < 1.0 |

## Workflow

1. **Extract Data**: Get trades, equity curve, returns
2. **Calculate Core Metrics**: Sharpe, Sortino, Max DD, etc.
3. **Calculate Trade Stats**: Win rate, profit factor, etc.
4. **Analyze Drawdowns**: Duration, recovery, events
5. **Calculate Time Metrics**: Monthly returns, best/worst
6. **Calculate Advanced Metrics**: VaR, Omega, SQN
7. **Generate Summary**: Grade and key findings

## Critical Rules

- **Handle edge cases** - Empty trades, zero returns, division by zero
- **Use proper annualization** - 252 trading days for daily returns
- **Include all metrics** - Comprehensive analysis needed
- **Round appropriately** - 2-4 decimal places depending on metric

## Invocation

Spawn @quant-metrics-calc when: Backtest completes and comprehensive performance metrics are needed for evaluation.

## Completion Marker

SUBAGENT_COMPLETE: quant-metrics-calc
FILES_CREATED: 1
