---
name: quant-signal-extractor
description: "Extract and add signal generation logic to indicators by converting visual patterns to buy/sell signals"
version: "1.0.0"
parent_worker: converter
max_duration: 2m
parallelizable: false
---

# Quant Signal Extractor Agent

## Purpose

Add intelligent signal generation logic to converted indicators. This agent analyzes the indicator's visual patterns and mathematical properties to generate actionable buy/sell signals. It handles common patterns like crossovers, threshold breaches, divergences, and multi-condition setups. The output enhances the indicator class with a robust `get_signal()` implementation.

## Skills Used

- `/technical-indicators` - Understanding indicator behavior and signal patterns
- `/trading-signals` - Signal generation patterns and strength calculation
- `/pattern-analysis` - Chart pattern detection and classification

## MCP Tools

- `Ref_ref_search_documentation` - Look up indicator signal interpretation
- `exa_get_code_context_exa` - Find signal extraction examples

## Input

```typescript
interface SignalExtractorInput {
  indicator_metadata: {
    name: string;
    type: "oscillator" | "overlay" | "volume" | "hybrid";
  };
  output_columns: string[];        // Columns calculated by indicator
  plotting_commands: Array<{
    type: string;
    series: string;
    location?: string;
  }>;
  indicator_bounds?: {
    min?: number;
    max?: number;
    overbought?: number;
    oversold?: number;
  };
  custom_signals?: Array<{        // Optional pre-defined signals from PineScript
    condition: string;
    direction: "long" | "short";
  }>;
}
```

## Output

```typescript
interface SignalExtractorOutput {
  signal_code: string;             // Python code for get_signal()
  signal_types: string[];          // Types of signals detected
  signal_parameters: Array<{       // Configurable signal thresholds
    name: string;
    default: number;
    description: string;
  }>;
  signal_documentation: string;    // Docstring for signal logic
}
```

## Signal Pattern Library

### 1. Crossover Signals

Detect when two series cross each other.

```python
def _detect_crossover_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
    """Detect crossover between fast and slow lines."""
    fast = df[self.fast_column].iloc[-2:]
    slow = df[self.slow_column].iloc[-2:]

    # Bullish crossover: fast crosses above slow
    if fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]:
        return {
            "direction": "long",
            "strength": self._calculate_crossover_strength(fast, slow),
            "reason": f"{self.fast_column} crossed above {self.slow_column}",
            "timestamp": df.index[-1]
        }

    # Bearish crossover: fast crosses below slow
    if fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]:
        return {
            "direction": "short",
            "strength": self._calculate_crossover_strength(fast, slow),
            "reason": f"{self.fast_column} crossed below {self.slow_column}",
            "timestamp": df.index[-1]
        }

    return {"direction": "neutral", "strength": 0.0, "reason": "No crossover", "timestamp": df.index[-1]}

def _calculate_crossover_strength(self, fast: pd.Series, slow: pd.Series) -> float:
    """Calculate signal strength based on crossover angle."""
    angle = abs(fast.iloc[-1] - slow.iloc[-1]) / abs(fast.iloc[-2] - slow.iloc[-2] + 0.0001)
    return min(1.0, angle / 2.0)  # Normalize to 0-1
```

### 2. Threshold Signals (Oscillators)

Detect overbought/oversold conditions.

```python
def _detect_threshold_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
    """Detect threshold breach signals for oscillator indicators."""
    current = df[self.value_column].iloc[-1]
    previous = df[self.value_column].iloc[-2]

    # Oversold bounce (bullish)
    if previous <= self.oversold and current > self.oversold:
        strength = (self.oversold - previous) / self.oversold * 2
        return {
            "direction": "long",
            "strength": min(1.0, strength),
            "reason": f"{self.value_column} bounced from oversold ({self.oversold})",
            "timestamp": df.index[-1]
        }

    # Overbought rejection (bearish)
    if previous >= self.overbought and current < self.overbought:
        strength = (previous - self.overbought) / (100 - self.overbought) * 2
        return {
            "direction": "short",
            "strength": min(1.0, strength),
            "reason": f"{self.value_column} rejected from overbought ({self.overbought})",
            "timestamp": df.index[-1]
        }

    # Still in extreme zone
    if current <= self.oversold:
        return {"direction": "long", "strength": 0.3, "reason": "In oversold zone", "timestamp": df.index[-1]}
    if current >= self.overbought:
        return {"direction": "short", "strength": 0.3, "reason": "In overbought zone", "timestamp": df.index[-1]}

    return {"direction": "neutral", "strength": 0.0, "reason": "Neutral zone", "timestamp": df.index[-1]}
```

### 3. Divergence Signals

Detect price/indicator divergence.

```python
def _detect_divergence_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
    """Detect bullish or bearish divergence."""
    lookback = self.divergence_lookback

    # Find recent swing highs/lows in price
    price_highs = self._find_swing_highs(df['close'], lookback)
    price_lows = self._find_swing_lows(df['close'], lookback)

    # Find corresponding indicator values
    ind_highs = self._find_swing_highs(df[self.value_column], lookback)
    ind_lows = self._find_swing_lows(df[self.value_column], lookback)

    # Bullish divergence: price lower low, indicator higher low
    if len(price_lows) >= 2 and len(ind_lows) >= 2:
        if (price_lows[-1] < price_lows[-2] and ind_lows[-1] > ind_lows[-2]):
            return {
                "direction": "long",
                "strength": 0.8,
                "reason": "Bullish divergence detected",
                "timestamp": df.index[-1]
            }

    # Bearish divergence: price higher high, indicator lower high
    if len(price_highs) >= 2 and len(ind_highs) >= 2:
        if (price_highs[-1] > price_highs[-2] and ind_highs[-1] < ind_highs[-2]):
            return {
                "direction": "short",
                "strength": 0.8,
                "reason": "Bearish divergence detected",
                "timestamp": df.index[-1]
            }

    return {"direction": "neutral", "strength": 0.0, "reason": "No divergence", "timestamp": df.index[-1]}

def _find_swing_highs(self, series: pd.Series, lookback: int) -> list:
    """Find swing high points in series."""
    highs = []
    for i in range(lookback, len(series) - lookback):
        if series.iloc[i] == series.iloc[i-lookback:i+lookback+1].max():
            highs.append(series.iloc[i])
    return highs[-2:]  # Return last 2

def _find_swing_lows(self, series: pd.Series, lookback: int) -> list:
    """Find swing low points in series."""
    lows = []
    for i in range(lookback, len(series) - lookback):
        if series.iloc[i] == series.iloc[i-lookback:i+lookback+1].min():
            lows.append(series.iloc[i])
    return lows[-2:]  # Return last 2
```

### 4. Band Breakout Signals

Detect price breaking through bands.

```python
def _detect_band_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
    """Detect band breakout or reversion signals."""
    close = df['close'].iloc[-1]
    upper = df[self.upper_band].iloc[-1]
    lower = df[self.lower_band].iloc[-1]
    middle = df[self.middle_band].iloc[-1]

    prev_close = df['close'].iloc[-2]

    # Breakout above upper band
    if prev_close <= upper and close > upper:
        return {
            "direction": "long",
            "strength": 0.7,
            "reason": "Breakout above upper band",
            "timestamp": df.index[-1]
        }

    # Breakdown below lower band
    if prev_close >= lower and close < lower:
        return {
            "direction": "short",
            "strength": 0.7,
            "reason": "Breakdown below lower band",
            "timestamp": df.index[-1]
        }

    # Mean reversion: price returning to middle from extremes
    if close > middle and prev_close > upper:
        return {
            "direction": "short",
            "strength": 0.5,
            "reason": "Mean reversion from upper band",
            "timestamp": df.index[-1]
        }

    if close < middle and prev_close < lower:
        return {
            "direction": "long",
            "strength": 0.5,
            "reason": "Mean reversion from lower band",
            "timestamp": df.index[-1]
        }

    return {"direction": "neutral", "strength": 0.0, "reason": "Within bands", "timestamp": df.index[-1]}
```

### 5. Multi-Condition Signals

Combine multiple conditions.

```python
def _detect_multi_condition_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
    """Combine multiple signal conditions with weighted scoring."""
    conditions = {
        "crossover": self._check_crossover(df),
        "threshold": self._check_threshold(df),
        "trend": self._check_trend(df),
        "momentum": self._check_momentum(df)
    }

    weights = {
        "crossover": 0.3,
        "threshold": 0.3,
        "trend": 0.2,
        "momentum": 0.2
    }

    # Calculate weighted score
    long_score = sum(
        weights[k] * v["strength"]
        for k, v in conditions.items()
        if v["direction"] == "long"
    )
    short_score = sum(
        weights[k] * v["strength"]
        for k, v in conditions.items()
        if v["direction"] == "short"
    )

    # Determine overall direction
    if long_score > short_score and long_score > 0.3:
        reasons = [v["reason"] for k, v in conditions.items() if v["direction"] == "long"]
        return {
            "direction": "long",
            "strength": min(1.0, long_score),
            "reason": " + ".join(reasons),
            "timestamp": df.index[-1],
            "sub_signals": conditions
        }
    elif short_score > long_score and short_score > 0.3:
        reasons = [v["reason"] for k, v in conditions.items() if v["direction"] == "short"]
        return {
            "direction": "short",
            "strength": min(1.0, short_score),
            "reason": " + ".join(reasons),
            "timestamp": df.index[-1],
            "sub_signals": conditions
        }

    return {
        "direction": "neutral",
        "strength": 0.0,
        "reason": "No clear signal",
        "timestamp": df.index[-1],
        "sub_signals": conditions
    }
```

## Signal Type Selection

| Indicator Type | Recommended Signal Patterns |
|---------------|----------------------------|
| Oscillator (RSI, Stochastic) | Threshold + Divergence |
| Moving Average | Crossover |
| Bands (Bollinger, Keltner) | Band Breakout |
| MACD | Crossover + Threshold (histogram) |
| Volume | Threshold + Trend |
| Custom | Multi-Condition |

## Processing Steps

1. **Analyze Indicator Type**: Determine best signal pattern for indicator category
2. **Identify Key Columns**: Find the series used for signal generation
3. **Extract Bounds**: Get overbought/oversold levels if applicable
4. **Map Visual Patterns**: Convert plotshape/plotchar to signal conditions
5. **Generate Signal Code**: Create the `get_signal()` method
6. **Add Helper Methods**: Include supporting functions (crossover detection, etc.)
7. **Add Parameters**: Create configurable thresholds
8. **Document Logic**: Write clear docstrings

## Invocation

Spawn @quant-signal-extractor when:
- Adding signal logic to a converted indicator
- Enhancing existing indicator with new signal types
- Converting visual PineScript signals to code
- Building multi-condition signal systems

## Completion Marker

SUBAGENT_COMPLETE: quant-signal-extractor
FILES_CREATED: 0
OUTPUT_TYPE: python_code_fragment
NEXT_AGENTS: [quant-class-wrapper]
