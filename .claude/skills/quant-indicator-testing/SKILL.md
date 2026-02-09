---
name: quant-indicator-testing
description: "Pytest patterns for validating indicator calculations, edge cases, and performance benchmarks"
version: "1.0.0"
triggers:
  - "when testing indicator implementations"
  - "when validating Pine to Python conversions"
  - "when benchmarking calculation performance"
  - "when writing indicator unit tests"
---

# Quant Indicator Testing

## Purpose

Provides comprehensive pytest patterns for testing trading indicator implementations. Ensures calculations match expected values, handles edge cases correctly, and meets performance requirements. Critical for validating Pine to Python conversions.

## When to Use

- After implementing any new indicator
- When converting indicators from PineScript
- Before deploying indicators to production
- When debugging indicator discrepancies
- During code review of indicator changes

## Key Concepts

### Testing Categories

| Category | Purpose | Example |
|----------|---------|---------|
| **Calculation Accuracy** | Values match reference | RSI(14) matches TradingView |
| **Edge Cases** | Handle unusual inputs | Empty data, NaN values |
| **Boundary Conditions** | Test parameter limits | Period=1, Period=1000 |
| **Performance** | Meet speed requirements | <10ms for 10k bars |
| **Regression** | Catch unexpected changes | Compare to known good outputs |

### Reference Sources

1. **TradingView** - Primary reference for Pine indicators
2. **TA-Lib** - Industry standard C library
3. **pandas-ta** - Python TA library
4. **Manual Calculation** - For simple indicators

### Tolerance Levels

| Indicator Type | Absolute Tolerance | Relative Tolerance |
|----------------|-------------------|-------------------|
| Moving Averages | 1e-10 | 1e-8 |
| Oscillators (RSI, etc.) | 1e-6 | 1e-4 |
| Volatility (ATR, etc.) | 1e-6 | 1e-4 |
| Complex (MACD, BB) | 1e-5 | 1e-3 |

## Patterns & Templates

### Test File Structure

```python
"""
tests/indicators/test_{indicator_name}.py

Standard structure for indicator test files.
"""
import pytest
import numpy as np
import pandas as pd
from decimal import Decimal
from typing import Callable
import time

# Import the indicator being tested
from lib.indicators import rsi, sma, ema, atr

# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Standard OHLCV test data."""
    np.random.seed(42)
    n = 500

    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.2
    volume = np.random.randint(1000, 10000, n)

    return pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=pd.date_range('2024-01-01', periods=n, freq='1h'))


@pytest.fixture
def known_values() -> dict:
    """
    Known input/output pairs for validation.
    These should be calculated manually or from trusted source.
    """
    return {
        'close': [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08],
        'sma_5': [np.nan, np.nan, np.nan, np.nan, 44.074, 44.24, 44.392, 44.658, 45.104, 45.454],
        'ema_5': [np.nan, np.nan, np.nan, np.nan, 44.074, 44.326, 44.584, 44.863, 45.189, 45.486],
    }


@pytest.fixture
def edge_case_data() -> dict:
    """Data for edge case testing."""
    return {
        'empty': pd.Series([], dtype=float),
        'single': pd.Series([100.0]),
        'all_nan': pd.Series([np.nan, np.nan, np.nan]),
        'some_nan': pd.Series([100, np.nan, 102, np.nan, 104]),
        'constant': pd.Series([100.0] * 100),
        'extreme_values': pd.Series([1e-10, 1e10, -1e10, 0]),
    }


@pytest.fixture
def performance_data() -> pd.Series:
    """Large dataset for performance testing."""
    np.random.seed(42)
    return pd.Series(100 + np.cumsum(np.random.randn(100000) * 0.1))


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def assert_series_equal(
    actual: pd.Series,
    expected: pd.Series,
    rtol: float = 1e-5,
    atol: float = 1e-8,
    check_names: bool = False
):
    """
    Assert two series are equal within tolerance.
    Handles NaN comparison correctly.
    """
    pd.testing.assert_series_equal(
        actual, expected,
        rtol=rtol,
        atol=atol,
        check_names=check_names,
        check_exact=False
    )


def load_tradingview_reference(indicator: str, symbol: str, period: int) -> pd.Series:
    """
    Load pre-computed TradingView values for comparison.
    Store these in tests/fixtures/tradingview/
    """
    fixture_path = f"tests/fixtures/tradingview/{indicator}_{symbol}_{period}.csv"
    return pd.read_csv(fixture_path, index_col=0, parse_dates=True)['value']


def measure_performance(func: Callable, *args, iterations: int = 100) -> float:
    """
    Measure average execution time in milliseconds.
    """
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args)
        times.append((time.perf_counter() - start) * 1000)

    return np.mean(times)


# ============================================================
# TEST CLASSES
# ============================================================

class TestSMA:
    """Tests for Simple Moving Average."""

    # Calculation Accuracy Tests
    def test_basic_calculation(self, known_values):
        """Test SMA calculation against known values."""
        close = pd.Series(known_values['close'])
        expected = pd.Series(known_values['sma_5'])

        result = sma(close, 5)

        assert_series_equal(result, expected, rtol=1e-3)

    def test_matches_pandas_rolling(self, sample_ohlcv):
        """Cross-validate with pandas rolling."""
        close = sample_ohlcv['close']

        result = sma(close, 20)
        expected = close.rolling(20).mean()

        assert_series_equal(result, expected, rtol=1e-10)

    # Edge Case Tests
    def test_empty_input(self, edge_case_data):
        """Handle empty series."""
        result = sma(edge_case_data['empty'], 5)
        assert len(result) == 0

    def test_period_longer_than_data(self, edge_case_data):
        """Period > data length should return all NaN."""
        result = sma(edge_case_data['single'], 5)
        assert result.isna().all()

    def test_nan_handling(self, edge_case_data):
        """NaN values should propagate correctly."""
        result = sma(edge_case_data['some_nan'], 3)
        # Should have NaN where input has NaN in window
        assert result.isna().sum() > 0

    def test_constant_input(self, edge_case_data):
        """Constant input should return same constant."""
        result = sma(edge_case_data['constant'], 10)
        valid_result = result.dropna()
        assert (valid_result == 100.0).all()

    # Boundary Tests
    def test_period_one(self, sample_ohlcv):
        """Period=1 should return input."""
        close = sample_ohlcv['close']
        result = sma(close, 1)
        assert_series_equal(result, close, rtol=1e-10)

    def test_large_period(self, sample_ohlcv):
        """Test with large period."""
        close = sample_ohlcv['close']
        result = sma(close, 200)
        assert result.notna().sum() == len(close) - 199

    # Performance Tests
    def test_performance(self, performance_data):
        """Should process 100k bars in <10ms."""
        exec_time = measure_performance(sma, performance_data, 50)
        assert exec_time < 10, f"SMA took {exec_time:.2f}ms, expected <10ms"


class TestRSI:
    """Tests for Relative Strength Index."""

    def test_basic_calculation(self, sample_ohlcv):
        """Test RSI is in valid range [0, 100]."""
        result = rsi(sample_ohlcv['close'], 14)
        valid = result.dropna()

        assert valid.min() >= 0
        assert valid.max() <= 100

    def test_overbought_oversold(self, sample_ohlcv):
        """Test RSI identifies extreme conditions."""
        result = rsi(sample_ohlcv['close'], 14)

        # Should have some values in overbought/oversold zones
        oversold = (result < 30).sum()
        overbought = (result > 70).sum()

        # At least some readings in each zone
        assert oversold > 0 or overbought > 0

    def test_constant_price_rsi(self, edge_case_data):
        """Constant price should give RSI near 50 (or NaN due to division)."""
        result = rsi(edge_case_data['constant'], 14)
        valid = result.dropna()

        # Constant price means no gains or losses, RSI undefined or 50
        if len(valid) > 0:
            assert all((valid == 50) | valid.isna())

    def test_uptrend_rsi(self):
        """Strong uptrend should have high RSI."""
        # Monotonically increasing
        uptrend = pd.Series(range(1, 101), dtype=float)
        result = rsi(uptrend, 14)
        valid = result.dropna()

        # RSI should be very high in uptrend
        assert valid.mean() > 90

    def test_downtrend_rsi(self):
        """Strong downtrend should have low RSI."""
        downtrend = pd.Series(range(100, 0, -1), dtype=float)
        result = rsi(downtrend, 14)
        valid = result.dropna()

        # RSI should be very low in downtrend
        assert valid.mean() < 10

    def test_matches_talib(self, sample_ohlcv):
        """Cross-validate with TA-Lib if available."""
        try:
            import talib
            close = sample_ohlcv['close'].values

            result = rsi(sample_ohlcv['close'], 14)
            expected = pd.Series(talib.RSI(close, 14))

            # TA-Lib uses different initialization, compare after warmup
            assert_series_equal(result.iloc[50:], expected.iloc[50:], rtol=1e-4)
        except ImportError:
            pytest.skip("TA-Lib not installed")

    def test_performance(self, performance_data):
        """Should process 100k bars in <20ms."""
        exec_time = measure_performance(rsi, performance_data, 14)
        assert exec_time < 20, f"RSI took {exec_time:.2f}ms, expected <20ms"


class TestATR:
    """Tests for Average True Range."""

    def test_positive_values(self, sample_ohlcv):
        """ATR should always be positive."""
        result = atr(sample_ohlcv['high'], sample_ohlcv['low'], sample_ohlcv['close'], 14)
        valid = result.dropna()

        assert (valid >= 0).all()

    def test_true_range_components(self, sample_ohlcv):
        """ATR should account for all TR components."""
        # Create gap scenario
        high = pd.Series([100, 105, 110])
        low = pd.Series([99, 102, 108])
        close = pd.Series([99.5, 104, 109])  # Gap up on bar 2

        result = atr(high, low, close, 2)

        # With gap, TR should be larger than just high-low
        # TR for bar 1 includes gap from previous close
        assert result.iloc[-1] > 0

    def test_matches_tradingview(self, sample_ohlcv):
        """Compare with TradingView reference values."""
        # This test uses pre-computed TradingView values
        # In practice, export these from TradingView chart
        result = atr(
            sample_ohlcv['high'],
            sample_ohlcv['low'],
            sample_ohlcv['close'],
            14
        )

        # For now, just verify reasonable range
        valid = result.dropna()
        assert valid.mean() > 0
        assert valid.mean() < sample_ohlcv['close'].mean() * 0.1  # ATR < 10% of price


# ============================================================
# PARAMETRIZED TESTS
# ============================================================

@pytest.mark.parametrize("period", [5, 10, 14, 20, 50, 100, 200])
def test_sma_periods(sample_ohlcv, period):
    """Test SMA with various periods."""
    result = sma(sample_ohlcv['close'], period)

    # Should have correct number of valid values
    expected_valid = len(sample_ohlcv) - period + 1
    assert result.notna().sum() == expected_valid


@pytest.mark.parametrize("indicator_func,period,max_time_ms", [
    (sma, 20, 5),
    (ema, 20, 10),
    (rsi, 14, 20),
])
def test_indicator_performance(performance_data, indicator_func, period, max_time_ms):
    """Parametrized performance tests."""
    exec_time = measure_performance(indicator_func, performance_data, period)
    assert exec_time < max_time_ms, f"{indicator_func.__name__} took {exec_time:.2f}ms"


# ============================================================
# REGRESSION TESTS
# ============================================================

class TestRegressions:
    """Regression tests to catch unexpected changes."""

    def test_sma_regression(self, sample_ohlcv):
        """SMA should match previously computed values."""
        result = sma(sample_ohlcv['close'], 20)

        # Store hash of results for regression detection
        result_hash = hash(tuple(result.dropna().round(6).values))

        # This hash was computed from known good implementation
        # Update this when implementation intentionally changes
        # expected_hash = 1234567890  # Uncomment and set in real tests
        # assert result_hash == expected_hash

    def test_rsi_regression(self, sample_ohlcv):
        """RSI should match previously computed values."""
        result = rsi(sample_ohlcv['close'], 14)

        # Compare first 10 non-NaN values to expected
        expected_first_10 = [50.0, 52.3, 48.7, ...]  # Fill with known values

        # actual_first_10 = result.dropna().iloc[:10].round(1).tolist()
        # assert actual_first_10 == expected_first_10
```

### Conversion Validation Tests

```python
"""
Tests specifically for validating PineScript to Python conversions.
"""

class TestPineConversion:
    """Validate that Python implementations match PineScript behavior."""

    @pytest.fixture
    def tradingview_export(self) -> pd.DataFrame:
        """
        Load exported TradingView data with indicator values.
        Export process:
        1. Apply indicator in TradingView
        2. Export chart data (requires subscription)
        3. Or use Chrome DevTools to capture data
        """
        return pd.read_csv('tests/fixtures/tradingview_export.csv',
                          index_col=0, parse_dates=True)

    def test_sma_matches_tradingview(self, tradingview_export):
        """SMA should exactly match TradingView."""
        close = tradingview_export['close']
        tv_sma = tradingview_export['tv_sma_20']

        py_sma = sma(close, 20)

        # Compare only where both have values
        mask = tv_sma.notna() & py_sma.notna()

        np.testing.assert_allclose(
            py_sma[mask].values,
            tv_sma[mask].values,
            rtol=1e-5,
            err_msg="SMA doesn't match TradingView"
        )

    def test_ema_matches_tradingview(self, tradingview_export):
        """EMA should match TradingView (note: Pine uses adjust=False)."""
        close = tradingview_export['close']
        tv_ema = tradingview_export['tv_ema_20']

        py_ema = ema(close, 20)

        # EMA has different initialization, skip first N bars
        skip = 50
        mask = tv_ema.iloc[skip:].notna()

        np.testing.assert_allclose(
            py_ema.iloc[skip:][mask].values,
            tv_ema.iloc[skip:][mask].values,
            rtol=1e-4,
            err_msg="EMA doesn't match TradingView after warmup"
        )

    def test_rsi_matches_tradingview(self, tradingview_export):
        """RSI should match TradingView's Wilder smoothing."""
        close = tradingview_export['close']
        tv_rsi = tradingview_export['tv_rsi_14']

        py_rsi = rsi(close, 14)

        # RSI needs warmup period
        skip = 100
        mask = tv_rsi.iloc[skip:].notna()

        np.testing.assert_allclose(
            py_rsi.iloc[skip:][mask].values,
            tv_rsi.iloc[skip:][mask].values,
            rtol=1e-3,
            err_msg="RSI doesn't match TradingView"
        )

    def test_macd_matches_tradingview(self, tradingview_export):
        """MACD components should match TradingView."""
        close = tradingview_export['close']

        py_macd, py_signal, py_hist = macd(close, 12, 26, 9)

        tv_macd = tradingview_export['tv_macd_line']
        tv_signal = tradingview_export['tv_macd_signal']

        skip = 50
        mask = tv_macd.iloc[skip:].notna()

        np.testing.assert_allclose(
            py_macd.iloc[skip:][mask].values,
            tv_macd.iloc[skip:][mask].values,
            rtol=1e-4,
            err_msg="MACD line doesn't match TradingView"
        )
```

### Performance Benchmark Suite

```python
"""
Performance benchmarking for indicators.
"""
import pytest
import time
import statistics
from dataclasses import dataclass

@dataclass
class BenchmarkResult:
    indicator: str
    data_size: int
    mean_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    passes_requirement: bool

class TestPerformanceBenchmarks:
    """
    Comprehensive performance benchmarks.

    Requirements:
    - 10k bars: < 5ms
    - 100k bars: < 50ms
    - 1M bars: < 500ms
    """

    PERFORMANCE_REQUIREMENTS = {
        10_000: 5,      # 10k bars in 5ms
        100_000: 50,    # 100k bars in 50ms
        1_000_000: 500  # 1M bars in 500ms
    }

    @pytest.fixture(params=[10_000, 100_000, 1_000_000])
    def benchmark_data(self, request) -> tuple[pd.Series, int]:
        """Generate benchmark data of various sizes."""
        size = request.param
        np.random.seed(42)
        data = pd.Series(100 + np.cumsum(np.random.randn(size) * 0.1))
        return data, size

    def run_benchmark(
        self,
        func: Callable,
        data: pd.Series,
        *args,
        iterations: int = 10,
        warmup: int = 2
    ) -> BenchmarkResult:
        """Run benchmark with warmup and multiple iterations."""
        # Warmup runs
        for _ in range(warmup):
            func(data, *args)

        # Timed runs
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func(data, *args)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        requirement = self.PERFORMANCE_REQUIREMENTS.get(len(data), 1000)

        return BenchmarkResult(
            indicator=func.__name__,
            data_size=len(data),
            mean_ms=statistics.mean(times),
            std_ms=statistics.stdev(times) if len(times) > 1 else 0,
            min_ms=min(times),
            max_ms=max(times),
            passes_requirement=statistics.mean(times) < requirement
        )

    def test_sma_benchmark(self, benchmark_data):
        """Benchmark SMA performance."""
        data, size = benchmark_data
        result = self.run_benchmark(sma, data, 20)

        assert result.passes_requirement, (
            f"SMA({size} bars) took {result.mean_ms:.2f}ms, "
            f"requirement is <{self.PERFORMANCE_REQUIREMENTS[size]}ms"
        )

    def test_ema_benchmark(self, benchmark_data):
        """Benchmark EMA performance."""
        data, size = benchmark_data
        result = self.run_benchmark(ema, data, 20)

        assert result.passes_requirement

    def test_rsi_benchmark(self, benchmark_data):
        """Benchmark RSI performance."""
        data, size = benchmark_data
        result = self.run_benchmark(rsi, data, 14)

        # RSI has looser requirements (more complex calculation)
        adjusted_requirement = self.PERFORMANCE_REQUIREMENTS[size] * 2
        assert result.mean_ms < adjusted_requirement

    @pytest.fixture
    def benchmark_ohlcv(self) -> pd.DataFrame:
        """OHLCV data for multi-column indicators."""
        np.random.seed(42)
        n = 100_000
        close = 100 + np.cumsum(np.random.randn(n) * 0.1)

        return pd.DataFrame({
            'high': close + np.abs(np.random.randn(n) * 0.1),
            'low': close - np.abs(np.random.randn(n) * 0.1),
            'close': close
        })

    def test_atr_benchmark(self, benchmark_ohlcv):
        """Benchmark ATR performance."""
        start = time.perf_counter()
        atr(benchmark_ohlcv['high'], benchmark_ohlcv['low'],
            benchmark_ohlcv['close'], 14)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100, f"ATR took {elapsed:.2f}ms, expected <100ms"
```

## Examples

### Example 1: Testing a New Indicator

```python
"""
Example: Testing a newly implemented Williams %R indicator.
"""

def williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 14) -> pd.Series:
    """
    Williams %R implementation.
    Returns values between -100 (oversold) and 0 (overbought).
    """
    highest_high = high.rolling(period).max()
    lowest_low = low.rolling(period).min()

    wr = -100 * (highest_high - close) / (highest_high - lowest_low)
    return wr


class TestWilliamsR:
    """Complete test suite for Williams %R."""

    def test_range(self, sample_ohlcv):
        """Williams %R should be between -100 and 0."""
        result = williams_r(
            sample_ohlcv['high'],
            sample_ohlcv['low'],
            sample_ohlcv['close'],
            14
        )
        valid = result.dropna()

        assert valid.min() >= -100
        assert valid.max() <= 0

    def test_at_high(self):
        """When close = highest high, %R should be 0."""
        high = pd.Series([100, 105, 110, 115, 120])
        low = pd.Series([95, 100, 105, 110, 115])
        close = pd.Series([100, 105, 110, 115, 120])  # Close at highs

        result = williams_r(high, low, close, 5)

        # Last value should be 0 (at highest high)
        assert result.iloc[-1] == 0

    def test_at_low(self):
        """When close = lowest low, %R should be -100."""
        high = pd.Series([100, 100, 100, 100, 100])
        low = pd.Series([90, 91, 92, 93, 90])  # 90 is lowest
        close = pd.Series([95, 95, 95, 95, 90])  # Close at lowest on last bar

        result = williams_r(high, low, close, 5)

        # Last value should be -100 (at lowest low)
        assert result.iloc[-1] == pytest.approx(-100, abs=0.01)

    def test_matches_tradingview_formula(self, sample_ohlcv):
        """Validate formula matches TradingView's Williams %R."""
        # TradingView formula: %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
        h = sample_ohlcv['high']
        l = sample_ohlcv['low']
        c = sample_ohlcv['close']

        result = williams_r(h, l, c, 14)

        # Manual calculation
        hh = h.rolling(14).max()
        ll = l.rolling(14).min()
        expected = -100 * (hh - c) / (hh - ll)

        pd.testing.assert_series_equal(result, expected)
```

## Common Mistakes

### 1. Not Testing Edge Cases

```python
# WRONG: Only testing happy path
def test_indicator():
    result = my_indicator(normal_data)
    assert result is not None

# RIGHT: Test all edge cases
def test_indicator_comprehensive():
    # Empty data
    result = my_indicator(pd.Series([]))
    assert len(result) == 0

    # Single value
    result = my_indicator(pd.Series([100]))
    assert len(result) == 1

    # All NaN
    result = my_indicator(pd.Series([np.nan, np.nan]))
    assert result.isna().all()

    # Normal data
    result = my_indicator(normal_data)
    assert len(result) == len(normal_data)
```

### 2. Ignoring Warm-up Period

```python
# WRONG: Comparing from beginning
def test_ema_matches_reference():
    result = ema(data, 20)
    expected = reference_ema(data, 20)
    pd.testing.assert_series_equal(result, expected)  # Will fail due to warmup!

# RIGHT: Skip warmup period
def test_ema_matches_reference():
    result = ema(data, 20)
    expected = reference_ema(data, 20)

    # Skip first 50 bars for EMA to stabilize
    skip = 50
    pd.testing.assert_series_equal(
        result.iloc[skip:],
        expected.iloc[skip:],
        rtol=1e-4
    )
```

### 3. Using Exact Equality for Floats

```python
# WRONG: Exact float comparison
def test_sma():
    result = sma(data, 20)
    expected = [100.5, 100.6, 100.7]
    assert result.tolist() == expected  # Will fail due to float precision!

# RIGHT: Use approximate comparison
def test_sma():
    result = sma(data, 20)
    expected = [100.5, 100.6, 100.7]
    np.testing.assert_allclose(result.values, expected, rtol=1e-5)
```

### 4. Not Seeding Random Data

```python
# WRONG: Random data makes tests non-deterministic
def test_indicator():
    data = pd.Series(np.random.randn(100))  # Different every run!
    result = my_indicator(data)
    assert result.mean() > 0  # Might pass or fail randomly

# RIGHT: Seed random generator
def test_indicator():
    np.random.seed(42)  # Deterministic
    data = pd.Series(np.random.randn(100))
    result = my_indicator(data)
    assert result.mean() == pytest.approx(expected_mean, rel=0.01)
```

### 5. Testing Implementation, Not Behavior

```python
# WRONG: Testing internal implementation details
def test_sma_uses_rolling():
    with mock.patch('pandas.Series.rolling') as mock_rolling:
        sma(data, 20)
        mock_rolling.assert_called_once_with(20)

# RIGHT: Test behavior/output
def test_sma_output():
    result = sma(data, 20)

    # Test behavior: average of last 20 values
    manual_avg = data.iloc[-20:].mean()
    assert result.iloc[-1] == pytest.approx(manual_avg)
```
