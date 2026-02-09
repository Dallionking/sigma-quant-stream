---
name: quant-base-hit-analysis
description: "Loss MFE analysis and Base Hit cash exit optimization"
version: "1.0.0"
triggers:
  - "when optimizing trade exits"
  - "when analyzing losing trades"
  - "when implementing cash exits"
---

# Quant Base Hit Analysis

## Purpose

Analyzes Maximum Favorable Excursion (MFE) of losing trades to calculate optimal cash exit levels. The Base Hit methodology converts losers into small winners by exiting at the average MFE of losses.

## When to Use

- After initial strategy validation
- When optimizing exit timing
- For any strategy being promoted to production

## The Russian Doll Framework

```
OUTER:  Strategy TP/SL (entry model - DON'T CHANGE)
MIDDLE: Partial TPs (optional profit taking)
INNER:  Cash Exit ← Set at LOSS MFE average
```

The cash exit is where you ACTUALLY close, before the strategy's theoretical exit.

## Core Concept: Loss MFE

**Loss MFE**: How far did price move IN YOUR FAVOR before the trade became a loser?

```
Example losing trade:
- Entry: 5000
- Direction: Long
- Max favorable: 5008 (8 ticks MFE)
- Exit: 4990 (10 tick loss)
- This trade reached +8 ticks profit before reversing!

Cash Exit Insight:
If we had exited at +4 ticks, we'd have a small winner instead of a loser.
```

## Implementation

```python
from dataclasses import dataclass
import pandas as pd
import numpy as np

@dataclass
class BaseHitConfig:
    """Base Hit cash exit configuration."""
    exit_ticks: float
    expected_improvement: float
    trades_converted: int
    new_win_rate: float

def calculate_loss_mfe(trades: pd.DataFrame) -> dict:
    """
    Analyze MFE of losing trades.

    Requires columns: pnl, mfe_ticks (max favorable excursion)
    """
    # Filter losing trades
    losers = trades[trades['pnl'] < 0]

    if len(losers) == 0:
        return {'error': 'No losing trades to analyze'}

    return {
        'n_losers': len(losers),
        'avg_loss_mfe': losers['mfe_ticks'].mean(),
        'median_loss_mfe': losers['mfe_ticks'].median(),
        'std_loss_mfe': losers['mfe_ticks'].std(),
        'pct_mfe_positive': (losers['mfe_ticks'] > 0).mean(),
        'distribution': losers['mfe_ticks'].describe()
    }

def optimize_cash_exit(
    trades: pd.DataFrame,
    tick_value: float = 12.50
) -> BaseHitConfig:
    """
    Calculate optimal cash exit level.

    Strategy:
    1. Find average MFE of losing trades
    2. Set cash exit slightly below average
    3. Calculate improvement in win rate
    """
    losers = trades[trades['pnl'] < 0]
    winners = trades[trades['pnl'] > 0]

    # Calculate loss MFE
    avg_loss_mfe = losers['mfe_ticks'].mean()

    # Cash exit = average loss MFE (conservative)
    # Could also use median for robustness
    cash_exit_ticks = int(avg_loss_mfe)

    # How many losers would become winners?
    converted = (losers['mfe_ticks'] >= cash_exit_ticks).sum()

    # New metrics
    original_win_rate = len(winners) / len(trades)
    new_winners = len(winners) + converted
    new_win_rate = new_winners / len(trades)

    # Expected P&L improvement
    avg_loss = losers['pnl'].mean()
    converted_pnl = cash_exit_ticks * tick_value  # Small profit instead of loss
    improvement_per_trade = converted_pnl - avg_loss
    total_improvement = improvement_per_trade * converted

    return BaseHitConfig(
        exit_ticks=cash_exit_ticks,
        expected_improvement=total_improvement,
        trades_converted=converted,
        new_win_rate=new_win_rate
    )
```

## Validation

```python
def validate_base_hit(
    trades: pd.DataFrame,
    config: BaseHitConfig
) -> dict:
    """Validate Base Hit configuration on out-of-sample data."""

    # Simulate cash exit
    simulated = trades.copy()

    # Apply cash exit to trades where MFE >= exit level
    mask = simulated['mfe_ticks'] >= config.exit_ticks
    simulated.loc[mask, 'adjusted_pnl'] = config.exit_ticks * 12.50  # Use tick value
    simulated.loc[~mask, 'adjusted_pnl'] = simulated.loc[~mask, 'pnl']

    # Compare original vs adjusted
    original_total = trades['pnl'].sum()
    adjusted_total = simulated['adjusted_pnl'].sum()

    return {
        'original_pnl': original_total,
        'adjusted_pnl': adjusted_total,
        'improvement': adjusted_total - original_total,
        'improvement_pct': (adjusted_total - original_total) / abs(original_total),
        'is_valid': adjusted_total > original_total
    }
```

## Output Format

```json
{
  "strategy": "RSI_ATR_ES_5min",
  "loss_mfe_analysis": {
    "total_losing_trades": 127,
    "avg_loss_mfe_ticks": 4.2,
    "median_loss_mfe_ticks": 3.8,
    "std_loss_mfe_ticks": 1.5
  },
  "cash_exit_config": {
    "exit_level_ticks": 4,
    "expected_savings_annual": 12500,
    "effective_stop_reduction": "35%"
  }
}
```

## Related Skills

- `quant-parameter-optimization` - Grid search for parameters
- `quant-metrics-calculation` - Performance metrics
