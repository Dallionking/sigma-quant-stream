---
name: quant-class-wrapper
description: "Generate Python indicator class following Sigma-Quant patterns with standard interface"
version: "1.0.0"
parent_worker: converter
max_duration: 2m
parallelizable: false
---

# Quant Class Wrapper Agent

## Purpose

Generate a standardized Python indicator class that wraps the converted calculations. This agent creates a clean, documented class following Sigma-Quant's indicator interface patterns, ensuring consistency across all converted indicators. The output class includes `__init__`, `calculate()`, `get_signal()`, and `get_plot_data()` methods.

## Skills Used

- `/technical-indicators` - Sigma-Quant indicator class patterns and interfaces
- `/database-models` - ORM integration for indicator persistence

## MCP Tools

- `exa_get_code_context_exa` - Find examples of well-structured indicator classes

## Input

```typescript
interface ClassWrapperInput {
  indicator_metadata: {
    name: string;
    type: "oscillator" | "overlay" | "volume" | "hybrid";
    overlay: boolean;
  };
  variable_declarations: Array<{
    name: string;
    type: string;
    data_type: string;
    default_value?: any;
    min?: number;
    max?: number;
  }>;
  calculation_code: string;
  imports: string[];
  custom_implementations: Array<{
    function_name: string;
    python_code: string;
  }>;
}
```

## Output

```typescript
interface ClassWrapperOutput {
  class_code: string;      // Complete Python class
  file_path: string;       // Suggested file location
  class_name: string;      // Generated class name
  interface_compliance: {
    has_init: boolean;
    has_calculate: boolean;
    has_get_signal: boolean;
    has_get_plot_data: boolean;
  };
}
```

## Sigma-Quant Indicator Interface

All converted indicators MUST implement this interface:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

class BaseIndicator(ABC):
    """Base class for all Sigma-Quant indicators."""

    # Class attributes
    name: str
    category: str  # "oscillator", "overlay", "volume", "hybrid"
    version: str
    description: str

    @abstractmethod
    def __init__(self, **params):
        """Initialize indicator with parameters."""
        pass

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicator values and return DataFrame with new columns."""
        pass

    @abstractmethod
    def get_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate trading signal based on current state."""
        pass

    @abstractmethod
    def get_plot_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Return data formatted for chart rendering."""
        pass

    def get_parameters(self) -> Dict[str, Any]:
        """Return current parameter values."""
        pass

    def validate_input(self, df: pd.DataFrame) -> bool:
        """Validate input DataFrame has required columns."""
        pass
```

## Class Template

```python
"""
{indicator_name} Indicator

Converted from PineScript to Python for Sigma-Quant Pipeline.
Original: {pinescript_source_reference}

Category: {category}
Version: {version}
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional, List
from indicators.base import BaseIndicator

{custom_implementations}


class {ClassName}(BaseIndicator):
    """
    {description}

    Parameters
    ----------
    {parameter_docs}

    Returns
    -------
    pd.DataFrame
        DataFrame with indicator columns added

    Example
    -------
    >>> indicator = {ClassName}(length=14)
    >>> df = indicator.calculate(ohlcv_df)
    >>> signal = indicator.get_signal(df)
    """

    name = "{indicator_name}"
    category = "{category}"
    version = "{version}"
    description = "{description}"

    # Required OHLCV columns
    required_columns = {required_columns}

    def __init__(
        self,
        {init_parameters}
    ):
        """Initialize {indicator_name} with parameters."""
        {init_body}
        self._validate_parameters()

    def _validate_parameters(self) -> None:
        """Validate parameter values are within acceptable ranges."""
        {validation_code}

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate {indicator_name} values.

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV DataFrame with columns: {required_columns}

        Returns
        -------
        pd.DataFrame
            Input DataFrame with indicator columns added:
            {output_columns}
        """
        self.validate_input(df)
        result = df.copy()

        {calculation_code}

        return result

    def get_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate trading signal based on indicator state.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with indicator values calculated

        Returns
        -------
        Dict[str, Any]
            Signal dictionary with keys:
            - direction: "long", "short", or "neutral"
            - strength: float 0-1
            - reason: str explanation
            - timestamp: datetime
        """
        if df.empty:
            return {
                "direction": "neutral",
                "strength": 0.0,
                "reason": "Insufficient data",
                "timestamp": None
            }

        {signal_logic}

    def get_plot_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Return data formatted for LightweightCharts rendering.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with indicator values calculated

        Returns
        -------
        Dict[str, Any]
            Plot configuration with keys:
            - series: List of series configurations
            - pane: "main" or "separate"
            - y_range: Optional fixed Y-axis range
        """
        {plot_data_code}

    def get_parameters(self) -> Dict[str, Any]:
        """Return current parameter values."""
        return {
            {parameter_dict}
        }

    def validate_input(self, df: pd.DataFrame) -> bool:
        """Validate input DataFrame has required columns."""
        missing = set(self.required_columns) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        return True
```

## Processing Steps

1. **Generate Class Name**: Convert indicator name to PascalCase
2. **Build Init Parameters**: Create typed parameters with defaults from variable declarations
3. **Add Validation**: Generate parameter validation code with min/max checks
4. **Wrap Calculations**: Place calculation code in `calculate()` method
5. **Generate Signal Logic**: Create signal extraction (placeholder if not provided)
6. **Format Plot Data**: Structure output for LightweightCharts
7. **Add Documentation**: Generate comprehensive docstrings
8. **Validate Interface**: Ensure all required methods are implemented

## File Naming Convention

```
indicators/
├── oscillators/
│   ├── rsi.py
│   ├── stochastic.py
│   └── macd.py
├── overlays/
│   ├── sma.py
│   ├── bollinger_bands.py
│   └── ichimoku.py
├── volume/
│   ├── obv.py
│   └── vwap.py
└── custom/
    └── {converted_indicator}.py
```

## Invocation

Spawn @quant-class-wrapper when:
- Wrapping converted calculations in a class
- Creating new indicator from scratch
- Refactoring existing indicator to Sigma-Quant pattern
- Generating indicator boilerplate

## Example Output

```python
class RSIDivergence(BaseIndicator):
    name = "RSI Divergence"
    category = "oscillator"
    version = "1.0.0"
    description = "RSI with divergence detection"
    required_columns = ["close"]

    def __init__(self, length: int = 14, overbought: float = 70, oversold: float = 30):
        self.length = length
        self.overbought = overbought
        self.oversold = oversold
        self._validate_parameters()

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        self.validate_input(df)
        result = df.copy()
        result["rsi"] = ta.rsi(result["close"], length=self.length)
        return result

    def get_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        latest = df.iloc[-1]
        if latest["rsi"] < self.oversold:
            return {"direction": "long", "strength": 0.7, "reason": "RSI oversold"}
        elif latest["rsi"] > self.overbought:
            return {"direction": "short", "strength": 0.7, "reason": "RSI overbought"}
        return {"direction": "neutral", "strength": 0.0, "reason": "RSI neutral"}

    def get_plot_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {
            "series": [{"name": "RSI", "data": df["rsi"].tolist(), "color": "#2196F3"}],
            "pane": "separate",
            "y_range": [0, 100],
            "horizontal_lines": [
                {"value": self.overbought, "color": "#FF5252", "style": "dashed"},
                {"value": self.oversold, "color": "#4CAF50", "style": "dashed"}
            ]
        }
```

## Completion Marker

SUBAGENT_COMPLETE: quant-class-wrapper
FILES_CREATED: 1
OUTPUT_TYPE: python_file
NEXT_AGENTS: [quant-test-writer, quant-signal-extractor]
