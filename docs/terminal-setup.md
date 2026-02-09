# Terminal Setup

This guide covers how to work with tmux and iTerm2 when running the
Sigma-Quant Stream agent swarm. You will learn how to navigate between panes,
read agent output, troubleshoot stuck agents, and customize the layout.

---

## Table of Contents

1. [tmux Quick Reference](#tmux-quick-reference)
2. [What Each Pane Shows](#what-each-pane-shows)
3. [Navigating the Session](#navigating-the-session)
4. [Reading Agent Output](#reading-agent-output)
5. [iTerm2 Native Panes (macOS)](#iterm2-native-panes-macos)
6. [Troubleshooting Stuck Agents](#troubleshooting-stuck-agents)
7. [Customizing the Layout](#customizing-the-layout)
8. [Using sigma-quant status as a Dashboard](#using-sigma-quant-status-as-a-dashboard)

---

## tmux Quick Reference

tmux is a terminal multiplexer that lets you run multiple terminal sessions
inside one window. Sigma-Quant Stream uses it to run 4 agent workers
simultaneously.

### Essential Commands

All tmux shortcuts start with the **prefix key**: `Ctrl-b`. Press `Ctrl-b`
first, release, then press the next key.

| Action | Keys | Description |
|--------|------|-------------|
| Attach to session | `tmux attach -t sigma-quant` | Reconnect to the running swarm |
| Detach | `Ctrl-b d` | Disconnect (agents keep running in background) |
| Navigate panes | `Ctrl-b arrow` | Move focus between panes (up/down/left/right) |
| Zoom pane | `Ctrl-b z` | Toggle full-screen zoom on current pane |
| Scroll mode | `Ctrl-b [` | Enter scroll mode to read history |
| Exit scroll | `q` | Leave scroll mode |
| List sessions | `tmux ls` | Show all active tmux sessions |
| Kill session | `tmux kill-session -t sigma-quant` | Force-stop the session |

### Scroll Mode Navigation

Once in scroll mode (`Ctrl-b [`), you can navigate:

| Action | Keys |
|--------|------|
| Scroll up | Arrow up, Page Up, or mouse wheel |
| Scroll down | Arrow down, Page Down, or mouse wheel |
| Search backward | `?` then type search term |
| Search forward | `/` then type search term |
| Go to top | `g` |
| Go to bottom | `G` |
| Exit scroll | `q` or `Escape` |

### Session Management

```bash
# List all sessions
tmux ls

# Attach to the sigma-quant session
tmux attach -t sigma-quant

# Create a new window within the session (for your own work)
# Ctrl-b c

# Switch between windows
# Ctrl-b n (next)
# Ctrl-b p (previous)

# Rename the current window
# Ctrl-b , (type new name, press Enter)
```

---

## What Each Pane Shows

When you attach to the sigma-quant tmux session, you see 4 panes in a grid.

### Pane Layout

```
+-------------------------------+-------------------------------+
|  Pane 0: RESEARCHER           |  Pane 1: CONVERTER            |
|                                |                                |
|  Claude Code session running   |  Claude Code session running   |
|  the researcher mission.       |  the converter mission.        |
|                                |                                |
|  You will see:                 |  You will see:                 |
|  - Pattern file loading        |  - PineScript parsing          |
|  - Web search queries          |  - Python code generation      |
|  - Hypothesis formulation      |  - Test creation               |
|  - Queue push operations       |  - Backtest queue pushes       |
|                                |                                |
+-------------------------------+-------------------------------+
|  Pane 2: BACKTESTER           |  Pane 3: OPTIMIZER            |
|                                |                                |
|  Claude Code session running   |  Claude Code session running   |
|  the backtester mission.       |  the optimizer mission.        |
|                                |                                |
|  You will see:                 |  You will see:                 |
|  - Walk-forward execution      |  - Grid search runs            |
|  - Overfit detection           |  - Perturbation tests          |
|  - Cost validation             |  - Prop firm compliance        |
|  - Strategy grading            |  - Strategy promotion          |
|                                |                                |
+-------------------------------+-------------------------------+
```

### Identifying a Pane

Each pane shows its worker type in the Claude Code session output. Look for
the session start marker:

```
SESSION_START: researcher-2026-02-09T08:30:00Z
PATTERN_FILES_READ: what-works.md, what-fails.md
QUEUE_DEPTH: hypotheses=5, to-convert=3, to-backtest=2, to-optimize=1
```

---

## Navigating the Session

### Moving Between Panes

1. Press `Ctrl-b` (prefix)
2. Press an arrow key to move to the adjacent pane

```
         Ctrl-b Up
              |
Ctrl-b Left --+-- Ctrl-b Right
              |
         Ctrl-b Down
```

### Zooming Into a Pane

To focus on a single pane full-screen:

1. Navigate to the pane you want to zoom
2. Press `Ctrl-b z`
3. The pane expands to fill the entire terminal
4. Press `Ctrl-b z` again to unzoom

This is useful when you want to read detailed agent output without the clutter
of other panes.

### Watching a Specific Worker

If you want to follow the Backtester closely:

1. Attach: `tmux attach -t sigma-quant`
2. Navigate to Pane 2 (bottom left): `Ctrl-b Down`, then `Ctrl-b Left` if needed
3. Zoom: `Ctrl-b z`
4. Watch the walk-forward validation in real time
5. Unzoom when done: `Ctrl-b z`

---

## Reading Agent Output

### Session Markers

Agents emit structured markers that help you understand what is happening.

#### Session Start

```
SESSION_START: backtester-2026-02-09T10:15:00Z
PATTERN_FILES_READ: what-works.md, what-fails.md
QUEUE_DEPTH: hypotheses=5, to-convert=3, to-backtest=2, to-optimize=1
```

Tells you: A new Ralph loop iteration started. The agent loaded pattern
knowledge and checked queue depths.

#### Task Processing

```
TASK_START: bt-2026-02-09-003
SUBAGENT_SPAWN: @quant-walk-forward
SUBAGENT_COMPLETE: @quant-walk-forward (duration: 3m22s)
SUBAGENT_SPAWN: @quant-overfit-checker
SUBAGENT_COMPLETE: @quant-overfit-checker (PASS)
```

Tells you: The agent is processing a specific queue item, delegating to
sub-agents for each step.

#### Strategy Grading

```
STRATEGY_GRADED: rsi-divergence-es-5m
  Sharpe: 1.42
  Max DD: -11.8%
  Trades: 234
  OOS Decay: 18.3%
  Verdict: GOOD
  Destination: output/strategies/good/
```

Tells you: A strategy completed validation and was routed to the appropriate
output directory.

#### Session End

```
DISTILLATION_COMPLETE
PATTERNS_UPDATED: what-works.md (+2 entries), what-fails.md (+1 entry)
SESSION_COMPLETE: backtester-2026-02-09T10:15:00Z
DURATION: 28m
TASKS_COMPLETED: 4
STRATEGIES_PRODUCED: 1
```

Tells you: The session is ending. Pattern files were updated with new
learnings. The Ralph loop will restart with fresh context.

### Common Output Patterns

| Pattern | Meaning |
|---------|---------|
| `STRATEGY_REJECTED` | Strategy failed validation (see reason) |
| `QUEUE_EMPTY` | No items to process, agent is discovering new work |
| `BUDGET_WARNING` | Approaching API cost cap |
| `RETRY_ATTEMPT` | An operation failed and is being retried |
| `CLAIMED: hyp-xxx` | Agent claimed a queue item for processing |

---

## iTerm2 Native Panes (macOS)

If you use iTerm2 on macOS, you can use native split panes instead of tmux.
This gives you better scrollback, search, and mouse support.

### Launching with iTerm2

The project includes an iTerm2 launcher script:

```bash
# Using the iTerm2 JavaScript launcher
osascript scripts/iterm-quant-launcher.js
```

This creates an iTerm2 window with 4 split panes, each running a worker.

### iTerm2 Keyboard Shortcuts

| Action | Keys |
|--------|------|
| Navigate panes | `Cmd-Option-Arrow` |
| Zoom pane | `Cmd-Shift-Enter` |
| Split horizontal | `Cmd-Shift-D` |
| Split vertical | `Cmd-D` |
| Close pane | `Cmd-W` |
| Search in pane | `Cmd-F` |
| Clear scrollback | `Cmd-K` |

### When to Use iTerm2 vs tmux

| Feature | tmux | iTerm2 |
|---------|------|--------|
| Runs without GUI | Yes | No |
| SSH-compatible | Yes | No |
| Mouse scrollback | Limited | Native |
| Search in output | Basic | Full |
| Runs on Linux | Yes | No |
| Background persistence | Yes | Only while iTerm2 is open |

**Recommendation:** Use tmux for production runs (especially headless or remote
servers). Use iTerm2 for local development when you want better readability.

---

## Troubleshooting Stuck Agents

### Symptoms of a Stuck Agent

- No new output in the pane for more than 5 minutes
- Repeated error messages in a loop
- Claude Code prompt waiting for input (should not happen in autonomous mode)

### Diagnostic Steps

1. **Attach and navigate to the stuck pane:**

```bash
tmux attach -t sigma-quant
# Ctrl-b arrow to navigate to the pane
```

2. **Enter scroll mode to read recent output:**

```
Ctrl-b [
```

Look for error messages, timeout notices, or API errors.

3. **Check if the Ralph loop is running:**

The Ralph loop should restart Claude Code automatically. If the pane shows a
bare shell prompt (`$`), the loop has exited.

4. **Restart the specific worker:**

```bash
sigma-quant stop researcher
sigma-quant start researcher
```

### Common Stuck Scenarios

**API rate limit:**
```
Error: rate_limit_exceeded
```
The Ralph loop will pause and retry automatically. If it persists, check your
Anthropic API usage at console.anthropic.com.

**Budget cap reached:**
```
BUDGET_CAP_REACHED: $50.00 limit
```
The worker stops to prevent overspending. Increase the budget in `config.json`:
```bash
sigma-quant config set modes.research.budgetCap 100
sigma-quant start
```

**Queue deadlock (all queues empty, all workers idle):**

This happens when the Researcher has not found any ideas yet. Seed hypotheses
to break the deadlock:

```bash
cp seed/hypotheses/*.json queues/hypotheses/
```

**Context window exhaustion:**

Claude Code sessions have a context limit. If an agent is doing very large
operations, it may fill the context and crash. The Ralph loop restarts
automatically with fresh context. If it keeps crashing on the same task:

```bash
# Remove the problematic queue item
ls queues/to-backtest/
rm queues/to-backtest/bt-problematic-item.json
```

---

## Customizing the Layout

### Changing the Number of Workers

Edit `config.json`:

```json
{
  "defaults": {
    "panes": 2
  }
}
```

With 2 panes, only the Researcher and Backtester run. This is useful for
reducing API costs during exploration.

### Starting Specific Workers

```bash
# Start only the researcher and backtester
sigma-quant start researcher
sigma-quant start backtester
```

### Custom tmux Layout

If you prefer a different pane arrangement, you can manually reconfigure after
launch:

```bash
# Attach to session
tmux attach -t sigma-quant

# Resize panes (make pane 0 taller)
# Ctrl-b : resize-pane -U 10

# Rearrange to horizontal layout
# Ctrl-b : select-layout even-horizontal

# Rearrange to vertical layout
# Ctrl-b : select-layout even-vertical
```

### Available tmux Layouts

| Layout | Command | Description |
|--------|---------|-------------|
| Even horizontal | `select-layout even-horizontal` | All panes side by side |
| Even vertical | `select-layout even-vertical` | All panes stacked |
| Main horizontal | `select-layout main-horizontal` | One large + others below |
| Main vertical | `select-layout main-vertical` | One large + others beside |
| Tiled | `select-layout tiled` | Grid (default for 4 panes) |

---

## Using sigma-quant status as a Dashboard

The `sigma-quant status` command provides a TUI dashboard that shows system
state without attaching to the tmux session.

### Static Status

```bash
sigma-quant status
```

Prints a one-shot snapshot of:
- Worker status (running/stopped) for each pane
- Queue depths and throughput
- Strategy counts by grade
- API cost tracking

### Live Dashboard

```bash
sigma-quant status --watch
```

Launches a Bubble Tea TUI that updates every 2 seconds. Navigate with:

| Key | Action |
|-----|--------|
| `Tab` | Switch between dashboard tabs |
| `q` / `Ctrl-c` | Exit the dashboard |
| `r` | Force refresh |
| Arrow keys | Navigate within lists |

### Dashboard Tabs

| Tab | Shows |
|-----|-------|
| Workers | Per-pane status, session count, last activity |
| Queues | Depth per queue, items processed, oldest pending |
| Strategies | Count by grade, recent discoveries |
| Costs | Cumulative spend, burn rate, budget remaining |

### Running Dashboard Alongside tmux

You can run the dashboard in a separate terminal while the agents work in tmux:

```
Terminal 1: tmux attach -t sigma-quant (watch agents)
Terminal 2: sigma-quant status --watch  (monitor metrics)
```

This gives you both detailed agent output and high-level metrics at the same
time.
