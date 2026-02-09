# Getting Started with Sigma-Quant Stream

This guide walks you through installing Sigma-Quant Stream and running your first
autonomous strategy research session. By the end, you will have 4 AI agents
working in parallel to discover, validate, and grade trading strategies.

---

## Prerequisites

Before installing, make sure you have the following tools available on your machine.

### Required

| Tool | Minimum Version | Purpose | Install |
|------|----------------|---------|---------|
| Go | 1.22+ | Build the `sigma-quant` binary | [go.dev/dl](https://go.dev/dl/) |
| Python | 3.11+ | Backtest engine, data adapters | [python.org](https://python.org) |
| tmux | 3.0+ | Multi-pane agent sessions | See below |
| Claude Code CLI | Latest | AI agent execution runtime | `npm install -g @anthropic-ai/claude-code` |
| `ANTHROPIC_API_KEY` | -- | Access to Claude API | [console.anthropic.com](https://console.anthropic.com) |

### Optional

| Tool | Purpose | When Needed |
|------|---------|-------------|
| `DATABENTO_API_KEY` | CME futures market data | Futures strategies |
| `ccxt` (Python) | Crypto exchange data | Crypto CEX strategies |
| Node.js 18+ | Installing Claude Code CLI | Only for initial CLI install |

### Installing tmux

```bash
# macOS
brew install tmux

# Ubuntu / Debian
sudo apt install tmux

# Arch Linux
sudo pacman -S tmux

# Fedora
sudo dnf install tmux
```

### Verifying Prerequisites

Run each of these to confirm versions:

```bash
go version          # go1.22 or higher
python3 --version   # 3.11 or higher
tmux -V             # tmux 3.0 or higher
claude --version    # any recent version
```

---

## Installation

Three commands to get a working binary.

### Step 1: Clone the Repository

```bash
git clone https://github.com/Dallionking/sigma-quant-stream.git
cd sigma-quant-stream
```

### Step 2: Build the Binary

```bash
make build
```

This compiles the Go binary to `bin/sigma-quant` with version information
embedded via linker flags. The binary is self-contained and has no Go runtime
dependencies.

### Step 3: Verify the Build

```bash
./bin/sigma-quant --version
```

You should see output like:

```
sigma-quant v2.1.0 (abc1234) built 2026-02-09T12:00:00Z
```

### Alternative Installation Methods

**Go install (adds to your `$GOPATH/bin`):**

```bash
go install github.com/Dallionking/sigma-quant-stream/cmd/sigma-quant@latest
```

**Homebrew (macOS / Linux):**

```bash
brew install Dallionking/tap/sigma-quant
```

After installing via any method, verify with:

```bash
sigma-quant --version
```

For the rest of this guide, we assume you are in the `sigma-quant-stream/`
directory and using `./bin/sigma-quant` or have added `bin/` to your `PATH`.

---

## Configuration

### Step 1: Set Up Environment Variables

```bash
cp .env.example .env
```

Open `.env` in your editor and add your Anthropic API key:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

If you plan to research futures strategies, also add:

```bash
DATABENTO_API_KEY=db-your-key-here
```

### Step 2: Run the Interactive Setup

```bash
sigma-quant init
```

The `init` command launches an interactive onboarding wizard that walks you
through:

1. **Market selection** -- Futures, Crypto CEX, Crypto DEX, or all three
2. **Data provider setup** -- Validates API keys and connectivity
3. **Symbol selection** -- Choose instruments or auto-discover by volume
4. **Mode selection** -- Research (sample data, lower cost) or Production (live feeds)
5. **Compliance preferences** -- Which prop firms or exchange rules to validate against

The wizard writes your choices to `config.json` and sets the active market
profile in `profiles/`.

### Step 3: Health Check

```bash
sigma-quant health
```

The health check validates:

- Python version and required packages
- Claude Code CLI installation and authentication
- tmux availability
- API key validity (Anthropic, Databento, exchange keys)
- Directory structure integrity (queues, output, patterns)
- Configuration file syntax

Each item is marked as PASS (green), WARN (yellow), or FAIL (red). Fix any FAIL
items before proceeding. WARN items are optional but recommended.

---

## First Run

### Launch the Agent Swarm

```bash
sigma-quant start
```

This command:

1. Creates a tmux session named `sigma-quant`
2. Splits it into 4 panes (one per worker)
3. Seeds each pane with its mission prompt from `prompts/`
4. Starts the Ralph loop in each pane (infinite restart cycle)
5. Returns control to your terminal

### What You Will See

After launching, attach to the tmux session to watch the agents work:

```bash
tmux attach -t sigma-quant
```

You will see 4 panes arranged in a grid:

```
+------------------------------+------------------------------+
|  PANE 0: Researcher          |  PANE 1: Converter           |
|                               |                               |
|  Hunting for trading edges    |  Translating PineScript to   |
|  from web, papers, TV ideas   |  Python + writing tests      |
|                               |                               |
+------------------------------+------------------------------+
|  PANE 2: Backtester          |  PANE 3: Optimizer           |
|                               |                               |
|  Running walk-forward         |  Grid search, perturbation   |
|  validation on strategies     |  testing, prop firm checks   |
|                               |                               |
+------------------------------+------------------------------+
```

Each pane shows a Claude Code session actively working. You will see the AI
agents reading pattern files, scanning queues, spawning sub-agents, and producing
artifacts in real time.

To detach and let the agents run in the background:

```
Ctrl-b d
```

### Understanding the Ralph Loop

Each worker runs an infinite restart cycle called the Ralph loop. When a Claude
Code session ends (context fills up, task completes, or timeout), a new session
starts automatically with:

1. The worker's mission prompt (e.g., `prompts/researcher.md`)
2. The last session summary (from `session-summaries/pane-N.md`)
3. Current pattern knowledge (`patterns/what-works.md`, `patterns/what-fails.md`)
4. Current queue state (pending items across all queues)

This means the swarm runs indefinitely. You start it, go to sleep, and wake up
to validated strategies.

---

## Monitoring Progress

### Live Dashboard

```bash
sigma-quant status --watch
```

This launches a real-time Bubble Tea TUI dashboard showing:

- Worker status (running, idle, restarting) for each pane
- Queue depths (hypotheses, to-convert, to-backtest, to-optimize)
- Strategy counts by grade (rejected, under review, good, prop firm ready)
- API cost tracking (cumulative spend across all sessions)

### One-Shot Status

```bash
sigma-quant status
```

Prints a static snapshot of the same information.

### List Discovered Strategies

```bash
# All strategies
sigma-quant strategies

# Filter by grade
sigma-quant strategies -g good
sigma-quant strategies -g prop_firm_ready

# Show details for a specific strategy
sigma-quant strategies --detail <strategy-id>
```

---

## Where Results Go

All output is written to the `output/` directory, organized by quality grade.

### Strategy Grades

| Directory | Meaning |
|-----------|---------|
| `output/strategies/rejected/` | Failed validation (Sharpe < 1.0, overfit, insufficient trades) |
| `output/strategies/under_review/` | Passed basic checks but has concerns (OOS decay 30-50%) |
| `output/strategies/good/` | Passed all validation gates and robustness checks |
| `output/strategies/prop_firm_ready/` | Passed compliance testing against 3+ prop firms or exchange rules |

### Other Output

| Directory | Contents |
|-----------|----------|
| `output/indicators/converted/` | Python indicators translated from PineScript |
| `output/indicators/created/` | Novel indicators created by the research agents |
| `output/backtests/` | Detailed backtest result JSON files |
| `output/research-logs/` | Session logs from each research cycle |

### Strategy Artifact Structure

Each strategy in `good/` or `prop_firm_ready/` includes:

```
output/strategies/good/rsi-divergence-es-5m/
  strategy.py          # The strategy implementation
  hypothesis.json      # The original hypothesis card
  backtest_results.json # Walk-forward backtest results
  parameters.json      # Optimized parameter set
  compliance.json      # Prop firm / exchange validation results
  README.md            # Auto-generated documentation
```

---

## Stopping the Swarm

### Graceful Shutdown

```bash
sigma-quant stop
```

This sends a stop signal to each pane, allowing current tasks to complete before
shutting down the tmux session. Session summaries are written so the next `start`
picks up where it left off.

### Immediate Shutdown

If you need to stop immediately:

```bash
tmux kill-session -t sigma-quant
```

Note: this does not write session summaries, so some in-progress work may be lost.

---

## Common Issues and Solutions

### "Claude Code CLI not found"

```
FAIL: claude command not available
```

**Fix:** Install the Claude Code CLI globally:

```bash
npm install -g @anthropic-ai/claude-code
```

If you do not have Node.js, install it first from [nodejs.org](https://nodejs.org).

### "ANTHROPIC_API_KEY not set"

```
FAIL: ANTHROPIC_API_KEY environment variable not set
```

**Fix:** Add your API key to the `.env` file:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-api03-your-key-here" >> .env
```

Or export it directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### "tmux session already exists"

```
duplicate session: sigma-quant
```

**Fix:** Either reattach to the existing session or kill it and restart:

```bash
# Reattach
tmux attach -t sigma-quant

# Or kill and restart
sigma-quant stop
sigma-quant start
```

### "Python package not found" (ccxt, pandas-ta, etc.)

```
WARN: ccxt not installed
```

**Fix:** Install the missing package:

```bash
pip install ccxt pandas-ta numpy pandas
```

Or use the auto-fix flag:

```bash
sigma-quant health --fix
```

### "Databento API returned 4xx"

Your Databento key may be invalid or expired. For futures research, this is
required. For crypto research, Databento is not needed.

**Fix:** Verify your key at [databento.com](https://databento.com) and update `.env`.

### Agents Appear Stuck in a Pane

If a pane shows no activity for more than 5 minutes:

1. Attach to the tmux session: `tmux attach -t sigma-quant`
2. Navigate to the stuck pane: `Ctrl-b arrow`
3. Check if Claude Code is waiting for input or has errored
4. If stuck, the Ralph loop should automatically restart the session

If the Ralph loop itself is stuck:

```bash
# Restart a single worker
sigma-quant stop researcher
sigma-quant start researcher
```

### "Queue directory missing"

```
FAIL: queues/hypotheses/ does not exist
```

**Fix:** Run init to recreate the directory structure:

```bash
sigma-quant init
```

Or create manually:

```bash
mkdir -p queues/{hypotheses,to-convert,to-backtest,to-optimize}
```

---

## Next Steps

Choose your path based on how you want to use Sigma-Quant Stream.

### Trader Path (No Coding Required)

If you want to discover strategies without writing code:

1. Read the [Trader Path Guide](trader-path.md) for a zero-code workflow
2. Seed hypotheses from your own trading ideas
3. Configure risk parameters in `config.json`
4. Let the agents research, validate, and grade strategies
5. Deploy validated strategies to Freqtrade paper trading

### Developer Path (Extend the System)

If you want to write custom indicators, strategies, or agents:

1. Read the [Developer Path Guide](developer-path.md) for code examples
2. Write custom Python indicators in `lib/`
3. Create hypothesis cards manually and drop them in `seed/hypotheses/`
4. Add new Claude Code agents in `.claude/agents/`
5. Extend worker prompts in `prompts/`

### Terminal Setup

For optimal tmux and iTerm2 configuration:

1. Read the [Terminal Setup Guide](terminal-setup.md)
2. Learn tmux navigation shortcuts
3. Customize the pane layout
4. Set up iTerm2 native panes (macOS)

### Architecture Deep Dive

To understand how the system works internally:

1. Read the [Architecture Guide](architecture.md)
2. Understand the Go package structure
3. Learn how the Bubble Tea TUI works
4. Study the file-based queue IPC system

---

## Quick Reference

### Essential Commands

```bash
sigma-quant init                # Interactive setup wizard
sigma-quant start               # Launch all 4 workers
sigma-quant stop                # Graceful shutdown
sigma-quant status              # One-shot status
sigma-quant status --watch      # Live dashboard
sigma-quant health              # Dependency check
sigma-quant strategies          # List discovered strategies
sigma-quant strategies -g good  # Filter by grade
sigma-quant deploy              # Export to Freqtrade paper trading
sigma-quant tutorial            # Guided 6-step walkthrough
```

### Key Directories

```bash
output/strategies/good/          # Validated strategies
output/strategies/prop_firm_ready/ # Compliance-tested strategies
patterns/                        # Cross-session knowledge base
queues/                          # Inter-worker communication
prompts/                         # Worker mission prompts
profiles/                        # Market profile configs
seed/hypotheses/                 # Pre-loaded strategy ideas
```

### tmux Essentials

```bash
tmux attach -t sigma-quant     # Attach to the agent session
Ctrl-b d                       # Detach (agents keep running)
Ctrl-b arrow                   # Navigate between panes
Ctrl-b z                       # Zoom/unzoom a pane
Ctrl-b [                       # Scroll mode (q to exit)
```
