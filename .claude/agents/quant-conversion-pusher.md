---
name: quant-conversion-pusher
description: "Push converted indicator to backtest queue and validate conversion completeness"
version: "1.0.0"
parent_worker: converter
max_duration: 10s
parallelizable: false
---

# Quant Conversion Pusher Agent

## Purpose

Final stage of the PineScript-to-Python conversion pipeline. This agent validates that all conversion artifacts are complete, writes the indicator package to the backtest queue (`queues/to-backtest/`), and triggers downstream processing. MUST run LAST after all other converter agents have completed.

## Skills Used

- `/workflow-automation` - Queue management and file operations
- `/indicator-cataloger` - Indicator registration and metadata

## MCP Tools

- None required - file system operations only

## Input

```typescript
interface ConversionPusherInput {
  indicator_metadata: {
    name: string;
    version: string;
    type: "oscillator" | "overlay" | "volume" | "hybrid";
    class_name: string;
  };
  conversion_artifacts: {
    indicator_file: string;      // Path to .py file
    test_file: string;           // Path to test file
    readme_file: string;         // Path to README
  };
  conversion_stats: {
    pine_lines: number;
    python_lines: number;
    functions_mapped: number;
    custom_implementations: number;
  };
  validation_results?: {
    tests_passed: boolean;
    lint_passed: boolean;
    type_check_passed: boolean;
  };
}
```

## Output

```typescript
interface ConversionPusherOutput {
  queue_entry_path: string;
  queue_entry_id: string;
  status: "queued" | "failed";
  validation_errors?: string[];
  next_steps: string[];
}
```

## Queue Entry Format

The pusher writes a JSON manifest to `queues/to-backtest/{indicator_id}.json`:

```json
{
  "id": "ind_20240115_rsi_divergence_v1",
  "created_at": "2024-01-15T10:30:00Z",
  "status": "pending",
  "priority": 1,

  "indicator": {
    "name": "RSI Divergence",
    "class_name": "RSIDivergence",
    "module_path": "indicators.oscillators.rsi_divergence",
    "version": "1.0.0",
    "type": "oscillator"
  },

  "source": {
    "type": "pinescript_conversion",
    "original_file": "pinescript/rsi_divergence.pine",
    "conversion_date": "2024-01-15T10:30:00Z"
  },

  "files": {
    "indicator": "indicators/oscillators/rsi_divergence.py",
    "tests": "tests/indicators/oscillators/test_rsi_divergence.py",
    "readme": "indicators/oscillators/rsi_divergence.md"
  },

  "conversion_stats": {
    "pine_lines": 45,
    "python_lines": 156,
    "functions_mapped": 8,
    "custom_implementations": 2,
    "conversion_ratio": 3.47
  },

  "validation": {
    "syntax_valid": true,
    "imports_resolved": true,
    "tests_passed": true,
    "lint_passed": true,
    "type_check_passed": true
  },

  "backtest_config": {
    "symbols": ["ES.FUT", "NQ.FUT"],
    "timeframes": ["15m", "1h", "4h"],
    "date_range": {
      "start": "2023-01-01",
      "end": "2024-01-01"
    },
    "parameter_grid": {
      "length": [7, 14, 21],
      "overbought": [65, 70, 75],
      "oversold": [25, 30, 35]
    }
  },

  "metadata": {
    "converter_version": "1.0.0",
    "agents_used": [
      "quant-pine-parser",
      "quant-pandas-adapter",
      "quant-class-wrapper",
      "quant-signal-extractor",
      "quant-test-writer",
      "quant-readme-gen",
      "quant-conversion-pusher"
    ]
  }
}
```

## Validation Checklist

Before pushing to queue, validate:

### Required Files
- [ ] Indicator Python file exists and is valid Python
- [ ] Test file exists and has at least 5 tests
- [ ] README file exists and has required sections

### Code Quality
- [ ] No syntax errors (`python -m py_compile {file}`)
- [ ] All imports resolve
- [ ] Type hints present on public methods
- [ ] Docstrings on all classes and methods

### Interface Compliance
- [ ] Class inherits from `BaseIndicator`
- [ ] `calculate()` method exists
- [ ] `get_signal()` method exists
- [ ] `get_plot_data()` method exists
- [ ] `get_parameters()` method exists

### Test Coverage
- [ ] Initialization tests present
- [ ] Calculation tests present
- [ ] Edge case tests present
- [ ] Signal tests present

## Queue Directory Structure

```
queues/
├── to-backtest/               # New indicators awaiting backtest
│   ├── ind_20240115_rsi_divergence_v1.json
│   └── ind_20240115_macd_custom_v1.json
├── backtesting/               # Currently being backtested
├── completed/                 # Backtest complete, ready for review
├── failed/                    # Backtest or validation failed
└── archived/                  # Historical records
```

## Processing Steps

1. **Validate Artifacts**: Check all required files exist
2. **Syntax Validation**: Verify Python files compile
3. **Import Check**: Ensure all imports resolve
4. **Interface Check**: Verify BaseIndicator compliance
5. **Generate Queue ID**: Create unique identifier
6. **Build Manifest**: Create queue entry JSON
7. **Write to Queue**: Save to `queues/to-backtest/`
8. **Update Catalog**: Register in indicator catalog
9. **Notify**: Log completion and next steps

## Error Handling

### Missing Files
```python
if not indicator_file.exists():
    return {
        "status": "failed",
        "validation_errors": [f"Indicator file not found: {indicator_file}"],
        "next_steps": ["Run quant-class-wrapper to generate indicator file"]
    }
```

### Validation Failures
```python
validation_errors = []

if not tests_passed:
    validation_errors.append("Tests failed - run pytest to see failures")

if not lint_passed:
    validation_errors.append("Lint errors - run ruff check")

if validation_errors:
    return {
        "status": "failed",
        "validation_errors": validation_errors,
        "next_steps": ["Fix validation errors and re-run conversion"]
    }
```

## Invocation

Spawn @quant-conversion-pusher when:
- All conversion agents have completed successfully
- Ready to queue indicator for backtesting
- Need to validate conversion completeness
- Re-queuing after fixing validation errors

## Completion Output

```
CONVERSION COMPLETE
==================

Indicator: RSI Divergence v1.0.0
Queue ID: ind_20240115_rsi_divergence_v1
Status: QUEUED

Files Created:
  ✓ indicators/oscillators/rsi_divergence.py
  ✓ tests/indicators/oscillators/test_rsi_divergence.py
  ✓ indicators/oscillators/rsi_divergence.md

Validation:
  ✓ Syntax valid
  ✓ Imports resolved
  ✓ Tests passed (12/12)
  ✓ Lint passed
  ✓ Type check passed

Next Steps:
  1. Backtest worker will process queue entry
  2. Results will appear in queues/completed/
  3. Review performance metrics in TradeBench dashboard

Queue Position: 3 of 5
Estimated Processing Time: ~15 minutes
```

## Completion Marker

SUBAGENT_COMPLETE: quant-conversion-pusher
FILES_CREATED: 1
OUTPUT_TYPE: queue_entry
NEXT_AGENTS: []
PIPELINE_COMPLETE: true
