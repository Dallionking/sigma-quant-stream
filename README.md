<p align="center">
  <strong>Sigma-Quant Stream</strong>
</p>

<p align="center">
  <em>Your autonomous hedge fund research team -- powered by Claude Code agent swarms.</em>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="License: AGPL-3.0"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB.svg?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Claude%20Code-agent%20swarm-orange.svg" alt="Claude Code">
  <img src="https://img.shields.io/badge/markets-futures%20%7C%20crypto-green.svg" alt="Markets">
  <a href="https://github.com/Dallionking/sigma-quant-stream/actions"><img src="https://img.shields.io/github/actions/workflow/status/Dallionking/sigma-quant-stream/test.yml?label=tests" alt="Tests"></a>
</p>

---

Sigma-Quant Stream is an open-source strategy research factory that runs autonomous AI agents to discover, backtest, and validate trading strategies. It is like having your own team of quant researchers working around the clock -- hunting for edges, converting indicators, running walk-forward backtests, and validating against prop firm and exchange compliance rules.

You start it. You go to sleep. You wake up to validated strategies.

---

## How It Works

```
+------------------------------------------------------------------+
|                    SIGMA-QUANT STREAM                             |
|                   tmux session (4 panes)                         |
+------------------------------------------------------------------+
|                          |                                        |
|  +--------------------+ | +--------------------+                  |
|  |  PANE 0            | | |  PANE 1            |                  |
|  |  Researcher        | | |  Converter          |                 |
|  |  8 sub-agents      | | |  7 sub-agents      |                  |
|  |                    | | |                    |                  |
|  |  Hunt ideas from   | | |  PineScript -->    |                  |
|  |  web, papers, TV   | | |  Python + tests    |                  |
|  +--------+-----------+ | +--------+-----------+                  |
|           |              |          |                              |
|           v              |          v                              |
|  +--------------------+ | +--------------------+                  |
|  |  PANE 2            | | |  PANE 3            |                  |
|  |  Backtester        | | |  Optimizer          |                 |
|  |  10 sub-agents     | | |  10 sub-agents     |                  |
|  |                    | | |                    |                  |
|  |  Walk-forward      | | |  Grid search,      |                  |
|  |  validation        | | |  prop firm test    |                  |
|  +--------+-----------+ | +--------+-----------+                  |
|           |              |          |                              |
+------------------------------------------------------------------+
            |                         |
            v                         v
+------------------------------------------------------------------+
|              FILE-BASED QUEUE COORDINATION                        |
|                                                                  |
|  hypotheses/ --> to-convert/ --> to-backtest/ --> to-optimize/    |
+------------------------------------------------------------------+
            |
            v
+------------------------------------------------------------------+
|              PATTERN KNOWLEDGE BASE                               |
|                                                                  |
|  what-works.md | what-fails.md | indicator-combos.md             |
|  (grows every session -- agents learn from each other)           |
+------------------------------------------------------------------+
            |
            v
+------------------------------------------------------------------+
|              OUTPUT: VALIDATED STRATEGIES                          |
|                                                                  |
|  strategies/good/  |  strategies/prop_firm_ready/  |  rejected/  |
+------------------------------------------------------------------+
```

Each worker runs an infinite **Ralph loop** -- when a Claude Code session ends, a new one starts with fresh context, injected with the latest pattern knowledge and queue state. The agents never stop discovering.

---

## Installation

### Homebrew (macOS/Linux)

```bash
brew install Dallionking/tap/sigma-quant
```

### Go Install

```bash
go install github.com/Dallionking/sigma-quant-stream/cmd/sigma-quant@latest
```

### From Source

```bash
git clone https://github.com/Dallionking/sigma-quant-stream.git
cd sigma-quant-stream
make build
./bin/sigma-quant --help
```

### Python (Legacy)

```bash
pip install -e .
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Dallionking/sigma-quant-stream.git
cd sigma-quant-stream

# 2. Install (Go binary)
make build

# 3. Configure
cp .env.example .env
# Edit .env with your API keys (at minimum: ANTHROPIC_API_KEY)

# 4. Health check
sigma-quant health

# 5. Launch all 4 workers
sigma-quant start

# 6. Monitor
sigma-quant status --watch
```

---

## Markets Supported

| Market | Data Source | Cost Model | Compliance | Status |
|--------|-----------|------------|------------|--------|
| CME Futures (ES, NQ, YM, GC) | Databento | Fixed per-contract ($2.50/side + tick slippage) | 14 prop firms | Production |
| Crypto CEX (Binance, Bybit, OKX) | CCXT (free) | Percentage-based (maker/taker + funding) | Exchange leverage tiers | Production |
| Crypto DEX (Hyperliquid) | Native API | Percentage + gas | On-chain limits | Production |

Market selection is profile-driven. Switch markets by changing the active profile:

```bash
sigma-quant config profiles    # List available profiles
```

---

## Features

### Research & Discovery
- **Autonomous Research** -- Agents discover strategies from the web, academic papers, and TradingView scripts
- **Hypothesis-First** -- Every strategy starts with a written hypothesis explaining why the edge should exist
- **Pattern Learning** -- Cross-session knowledge base (`what-works.md`, `what-fails.md`) that improves over time
- **Multi-Source** -- EXA web search, academic paper analysis, TradingView indicator scraping

### Validation & Quality
- **Walk-Forward Validation** -- No random shuffles, proper out-of-sample testing with tracked IS/OOS decay
- **Anti-Overfitting Gates** -- Automatic rejection of curve-fitted strategies (Sharpe > 3, win rate > 80%, < 100 trades)
- **Cost-Inclusive Backtesting** -- Every backtest includes commissions + slippage. Never test without costs.
- **Robustness Checks** -- Parameter perturbation testing (plus/minus 20% must maintain profitability)

### Compliance
- **Prop Firm Compliance** -- Validates futures strategies against 14 prop firms (Apex, Topstep, Earn2Trade, etc.)
- **Exchange Compliance** -- Validates crypto strategies against exchange rules (leverage tiers, liquidation buffers)
- **Base Hit Optimization** -- Cash exit analysis (loss MFE) on every strategy

### Deployment
- **Paper Trading** -- Deploy validated strategies to Freqtrade dry-run with one command
- **Strategy Grading** -- Automatic routing: `rejected/` -> `under_review/` -> `good/` -> `prop_firm_ready/`

---

## Agent Swarm Architecture

The system runs **4 main workers** in tmux panes, each with specialized sub-agents:

### Workers

| Worker | Pane | Mission | Sub-Agents | Output Queue |
|--------|------|---------|------------|--------------|
| **Researcher** | 0 | Hunt for trading edges | 8 | `hypotheses/`, `to-convert/` |
| **Converter** | 1 | PineScript to Python translation | 7 | `to-backtest/` |
| **Backtester** | 2 | Walk-forward validation, reject overfit | 10 | `to-optimize/` |
| **Optimizer** | 3 | Parameter optimization, compliance testing | 10 | `output/strategies/` |

### Sub-Agents (44 Total)

**Researcher (8):** idea-hunter, paper-analyzer, tv-scraper, hypothesis-writer, combo-finder, edge-validator, pattern-learner, queue-pusher

**Converter (7):** pine-parser, pandas-adapter, class-wrapper, test-writer, signal-extractor, readme-gen, conversion-pusher

**Backtester (10):** walk-forward, oos-analyzer, overfit-checker, sample-validator, mfe-tracker, cost-validator, regime-detector, metrics-calc, reject-router, results-logger

**Optimizer (10):** coarse-grid, perturb-tester, loss-mfe, base-hit, prop-firm-validator, firm-ranker, config-gen, artifact-builder, promo-router, notifier

**Crypto (9):** crypto-researcher, exchange-validator, funding-analyzer, liquidation-tracker, onchain-researcher, market-maker, arb-detector, freqtrade-deployer, risk-modeler

### The Ralph Loop

Each worker runs an infinite restart loop. When a Claude Code session ends (context fills up, task completes, or timeout), a fresh session starts with:

1. The worker's mission prompt
2. The last session summary
3. Current pattern knowledge (what works, what fails)
4. Current queue state

This means the swarm runs indefinitely -- discovering, converting, backtesting, and optimizing strategies without human intervention.

### Queue IPC Protocol

Workers communicate through file-based queues with atomic operations:

```
Researcher -> hypotheses/     -> Backtester
Researcher -> to-convert/     -> Converter
Converter  -> to-backtest/    -> Backtester
Backtester -> to-optimize/    -> Optimizer
Optimizer  -> output/strategies/
```

Each queue item is a JSON file with an ID, timestamp, priority, status, and payload. Claiming uses atomic file rename to prevent conflicts.

---

## Strategy Pass Criteria

| Metric | Pass | Good | Reject |
|--------|------|------|--------|
| Sharpe Ratio | > 1.0 | > 1.5 | < 1.0 or > 3.0 |
| Max Drawdown | < 20% | < 15% | > 30% |
| Trade Count | > 100 | > 200 | < 30 |
| OOS Decay | < 30% | < 20% | > 50% |
| Win Rate | < 80% | 50-70% | > 80% (bias) |

Strategies with Sharpe > 3.0 or win rate > 80% are auto-rejected as likely curve-fitted.

---

## Tutorial

Run `sigma-quant tutorial` for a guided 6-step walkthrough:

1. **Create a hypothesis** -- Write a testable trading idea with economic rationale
2. **Write a strategy** -- Implement the strategy as a Python class with signal generation
3. **Run a backtest** -- Execute walk-forward validation with cost-inclusive simulation
4. **Optimize parameters** -- Coarse grid search with perturbation robustness testing
5. **Validate compliance** -- Test against prop firms (futures) or exchange rules (crypto)
6. **Deploy to paper trading** -- Export to Freqtrade dry-run for live validation

---

## Configuration

### config.json

The main configuration file controls workers, queues, validation thresholds, and market profiles:

```json
{
  "activeProfile": "profiles/futures.json",
  "defaults": {
    "panes": 4,
    "mode": "research",
    "maxHours": 24,
    "notify": "elevenlabs"
  },
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

### Market Profiles

Profiles live in `profiles/` and control data sources, cost models, and compliance rules:

- `futures.json` -- Databento data, per-contract costs, 14 prop firm validators
- `crypto-cex.json` -- CCXT data, percentage-based fees + funding, exchange leverage tiers
- `crypto-dex-hyperliquid.json` -- Hyperliquid API, percentage + gas, on-chain limits

### Cost Models

Costs are **never hardcoded**. They are dispatched from the active profile:

- **Futures:** $2.50/contract/side commission + 0.5 tick slippage
- **Crypto CEX:** Maker 0.02% + Taker 0.05% + funding rate (8h) + 0.05% slippage
- **Crypto DEX:** Maker 0.02% + Taker 0.05% + gas (variable) + 0.1% slippage

---

## Project Structure

```
sigma-quant-stream/
|-- cli/                          # CLI commands (sigma-quant)
|   |-- main.py                   # Typer app entry point
|   |-- health.py                 # Health check logic
|   |-- status.py                 # Dashboard and monitoring
|   +-- strategies.py             # Strategy listing
|-- lib/                          # Core library
|   |-- backtest_runner.py        # Vectorized backtest engine
|   +-- crypto/                   # Crypto market adapters
|       |-- exchange_adapters.py  # CCXT + Hyperliquid adapters
|       |-- cost_model.py         # Crypto cost calculations
|       |-- funding_rate_service.py
|       |-- liquidation_service.py
|       |-- onchain_service.py
|       |-- risk_modeler.py
|       |-- freqtrade_bridge.py   # Freqtrade IStrategy conversion
|       +-- arbitrage_detector.py
|-- profiles/                     # Market profile configs
|   |-- futures.json
|   |-- crypto-cex.json
|   +-- crypto-dex-hyperliquid.json
|-- patterns/                     # Cross-session knowledge base
|   |-- what-works.md
|   |-- what-fails.md
|   |-- indicator-combos.md
|   +-- exchange-gotchas.md
|-- queues/                       # Inter-worker IPC
|   |-- hypotheses/
|   |-- to-convert/
|   |-- to-backtest/
|   +-- to-optimize/
|-- seed/                         # Queue priming data
|   |-- hypotheses/
|   +-- to-convert/
|-- scripts/                      # Operational scripts
|   |-- quant-ralph.sh            # Ralph loop (infinite restart)
|   |-- tmux-quant-launcher.sh    # tmux session manager
|   |-- spawn-quant-team.sh       # Team launcher
|   |-- health-check.py           # Dependency checker
|   +-- setup-wizard.py           # Interactive setup
|-- prompts/                      # Worker mission prompts
|   |-- researcher.md
|   |-- converter.md
|   |-- backtester.md
|   +-- optimizer.md
|-- output/                       # Results and artifacts
|   |-- strategies/
|   |   |-- good/
|   |   |-- prop_firm_ready/
|   |   |-- under_review/
|   |   +-- rejected/
|   +-- backtests/
|-- data/                         # Sample and downloaded data
|-- freqtrade/                    # Freqtrade deployment configs
+-- config.json                   # Main configuration
```

---

## Requirements

| Dependency | Required | Purpose |
|-----------|----------|---------|
| Python 3.11+ | Yes | Runtime |
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) | Yes | Agent swarm execution |
| tmux | Yes | Multi-pane agent sessions |
| `ANTHROPIC_API_KEY` | Yes | Claude API access |
| `DATABENTO_API_KEY` | Optional | CME futures market data |
| Exchange API keys | Optional | Crypto CEX trading (public data works without keys) |

Install tmux:
```bash
# macOS
brew install tmux

# Ubuntu/Debian
sudo apt install tmux

# Arch
sudo pacman -S tmux
```

---

## CLI Reference

```bash
sigma-quant init              # Interactive onboarding
sigma-quant start             # Launch all 4 workers in tmux
sigma-quant start researcher  # Launch a single worker
sigma-quant stop              # Graceful shutdown
sigma-quant status            # Dashboard: workers, queues, costs
sigma-quant status --watch    # Live-updating dashboard
sigma-quant strategies        # List discovered strategies
sigma-quant strategies -g good  # Filter by grade
sigma-quant health            # Dependency and config check
sigma-quant deploy            # Export to Freqtrade paper trading
sigma-quant tutorial          # Guided 6-step walkthrough
sigma-quant config            # View config.json
sigma-quant config profiles   # List market profiles
sigma-quant data download     # Download market data
sigma-quant data status       # Show data coverage
```

---

## Community

- [YouTube](https://youtube.com/@sigma-quant) -- Tutorials and strategy research walkthroughs
- [GitHub Discussions](https://github.com/Dallionking/sigma-quant-stream/discussions) -- Questions, ideas, show-and-tell
- [Instagram](https://instagram.com/sigma.quant) -- Updates and behind-the-scenes

---

## License

AGPL-3.0 -- See [LICENSE](LICENSE) for the full text.

Copyright 2026 Dallion King.
