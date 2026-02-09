---
name: quant-test-writer
description: "Generate comprehensive pytest tests for converted indicators including accuracy and edge cases"
version: "1.0.0"
parent_worker: converter
max_duration: 2m
parallelizable: true
---

# Quant Test Writer Agent

## Purpose

Generate comprehensive pytest test suites for converted indicators. This agent creates tests covering calculation accuracy, edge cases, parameter validation, and performance benchmarks. Tests ensure the Python implementation matches expected behavior and maintains calculation fidelity compared to the original PineScript.

## Skills Used

- `/indicator-testing` - Testing patterns for technical indicators
- `/testing-patterns` - General pytest patterns and fixtures
- `/technical-indicators` - Understanding expected indicator behavior

## MCP Tools

- `exa_get_code_context_exa` - Find testing examples for similar indicators
- `Ref_ref_search_documentation` - Look up pytest patterns and assertion methods

## Input

```typescript
interface TestWriterInput {
  indicator_class: string;         // Class name
  indicator_file: string;          // Path to indicator file
  indicator_metadata: {
    name: string;
    category: string;
    required_columns: string[];
  };
  parameters: Array<{
    name: string;
    type: string;
    default: any;
    min?: number;
    max?: number;
  }>;
  expected_outputs: string[];      // Column names added by calculate()
  signal_outputs: string[];        // Signal types returned
}
```

## Output

```typescript
interface TestWriterOutput {
  test_file_path: string;
  test_code: string;
  test_count: number;
  coverage_areas: string[];
}
```

## Test Categories

### 1. Initialization Tests
- Default parameter values
- Custom parameter values
- Parameter validation (min/max bounds)
- Invalid parameter rejection

### 2. Calculation Accuracy Tests
- Known input/output pairs
- Comparison with reference implementation
- Multi-timeframe consistency
- Decimal precision validation

### 3. Edge Case Tests
- Empty DataFrame
- Single row DataFrame
- NaN handling
- Extreme values (very large/small numbers)
- Zero values
- Negative values (where applicable)

### 4. Signal Generation Tests
- Correct signal direction
- Signal strength bounds (0-1)
- Signal reason populated
- Timestamp present

### 5. Plot Data Tests
- Correct series format
- Y-range validity
- Color format validation
- Pane assignment

### 6. Performance Tests
- Calculation time benchmark
- Memory usage check
- Large dataset handling (10k+ rows)

## Test Template

```python
"""
Tests for {IndicatorName} Indicator

Tests cover:
- Initialization and parameter validation
- Calculation accuracy
- Edge cases and error handling
- Signal generation
- Plot data formatting
- Performance benchmarks

Run with: pytest tests/indicators/test_{indicator_file}.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

from indicators.{category}.{module} import {ClassName}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="1D")
    np.random.seed(42)  # Reproducible random data

    close = 100 + np.cumsum(np.random.randn(100) * 2)
    high = close + np.abs(np.random.randn(100))
    low = close - np.abs(np.random.randn(100))
    open_ = close + np.random.randn(100) * 0.5
    volume = np.random.randint(1000, 10000, 100)

    return pd.DataFrame({
        "timestamp": dates,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })


@pytest.fixture
def indicator_default() -> {ClassName}:
    """Create indicator with default parameters."""
    return {ClassName}()


@pytest.fixture
def indicator_custom() -> {ClassName}:
    """Create indicator with custom parameters."""
    return {ClassName}({custom_params})


# ============================================================================
# Initialization Tests
# ============================================================================

class TestInitialization:
    """Test indicator initialization and parameter handling."""

    def test_default_parameters(self, indicator_default):
        """Test that default parameters are set correctly."""
        params = indicator_default.get_parameters()
        {default_param_assertions}

    def test_custom_parameters(self, indicator_custom):
        """Test that custom parameters are accepted."""
        params = indicator_custom.get_parameters()
        {custom_param_assertions}

    @pytest.mark.parametrize("param,value,should_raise", [
        {parameter_validation_cases}
    ])
    def test_parameter_validation(self, param, value, should_raise):
        """Test parameter validation raises appropriate errors."""
        kwargs = {{param: value}}
        if should_raise:
            with pytest.raises((ValueError, TypeError)):
                {ClassName}(**kwargs)
        else:
            indicator = {ClassName}(**kwargs)
            assert indicator.get_parameters()[param] == value

    def test_class_attributes(self, indicator_default):
        """Test that required class attributes are set."""
        assert hasattr(indicator_default, 'name')
        assert hasattr(indicator_default, 'category')
        assert hasattr(indicator_default, 'version')
        assert indicator_default.category == "{category}"


# ============================================================================
# Calculation Tests
# ============================================================================

class TestCalculation:
    """Test indicator calculation accuracy."""

    def test_calculate_returns_dataframe(self, indicator_default, sample_ohlcv):
        """Test that calculate() returns a DataFrame."""
        result = indicator_default.calculate(sample_ohlcv)
        assert isinstance(result, pd.DataFrame)

    def test_calculate_adds_columns(self, indicator_default, sample_ohlcv):
        """Test that calculate() adds expected columns."""
        result = indicator_default.calculate(sample_ohlcv)
        expected_columns = {expected_output_columns}
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {{col}}"

    def test_calculate_preserves_input(self, indicator_default, sample_ohlcv):
        """Test that calculate() preserves original columns."""
        original_cols = set(sample_ohlcv.columns)
        result = indicator_default.calculate(sample_ohlcv)
        assert original_cols.issubset(set(result.columns))

    def test_calculate_row_count(self, indicator_default, sample_ohlcv):
        """Test that row count is preserved."""
        result = indicator_default.calculate(sample_ohlcv)
        assert len(result) == len(sample_ohlcv)

    def test_known_values(self, indicator_default):
        """Test calculation against known input/output pairs."""
        # Known test data with expected results
        test_df = pd.DataFrame({
            {known_test_data}
        })
        result = indicator_default.calculate(test_df)

        {known_value_assertions}

    def test_calculation_consistency(self, indicator_default, sample_ohlcv):
        """Test that repeated calculations produce same results."""
        result1 = indicator_default.calculate(sample_ohlcv)
        result2 = indicator_default.calculate(sample_ohlcv)
        pd.testing.assert_frame_equal(result1, result2)


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self, indicator_default):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame(columns={required_columns})
        with pytest.raises(ValueError, match="empty"):
            indicator_default.calculate(empty_df)

    def test_single_row(self, indicator_default):
        """Test handling of single row DataFrame."""
        single_row = pd.DataFrame({
            {single_row_data}
        })
        # Should not raise, may return NaN values
        result = indicator_default.calculate(single_row)
        assert len(result) == 1

    def test_nan_handling(self, indicator_default, sample_ohlcv):
        """Test that NaN values are handled appropriately."""
        df_with_nan = sample_ohlcv.copy()
        df_with_nan.loc[10:15, "close"] = np.nan

        result = indicator_default.calculate(df_with_nan)
        # Indicator should not crash; may propagate NaN
        assert isinstance(result, pd.DataFrame)

    def test_missing_columns(self, indicator_default):
        """Test that missing required columns raise error."""
        incomplete_df = pd.DataFrame({{"open": [1, 2, 3]}})
        with pytest.raises(ValueError, match="Missing required columns"):
            indicator_default.calculate(incomplete_df)

    def test_extreme_values(self, indicator_default):
        """Test handling of extreme values."""
        extreme_df = pd.DataFrame({
            {extreme_value_data}
        })
        result = indicator_default.calculate(extreme_df)
        # Should not overflow or produce inf
        assert not result.isin([np.inf, -np.inf]).any().any()


# ============================================================================
# Signal Tests
# ============================================================================

class TestSignalGeneration:
    """Test signal generation logic."""

    def test_signal_structure(self, indicator_default, sample_ohlcv):
        """Test that signal has required keys."""
        df = indicator_default.calculate(sample_ohlcv)
        signal = indicator_default.get_signal(df)

        assert "direction" in signal
        assert "strength" in signal
        assert "reason" in signal
        assert "timestamp" in signal

    def test_signal_direction_values(self, indicator_default, sample_ohlcv):
        """Test that signal direction is valid."""
        df = indicator_default.calculate(sample_ohlcv)
        signal = indicator_default.get_signal(df)

        assert signal["direction"] in ["long", "short", "neutral"]

    def test_signal_strength_bounds(self, indicator_default, sample_ohlcv):
        """Test that signal strength is between 0 and 1."""
        df = indicator_default.calculate(sample_ohlcv)
        signal = indicator_default.get_signal(df)

        assert 0.0 <= signal["strength"] <= 1.0

    def test_signal_empty_dataframe(self, indicator_default):
        """Test signal generation with insufficient data."""
        empty_df = pd.DataFrame()
        signal = indicator_default.get_signal(empty_df)

        assert signal["direction"] == "neutral"
        assert signal["strength"] == 0.0


# ============================================================================
# Plot Data Tests
# ============================================================================

class TestPlotData:
    """Test plot data formatting."""

    def test_plot_data_structure(self, indicator_default, sample_ohlcv):
        """Test that plot data has required structure."""
        df = indicator_default.calculate(sample_ohlcv)
        plot_data = indicator_default.get_plot_data(df)

        assert "series" in plot_data
        assert "pane" in plot_data
        assert isinstance(plot_data["series"], list)

    def test_plot_pane_value(self, indicator_default, sample_ohlcv):
        """Test that pane value is valid."""
        df = indicator_default.calculate(sample_ohlcv)
        plot_data = indicator_default.get_plot_data(df)

        assert plot_data["pane"] in ["main", "separate"]

    def test_series_format(self, indicator_default, sample_ohlcv):
        """Test that series are properly formatted."""
        df = indicator_default.calculate(sample_ohlcv)
        plot_data = indicator_default.get_plot_data(df)

        for series in plot_data["series"]:
            assert "name" in series
            assert "data" in series


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.benchmark
    def test_calculation_speed(self, indicator_default, benchmark):
        """Benchmark calculation speed."""
        # Generate larger dataset
        large_df = pd.DataFrame({
            "open": np.random.randn(10000) + 100,
            "high": np.random.randn(10000) + 101,
            "low": np.random.randn(10000) + 99,
            "close": np.random.randn(10000) + 100,
            "volume": np.random.randint(1000, 10000, 10000)
        })

        result = benchmark(indicator_default.calculate, large_df)
        assert result is not None

    def test_large_dataset(self, indicator_default):
        """Test handling of large dataset."""
        large_df = pd.DataFrame({
            "open": np.random.randn(50000) + 100,
            "high": np.random.randn(50000) + 101,
            "low": np.random.randn(50000) + 99,
            "close": np.random.randn(50000) + 100,
            "volume": np.random.randint(1000, 10000, 50000)
        })

        # Should complete without memory issues
        result = indicator_default.calculate(large_df)
        assert len(result) == 50000
```

## Invocation

Spawn @quant-test-writer when:
- Converting a new indicator and need tests
- Adding tests to existing indicator
- Validating conversion accuracy
- Setting up CI test coverage

## Test File Location

```
tests/
├── indicators/
│   ├── oscillators/
│   │   └── test_{indicator}.py
│   ├── overlays/
│   │   └── test_{indicator}.py
│   └── volume/
│       └── test_{indicator}.py
└── conftest.py
```

## Completion Marker

SUBAGENT_COMPLETE: quant-test-writer
FILES_CREATED: 1
OUTPUT_TYPE: test_file
NEXT_AGENTS: [quant-readme-gen]
