---
name: quant-research-methodology
description: "Medallion-style research doctrine for systematic strategy development with academic rigor"
version: "1.0.0"
triggers:
  - "when developing new trading strategies"
  - "when researching market anomalies"
  - "when validating trading hypotheses"
  - "when applying De Prado methodology"
---

# Quant Research Methodology

## Purpose

Implements a Medallion Fund-inspired research doctrine that enforces hypothesis-first development, statistical rigor, and systematic edge discovery. This methodology separates Sigma-Quant from retail trading approaches by demanding academic-grade validation before any strategy reaches production.

## When to Use

- Starting new strategy research from scratch
- Validating an existing strategy idea
- Converting discretionary trading rules to systematic strategies
- Reviewing imported strategies (PineScript, community, etc.)
- Training quant team members on research standards

## Key Concepts

### The Medallion Doctrine

Renaissance Technologies' approach distilled into actionable principles:

1. **Edge Must Be Explainable**: If you can't articulate WHY it works, it doesn't work
2. **Out-of-Sample is Truth**: In-sample performance is marketing; OOS is reality
3. **Small Edges, High Frequency**: Prefer 55% win rate with 1000 trades over 80% with 50
4. **Decay is Expected**: All edges decay; plan for it
5. **Correlation Kills**: Uncorrelated strategies > high-Sharpe correlated ones

### Hypothesis-First Development

```
WRONG: "Let me optimize these indicators until something works"
RIGHT: "I hypothesize that mean reversion occurs at session boundaries due to institutional rebalancing"
```

### De Prado's Triple Barrier Method

Every trade has THREE possible exits:
1. **Take Profit** (upper barrier): Fixed or dynamic
2. **Stop Loss** (lower barrier): Fixed or dynamic
3. **Time Expiry** (vertical barrier): Maximum holding period

```python
# De Prado Triple Barrier Implementation
def apply_triple_barrier(
    close: pd.Series,
    events: pd.DatetimeIndex,
    pt_sl: tuple[float, float],  # (profit_target, stop_loss) as multipliers
    min_ret: float,  # Minimum return threshold
    num_days: int,  # Maximum holding period
) -> pd.DataFrame:
    """
    Returns DataFrame with:
    - t1: Time of first barrier touch
    - ret: Return at barrier touch
    - bin: Label (-1, 0, 1)
    """
    pass
```

### Meta-Labeling (De Prado)

Two-stage classification:
1. **Primary Model**: Predicts direction (buy/sell signal)
2. **Secondary Model**: Predicts probability of primary being correct

```python
# Meta-labeling pattern
def meta_label(primary_signal: int, features: pd.DataFrame) -> float:
    """
    Returns probability that primary_signal is correct.
    Only trade when meta_label > threshold.
    """
    pass
```

## Patterns & Templates

### Research Session Template

```markdown
# Research Session: {YYYY-MM-DD}

## Hypothesis Under Test
{Clear, falsifiable statement}

## Edge Rationale
{Why this should work - market microstructure, behavioral, statistical}

## Data Requirements
- Symbol: {e.g., ES.FUT}
- Timeframe: {e.g., 15m}
- Period: {e.g., 2020-01-01 to 2024-12-31}
- Minimum Trades: {e.g., 200+}

## Methodology
1. {Step 1}
2. {Step 2}
3. {Step 3}

## Expected Results
- Win Rate: {range}
- Sharpe: {range}
- Max DD: {range}

## Actual Results
{Fill after testing}

## Conclusion
{VALIDATED / INVALIDATED / INCONCLUSIVE}

## Next Steps
{What to do based on results}
```

### Edge Discovery Framework

```python
class EdgeDiscoveryFramework:
    """
    Systematic approach to finding tradeable edges.
    """

    EDGE_SOURCES = [
        "market_microstructure",  # Order flow, bid-ask dynamics
        "behavioral_biases",      # Overreaction, anchoring, herding
        "structural_constraints", # Index rebalancing, option expiry
        "information_asymmetry",  # Earnings, news, data releases
        "risk_premia",           # Carry, momentum, value, volatility
        "regulatory_arbitrage",   # Tax effects, regulatory constraints
    ]

    VALIDATION_STAGES = [
        ("hypothesis", "Is the edge logically sound?"),
        ("in_sample", "Does it work in training data?"),
        ("out_of_sample", "Does it work in unseen data?"),
        ("paper_trade", "Does it work in real-time?"),
        ("small_live", "Does it survive execution costs?"),
        ("scale_up", "Does it maintain edge at scale?"),
    ]

    def validate_hypothesis(self, hypothesis: str) -> dict:
        """
        Check hypothesis against quality criteria.
        """
        criteria = {
            "falsifiable": self._is_falsifiable(hypothesis),
            "specific": self._is_specific(hypothesis),
            "measurable": self._is_measurable(hypothesis),
            "has_rationale": self._has_rationale(hypothesis),
            "novel": self._is_novel(hypothesis),
        }
        return criteria
```

### Academic Paper Review Template

When reviewing academic papers for strategy ideas:

```markdown
## Paper Review: {Title}

### Citation
{Authors}, {Year}, {Journal}

### Key Claim
{Main finding in one sentence}

### Data Used
- Period: {years}
- Universe: {assets}
- Frequency: {daily, intraday, etc.}

### Methodology
{Brief description}

### Reported Results
- Sharpe: {X}
- Alpha: {X}
- Statistical Significance: {t-stat, p-value}

### Red Flags
- [ ] Look-ahead bias
- [ ] Survivorship bias
- [ ] Data snooping
- [ ] Transaction costs ignored
- [ ] Unrealistic assumptions

### Replicability Score
{1-10, with justification}

### Adaptation for Sigma-Quant
{How to adapt for futures prop trading}
```

## Examples

### Example 1: Session Boundary Mean Reversion

```python
# Hypothesis: Price tends to revert after session open gaps

class SessionBoundaryResearch:
    """
    Research session boundary mean reversion.
    """

    hypothesis = """
    After the RTH session opens with a gap > 0.5%,
    price tends to fill at least 50% of the gap
    within the first 30 minutes due to:
    1. Overnight position unwinding
    2. Retail stop-loss hunting
    3. Institutional rebalancing
    """

    edge_rationale = """
    - Market microstructure: Overnight liquidity is lower
    - Behavioral: Retail traders panic on gaps
    - Structural: Market makers need to rebalance inventory
    """

    def run_research(self, df: pd.DataFrame) -> dict:
        # 1. Identify gap days
        gaps = self._identify_gaps(df, threshold=0.005)

        # 2. Measure gap fill rate
        fill_rate = self._measure_gap_fills(df, gaps)

        # 3. Calculate profitability
        returns = self._simulate_trades(df, gaps)

        # 4. Statistical significance
        t_stat, p_value = self._test_significance(returns)

        return {
            "sample_size": len(gaps),
            "fill_rate": fill_rate,
            "mean_return": returns.mean(),
            "sharpe": returns.mean() / returns.std() * np.sqrt(252),
            "t_stat": t_stat,
            "p_value": p_value,
            "conclusion": "VALIDATED" if p_value < 0.05 else "INVALIDATED"
        }
```

### Example 2: De Prado Research Workflow

```python
from mlfinlab.labeling import get_events, add_vertical_barrier
from mlfinlab.features import get_daily_vol

def deprado_research_workflow(close: pd.Series, side: pd.Series):
    """
    Full De Prado research workflow.
    """
    # 1. Compute daily volatility for dynamic barriers
    daily_vol = get_daily_vol(close, span=50)

    # 2. Get vertical barriers (time limit)
    t1 = add_vertical_barrier(
        close.index,
        close,
        num_days=5  # Max 5-day holding
    )

    # 3. Apply triple barrier with dynamic thresholds
    events = get_events(
        close=close,
        t_events=side.index,  # Signal timestamps
        pt_sl=[2.0, 1.0],     # 2:1 reward:risk
        target=daily_vol,     # Dynamic target
        min_ret=0.01,         # Minimum 1% return
        num_threads=4,
        t1=t1,
        side=side
    )

    # 4. Analyze results
    labels = events['bin']
    print(f"Win Rate: {(labels == 1).mean():.2%}")
    print(f"Avg Return: {events['ret'].mean():.4f}")
    print(f"Sample Size: {len(events)}")

    return events
```

## Common Mistakes

### 1. Optimization Masquerading as Research

```python
# WRONG: This is curve-fitting, not research
for rsi_period in range(5, 50):
    for ma_period in range(10, 200):
        for threshold in np.arange(20, 40, 1):
            result = backtest(rsi_period, ma_period, threshold)
            if result.sharpe > best_sharpe:
                best_params = (rsi_period, ma_period, threshold)

# RIGHT: Hypothesis-driven parameter selection
# "RSI period should be 14 because that's what institutions use"
# "MA period should be 20 for swing trading timeframe"
# "Threshold at 30 aligns with textbook oversold levels"
```

### 2. Ignoring Transaction Costs

```python
# WRONG: Gross returns only
gross_sharpe = returns.mean() / returns.std() * np.sqrt(252)

# RIGHT: Net of realistic costs
COMMISSION_PER_CONTRACT = 4.50  # Round trip
SLIPPAGE_TICKS = 1
TICK_VALUE = 12.50  # ES futures

total_cost = (COMMISSION_PER_CONTRACT + SLIPPAGE_TICKS * TICK_VALUE) * 2
net_returns = returns - (total_cost / capital_per_trade)
net_sharpe = net_returns.mean() / net_returns.std() * np.sqrt(252)
```

### 3. Small Sample Conclusions

```python
# WRONG: Drawing conclusions from insufficient data
if num_trades < 100:
    raise ValueError(
        f"Only {num_trades} trades - minimum 100 required for statistical validity"
    )

# Sample size requirements:
# - Win rate: n > 100 for ±10% confidence
# - Sharpe ratio: n > 200 for stable estimate
# - Drawdown: n > 500 to capture tail events
```

### 4. Look-Ahead Bias

```python
# WRONG: Using future information
df['signal'] = np.where(df['close'].shift(-1) > df['close'], 1, -1)

# WRONG: Fitting on full dataset then testing on same
model.fit(full_data)
predictions = model.predict(full_data)

# RIGHT: Strict train/test split with temporal ordering
train = df[df.index < '2023-01-01']
test = df[df.index >= '2023-01-01']
model.fit(train)
predictions = model.predict(test)
```

### 5. Data Snooping (Multiple Testing)

```python
# WRONG: Testing 100 strategies, reporting the best
strategies_tested = 100
best_pvalue = 0.03
# False discovery is almost certain!

# RIGHT: Apply Bonferroni correction
corrected_threshold = 0.05 / strategies_tested  # 0.0005
if best_pvalue > corrected_threshold:
    print("Not statistically significant after correction")
```

## References

- De Prado, M. L. (2018). *Advances in Financial Machine Learning*
- De Prado, M. L. (2020). *Machine Learning for Asset Managers*
- Chan, E. P. (2013). *Algorithmic Trading: Winning Strategies*
- Aronson, D. (2006). *Evidence-Based Technical Analysis*
