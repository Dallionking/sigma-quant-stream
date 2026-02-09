# Developer Path

This guide is for developers who want to extend Sigma-Quant Stream by writing
custom indicators, creating hypothesis cards, building exchange adapters, or
adding new Claude Code agents. It assumes you have completed the
[Getting Started](getting-started.md) guide and have the system running.

---

## Table of Contents

1. [Writing Custom Indicators](#writing-custom-indicators)
2. [Creating Hypothesis Cards](#creating-hypothesis-cards)
3. [Adding Exchange Adapters](#adding-exchange-adapters)
4. [Extending Worker Prompts](#extending-worker-prompts)
5. [Creating Custom Agents](#creating-custom-agents)
6. [Creating Custom Skills](#creating-custom-skills)
7. [Using the Backtest Runner](#using-the-backtest-runner)
8. [Pattern Knowledge Base](#pattern-knowledge-base)
9. [Testing Your Code](#testing-your-code)

---

## Writing Custom Indicators

Custom indicators go in `lib/` or `output/indicators/created/`. Each indicator
is a Python class that takes OHLCV data and returns a signal series.

### Indicator Template

```python
"""
Custom indicator: Adaptive RSI with Volume Confirmation

Hypothesis: Standard RSI divergences are more reliable when confirmed
by volume expansion at reversal points.
"""

import pandas as pd
import numpy as np


class AdaptiveRSIVolume:
    """RSI divergence detector with volume confirmation."""

    def __init__(
        self,
        rsi_period: int = 14,
        divergence_window: int = 5,
        volume_threshold: float = 1.5,
    ):
        self.rsi_period = rsi_period
        self.divergence_window = divergence_window
        self.volume_threshold = volume_threshold

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicator signals.

        Parameters:
            df: DataFrame with columns [open, high, low, close, volume]

        Returns:
            DataFrame with added columns:
              - rsi: RSI values
              - volume_ratio: current volume / SMA(volume)
              - signal: 1 (long), -1 (short), 0 (neutral)
        """
        df = df.copy()

        # RSI calculation
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))

        # Volume ratio
        df["volume_sma"] = df["volume"].rolling(20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma"]

        # Signal generation
        df["signal"] = 0

        for i in range(self.divergence_window, len(df)):
            window = df.iloc[i - self.divergence_window : i + 1]

            # Bullish divergence: price lower low, RSI higher low
            price_lower = window["close"].iloc[-1] < window["close"].min()
            rsi_higher = window["rsi"].iloc[-1] > window["rsi"].min()
            vol_confirm = df["volume_ratio"].iloc[i] > self.volume_threshold

            if price_lower and rsi_higher and vol_confirm:
                df.loc[df.index[i], "signal"] = 1

            # Bearish divergence: price higher high, RSI lower high
            price_higher = window["close"].iloc[-1] > window["close"].max()
            rsi_lower = window["rsi"].iloc[-1] < window["rsi"].max()

            if price_higher and rsi_lower and vol_confirm:
                df.loc[df.index[i], "signal"] = -1

        return df

    def get_parameters(self) -> dict:
        """Return current parameters for serialization."""
        return {
            "rsi_period": self.rsi_period,
            "divergence_window": self.divergence_window,
            "volume_threshold": self.volume_threshold,
        }
```

### Indicator Requirements

Every custom indicator must:

1. Accept a DataFrame with `open`, `high`, `low`, `close`, `volume` columns
2. Return a DataFrame with a `signal` column (1, -1, or 0)
3. Have a `get_parameters()` method for serialization
4. Include a docstring explaining the hypothesis
5. Use no look-ahead bias (only use data up to and including the current bar)

### Testing Your Indicator

```python
# test_adaptive_rsi_volume.py
import pytest
import pandas as pd
import numpy as np
from lib.adaptive_rsi_volume import AdaptiveRSIVolume


def make_sample_data(rows: int = 500) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    np.random.seed(42)
    close = 5000 + np.cumsum(np.random.randn(rows) * 10)
    return pd.DataFrame({
        "open": close + np.random.randn(rows),
        "high": close + abs(np.random.randn(rows) * 5),
        "low": close - abs(np.random.randn(rows) * 5),
        "close": close,
        "volume": np.random.randint(1000, 10000, rows).astype(float),
    })


class TestAdaptiveRSIVolume:
    def test_output_columns(self):
        df = make_sample_data()
        indicator = AdaptiveRSIVolume()
        result = indicator.calculate(df)
        assert "rsi" in result.columns
        assert "signal" in result.columns
        assert "volume_ratio" in result.columns

    def test_signal_values(self):
        df = make_sample_data()
        indicator = AdaptiveRSIVolume()
        result = indicator.calculate(df)
        assert set(result["signal"].unique()).issubset({-1, 0, 1})

    def test_no_lookahead(self):
        df = make_sample_data(200)
        indicator = AdaptiveRSIVolume()
        full = indicator.calculate(df)
        partial = indicator.calculate(df.iloc[:100])
        # Signals for first 100 bars should be identical
        pd.testing.assert_series_equal(
            full["signal"].iloc[:100].reset_index(drop=True),
            partial["signal"].reset_index(drop=True),
        )

    def test_parameters_serializable(self):
        indicator = AdaptiveRSIVolume(rsi_period=21)
        params = indicator.get_parameters()
        assert params["rsi_period"] == 21
        assert isinstance(params, dict)
```

Run tests with:

```bash
cd /path/to/sigma-quant-stream
python -m pytest test_adaptive_rsi_volume.py -v
```

---

## Creating Hypothesis Cards

Hypothesis cards are JSON files that describe a testable trading idea. They feed
the research pipeline and ensure every strategy starts with an economic
rationale.

### Hypothesis Card Format

```json
{
  "id": "hyp-custom-001",
  "title": "VWAP Mean Reversion on NQ 15min",
  "hypothesis": "NQ tends to revert to VWAP during low-volatility sessions. When price deviates more than 1.5 standard deviations from VWAP and volume is declining, a mean-reversion entry has positive expectancy.",
  "counterparty": "Momentum traders who chase breakouts during range-bound sessions",
  "edgeSource": "Structural: institutional VWAP algos create mean-reverting pressure",
  "markets": ["NQ"],
  "timeframes": ["15m"],
  "parameterCount": 4,
  "priority": 1,
  "source": "Chan 'Quantitative Trading' Chapter 3 + personal observation",
  "references": [
    "Ernest Chan - Quantitative Trading (mean reversion chapter)",
    "Barra risk model literature on intraday VWAP behavior"
  ],
  "expectedMetrics": {
    "sharpeRange": [1.0, 2.0],
    "winRateRange": [0.55, 0.70],
    "tradesPerMonth": 20
  },
  "testConditions": {
    "vwapDeviationThreshold": [1.0, 2.0],
    "volumeDeclineWindow": [5, 10],
    "holdingPeriod": [15, 60],
    "stopLossATR": [1.5, 2.5]
  },
  "created": "2026-02-09T00:00:00Z",
  "seeded": false
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier, format: `hyp-{name}-{number}` |
| `title` | Yes | Short descriptive title |
| `hypothesis` | Yes | The testable claim with economic rationale |
| `counterparty` | Yes | Who is on the other side of the trade and why they lose |
| `edgeSource` | Yes | What market inefficiency creates this edge |
| `markets` | Yes | Array of instrument symbols (ES, NQ, YM, GC, BTC, ETH, etc.) |
| `timeframes` | Yes | Array of timeframes to test (5m, 15m, 1h, etc.) |
| `parameterCount` | Yes | Number of tunable parameters (lower is better) |
| `priority` | Yes | 1 (high), 2 (medium), 3 (low) |
| `source` | Yes | Where the idea came from |
| `references` | No | Academic papers, books, or URLs |
| `expectedMetrics` | No | Expected Sharpe range, win rate range, trades/month |
| `testConditions` | No | Parameter ranges to test |
| `created` | Yes | ISO 8601 timestamp |
| `seeded` | No | `true` if this is a pre-loaded seed hypothesis |

### Submitting a Hypothesis

Drop your hypothesis JSON file into the appropriate queue:

```bash
# For direct backtesting (already has a strategy idea)
cp my-hypothesis.json queues/hypotheses/

# For research and conversion (needs indicator work)
cp my-hypothesis.json queues/to-convert/
```

Or use the seed directory for hypotheses that should survive queue resets:

```bash
cp my-hypothesis.json seed/hypotheses/
```

The Researcher worker will pick up hypotheses from the queue and process them.

### Hypothesis Quality Checklist

Before submitting, verify your hypothesis has:

- [ ] A clear, testable claim (not vague)
- [ ] An identified counterparty (who loses money)
- [ ] An economic rationale (why the edge exists)
- [ ] Reasonable expected metrics (Sharpe 1.0-2.5, not 5.0)
- [ ] Fewer than 6 parameters (more = higher overfit risk)

---

## Adding Exchange Adapters

Exchange adapters live in `lib/crypto/` and provide data access and cost
calculation for specific exchanges.

### Adapter Interface

Every exchange adapter must implement these functions:

```python
"""
Exchange adapter for a new crypto exchange.
"""

from typing import Optional
import pandas as pd


class NewExchangeAdapter:
    """Adapter for NewExchange perpetual futures."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "5m",
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data.

        Returns DataFrame with columns: [timestamp, open, high, low, close, volume]
        Timestamps must be UTC.
        """
        # Implementation here
        ...

    def get_funding_rate(self, symbol: str) -> float:
        """Return current funding rate as a decimal (e.g., 0.0001 = 0.01%)."""
        ...

    def get_leverage_tiers(self, symbol: str) -> list[dict]:
        """
        Return leverage tiers for the symbol.

        Each tier: {"max_notional": float, "max_leverage": int, "margin_rate": float}
        """
        ...

    def calculate_cost(
        self,
        quantity: float,
        price: float,
        side: str,  # "buy" or "sell"
        is_maker: bool = False,
    ) -> float:
        """Calculate total cost for a trade (commission + slippage estimate)."""
        ...

    def get_symbols(self, min_volume_usd: float = 50_000_000) -> list[str]:
        """Discover symbols by minimum 24h volume."""
        ...
```

### Registering the Adapter

Add the adapter to `lib/crypto/exchange_adapters.py`:

```python
from lib.crypto.new_exchange import NewExchangeAdapter

EXCHANGE_ADAPTERS = {
    "binance": BinanceAdapter,
    "bybit": BybitAdapter,
    "okx": OKXAdapter,
    "hyperliquid": HyperliquidAdapter,
    "newexchange": NewExchangeAdapter,  # Add your adapter
}
```

Then create a market profile in `profiles/crypto-cex-newexchange.json`.

---

## Extending Worker Prompts

Worker prompts define the mission for each AI agent type. They live in
`prompts/` and are injected at the start of every Ralph loop session.

### Prompt Structure

```markdown
# Researcher Mission

You are the Researcher worker in the Sigma-Quant Stream research factory.

## Your Mission

Hunt for profitable trading edges from multiple sources...

## Sub-Agents Available

- @quant-idea-hunter: Search the web for trading ideas
- @quant-paper-analyzer: Parse academic papers
...

## Rules

1. Always start by invoking @quant-pattern-learner
2. Delegate all work to sub-agents
3. Never work solo
...

## Output

Push results to queues/hypotheses/ and queues/to-convert/
```

### Customization Points

You can modify prompts to:

- **Change research focus:** Add specific topics or markets to prioritize
- **Adjust quality gates:** Change the validation thresholds
- **Add new sources:** Point agents at specific websites, papers, or datasets
- **Change delegation patterns:** Modify which sub-agents are invoked and when

### Example: Adding a Research Focus

To make the Researcher prioritize funding rate strategies, add to
`prompts/researcher.md`:

```markdown
## Priority Focus (This Session)

Prioritize funding rate mean-reversion strategies for BTC and ETH perpetuals.
Key hypothesis: When 8-hour funding exceeds 0.1%, short bias generates positive
expectancy from funding payments alone.

Sources to search:
- Coinglass funding rate data
- CryptoQuant open interest divergence metrics
- Laevitas funding rate dashboards
```

---

## Creating Custom Agents

Custom agents are Claude Code sub-agents that workers can delegate to. Each
agent is a markdown file in `.claude/agents/`.

### Agent File Format

```markdown
---
model: sonnet
mode: bypassPermissions
skills:
  - quant-research-methodology
  - quant-pattern-knowledge
---

# Quant Funding Rate Analyzer

You are a specialized sub-agent that analyzes cryptocurrency funding rates
to identify mean-reversion trading opportunities.

## Your Job

1. Read the current pattern knowledge from patterns/crypto-what-works.md
2. Fetch funding rate data using the exchange adapter
3. Identify periods where funding rate exceeds historical norms
4. Formulate a hypothesis about the mean-reversion opportunity
5. Push the hypothesis to queues/hypotheses/

## Rules

- Always include cost of funding in your analysis
- Account for liquidation risk at high-leverage entries
- Cross-reference with open interest data
- Never assume funding rate direction persists

## Output Format

Produce a hypothesis JSON file following the standard schema.
```

### Agent Frontmatter Fields

| Field | Options | Description |
|-------|---------|-------------|
| `model` | `opus`, `sonnet`, `haiku` | Which Claude model to use |
| `mode` | `bypassPermissions`, `plan` | Whether the agent can write files directly |
| `skills` | Array of skill names | Domain knowledge to inject |

### Naming Convention

Agent files follow the pattern: `quant-{function}.md`

Examples:
- `quant-funding-analyzer.md`
- `quant-correlation-scanner.md`
- `quant-regime-classifier.md`

---

## Creating Custom Skills

Skills provide domain knowledge that agents reference during execution. They are
markdown files in `.claude/skills/`.

### Skill Directory Structure

```
.claude/skills/
  quant-new-skill/
    SKILL.md              # The skill content
```

### Skill File Format

```markdown
# Funding Rate Analysis Skill

## When to Use

Invoke this skill when analyzing cryptocurrency funding rates for
mean-reversion or carry trade opportunities.

## Key Concepts

### Funding Rate Mechanics

Perpetual futures use funding rates to anchor the perp price to spot.

- **Positive funding:** Longs pay shorts (market is bullish-biased)
- **Negative funding:** Shorts pay longs (market is bearish-biased)
- **Settlement:** Every 8 hours on most exchanges (00:00, 08:00, 16:00 UTC)

### Mean-Reversion Signal

When funding rate exceeds 0.1% per 8-hour period:
1. The cost of holding the position becomes significant
2. Leveraged longs begin to close (reducing buying pressure)
3. Short entry has dual edge: directional + funding income

### Historical Ranges

| Condition | Funding Rate | Signal |
|-----------|-------------|--------|
| Normal | -0.01% to 0.03% | Neutral |
| Elevated | 0.03% to 0.10% | Watch |
| Extreme | > 0.10% | Strong short signal |
| Negative extreme | < -0.05% | Strong long signal |

## Quality Gates

- [ ] Minimum 6 months of funding rate history
- [ ] Account for funding payment timing (not continuous)
- [ ] Include slippage and fees in funding carry calculation
- [ ] Test across multiple market regimes
```

### Referencing Skills in Agents

Add the skill name to the agent's frontmatter:

```yaml
skills:
  - quant-funding-rate-analysis
```

---

## Using the Backtest Runner

The backtest runner at `lib/backtest_runner.py` is the core engine that agents
use for walk-forward validation.

### Direct Usage

```python
from lib.backtest_runner import BacktestRunner

runner = BacktestRunner(
    strategy_class=MyStrategy,
    data_path="data/ES_5m.csv",
    initial_capital=100000,
    commission_per_side=2.50,
    slippage_ticks=0.5,
)

results = runner.run_walk_forward(
    n_splits=5,
    train_pct=0.70,
)

print(f"Sharpe: {results['sharpe']:.2f}")
print(f"Max DD: {results['max_drawdown']:.2%}")
print(f"Trades: {results['total_trades']}")
print(f"OOS Decay: {results['oos_decay']:.2%}")
```

### Walk-Forward Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_splits` | 5 | Number of walk-forward windows |
| `train_pct` | 0.70 | Percentage of data for in-sample training |
| `commission_per_side` | 2.50 | Commission per contract per side (futures) |
| `slippage_ticks` | 0.5 | Slippage in ticks per trade |
| `initial_capital` | 100000 | Starting equity |

### Strategy Class Interface

Your strategy must implement:

```python
class MyStrategy:
    def __init__(self, **params):
        """Accept parameters as keyword arguments."""
        ...

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return a Series of signals: 1 (long), -1 (short), 0 (flat)."""
        ...

    def get_parameters(self) -> dict:
        """Return current parameters."""
        ...
```

---

## Pattern Knowledge Base

The pattern knowledge base is a collection of markdown files in `patterns/`
that agents read at the start of every session and update at the end.

### Files

| File | Purpose |
|------|---------|
| `patterns/what-works.md` | Validated futures approaches with evidence |
| `patterns/what-fails.md` | Documented futures failures to avoid |
| `patterns/indicator-combos.md` | Known good indicator combinations (futures) |
| `patterns/prop-firm-gotchas.md` | Prop firm quirks and edge cases |
| `patterns/crypto-what-works.md` | Validated crypto approaches |
| `patterns/crypto-what-fails.md` | Documented crypto failures |
| `patterns/exchange-gotchas.md` | Per-exchange compliance issues |
| `patterns/indicator-combos-crypto.md` | Crypto indicator combinations |

### Entry Format

Entries in pattern files follow a standard format:

```markdown
### RSI Divergence + Volume Confirmation on ES 5m

**Date:** 2026-01-28
**Session:** researcher-pane-0-session-14
**Result:** PASS (Sharpe 1.4, 180 trades, 12% max DD)

**What worked:** Combining RSI divergence detection with volume spike
confirmation reduced false signals by 40%. The volume filter eliminated
most of the noise from low-volatility periods.

**Parameters:** RSI period=14, divergence window=5, volume threshold=1.5x SMA(20)

**Caveat:** Performance degrades significantly during FOMC announcement days.
Consider adding a news filter.
```

### Contributing to Patterns

You can manually add entries to pattern files. Agents also update them
automatically at the end of each session via the `@sigma-distiller` agent.

When adding entries manually:

1. Include the date and context
2. State whether the approach passed or failed
3. Provide specific metrics (Sharpe, DD, trade count)
4. Document parameters that were tested
5. Note any caveats or edge cases

---

## Testing Your Code

### Python Tests

```bash
# Run all Python tests
python -m pytest -v

# Run a specific test file
python -m pytest test_adaptive_rsi_volume.py -v

# Run with coverage
python -m pytest --cov=lib --cov-report=term-missing
```

### Go Tests

```bash
# Run all Go tests
make test

# Run a specific package
go test ./internal/queue/ -v

# Run with race detector
go test ./... -race
```

### Integration Testing

To test a complete pipeline run without starting the full swarm:

```bash
# Seed a single hypothesis
cp seed/hypotheses/hyp-seed-001-rsi-divergence.json queues/hypotheses/

# Start only the backtester
sigma-quant start backtester

# Watch for results
sigma-quant status --watch
```

### Validating Custom Agents

To test a custom agent in isolation:

```bash
# Run Claude Code with your agent directly
claude --agent .claude/agents/quant-funding-analyzer.md \
  --prompt "Analyze BTC funding rates for the past month"
```

This lets you verify the agent's behavior before integrating it into the
worker pipeline.
