---
name: quant-hypothesis-generation
description: "Structured hypothesis card format for systematic strategy development and validation"
version: "1.0.0"
triggers:
  - "when creating new strategy hypotheses"
  - "when documenting trading ideas"
  - "when validating edge rationale"
  - "when tracking hypothesis outcomes"
---

# Quant Hypothesis Generation

## Purpose

Provides a structured format for generating, documenting, and tracking trading hypotheses. Every strategy must start with a clear, falsifiable hypothesis before any code is written. This skill ensures consistent documentation and enables systematic tracking of what works and what doesn't.

## When to Use

- Starting any new strategy research
- Converting discretionary ideas to systematic rules
- Documenting imported strategies (PineScript, community)
- Reviewing and prioritizing the research backlog
- Post-mortem analysis of failed strategies

## Key Concepts

### What Makes a Good Hypothesis

A trading hypothesis must be:

1. **Falsifiable**: Can be proven wrong with data
2. **Specific**: Clear entry/exit conditions, not vague
3. **Measurable**: Quantifiable success criteria
4. **Rational**: Has a logical edge explanation
5. **Actionable**: Can be implemented as code

### Hypothesis Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Mean Reversion** | Price returns to average | "Price reverts after 2 ATR move" |
| **Momentum** | Trend continuation | "Breakouts above 20-day high continue" |
| **Microstructure** | Order flow patterns | "Large orders precede price moves" |
| **Calendar** | Time-based patterns | "Monday reversals after Friday trends" |
| **Behavioral** | Human bias exploitation | "Panic selling creates overshoots" |
| **Structural** | Market mechanics | "Option expiry creates pinning" |

### Edge Rationale Types

Every hypothesis must explain WHY the edge exists:

```
1. Information Asymmetry: You know something others don't
2. Behavioral Bias: Exploiting human psychology
3. Structural Constraint: Regulatory or mechanical cause
4. Risk Premium: Being paid for bearing risk
5. Liquidity Provision: Market making compensation
6. Execution Advantage: Speed or access advantage
```

## Patterns & Templates

### Hypothesis Card JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HypothesisCard",
  "type": "object",
  "required": [
    "id",
    "title",
    "hypothesis",
    "edge_rationale",
    "entry_rules",
    "exit_rules",
    "expected_metrics",
    "validation_criteria",
    "status"
  ],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^HYP-[0-9]{4}$",
      "description": "Unique hypothesis identifier"
    },
    "title": {
      "type": "string",
      "maxLength": 100,
      "description": "Brief descriptive title"
    },
    "hypothesis": {
      "type": "string",
      "minLength": 50,
      "description": "Clear, falsifiable hypothesis statement"
    },
    "edge_rationale": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": [
            "information_asymmetry",
            "behavioral_bias",
            "structural_constraint",
            "risk_premium",
            "liquidity_provision",
            "execution_advantage"
          ]
        },
        "explanation": {
          "type": "string",
          "minLength": 100
        },
        "academic_support": {
          "type": "array",
          "items": {"type": "string"}
        }
      },
      "required": ["type", "explanation"]
    },
    "entry_rules": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "condition": {"type": "string"},
          "parameter": {"type": "string"},
          "value": {"type": ["number", "string"]}
        }
      },
      "minItems": 1
    },
    "exit_rules": {
      "type": "object",
      "properties": {
        "take_profit": {"type": "string"},
        "stop_loss": {"type": "string"},
        "time_exit": {"type": "string"},
        "other_conditions": {
          "type": "array",
          "items": {"type": "string"}
        }
      },
      "required": ["stop_loss"]
    },
    "expected_metrics": {
      "type": "object",
      "properties": {
        "win_rate": {
          "type": "object",
          "properties": {
            "min": {"type": "number"},
            "max": {"type": "number"}
          }
        },
        "sharpe_ratio": {
          "type": "object",
          "properties": {
            "min": {"type": "number"},
            "max": {"type": "number"}
          }
        },
        "max_drawdown": {
          "type": "object",
          "properties": {
            "max": {"type": "number"}
          }
        },
        "trades_per_month": {
          "type": "object",
          "properties": {
            "min": {"type": "number"}
          }
        }
      }
    },
    "validation_criteria": {
      "type": "object",
      "properties": {
        "min_trades": {"type": "integer", "minimum": 100},
        "min_sharpe": {"type": "number"},
        "max_drawdown": {"type": "number"},
        "min_oos_retention": {"type": "number"},
        "statistical_significance": {"type": "number"}
      },
      "required": ["min_trades", "min_sharpe", "max_drawdown"]
    },
    "status": {
      "type": "string",
      "enum": [
        "draft",
        "ready_for_test",
        "in_sample_testing",
        "out_of_sample_testing",
        "validated",
        "invalidated",
        "abandoned"
      ]
    },
    "results": {
      "type": "object",
      "properties": {
        "in_sample": {"$ref": "#/definitions/TestResults"},
        "out_of_sample": {"$ref": "#/definitions/TestResults"}
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "created_date": {"type": "string", "format": "date"},
        "author": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "priority": {"type": "integer", "minimum": 1, "maximum": 5},
        "estimated_hours": {"type": "number"}
      }
    }
  },
  "definitions": {
    "TestResults": {
      "type": "object",
      "properties": {
        "total_trades": {"type": "integer"},
        "win_rate": {"type": "number"},
        "sharpe_ratio": {"type": "number"},
        "max_drawdown": {"type": "number"},
        "profit_factor": {"type": "number"},
        "test_period": {"type": "string"},
        "test_date": {"type": "string", "format": "date"}
      }
    }
  }
}
```

### Hypothesis Card Template (Markdown)

```markdown
# Hypothesis Card: HYP-{XXXX}

## Title
{Brief descriptive title - max 100 chars}

## Status
{draft | ready_for_test | in_sample_testing | out_of_sample_testing | validated | invalidated | abandoned}

## Hypothesis Statement
{Clear, falsifiable statement of what you believe to be true}

> "When [CONDITION], [OUTCOME] occurs because [REASON], resulting in [TRADEABLE EDGE]."

## Edge Rationale

### Type
{information_asymmetry | behavioral_bias | structural_constraint | risk_premium | liquidity_provision | execution_advantage}

### Explanation
{Detailed explanation of WHY this edge exists - minimum 100 words}

### Academic Support
- {Paper 1 citation}
- {Paper 2 citation}
- {Relevant studies}

## Trading Rules

### Entry Conditions
1. {Condition 1}: {Parameter} {Operator} {Value}
2. {Condition 2}: {Parameter} {Operator} {Value}
3. {Condition 3}: {Parameter} {Operator} {Value}

### Exit Rules
- **Take Profit**: {Rule}
- **Stop Loss**: {Rule}
- **Time Exit**: {Rule}
- **Other**: {Any additional exit conditions}

## Expected Metrics

| Metric | Min | Max | Notes |
|--------|-----|-----|-------|
| Win Rate | {X}% | {Y}% | |
| Sharpe Ratio | {X} | {Y} | |
| Max Drawdown | - | {Y}% | |
| Trades/Month | {X} | - | |

## Validation Criteria

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Minimum Trades | {N} | Statistical significance |
| Minimum Sharpe | {X} | After costs |
| Maximum Drawdown | {Y}% | Prop firm limits |
| OOS Retention | {Z}% | Avoid overfitting |
| P-Value | < 0.05 | Statistical significance |

## Test Results

### In-Sample
- **Period**: {start} to {end}
- **Trades**: {N}
- **Win Rate**: {X}%
- **Sharpe**: {X}
- **Max DD**: {X}%
- **Test Date**: {YYYY-MM-DD}

### Out-of-Sample
- **Period**: {start} to {end}
- **Trades**: {N}
- **Win Rate**: {X}%
- **Sharpe**: {X}
- **Max DD**: {X}%
- **Test Date**: {YYYY-MM-DD}

## Conclusion
{VALIDATED | INVALIDATED | INCONCLUSIVE}

{Detailed analysis of results and next steps}

## Metadata
- **Created**: {YYYY-MM-DD}
- **Author**: {Name}
- **Priority**: {1-5}
- **Tags**: {tag1}, {tag2}
- **Estimated Hours**: {X}
```

### Hypothesis Generation Prompts

Use these prompts to generate new hypothesis ideas:

```python
HYPOTHESIS_GENERATION_PROMPTS = {
    "mean_reversion": """
        What conditions indicate price has moved too far too fast?
        - Bollinger Band extremes
        - RSI oversold/overbought
        - Distance from VWAP
        - Multi-ATR moves
        - Gap fills
    """,

    "momentum": """
        What conditions indicate trend continuation?
        - Breakouts from consolidation
        - Moving average crossovers
        - Volume confirmation
        - Higher highs/higher lows
        - Sector rotation signals
    """,

    "microstructure": """
        What order flow patterns precede moves?
        - Delta divergence
        - Large block trades
        - Bid/ask imbalance
        - Absorption patterns
        - Iceberg detection
    """,

    "calendar": """
        What time-based patterns exist?
        - Day of week effects
        - Time of day patterns
        - Monthly seasonality
        - Options expiration
        - Economic calendar
    """,

    "behavioral": """
        What human biases can be exploited?
        - Overreaction to news
        - Round number anchoring
        - Recency bias
        - Loss aversion
        - Herding behavior
    """,

    "structural": """
        What market mechanics create opportunity?
        - Index rebalancing
        - ETF creation/redemption
        - Margin calls
        - Option hedging (gamma)
        - Regulatory constraints
    """
}
```

## Examples

### Example 1: Complete Hypothesis Card

```json
{
  "id": "HYP-0042",
  "title": "RTH Open Gap Fade on ES Futures",
  "hypothesis": "When ES futures open RTH session with a gap greater than 0.3% from prior close, price fills at least 50% of the gap within the first 60 minutes in 65%+ of cases, due to overnight position unwinding and retail stop hunting.",
  "edge_rationale": {
    "type": "behavioral_bias",
    "explanation": "Overnight gaps trigger retail stop losses and margin calls at market open. Institutional traders and market makers absorb this flow and push price back toward fair value (prior close). The gap creates a temporary liquidity imbalance that mean-reverts as the market digests overnight information and repositions. This is exacerbated by algorithmic traders who specifically target gap fills.",
    "academic_support": [
      "Cooper et al. (2006) - 'Return Predictability and the Opening Gap'",
      "Hirschey (2004) - 'An Analysis of Gap Trading'"
    ]
  },
  "entry_rules": [
    {"condition": "Gap from prior close", "parameter": "gap_pct", "value": "> 0.3%"},
    {"condition": "Time window", "parameter": "entry_time", "value": "First 5 min of RTH"},
    {"condition": "Gap direction", "parameter": "direction", "value": "Any (fade the gap)"}
  ],
  "exit_rules": {
    "take_profit": "50% gap fill (half the distance to prior close)",
    "stop_loss": "Gap extends by 50% (1.5x original gap)",
    "time_exit": "60 minutes from entry",
    "other_conditions": ["Exit if VWAP crossed against position"]
  },
  "expected_metrics": {
    "win_rate": {"min": 55, "max": 70},
    "sharpe_ratio": {"min": 1.0, "max": 2.0},
    "max_drawdown": {"max": 15},
    "trades_per_month": {"min": 8}
  },
  "validation_criteria": {
    "min_trades": 200,
    "min_sharpe": 1.0,
    "max_drawdown": 20,
    "min_oos_retention": 60,
    "statistical_significance": 0.05
  },
  "status": "validated",
  "results": {
    "in_sample": {
      "total_trades": 312,
      "win_rate": 64.1,
      "sharpe_ratio": 1.42,
      "max_drawdown": 11.3,
      "profit_factor": 1.78,
      "test_period": "2020-01-01 to 2023-06-30",
      "test_date": "2024-01-15"
    },
    "out_of_sample": {
      "total_trades": 89,
      "win_rate": 61.8,
      "sharpe_ratio": 1.21,
      "max_drawdown": 14.2,
      "profit_factor": 1.52,
      "test_period": "2023-07-01 to 2024-12-31",
      "test_date": "2024-01-15"
    }
  },
  "metadata": {
    "created_date": "2024-01-10",
    "author": "Quant Team",
    "tags": ["mean_reversion", "gap_trading", "intraday", "ES"],
    "priority": 2,
    "estimated_hours": 8
  }
}
```

### Example 2: Hypothesis Generation Workflow

```python
class HypothesisGenerator:
    """
    Systematic hypothesis generation workflow.
    """

    def __init__(self, knowledge_base_path: str):
        self.kb = self._load_knowledge_base(knowledge_base_path)
        self.existing_hypotheses = self._load_existing()

    def generate_from_observation(self, observation: str) -> dict:
        """
        Convert a market observation into a structured hypothesis.
        """
        # 1. Classify the observation
        category = self._classify_observation(observation)

        # 2. Extract tradeable components
        components = self._extract_components(observation)

        # 3. Generate hypothesis statement
        hypothesis = self._format_hypothesis(components)

        # 4. Check for duplicates
        if self._is_duplicate(hypothesis):
            raise ValueError("Similar hypothesis already exists")

        # 5. Generate hypothesis card
        card = {
            "id": self._generate_id(),
            "title": self._generate_title(components),
            "hypothesis": hypothesis,
            "edge_rationale": self._generate_rationale(category, components),
            "entry_rules": self._suggest_entry_rules(components),
            "exit_rules": self._suggest_exit_rules(components),
            "expected_metrics": self._estimate_metrics(category),
            "validation_criteria": self._default_validation_criteria(),
            "status": "draft",
            "metadata": {
                "created_date": datetime.now().isoformat(),
                "author": "HypothesisGenerator",
                "tags": [category],
                "priority": 3,
                "estimated_hours": 8
            }
        }

        return card

    def prioritize_backlog(self, hypotheses: list[dict]) -> list[dict]:
        """
        Score and prioritize hypothesis backlog.
        """
        scored = []
        for h in hypotheses:
            score = self._calculate_priority_score(h)
            scored.append((score, h))

        return [h for _, h in sorted(scored, reverse=True)]

    def _calculate_priority_score(self, hypothesis: dict) -> float:
        """
        Priority score based on:
        - Expected Sharpe (higher = better)
        - Estimated hours (lower = better)
        - Academic support (more = better)
        - Novelty (unique = better)
        """
        expected_sharpe = hypothesis["expected_metrics"]["sharpe_ratio"]["min"]
        hours = hypothesis["metadata"]["estimated_hours"]
        academic_refs = len(hypothesis["edge_rationale"].get("academic_support", []))

        score = (
            expected_sharpe * 2.0 +      # Weight Sharpe heavily
            (20 - hours) * 0.1 +         # Prefer quick wins
            academic_refs * 0.5 +        # Academic support
            (5 - hypothesis["metadata"]["priority"])  # User priority
        )

        return score
```

## Common Mistakes

### 1. Vague Hypotheses

```markdown
# WRONG - Too vague
"RSI works for trading"

# RIGHT - Specific and falsifiable
"When RSI(14) crosses below 30 on ES 15-minute chart during RTH,
going long with a 2:1 reward-to-risk produces a Sharpe > 1.0
over 100+ trades because oversold conditions attract mean-reversion
buyers within the first 30 minutes."
```

### 2. Missing Edge Rationale

```markdown
# WRONG - No explanation
Entry: MA crossover
Exit: Trailing stop

# RIGHT - With rationale
Entry: 9/21 EMA crossover
Rationale: Short-term momentum shift detected before
institutional algo systems react (most use 20/50).
The faster signal captures early trend initiation.
```

### 3. Unvalidatable Criteria

```markdown
# WRONG - Can't measure "works"
Validation: Strategy works well

# RIGHT - Specific thresholds
Validation:
- Min Sharpe: 1.0 (after $4.50 RT commission)
- Max DD: 15% (fits Apex $2500 limit)
- Min trades: 200 (statistical significance)
- OOS retention: > 60% of IS Sharpe
```

### 4. Forgetting Transaction Costs

```python
# WRONG - Ignoring costs leads to false positives
expected_metrics = {
    "sharpe_ratio": {"min": 0.8}  # Before costs
}

# RIGHT - Account for real trading costs
# ES futures: $4.50 RT commission + 1 tick slippage = $17 per trade
expected_metrics = {
    "sharpe_ratio": {"min": 1.2},  # Before costs (expect 0.8 after)
    "notes": "Assumes $17 per RT (commission + slippage)"
}
```

### 5. Over-complicated Hypotheses

```markdown
# WRONG - Too many conditions
"When RSI < 30 AND MACD crosses up AND volume > 2x avg AND
price < lower BB AND it's Tuesday AND VIX > 20..."

# RIGHT - Simple, robust edge
"When RSI(14) < 30, mean reversion occurs within 4 bars
because algorithmic buyers target oversold conditions."

# Add complexity only if proven necessary through testing
```

## Hypothesis Status Workflow

```
draft → ready_for_test → in_sample_testing → out_of_sample_testing → validated/invalidated
                                    ↓                    ↓
                               invalidated          abandoned
```

### Status Transition Rules

| From | To | Condition |
|------|-----|-----------|
| draft | ready_for_test | All required fields complete |
| ready_for_test | in_sample_testing | Research session started |
| in_sample_testing | out_of_sample_testing | IS metrics meet criteria |
| in_sample_testing | invalidated | IS metrics fail criteria |
| out_of_sample_testing | validated | OOS retention > threshold |
| out_of_sample_testing | invalidated | OOS retention < threshold |
| any | abandoned | Manual decision to stop |
