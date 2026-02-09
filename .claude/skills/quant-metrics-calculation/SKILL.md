---
name: quant-metrics-calculation
description: "Sharpe ratio, drawdown, and performance metrics calculation"
version: "1.0.0"
triggers:
  - "when calculating strategy performance"
  - "when comparing strategies"
  - "when validating backtest results"
---

# Quant Metrics Calculation

## Purpose

Standardized calculation of trading performance metrics. Consistent metrics enable apples-to-apples strategy comparison.

## When to Use

- After every backtest
- When comparing strategies
- When reporting performance
- When validating third-party results

## Core Metrics

| Metric | Formula | Good | Excellent |
|--------|---------|------|-----------|
| **Sharpe Ratio** | (Rp - Rf) / σp | > 1.0 | > 1.5 |
| **Max Drawdown** | Max peak-to-trough | < 20% | < 10% |
| **Win Rate** | Wins / Total | 50-65% | 55-60% |
| **Profit Factor** | Gross Profit / Gross Loss | > 1.3 | > 1.5 |
| **Calmar Ratio** | CAGR / Max DD | > 1.0 | > 2.0 |

## Implementation

```python
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    """Complete performance metrics."""
    sharpe: float
    max_dd: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade: float
    calmar: float

def calculate_sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    """
    Calculate annualized Sharpe ratio.

    Args:
        returns: Period returns (daily, etc.)
        rf: Risk-free rate (annualized)
    """
    # Assume 252 trading days
    excess = returns - rf / 252
    return np.sqrt(252) * excess.mean() / excess.std()

def calculate_max_drawdown(equity: pd.Series) -> float:
    """Calculate maximum drawdown."""
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak
    return drawdown.min()

def calculate_metrics(
    trades: pd.DataFrame,
    returns: pd.Series
) -> PerformanceMetrics:
    """Calculate all performance metrics."""

    # Equity curve
    equity = (1 + returns).cumprod()

    # Win rate
    wins = trades[trades['pnl'] > 0]
    win_rate = len(wins) / len(trades) if len(trades) > 0 else 0

    # Profit factor
    gross_profit = trades[trades['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(trades[trades['pnl'] < 0]['pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Max drawdown
    max_dd = calculate_max_drawdown(equity)

    # Sharpe
    sharpe = calculate_sharpe(returns)

    # Calmar
    cagr = (equity.iloc[-1] ** (252 / len(equity))) - 1
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0

    return PerformanceMetrics(
        sharpe=sharpe,
        max_dd=max_dd,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=len(trades),
        avg_trade=trades['pnl'].mean() if len(trades) > 0 else 0,
        calmar=calmar
    )
```

## Decay Calculation

```python
def calculate_decay(is_metrics: dict, oos_metrics: dict) -> dict:
    """Calculate IS to OOS performance decay."""

    sharpe_decay = (
        (is_metrics['sharpe'] - oos_metrics['sharpe']) / is_metrics['sharpe']
        if is_metrics['sharpe'] > 0 else 1.0
    )

    win_rate_decay = (
        (is_metrics['win_rate'] - oos_metrics['win_rate']) / is_metrics['win_rate']
        if is_metrics['win_rate'] > 0 else 1.0
    )

    return {
        'sharpe_decay': sharpe_decay,
        'win_rate_decay': win_rate_decay,
        'is_healthy': sharpe_decay < 0.30  # Less than 30% decay
    }
```

## Quality Thresholds

| Metric | Pass | Good | Red Flag |
|--------|------|------|----------|
| Sharpe | > 1.0 | > 1.5 | > 3.0 (overfit) |
| Max DD | < 20% | < 15% | > 30% |
| Trades | > 100 | > 200 | < 30 |
| OOS Decay | < 30% | < 20% | > 50% |
| Win Rate | < 80% | 50-65% | > 80% |

## Related Skills

- `quant-overfitting-detection` - Red flag detection
- `quant-cost-modeling` - Ensure net metrics
