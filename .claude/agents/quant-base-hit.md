---
name: quant-base-hit
description: "Calculate cash exit levels using Russian Doll framework"
version: "1.0.0"
parent_worker: optimizer
max_duration: 3m
parallelizable: false
---

# Quant Base Hit Agent

## Purpose
Calculates optimal "Base Hit" cash exit levels using the Russian Doll framework. Instead of swinging for home runs, Base Hit strategy takes quick, consistent profits. The Russian Doll framework defines three nested layers: OUTER (full target), MIDDLE (partial exit), and INNER (quick cash). This dramatically improves win rate while maintaining positive expectancy.

## Skills Used
- `/quant-base-hit-analysis` - Core skill for Russian Doll calculations
- `/tradebench-metrics` - For expectancy calculations at each layer
- `/prop-firm-rules` - For ensuring cash exits meet prop firm consistency requirements

## MCP Tools
- `sequential_thinking` - Plan Russian Doll layer optimization
- `exa_get_code_context_exa` - Reference Base Hit methodologies

## Input
```python
{
    "strategy_class": str,
    "symbol": str,
    "timeframe": str,
    "params": dict,
    "mfe_analysis": {                # From quant-loss-mfe
        "optimal_cash_exit": {
            "mfe_ticks": float,
            "expected_capture_rate": float
        },
        "mfe_percentiles": dict
    },
    "baseline_metrics": {
        "avg_winner": float,         # Ticks
        "avg_loser": float,          # Ticks
        "win_rate": float,
        "expectancy": float          # Per trade $
    },
    "tick_value": float,
    "target_win_rate": float         # Prop firm often needs 60%+
}
```

## Output
```python
{
    "russian_doll_config": {
        "OUTER": {
            "target_ticks": float,
            "position_pct": float,   # % of position at this level
            "expected_hit_rate": float,
            "risk_reward": float
        },
        "MIDDLE": {
            "target_ticks": float,
            "position_pct": float,
            "expected_hit_rate": float,
            "risk_reward": float
        },
        "INNER": {
            "target_ticks": float,
            "position_pct": float,
            "expected_hit_rate": float,
            "risk_reward": float
        }
    },
    "combined_metrics": {
        "expected_win_rate": float,  # Blended across layers
        "expected_avg_win": float,   # Weighted average
        "expected_expectancy": float,
        "consistency_score": float   # For prop firm eval
    },
    "scaling_recommendation": {
        "contracts_per_layer": {
            "INNER": int,
            "MIDDLE": int,
            "OUTER": int
        },
        "example_3_contract": str    # "1 INNER, 1 MIDDLE, 1 OUTER"
    },
    "prop_firm_compatibility": {
        "meets_consistency_rule": bool,
        "estimated_green_days_pct": float
    }
}
```

## Russian Doll Framework

### Layer Definitions
```
OUTER (Home Run)
├── Target: Full original strategy target
├── Position: 20-30% of size
├── Win Rate: Original (e.g., 45%)
└── Purpose: Capture full move when it happens

MIDDLE (Double)
├── Target: 50-70% of outer target
├── Position: 30-40% of size
├── Win Rate: Higher (e.g., 55%)
└── Purpose: Balance between profit and probability

INNER (Base Hit / Cash Exit)
├── Target: MFE-based quick profit (4-8 ticks)
├── Position: 30-50% of size
├── Win Rate: Very high (e.g., 75%)
└── Purpose: Consistent small wins, fund losers
```

### Visual Representation
```
Entry ──────┬─────────────────────────────────────► OUTER (20%)
            │
            ├────────────────────► MIDDLE (35%)
            │
            ├─────► INNER (45%)   ← Cash Exit (highest probability)
            │
            └─ Stop Loss
```

## Algorithm
1. **INNER Layer Calculation**
   - Use MFE analysis to set cash exit
   - Target: MFE where 65-75% of losers reached
   - Size: 40-50% of position
   ```python
   inner_target = mfe_analysis.optimal_cash_exit.mfe_ticks
   inner_hit_rate = mfe_analysis.optimal_cash_exit.expected_capture_rate
   ```

2. **MIDDLE Layer Calculation**
   - Target: Midpoint between INNER and OUTER
   - Estimated hit rate: Interpolate between layers
   ```python
   middle_target = (inner_target + outer_target) / 2
   middle_hit_rate = (inner_hit_rate + outer_hit_rate) / 2
   ```

3. **OUTER Layer Calculation**
   - Target: Original strategy target
   - Keep for "let winners run" scenario
   ```python
   outer_target = baseline_metrics.avg_winner
   outer_hit_rate = baseline_metrics.win_rate
   ```

4. **Position Sizing Optimization**
   - Optimize layer percentages to maximize expectancy
   - Constraint: Combined win rate >= target_win_rate
   ```python
   # Optimization target:
   maximize: sum(layer.pct * layer.target * layer.hit_rate) -
             (1 - combined_win_rate) * avg_loser
   subject to: combined_win_rate >= target_win_rate
   ```

5. **Expectancy Calculation**
   ```python
   combined_expectancy = sum(
       layer.position_pct * layer.target * layer.hit_rate * tick_value
   ) - (1 - combined_win_rate) * avg_loser * tick_value
   ```

## Prop Firm Consistency Rules
- Many prop firms require 60%+ win rate for evaluation
- Base Hit typically achieves 70-80% win rate
- Green day percentage critical for passing evaluations
- INNER layer funds losing trades, maintaining account equity

## Example Configuration
```python
# ES Futures, $12.50/tick
{
    "russian_doll_config": {
        "OUTER": {
            "target_ticks": 20,
            "position_pct": 0.25,
            "expected_hit_rate": 0.45,
            "risk_reward": 2.5
        },
        "MIDDLE": {
            "target_ticks": 10,
            "position_pct": 0.35,
            "expected_hit_rate": 0.58,
            "risk_reward": 1.25
        },
        "INNER": {
            "target_ticks": 4,
            "position_pct": 0.40,
            "expected_hit_rate": 0.78,
            "risk_reward": 0.5
        }
    },
    "combined_metrics": {
        "expected_win_rate": 0.72,
        "expected_expectancy": 18.50  # Per trade
    }
}
```

## Invocation
Spawn @quant-base-hit when: MFE analysis is complete and you need to configure Russian Doll exit layers. This is the core Base Hit calculation step.

## Dependencies
- Requires: `quant-loss-mfe` must complete first (need MFE data)
- Feeds into: `quant-prop-firm-validator`, `quant-config-gen`

## Completion Marker
SUBAGENT_COMPLETE: quant-base-hit
FILES_CREATED: 1
OUTPUT: russian_doll_config.json in strategy working directory
