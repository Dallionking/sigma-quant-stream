# Stream-Quant Autonomous Research Factory

> **Mission**: Discover, validate, and integrate profitable trading strategies overnight.
> **Mode**: Fully autonomous swarm with 4 workers + 44 specialized sub-agents.
> **Markets**: Futures (ES, NQ, YM, GC) + Crypto (BTC, ETH perps on Binance/Bybit/OKX/Hyperliquid)
> **Philosophy**: Swarm-first — always delegate to sub-agents.

---

## Swarm Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         STREAM-QUANT SWARM FACTORY                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   CLAUDE.md     │         │   config.json   │         │   prompts/*.md  │
│ (Swarm Rules)   │         │ (Configuration) │         │ (Worker Missions)│
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │  quant-ralph.sh │ │ quant-swarm-    │ │ quant-control.sh│
          │  (Worker Loop)  │ │ launcher.sh     │ │ (Dashboard)     │
          └────────┬────────┘ └─────────────────┘ └─────────────────┘
                   │
     ┌─────────────┼─────────────┬─────────────┬─────────────┐
     │             │             │             │             │
     ▼             ▼             ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐
│RESEARCHER│  │CONVERTER│  │BACKTESTER│ │OPTIMIZER│  │@sigma-      │
│ (Pane 0)│  │ (Pane 1)│  │ (Pane 2) │ │ (Pane 3)│  │ distiller   │
│ 8 agents│  │ 7 agents│  │ 10 agents│ │10 agents│  │(Session End)│
└────┬────┘  └────┬────┘  └────┬─────┘ └────┬────┘  └─────────────┘
     │            │            │            │
     ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      QUEUE LAYER (File IPC)                      │
│  hypotheses/ → to-convert/ → to-backtest/ → to-optimize/        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PATTERN KNOWLEDGE BASE                       │
│  what-works.md │ what-fails.md │ indicator-combos.md             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        OUTPUT ARTIFACTS                          │
│  strategies/good/ │ strategies/prop_firm_ready/ │ rejected/      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Swarm-First Philosophy

**CRITICAL RULE: Never work solo. Always delegate to sub-agents.**

Every task, no matter how simple, should leverage the agent swarm.

### Mandatory Delegation Rules

1. **Always spawn sub-agents** - Use the Task tool to delegate work
2. **Match agents to tasks** - Use the right quant-* agent for each job
3. **Invoke skills explicitly** - Sub-agents MUST use `/skill-name` for domain expertise
4. **Parallelize when possible** - Spawn up to 5 sub-agents concurrently
5. **Pattern-first** - Always read pattern files before starting

### Worker → Sub-Agent Delegation Pattern

```bash
# WRONG - Working solo
[Read files, make edits directly, run backtests]

# CORRECT - Delegate to swarm
[Spawn @quant-pattern-learner first]     # Load context
[Spawn @quant-idea-hunter in parallel]   # Find ideas
[Spawn @quant-hypothesis-writer]         # Formulate
[Spawn @quant-queue-pusher last]         # Queue atomically
```

---

## Worker Definitions (4 Main Workers)

| Worker | Pane | Mission | Sub-Agents | Output Queue |
|--------|------|---------|------------|--------------|
| **Researcher** | 0 | Hunt for edges, formulate hypotheses | 8 | `queues/hypotheses/`, `queues/to-convert/` |
| **Converter** | 1 | PineScript → Python translation | 7 | `queues/to-backtest/` |
| **Backtester** | 2 | Walk-forward validation, reject overfit | 10 | `queues/to-optimize/` |
| **Optimizer** | 3 | Parameters, Base Hit, prop firm compliance | 10 | `output/strategies/` |

Each worker runs an infinite mission loop — never stop when queues empty, keep discovering.

---

## Market Profiles

The factory supports multiple market profiles. Each profile configures data sources, cost models, and compliance rules.

| Profile | Data Source | Cost Model | Compliance |
|---------|------------|------------|------------|
| `futures` | Databento | $2.50/side + 0.5 tick slippage | 14 prop firms |
| `crypto-cex` | CCXT (Binance, Bybit, OKX) | maker/taker % + funding + slippage | Exchange leverage tiers |
| `crypto-dex` | Hyperliquid SDK | maker/taker % + gas + slippage | On-chain limits |

### Profile Dispatch Rules
- **Data**: Futures → Databento bars; Crypto → CCXT OHLCV or Hyperliquid API
- **Costs**: Futures → fixed $/contract; Crypto → percentage-based fees + funding rate + gas
- **Compliance**: Futures → prop firm validation (14 firms); Crypto → exchange validation (leverage tiers, liquidation buffers)
- **Risk**: Futures → 1.5x margin buffer; Crypto → 2-3x margin buffer (fat tails)
- **Pattern files**: Futures → `what-works.md`, `what-fails.md`; Crypto → `crypto-what-works.md`, `crypto-what-fails.md`

---

## Sub-Agent Registry (44 Specialized Agents)

### Researcher Sub-Agents (8)

| Agent | File | Purpose | Parallelizable |
|-------|------|---------|----------------|
| `@quant-idea-hunter` | `.claude/agents/stream-quant/quant-idea-hunter.md` | Search web for trading ideas via EXA | Yes |
| `@quant-paper-analyzer` | `.claude/agents/stream-quant/quant-paper-analyzer.md` | Parse academic papers, extract methods | Yes |
| `@quant-tv-scraper` | `.claude/agents/stream-quant/quant-tv-scraper.md` | Scrape TradingView indicators | Yes |
| `@quant-hypothesis-writer` | `.claude/agents/stream-quant/quant-hypothesis-writer.md` | Formulate testable hypotheses | No |
| `@quant-combo-finder` | `.claude/agents/stream-quant/quant-combo-finder.md` | Find complementary indicator pairs | Yes |
| `@quant-edge-validator` | `.claude/agents/stream-quant/quant-edge-validator.md` | Pre-validate economic rationale | No |
| `@quant-pattern-learner` | `.claude/agents/stream-quant/quant-pattern-learner.md` | Read pattern files at session start | No (FIRST) |
| `@quant-queue-pusher` | `.claude/agents/stream-quant/quant-queue-pusher.md` | Atomic queue file operations | No (LAST) |

**Invocation Order**: `@quant-pattern-learner` → [parallel agents] → `@quant-queue-pusher`

### Converter Sub-Agents (7)

| Agent | File | Purpose | Parallelizable |
|-------|------|---------|----------------|
| `@quant-pine-parser` | `.claude/agents/stream-quant/quant-pine-parser.md` | Parse PineScript AST | No (FIRST) |
| `@quant-pandas-adapter` | `.claude/agents/stream-quant/quant-pandas-adapter.md` | Map to pandas-ta functions | Yes |
| `@quant-class-wrapper` | `.claude/agents/stream-quant/quant-class-wrapper.md` | Generate Python class | No |
| `@quant-test-writer` | `.claude/agents/stream-quant/quant-test-writer.md` | Generate pytest tests | Yes |
| `@quant-signal-extractor` | `.claude/agents/stream-quant/quant-signal-extractor.md` | Add signal generation logic | No |
| `@quant-readme-gen` | `.claude/agents/stream-quant/quant-readme-gen.md` | Generate documentation | Yes |
| `@quant-conversion-pusher` | `.claude/agents/stream-quant/quant-conversion-pusher.md` | Push to backtest queue | No (LAST) |

### Backtester Sub-Agents (10)

| Agent | File | Purpose | Parallelizable |
|-------|------|---------|----------------|
| `@quant-walk-forward` | `.claude/agents/stream-quant/quant-walk-forward.md` | Execute WFO backtest | No (FIRST) |
| `@quant-oos-analyzer` | `.claude/agents/stream-quant/quant-oos-analyzer.md` | Calculate OOS decay | Yes |
| `@quant-overfit-checker` | `.claude/agents/stream-quant/quant-overfit-checker.md` | Check Sharpe>3, WR>80% | Yes |
| `@quant-sample-validator` | `.claude/agents/stream-quant/quant-sample-validator.md` | Ensure 100+ trades | Yes |
| `@quant-mfe-tracker` | `.claude/agents/stream-quant/quant-mfe-tracker.md` | Track MFE on each trade | Yes |
| `@quant-cost-validator` | `.claude/agents/stream-quant/quant-cost-validator.md` | Ensure costs included | Yes |
| `@quant-regime-detector` | `.claude/agents/stream-quant/quant-regime-detector.md` | Detect market regime | Yes |
| `@quant-metrics-calc` | `.claude/agents/stream-quant/quant-metrics-calc.md` | Calculate Sharpe, DD, etc. | Yes |
| `@quant-reject-router` | `.claude/agents/stream-quant/quant-reject-router.md` | Route failures to rejected/ | No |
| `@quant-results-logger` | `.claude/agents/stream-quant/quant-results-logger.md` | Log all backtest results | No (LAST) |

### Optimizer Sub-Agents (10)

| Agent | File | Purpose | Parallelizable |
|-------|------|---------|----------------|
| `@quant-coarse-grid` | `.claude/agents/stream-quant/quant-coarse-grid.md` | Coarse parameter grid search | No (FIRST) |
| `@quant-perturb-tester` | `.claude/agents/stream-quant/quant-perturb-tester.md` | ±20% robustness test | Yes |
| `@quant-loss-mfe` | `.claude/agents/stream-quant/quant-loss-mfe.md` | Analyze losing trade MFE | Yes |
| `@quant-base-hit` | `.claude/agents/stream-quant/quant-base-hit.md` | Calculate cash exit levels | No |
| `@quant-prop-firm-validator` | `.claude/agents/stream-quant/quant-prop-firm-validator.md` | Test all 14 prop firms | Yes |
| `@quant-firm-ranker` | `.claude/agents/stream-quant/quant-firm-ranker.md` | Rank best firms for strategy | No |
| `@quant-config-gen` | `.claude/agents/stream-quant/quant-config-gen.md` | Generate strategy configs | Yes |
| `@quant-artifact-builder` | `.claude/agents/stream-quant/quant-artifact-builder.md` | Build strategy package | No |
| `@quant-promo-router` | `.claude/agents/stream-quant/quant-promo-router.md` | Route to good/prop_firm_ready | No |
| `@quant-notifier` | `.claude/agents/stream-quant/quant-notifier.md` | ElevenLabs voice notifications | No (LAST) |

### Crypto Sub-Agents (9)

| Agent | File | Purpose | Parallelizable |
|-------|------|---------|----------------|
| `@quant-crypto-researcher` | `.claude/agents/stream-quant/quant-crypto-researcher.md` | Crypto idea hunting (CryptoQuant, Glassnode, DeFi Llama) | Yes |
| `@quant-exchange-validator` | `.claude/agents/stream-quant/quant-exchange-validator.md` | Exchange compliance (leverage tiers, liquidation buffers) | Yes |
| `@quant-funding-analyzer` | `.claude/agents/stream-quant/quant-funding-analyzer.md` | Funding rate analysis & carry trades | Yes |
| `@quant-liquidation-tracker` | `.claude/agents/stream-quant/quant-liquidation-tracker.md` | Liquidation cascade detection & OI divergence | Yes |
| `@quant-onchain-researcher` | `.claude/agents/stream-quant/quant-onchain-researcher.md` | On-chain signal aggregation (SOPR, MVRV, flows) | Yes |
| `@quant-market-maker` | `.claude/agents/stream-quant/quant-market-maker.md` | Avellaneda-Stoikov market making for crypto perps | No |
| `@quant-arb-detector` | `.claude/agents/stream-quant/quant-arb-detector.md` | Cross-exchange arbitrage detection | Yes |
| `@quant-freqtrade-deployer` | `.claude/agents/stream-quant/quant-freqtrade-deployer.md` | Freqtrade IStrategy conversion & deployment | No |
| `@quant-risk-modeler` | `.claude/agents/stream-quant/quant-risk-modeler.md` | Crypto risk (EVT VaR, liquidation cascade scoring) | Yes |

---

## Skills Registry (16 Quant-Specific Skills)

### Research Skills
| Skill | Invoke | Purpose |
|-------|--------|---------|
| `/quant-research-methodology` | Research tasks | Medallion-style research doctrine |
| `/quant-hypothesis-generation` | Idea formulation | Hypothesis card format & validation |
| `/quant-pattern-knowledge` | Pattern learning | Read/write pattern files correctly |

### Conversion Skills
| Skill | Invoke | Purpose |
|-------|--------|---------|
| `/quant-pinescript-patterns` | Pine conversion | Pine→Python translation patterns |
| `/quant-indicator-testing` | Test generation | Pytest patterns for indicators |

### Backtesting Skills
| Skill | Invoke | Purpose |
|-------|--------|---------|
| `/quant-walk-forward-validation` | WFO setup | Walk-forward implementation |
| `/quant-overfitting-detection` | Red flag check | Overfitting pattern detection |
| `/quant-cost-modeling` | Cost validation | Commission + slippage modeling |
| `/quant-metrics-calculation` | Metrics | Sharpe, DD, win rate calculations |

### Optimization Skills
| Skill | Invoke | Purpose |
|-------|--------|---------|
| `/quant-parameter-optimization` | Grid search | Coarse grid methodology |
| `/quant-robustness-testing` | Perturbation | ±20% parameter stability |
| `/quant-base-hit-analysis` | Loss MFE | Base Hit cash exit methodology |
| `/quant-prop-firm-compliance` | Firm testing | All 14 firms' rules |

### Orchestration Skills
| Skill | Invoke | Purpose |
|-------|--------|---------|
| `/quant-session-management` | Session lifecycle | Start → Execute → Distill → Complete |
| `/quant-queue-coordination` | Queue IPC | Inter-worker file coordination |
| `/quant-artifact-routing` | Output routing | Organize artifacts correctly |

---

## Research Doctrine ("If I wanted my own Medallion")

These rules are **non-negotiable**. They prevent backtest hallucinations:

### 1. Hypothesis-First
Every strategy MUST have a written hypothesis:
- "Why should this edge exist?"
- Who is on the other side of the trade?
- What market inefficiency are we exploiting?

### 2. Reproducibility
Every run produces a deterministic artifact set:
- Strategy code
- Parameters
- Dataset window (bar count, not dates)
- Costs model (commissions + slippage)
- Backtest config
- Results JSON

### 3. Anti-Overfitting Gates (Hard Rejects)

| Signal | Action | Reason |
|--------|--------|--------|
| Sharpe > 3.0 | REJECT | Fraud check — curve-fitted |
| Win rate > 80% | REJECT | Bias check — look-ahead suspected |
| Trades < 100 | REJECT | Insufficient sample |
| OOS decay > 50% | REJECT | Doesn't generalize |
| No losing months | REJECT | Suspiciously perfect |

### 4. Out-of-Sample Discipline
- Walk-forward splits ONLY (no random shuffles)
- Track in-sample vs OOS decay
- Decay > 30% = "under_review", > 50% = REJECT

### 5. Costs Always On (Profile-Dispatched)
**Futures**: Commissions $2.50/contract/side + slippage 0.5 ticks minimum
**Crypto CEX**: Maker 0.02-0.04% + Taker 0.04-0.06% + funding rate (8h) + slippage 0.05%
**Crypto DEX**: Maker 0.02% + Taker 0.05% + gas (variable) + slippage 0.1%
- **Never backtest without costs**

### 6. Robustness Checks (for "good/" promotion)
- Parameter sensitivity (no knife-edge optima)
- ±20% perturbation must maintain profitability
- Multiple contiguous time windows

### 7. Base Hit Inside Every Strategy
- Run Base Hit optimization (loss MFE cash exit)
- Store `baseHitConfig` in every strategy artifact
- This is MANDATORY for all strategies

---

## Queue Protocol (File-Based IPC)

### Directory Structure
```
stream-quant/queues/
├── hypotheses/              # Researcher → Backtester
│   └── hyp-{timestamp}.json
├── to-convert/              # Researcher → Converter
│   └── conv-{timestamp}.json
├── to-backtest/             # Converter → Backtester
│   └── bt-{timestamp}.json
└── to-optimize/             # Backtester → Optimizer
    └── opt-{timestamp}.json
```

### Queue Item Schema
```json
{
  "id": "hyp-2026-01-26-001",
  "created_at": "2026-01-26T08:30:00Z",
  "created_by": "researcher-pane-0",
  "priority": "high|medium|low",
  "status": "pending|in_progress|completed|failed",
  "claimed_by": null,
  "payload": { /* task-specific data */ }
}
```

### Atomic Operations
- **Push**: Write to temp file, then `mv` to queue dir
- **Claim**: Rename with `.claimed-{pane}` suffix
- **Complete**: Move to `completed/` archive
- **Fail**: Move to `failed/` with error log

### Priority Rules
1. `high` items processed first
2. FIFO within same priority
3. Unclaimed items > 10min get priority boost

---

## Session Lifecycle Protocol

### 1. SESSION_START
```
SESSION_START: {worker-type}-{timestamp}
PATTERN_FILES_READ: what-works.md, what-fails.md
QUEUE_DEPTH: hypotheses=5, to-convert=3, to-backtest=2, to-optimize=1
```

### 2. Execution Loop
```
TASK_START: {task-id}
SUBAGENT_SPAWN: @quant-{name}
SUBAGENT_COMPLETE: @quant-{name}
FILES_CREATED: 3
TASK_COMPLETE: {task-id}
```

### 3. SESSION_DISTILL (Mandatory)
```
# At session end, ALWAYS invoke:
@sigma-distiller: Analyze this session and update pattern files

Expected markers:
DISTILLATION_COMPLETE
PATTERNS_UPDATED: what-works.md (+2 entries)
```

### 4. SESSION_COMPLETE
```
SESSION_COMPLETE: {worker-type}-{timestamp}
DURATION: 45m
TASKS_COMPLETED: 8
STRATEGIES_PRODUCED: 2
HYPOTHESES_QUEUED: 5
```

---

## Strategy Pass Criteria

| Metric | Pass | Good | Reject |
|--------|------|------|--------|
| Sharpe Ratio | > 1.0 | > 1.5 | < 1.0 or > 3.0 |
| Max Drawdown | < 20% | < 15% | > 30% |
| Trade Count | > 100 | > 200 | < 30 |
| OOS Decay | < 30% | < 20% | > 50% |
| Win Rate | < 80% | 50-70% | > 80% (bias) |

---

## Compliance Validation

### Futures: Prop Firm Integration

Futures strategies reaching optimizer MUST be tested against all 14 prop firms:

| Firm | Daily Loss | Trailing DD | Consistency | Platform |
|------|------------|-------------|-------------|----------|
| TakeProfitTrader | None | 8% EOD | 50% max single day | Tradovate |
| TopStep | $1-3K | 3% (reduced) | 50% max single day | ProjectX |
| Apex (3.0) | None | 4% intraday | 30% windfall rule | Tradovate |
| Tradeify | $1.25-3.75K | Varies | 35% standard | Tradovate |
| Bulenox | $1.5-2K | $2.5-3K | Varies | Tradovate |
| Earn2Trade | $2K | $2.5K | 50% | Tradovate |
| MyFundedFX | $2K | $3K | 50% | Tradovate |
| The Funded Trader | Varies | Varies | 50% | Tradovate |
| BluSky | Varies | Varies | Varies | Tradovate |
| Leeloo | $1.5K | 6% | 50% | Tradovate |
| OneUp Trader | $1.5K | 6% | 50% | Tradovate |
| FTMO | N/A | N/A | N/A | Not supported (forex) |
| Funded Trading Plus | Varies | Varies | Varies | Tradovate |
| True Trader | Varies | Varies | Varies | Tradovate |

**Deployment Ready**: Strategy passes >= 3 firms → `output/strategies/prop_firm_ready/`

### Crypto: Exchange Compliance

Crypto strategies MUST pass exchange validation before deployment:

| Exchange | Max Leverage | Rate Limit | Settlement | Key Gotcha |
|----------|-------------|-----------|------------|------------|
| Binance | Tier-based (125x→10x) | 1200 req/min | Continuous | ADL risk, IP-based limits |
| Bybit | 100x | 120 req/min | 00/08/16 UTC | Order fails during settlement |
| OKX | 100x (isolated) | 60 req/2s | Continuous | Margin mode switching |
| Hyperliquid | 50x | 1200 req/min | Continuous | Gas spikes, on-chain delay |

**Exchange Ready**: Strategy passes exchange validator → `output/strategies/exchange_ready/`

See `patterns/exchange-gotchas.md` for detailed per-exchange issues.

---

## MCP Tools Available

### Research Tools (Priority Order)

| Priority | Tool | Use When |
|----------|------|----------|
| 1 | `mcp_Ref_ref_search_documentation` | Official docs, API refs |
| 2 | `mcp_exa_get_code_context_exa` | Code examples, implementations |
| 3 | `mcp_exa_web_search_exa` | Real-time web search |
| 4 | `mcp_exa_crawling_exa` | Extract from specific URLs |
| 5 | `mcp_perplexity-ask_perplexity_ask` | Complex research queries |

### Research Scope (Medallion-Style Learning)
- **People**: Jim Simons, Lo/De Prado, Chan, Aronson, Clenow
- **Methods**: Feature engineering, overfitting control, walk-forward, PBO, meta-labeling
- **ML/RL**: Only with proper validation discipline

---

## Directory Structure

```
stream-quant/
├── CLAUDE.md                      # ← YOU ARE HERE
├── config.json                    # Team configuration
├── prompts/                       # Worker mission prompts
│   ├── researcher.md
│   ├── converter.md
│   ├── backtester.md
│   └── optimizer.md
├── queues/                        # Inter-worker IPC
│   ├── hypotheses/
│   ├── to-convert/
│   ├── to-backtest/
│   └── to-optimize/
├── patterns/                      # Cross-session learning
│   ├── what-works.md              # Validated futures approaches
│   ├── what-fails.md              # Documented futures failures
│   ├── indicator-combos.md        # Futures indicator combos
│   ├── prop-firm-gotchas.md       # Prop firm quirks
│   ├── crypto-what-works.md       # Validated crypto approaches
│   ├── crypto-what-fails.md       # Documented crypto failures
│   ├── exchange-gotchas.md        # Per-exchange compliance issues
│   └── indicator-combos-crypto.md # Crypto indicator combos
├── profiles/                      # Market profile configs
├── data/                          # Sample & reference data
│   └── samples/                   # Sample OHLCV CSVs
├── seed/                          # Queue priming data
│   ├── hypotheses/
│   │   └── crypto/                # Crypto seed hypotheses
│   └── to-convert/
├── output/                        # Results & artifacts
│   ├── strategies/
│   │   ├── good/
│   │   ├── under_review/
│   │   ├── rejected/
│   │   └── prop_firm_ready/
│   ├── indicators/
│   │   ├── converted/
│   │   └── created/
│   ├── combinations/
│   ├── backtests/
│   ├── hypotheses/
│   └── research-logs/
├── session-summaries/             # Per-pane summaries
│   ├── pane-0.md
│   ├── pane-1.md
│   ├── pane-2.md
│   └── pane-3.md
├── checkpoints/                   # Crash recovery
├── claimed-ideas.json             # Global idea registry
└── cost-tracker.json              # API spend tracking
```

---

## Completion Markers

### Task Completion
```
QUANT_TASK_COMPLETE: <task-id>
FILES_CREATED: <count>
ARTIFACTS: <list>
```

### Task Blocked
```
QUANT_TASK_BLOCKED: <task-id>
REASON: <explain why>
NEEDS: <what's required>
```

### Sub-Agent Completion
```
SUBAGENT_COMPLETE: @quant-{name}
DURATION: <time>
OUTPUT: <summary>
```

### Session Completion
```
SESSION_COMPLETE: {worker-type}-{timestamp}
DISTILLATION_COMPLETE
PATTERNS_UPDATED: {list}
```

---

## Quick Start

1. **Read pattern files first** (via `@quant-pattern-learner`)
2. **Check your queue** for pending items
3. **Spawn appropriate sub-agents** for the task
4. **Validate against criteria** before completion
5. **Push results** to correct output/queue
6. **Invoke @sigma-distiller** at session end
7. **Output SESSION_COMPLETE** marker

**Begin your autonomous research loop now.**

---

## Market Profiles (Multi-Market Expansion)

Stream-Quant now supports three market types through a profile system. The active profile controls data sources, cost models, compliance validators, and symbol discovery.

### Supported Market Types

| Market | Data Provider | Cost Model | Compliance | Symbols |
|--------|--------------|------------|------------|---------|
| **Futures** | Databento (bars=N, live) | Fixed per-contract ($2.50/side + tick slippage) | PropFirmValidator (14 firms) | ES, NQ, YM, GC, CL |
| **Crypto CEX** | CCXT (Binance, Bybit, OKX) | Percentage (maker/taker + withdrawal) | ExchangeRiskValidator (leverage tiers) | BTC, ETH, SOL, etc. perps/spot |
| **Crypto DEX** | Hyperliquid SDK | Percentage (maker/taker + gas) | ExchangeRiskValidator (max leverage) | BTC, ETH perps |

### Profile System

Profiles live in `stream-quant/profiles/` and are selected via `stream-quant/active-profile.json`:

```
stream-quant/profiles/
  futures-default.json        # Databento + prop firm rules (existing behavior)
  crypto-cex-binance.json     # CCXT Binance + exchange rules
  crypto-cex-bybit.json       # CCXT Bybit + exchange rules
  crypto-cex-okx.json         # CCXT OKX + exchange rules
  crypto-dex-hyperliquid.json # Hyperliquid SDK + DEX rules
```

```json
// active-profile.json
{
  "active": "futures-default",
  "path": "profiles/futures-default.json"
}
```

### How Costs Are Loaded (Not Hardcoded)

Costs are dispatched from the active profile, never hardcoded:

```python
from stream_quant.profiles import get_active_profile, get_instrument_spec

profile = get_active_profile()
spec = get_instrument_spec(profile, symbol)

# spec is either ContractSpec (futures) or CryptoPerpSpec/CryptoSpotSpec (crypto)
# Cost calculation uses the spec's methods, not hardcoded values
cost = spec.calculate_round_trip_cost(quantity)
```

For futures: fixed commissions ($2.50/side) + tick-based slippage.
For crypto: percentage-based fees (maker 0.02%, taker 0.05%) + gas (DEX only).

### How Compliance Is Profile-Dispatched

```python
from stream_quant.profiles import get_validator

validator = get_validator(profile)

# Futures profile -> PropFirmValidator (checks 14 prop firms)
# Crypto profile -> ExchangeRiskValidator (checks leverage tiers, liquidation buffers)
result = validator.validate(equity_curve, daily_pnl)
```

Futures strategies validate against prop firm rules (daily loss, trailing DD, consistency).
Crypto strategies validate against exchange rules (max leverage per tier, margin requirements, liquidation buffer %).

### Crypto Research Doctrine

**Sources (Priority Order)**:
1. **CryptoQuant** -- On-chain metrics, exchange flows, miner data
2. **Glassnode** -- SOPR, MVRV, NUPL, entity-adjusted metrics
3. **DeFi Llama** -- TVL, protocol yields, DEX volume
4. **MoonDev** -- Whale tracking, smart money flow
5. **Coinglass** -- Funding rates, open interest, liquidation maps

**Edge Types for Crypto**:
- Funding rate mean-reversion (8h funding > 0.1% = short bias)
- Liquidation cascade front-running (OI divergence from price)
- Cross-exchange basis arbitrage (CEX vs DEX price divergence)
- On-chain flow signals (exchange inflow/outflow spikes)
- Market making spread capture (Avellaneda-Stoikov on perps)

### Symbol Discovery (Dynamic)

Futures: Fixed universe (ES, NQ, YM, GC, CL) via Databento.

Crypto: Dynamic discovery by volume and open interest:
```python
# Discover top symbols by 24h volume on active exchange
symbols = discover_symbols(profile, min_volume_usd=50_000_000, min_oi_usd=10_000_000)
# Returns: ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", ...]
```

### Key Rules for Multi-Market

1. **Never hardcode data source** -- always dispatch from profile
2. **Never hardcode cost model** -- use `get_instrument_spec(profile, symbol)`
3. **Never hardcode compliance rules** -- use `get_validator(profile)`
4. **All existing futures pipeline code remains unchanged** -- crypto is additive
5. **Same quality gates apply** -- Sharpe > 1.0, 100+ trades, OOS decay < 30%
6. **Walk-forward is mandatory for crypto too** -- no random shuffles on 24/7 data
