---
name: quant-queue-pusher
description: "Atomic queue file operations - writes to hypothesis and conversion queues using temp file + mv pattern"
version: "1.0.0"
parent_worker: researcher
max_duration: 10s
parallelizable: false
---

# Quant Queue Pusher Agent

## Purpose

**MUST RUN LAST** in the research pipeline. This agent handles atomic file operations for the queue system:

- **queues/hypotheses/**: Validated hypotheses ready for backtesting
- **queues/to-convert/**: Indicators ready for Python conversion

Uses temp file + atomic mv pattern to prevent partial writes and race conditions.

## Skills Used

None - this is a pure file operations agent.

## MCP Tools

None required - uses only file system operations.

## Input

```yaml
queue_operations:
  - type: "hypothesis" | "to-convert"
    payload: object  # The data to write
    filename: string  # Suggested filename (agent may adjust)
    priority: "high" | "normal" | "low"

atomic_options:
  use_temp_file: true  # Always true for safety
  verify_after_write: true
```

## Output

```yaml
operations_completed:
  - type: string
    filename: string
    path: string
    size_bytes: number
    checksum: string
    timestamp: string

  success_count: number
  failure_count: number

  failures:
    - type: string
      filename: string
      error: string
```

## Queue Directory Structure

```
queues/
├── hypotheses/
│   ├── high/           # High priority - test first
│   │   └── H-20260126-001.yaml
│   ├── normal/         # Normal priority
│   │   └── H-20260126-002.yaml
│   └── low/            # Low priority - test when capacity
│       └── H-20260126-003.yaml
│
├── to-convert/
│   ├── pinescript/     # PineScript indicators
│   │   └── tv-rsi-divergence.pine
│   └── paper/          # Academic paper methods
│       └── deprado-triple-barrier.yaml
│
└── archive/            # Completed items
    ├── tested/
    └── converted/
```

## Atomic Write Pattern

**CRITICAL**: Never write directly to queue files. Always use temp + mv.

```bash
# WRONG - Risk of partial write
echo "$content" > queues/hypotheses/H-001.yaml

# CORRECT - Atomic operation
TEMP=$(mktemp)
echo "$content" > "$TEMP"
mv "$TEMP" queues/hypotheses/high/H-001.yaml
```

### Why Atomic Matters

1. **Partial Write Prevention**: If agent crashes mid-write, temp file is orphaned (safe)
2. **Race Condition Safety**: Multiple agents can push without collision
3. **Consumer Safety**: Queue consumers only see complete files

## File Naming Convention

### Hypothesis Files
```
H-{YYYYMMDD}-{sequence}.yaml
H-20260126-001.yaml
H-20260126-002.yaml
```

### Indicator Files (to-convert)
```
{source}-{name}.{ext}
tv-rsi-divergence.pine
paper-deprado-metalabeling.yaml
```

## Hypothesis Queue Schema

```yaml
# queues/hypotheses/high/H-20260126-001.yaml
id: "H-20260126-001"
created_at: "2026-01-26T14:30:00Z"
priority: "high"
status: "queued"

hypothesis:
  title: string
  thesis: string
  edge_type: string
  counterparty: string

test_spec:
  symbols: ["ES.FUT"]
  timeframe: "15m"
  lookback_bars: 1000
  entry_rules: []
  exit_rules: []

expected_metrics:
  sharpe_range: [0.8, 1.5]
  max_drawdown_range: [0.1, 0.2]

reject_if:
  sharpe_below: 0.5
  drawdown_above: 0.25

metadata:
  source: "quant-idea-hunter"
  source_id: "web-search-123"
  validated_by: "quant-edge-validator"
  validation_score: 75
```

## To-Convert Queue Schema

```yaml
# queues/to-convert/pinescript/tv-rsi-divergence.yaml
id: "tv-rsi-divergence"
created_at: "2026-01-26T14:35:00Z"
source: "tradingview"
priority: "normal"

indicator:
  name: "RSI Divergence Detector"
  tv_url: "https://tradingview.com/script/abc123"
  author: "tradingview_user"

pinescript:
  version: "v5"
  code: |
    //@version=5
    indicator("RSI Divergence", overlay=false)
    ...
  line_count: 45

parameters:
  - name: "length"
    type: "int"
    default: 14

conversion_notes:
  - "Uses ta.rsi() - map to pandas_ta.rsi()"
  - "Has plot() calls - convert to return values"
```

## Priority Routing

| Priority | Path | When to Use |
|----------|------|-------------|
| high | `queues/hypotheses/high/` | Strong edge, validated, high confidence |
| normal | `queues/hypotheses/normal/` | Standard hypotheses |
| low | `queues/hypotheses/low/` | Exploratory, weak edge |

## Invocation

Spawn @quant-queue-pusher when:
- quant-hypothesis-writer has approved hypothesis
- quant-edge-validator approves hypothesis
- quant-tv-scraper has indicator ready for conversion
- quant-paper-analyzer extracts method for conversion

**CRITICAL**: This agent MUST run LAST after:
- quant-hypothesis-writer (hypothesis ready)
- quant-edge-validator (hypothesis approved)
- All validation complete

## Example Usage

```
Input:
{
  queue_operations: [
    {
      type: "hypothesis",
      payload: { ...hypothesis_card },
      filename: "H-20260126-001.yaml",
      priority: "high"
    }
  ]
}

Process:
1. Create temp file: /tmp/queue-xyz123
2. Write hypothesis YAML to temp
3. Validate YAML syntax
4. Atomic move: mv /tmp/queue-xyz123 queues/hypotheses/high/H-20260126-001.yaml
5. Verify file exists and is readable

Output:
{
  operations_completed: [{
    type: "hypothesis",
    filename: "H-20260126-001.yaml",
    path: "queues/hypotheses/high/H-20260126-001.yaml",
    size_bytes: 1234,
    checksum: "sha256:abc123...",
    timestamp: "2026-01-26T14:30:00Z"
  }],
  success_count: 1,
  failure_count: 0
}
```

## Error Handling

- If queue directory missing: Create it with proper permissions
- If temp file fails: Retry with different temp path
- If mv fails: Log error, leave temp file for inspection
- If validation fails: Reject write, return error details
- If disk full: Return clear error, do not attempt write

## Safety Checks

Before writing:
1. [ ] Payload is valid YAML/JSON
2. [ ] Filename matches convention
3. [ ] Target directory exists (create if not)
4. [ ] No existing file with same name (append sequence if collision)
5. [ ] Sufficient disk space

After writing:
1. [ ] File exists at target path
2. [ ] File is readable
3. [ ] File content matches payload (optional checksum verify)

## Completion Marker

SUBAGENT_COMPLETE: quant-queue-pusher
FILES_CREATED: {count}
HYPOTHESES_QUEUED: {count}
CONVERSIONS_QUEUED: {count}
FAILURES: {count}
