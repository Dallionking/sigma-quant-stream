---
name: quant-pattern-knowledge
description: "Pattern file read/write for tracking what-works.md and what-fails.md knowledge bases"
version: "1.0.0"
triggers:
  - "when documenting successful strategies"
  - "when recording failed experiments"
  - "when updating pattern knowledge base"
  - "when deduplicating research findings"
---

# Quant Pattern Knowledge

## Purpose

Manages the institutional knowledge base of what trading patterns work and what fails. This skill ensures that research findings are captured, deduplicated, and accessible for future reference. Prevents rediscovering failures and accelerates finding new edges by building on proven patterns.

## When to Use

- After completing any hypothesis validation (pass or fail)
- When starting new research (check what's already known)
- During strategy review sessions
- When onboarding new quant team members
- Before importing external strategies

## Key Concepts

### Knowledge Base Structure

```
.claude/knowledge/quant/
├── what-works.md           # Validated patterns
├── what-fails.md           # Invalidated patterns
├── under-investigation.md  # Active research
├── pattern-index.json      # Searchable index
└── archives/
    ├── 2024-patterns.md    # Yearly archives
    └── 2025-patterns.md
```

### Pattern Categories

| Category | Description | Typical Timeframe |
|----------|-------------|-------------------|
| **Mean Reversion** | Price returns to average | Hours to days |
| **Momentum** | Trend continuation | Days to weeks |
| **Breakout** | Range expansion | Hours to days |
| **Scalping** | Quick in/out | Minutes |
| **Swing** | Multi-day holds | Days to weeks |
| **Volatility** | Vol expansion/contraction | Variable |
| **Calendar** | Time-based patterns | Specific times |
| **Microstructure** | Order flow patterns | Seconds to minutes |

### Deduplication Rules

Patterns are considered duplicates if:

1. **Same core indicator** with similar parameters (±20%)
2. **Same entry logic** on same timeframe
3. **Same edge rationale** (why it works)
4. **Same market condition** applicability

## Patterns & Templates

### what-works.md Format

```markdown
# What Works - Sigma-Quant Pattern Library

> Last Updated: {YYYY-MM-DD}
> Total Patterns: {N}
> Categories: Mean Reversion ({N}), Momentum ({N}), ...

---

## Pattern: {PATTERN-ID} - {Title}

### Summary
{One-line description of the pattern}

### Category
{Mean Reversion | Momentum | Breakout | Scalping | Swing | Volatility | Calendar | Microstructure}

### Instruments
{ES, NQ, YM, GC, etc.}

### Timeframes
{1m, 5m, 15m, 1H, 4H, D}

### Edge Rationale
{Why this works - behavioral, structural, microstructure}

### Entry Rules
```
1. {Condition 1}
2. {Condition 2}
3. {Condition 3}
```

### Exit Rules
```
- Take Profit: {Rule}
- Stop Loss: {Rule}
- Time Exit: {Rule}
```

### Key Parameters
| Parameter | Value | Sensitivity |
|-----------|-------|-------------|
| {Param1} | {Value} | {Low/Medium/High} |
| {Param2} | {Value} | {Low/Medium/High} |

### Performance Metrics
| Metric | In-Sample | Out-of-Sample |
|--------|-----------|---------------|
| Sharpe | {X} | {X} |
| Win Rate | {X}% | {X}% |
| Max DD | {X}% | {X}% |
| Trades | {N} | {N} |
| Period | {dates} | {dates} |

### Validation History
- **Validated**: {YYYY-MM-DD}
- **Last Reviewed**: {YYYY-MM-DD}
- **Status**: {Active | Monitoring | Deprecated}

### Notes
{Any additional observations, edge cases, or warnings}

### Related Patterns
- {PATTERN-ID-X}: {Brief description}
- {PATTERN-ID-Y}: {Brief description}

---
```

### what-fails.md Format

```markdown
# What Fails - Sigma-Quant Anti-Pattern Library

> Last Updated: {YYYY-MM-DD}
> Total Anti-Patterns: {N}
> **Purpose**: Prevent wasting time on proven failures

---

## Anti-Pattern: {ANTI-ID} - {Title}

### Summary
{One-line description of why this fails}

### Category
{Mean Reversion | Momentum | Breakout | etc.}

### Why It Seems Like It Should Work
{The intuitive appeal that makes people try this}

### Why It Actually Fails
{The real reason - data snooping, costs, regime change, etc.}

### Evidence
- **Test Period**: {dates}
- **Sample Size**: {N trades}
- **Sharpe Before Costs**: {X}
- **Sharpe After Costs**: {X}
- **Key Finding**: {What killed it}

### Variations Tested
| Variation | Result |
|-----------|--------|
| {Variation 1} | {Failed: reason} |
| {Variation 2} | {Failed: reason} |
| {Variation 3} | {Failed: reason} |

### Red Flags That Indicated Failure
- [ ] Sharpe > 3.0 (overfitting)
- [ ] Win rate > 80% (look-ahead)
- [ ] OOS decay > 50%
- [ ] Too few trades (< 100)
- [ ] {Other specific red flag}

### Don't Waste Time On
{Specific variations not worth testing}

### Exception Cases
{Any conditions where this MIGHT work - rare}

### Date Invalidated
{YYYY-MM-DD}

### Tested By
{Researcher name/ID}

---
```

### Pattern Index JSON Schema

```json
{
  "version": "1.0.0",
  "last_updated": "2025-01-26",
  "patterns": {
    "works": [
      {
        "id": "PATTERN-001",
        "title": "RTH Gap Fade",
        "category": "mean_reversion",
        "instruments": ["ES", "NQ"],
        "timeframes": ["15m"],
        "sharpe": 1.42,
        "status": "active",
        "keywords": ["gap", "fade", "mean_reversion", "session_open"],
        "file_ref": "what-works.md#pattern-001"
      }
    ],
    "fails": [
      {
        "id": "ANTI-001",
        "title": "Simple RSI Oversold",
        "category": "mean_reversion",
        "why_failed": "No edge after transaction costs",
        "keywords": ["RSI", "oversold", "mean_reversion"],
        "file_ref": "what-fails.md#anti-001"
      }
    ]
  },
  "statistics": {
    "total_works": 42,
    "total_fails": 156,
    "categories": {
      "mean_reversion": {"works": 15, "fails": 48},
      "momentum": {"works": 12, "fails": 35},
      "breakout": {"works": 8, "fails": 42},
      "other": {"works": 7, "fails": 31}
    }
  }
}
```

### Python Pattern Manager

```python
import json
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Literal

@dataclass
class Pattern:
    id: str
    title: str
    category: str
    summary: str
    instruments: list[str]
    timeframes: list[str]
    entry_rules: list[str]
    exit_rules: dict
    parameters: dict
    metrics: dict
    edge_rationale: str
    status: Literal["active", "monitoring", "deprecated"]
    validated_date: str
    keywords: list[str]

@dataclass
class AntiPattern:
    id: str
    title: str
    category: str
    summary: str
    why_seems_good: str
    why_fails: str
    evidence: dict
    variations_tested: list[dict]
    red_flags: list[str]
    invalidated_date: str
    tested_by: str
    keywords: list[str]

class PatternKnowledgeBase:
    """
    Manages the quant pattern knowledge base.
    """

    def __init__(self, kb_path: str = ".claude/knowledge/quant"):
        self.kb_path = Path(kb_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)
        self.index = self._load_index()

    def _load_index(self) -> dict:
        index_path = self.kb_path / "pattern-index.json"
        if index_path.exists():
            return json.loads(index_path.read_text())
        return {"version": "1.0.0", "patterns": {"works": [], "fails": []}, "statistics": {}}

    def _save_index(self):
        index_path = self.kb_path / "pattern-index.json"
        index_path.write_text(json.dumps(self.index, indent=2))

    def _generate_content_hash(self, pattern: dict) -> str:
        """Generate hash for deduplication."""
        key_fields = [
            pattern.get("category", ""),
            pattern.get("edge_rationale", ""),
            str(pattern.get("entry_rules", [])),
            str(pattern.get("timeframes", []))
        ]
        content = "|".join(key_fields).lower()
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def check_duplicate(self, pattern: dict) -> Optional[str]:
        """
        Check if pattern is duplicate. Returns existing pattern ID if duplicate.
        """
        new_hash = self._generate_content_hash(pattern)

        for existing in self.index["patterns"]["works"]:
            existing_hash = self._generate_content_hash(existing)
            if new_hash == existing_hash:
                return existing["id"]

            # Also check for similar titles
            if self._similar_title(pattern["title"], existing["title"]):
                return existing["id"]

        return None

    def _similar_title(self, title1: str, title2: str) -> bool:
        """Check if titles are similar (Jaccard similarity > 0.7)."""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        if not words1 or not words2:
            return False

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return (intersection / union) > 0.7

    def add_working_pattern(self, pattern: Pattern) -> str:
        """Add a validated pattern to what-works."""
        # Check for duplicates
        dup_id = self.check_duplicate(asdict(pattern))
        if dup_id:
            raise ValueError(f"Duplicate of existing pattern: {dup_id}")

        # Generate ID if not provided
        if not pattern.id:
            count = len(self.index["patterns"]["works"]) + 1
            pattern.id = f"PATTERN-{count:03d}"

        # Add to index
        self.index["patterns"]["works"].append({
            "id": pattern.id,
            "title": pattern.title,
            "category": pattern.category,
            "instruments": pattern.instruments,
            "timeframes": pattern.timeframes,
            "sharpe": pattern.metrics.get("sharpe_oos", 0),
            "status": pattern.status,
            "keywords": pattern.keywords,
            "file_ref": f"what-works.md#{pattern.id.lower()}"
        })

        # Update statistics
        self._update_statistics()

        # Save index
        self._save_index()

        # Append to what-works.md
        self._append_to_works_file(pattern)

        return pattern.id

    def add_anti_pattern(self, anti_pattern: AntiPattern) -> str:
        """Add a failed pattern to what-fails."""
        # Generate ID if not provided
        if not anti_pattern.id:
            count = len(self.index["patterns"]["fails"]) + 1
            anti_pattern.id = f"ANTI-{count:03d}"

        # Add to index
        self.index["patterns"]["fails"].append({
            "id": anti_pattern.id,
            "title": anti_pattern.title,
            "category": anti_pattern.category,
            "why_failed": anti_pattern.why_fails[:100],
            "keywords": anti_pattern.keywords,
            "file_ref": f"what-fails.md#{anti_pattern.id.lower()}"
        })

        # Update statistics
        self._update_statistics()

        # Save index
        self._save_index()

        # Append to what-fails.md
        self._append_to_fails_file(anti_pattern)

        return anti_pattern.id

    def search(self, query: str, search_type: str = "all") -> list[dict]:
        """
        Search patterns by keyword.
        search_type: "works", "fails", or "all"
        """
        results = []
        query_lower = query.lower()

        if search_type in ["works", "all"]:
            for p in self.index["patterns"]["works"]:
                if self._matches_query(p, query_lower):
                    results.append({"type": "works", **p})

        if search_type in ["fails", "all"]:
            for p in self.index["patterns"]["fails"]:
                if self._matches_query(p, query_lower):
                    results.append({"type": "fails", **p})

        return results

    def _matches_query(self, pattern: dict, query: str) -> bool:
        """Check if pattern matches search query."""
        searchable = [
            pattern.get("title", ""),
            pattern.get("category", ""),
            " ".join(pattern.get("keywords", [])),
            pattern.get("why_failed", "")
        ]
        return query in " ".join(searchable).lower()

    def _update_statistics(self):
        """Update statistics in index."""
        works = self.index["patterns"]["works"]
        fails = self.index["patterns"]["fails"]

        categories = {}
        for p in works:
            cat = p["category"]
            if cat not in categories:
                categories[cat] = {"works": 0, "fails": 0}
            categories[cat]["works"] += 1

        for p in fails:
            cat = p["category"]
            if cat not in categories:
                categories[cat] = {"works": 0, "fails": 0}
            categories[cat]["fails"] += 1

        self.index["statistics"] = {
            "total_works": len(works),
            "total_fails": len(fails),
            "categories": categories
        }
        self.index["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    def _append_to_works_file(self, pattern: Pattern):
        """Append pattern to what-works.md."""
        works_path = self.kb_path / "what-works.md"

        entry = f"""
---

## Pattern: {pattern.id} - {pattern.title}

### Summary
{pattern.summary}

### Category
{pattern.category}

### Instruments
{', '.join(pattern.instruments)}

### Timeframes
{', '.join(pattern.timeframes)}

### Edge Rationale
{pattern.edge_rationale}

### Entry Rules
```
{chr(10).join(f"{i+1}. {rule}" for i, rule in enumerate(pattern.entry_rules))}
```

### Exit Rules
```
- Take Profit: {pattern.exit_rules.get('take_profit', 'N/A')}
- Stop Loss: {pattern.exit_rules.get('stop_loss', 'N/A')}
- Time Exit: {pattern.exit_rules.get('time_exit', 'N/A')}
```

### Performance Metrics
| Metric | In-Sample | Out-of-Sample |
|--------|-----------|---------------|
| Sharpe | {pattern.metrics.get('sharpe_is', 'N/A')} | {pattern.metrics.get('sharpe_oos', 'N/A')} |
| Win Rate | {pattern.metrics.get('winrate_is', 'N/A')}% | {pattern.metrics.get('winrate_oos', 'N/A')}% |
| Max DD | {pattern.metrics.get('maxdd_is', 'N/A')}% | {pattern.metrics.get('maxdd_oos', 'N/A')}% |

### Validation History
- **Validated**: {pattern.validated_date}
- **Status**: {pattern.status}

"""

        with open(works_path, 'a') as f:
            f.write(entry)

    def _append_to_fails_file(self, anti_pattern: AntiPattern):
        """Append anti-pattern to what-fails.md."""
        fails_path = self.kb_path / "what-fails.md"

        entry = f"""
---

## Anti-Pattern: {anti_pattern.id} - {anti_pattern.title}

### Summary
{anti_pattern.summary}

### Category
{anti_pattern.category}

### Why It Seems Like It Should Work
{anti_pattern.why_seems_good}

### Why It Actually Fails
{anti_pattern.why_fails}

### Evidence
- **Test Period**: {anti_pattern.evidence.get('test_period', 'N/A')}
- **Sample Size**: {anti_pattern.evidence.get('sample_size', 'N/A')} trades
- **Sharpe Before Costs**: {anti_pattern.evidence.get('sharpe_before', 'N/A')}
- **Sharpe After Costs**: {anti_pattern.evidence.get('sharpe_after', 'N/A')}

### Red Flags
{chr(10).join(f"- {flag}" for flag in anti_pattern.red_flags)}

### Date Invalidated
{anti_pattern.invalidated_date}

### Tested By
{anti_pattern.tested_by}

"""

        with open(fails_path, 'a') as f:
            f.write(entry)
```

## Examples

### Example 1: Adding a Working Pattern

```python
kb = PatternKnowledgeBase()

pattern = Pattern(
    id="",  # Auto-generated
    title="RTH Open Gap Fade",
    category="mean_reversion",
    summary="Fade gaps > 0.3% at RTH open for 50% fill within 60 min",
    instruments=["ES", "NQ"],
    timeframes=["15m"],
    entry_rules=[
        "Gap from prior close > 0.3%",
        "Enter within first 5 min of RTH",
        "Fade direction (short gaps up, long gaps down)"
    ],
    exit_rules={
        "take_profit": "50% gap fill",
        "stop_loss": "Gap extends 50%",
        "time_exit": "60 minutes"
    },
    parameters={
        "gap_threshold": {"value": 0.3, "sensitivity": "medium"},
        "fill_target": {"value": 0.5, "sensitivity": "low"}
    },
    metrics={
        "sharpe_is": 1.42,
        "sharpe_oos": 1.21,
        "winrate_is": 64.1,
        "winrate_oos": 61.8,
        "maxdd_is": 11.3,
        "maxdd_oos": 14.2
    },
    edge_rationale="Overnight gaps trigger retail stops; institutions revert to fair value",
    status="active",
    validated_date="2025-01-15",
    keywords=["gap", "fade", "mean_reversion", "session_open", "RTH"]
)

pattern_id = kb.add_working_pattern(pattern)
print(f"Added pattern: {pattern_id}")
```

### Example 2: Recording a Failed Pattern

```python
kb = PatternKnowledgeBase()

anti_pattern = AntiPattern(
    id="",  # Auto-generated
    title="Simple RSI Oversold/Overbought",
    category="mean_reversion",
    summary="RSI crosses below 30 = buy, above 70 = sell",
    why_seems_good="Classic textbook indicator, widely taught",
    why_fails="No edge after transaction costs; too many traders use same signal",
    evidence={
        "test_period": "2020-01-01 to 2024-12-31",
        "sample_size": 1542,
        "sharpe_before": 0.42,
        "sharpe_after": -0.15
    },
    variations_tested=[
        {"variation": "RSI(7)", "result": "Sharpe 0.38 before costs"},
        {"variation": "RSI(21)", "result": "Sharpe 0.29 before costs"},
        {"variation": "RSI + Volume filter", "result": "Sharpe 0.51 before costs"},
        {"variation": "RSI + Trend filter", "result": "Sharpe 0.61 before costs, still negative after"}
    ],
    red_flags=[
        "Sharpe < 0.5 before costs",
        "High trade frequency amplifies costs",
        "Signal too crowded (everyone uses RSI)"
    ],
    invalidated_date="2025-01-10",
    tested_by="quant-team",
    keywords=["RSI", "oversold", "overbought", "mean_reversion", "crowded"]
)

anti_id = kb.add_anti_pattern(anti_pattern)
print(f"Added anti-pattern: {anti_id}")
```

### Example 3: Searching Before Research

```python
kb = PatternKnowledgeBase()

# Before starting new RSI research, check what's already known
results = kb.search("RSI")

print("=== Existing RSI Knowledge ===")
for r in results:
    if r["type"] == "works":
        print(f"WORKS: {r['id']} - {r['title']} (Sharpe: {r['sharpe']})")
    else:
        print(f"FAILS: {r['id']} - {r['title']} ({r['why_failed']})")

# Output:
# === Existing RSI Knowledge ===
# FAILS: ANTI-001 - Simple RSI Oversold/Overbought (No edge after transaction costs)
# WORKS: PATTERN-015 - RSI Divergence + Volume Spike (Sharpe: 1.31)
```

## Common Mistakes

### 1. Not Checking Before Research

```python
# WRONG: Starting research without checking knowledge base
def start_research(hypothesis):
    # Jump straight into testing
    return run_backtest(hypothesis)

# RIGHT: Always check existing knowledge first
def start_research(hypothesis):
    kb = PatternKnowledgeBase()

    # Check for existing patterns
    existing = kb.search(hypothesis.keywords[0])

    if existing:
        print("Found existing knowledge:")
        for e in existing:
            print(f"  - {e['id']}: {e['title']}")

        # Ask for confirmation to proceed
        if not confirm_proceed():
            return None

    return run_backtest(hypothesis)
```

### 2. Recording Without Detail

```python
# WRONG: Vague failure record
anti_pattern = AntiPattern(
    title="MA Crossover",
    why_fails="Doesn't work",  # Too vague!
    ...
)

# RIGHT: Detailed failure analysis
anti_pattern = AntiPattern(
    title="9/21 EMA Crossover on ES 15m",
    why_fails="""
    1. Signal generates during sideways markets (70% of time)
    2. Whipsaws in consolidation eat profits
    3. By the time crossover confirms, 40% of move is done
    4. Transaction costs ($17/RT) consume 65% of gross profit
    5. Tested 12 MA combinations, all negative after costs
    """,
    ...
)
```

### 3. Failing to Update Status

```python
# WRONG: Pattern status never updated
# Pattern validated in 2023, never reviewed, still marked "active"

# RIGHT: Regular status reviews
def quarterly_pattern_review():
    kb = PatternKnowledgeBase()

    for pattern in kb.index["patterns"]["works"]:
        # Check recent performance
        recent_metrics = get_recent_metrics(pattern["id"])

        if recent_metrics["sharpe"] < 0.5:
            # Downgrade status
            update_pattern_status(pattern["id"], "monitoring")
            log_review(pattern["id"], "Downgraded due to performance decay")
        elif recent_metrics["sharpe"] < 0:
            update_pattern_status(pattern["id"], "deprecated")
            log_review(pattern["id"], "Deprecated - no longer profitable")
```

### 4. Duplicate Patterns with Slight Variations

```python
# WRONG: Adding variations as separate patterns
# PATTERN-001: RSI(14) < 30 buy
# PATTERN-002: RSI(7) < 30 buy
# PATTERN-003: RSI(21) < 30 buy
# These are the SAME pattern with different parameters!

# RIGHT: One pattern with parameter ranges
pattern = Pattern(
    title="RSI Oversold Mean Reversion",
    parameters={
        "rsi_period": {"value": 14, "tested_range": "7-21", "sensitivity": "low"},
        "threshold": {"value": 30, "tested_range": "25-35", "sensitivity": "medium"}
    },
    ...
)
```
