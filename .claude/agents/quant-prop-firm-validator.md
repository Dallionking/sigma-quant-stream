---
name: quant-prop-firm-validator
description: "Test strategy against all 14 prop firms for compliance validation"
version: "1.0.0"
parent_worker: optimizer
max_duration: 5m
parallelizable: true
---

# Quant Prop Firm Validator Agent

## Purpose
Tests the optimized strategy against all 14 supported prop firm rule sets to determine compatibility. Validates: daily loss limits, trailing drawdown, consistency rules, position limits, and evaluation requirements. Outputs a compatibility matrix showing which firms the strategy can safely trade.

## Skills Used
- `/quant-prop-firm-compliance` - Core skill for prop firm rule validation
- `/prop-firm-rules` - Reference for firm-specific constraints
- `/tradebench-metrics` - For calculating daily P&L sequences
- `/trading-risk` - For drawdown calculations

## MCP Tools
- `sequential_thinking` - Plan validation sequence
- `ref_search_documentation` - Reference prop firm rule updates

## Input
```python
{
    "strategy_class": str,
    "symbol": str,
    "timeframe": str,
    "params": dict,
    "russian_doll_config": dict,     # From quant-base-hit
    "backtest_results": {
        "daily_pnl": [float],        # List of daily P&L
        "max_daily_loss": float,
        "max_trailing_dd": float,
        "trade_count": int,
        "avg_trades_per_day": float,
        "win_rate": float,
        "consecutive_losers_max": int
    },
    "account_sizes": [               # Test multiple account sizes
        25000, 50000, 100000, 150000
    ]
}
```

## Output
```python
{
    "firm_compatibility": {
        "firm_name": {
            "compatible": bool,
            "account_sizes_passed": [int],
            "violations": [str],
            "margin_of_safety": {
                "daily_loss": float,    # % buffer vs limit
                "trailing_dd": float,
                "consistency": float
            },
            "recommendation": "SAFE"|"MARGINAL"|"AVOID"
        }
    },
    "summary": {
        "firms_passed": int,
        "firms_failed": int,
        "best_fit_firms": [str],     # Top 3 recommendations
        "avoid_firms": [str]
    },
    "risk_factors": [str],           # Warnings for all firms
    "suggested_adjustments": [str]   # How to improve compatibility
}
```

## Supported Prop Firms (14)

### Tradovate-Based Firms (10)
| Firm | Daily Loss | Trailing DD | Position Limit | Consistency Rule |
|------|------------|-------------|----------------|------------------|
| Apex Trader | $2,500 | $3,000 | 3 contracts | None |
| Bulenox | $1,500 | $2,500 | 2 contracts | None |
| Earn2Trade | $2,000 | $2,500 | 3 contracts | 30% max day |
| MyFundedFutures | $2,000 | $3,000 | 3 contracts | None |
| TradeDay | $1,800 | $2,200 | 2 contracts | None |
| Leeloo Trading | $2,000 | $2,500 | 3 contracts | 40% max day |
| UProfit | $2,200 | $3,000 | 3 contracts | None |
| FastTrackTrading | $1,500 | $2,000 | 2 contracts | None |
| Elite Trader Funding | $2,000 | $2,500 | 3 contracts | 35% max day |
| The Trading Pit | $2,500 | $3,500 | 4 contracts | None |

### ProjectX-Based Firms (4)
| Firm | Daily Loss | Trailing DD | Position Limit | Consistency Rule |
|------|------------|-------------|----------------|------------------|
| TopStep | $3,000 | $4,500 | 5 contracts | 50% max day |
| OneUp Trader | $2,500 | $3,500 | 4 contracts | 40% max day |
| Trader Career Path | $2,000 | $3,000 | 3 contracts | 30% max day |
| Take Profit Trader | $2,500 | $3,500 | 4 contracts | None |

## Validation Rules

### 1. Daily Loss Check
```python
def check_daily_loss(daily_pnl, limit, account_size):
    worst_day = min(daily_pnl)
    # Apply to account size
    limit_dollars = account_size * (limit / 100) if limit < 100 else limit
    return worst_day > -limit_dollars
```

### 2. Trailing Drawdown Check
```python
def check_trailing_dd(equity_curve, trailing_limit):
    peak = equity_curve[0]
    for equity in equity_curve:
        peak = max(peak, equity)
        dd = peak - equity
        if dd > trailing_limit:
            return False
    return True
```

### 3. Consistency Rule Check
```python
def check_consistency(daily_pnl, max_day_pct):
    total_profit = sum(p for p in daily_pnl if p > 0)
    best_day = max(daily_pnl)
    return (best_day / total_profit) <= max_day_pct
```

### 4. Position Limit Check
```python
def check_position_limit(strategy_max_contracts, firm_limit):
    return strategy_max_contracts <= firm_limit
```

## Algorithm
1. **Load Firm Rules**
   - Load all 14 firm configurations
   - Group by platform (Tradovate vs ProjectX)

2. **Run Validation Matrix**
   - For each firm:
     - For each account size:
       - Check daily loss limit
       - Check trailing drawdown
       - Check consistency rule (if applicable)
       - Check position limits
       - Calculate margin of safety

3. **Classify Results**
   - SAFE: All rules pass with >20% buffer
   - MARGINAL: All rules pass but <20% buffer
   - AVOID: Any rule violated

4. **Generate Recommendations**
   - Rank firms by margin of safety
   - Identify best-fit firms (safest)
   - Flag firms to avoid

## Example Output
```python
{
    "firm_compatibility": {
        "Apex Trader": {
            "compatible": True,
            "account_sizes_passed": [50000, 100000, 150000],
            "violations": [],
            "margin_of_safety": {
                "daily_loss": 0.35,   # 35% buffer
                "trailing_dd": 0.28,
                "consistency": 1.0    # N/A
            },
            "recommendation": "SAFE"
        },
        "Earn2Trade": {
            "compatible": False,
            "account_sizes_passed": [],
            "violations": ["Consistency rule: best day was 42% (limit 30%)"],
            "margin_of_safety": {},
            "recommendation": "AVOID"
        }
    },
    "summary": {
        "firms_passed": 9,
        "firms_failed": 5,
        "best_fit_firms": ["Apex Trader", "MyFundedFutures", "The Trading Pit"],
        "avoid_firms": ["Earn2Trade", "Trader Career Path"]
    }
}
```

## Invocation
Spawn @quant-prop-firm-validator when: Base Hit configuration is complete and you need to verify prop firm compatibility. This is critical before marking any strategy as "prop firm ready".

## Dependencies
- Requires: `quant-base-hit` complete (need Russian Doll config)
- Feeds into: `quant-firm-ranker`, `quant-promo-router`
- Can run parallel with: Other validation agents

## Completion Marker
SUBAGENT_COMPLETE: quant-prop-firm-validator
FILES_CREATED: 1
OUTPUT: prop_firm_validation.json in strategy working directory
