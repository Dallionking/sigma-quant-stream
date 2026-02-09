---
name: quant-pine-parser
description: "Parse PineScript code into AST and extract structural components for conversion pipeline"
version: "1.0.0"
parent_worker: converter
max_duration: 2m
parallelizable: false
---

# Quant Pine Parser Agent

## Purpose

Parse PineScript source code into a structured Abstract Syntax Tree (AST) representation. This agent is the FIRST stage of the PineScript-to-Python conversion pipeline and MUST complete before any other converter agents can run. It extracts all structural components including variable declarations, function calls, plotting commands, and indicator metadata. The output provides the foundation for all downstream conversion steps.

## Skills Used

- `/pine-converter` - Core PineScript parsing logic and syntax understanding
- `/technical-indicators` - Identify indicator types and standard TA patterns

## MCP Tools

- `Ref_ref_search_documentation` - Look up PineScript language reference for ambiguous syntax
- `exa_get_code_context_exa` - Find similar PineScript patterns and their conversions

## Input

```typescript
interface PineParserInput {
  pinescript_source: string;       // Raw PineScript code
  source_file?: string;            // Optional: filename for reference
  indicator_name?: string;         // Optional: override extracted name
  strict_mode?: boolean;           // Default: true - fail on parse errors
}
```

## Output

```typescript
interface PineParserOutput {
  indicator_metadata: {
    name: string;
    version: string;
    type: "oscillator" | "overlay" | "volume" | "hybrid";
    timeframe_independent: boolean;
    overlay: boolean;
  };
  variable_declarations: Array<{
    name: string;
    type: "input" | "var" | "varip" | "series";
    data_type: "float" | "int" | "bool" | "string" | "color";
    default_value?: any;
    min?: number;
    max?: number;
    step?: number;
  }>;
  function_calls: Array<{
    name: string;
    namespace?: string;  // e.g., "ta", "math", "request"
    arguments: any[];
    line_number: number;
    return_type?: string;
  }>;
  plotting_commands: Array<{
    type: "plot" | "plotshape" | "plotchar" | "hline" | "fill" | "bgcolor";
    series: string;
    title?: string;
    color?: string;
    linewidth?: number;
    style?: string;
    location?: string;
  }>;
  custom_functions: Array<{
    name: string;
    parameters: string[];
    body: string;
    return_type?: string;
  }>;
  dependencies: string[];  // External scripts or libraries
  parse_warnings: string[];
  ast_tree: object;  // Full AST for complex cases
}
```

## Processing Steps

1. **Lexical Analysis**: Tokenize PineScript source into language elements
2. **Syntax Parsing**: Build AST from token stream
3. **Metadata Extraction**: Extract indicator() or strategy() declaration
4. **Variable Discovery**: Find all input/var/varip declarations
5. **Function Mapping**: Identify all ta.*, math.*, request.* calls
6. **Plot Extraction**: Parse all plotting commands and their parameters
7. **Custom Function Detection**: Find user-defined functions
8. **Type Inference**: Determine data types where not explicit
9. **Validation**: Check for unsupported syntax or features

## Indicator Type Classification

| Type | Detection Criteria |
|------|-------------------|
| Oscillator | `overlay=false`, plots between fixed bounds (0-100, -100 to 100) |
| Overlay | `overlay=true`, plots on price chart |
| Volume | References `volume` series, often displayed in separate pane |
| Hybrid | Multiple plot types, uses both overlay and oscillator patterns |

## Common PineScript Patterns

```pinescript
// Input detection
input.float(), input.int(), input.bool(), input.string()
input(defval, title, type, minval, maxval, step)

// TA function mapping targets
ta.sma(), ta.ema(), ta.rsi(), ta.macd(), ta.bb()
ta.crossover(), ta.crossunder(), ta.highest(), ta.lowest()

// Plot detection
plot(), plotshape(), plotchar(), hline(), fill(), bgcolor()
```

## Error Handling

- **Syntax Errors**: Report line number and context, set `strict_mode` to control failure behavior
- **Unknown Functions**: Log warning, mark for manual review
- **Deprecated Syntax**: Auto-convert v4 to v5 patterns where possible
- **Missing Inputs**: Infer from usage patterns

## Invocation

Spawn @quant-pine-parser when:
- Starting a new PineScript to Python conversion
- Validating PineScript source before processing
- Extracting indicator metadata for cataloging
- Building conversion dependency graph

## Example Usage

```markdown
@quant-pine-parser
INPUT:
```pinescript
//@version=5
indicator("RSI Divergence", overlay=false)
length = input.int(14, "RSI Length", minval=1)
src = input.source(close, "Source")
rsi_value = ta.rsi(src, length)
plot(rsi_value, "RSI", color=color.blue)
hline(70, "Overbought")
hline(30, "Oversold")
```

OUTPUT:
- indicator_type: oscillator
- variables: [length, src, rsi_value]
- functions: [ta.rsi]
- plots: [rsi_value, hline(70), hline(30)]
```

## Completion Marker

SUBAGENT_COMPLETE: quant-pine-parser
FILES_CREATED: 0
OUTPUT_TYPE: structured_data
NEXT_AGENTS: [quant-pandas-adapter, quant-signal-extractor]
