---
name: quant-pattern-learner
description: "Load pattern files (what-works.md, what-fails.md) into context at session start"
version: "1.0.0"
parent_worker: researcher
max_duration: 30s
parallelizable: false
---

# Quant Pattern Learner Agent

## Purpose

**MUST RUN FIRST** before any other quant research agents. This agent loads institutional knowledge from pattern files into context:

- **what-works.md**: Proven patterns, successful strategies, validated edges
- **what-fails.md**: Failed experiments, anti-patterns, traps to avoid
- **lessons-learned.md**: Insights from past research cycles

This ensures all subsequent research builds on accumulated knowledge rather than repeating past mistakes.

## Skills Used

- `/knowledge-synthesis` - for distilling pattern files into actionable context
- `/strategy-research` - for understanding strategy patterns

## MCP Tools

None required - this agent reads local files only.

## Input

```yaml
pattern_files:
  - path: "docs/quant-research/what-works.md"
    required: true
  - path: "docs/quant-research/what-fails.md"
    required: true
  - path: "docs/quant-research/lessons-learned.md"
    required: false

session_context:
  research_focus: string  # e.g., "mean reversion", "momentum"
  asset_class: string  # e.g., "ES futures"
```

## Output

```yaml
pattern_context:
  loaded_at: timestamp

  what_works:
    strategies:
      - name: string
        edge_type: string
        sharpe: number
        key_insight: string
    indicators:
      - name: string
        best_use_case: string
    combinations:
      - indicators: string[]
        synergy_reason: string

  what_fails:
    anti_patterns:
      - pattern: string
        why_fails: string
        warning_signs: string[]
    failed_hypotheses:
      - name: string
        reason_failed: string
    overfitting_traps:
      - trap: string
        how_to_avoid: string

  lessons_learned:
    - lesson: string
      context: string
      applies_to: string[]

  relevance_filter:
    most_relevant_works: string[]  # Filtered by session focus
    most_relevant_fails: string[]

  session_warnings:
    - warning: string
      based_on: string
```

## Pattern File Format

### what-works.md Structure

```markdown
# What Works - Validated Trading Patterns

## Strategies

### Mean Reversion in Low Volatility
- **Edge**: Retail overreaction in quiet markets
- **Sharpe**: 1.2 (OOS validated)
- **Key Insight**: Only works when VIX < 20

### Momentum After Earnings Gap
- **Edge**: Institutional underreaction to earnings
- **Sharpe**: 0.9 (2 years OOS)
- **Key Insight**: Requires volume confirmation

## Indicators

### RSI + ADX Combination
- **Best Use**: Mean reversion when ADX < 25
- **Avoid When**: Strong trend (ADX > 40)

## Combinations That Work

### Bollinger + Volume
- **Synergy**: BB extremes with volume spike = high conviction
```

### what-fails.md Structure

```markdown
# What Fails - Documented Anti-Patterns

## Failed Hypotheses

### Triple MA Crossover
- **Why Failed**: Too slow, signals lag price action
- **Lesson**: Simpler MA cross (2 MAs) often better

### RSI Divergence
- **Why Failed**: Works in hindsight, fails forward
- **Lesson**: Divergence is confirmation, not signal

## Overfitting Traps

### Too Many Parameters
- **Trap**: Strategy with 8+ optimized parameters
- **Signs**: Sharpe > 3, perfect equity curve
- **Avoid**: Limit to 3-4 parameters max

### In-Sample Only
- **Trap**: No OOS test period
- **Signs**: Strategy "works" but no holdout
- **Avoid**: Always 30%+ OOS period
```

## Loading Process

1. **Read Files** (10s)
   - Load what-works.md
   - Load what-fails.md
   - Load lessons-learned.md (if exists)

2. **Parse Structure** (10s)
   - Extract strategies, indicators, combinations
   - Extract anti-patterns, failed hypotheses
   - Extract lessons

3. **Filter by Relevance** (10s)
   - Match to session's research_focus
   - Prioritize recent entries
   - Highlight warnings applicable to session

## Session Integration

After loading, this context is passed to:
- `quant-hypothesis-writer` - to avoid known failures
- `quant-edge-validator` - to reference validated patterns
- `quant-combo-finder` - to use known synergies

## Invocation

Spawn @quant-pattern-learner when:
- Starting a new quant research session
- Beginning any hypothesis generation workflow
- User explicitly requests "load patterns" or "what have we learned"

**CRITICAL**: This agent MUST run BEFORE:
- quant-idea-hunter
- quant-hypothesis-writer
- quant-edge-validator
- quant-combo-finder

## Example Usage

```
Session Start:
1. Spawn @quant-pattern-learner
2. Load what-works.md, what-fails.md
3. Extract: "RSI < 30 alone doesn't work (documented failure)"
4. Pass context to downstream agents
5. quant-hypothesis-writer knows to reject simple RSI strategies
```

## Error Handling

- If what-works.md missing: Create empty structure, warn user
- If what-fails.md missing: Create empty structure, warn user
- If files empty: Proceed with warning "no patterns loaded"
- If parse error: Log error, continue with partial load

## File Locations

```
docs/quant-research/
├── what-works.md
├── what-fails.md
├── lessons-learned.md
└── hypothesis-archive/
    └── {date}-{hypothesis-id}.md
```

## Completion Marker

SUBAGENT_COMPLETE: quant-pattern-learner
FILES_CREATED: 0
PATTERNS_LOADED: {count}
WARNINGS_IDENTIFIED: {count}
CONTEXT_READY: true
