---
name: quant-readme-gen
description: "Generate comprehensive documentation for converted indicators including usage examples and visual references"
version: "1.0.0"
parent_worker: converter
max_duration: 1m
parallelizable: true
---

# Quant README Generator Agent

## Purpose

Generate comprehensive documentation for converted indicators. This agent creates clear, well-structured README files that include indicator description, parameter documentation, usage examples, signal interpretation guides, and visual references. The documentation enables traders and developers to quickly understand and use the indicator.

## Skills Used

- `/documentation` - Documentation generation patterns
- `/technical-indicators` - Indicator behavior and interpretation

## MCP Tools

- `Ref_ref_search_documentation` - Find official indicator documentation for reference
- `exa_web_search_exa` - Find trading examples and interpretations

## Input

```typescript
interface ReadmeGenInput {
  indicator_metadata: {
    name: string;
    version: string;
    type: "oscillator" | "overlay" | "volume" | "hybrid";
    description: string;
  };
  parameters: Array<{
    name: string;
    type: string;
    default: any;
    min?: number;
    max?: number;
    description: string;
  }>;
  output_columns: string[];
  signal_types: string[];
  original_pinescript?: string;
  class_name: string;
  file_path: string;
}
```

## Output

```typescript
interface ReadmeGenOutput {
  readme_content: string;
  readme_path: string;
}
```

## Documentation Template

```markdown
# {Indicator Name}

> {Short description - one sentence}

## Overview

{Detailed description of what the indicator does, its purpose, and common use cases. 2-3 paragraphs.}

### Indicator Type

- **Category**: {oscillator|overlay|volume|hybrid}
- **Overlay**: {Yes|No} - {explanation of where it displays}
- **Timeframe**: Works on all timeframes

### Original Source

{If converted from PineScript, reference the original}

---

## Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
{parameter_table_rows}

### Parameter Guidelines

{parameter_usage_tips}

---

## Outputs

### Calculated Columns

The indicator adds the following columns to the DataFrame:

| Column | Type | Description |
|--------|------|-------------|
{output_column_table_rows}

### Signal Structure

```python
{
    "direction": "long" | "short" | "neutral",
    "strength": 0.0 - 1.0,
    "reason": "Human-readable explanation",
    "timestamp": datetime
}
```

---

## Usage

### Basic Usage

```python
from indicators.{category}.{module} import {ClassName}
import pandas as pd

# Create indicator with default parameters
indicator = {ClassName}()

# Load your OHLCV data
df = pd.read_csv("market_data.csv")

# Calculate indicator values
df = indicator.calculate(df)

# Get trading signal
signal = indicator.get_signal(df)
print(f"Signal: {signal['direction']} (strength: {signal['strength']})")
```

### Custom Parameters

```python
# Create indicator with custom parameters
indicator = {ClassName}(
    {custom_params_example}
)

df = indicator.calculate(df)
```

### Integration with Sigma-Quant

```python
from trading.signal_manager import SignalManager
from indicators.{category}.{module} import {ClassName}

# Register indicator with signal manager
signal_manager = SignalManager()
signal_manager.add_indicator({ClassName}(length=14))

# Process market data
signal = signal_manager.process(df)
```

---

## Signal Interpretation

### {Signal Type 1}

{Explanation of when this signal fires and what it means}

**Bullish Signal:**
- Condition: {condition}
- Interpretation: {what it means}
- Recommended Action: {suggestion}

**Bearish Signal:**
- Condition: {condition}
- Interpretation: {what it means}
- Recommended Action: {suggestion}

### Signal Strength

| Strength | Interpretation | Recommended Action |
|----------|---------------|-------------------|
| 0.0 - 0.3 | Weak | Wait for confirmation |
| 0.3 - 0.6 | Moderate | Consider entry with tight stop |
| 0.6 - 0.8 | Strong | Standard position size |
| 0.8 - 1.0 | Very Strong | Full position size |

---

## Chart Display

### Plot Configuration

```python
plot_data = indicator.get_plot_data(df)
# Returns:
{
    "series": [...],
    "pane": "{pane}",
    "y_range": {y_range},
    "horizontal_lines": [...]
}
```

### Visual Example

```
{ASCII chart representation or description}
```

---

## Best Practices

### Recommended Combinations

- **Trend Confirmation**: Combine with {complementary_indicator_1}
- **Entry Timing**: Use with {complementary_indicator_2}
- **Risk Management**: Set stops based on {risk_suggestion}

### Common Pitfalls

1. **{Pitfall 1}**: {explanation and solution}
2. **{Pitfall 2}**: {explanation and solution}
3. **{Pitfall 3}**: {explanation and solution}

### Timeframe Considerations

| Timeframe | Recommended Settings | Notes |
|-----------|---------------------|-------|
| 1m - 5m | {settings} | {notes} |
| 15m - 1h | {settings} | {notes} |
| 4h - 1D | {settings} | {notes} |

---

## Mathematical Formula

{If applicable, show the mathematical formula}

```
{formula_representation}
```

---

## Performance Notes

- **Calculation Time**: {benchmark_info}
- **Memory Usage**: {memory_info}
- **Lookback Period**: Requires {N} bars of history

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | {date} | Initial conversion from PineScript |

---

## Related Indicators

- [{Related Indicator 1}](link) - {relationship}
- [{Related Indicator 2}](link) - {relationship}

---

## References

- [Original PineScript]({link_if_available})
- [Technical Analysis Theory]({reference_link})
- [Sigma-Quant Indicator Guidelines](../INDICATOR_GUIDELINES.md)

---

*Generated by Sigma-Quant Indicator Converter v1.0*
```

## Processing Steps

1. **Extract Metadata**: Gather indicator name, type, version
2. **Format Parameters**: Create parameter table with descriptions
3. **Document Outputs**: List all calculated columns
4. **Generate Usage Examples**: Create copy-paste ready code samples
5. **Write Signal Guide**: Explain signal interpretation
6. **Add Best Practices**: Include trading recommendations
7. **Format Markdown**: Ensure consistent formatting

## File Location

```
indicators/
├── oscillators/
│   ├── rsi.py
│   └── README.md          # One README per category OR
│       └── rsi.md         # One per indicator
├── overlays/
└── volume/
```

## Invocation

Spawn @quant-readme-gen when:
- Completing a PineScript conversion
- Updating indicator documentation
- Generating API documentation
- Creating user guides

## Example Output Excerpt

```markdown
# RSI Divergence Indicator

> Relative Strength Index with automatic divergence detection for trend reversal signals.

## Overview

The RSI Divergence indicator combines the classic RSI oscillator with automatic
divergence detection. When price makes a new high but RSI makes a lower high,
it signals potential bearish reversal. Conversely, when price makes a new low
but RSI makes a higher low, it signals potential bullish reversal.

### Indicator Type

- **Category**: Oscillator
- **Overlay**: No - displays in separate pane
- **Timeframe**: Works on all timeframes, best on 15m+

## Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| length | int | 14 | 1-100 | RSI calculation period |
| overbought | float | 70 | 50-95 | Overbought threshold |
| oversold | float | 30 | 5-50 | Oversold threshold |
| divergence_lookback | int | 5 | 2-20 | Bars to look back for divergence |
```

## Completion Marker

SUBAGENT_COMPLETE: quant-readme-gen
FILES_CREATED: 1
OUTPUT_TYPE: markdown_file
NEXT_AGENTS: [quant-conversion-pusher]
