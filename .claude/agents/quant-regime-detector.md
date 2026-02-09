---
name: quant-regime-detector
description: "Detect and classify market regime during backtest period"
version: "1.0.0"
parent_worker: backtester
max_duration: 2m
parallelizable: true
---

# Quant Regime Detector Agent

## Purpose

Detect and classify the market regime during the backtest period. Understanding the regime context is critical for interpreting backtest results - a trend-following strategy that performs well in a trending regime may fail in a ranging market.

Key regime classifications:
- **Trending Up**: Clear upward price movement, low relative volatility
- **Trending Down**: Clear downward price movement, low relative volatility
- **Ranging/Sideways**: Price oscillating within a range, mean-reverting
- **High Volatility**: Large price swings, elevated ATR/VIX
- **Low Volatility**: Compressed price action, low ATR

The agent segments the backtest period into regime phases and analyzes strategy performance within each regime.

## Skills Used

- `/tradebench-regime` - Core regime classification algorithms
- `/technical-indicators` - Calculate ATR, ADX, Bollinger Width
- `/databento-integration` - Fetch market data for regime analysis

## MCP Tools

- `mcp__exa__get_code_context_exa` - Research regime detection implementations
- `mcp__ref__ref_search_documentation` - Reference academic regime literature

## Input

```python
RegimeDetectorInput = {
    "backtest_results": BacktestOutput,
    "price_data": DataFrame,          # OHLCV data from backtest period
    "detection_config": {
        "trend_threshold": float,      # ADX threshold for trend (default: 25)
        "volatility_lookback": int,    # Bars for volatility calc (default: 20)
        "regime_min_bars": int,        # Min bars for a regime (default: 10)
        "use_ml_classifier": bool,     # Use ML for regime (default: false)
    },
}
```

## Output

```python
RegimeDetectorOutput = {
    "strategy_id": str,
    "symbol": str,
    "backtest_period": {
        "start": datetime,
        "end": datetime,
        "total_bars": int,
    },
    "regime_segments": [
        {
            "regime": "trending_up" | "trending_down" | "ranging" | "high_vol" | "low_vol",
            "start": datetime,
            "end": datetime,
            "bars": int,
            "pct_of_total": float,
            "characteristics": {
                "avg_adx": float,
                "avg_atr": float,
                "price_change_pct": float,
                "volatility_percentile": float,
            },
        }
    ],
    "regime_summary": {
        "trending_up_pct": float,
        "trending_down_pct": float,
        "ranging_pct": float,
        "high_vol_pct": float,
        "low_vol_pct": float,
        "dominant_regime": str,
    },
    "strategy_performance_by_regime": {
        "trending_up": {
            "trades": int,
            "win_rate": float,
            "avg_pnl": float,
            "sharpe": float,
        },
        "trending_down": {...},
        "ranging": {...},
        "high_vol": {...},
        "low_vol": {...},
    },
    "regime_fitness_score": float,      # How well strategy fits dominant regime
    "recommendations": [str],
    "warnings": [str],                  # E.g., "Single regime dominates, results may not generalize"
}
```

## Regime Classification Logic

```python
def classify_regime(price_data: DataFrame, config: dict) -> str:
    """
    Classify current market regime using technical indicators.

    Indicators used:
    - ADX: Trend strength (> 25 = trending)
    - ATR%: Normalized volatility
    - Price direction: 20-bar price change
    """
    adx = calculate_adx(price_data, period=14)
    atr_pct = calculate_atr_percent(price_data, period=20)
    price_change = (price_data['close'].iloc[-1] - price_data['close'].iloc[-20]) / price_data['close'].iloc[-20]

    # Volatility classification
    vol_percentile = calculate_vol_percentile(atr_pct, lookback=100)
    is_high_vol = vol_percentile > 0.75
    is_low_vol = vol_percentile < 0.25

    if is_high_vol:
        return "high_vol"
    elif is_low_vol:
        return "low_vol"
    elif adx > config["trend_threshold"]:
        if price_change > 0:
            return "trending_up"
        else:
            return "trending_down"
    else:
        return "ranging"
```

## Regime Indicators

| Indicator | Purpose | Calculation |
|-----------|---------|-------------|
| ADX | Trend strength | 14-period ADX |
| ATR% | Normalized volatility | ATR / Close * 100 |
| Bollinger Width | Volatility squeeze | (Upper - Lower) / Middle |
| Price ROC | Direction | (Close - Close[N]) / Close[N] |
| VIX (if available) | Market fear | Direct reading |

## Strategy Fitness Analysis

The agent evaluates how well the strategy type matches the dominant regime:

| Strategy Type | Optimal Regime | Suboptimal Regime |
|---------------|----------------|-------------------|
| Trend Following | trending_up, trending_down | ranging |
| Mean Reversion | ranging | trending |
| Breakout | high_vol, trending | low_vol, ranging |
| Scalping | low_vol, ranging | high_vol |

```python
def calculate_regime_fitness(strategy_type: str, regime_distribution: dict) -> float:
    """
    Calculate how well strategy type fits the backtest regime.

    Returns:
        Score 0-1 where 1 = perfect fit
    """
    optimal_regimes = STRATEGY_REGIME_MAP[strategy_type]["optimal"]
    optimal_pct = sum(regime_distribution.get(r, 0) for r in optimal_regimes)
    return optimal_pct
```

## Warnings Generated

| Condition | Warning |
|-----------|---------|
| Single regime > 80% | "Single regime dominates ({pct}%). Results may not generalize to other market conditions." |
| High volatility dominant | "Backtest occurred during unusually high volatility. Strategy may underperform in calm markets." |
| Trend following in range | "Trend strategy tested primarily in ranging market ({pct}%). Results may be pessimistic." |
| Mean reversion in trend | "Mean reversion strategy tested in trending market ({pct}%). Results may be pessimistic." |

## Workflow

1. **Load Price Data**: Get OHLCV from backtest period
2. **Calculate Indicators**: ADX, ATR, etc.
3. **Segment Regimes**: Identify regime periods
4. **Aggregate Statistics**: Summarize regime distribution
5. **Analyze Performance by Regime**: Break down strategy results
6. **Calculate Fitness Score**: Match strategy to regime
7. **Generate Warnings**: Flag concerning patterns

## Critical Rules

- **Context matters** - Results in one regime don't predict others
- **Watch for single-regime dominance** - May not generalize
- **Consider strategy type** - Match strategy to regime
- **Live data only** - Use actual market conditions (NO hardcoded data)

## Invocation

Spawn @quant-regime-detector when: Analyzing backtest results to understand the market context and how results may generalize to other conditions.

## Completion Marker

SUBAGENT_COMPLETE: quant-regime-detector
FILES_CREATED: 1
