---
name: quant-config-gen
description: "Generate strategy configuration files for deployment"
version: "1.0.0"
parent_worker: optimizer
max_duration: 1m
parallelizable: true
---

# Quant Config Gen Agent

## Purpose
Generates comprehensive strategy configuration files for deployment. Creates: default_config.json (universal settings), {symbol}_config.json (symbol-specific), and {firm}_config.json (prop firm specific). These configs are immediately usable by the trading system.

## Skills Used
- `/quant-parameter-optimization` - For parameter formatting
- `/trading-strategies` - For strategy configuration standards
- `/prop-firm-rules` - For firm-specific overrides

## MCP Tools
- `sequential_thinking` - Plan config structure

## Input
```python
{
    "strategy_class": str,
    "strategy_name": str,
    "symbol": str,
    "timeframe": str,
    "optimized_params": dict,        # From coarse-grid
    "russian_doll_config": dict,     # From base-hit
    "firm_rankings": [dict],         # From firm-ranker
    "robustness_results": {
        "is_robust": bool,
        "sensitivity_scores": dict
    },
    "backtest_metrics": {
        "sharpe": float,
        "calmar": float,
        "max_dd": float,
        "win_rate": float,
        "expectancy": float
    }
}
```

## Output
```python
{
    "files_created": [
        "default_config.json",
        "{symbol}_config.json",
        "{firm}_config.json"  # For top 3 firms
    ],
    "config_summary": {
        "total_files": int,
        "symbols_covered": [str],
        "firms_covered": [str]
    }
}
```

## Config File Structures

### 1. default_config.json
```json
{
    "strategy_meta": {
        "name": "MomentumBreakout_v1",
        "class": "MomentumBreakoutStrategy",
        "version": "1.0.0",
        "created_at": "2025-01-26T12:00:00Z",
        "optimization_date": "2025-01-26"
    },
    "parameters": {
        "lookback": 50,
        "entry_threshold": 1.2,
        "exit_threshold": 0.5,
        "atr_period": 14,
        "atr_multiplier": 2.0
    },
    "base_hit": {
        "enabled": true,
        "layers": {
            "INNER": {
                "target_ticks": 4,
                "position_pct": 0.40
            },
            "MIDDLE": {
                "target_ticks": 10,
                "position_pct": 0.35
            },
            "OUTER": {
                "target_ticks": 20,
                "position_pct": 0.25
            }
        }
    },
    "risk": {
        "max_position_size": 3,
        "max_daily_loss_pct": 2.0,
        "max_trade_risk_pct": 1.0,
        "stop_loss_ticks": 8
    },
    "execution": {
        "order_type": "limit",
        "slippage_buffer_ticks": 1,
        "timeout_seconds": 30
    },
    "performance_baseline": {
        "sharpe": 1.85,
        "calmar": 2.1,
        "max_dd_pct": 12.5,
        "win_rate": 0.72,
        "expectancy_per_trade": 18.50
    }
}
```

### 2. {symbol}_config.json (e.g., ES_config.json)
```json
{
    "extends": "default_config.json",
    "symbol": {
        "id": "ES.FUT",
        "name": "E-mini S&P 500",
        "tick_size": 0.25,
        "tick_value": 12.50,
        "margin_required": 500,
        "trading_hours": {
            "regular": "09:30-16:00 ET",
            "extended": "18:00-17:00 ET"
        }
    },
    "parameter_overrides": {
        "atr_multiplier": 1.8
    },
    "base_hit_overrides": {
        "INNER": {
            "target_ticks": 4,
            "dollar_value": 50.0
        }
    },
    "session_filters": {
        "trade_regular_hours_only": true,
        "avoid_first_15_min": true,
        "avoid_last_15_min": true
    }
}
```

### 3. {firm}_config.json (e.g., apex_config.json)
```json
{
    "extends": "ES_config.json",
    "prop_firm": {
        "name": "Apex Trader",
        "platform": "tradovate",
        "account_size": 100000
    },
    "risk_overrides": {
        "max_position_size": 3,
        "max_daily_loss_dollars": 2500,
        "max_trailing_dd_dollars": 3000,
        "consistency_rule": null
    },
    "compliance": {
        "require_daily_loss_check": true,
        "require_trailing_dd_check": true,
        "auto_flatten_at_limit": true,
        "flatten_threshold_pct": 0.90
    },
    "alerts": {
        "warn_at_daily_loss_pct": 0.70,
        "warn_at_trailing_dd_pct": 0.70
    }
}
```

## Algorithm
1. **Load Optimization Results**
   - Gather all optimization outputs
   - Validate required fields present

2. **Generate Default Config**
   - Combine strategy params
   - Add Base Hit configuration
   - Set performance baseline
   - Include risk defaults

3. **Generate Symbol Config**
   - Load symbol specifications
   - Apply symbol-specific overrides
   - Set tick values and margins

4. **Generate Firm Configs**
   - For top 3 ranked firms:
     - Load firm rule set
     - Calculate safe limits (90% of max)
     - Add compliance flags
     - Set alert thresholds

5. **Validate Configs**
   - JSON schema validation
   - Cross-reference check
   - Ensure no conflicts

## File Output Location
```
strategies/{strategy_name}/
├── configs/
│   ├── default_config.json
│   ├── ES_config.json
│   ├── NQ_config.json
│   ├── apex_config.json
│   ├── myfundedfutures_config.json
│   └── tradingpit_config.json
```

## Validation Rules
- All numeric values must be finite
- Tick values must match symbol specifications
- Risk limits must not exceed firm limits
- Base Hit percentages must sum to 1.0
- JSON must be valid and parseable

## Invocation
Spawn @quant-config-gen when: Optimization and prop firm validation are complete. This creates deployment-ready configuration files.

## Dependencies
- Requires: `quant-coarse-grid`, `quant-base-hit`, `quant-firm-ranker`
- Feeds into: `quant-artifact-builder`
- Can run parallel with: Other config generation tasks

## Completion Marker
SUBAGENT_COMPLETE: quant-config-gen
FILES_CREATED: 5-7 (depends on firm count)
OUTPUT: configs/ directory with all JSON files
