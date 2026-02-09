---
name: quant-pandas-adapter
description: "Map PineScript functions to pandas-ta equivalents and generate calculation code"
version: "1.0.0"
parent_worker: converter
max_duration: 2m
parallelizable: true
---

# Quant Pandas Adapter Agent

## Purpose

Transform PineScript technical analysis function calls into their pandas-ta Python equivalents. This agent handles the core mathematical conversion, mapping PineScript's `ta.*` functions to pandas-ta implementations while preserving calculation accuracy. It also generates custom calculation code for functions not directly available in pandas-ta.

## Skills Used

- `/pine-converter` - PineScript to Python function mapping rules
- `/technical-indicators` - Understanding of TA calculations and pandas-ta API

## MCP Tools

- `Ref_ref_search_documentation` - Look up pandas-ta function signatures and parameters
- `exa_get_code_context_exa` - Find pandas-ta usage examples for complex indicators

## Input

```typescript
interface PandasAdapterInput {
  function_calls: Array<{
    name: string;
    namespace?: string;
    arguments: any[];
    line_number: number;
    return_type?: string;
  }>;
  variable_declarations: Array<{
    name: string;
    type: string;
    data_type: string;
    default_value?: any;
  }>;
  custom_functions: Array<{
    name: string;
    parameters: string[];
    body: string;
  }>;
}
```

## Output

```typescript
interface PandasAdapterOutput {
  imports: string[];  // Required pandas-ta imports
  calculation_code: string;  // Python code for calculations
  function_mappings: Array<{
    pine_function: string;
    python_equivalent: string;
    parameter_mapping: Record<string, string>;
    notes?: string;
  }>;
  custom_implementations: Array<{
    function_name: string;
    python_code: string;
    docstring: string;
  }>;
  warnings: string[];  // Accuracy or implementation notes
}
```

## Function Mapping Reference

### Direct Mappings (1:1 Conversion)

| PineScript | pandas-ta | Notes |
|------------|-----------|-------|
| `ta.sma(src, length)` | `ta.sma(close, length=N)` | Direct mapping |
| `ta.ema(src, length)` | `ta.ema(close, length=N)` | Direct mapping |
| `ta.rsi(src, length)` | `ta.rsi(close, length=N)` | Direct mapping |
| `ta.atr(length)` | `ta.atr(high, low, close, length=N)` | Requires OHLC |
| `ta.stoch(close, high, low, k, d, smooth)` | `ta.stoch(high, low, close, k=N, d=N, smooth_k=N)` | Param rename |
| `ta.macd(src, fast, slow, signal)` | `ta.macd(close, fast=N, slow=N, signal=N)` | Returns DataFrame |
| `ta.bb(src, length, mult)` | `ta.bbands(close, length=N, std=N)` | Different name |
| `ta.adx(len)` | `ta.adx(high, low, close, length=N)` | Requires HLC |
| `ta.cci(src, length)` | `ta.cci(high, low, close, length=N)` | Requires HLC |
| `ta.mfi(src, length)` | `ta.mfi(high, low, close, volume, length=N)` | Requires OHLCV |

### Utility Function Mappings

| PineScript | Python | Notes |
|------------|--------|-------|
| `ta.crossover(a, b)` | `ta.cross(a, b, above=True)` | Or custom: `(a > b) & (a.shift(1) <= b.shift(1))` |
| `ta.crossunder(a, b)` | `ta.cross(a, b, above=False)` | Or custom implementation |
| `ta.highest(src, length)` | `src.rolling(length).max()` | Native pandas |
| `ta.lowest(src, length)` | `src.rolling(length).min()` | Native pandas |
| `ta.change(src, length)` | `src.diff(length)` | Native pandas |
| `ta.valuewhen(cond, src, occ)` | Custom implementation | Requires lookback logic |
| `ta.barssince(cond)` | Custom implementation | Count bars since condition |

### Math Function Mappings

| PineScript | Python | Notes |
|------------|--------|-------|
| `math.abs(x)` | `np.abs(x)` | NumPy |
| `math.sqrt(x)` | `np.sqrt(x)` | NumPy |
| `math.log(x)` | `np.log(x)` | NumPy |
| `math.pow(x, y)` | `np.power(x, y)` | NumPy |
| `math.max(a, b)` | `np.maximum(a, b)` | Element-wise |
| `math.min(a, b)` | `np.minimum(a, b)` | Element-wise |
| `math.round(x)` | `np.round(x)` | NumPy |

## Custom Implementation Templates

### Crossover Detection
```python
def crossover(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """Detect when series_a crosses above series_b."""
    return (series_a > series_b) & (series_a.shift(1) <= series_b.shift(1))

def crossunder(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """Detect when series_a crosses below series_b."""
    return (series_a < series_b) & (series_a.shift(1) >= series_b.shift(1))
```

### Bars Since Condition
```python
def barssince(condition: pd.Series) -> pd.Series:
    """Count bars since condition was last true."""
    groups = (~condition).cumsum()
    return condition.groupby(groups).cumcount()
```

### Value When Condition
```python
def valuewhen(condition: pd.Series, source: pd.Series, occurrence: int = 0) -> pd.Series:
    """Get value of source when condition was true, N occurrences ago."""
    mask = condition.values
    values = source.values
    result = np.full_like(values, np.nan, dtype=float)

    for i in range(len(values)):
        count = 0
        for j in range(i, -1, -1):
            if mask[j]:
                if count == occurrence:
                    result[i] = values[j]
                    break
                count += 1
    return pd.Series(result, index=source.index)
```

## Processing Steps

1. **Parse Function Calls**: Extract all ta.*, math.*, and custom functions
2. **Lookup Mappings**: Find pandas-ta equivalents for each function
3. **Parameter Translation**: Map PineScript params to pandas-ta params
4. **Handle Custom Functions**: Generate Python implementations for non-standard functions
5. **Resolve Dependencies**: Order calculations based on variable dependencies
6. **Generate Code**: Output clean, documented Python calculation code
7. **Validate Accuracy**: Note any precision differences between implementations

## Invocation

Spawn @quant-pandas-adapter when:
- Converting PineScript indicator calculations to Python
- Mapping ta.* functions to pandas-ta
- Generating custom implementations for non-standard functions
- Validating calculation accuracy between PineScript and Python

## Example Conversion

**Input (PineScript):**
```pinescript
rsi_value = ta.rsi(close, 14)
sma_value = ta.sma(rsi_value, 5)
cross_up = ta.crossover(rsi_value, 30)
```

**Output (Python):**
```python
import pandas_ta as ta
import pandas as pd

def crossover(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    return (series_a > series_b) & (series_a.shift(1) <= series_b.shift(1))

# Calculations
rsi_value = ta.rsi(df['close'], length=14)
sma_value = ta.sma(rsi_value, length=5)
cross_up = crossover(rsi_value, pd.Series(30, index=rsi_value.index))
```

## Completion Marker

SUBAGENT_COMPLETE: quant-pandas-adapter
FILES_CREATED: 0
OUTPUT_TYPE: python_code
NEXT_AGENTS: [quant-class-wrapper]
