# Architecture

This document describes the technical architecture of Sigma-Quant Stream:
how the Go CLI orchestrates a swarm of Claude Code agents, how workers
communicate through file-based queues, and how the Bubble Tea TUI renders
real-time dashboards.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Diagram](#component-diagram)
3. [Go Package Structure](#go-package-structure)
4. [Command Tree (Cobra)](#command-tree-cobra)
5. [Bubble Tea TUI](#bubble-tea-tui)
6. [Agent Orchestration](#agent-orchestration)
7. [File-Based Queue IPC](#file-based-queue-ipc)
8. [Worker Lifecycle (Ralph Loop)](#worker-lifecycle-ralph-loop)
9. [Agent and Skill System](#agent-and-skill-system)
10. [Market Profile System](#market-profile-system)
11. [Configuration](#configuration)
12. [Python Integration](#python-integration)
13. [Extension Points](#extension-points)

---

## System Overview

Sigma-Quant Stream is a Go CLI application that manages an autonomous swarm of
Claude Code AI agents. The system has three layers:

1. **CLI Layer** -- A Cobra-based command tree that handles user commands
   (`start`, `stop`, `status`, `health`, etc.) and launches Bubble Tea TUI
   views for interactive experiences.

2. **Orchestration Layer** -- Manages tmux sessions, spawns Claude Code
   processes in panes, implements the Ralph loop (infinite restart), and
   monitors agent health.

3. **Execution Layer** -- The Claude Code agents themselves, running in tmux
   panes, reading mission prompts, processing queue items, and writing output
   artifacts. Python scripts handle backtesting, data downloading, and
   exchange adapters.

```
User
  |
  v
sigma-quant binary (Go)
  |
  +-- Cobra commands (init, start, stop, status, health, ...)
  |
  +-- Bubble Tea TUI (dashboard, onboarding wizard, strategy browser)
  |
  +-- Agent Manager (tmux spawn, Ralph loop, health polling)
  |
  v
tmux session (4 panes)
  |
  +-- Pane 0: Researcher (Claude Code + 8 sub-agents)
  +-- Pane 1: Converter  (Claude Code + 7 sub-agents)
  +-- Pane 2: Backtester (Claude Code + 10 sub-agents)
  +-- Pane 3: Optimizer  (Claude Code + 10 sub-agents)
  |
  v
File-based queues (hypotheses/ -> to-convert/ -> to-backtest/ -> to-optimize/)
  |
  v
Output artifacts (output/strategies/good/, output/strategies/prop_firm_ready/)
```

---

## Component Diagram

```
+----------------------------------------------------------------------+
|                       sigma-quant binary                              |
+----------------------------------------------------------------------+
|                                                                      |
|  +-----------------+  +-----------------+  +----------------------+  |
|  | Cobra Commands  |  | Bubble Tea TUI  |  | Viper Config         |  |
|  |                 |  |                 |  |                      |  |
|  | init            |  | Dashboard Model |  | config.json          |  |
|  | start        ----->| Onboarding   ----->| .env                 |  |
|  | stop            |  | Tutorial Model  |  | profiles/*.json      |  |
|  | status          |  | Strategy Model  |  | CLI flags override   |  |
|  | health          |  | Health Model    |  |                      |  |
|  | data *          |  |                 |  +----------------------+  |
|  | strategies      |  +--------+--------+                            |
|  | deploy          |           |                                     |
|  | tutorial        |           v                                     |
|  | config *        |  +-----------------+  +----------------------+  |
|  | setup-claude    |  | Lipgloss Theme  |  | Agent Orchestration  |  |
|  +-----------------+  | (Sharian Dark)  |  |                      |  |
|                       +-----------------+  | tmux spawn/kill      |  |
|                                            | Ralph loop manager   |  |
|                                            | health poll (tick)   |  |
|                                            | log capture          |  |
|                                            +----------+-----------+  |
|                                                       |              |
+-------------------------------------------------------+--------------+
                                                        |
                          +-----------------------------v--------------+
                          |        External Processes                   |
                          |                                            |
                          |  tmux session: sigma-quant (4 panes)       |
                          |  claude --dangerously-skip-permissions      |
                          |  python lib/backtest_runner.py              |
                          |  python lib/crypto/*.py                    |
                          |  python scripts/download-data.py           |
                          +--------------------------------------------+
```

---

## Go Package Structure

```
sigma-quant-stream/
  cmd/
    sigma-quant/
      main.go                # Entry point: calls internal/cmd.Execute()

  internal/
    cmd/                     # Cobra command definitions
      root.go                # Root command, global flags, Viper init
      init.go                # sigma-quant init (onboarding wizard)
      start.go               # sigma-quant start [worker]
      stop.go                # sigma-quant stop [worker]
      status.go              # sigma-quant status [--watch]
      health.go              # sigma-quant health [--fix]
      strategies.go          # sigma-quant strategies [-g grade]
      deploy.go              # sigma-quant deploy
      tutorial.go            # sigma-quant tutorial
      data.go                # sigma-quant data {download,status}
      config_cmd.go          # sigma-quant config {show,profiles,set}
      setup_claude.go        # sigma-quant setup-claude
      version.go             # sigma-quant --version

    tui/                     # Bubble Tea TUI layer
      models/                # Bubble Tea Model implementations
        setup_claude.go      # Setup Claude wizard model
        strategies.go        # Strategy browser model
      views/                 # View rendering functions
        setup_claude.go      # Setup Claude view
        strategy_browser.go  # Strategy browser view
      components/            # Reusable UI components
        header.go            # App header with logo
        footer.go            # Keybinding hints
        worker_panel.go      # Per-worker status panel
        queue_bar.go         # Queue depth progress bar
        strategy_card.go     # Strategy summary card
        metric_gauge.go      # Numeric metric with label
        log_stream.go        # Scrolling log viewer
        tab_bar.go           # Tab navigation
        progress_step.go     # Step-by-step progress
        cost_tracker.go      # API cost display
        confirm_dialog.go    # Yes/No confirmation
        helpers.go           # Shared rendering helpers
      styles/                # Lipgloss theme layer
        theme.go             # Master theme definition
        colors.go            # Color palette (Sharian dark)
        borders.go           # Border styles
        text.go              # Typography styles
        logo.go              # ASCII art logo

    agent/                   # Agent orchestration
      manager.go             # Worker lifecycle management
      tmux.go                # tmux session/pane operations
      monitor.go             # Health polling and log capture
      prompts.go             # Prompt file loading and injection

    queue/                   # File-based queue system
      queue.go               # Core queue operations (push, claim, complete)
      types.go               # QueueItem, QueueStats types
      watcher.go             # fsnotify-based queue watcher
      pipeline.go            # Pipeline orchestration (queue chaining)

    config/                  # Configuration management
      (Viper-based config loading, profile resolution)

    health/                  # Health check logic
      (Dependency verification, auto-fix)

    python/                  # Python subprocess integration
      (Backtest runner invocation, data download delegation)
```

### Package Dependency Flow

```
cmd/ --depends-on--> tui/, agent/, queue/, config/, health/, python/
tui/ --depends-on--> styles/, components/, models/, views/
agent/ --depends-on--> config/, queue/
queue/ --depends-on--> config/
```

No circular dependencies. Each package has a clear responsibility and
communicates through well-defined interfaces.

---

## Command Tree (Cobra)

The `sigma-quant` binary uses [Cobra](https://github.com/spf13/cobra) for
command routing. Every command is defined in `internal/cmd/`.

```
sigma-quant
  |-- init                  Launch interactive onboarding wizard
  |-- start [worker]        Start all workers or a specific one
  |-- stop [worker]         Stop all workers or a specific one
  |-- status [--watch]      Show status (static or live TUI)
  |-- health [--fix]        Run dependency health checks
  |-- strategies [-g grade] List discovered strategies
  |-- deploy                Export strategy to Freqtrade
  |-- tutorial              Guided 6-step walkthrough
  |-- data
  |     |-- download        Download market data
  |     +-- status          Show data coverage
  |-- config
  |     |-- show            Print current config.json
  |     |-- profiles        List available market profiles
  |     +-- set <key> <val> Update a config value
  |-- setup-claude          Configure Claude Code settings
  +-- version               Print version information
```

### Flag Precedence

Viper handles configuration with the following precedence (highest wins):

1. CLI flags (`--panes 2`)
2. Environment variables (`SIGMA_QUANT_PANES=2`)
3. `config.json` values
4. Default values in code

---

## Bubble Tea TUI

The TUI is built with [Bubble Tea](https://github.com/charmbracelet/bubbletea),
which uses the Elm architecture: **Init**, **Update**, **View**.

### Elm Architecture

```
            +---> View() renders the UI as a string
            |
State ------+
            |
            +---> Update(msg) handles input, returns new state
                       ^
                       |
                  Messages (key press, tick, resize, custom)
```

Every TUI screen is a Bubble Tea `Model` that implements three methods:

```go
type Model interface {
    Init() tea.Cmd            // Initial command (start ticks, load data)
    Update(tea.Msg) (Model, tea.Cmd)  // Handle messages, return new state
    View() string             // Render current state to string
}
```

### Key Models

| Model | Location | Purpose |
|-------|----------|---------|
| Dashboard | `internal/tui/models/` | Live status with worker panels, queue bars, cost tracker |
| Onboarding | `internal/tui/models/` | Huh-based form wizard for `sigma-quant init` |
| Strategy Browser | `internal/tui/models/strategies.go` | Filterable strategy list with detail view |
| Setup Claude | `internal/tui/models/setup_claude.go` | Claude Code configuration wizard |

### Component Hierarchy (Dashboard Example)

```
Dashboard Model
  +-- Header Component (logo, version, session timer)
  +-- Tab Bar Component (Workers | Queues | Strategies | Costs)
  +-- [active tab content]
  |     +-- Worker Panel x4 (status, session count, last output)
  |     +-- Queue Bar x4 (depth, throughput, oldest item)
  |     +-- Strategy Card list (grade, Sharpe, DD, trades)
  |     +-- Cost Tracker (cumulative spend, burn rate)
  +-- Footer Component (keybinding hints)
```

### Tick-Based Updates

The dashboard uses `tea.Tick` for periodic state refresh:

```go
func tickCmd() tea.Cmd {
    return tea.Tick(2*time.Second, func(t time.Time) tea.Msg {
        return tickMsg(t)
    })
}
```

Every 2 seconds, the dashboard:

1. Polls tmux for pane status
2. Reads queue directories for depth counts
3. Scans output directories for strategy counts
4. Reads `cost-tracker.json` for spend data
5. Re-renders the View

### Styling (Lipgloss)

All styles are defined in `internal/tui/styles/` using
[Lipgloss](https://github.com/charmbracelet/lipgloss). The theme uses a
"Sharian dark" cyberpunk aesthetic.

```go
// internal/tui/styles/colors.go
var (
    Primary    = lipgloss.Color("#7C3AED")  // Purple
    Secondary  = lipgloss.Color("#06B6D4")  // Cyan
    Success    = lipgloss.Color("#22C55E")  // Green
    Warning    = lipgloss.Color("#F59E0B")  // Amber
    Error      = lipgloss.Color("#EF4444")  // Red
    Surface    = lipgloss.Color("#1E1B2E")  // Dark purple-gray
    Background = lipgloss.Color("#0F0D1A")  // Near-black
)
```

Components compose styles from the theme, never hardcoding colors directly.

---

## Agent Orchestration

The `internal/agent/` package manages the lifecycle of Claude Code processes
running in tmux panes.

### tmux Operations (`tmux.go`)

```go
// CreateSession creates the tmux session with N panes
func CreateSession(name string, panes int) error

// SendCommand sends a shell command to a specific pane
func SendCommand(session string, pane int, command string) error

// GetPaneContent reads the current visible content of a pane
func GetPaneContent(session string, pane int) (string, error)

// KillSession destroys the tmux session
func KillSession(name string) error
```

tmux operations are executed via `os/exec` calls to the `tmux` binary. The Go
process does not embed tmux -- it manages it as an external process.

### Worker Manager (`manager.go`)

The manager tracks worker state and coordinates startup/shutdown:

```go
type WorkerManager struct {
    Session   string
    Workers   []Worker
    Config    *config.Config
    Queue     *queue.Pipeline
}

type Worker struct {
    Type      string  // "researcher", "converter", "backtester", "optimizer"
    Pane      int     // tmux pane index
    Status    string  // "running", "idle", "restarting", "stopped"
    Sessions  int     // Number of Ralph loop iterations
    StartedAt time.Time
}
```

### Health Monitor (`monitor.go`)

The monitor runs as a goroutine, polling pane content at regular intervals to
detect:

- Session completion markers (`SESSION_COMPLETE`)
- Error states (repeated failures, stuck loops)
- Resource warnings (API budget approaching cap)

When a session completes, the monitor triggers a Ralph loop restart for that
pane.

---

## File-Based Queue IPC

Workers communicate through file-based queues. This design was chosen over
Redis, SQLite, or other IPC mechanisms because:

1. Claude Code agents can read and write files natively
2. No external service dependencies
3. Atomic operations via `rename()` system call
4. Human-readable for debugging
5. Survives process crashes (files persist on disk)

### Queue Directory Layout

```
queues/
  hypotheses/           # Researcher --> Backtester
    hyp-1706234800.json
    hyp-1706234801.json
  to-convert/           # Researcher --> Converter
    conv-1706234800.json
  to-backtest/          # Converter --> Backtester
    bt-1706234800.json
  to-optimize/          # Backtester --> Optimizer
    opt-1706234800.json
```

### Queue Item Schema

Every queue item is a JSON file with a standard envelope:

```json
{
  "id": "hyp-2026-01-26-001",
  "created_at": "2026-01-26T08:30:00Z",
  "created_by": "researcher-pane-0",
  "priority": "high",
  "status": "pending",
  "claimed_by": null,
  "payload": {
    "title": "RSI Divergence on ES 5min",
    "hypothesis": "Bullish divergence predicts short-term reversal...",
    "markets": ["ES", "NQ"],
    "timeframes": ["5m", "15m"]
  }
}
```

### Atomic Operations

The queue system uses atomic file operations to prevent race conditions between
concurrent workers:

| Operation | Implementation | Guarantees |
|-----------|---------------|------------|
| **Push** | Write to temp file, then `os.Rename()` into queue dir | Atomic appearance |
| **Claim** | `os.Rename()` with `.claimed-{pane}` suffix | Only one claimer wins |
| **Complete** | Move to `completed/` subdirectory | Item removed from active queue |
| **Fail** | Move to `failed/` with error log appended | Failure preserved for debugging |

### Priority Handling

```
1. High priority items processed first
2. Within same priority, FIFO order (by timestamp in filename)
3. Items unclaimed for > 10 minutes get automatic priority boost
```

### Pipeline Orchestration (`pipeline.go`)

The `Pipeline` struct chains queues together and tracks flow:

```
Researcher --push--> hypotheses/ --claim--> Backtester
Researcher --push--> to-convert/ --claim--> Converter
Converter  --push--> to-backtest/ --claim--> Backtester
Backtester --push--> to-optimize/ --claim--> Optimizer
Optimizer  --push--> output/strategies/
```

### Queue Watcher (`watcher.go`)

Uses `fsnotify` to watch queue directories for new files. When a new item
appears, the watcher emits a Bubble Tea message to update the dashboard in
real time, without polling.

---

## Worker Lifecycle (Ralph Loop)

The Ralph loop is the infinite restart mechanism that keeps workers productive
across Claude Code session boundaries.

### Lifecycle

```
                    +---> [1] Load mission prompt
                    |
                    +---> [2] Inject last session summary
                    |
[Start] ---> [Ralph Loop] ---> [3] Inject pattern knowledge
                    |
                    +---> [4] Spawn Claude Code in pane
                    |
                    +---> [5] Monitor for SESSION_COMPLETE
                    |
                    +---> [6] Capture session summary
                    |
                    +---> [7] Restart from [1]
```

### Prompt Assembly

Before each Claude Code session, the manager assembles a context payload:

```
prompts/{worker}.md           # Static mission prompt
+
session-summaries/pane-{N}.md # Previous session summary
+
patterns/what-works.md        # Cross-session knowledge (futures)
patterns/what-fails.md        # Cross-session knowledge (futures)
patterns/crypto-what-works.md # Cross-session knowledge (crypto)
+
Queue state summary           # What is pending in each queue
```

This payload is written to a temporary file and passed to Claude Code as the
initial prompt.

### Session Timeout

Sessions are time-bounded by the `sessionTimeout` config value (default: 1800
seconds for research mode, 3600 for production). When the timeout hits, the
current Claude Code process is terminated and the Ralph loop restarts.

### Crash Recovery

If a Claude Code process crashes (non-zero exit):

1. The crash is logged to `checkpoints/`
2. A consecutive failure counter increments
3. After 3 consecutive failures (`maxConsecutiveFailures`), the pane enters a
   cooldown period (60 seconds) before retrying
4. Cooldown resets on any successful session

---

## Agent and Skill System

Each worker delegates to specialized sub-agents using Claude Code's Task tool.
Sub-agents are defined as markdown files in `.claude/agents/`.

### Agent Registry

```
.claude/agents/
  quant-idea-hunter.md        # Researcher: search web for trading ideas
  quant-paper-analyzer.md     # Researcher: parse academic papers
  quant-tv-scraper.md         # Researcher: scrape TradingView indicators
  quant-hypothesis-writer.md  # Researcher: formulate testable hypotheses
  quant-combo-finder.md       # Researcher: find indicator combinations
  quant-edge-validator.md     # Researcher: validate economic rationale
  quant-pattern-learner.md    # Researcher: read pattern knowledge base
  quant-queue-pusher.md       # Researcher: push items to queues
  quant-pine-parser.md        # Converter: parse PineScript
  quant-pandas-adapter.md     # Converter: map to pandas-ta
  quant-class-wrapper.md      # Converter: generate Python class
  quant-test-writer.md        # Converter: generate pytest tests
  quant-walk-forward.md       # Backtester: walk-forward validation
  quant-overfit-checker.md    # Backtester: detect curve-fitting
  quant-coarse-grid.md        # Optimizer: grid search
  quant-perturb-tester.md     # Optimizer: parameter perturbation
  quant-prop-firm-validator.md # Optimizer: prop firm compliance
  ... (44 agents total)
```

### Skills

Skills provide domain knowledge that agents invoke during execution. They are
defined in `.claude/skills/` and referenced by agents in their frontmatter.

```
.claude/skills/
  quant-research-methodology/   # How to find edges
  quant-hypothesis-generation/  # Hypothesis card format
  quant-pattern-knowledge/      # Reading/writing pattern files
  quant-pinescript-patterns/    # Pine to Python translation
  quant-walk-forward-validation/ # WFO implementation
  quant-overfitting-detection/  # Red flag patterns
  quant-cost-modeling/          # Commission + slippage
  quant-prop-firm-compliance/   # 14 firms' rules
  quant-parameter-optimization/ # Grid search methodology
  quant-robustness-testing/     # Perturbation testing
  quant-base-hit-analysis/      # Loss MFE cash exit
  quant-queue-coordination/     # File-based IPC protocol
  quant-artifact-routing/       # Output organization
  quant-session-management/     # Session lifecycle
  quant-metrics-calculation/    # Sharpe, DD, win rate
  quant-indicator-testing/      # Pytest patterns for indicators
```

### Invocation Pattern

Workers delegate to sub-agents in a specific order:

```
1. @quant-pattern-learner    (always first -- load context)
2. [parallel sub-agents]     (task-specific work)
3. @quant-queue-pusher       (always last -- atomic output)
```

---

## Market Profile System

Market profiles control data sources, cost models, compliance rules, and symbol
discovery. Profiles live in `profiles/` and are selected via `config.json`.

### Available Profiles

| Profile | File | Data Source | Cost Model | Compliance |
|---------|------|-----------|------------|------------|
| Futures | `profiles/futures.json` | Databento | $2.50/contract/side + tick slippage | 14 prop firms |
| Crypto CEX | `profiles/crypto-cex.json` | CCXT | maker/taker % + funding + slippage | Exchange leverage tiers |
| Crypto DEX | `profiles/crypto-dex-hyperliquid.json` | Hyperliquid API | maker/taker % + gas + slippage | On-chain limits |

### Profile Dispatch

All market-specific behavior is dispatched through the active profile. Nothing
is hardcoded:

- **Data source:** Futures use Databento bars; crypto uses CCXT OHLCV or Hyperliquid API
- **Cost model:** Futures use fixed $/contract; crypto uses percentage-based fees + funding
- **Compliance:** Futures validate against prop firms; crypto validates against exchange rules
- **Risk margins:** Futures use 1.5x buffer; crypto uses 2-3x buffer (fat tails)
- **Pattern files:** Futures read `what-works.md`; crypto reads `crypto-what-works.md`

### Switching Profiles

```bash
sigma-quant config set activeProfile profiles/crypto-cex.json
```

Or use the interactive wizard:

```bash
sigma-quant init
```

---

## Configuration

### config.json

The main configuration file at the project root. Managed by Viper.

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
  },
  "recovery": {
    "maxConsecutiveFailures": 3,
    "autoResume": true
  }
}
```

### .env

Environment variables for API keys and secrets:

```bash
ANTHROPIC_API_KEY=sk-ant-...
DATABENTO_API_KEY=db-...
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

### Profile Files

Market-specific configuration in `profiles/*.json`. Each profile defines:

- `marketType`: `"futures"`, `"crypto-cex"`, or `"crypto-dex"`
- `dataSource`: Provider and connection details
- `instruments`: Symbol definitions with tick sizes, lot sizes, margin requirements
- `costModel`: Commission, slippage, and fee structure
- `compliance`: Rules and thresholds for validation

### CLI Flag Overrides

Any config value can be overridden via CLI flags:

```bash
sigma-quant start --panes 2 --mode production
```

---

## Python Integration

The Go binary delegates compute-heavy tasks to Python scripts via
`os/exec.Command`. The `internal/python/` package handles this integration.

### Delegated Tasks

| Task | Python Script | Called By |
|------|--------------|-----------|
| Backtesting | `lib/backtest_runner.py` | Backtester agent |
| Data download | `scripts/download-data.py` | `sigma-quant data download` |
| Health check | `scripts/health-check.py` | `sigma-quant health` |
| Prop firm validation | `scripts/prop-firm-validator.py` | Optimizer agent |
| Freqtrade deploy | `scripts/freqtrade-deploy.sh` | `sigma-quant deploy` |
| Cost tracking | `scripts/cost-tracker.py` | Agent orchestration |
| Crypto exchange adapters | `lib/crypto/exchange_adapters.py` | Crypto agents |
| Crypto risk modeling | `lib/crypto/risk_modeler.py` | Crypto agents |

### Python Environment

The Go binary expects `python3` to be available on `$PATH`. No virtual
environment is created automatically. Users should install Python dependencies
before running:

```bash
pip install pandas numpy pandas-ta ccxt
```

---

## Extension Points

### Adding a New Market

1. Create a new profile in `profiles/new-market.json`
2. Define instruments, cost model, and compliance rules
3. Add a data adapter in `lib/` if the data source is new
4. Add pattern files in `patterns/` (e.g., `new-market-what-works.md`)
5. Add seed hypotheses in `seed/hypotheses/new-market/`
6. Set the new profile as active: `sigma-quant config set activeProfile profiles/new-market.json`

### Adding a New Worker

1. Create a mission prompt in `prompts/new-worker.md`
2. Define sub-agent files in `.claude/agents/`
3. Update `config.json` to include the new worker type and pane mapping
4. Update `internal/cmd/start.go` to handle the new worker type
5. Increase the default pane count if needed

### Adding a New Claude Code Agent

1. Create a markdown file in `.claude/agents/quant-new-agent.md`
2. Add frontmatter with the agent's model, mode, and skill references
3. Define the agent's purpose and output expectations
4. Reference it from the appropriate worker's prompt

### Adding a New Skill

1. Create a directory in `.claude/skills/quant-new-skill/`
2. Add a `SKILL.md` file with the skill's knowledge
3. Reference it in the relevant agent's frontmatter
4. Skills are pure knowledge -- they have no runtime behavior

### Adding a TUI Component

1. Create a new file in `internal/tui/components/`
2. Implement the component using Lipgloss styles from `internal/tui/styles/`
3. Use the component in a model's `View()` method
4. Components are pure rendering functions -- they take data and return strings

### Adding a CLI Command

1. Create a new file in `internal/cmd/` (e.g., `internal/cmd/new_command.go`)
2. Define a `cobra.Command` struct
3. Register it with the root command in `init()`
4. If the command needs a TUI, create a model in `internal/tui/models/`
