# Trader Path

This guide is for traders who want to discover and validate strategies without
writing code. Sigma-Quant Stream handles the research, backtesting, and
compliance testing autonomously. Your job is to seed ideas, configure risk
parameters, and review the results.

---

## Table of Contents

1. [Zero-Code Workflow Overview](#zero-code-workflow-overview)
2. [Seeding Hypotheses from Your Ideas](#seeding-hypotheses-from-your-ideas)
3. [Configuring Risk Parameters](#configuring-risk-parameters)
4. [Understanding the Strategy Pipeline](#understanding-the-strategy-pipeline)
5. [Reading Backtest Reports](#reading-backtest-reports)
6. [Understanding Prop Firm Compliance](#understanding-prop-firm-compliance)
7. [Deploying to Paper Trading](#deploying-to-paper-trading)
8. [Day-to-Day Usage](#day-to-day-usage)
9. [When to Switch to the Developer Path](#when-to-switch-to-the-developer-path)

---

## Zero-Code Workflow Overview

Here is the complete workflow from idea to paper trading, with no coding
required at any step.

```
Step 1: Configure
  sigma-quant init
  (Choose your market, risk limits, and prop firms)

Step 2: Seed Ideas (optional)
  Write a hypothesis in plain text --> agents convert it to JSON
  Or: let the Researcher agent find ideas autonomously

Step 3: Launch
  sigma-quant start
  (4 agents begin working)

Step 4: Monitor
  sigma-quant status --watch
  (Watch strategies flow through the pipeline)

Step 5: Review Results
  sigma-quant strategies -g good
  sigma-quant strategies -g prop_firm_ready
  (Read the backtest reports and compliance results)

Step 6: Deploy
  sigma-quant deploy
  (Export validated strategy to Freqtrade paper trading)
```

You do not need to write Python, read source code, or understand the internals.
The agents handle everything.

---

## Seeding Hypotheses from Your Ideas

The Researcher agent discovers strategies autonomously, but you can accelerate
the process by seeding your own trading ideas.

### From a TradingView Idea

If you found a promising indicator or strategy on TradingView:

1. Copy the TradingView idea URL or PineScript code
2. Create a text file describing what you want to test:

```
File: seed/hypotheses/my-idea.txt

Title: VWAP Deviation Mean Reversion on ES

I noticed that ES tends to revert to VWAP when it deviates more than
1.5 standard deviations during low-volatility sessions (no FOMC, no
major news). The best entries seem to happen when volume is declining
as price pushes away from VWAP.

Source: TradingView idea by @traderXYZ (https://www.tradingview.com/...)
Markets: ES, NQ
Timeframes: 5min, 15min

Why I think this works:
Institutional VWAP execution algorithms create natural mean-reverting
pressure. When retail traders chase breakouts in a range-bound market,
they become the counterparty.
```

3. Drop it into the seed directory:

```bash
cp my-idea.txt seed/hypotheses/
```

The Researcher agent will pick this up, convert it to a formal hypothesis
card, and push it through the pipeline.

### From Your Own Trading Journal

If you have a recurring pattern you trade manually:

1. Describe the setup conditions
2. Describe the entry and exit rules
3. Estimate how often it triggers per month
4. Explain why you think it works

Write this in plain English and drop it into `seed/hypotheses/`. The agents
will formalize it.

### Letting the Agents Find Ideas

If you have no specific ideas, that is fine. The Researcher agent automatically:

- Searches the web for trading strategies and indicators
- Analyzes academic papers on quantitative trading
- Scrapes TradingView for popular indicators
- Combines known indicators in novel ways
- Tests ideas from the pattern knowledge base

Just run `sigma-quant start` and let it work.

---

## Configuring Risk Parameters

Risk parameters control which strategies pass validation and which get rejected.
You configure these once during `sigma-quant init` or by editing `config.json`.

### Validation Thresholds

```json
{
  "validation": {
    "strategy": {
      "minSharpe": 1.0,
      "maxSharpe": 3.0,
      "maxDrawdown": 0.20,
      "minTrades": 100,
      "maxWinRate": 0.80,
      "maxOosDecay": 0.30
    }
  }
}
```

### What Each Threshold Means

| Parameter | Default | What It Controls |
|-----------|---------|-----------------|
| `minSharpe` | 1.0 | Minimum risk-adjusted return. Below this, strategy is rejected. |
| `maxSharpe` | 3.0 | Maximum Sharpe before suspecting curve-fitting. Above this, rejected. |
| `maxDrawdown` | 0.20 | Maximum peak-to-trough loss (20%). Above this, rejected. |
| `minTrades` | 100 | Minimum number of trades for statistical significance. |
| `maxWinRate` | 0.80 | Win rates above 80% suggest look-ahead bias. Rejected. |
| `maxOosDecay` | 0.30 | How much performance drops out-of-sample. Above 30%, under review. |

### Adjusting for Your Risk Tolerance

**Conservative trader (smaller drawdowns, more trades):**

```json
{
  "validation": {
    "strategy": {
      "minSharpe": 1.2,
      "maxDrawdown": 0.10,
      "minTrades": 200
    }
  }
}
```

**Aggressive trader (accept larger drawdowns for higher returns):**

```json
{
  "validation": {
    "strategy": {
      "minSharpe": 0.8,
      "maxDrawdown": 0.30,
      "minTrades": 50
    }
  }
}
```

Edit `config.json` directly, or use:

```bash
sigma-quant config set validation.strategy.maxDrawdown 0.15
```

### Choosing Your Market Profile

```bash
# List available profiles
sigma-quant config profiles

# Switch to crypto
sigma-quant config set activeProfile profiles/crypto-cex.json

# Switch back to futures
sigma-quant config set activeProfile profiles/futures.json
```

Each profile has its own cost model and compliance rules. You do not need to
configure costs manually.

---

## Understanding the Strategy Pipeline

Every strategy flows through four stages, each handled by a different worker.

### Stage 1: Research (Researcher Agent)

The Researcher hunts for trading ideas from:
- Web search (academic papers, trading forums, blogs)
- TradingView indicator analysis
- Your seeded hypotheses
- Pattern knowledge base (what has worked before)

**Output:** Hypothesis cards pushed to `queues/hypotheses/` or `queues/to-convert/`

### Stage 2: Conversion (Converter Agent)

The Converter takes strategy ideas and turns them into testable Python code:
- Translates PineScript indicators to Python
- Wraps indicators into strategy classes
- Generates unit tests
- Creates documentation

**Output:** Python strategies pushed to `queues/to-backtest/`

### Stage 3: Backtesting (Backtester Agent)

The Backtester runs rigorous validation:
- Walk-forward testing (no random shuffles, proper train/test splits)
- Cost-inclusive simulation (commissions + slippage always included)
- Anti-overfitting checks (Sharpe > 3 = rejected, win rate > 80% = rejected)
- Out-of-sample decay measurement

**Output:** Validated strategies pushed to `queues/to-optimize/`. Failures go
to `output/strategies/rejected/`.

### Stage 4: Optimization (Optimizer Agent)

The Optimizer fine-tunes and validates compliance:
- Coarse grid search for parameter optimization
- Perturbation testing (parameters shifted +/- 20% must stay profitable)
- Base Hit analysis (cash exit optimization on losing trades)
- Prop firm compliance testing (14 firms for futures)
- Exchange compliance testing (leverage tiers for crypto)

**Output:** Strategies routed to:
- `output/strategies/good/` -- Passed all checks
- `output/strategies/prop_firm_ready/` -- Also passed 3+ prop firm validators
- `output/strategies/under_review/` -- Borderline metrics (needs human review)

### Pipeline Flow Diagram

```
Your Ideas + Agent Research
         |
         v
  [1] RESEARCHER ---> hypotheses queue
         |
         v
  [2] CONVERTER  ---> to-backtest queue
         |
         v
  [3] BACKTESTER ---> to-optimize queue
         |                    |
         |                    +---> rejected/ (fails validation)
         v
  [4] OPTIMIZER  ---> good/
                 ---> prop_firm_ready/
                 ---> under_review/
```

---

## Reading Backtest Reports

Each validated strategy produces a `backtest_results.json` file. Here is how to
interpret the key metrics.

### Key Metrics Explained

| Metric | What It Means | Good Range | Red Flag |
|--------|--------------|------------|----------|
| **Sharpe Ratio** | Return per unit of risk. Higher = better risk-adjusted returns. | 1.0 - 2.5 | < 1.0 (too risky) or > 3.0 (likely overfit) |
| **Max Drawdown** | Largest peak-to-trough decline. How much you could lose before recovery. | < 15% | > 30% |
| **Total Trades** | Number of trades in the backtest. More = more statistical confidence. | > 100 | < 30 (insufficient data) |
| **Win Rate** | Percentage of winning trades. | 50% - 70% | > 80% (suspicious) |
| **Profit Factor** | Gross profits / gross losses. Above 1.0 means net profitable. | 1.3 - 2.5 | < 1.0 (unprofitable) |
| **OOS Decay** | How much Sharpe drops from in-sample to out-of-sample. Measures generalization. | < 20% | > 50% (does not generalize) |
| **Avg Trade** | Average profit/loss per trade including costs. | Positive | Negative |
| **Max Consecutive Losses** | Longest losing streak. Affects psychological tolerance. | < 10 | > 20 |

### Example Report

```
Strategy: RSI Divergence + Volume (ES 5m)
Period: 2023-01-01 to 2025-12-31 (3 years)
Walk-forward: 5 splits, 70/30 train/test

Results:
  Sharpe Ratio:     1.42
  Max Drawdown:     -11.8%
  Total Trades:     234
  Win Rate:         58.1%
  Profit Factor:    1.67
  OOS Decay:        18.3%
  Avg Trade:        $127.50
  Max Consec Losses: 7
  Net Profit:       $29,835

Costs Included:
  Commission:       $2.50/side
  Slippage:         0.5 ticks
  Total Cost Impact: $1,170

Verdict: GOOD (promoted to output/strategies/good/)
```

### What "Good" vs "Prop Firm Ready" Means

- **Good:** The strategy passes all validation gates. It has a real edge based
  on the backtest data. Suitable for personal paper trading.

- **Prop Firm Ready:** The strategy additionally passes compliance tests for 3
  or more prop trading firms. This means it respects daily loss limits, trailing
  drawdown rules, and consistency requirements specific to those firms.

---

## Understanding Prop Firm Compliance

If you trade futures through a prop firm, the Optimizer tests every strategy
against the rules of 14 firms.

### What Gets Tested

| Rule | Description |
|------|-------------|
| **Daily Loss Limit** | Maximum loss allowed in a single trading day |
| **Trailing Drawdown** | Maximum drawdown from peak equity (resets or does not, varies by firm) |
| **Consistency Rule** | No single day can represent more than X% of total profits |
| **Windfall Rule** | Limits on maximum single-day profit (some firms only) |
| **Max Position Size** | Maximum contracts allowed per trade |

### Firms Tested

The system tests against: TakeProfitTrader, TopStep, Apex, Tradeify, Bulenox,
Earn2Trade, MyFundedFX, The Funded Trader, BluSky, Leeloo, OneUp Trader,
Funded Trading Plus, and True Trader.

### Reading Compliance Results

Each strategy in `prop_firm_ready/` includes a `compliance.json`:

```json
{
  "firms_tested": 14,
  "firms_passed": 8,
  "firms_failed": 6,
  "passing_firms": [
    {"name": "TakeProfitTrader", "margin": "32% below daily limit"},
    {"name": "TopStep", "margin": "18% below trailing DD"},
    {"name": "Apex", "margin": "25% below windfall rule"}
  ],
  "failing_firms": [
    {"name": "Bulenox", "reason": "Exceeds daily loss limit by 12%"},
    {"name": "FTMO", "reason": "Not supported (forex only)"}
  ]
}
```

The "margin" field tells you how much headroom the strategy has before hitting
the firm's limits. Higher margins are better.

---

## Deploying to Paper Trading

Once you have a strategy in `good/` or `prop_firm_ready/`, deploy it to
Freqtrade paper trading.

### Deploy Command

```bash
sigma-quant deploy
```

This interactive command:

1. Lists all strategies in `good/` and `prop_firm_ready/`
2. Lets you select one to deploy
3. Converts the strategy to a Freqtrade `IStrategy` class
4. Generates Freqtrade configuration (dry-run mode)
5. Provides instructions to start Freqtrade

### Freqtrade Dry-Run

Freqtrade dry-run mode simulates live trading with real market data but no real
money. This is the recommended step before going live.

```bash
# After sigma-quant deploy generates the config:
cd freqtrade/
freqtrade trade --config user_data/config.json --strategy SigmaQuantStrategy --dry-run
```

### What to Watch During Paper Trading

| Check | Frequency | Action |
|-------|-----------|--------|
| Trade frequency | Daily | Should match backtest's trades/month |
| Win rate | Weekly | Should be within 10% of backtest |
| Drawdown | Continuous | Should not exceed backtest max DD significantly |
| Slippage | Weekly | Compare actual fills to expected fills |
| Edge decay | Monthly | If Sharpe drops below 0.5, deactivate |

Paper trade for at least 2-4 weeks before considering live deployment.

---

## Day-to-Day Usage

### Morning Routine

```bash
# Check what the agents found overnight
sigma-quant strategies -g good
sigma-quant strategies -g prop_firm_ready

# Check swarm status
sigma-quant status
```

### Keeping the Swarm Running

The swarm runs indefinitely once started. To keep it productive:

1. **Check costs weekly:** `sigma-quant status` shows cumulative API spend
2. **Review rejected strategies:** Browse `output/strategies/rejected/` to
   understand what the agents tried and why it failed
3. **Seed new ideas:** Drop hypothesis files into `seed/hypotheses/` when you
   have new trading ideas
4. **Update risk parameters:** If your risk tolerance changes, update
   `config.json` and restart the swarm

### Restarting After Maintenance

```bash
sigma-quant stop
# Make any config changes
sigma-quant start
```

The agents pick up where they left off, reading session summaries and queue
state from the previous run.

---

## When to Switch to the Developer Path

Consider the [Developer Path](developer-path.md) when you want to:

- **Write custom indicators** that the agents cannot discover on their own
- **Add a new data source** (e.g., an exchange not currently supported)
- **Modify validation rules** beyond what config.json allows
- **Create specialized agents** for a niche market or strategy type
- **Integrate with your existing trading infrastructure**

You do not need to switch entirely. Many users combine both paths: letting
the agents discover strategies autonomously while also seeding custom
hypotheses and indicators.

The developer path gives you full control over every aspect of the system.
The trader path gives you results with minimal effort. Both are valid
approaches.
