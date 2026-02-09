---
name: quant-firm-ranker
description: "Rank best prop firms for strategy compatibility scoring"
version: "1.0.0"
parent_worker: optimizer
max_duration: 1m
parallelizable: false
---

# Quant Firm Ranker Agent

## Purpose
Ranks compatible prop firms by overall fit for the strategy. Creates a composite compatibility score based on: margin of safety, evaluation difficulty, payout terms, and platform preference. Outputs a prioritized list of recommended firms for the user to pursue.

## Skills Used
- `/quant-prop-firm-compliance` - For understanding firm rule nuances
- `/prop-firm-rules` - For firm comparison data

## MCP Tools
- `sequential_thinking` - Plan ranking algorithm

## Input
```python
{
    "prop_firm_validation": {        # From quant-prop-firm-validator
        "firm_compatibility": dict,
        "summary": dict
    },
    "user_preferences": {
        "preferred_platform": "tradovate"|"projectx"|"any",
        "account_size_target": int,
        "risk_tolerance": "conservative"|"moderate"|"aggressive",
        "priority": "safety"|"payout"|"evaluation_speed"
    },
    "strategy_profile": {
        "avg_trades_per_day": float,
        "typical_hold_time": str,
        "max_contracts_needed": int
    }
}
```

## Output
```python
{
    "firm_rankings": [
        {
            "rank": int,
            "firm_name": str,
            "platform": str,
            "compatibility_score": float,   # 0-100
            "score_breakdown": {
                "safety_margin": float,     # 0-30 points
                "evaluation_ease": float,   # 0-25 points
                "payout_terms": float,      # 0-25 points
                "platform_match": float     # 0-20 points
            },
            "recommended_account_size": int,
            "key_strengths": [str],
            "watch_out_for": [str]
        }
    ],
    "top_3_recommendation": {
        "primary": str,
        "secondary": str,
        "tertiary": str,
        "rationale": str
    },
    "platform_summary": {
        "tradovate_firms_compatible": int,
        "projectx_firms_compatible": int,
        "recommended_platform": str
    }
}
```

## Scoring Algorithm

### Component Weights
| Component | Weight | Description |
|-----------|--------|-------------|
| Safety Margin | 30% | Buffer vs daily loss and trailing DD limits |
| Evaluation Ease | 25% | How easy to pass evaluation rules |
| Payout Terms | 25% | Split, frequency, minimums |
| Platform Match | 20% | User preference alignment |

### Safety Margin Score (0-30)
```python
def safety_score(margin_of_safety):
    # margin_of_safety is dict from validator
    avg_margin = mean(margin_of_safety.values())

    if avg_margin > 0.40:
        return 30  # >40% buffer = perfect
    elif avg_margin > 0.25:
        return 25
    elif avg_margin > 0.15:
        return 20
    elif avg_margin > 0.10:
        return 15
    else:
        return 10  # Tight margins
```

### Evaluation Ease Score (0-25)
```python
evaluation_difficulty = {
    "TopStep": 15,       # Hardest (consistency rule)
    "Earn2Trade": 18,    # Hard (30% rule)
    "Leeloo": 20,        # Medium (40% rule)
    "Apex": 25,          # Easy (no consistency)
    "MyFundedFutures": 25,
    # etc.
}
```

### Payout Terms Score (0-25)
```python
# Based on profit split, payout frequency, minimum withdrawal
payout_scores = {
    "Apex": 22,          # 90% split, weekly
    "TopStep": 20,       # 80% split, bi-weekly
    "Earn2Trade": 18,    # 80% split, monthly
    # etc.
}
```

### Platform Match Score (0-20)
```python
def platform_score(firm_platform, user_preference):
    if user_preference == "any":
        return 15  # Slight preference for Tradovate (more firms)
    elif firm_platform == user_preference:
        return 20
    else:
        return 5   # Wrong platform
```

## Firm Characteristics Reference

### Best for Different Strategy Types
| Strategy Type | Best Firms | Why |
|--------------|------------|-----|
| Scalping (many trades) | Apex, MyFundedFutures | No consistency rule |
| Swing (few big wins) | TopStep, OneUp | Higher limits allow variance |
| Base Hit (consistent) | Any | Designed for consistency |
| High frequency | TopStep | Higher position limits |

### Platform Considerations
| Aspect | Tradovate | ProjectX |
|--------|-----------|----------|
| Firms available | 10 | 4 |
| API access | Yes | Limited |
| Browser automation | Easier | Harder |
| Data feed | Better | Good |

## Example Output
```python
{
    "firm_rankings": [
        {
            "rank": 1,
            "firm_name": "Apex Trader",
            "platform": "tradovate",
            "compatibility_score": 92.5,
            "score_breakdown": {
                "safety_margin": 28,
                "evaluation_ease": 25,
                "payout_terms": 22,
                "platform_match": 17.5
            },
            "recommended_account_size": 100000,
            "key_strengths": ["No consistency rule", "90% profit split", "Weekly payouts"],
            "watch_out_for": ["$2,500 daily loss limit is moderate"]
        },
        {
            "rank": 2,
            "firm_name": "MyFundedFutures",
            "platform": "tradovate",
            "compatibility_score": 88.0,
            ...
        }
    ],
    "top_3_recommendation": {
        "primary": "Apex Trader",
        "secondary": "MyFundedFutures",
        "tertiary": "The Trading Pit",
        "rationale": "All three have no consistency rules, matching Base Hit's high win rate approach. Apex offers best payout terms."
    }
}
```

## Invocation
Spawn @quant-firm-ranker when: Prop firm validation is complete and you need to prioritize which firms to pursue. This helps users focus on the best opportunities.

## Dependencies
- Requires: `quant-prop-firm-validator` must complete first
- Feeds into: `quant-config-gen` (firm-specific configs), `quant-promo-router`

## Completion Marker
SUBAGENT_COMPLETE: quant-firm-ranker
FILES_CREATED: 1
OUTPUT: firm_rankings.json in strategy working directory
