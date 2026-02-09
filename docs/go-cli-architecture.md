# Sigma-Quant Stream: Go CLI Architecture

**Version:** 1.0.0
**Last Updated:** 2026-02-09
**Author:** Lead Architect Agent
**Status:** Accepted

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Go Project Structure](#2-go-project-structure)
3. [Command Tree (Cobra)](#3-command-tree-cobra)
4. [Bubble Tea TUI Architecture](#4-bubble-tea-tui-architecture)
5. [Agent Orchestration Layer](#5-agent-orchestration-layer)
6. [Python Integration Layer](#6-python-integration-layer)
7. [Configuration Management (Viper)](#7-configuration-management-viper)
8. [Queue System](#8-queue-system)
9. [Dual-Path Onboarding Design](#9-dual-path-onboarding-design)
10. [Cross-Compilation and Distribution](#10-cross-compilation-and-distribution)
11. [Testing Strategy](#11-testing-strategy)
12. [Architecture Decision Records](#12-architecture-decision-records)

---

## 1. System Overview

### What This Replaces

The existing CLI is a Python/Typer/Rich application spread across `cli/main.py`, `cli/onboarding.py`, `cli/status.py`, `cli/tutorial.py`, `cli/strategies.py`, `cli/health.py`, and `cli/setup_claude.py`. It works, but has limitations:

- No real-time TUI (Rich tables are static, `--watch` uses `time.sleep` polling with full redraws)
- No composable UI components (each command reimplements rendering)
- Distribution requires Python + pip/uv + all dependencies on the user's machine
- No animated transitions, no keyboard-driven navigation, no split-pane layouts

### What the Go CLI Provides

A single statically-linked binary (`sigma-quant`) that:

1. Replaces all Python CLI commands with native Go implementations
2. Adds a real-time Bubble Tea TUI dashboard with tick-based updates
3. Provides animated onboarding wizards via Huh forms
4. Ships as a single binary (no runtime dependencies except tmux and Python for backends)
5. Implements the "Sharian" dark cyberpunk aesthetic via a Lipgloss theme layer

### High-Level Component Diagram

```
+----------------------------------------------------------------------+
|                         sigma-quant binary                           |
+----------------------------------------------------------------------+
|                                                                      |
|  +------------------+    +------------------+    +-----------------+ |
|  |   Cobra Commands |    | Bubble Tea TUI   |    |  Viper Config   | |
|  |                  |    |                  |    |                 | |
|  |  init            |    |  Dashboard Model |    |  config.json    | |
|  |  start           |--->|  Onboarding Model|--->|  .env           | |
|  |  stop            |    |  Tutorial Model  |    |  profiles/*.json| |
|  |  status          |    |  Strategy Model  |    |  CLI flags      | |
|  |  health          |    |  Health Model    |    |                 | |
|  |  data *          |    |                  |    |                 | |
|  |  strategies      |    +--------+---------+    +-----------------+ |
|  |  deploy          |             |                                  |
|  |  tutorial         |             |                                  |
|  |  config *        |             v                                  |
|  |  setup-claude    |    +-----------------+    +-----------------+  |
|  +------------------+    | Lipgloss Theme  |    |  Agent Orch.    |  |
|                          | (Sharian Dark)  |    |                 |  |
|                          +-----------------+    |  tmux spawn     |  |
|                                                 |  health poll    |  |
|                                                 |  ralph loop     |  |
|                                                 |  log capture    |  |
|                                                 +---------+-------+  |
|                                                           |          |
+-----------------------------------------------------------+----------+
                                                            |
                               +----------------------------v----------+
                               |       External Processes              |
                               |                                       |
                               |  tmux sessions (4 panes)              |
                               |  claude --dangerously-skip-permissions|
                               |  python lib/backtest_runner.py        |
                               |  python lib/crypto/*.py               |
                               |  python scripts/download-data.py     |
                               +---------------------------------------+
```

### Technology Selection Rationale

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **Go 1.22+** | Language | Single binary, fast startup, strong concurrency, cross-compilation |
| **Cobra** | CLI framework | Industry standard (kubectl, gh, docker all use it), subcommand routing |
| **Bubble Tea** | TUI framework | Elm architecture, composable models, tick-based updates |
| **Huh** | Form library | Built for Bubble Tea, accessible, validates input |
| **Lipgloss** | Styling | CSS-like API, theme tokens, works with Bubble Tea |
| **Bubbles** | Components | Spinners, progress bars, viewports, text inputs |
| **Viper** | Config | Flag/env/file precedence, watches for changes, JSON/YAML/TOML |
| **goreleaser** | Distribution | Cross-compilation, Homebrew, checksums, GitHub Releases |

---

## 2. Go Project Structure

```
sigma-quant-cli/
├── cmd/
│   └── sigma-quant/
│       └── main.go                    # Entry point: rootCmd.Execute()
│
├── internal/
│   ├── cmd/                           # Cobra command definitions
│   │   ├── root.go                    # Root command, global flags, Viper binding
│   │   ├── init.go                    # sigma-quant init
│   │   ├── setup_claude.go            # sigma-quant setup-claude
│   │   ├── start.go                   # sigma-quant start [worker]
│   │   ├── stop.go                    # sigma-quant stop [--force]
│   │   ├── status.go                  # sigma-quant status [--watch]
│   │   ├── health.go                  # sigma-quant health
│   │   ├── strategies.go              # sigma-quant strategies [--grade]
│   │   ├── deploy.go                  # sigma-quant deploy [strategy] [--dry-run]
│   │   ├── tutorial.go                # sigma-quant tutorial
│   │   ├── data.go                    # sigma-quant data (parent)
│   │   ├── data_download.go           # sigma-quant data download
│   │   ├── data_status.go             # sigma-quant data status
│   │   ├── config.go                  # sigma-quant config (parent)
│   │   ├── config_view.go             # sigma-quant config view
│   │   ├── config_set.go              # sigma-quant config set
│   │   ├── config_profiles.go         # sigma-quant config profiles
│   │   └── config_switch.go           # sigma-quant config switch
│   │
│   ├── tui/                           # Bubble Tea TUI layer
│   │   ├── app.go                     # Top-level tea.Model router
│   │   ├── keys.go                    # Global keybinding definitions
│   │   │
│   │   ├── models/                    # Individual Bubble Tea models
│   │   │   ├── dashboard.go           # Real-time status dashboard
│   │   │   ├── onboarding.go          # Multi-step onboarding wizard
│   │   │   ├── tutorial.go            # 6-step pipeline walkthrough
│   │   │   ├── strategy_browser.go    # Sortable strategy table
│   │   │   ├── health_report.go       # Health check display
│   │   │   ├── data_progress.go       # Download progress tracking
│   │   │   ├── deploy_confirm.go      # Deploy confirmation flow
│   │   │   ├── spinner.go             # Reusable spinner model
│   │   │   └── help_overlay.go        # ? key overlay
│   │   │
│   │   ├── views/                     # Composed multi-model views
│   │   │   ├── dashboard_view.go      # 4-pane dashboard layout
│   │   │   ├── onboarding_view.go     # Onboarding step composition
│   │   │   └── tutorial_view.go       # Tutorial step composition
│   │   │
│   │   ├── theme/                     # Lipgloss theme system
│   │   │   ├── colors.go              # Sharian color palette
│   │   │   ├── styles.go              # Reusable Lipgloss styles
│   │   │   ├── borders.go             # Custom border definitions
│   │   │   └── animation.go           # Spring-based animation helpers
│   │   │
│   │   └── components/                # Reusable Bubble Tea sub-models
│   │       ├── worker_card.go         # Single worker status card
│   │       ├── queue_bar.go           # Queue depth bar chart
│   │       ├── cost_tracker.go        # Running cost display
│   │       ├── strategy_row.go        # Single strategy table row
│   │       ├── step_indicator.go      # Step N/M progress dots
│   │       ├── code_block.go          # Syntax-highlighted code
│   │       └── notification.go        # Toast notification
│   │
│   ├── agent/                         # Agent orchestration
│   │   ├── manager.go                 # Agent lifecycle manager
│   │   ├── tmux.go                    # tmux session operations
│   │   ├── ralph.go                   # Ralph loop implementation
│   │   ├── health.go                  # Pane health monitoring
│   │   ├── log.go                     # Log capture and tail
│   │   └── types.go                   # Worker, AgentState types
│   │
│   ├── config/                        # Configuration management
│   │   ├── config.go                  # Viper setup, load, save
│   │   ├── profile.go                 # Market profile operations
│   │   ├── env.go                     # .env file read/write
│   │   ├── defaults.go               # Default configuration values
│   │   └── types.go                   # Config struct definitions
│   │
│   ├── queue/                         # File-based queue operations
│   │   ├── queue.go                   # Queue read/write/claim/complete
│   │   ├── watcher.go                 # fsnotify-based queue watcher
│   │   ├── item.go                    # QueueItem struct
│   │   └── stats.go                   # Queue depth/throughput stats
│   │
│   ├── python/                        # Python subprocess integration
│   │   ├── runner.go                  # Generic Python script executor
│   │   ├── backtest.go                # backtest_runner.py integration
│   │   ├── data.go                    # download-data.py integration
│   │   ├── propfirm.go               # prop-firm-validator.py integration
│   │   └── output.go                 # stdout/stderr parsing
│   │
│   ├── health/                        # System health checks
│   │   ├── checker.go                 # Health check runner
│   │   ├── checks.go                  # Individual check implementations
│   │   └── types.go                   # CheckResult type
│   │
│   └── strategy/                      # Strategy file operations
│       ├── loader.go                  # Load strategy JSON files
│       ├── metrics.go                 # Extract/format metrics
│       ├── grader.go                  # Grade computation
│       └── types.go                   # Strategy, Metrics structs
│
├── go.mod
├── go.sum
├── Makefile
├── .goreleaser.yaml
└── README.md
```

### Package Dependency Graph

```
cmd/sigma-quant/main.go
  └── internal/cmd/root.go
        ├── internal/cmd/*.go          (all subcommands)
        │     ├── internal/tui/*       (TUI models for interactive commands)
        │     ├── internal/agent/*     (agent orchestration)
        │     ├── internal/config/*    (configuration)
        │     ├── internal/queue/*     (queue operations)
        │     ├── internal/python/*    (Python subprocess calls)
        │     ├── internal/health/*    (health checks)
        │     └── internal/strategy/*  (strategy file I/O)
        └── internal/config/config.go  (Viper initialization)
```

**Rule: No circular dependencies.** The dependency flow is strictly top-down. `tui` may import `agent`, `config`, `queue`, `strategy`. None of those may import `tui`. The `cmd` package is the only package that wires things together.

---

## 3. Command Tree (Cobra)

### Root Command

```go
// internal/cmd/root.go
package cmd

import (
    "fmt"
    "os"

    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

var (
    cfgFile     string
    projectRoot string
    verbose     bool
)

var rootCmd = &cobra.Command{
    Use:   "sigma-quant",
    Short: "Autonomous Strategy Research Factory",
    Long: `Sigma-Quant Stream discovers, validates, and deploys profitable
trading strategies using 4 AI agents coordinating through file-based queues.

Markets: CME Futures (ES, NQ, YM, GC) + Crypto (BTC, ETH perps)`,
    SilenceUsage:  true,
    SilenceErrors: true,
}

func Execute() {
    if err := rootCmd.Execute(); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}

func init() {
    cobra.OnInitialize(initConfig)

    rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "",
        "config file (default: ./config.json)")
    rootCmd.PersistentFlags().StringVar(&projectRoot, "root", "",
        "project root directory (default: auto-detect)")
    rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false,
        "verbose output")

    viper.BindPFlag("root", rootCmd.PersistentFlags().Lookup("root"))
}

func initConfig() {
    if cfgFile != "" {
        viper.SetConfigFile(cfgFile)
    } else {
        viper.SetConfigName("config")
        viper.SetConfigType("json")
        viper.AddConfigPath(".")
        viper.AddConfigPath("$HOME/.sigma-quant")
    }

    viper.AutomaticEnv()
    viper.SetEnvPrefix("SIGMA_QUANT")

    if err := viper.ReadInConfig(); err != nil {
        if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
            fmt.Fprintf(os.Stderr, "Error reading config: %s\n", err)
        }
    }
}
```

### Complete Command Map

Every command maps from Cobra definition to its implementation module.

| Command | Cobra File | Interactive? | Implementation |
|---------|-----------|--------------|----------------|
| `sigma-quant` | `root.go` | No | Show help |
| `sigma-quant init` | `init.go` | Yes (Huh) | `tui/models/onboarding.go` |
| `sigma-quant setup-claude` | `setup_claude.go` | Yes (Huh) | `tui/models/setup_claude.go` |
| `sigma-quant start` | `start.go` | No | `agent/manager.go` |
| `sigma-quant start <worker>` | `start.go` | No | `agent/manager.go` |
| `sigma-quant stop` | `stop.go` | No | `agent/manager.go` |
| `sigma-quant stop --force` | `stop.go` | No | `agent/manager.go` |
| `sigma-quant status` | `status.go` | No | One-shot render |
| `sigma-quant status --watch` | `status.go` | Yes (BubbleTea) | `tui/models/dashboard.go` |
| `sigma-quant health` | `health.go` | No | `health/checker.go` |
| `sigma-quant strategies` | `strategies.go` | Yes (BubbleTea) | `tui/models/strategy_browser.go` |
| `sigma-quant strategies --grade X` | `strategies.go` | No | Filtered one-shot |
| `sigma-quant deploy` | `deploy.go` | Yes (confirm) | `python/runner.go` |
| `sigma-quant deploy --dry-run` | `deploy.go` | No | List only |
| `sigma-quant tutorial` | `tutorial.go` | Yes (BubbleTea) | `tui/models/tutorial.go` |
| `sigma-quant data download` | `data_download.go` | Yes (progress) | `python/data.go` |
| `sigma-quant data status` | `data_status.go` | No | One-shot table |
| `sigma-quant config` | `config.go` | No | Show JSON |
| `sigma-quant config view` | `config_view.go` | No | Pretty-print |
| `sigma-quant config set <k> <v>` | `config_set.go` | No | `config/config.go` |
| `sigma-quant config profiles` | `config_profiles.go` | No | Table render |
| `sigma-quant config switch <p>` | `config_switch.go` | No | `config/profile.go` |

### Example Subcommand Registration

```go
// internal/cmd/start.go
package cmd

import (
    "fmt"

    "github.com/sigma-algo/sigma-quant-cli/internal/agent"
    "github.com/sigma-algo/sigma-quant-cli/internal/config"
    "github.com/spf13/cobra"
)

var startCmd = &cobra.Command{
    Use:   "start [worker]",
    Short: "Launch workers in tmux",
    Long: `Launch the Ralph loop for one or all workers in tmux panes.

Workers: researcher, converter, backtester, optimizer

Examples:
  sigma-quant start              # Launch all 4 workers + dashboard
  sigma-quant start researcher   # Launch only the researcher`,
    Args: cobra.MaximumNArgs(1),
    ValidArgs: []string{"researcher", "converter", "backtester", "optimizer"},
    RunE: func(cmd *cobra.Command, args []string) error {
        cfg, err := config.Load()
        if err != nil {
            return fmt.Errorf("failed to load config: %w", err)
        }

        mgr := agent.NewManager(cfg)

        if len(args) == 1 {
            return mgr.StartWorker(args[0])
        }
        return mgr.StartAll()
    },
}

func init() {
    rootCmd.AddCommand(startCmd)
}
```

---

## 4. Bubble Tea TUI Architecture

### Core Elm Architecture Pattern

Every interactive view follows the same pattern. This is non-negotiable.

```go
// The Elm Architecture in Go:
//   Model  = struct with all state
//   Init   = func() tea.Cmd           (initial side effects)
//   Update = func(tea.Msg) tea.Cmd    (state transitions)
//   View   = func() string            (pure render)
```

### 4.1 Message Types (Global)

All custom messages live in a shared package to avoid import cycles.

```go
// internal/tui/messages.go
package tui

import "time"

// -- Tick messages for polling --

// TickMsg triggers periodic state refresh.
type TickMsg time.Time

// -- Agent messages --

// WorkerStatusMsg carries updated worker state.
type WorkerStatusMsg struct {
    Workers []WorkerState
}

// WorkerState represents one agent pane's current status.
type WorkerState struct {
    Name       string        // "researcher", "converter", etc.
    PaneIndex  int           // 0-3
    Running    bool          // tmux pane alive
    PID        int           // process ID in pane
    LastOutput string        // last line of output (truncated)
    Uptime     time.Duration // time since pane started
    TaskCount  int           // tasks completed this session
    Errors     int           // error count this session
}

// -- Queue messages --

// QueueStatsMsg carries queue depth information.
type QueueStatsMsg struct {
    Hypotheses int
    ToConvert  int
    ToBacktest int
    ToOptimize int
    Completed  int
    Failed     int
}

// -- Strategy messages --

// StrategyListMsg carries loaded strategies.
type StrategyListMsg struct {
    Strategies []StrategyEntry
    Err        error
}

// StrategyEntry is a single strategy with extracted metrics.
type StrategyEntry struct {
    Name           string
    Grade          string  // "prop_firm_ready", "good", "under_review", "rejected"
    Sharpe         float64
    WinRate        float64
    MaxDrawdown    float64
    Trades         int
    ProfitFactor   float64
    PropFirmsPassed []string
    FilePath       string
}

// -- Health messages --

// HealthResultMsg carries completed health check results.
type HealthResultMsg struct {
    Results []HealthCheck
}

// HealthCheck is a single pass/fail check.
type HealthCheck struct {
    Name    string
    Passed  bool
    Detail  string
    Category string // "runtime", "config", "data", "tools"
}

// -- Cost messages --

// CostUpdateMsg carries cost tracker state.
type CostUpdateMsg struct {
    SessionCost   float64
    BudgetCap     float64
    TokensUsed    int64
    EstTimeLeft   time.Duration
}

// -- Navigation messages --

// SwitchViewMsg tells the top-level router to change views.
type SwitchViewMsg struct {
    View string // "dashboard", "strategies", "tutorial", "help"
}

// ErrorMsg carries an error to display.
type ErrorMsg struct {
    Err error
}

// NotificationMsg triggers a toast notification.
type NotificationMsg struct {
    Title   string
    Body    string
    Level   string // "info", "success", "warning", "error"
    TTL     time.Duration
}
```

### 4.2 Theme System (Sharian Dark)

```go
// internal/tui/theme/colors.go
package theme

import "github.com/charmbracelet/lipgloss"

// Sharian palette: dark, cyberpunk, Gotham-inspired.
// Named after the aesthetic, not the colors themselves.
var (
    // -- Base tones --
    Black       = lipgloss.Color("#0a0a0f")    // Deep void
    DarkGray    = lipgloss.Color("#1a1a2e")    // Panel backgrounds
    MidGray     = lipgloss.Color("#2d2d44")    // Borders, separators
    LightGray   = lipgloss.Color("#6c6c8a")    // Muted text
    OffWhite    = lipgloss.Color("#c8c8d4")    // Body text
    White       = lipgloss.Color("#e8e8f0")    // Bright text

    // -- Accent colors --
    Cyan        = lipgloss.Color("#00d4ff")    // Primary accent
    CyanDim     = lipgloss.Color("#0088aa")    // Secondary accent
    Purple      = lipgloss.Color("#7b68ee")    // Highlights
    PurpleDim   = lipgloss.Color("#5548b0")    // Muted highlights
    Magenta     = lipgloss.Color("#ff2d95")    // Alerts, hot items

    // -- Semantic colors --
    Green       = lipgloss.Color("#00ff88")    // Pass, good, running
    GreenDim    = lipgloss.Color("#00aa55")    // Muted success
    Yellow      = lipgloss.Color("#ffd700")    // Warning, under review
    YellowDim   = lipgloss.Color("#aa8f00")    // Muted warning
    Red         = lipgloss.Color("#ff3366")    // Fail, rejected, error
    RedDim      = lipgloss.Color("#aa2244")    // Muted error
    Orange      = lipgloss.Color("#ff8c00")    // In-progress

    // -- Grade colors (strategy grading) --
    GradePropFirm  = Green
    GradeGood      = lipgloss.Color("#66ff66")
    GradeReview    = Yellow
    GradeRejected  = Red
)

// GradeColor returns the color for a strategy grade string.
func GradeColor(grade string) lipgloss.Color {
    switch grade {
    case "prop_firm_ready":
        return GradePropFirm
    case "good":
        return GradeGood
    case "under_review":
        return GradeReview
    case "rejected":
        return GradeRejected
    default:
        return LightGray
    }
}
```

```go
// internal/tui/theme/styles.go
package theme

import "github.com/charmbracelet/lipgloss"

var (
    // -- Layout styles --
    AppStyle = lipgloss.NewStyle().
        Background(Black).
        Padding(1, 2)

    PanelStyle = lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(MidGray).
        Background(DarkGray).
        Padding(1, 2)

    ActivePanelStyle = PanelStyle.
        BorderForeground(Cyan)

    // -- Text styles --
    TitleStyle = lipgloss.NewStyle().
        Foreground(Cyan).
        Bold(true).
        MarginBottom(1)

    SubtitleStyle = lipgloss.NewStyle().
        Foreground(LightGray).
        Italic(true)

    BodyStyle = lipgloss.NewStyle().
        Foreground(OffWhite)

    MutedStyle = lipgloss.NewStyle().
        Foreground(LightGray)

    BrightStyle = lipgloss.NewStyle().
        Foreground(White).
        Bold(true)

    // -- Status styles --
    RunningStyle = lipgloss.NewStyle().
        Foreground(Green).
        Bold(true)

    StoppedStyle = lipgloss.NewStyle().
        Foreground(Red)

    WarningStyle = lipgloss.NewStyle().
        Foreground(Yellow)

    ErrorStyle = lipgloss.NewStyle().
        Foreground(Red).
        Bold(true)

    // -- Interactive styles --
    SelectedStyle = lipgloss.NewStyle().
        Foreground(Cyan).
        Background(MidGray).
        Bold(true)

    KeyStyle = lipgloss.NewStyle().
        Foreground(Purple).
        Bold(true)

    HelpKeyStyle = lipgloss.NewStyle().
        Foreground(CyanDim)

    HelpDescStyle = lipgloss.NewStyle().
        Foreground(LightGray)

    // -- Notification styles --
    ToastInfoStyle = PanelStyle.
        BorderForeground(Cyan)

    ToastSuccessStyle = PanelStyle.
        BorderForeground(Green)

    ToastWarningStyle = PanelStyle.
        BorderForeground(Yellow)

    ToastErrorStyle = PanelStyle.
        BorderForeground(Red)

    // -- Code block style --
    CodeBlockStyle = lipgloss.NewStyle().
        Background(lipgloss.Color("#111122")).
        Foreground(lipgloss.Color("#d4d4d4")).
        Padding(1, 2).
        Border(lipgloss.NormalBorder()).
        BorderForeground(MidGray)
)

// StatusStyle returns the appropriate style for a boolean status.
func StatusStyle(running bool) lipgloss.Style {
    if running {
        return RunningStyle
    }
    return StoppedStyle
}

// StatusIndicator returns a colored status string.
func StatusIndicator(running bool) string {
    if running {
        return RunningStyle.Render("RUNNING")
    }
    return StoppedStyle.Render("STOPPED")
}
```

### 4.3 Keybindings

```go
// internal/tui/keys.go
package tui

import "github.com/charmbracelet/bubbles/key"

// GlobalKeys are available in every view.
type GlobalKeys struct {
    Quit       key.Binding
    Help       key.Binding
    ForceQuit  key.Binding
}

var GlobalKeyMap = GlobalKeys{
    Quit: key.NewBinding(
        key.WithKeys("q", "ctrl+c"),
        key.WithHelp("q", "quit"),
    ),
    Help: key.NewBinding(
        key.WithKeys("?"),
        key.WithHelp("?", "toggle help"),
    ),
    ForceQuit: key.NewBinding(
        key.WithKeys("ctrl+c"),
        key.WithHelp("ctrl+c", "force quit"),
    ),
}

// NavigationKeys are for list/table views.
type NavigationKeys struct {
    Up       key.Binding
    Down     key.Binding
    Top      key.Binding
    Bottom   key.Binding
    PageUp   key.Binding
    PageDown key.Binding
    Search   key.Binding
    Enter    key.Binding
    Back     key.Binding
    Tab      key.Binding
}

var NavKeyMap = NavigationKeys{
    Up: key.NewBinding(
        key.WithKeys("up", "k"),
        key.WithHelp("k/up", "up"),
    ),
    Down: key.NewBinding(
        key.WithKeys("down", "j"),
        key.WithHelp("j/down", "down"),
    ),
    Top: key.NewBinding(
        key.WithKeys("g"),
        key.WithHelp("g", "go to top"),
    ),
    Bottom: key.NewBinding(
        key.WithKeys("G"),
        key.WithHelp("G", "go to bottom"),
    ),
    PageUp: key.NewBinding(
        key.WithKeys("ctrl+u", "pgup"),
        key.WithHelp("ctrl+u", "page up"),
    ),
    PageDown: key.NewBinding(
        key.WithKeys("ctrl+d", "pgdown"),
        key.WithHelp("ctrl+d", "page down"),
    ),
    Search: key.NewBinding(
        key.WithKeys("/"),
        key.WithHelp("/", "search"),
    ),
    Enter: key.NewBinding(
        key.WithKeys("enter"),
        key.WithHelp("enter", "select"),
    ),
    Back: key.NewBinding(
        key.WithKeys("esc"),
        key.WithHelp("esc", "back"),
    ),
    Tab: key.NewBinding(
        key.WithKeys("tab"),
        key.WithHelp("tab", "next section"),
    ),
}
```

### 4.4 Dashboard Model (status --watch)

The dashboard is the most complex TUI view. It shows 4 worker panels, queue depths, strategy counts, and a cost tracker, all updating in real-time.

```go
// internal/tui/models/dashboard.go
package models

import (
    "fmt"
    "strings"
    "time"

    "github.com/charmbracelet/bubbles/spinner"
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"

    "github.com/sigma-algo/sigma-quant-cli/internal/agent"
    "github.com/sigma-algo/sigma-quant-cli/internal/config"
    "github.com/sigma-algo/sigma-quant-cli/internal/queue"
    "github.com/sigma-algo/sigma-quant-cli/internal/strategy"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui/theme"
)

const dashboardTickInterval = 3 * time.Second

// DashboardModel is the real-time monitoring dashboard.
type DashboardModel struct {
    // Dependencies (injected)
    agentMgr    *agent.Manager
    queueReader *queue.Reader
    stratLoader *strategy.Loader
    cfg         *config.Config

    // State
    workers       []tui.WorkerState
    queueStats    tui.QueueStatsMsg
    strategies    []tui.StrategyEntry
    costState     tui.CostUpdateMsg
    notifications []tui.NotificationMsg

    // UI state
    width       int
    height      int
    activePanel int     // 0=workers, 1=queues, 2=strategies, 3=cost
    showHelp    bool
    spinner     spinner.Model
    startTime   time.Time

    // Polling
    lastTick time.Time
}

// NewDashboardModel creates a dashboard with injected dependencies.
func NewDashboardModel(
    agentMgr *agent.Manager,
    queueReader *queue.Reader,
    stratLoader *strategy.Loader,
    cfg *config.Config,
) DashboardModel {
    s := spinner.New()
    s.Spinner = spinner.Dot
    s.Style = lipgloss.NewStyle().Foreground(theme.Cyan)

    return DashboardModel{
        agentMgr:    agentMgr,
        queueReader: queueReader,
        stratLoader: stratLoader,
        cfg:         cfg,
        activePanel: 0,
        spinner:     s,
        startTime:   time.Now(),
    }
}

func (m DashboardModel) Init() tea.Cmd {
    return tea.Batch(
        m.spinner.Tick,
        m.tickCmd(),
        m.pollWorkers(),
        m.pollQueues(),
        m.pollStrategies(),
        m.pollCost(),
    )
}

func (m DashboardModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    switch msg := msg.(type) {

    case tea.KeyMsg:
        switch {
        case key.Matches(msg, tui.GlobalKeyMap.Quit):
            return m, tea.Quit
        case key.Matches(msg, tui.GlobalKeyMap.Help):
            m.showHelp = !m.showHelp
        case key.Matches(msg, tui.NavKeyMap.Tab):
            m.activePanel = (m.activePanel + 1) % 4
        case msg.String() == "1":
            m.activePanel = 0
        case msg.String() == "2":
            m.activePanel = 1
        case msg.String() == "3":
            m.activePanel = 2
        case msg.String() == "4":
            m.activePanel = 3
        }

    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height

    case tui.TickMsg:
        m.lastTick = time.Time(msg)
        cmds = append(cmds,
            m.tickCmd(),
            m.pollWorkers(),
            m.pollQueues(),
            m.pollStrategies(),
            m.pollCost(),
        )

    case tui.WorkerStatusMsg:
        m.workers = msg.Workers

    case tui.QueueStatsMsg:
        m.queueStats = msg

    case tui.StrategyListMsg:
        if msg.Err == nil {
            m.strategies = msg.Strategies
        }

    case tui.CostUpdateMsg:
        m.costState = msg

    case spinner.TickMsg:
        var cmd tea.Cmd
        m.spinner, cmd = m.spinner.Update(msg)
        cmds = append(cmds, cmd)
    }

    return m, tea.Batch(cmds...)
}

func (m DashboardModel) View() string {
    if m.width == 0 {
        return "Initializing..."
    }

    // Header
    uptime := time.Since(m.startTime).Truncate(time.Second)
    header := theme.TitleStyle.Render(
        fmt.Sprintf(" SIGMA-QUANT DASHBOARD  %s  Uptime: %s",
            m.spinner.View(), uptime))

    // Calculate panel widths: 2 columns, each half screen width
    halfWidth := (m.width - 6) / 2 // account for borders + padding
    if halfWidth < 30 {
        halfWidth = 30
    }

    // Top row: Workers | Queues
    workersPanel := m.renderWorkersPanel(halfWidth)
    queuesPanel := m.renderQueuesPanel(halfWidth)
    topRow := lipgloss.JoinHorizontal(lipgloss.Top, workersPanel, "  ", queuesPanel)

    // Bottom row: Strategies | Cost
    strategiesPanel := m.renderStrategiesPanel(halfWidth)
    costPanel := m.renderCostPanel(halfWidth)
    bottomRow := lipgloss.JoinHorizontal(lipgloss.Top, strategiesPanel, "  ", costPanel)

    // Help bar
    helpBar := m.renderHelpBar()

    return lipgloss.JoinVertical(lipgloss.Left,
        header,
        "",
        topRow,
        "",
        bottomRow,
        "",
        helpBar,
    )
}

// -- Polling commands (return tea.Cmd) --

func (m DashboardModel) tickCmd() tea.Cmd {
    return tea.Tick(dashboardTickInterval, func(t time.Time) tea.Msg {
        return tui.TickMsg(t)
    })
}

func (m DashboardModel) pollWorkers() tea.Cmd {
    return func() tea.Msg {
        states := m.agentMgr.GetWorkerStates()
        return tui.WorkerStatusMsg{Workers: states}
    }
}

func (m DashboardModel) pollQueues() tea.Cmd {
    return func() tea.Msg {
        return m.queueReader.GetStats()
    }
}

func (m DashboardModel) pollStrategies() tea.Cmd {
    return func() tea.Msg {
        entries, err := m.stratLoader.LoadAll()
        return tui.StrategyListMsg{Strategies: entries, Err: err}
    }
}

func (m DashboardModel) pollCost() tea.Cmd {
    return func() tea.Msg {
        // Read cost-tracker.json
        return m.cfg.ReadCostTracker()
    }
}

// -- Render helpers --

func (m DashboardModel) renderWorkersPanel(width int) string {
    style := theme.PanelStyle.Width(width)
    if m.activePanel == 0 {
        style = theme.ActivePanelStyle.Width(width)
    }

    var sb strings.Builder
    sb.WriteString(theme.BrightStyle.Render("WORKERS") + "\n\n")

    workerNames := []string{"researcher", "converter", "backtester", "optimizer"}
    for i, name := range workerNames {
        status := "STOPPED"
        statusStyle := theme.StoppedStyle
        detail := ""

        for _, w := range m.workers {
            if w.Name == name {
                if w.Running {
                    status = "RUNNING"
                    statusStyle = theme.RunningStyle
                    detail = fmt.Sprintf(" (%d tasks, %s)",
                        w.TaskCount, w.Uptime.Truncate(time.Second))
                }
                break
            }
        }

        paneLabel := theme.MutedStyle.Render(fmt.Sprintf("[%d]", i))
        nameStr := theme.BodyStyle.Render(fmt.Sprintf("%-12s", name))
        statusStr := statusStyle.Render(status)
        detailStr := theme.MutedStyle.Render(detail)

        sb.WriteString(fmt.Sprintf(" %s %s %s%s\n", paneLabel, nameStr, statusStr, detailStr))
    }

    return style.Render(sb.String())
}

func (m DashboardModel) renderQueuesPanel(width int) string {
    style := theme.PanelStyle.Width(width)
    if m.activePanel == 1 {
        style = theme.ActivePanelStyle.Width(width)
    }

    var sb strings.Builder
    sb.WriteString(theme.BrightStyle.Render("QUEUES") + "\n\n")

    queues := []struct {
        name  string
        depth int
    }{
        {"hypotheses", m.queueStats.Hypotheses},
        {"to-convert", m.queueStats.ToConvert},
        {"to-backtest", m.queueStats.ToBacktest},
        {"to-optimize", m.queueStats.ToOptimize},
    }

    maxBar := width - 30
    if maxBar < 10 {
        maxBar = 10
    }

    maxDepth := 1
    for _, q := range queues {
        if q.depth > maxDepth {
            maxDepth = q.depth
        }
    }

    for _, q := range queues {
        barLen := 0
        if maxDepth > 0 {
            barLen = (q.depth * maxBar) / maxDepth
        }
        bar := strings.Repeat("█", barLen) + strings.Repeat("░", maxBar-barLen)

        nameStr := theme.BodyStyle.Render(fmt.Sprintf("%-14s", q.name))
        countStr := theme.CyanStyle.Render(fmt.Sprintf("%3d", q.depth))
        barStr := theme.CyanDimStyle.Render(bar)

        sb.WriteString(fmt.Sprintf(" %s %s %s\n", nameStr, countStr, barStr))
    }

    sb.WriteString(fmt.Sprintf("\n %s  %s",
        theme.MutedStyle.Render("completed:"),
        theme.GreenDimStyle.Render(fmt.Sprintf("%d", m.queueStats.Completed))))
    sb.WriteString(fmt.Sprintf("  %s  %s",
        theme.MutedStyle.Render("failed:"),
        theme.RedDimStyle.Render(fmt.Sprintf("%d", m.queueStats.Failed))))

    return style.Render(sb.String())
}

func (m DashboardModel) renderStrategiesPanel(width int) string {
    style := theme.PanelStyle.Width(width)
    if m.activePanel == 2 {
        style = theme.ActivePanelStyle.Width(width)
    }

    var sb strings.Builder
    sb.WriteString(theme.BrightStyle.Render("STRATEGIES") + "\n\n")

    counts := map[string]int{
        "prop_firm_ready": 0,
        "good":            0,
        "under_review":    0,
        "rejected":        0,
    }
    for _, s := range m.strategies {
        counts[s.Grade]++
    }

    gradeOrder := []struct {
        key   string
        label string
    }{
        {"prop_firm_ready", "Prop Firm Ready"},
        {"good", "Good"},
        {"under_review", "Under Review"},
        {"rejected", "Rejected"},
    }

    for _, g := range gradeOrder {
        color := theme.GradeColor(g.key)
        countStyle := lipgloss.NewStyle().Foreground(color).Bold(true)
        labelStyle := lipgloss.NewStyle().Foreground(color)
        sb.WriteString(fmt.Sprintf(" %s  %s\n",
            countStyle.Render(fmt.Sprintf("%3d", counts[g.key])),
            labelStyle.Render(g.label)))
    }

    sb.WriteString(fmt.Sprintf("\n %s %d",
        theme.MutedStyle.Render("Total:"),
        len(m.strategies)))

    return style.Render(sb.String())
}

func (m DashboardModel) renderCostPanel(width int) string {
    style := theme.PanelStyle.Width(width)
    if m.activePanel == 3 {
        style = theme.ActivePanelStyle.Width(width)
    }

    var sb strings.Builder
    sb.WriteString(theme.BrightStyle.Render("COST TRACKER") + "\n\n")

    pct := 0.0
    if m.costState.BudgetCap > 0 {
        pct = (m.costState.SessionCost / m.costState.BudgetCap) * 100
    }

    costColor := theme.Green
    if pct > 80 {
        costColor = theme.Red
    } else if pct > 60 {
        costColor = theme.Yellow
    }

    costStyle := lipgloss.NewStyle().Foreground(costColor).Bold(true)

    sb.WriteString(fmt.Sprintf(" Session:  %s / $%.2f\n",
        costStyle.Render(fmt.Sprintf("$%.2f", m.costState.SessionCost)),
        m.costState.BudgetCap))
    sb.WriteString(fmt.Sprintf(" Usage:    %s\n",
        costStyle.Render(fmt.Sprintf("%.1f%%", pct))))
    sb.WriteString(fmt.Sprintf(" Tokens:   %s\n",
        theme.BodyStyle.Render(fmt.Sprintf("%dk", m.costState.TokensUsed/1000))))

    return style.Render(sb.String())
}

func (m DashboardModel) renderHelpBar() string {
    pairs := []struct{ key, desc string }{
        {"q", "quit"},
        {"tab", "switch panel"},
        {"1-4", "jump to panel"},
        {"?", "help"},
    }

    var parts []string
    for _, p := range pairs {
        parts = append(parts,
            theme.KeyStyle.Render(p.key)+" "+theme.MutedStyle.Render(p.desc))
    }

    return theme.MutedStyle.Render(" ") + strings.Join(parts, "  ")
}
```

### 4.5 Onboarding Model (init)

The onboarding wizard uses Huh forms for each step and wraps them in a Bubble Tea model for transitions and animations.

```go
// internal/tui/models/onboarding.go
package models

import (
    "time"

    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/huh"

    "github.com/sigma-algo/sigma-quant-cli/internal/config"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui/theme"
)

// OnboardingStep enumerates the 6 onboarding steps.
type OnboardingStep int

const (
    StepWelcome OnboardingStep = iota
    StepPath          // Developer vs Trader
    StepMarket        // Futures / Crypto CEX / Crypto DEX
    StepAPIKeys       // Databento, exchange keys
    StepDataDownload  // Download sample data
    StepVerify        // Run health check
    StepComplete      // Success screen
)

// OnboardingModel manages the multi-step onboarding flow.
type OnboardingModel struct {
    step       OnboardingStep
    totalSteps int
    explain    bool // --explain flag: show educational panels

    // User selections
    userPath    string // "developer" or "trader"
    market      string // "futures", "crypto-cex", "crypto-dex-hyperliquid"
    apiKeys     map[string]string
    dataChoice  string // "sample" or "live"

    // Active form (only one at a time)
    activeForm *huh.Form

    // State
    width      int
    height     int
    err        error
    cfg        *config.Config

    // Animation
    fadeIn     float64
    startTime  time.Time
}

// NewOnboardingModel creates the onboarding wizard.
func NewOnboardingModel(cfg *config.Config, explain bool) OnboardingModel {
    return OnboardingModel{
        step:       StepWelcome,
        totalSteps: 6,
        explain:    explain,
        apiKeys:    make(map[string]string),
        cfg:        cfg,
        startTime:  time.Now(),
    }
}

func (m OnboardingModel) Init() tea.Cmd {
    return m.buildForm()
}

func (m OnboardingModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        if msg.String() == "ctrl+c" {
            return m, tea.Quit
        }

    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height

    case formCompleteMsg:
        // Advance to next step
        m.extractFormValues()
        m.step++
        if m.step > StepComplete {
            return m, tea.Quit
        }
        return m, m.buildForm()
    }

    // Delegate to the active form
    if m.activeForm != nil {
        form, cmd := m.activeForm.Update(msg)
        if f, ok := form.(*huh.Form); ok {
            m.activeForm = f
            if f.State == huh.StateCompleted {
                return m, func() tea.Msg { return formCompleteMsg{} }
            }
        }
        return m, cmd
    }

    return m, nil
}

type formCompleteMsg struct{}

func (m OnboardingModel) buildForm() tea.Cmd {
    var form *huh.Form

    huhTheme := huh.ThemeCharm()

    switch m.step {
    case StepWelcome:
        form = huh.NewForm(
            huh.NewGroup(
                huh.NewConfirm().
                    Title("Welcome to Sigma-Quant Stream").
                    Description("Ready to set up your autonomous research factory?").
                    Affirmative("Let's go").
                    Negative("Exit"),
            ),
        ).WithTheme(huhTheme)

    case StepPath:
        form = huh.NewForm(
            huh.NewGroup(
                huh.NewSelect[string]().
                    Title("Choose your path").
                    Description("This controls information density and defaults.").
                    Options(
                        huh.NewOption("Developer -- Full control, manual settings", "developer"),
                        huh.NewOption("Trader -- Auto-pilot, curated defaults", "trader"),
                    ).
                    Value(&m.userPath),
            ),
        ).WithTheme(huhTheme)

    case StepMarket:
        form = huh.NewForm(
            huh.NewGroup(
                huh.NewSelect[string]().
                    Title("Select your market").
                    Description("Determines data sources, cost models, and compliance rules.").
                    Options(
                        huh.NewOption("CME Futures (ES, NQ, YM, GC)", "futures"),
                        huh.NewOption("Crypto CEX (Binance, Bybit, OKX)", "crypto-cex"),
                        huh.NewOption("Crypto DEX (Hyperliquid)", "crypto-dex-hyperliquid"),
                    ).
                    Value(&m.market),
            ),
        ).WithTheme(huhTheme)

    case StepAPIKeys:
        // Build key fields dynamically based on market
        group := m.buildAPIKeyGroup()
        form = huh.NewForm(group).WithTheme(huhTheme)

    case StepDataDownload:
        form = huh.NewForm(
            huh.NewGroup(
                huh.NewSelect[string]().
                    Title("Data setup").
                    Description("Sample data is free and included. Live data requires API keys.").
                    Options(
                        huh.NewOption("Use sample data (recommended for first run)", "sample"),
                        huh.NewOption("Download live data now", "live"),
                    ).
                    Value(&m.dataChoice),
            ),
        ).WithTheme(huhTheme)

    case StepVerify:
        // This step runs health check, no form needed
        form = huh.NewForm(
            huh.NewGroup(
                huh.NewConfirm().
                    Title("Run health check?").
                    Description("Verifies all dependencies are installed correctly.").
                    Affirmative("Run check").
                    Negative("Skip"),
            ),
        ).WithTheme(huhTheme)

    case StepComplete:
        form = huh.NewForm(
            huh.NewGroup(
                huh.NewConfirm().
                    Title("Setup complete!").
                    Description("Run 'sigma-quant start' to launch the research factory.").
                    Affirmative("Done"),
            ),
        ).WithTheme(huhTheme)
    }

    m.activeForm = form
    return form.Init()
}

func (m *OnboardingModel) buildAPIKeyGroup() *huh.Group {
    switch m.market {
    case "futures":
        var dbKey string
        m.apiKeys["DATABENTO_API_KEY"] = ""
        return huh.NewGroup(
            huh.NewInput().
                Title("Databento API Key").
                Description("Required for CME futures data. Get one at databento.com").
                Placeholder("db-...").
                Value(&dbKey),
        )
    case "crypto-cex":
        var exchangeKey, exchangeSecret string
        return huh.NewGroup(
            huh.NewInput().
                Title("Exchange API Key").
                Description("Binance/Bybit/OKX API key for market data.").
                Value(&exchangeKey),
            huh.NewInput().
                Title("Exchange API Secret").
                Description("Keep this secret. Stored in .env locally.").
                EchoMode(huh.EchoModePassword).
                Value(&exchangeSecret),
        )
    default:
        return huh.NewGroup(
            huh.NewNote().
                Title("No API keys needed").
                Description("Hyperliquid uses public endpoints for market data."),
        )
    }
}

func (m *OnboardingModel) extractFormValues() {
    // Save state to config after each step
    switch m.step {
    case StepPath:
        m.cfg.SetUserPath(m.userPath)
    case StepMarket:
        m.cfg.SwitchProfile(m.market)
    case StepAPIKeys:
        m.cfg.WriteEnvKeys(m.apiKeys)
    case StepDataDownload:
        m.cfg.SetDataMode(m.dataChoice)
    }
}

func (m OnboardingModel) View() string {
    stepIndicator := theme.StepIndicatorView(int(m.step), m.totalSteps)
    title := theme.TitleStyle.Render(m.stepTitle())

    var formView string
    if m.activeForm != nil {
        formView = m.activeForm.View()
    }

    return lipgloss.JoinVertical(lipgloss.Left,
        "",
        stepIndicator,
        title,
        "",
        formView,
    )
}

func (m OnboardingModel) stepTitle() string {
    titles := map[OnboardingStep]string{
        StepWelcome:      "Welcome",
        StepPath:         "Choose Your Path",
        StepMarket:       "Select Market",
        StepAPIKeys:      "API Configuration",
        StepDataDownload: "Data Setup",
        StepVerify:       "Health Check",
        StepComplete:     "Ready to Launch",
    }
    return titles[m.step]
}
```

### 4.6 Strategy Browser Model (strategies)

```go
// internal/tui/models/strategy_browser.go
package models

import (
    "fmt"
    "sort"
    "strings"

    "github.com/charmbracelet/bubbles/table"
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"

    "github.com/sigma-algo/sigma-quant-cli/internal/strategy"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui/theme"
)

// SortField determines which column the table is sorted by.
type SortField int

const (
    SortByGrade SortField = iota
    SortBySharpe
    SortByWinRate
    SortByDrawdown
    SortByTrades
    SortByProfitFactor
)

// StrategyBrowserModel is an interactive, sortable strategy table.
type StrategyBrowserModel struct {
    loader     *strategy.Loader
    strategies []tui.StrategyEntry
    table      table.Model
    sortField  SortField
    sortAsc    bool
    filter     string // grade filter or empty
    width      int
    height     int
    err        error
}

// NewStrategyBrowserModel creates the strategy browser.
func NewStrategyBrowserModel(loader *strategy.Loader, filter string) StrategyBrowserModel {
    columns := []table.Column{
        {Title: "Grade", Width: 16},
        {Title: "Name", Width: 28},
        {Title: "Sharpe", Width: 8},
        {Title: "Win%", Width: 7},
        {Title: "MaxDD", Width: 8},
        {Title: "Trades", Width: 8},
        {Title: "PF", Width: 6},
        {Title: "Firms", Width: 6},
    }

    t := table.New(
        table.WithColumns(columns),
        table.WithFocused(true),
        table.WithHeight(20),
    )

    s := table.DefaultStyles()
    s.Header = s.Header.
        BorderStyle(lipgloss.NormalBorder()).
        BorderForeground(theme.MidGray).
        BorderBottom(true).
        Foreground(theme.Cyan).
        Bold(true)
    s.Selected = s.Selected.
        Foreground(theme.White).
        Background(theme.MidGray).
        Bold(true)
    t.SetStyles(s)

    return StrategyBrowserModel{
        loader:    loader,
        table:     t,
        sortField: SortBySharpe,
        sortAsc:   false, // descending by default
        filter:    filter,
    }
}

func (m StrategyBrowserModel) Init() tea.Cmd {
    return m.loadStrategies()
}

func (m StrategyBrowserModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "q", "ctrl+c":
            return m, tea.Quit
        case "s": // sort by sharpe
            m.toggleSort(SortBySharpe)
        case "w": // sort by win rate
            m.toggleSort(SortByWinRate)
        case "d": // sort by drawdown
            m.toggleSort(SortByDrawdown)
        case "t": // sort by trades
            m.toggleSort(SortByTrades)
        case "g": // sort by grade
            m.toggleSort(SortByGrade)
        case "r": // refresh
            return m, m.loadStrategies()
        }

    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height
        m.table.SetHeight(msg.Height - 8)

    case tui.StrategyListMsg:
        if msg.Err != nil {
            m.err = msg.Err
        } else {
            m.strategies = msg.Strategies
            m.rebuildTable()
        }
    }

    var cmd tea.Cmd
    m.table, cmd = m.table.Update(msg)
    return m, cmd
}

func (m *StrategyBrowserModel) toggleSort(field SortField) {
    if m.sortField == field {
        m.sortAsc = !m.sortAsc
    } else {
        m.sortField = field
        m.sortAsc = false
    }
    m.rebuildTable()
}

func (m *StrategyBrowserModel) rebuildTable() {
    filtered := m.strategies
    if m.filter != "" {
        var f []tui.StrategyEntry
        for _, s := range filtered {
            if s.Grade == m.filter {
                f = append(f, s)
            }
        }
        filtered = f
    }

    // Sort
    sort.Slice(filtered, func(i, j int) bool {
        var less bool
        switch m.sortField {
        case SortBySharpe:
            less = filtered[i].Sharpe < filtered[j].Sharpe
        case SortByWinRate:
            less = filtered[i].WinRate < filtered[j].WinRate
        case SortByDrawdown:
            less = filtered[i].MaxDrawdown < filtered[j].MaxDrawdown
        case SortByTrades:
            less = filtered[i].Trades < filtered[j].Trades
        case SortByProfitFactor:
            less = filtered[i].ProfitFactor < filtered[j].ProfitFactor
        case SortByGrade:
            less = filtered[i].Grade < filtered[j].Grade
        }
        if m.sortAsc {
            return less
        }
        return !less
    })

    rows := make([]table.Row, len(filtered))
    for i, s := range filtered {
        gradeStyle := lipgloss.NewStyle().Foreground(theme.GradeColor(s.Grade))
        rows[i] = table.Row{
            gradeStyle.Render(s.Grade),
            s.Name,
            fmt.Sprintf("%.2f", s.Sharpe),
            fmt.Sprintf("%.1f%%", s.WinRate*100),
            fmt.Sprintf("%.1f%%", s.MaxDrawdown*100),
            fmt.Sprintf("%d", s.Trades),
            fmt.Sprintf("%.2f", s.ProfitFactor),
            fmt.Sprintf("%d", len(s.PropFirmsPassed)),
        }
    }
    m.table.SetRows(rows)
}

func (m StrategyBrowserModel) loadStrategies() tea.Cmd {
    return func() tea.Msg {
        entries, err := m.loader.LoadAll()
        return tui.StrategyListMsg{Strategies: entries, Err: err}
    }
}

func (m StrategyBrowserModel) View() string {
    title := theme.TitleStyle.Render("STRATEGY BROWSER")
    countStr := theme.MutedStyle.Render(fmt.Sprintf("(%d strategies)", len(m.strategies)))

    help := strings.Join([]string{
        theme.KeyStyle.Render("s") + " sharpe",
        theme.KeyStyle.Render("w") + " win%",
        theme.KeyStyle.Render("d") + " drawdown",
        theme.KeyStyle.Render("t") + " trades",
        theme.KeyStyle.Render("g") + " grade",
        theme.KeyStyle.Render("r") + " refresh",
        theme.KeyStyle.Render("q") + " quit",
    }, "  ")

    return lipgloss.JoinVertical(lipgloss.Left,
        title+" "+countStr,
        "",
        m.table.View(),
        "",
        theme.MutedStyle.Render(" Sort: ")+help,
    )
}
```

### 4.7 Tutorial Model (tutorial)

```go
// internal/tui/models/tutorial.go
package models

import (
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"

    "github.com/sigma-algo/sigma-quant-cli/internal/python"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui/theme"
)

// TutorialStep enumerates the 6 tutorial steps.
type TutorialStep int

const (
    TutHypothesis TutorialStep = iota
    TutConvert
    TutBacktest
    TutOptimize
    TutPropFirm
    TutDeploy
)

// TutorialStepDef describes one tutorial step's content.
type TutorialStepDef struct {
    Title       string
    Subtitle    string
    Explanation string
    CodeExample string
    CodeLang    string
    CanExecute  bool   // Can invoke real Python backend
    ExecuteCmd  string // Python command to run
}

var tutorialSteps = []TutorialStepDef{
    {
        Title:       "HYPOTHESIS",
        Subtitle:    "Every strategy starts with a testable idea",
        Explanation: "A hypothesis answers three questions:\n1. What edge does this exploit?\n2. Who is on the other side of the trade?\n3. Why should this inefficiency persist?",
        CodeExample: `{
  "id": "hyp-example-001",
  "name": "Funding Rate Mean Reversion",
  "edge": "When perp funding > 0.05%, price reverts",
  "counterparty": "Over-leveraged momentum chasers",
  "expected_metrics": {
    "target_sharpe": 1.5,
    "max_acceptable_drawdown": 0.15
  }
}`,
        CodeLang:   "json",
        CanExecute: false,
    },
    {
        Title:       "CONVERT",
        Subtitle:    "PineScript to Python translation",
        Explanation: "The converter translates TradingView indicators into pandas-ta functions with proper signal generation.",
        CodeExample: `class FundingReversion(BaseStrategy):
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["funding_zscore"] = zscore(df["funding_rate"], window=168)
        df["signal"] = np.where(df["funding_zscore"] < -2, 1,
                       np.where(df["funding_zscore"] > 2, -1, 0))
        return df`,
        CodeLang:   "python",
        CanExecute: false,
    },
    {
        Title:       "BACKTEST",
        Subtitle:    "Walk-forward validation with cost modeling",
        Explanation: "Walk-forward optimization splits data into in-sample and out-of-sample windows.\nOverfitting gates reject strategies with Sharpe > 3.0, WR > 80%, or < 100 trades.",
        CodeExample: `python lib/backtest_runner.py \
  --strategy FundingReversion \
  --bars 5000 \
  --timeframe 5m \
  --walk-forward \
  --costs always`,
        CodeLang:   "bash",
        CanExecute: true,
        ExecuteCmd: "lib/backtest_runner.py --strategy example --dry-run",
    },
    {
        Title:       "OPTIMIZE",
        Subtitle:    "Coarse grid search with robustness testing",
        Explanation: "Parameters are tested on a coarse grid first.\nEvery result must survive +/-20% perturbation.\nKnife-edge optima are rejected.",
        CodeExample: `# Coarse grid
param_grid = {
    "zscore_window": [84, 168, 336],
    "entry_threshold": [1.5, 2.0, 2.5],
    "exit_threshold": [0.5, 1.0],
}
# Perturbation test: must remain profitable at +/-20%`,
        CodeLang:   "python",
        CanExecute: false,
    },
    {
        Title:       "PROP FIRM VALIDATION",
        Subtitle:    "Test against 14 prop firm rule sets",
        Explanation: "Each strategy is tested against real prop firm rules:\n- Daily loss limits\n- Max drawdown\n- Minimum trading days\n- Trailing drawdown (where applicable)",
        CodeExample: `python scripts/prop-firm-validator.py \
  --strategy FundingReversion \
  --account-sizes 50000,100000 \
  --firms all`,
        CodeLang:   "bash",
        CanExecute: true,
        ExecuteCmd: "scripts/prop-firm-validator.py --dry-run",
    },
    {
        Title:       "DEPLOY",
        Subtitle:    "Export to Freqtrade for paper trading",
        Explanation: "Validated strategies are converted to Freqtrade IStrategy format and deployed to a paper trading bot.",
        CodeExample: `sigma-quant deploy FundingReversion --dry-run`,
        CodeLang:   "bash",
        CanExecute: false,
    },
}

// TutorialModel drives the 6-step interactive tutorial.
type TutorialModel struct {
    step       int
    totalSteps int
    pyRunner   *python.Runner

    // Execution state
    executing bool
    output    string
    err       error

    width  int
    height int
}

func NewTutorialModel(pyRunner *python.Runner) TutorialModel {
    return TutorialModel{
        step:       0,
        totalSteps: len(tutorialSteps),
        pyRunner:   pyRunner,
    }
}

func (m TutorialModel) Init() tea.Cmd {
    return nil
}

func (m TutorialModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "q", "ctrl+c":
            return m, tea.Quit
        case "right", "l", "enter", "n":
            if m.step < m.totalSteps-1 {
                m.step++
                m.output = ""
                m.executing = false
            }
        case "left", "h", "p":
            if m.step > 0 {
                m.step--
                m.output = ""
                m.executing = false
            }
        case "x": // execute
            step := tutorialSteps[m.step]
            if step.CanExecute && !m.executing {
                m.executing = true
                return m, m.executeStep(step.ExecuteCmd)
            }
        }

    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height

    case pythonOutputMsg:
        m.executing = false
        m.output = msg.output
        m.err = msg.err
    }

    return m, nil
}

type pythonOutputMsg struct {
    output string
    err    error
}

func (m TutorialModel) executeStep(cmd string) tea.Cmd {
    return func() tea.Msg {
        out, err := m.pyRunner.RunScript(cmd)
        return pythonOutputMsg{output: out, err: err}
    }
}

func (m TutorialModel) View() string {
    step := tutorialSteps[m.step]

    stepBar := theme.StepIndicatorView(m.step, m.totalSteps)
    title := theme.TitleStyle.Render(step.Title)
    subtitle := theme.SubtitleStyle.Render(step.Subtitle)

    explanation := theme.BodyStyle.Render(step.Explanation)
    codeBlock := theme.CodeBlockStyle.Render(step.CodeExample)

    var execHint string
    if step.CanExecute {
        execHint = theme.KeyStyle.Render("x") + " " +
            theme.MutedStyle.Render("execute this step")
    }

    var outputBlock string
    if m.output != "" {
        outputBlock = theme.PanelStyle.Render(m.output)
    }

    nav := theme.MutedStyle.Render("  h/left  previous  |  l/right  next  |  q  quit")

    return lipgloss.JoinVertical(lipgloss.Left,
        stepBar,
        title,
        subtitle,
        "",
        explanation,
        "",
        codeBlock,
        "",
        execHint,
        outputBlock,
        "",
        nav,
    )
}
```

### 4.8 Reusable Components

```go
// internal/tui/components/step_indicator.go
package components

import (
    "strings"

    "github.com/charmbracelet/lipgloss"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui/theme"
)

// StepIndicatorView renders step dots: [*] [*] [ ] [ ] [ ] [ ]
func StepIndicatorView(current, total int) string {
    var parts []string
    for i := 0; i < total; i++ {
        if i < current {
            parts = append(parts, lipgloss.NewStyle().
                Foreground(theme.Cyan).Render("[*]"))
        } else if i == current {
            parts = append(parts, lipgloss.NewStyle().
                Foreground(theme.Cyan).Bold(true).Render("[>]"))
        } else {
            parts = append(parts, lipgloss.NewStyle().
                Foreground(theme.MidGray).Render("[ ]"))
        }
    }
    return strings.Join(parts, " ")
}
```

```go
// internal/tui/components/worker_card.go
package components

import (
    "fmt"
    "time"

    "github.com/charmbracelet/lipgloss"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui/theme"
)

// WorkerCardView renders a single worker status card.
func WorkerCardView(w tui.WorkerState, width int) string {
    style := theme.PanelStyle.Width(width)

    nameStyle := theme.BrightStyle
    var status string
    if w.Running {
        status = theme.RunningStyle.Render("RUNNING")
    } else {
        status = theme.StoppedStyle.Render("STOPPED")
    }

    header := nameStyle.Render(w.Name) + "  " + status

    var details string
    if w.Running {
        details = fmt.Sprintf(
            "%s tasks | %s errors | up %s",
            theme.BodyStyle.Render(fmt.Sprintf("%d", w.TaskCount)),
            theme.ErrorStyle.Render(fmt.Sprintf("%d", w.Errors)),
            theme.MutedStyle.Render(w.Uptime.Truncate(time.Second).String()),
        )
    } else {
        details = theme.MutedStyle.Render("not running")
    }

    lastLine := ""
    if w.LastOutput != "" {
        truncated := w.LastOutput
        if len(truncated) > width-8 {
            truncated = truncated[:width-11] + "..."
        }
        lastLine = theme.MutedStyle.Render(truncated)
    }

    return style.Render(
        header + "\n" + details + "\n" + lastLine,
    )
}
```

---

## 5. Agent Orchestration Layer

The agent orchestration layer manages the lifecycle of Claude Code agents running in tmux panes. It replaces the existing bash scripts (`quant-ralph.sh`, `tmux-quant-launcher.sh`, `quant-swarm-launcher.sh`) with a structured Go implementation.

### 5.1 Core Types

```go
// internal/agent/types.go
package agent

import "time"

// WorkerType is one of the 4 pipeline workers.
type WorkerType string

const (
    WorkerResearcher WorkerType = "researcher"
    WorkerConverter  WorkerType = "converter"
    WorkerBacktester WorkerType = "backtester"
    WorkerOptimizer  WorkerType = "optimizer"
)

// AllWorkers returns the canonical worker order.
func AllWorkers() []WorkerType {
    return []WorkerType{
        WorkerResearcher,
        WorkerConverter,
        WorkerBacktester,
        WorkerOptimizer,
    }
}

// WorkerState tracks the current state of a single worker pane.
type WorkerState struct {
    Type       WorkerType
    PaneIndex  int
    Running    bool
    PID        int
    StartedAt  time.Time
    LastOutput string
    TaskCount  int
    ErrorCount int
    Restarts   int           // How many times ralph has restarted this worker
    LastError  string
    Phase      WorkerPhase
}

// WorkerPhase tracks where in the ralph loop a worker is.
type WorkerPhase string

const (
    PhaseIdle       WorkerPhase = "idle"
    PhaseStarting   WorkerPhase = "starting"
    PhaseRunning    WorkerPhase = "running"
    PhaseTimeout    WorkerPhase = "timeout"
    PhaseStopping   WorkerPhase = "stopping"
    PhaseFailed     WorkerPhase = "failed"
    PhaseCooldown   WorkerPhase = "cooldown"
)

// SessionConfig holds settings for a tmux session launch.
type SessionConfig struct {
    SessionName    string
    ProjectRoot    string
    Workers        []WorkerType
    PromptDir      string        // Path to prompts/ directory
    SessionTimeout time.Duration // Per-session timeout (from config.json)
    BudgetCap      float64       // Max cost per session
    Mode           string        // "research" or "production"
}

// RalphConfig controls the Ralph loop behavior.
type RalphConfig struct {
    SessionTimeout    time.Duration // How long before restarting a worker
    CooldownDuration  time.Duration // Pause between restarts
    MaxConsecutiveFail int          // 3-strike rule
    MaxTotalRestarts   int          // Safety cap on total restarts
    HealthCheckInterval time.Duration
}
```

### 5.2 tmux Operations

```go
// internal/agent/tmux.go
package agent

import (
    "fmt"
    "os/exec"
    "strconv"
    "strings"
    "time"
)

// TmuxClient wraps tmux CLI operations.
type TmuxClient struct {
    tmuxPath string // Path to tmux binary
}

// NewTmuxClient creates a tmux client, verifying tmux is installed.
func NewTmuxClient() (*TmuxClient, error) {
    path, err := exec.LookPath("tmux")
    if err != nil {
        return nil, fmt.Errorf("tmux not found: install with 'brew install tmux'")
    }
    return &TmuxClient{tmuxPath: path}, nil
}

// SessionExists checks if a named tmux session exists.
func (t *TmuxClient) SessionExists(name string) bool {
    cmd := exec.Command(t.tmuxPath, "has-session", "-t", name)
    return cmd.Run() == nil
}

// CreateSession creates a new tmux session with the given name.
func (t *TmuxClient) CreateSession(name, windowName, initialCmd string, cwd string) error {
    args := []string{"new-session", "-d", "-s", name, "-n", windowName}
    if initialCmd != "" {
        args = append(args, initialCmd)
    }
    cmd := exec.Command(t.tmuxPath, args...)
    cmd.Dir = cwd
    return cmd.Run()
}

// SplitPane adds a new pane to an existing session window.
func (t *TmuxClient) SplitPane(session, window string, horizontal bool, cmd string) error {
    splitFlag := "-v"
    if horizontal {
        splitFlag = "-h"
    }
    args := []string{"split-window", splitFlag, "-t", fmt.Sprintf("%s:%s", session, window)}
    if cmd != "" {
        args = append(args, cmd)
    }
    return exec.Command(t.tmuxPath, args...).Run()
}

// TileLayout applies the "tiled" layout to distribute panes evenly.
func (t *TmuxClient) TileLayout(session, window string) error {
    return exec.Command(t.tmuxPath, "select-layout", "-t",
        fmt.Sprintf("%s:%s", session, window), "tiled").Run()
}

// KillSession destroys a tmux session.
func (t *TmuxClient) KillSession(name string) error {
    return exec.Command(t.tmuxPath, "kill-session", "-t", name).Run()
}

// SendKeys sends keystrokes to a specific pane.
func (t *TmuxClient) SendKeys(session string, paneIndex int, keys string) error {
    target := fmt.Sprintf("%s:%d", session, paneIndex)
    return exec.Command(t.tmuxPath, "send-keys", "-t", target, keys, "Enter").Run()
}

// GetPanePIDs returns the PIDs of all panes in a session.
func (t *TmuxClient) GetPanePIDs(session string) ([]int, error) {
    cmd := exec.Command(t.tmuxPath, "list-panes", "-t", session,
        "-F", "#{pane_pid}")
    out, err := cmd.Output()
    if err != nil {
        return nil, err
    }

    var pids []int
    for _, line := range strings.Split(strings.TrimSpace(string(out)), "\n") {
        if pid, err := strconv.Atoi(strings.TrimSpace(line)); err == nil {
            pids = append(pids, pid)
        }
    }
    return pids, nil
}

// CapturePaneOutput captures the last N lines from a pane.
func (t *TmuxClient) CapturePaneOutput(session string, paneIndex int, lines int) (string, error) {
    target := fmt.Sprintf("%s:%d", session, paneIndex)
    startLine := fmt.Sprintf("-%d", lines)
    cmd := exec.Command(t.tmuxPath, "capture-pane", "-t", target,
        "-p", "-S", startLine)
    out, err := cmd.Output()
    if err != nil {
        return "", err
    }
    return strings.TrimSpace(string(out)), nil
}

// IsPaneAlive checks if a pane's process is still running.
func (t *TmuxClient) IsPaneAlive(session string, paneIndex int) bool {
    target := fmt.Sprintf("%s:%d", session, paneIndex)
    cmd := exec.Command(t.tmuxPath, "list-panes", "-t", target,
        "-F", "#{pane_dead}")
    out, err := cmd.Output()
    if err != nil {
        return false
    }
    return strings.TrimSpace(string(out)) == "0"
}
```

### 5.3 Agent Manager

```go
// internal/agent/manager.go
package agent

import (
    "fmt"
    "os"
    "path/filepath"
    "sync"
    "syscall"
    "time"

    "github.com/sigma-algo/sigma-quant-cli/internal/config"
)

const defaultSessionName = "sigma-quant"

// Manager coordinates agent lifecycle across tmux panes.
type Manager struct {
    tmux   *TmuxClient
    cfg    *config.Config
    states map[WorkerType]*WorkerState
    mu     sync.RWMutex
}

// NewManager creates an agent manager.
func NewManager(cfg *config.Config) *Manager {
    tmux, _ := NewTmuxClient() // Error handled at command level
    return &Manager{
        tmux:   tmux,
        cfg:    cfg,
        states: make(map[WorkerType]*WorkerState),
    }
}

// StartAll launches all 4 workers in a single tmux session.
func (m *Manager) StartAll() error {
    if m.tmux == nil {
        return fmt.Errorf("tmux not available")
    }

    if m.tmux.SessionExists(defaultSessionName) {
        return fmt.Errorf("session '%s' already running; use 'sigma-quant stop' first",
            defaultSessionName)
    }

    workers := AllWorkers()
    projectRoot := m.cfg.ProjectRoot()

    // Create session with first worker
    claudeCmd := m.buildClaudeCommand(workers[0])
    if err := m.tmux.CreateSession(defaultSessionName, "workers", claudeCmd, projectRoot); err != nil {
        return fmt.Errorf("failed to create tmux session: %w", err)
    }

    m.mu.Lock()
    m.states[workers[0]] = &WorkerState{
        Type:      workers[0],
        PaneIndex: 0,
        Running:   true,
        StartedAt: time.Now(),
        Phase:     PhaseStarting,
    }
    m.mu.Unlock()

    // Split panes for remaining workers
    for i, w := range workers[1:] {
        cmd := m.buildClaudeCommand(w)
        if err := m.tmux.SplitPane(defaultSessionName, "workers", false, cmd); err != nil {
            return fmt.Errorf("failed to create pane for %s: %w", w, err)
        }

        m.mu.Lock()
        m.states[w] = &WorkerState{
            Type:      w,
            PaneIndex: i + 1,
            Running:   true,
            StartedAt: time.Now(),
            Phase:     PhaseStarting,
        }
        m.mu.Unlock()
    }

    // Apply tiled layout
    return m.tmux.TileLayout(defaultSessionName, "workers")
}

// StartWorker launches a single worker in its own tmux session.
func (m *Manager) StartWorker(name string) error {
    wt := WorkerType(name)
    sessionName := fmt.Sprintf("quant-%s", name)

    if m.tmux.SessionExists(sessionName) {
        return fmt.Errorf("session '%s' already running", sessionName)
    }

    claudeCmd := m.buildClaudeCommand(wt)
    return m.tmux.CreateSession(sessionName, name, claudeCmd, m.cfg.ProjectRoot())
}

// StopAll gracefully shuts down all workers.
func (m *Manager) StopAll(force bool) error {
    stopped := false

    // Main session
    if m.tmux.SessionExists(defaultSessionName) {
        if !force {
            // Send SIGTERM to each pane process
            pids, err := m.tmux.GetPanePIDs(defaultSessionName)
            if err == nil {
                for _, pid := range pids {
                    syscall.Kill(pid, syscall.SIGTERM)
                }
                time.Sleep(3 * time.Second) // Grace period
            }
        }
        m.tmux.KillSession(defaultSessionName)
        stopped = true
    }

    // Individual sessions
    for _, w := range AllWorkers() {
        sessionName := fmt.Sprintf("quant-%s", string(w))
        if m.tmux.SessionExists(sessionName) {
            m.tmux.KillSession(sessionName)
            stopped = true
        }
    }

    if !stopped {
        return fmt.Errorf("no active sessions found")
    }
    return nil
}

// GetWorkerStates returns current state of all workers.
func (m *Manager) GetWorkerStates() []WorkerState {
    m.mu.RLock()
    defer m.mu.RUnlock()

    var states []WorkerState
    for _, w := range AllWorkers() {
        if s, ok := m.states[w]; ok {
            // Refresh running status from tmux
            s.Running = m.tmux.IsPaneAlive(defaultSessionName, s.PaneIndex)
            if s.Running {
                s.Phase = PhaseRunning
                // Capture last output line
                if out, err := m.tmux.CapturePaneOutput(
                    defaultSessionName, s.PaneIndex, 1); err == nil {
                    s.LastOutput = out
                }
            } else {
                s.Phase = PhaseFailed
            }
            states = append(states, *s)
        } else {
            // Worker not tracked yet, check if tmux has it
            running := m.tmux.SessionExists(defaultSessionName) &&
                m.tmux.IsPaneAlive(defaultSessionName, int(workerIndex(w)))
            states = append(states, WorkerState{
                Type:      w,
                PaneIndex: int(workerIndex(w)),
                Running:   running,
                Phase:     PhaseIdle,
            })
        }
    }
    return states
}

// buildClaudeCommand constructs the claude CLI invocation for a worker.
func (m *Manager) buildClaudeCommand(w WorkerType) string {
    promptPath := filepath.Join(m.cfg.ProjectRoot(), "prompts", string(w)+".md")

    // Check if prompt file exists
    if _, err := os.Stat(promptPath); err != nil {
        // Fallback: just launch claude with the worker name as context
        return fmt.Sprintf("claude --dangerously-skip-permissions -p 'You are the %s worker. Read CLAUDE.md for your mission.'", w)
    }

    return fmt.Sprintf("claude --dangerously-skip-permissions --resume-session-id quant-%s < %s",
        w, promptPath)
}

func workerIndex(w WorkerType) int {
    for i, wt := range AllWorkers() {
        if wt == w {
            return i
        }
    }
    return -1
}
```

### 5.4 Ralph Loop (Spawn-Timeout-Restart)

The Ralph loop is the core autonomous execution pattern. It spawns a Claude Code agent, monitors it, and restarts it when the session times out or crashes.

```go
// internal/agent/ralph.go
package agent

import (
    "context"
    "fmt"
    "log"
    "time"
)

// RalphLoop runs the spawn-monitor-restart loop for a single worker.
// This is meant to run as a goroutine.
func (m *Manager) RalphLoop(ctx context.Context, worker WorkerType, rcfg RalphConfig) {
    consecutiveFailures := 0
    totalRestarts := 0

    for {
        select {
        case <-ctx.Done():
            log.Printf("[ralph/%s] Context cancelled, stopping", worker)
            return
        default:
        }

        // 3-strike rule
        if consecutiveFailures >= rcfg.MaxConsecutiveFail {
            log.Printf("[ralph/%s] 3 consecutive failures, entering cooldown", worker)
            m.updatePhase(worker, PhaseCooldown)

            select {
            case <-time.After(rcfg.CooldownDuration * 3): // Triple cooldown after 3 strikes
                consecutiveFailures = 0
            case <-ctx.Done():
                return
            }
        }

        // Safety cap
        if rcfg.MaxTotalRestarts > 0 && totalRestarts >= rcfg.MaxTotalRestarts {
            log.Printf("[ralph/%s] Max total restarts (%d) reached, stopping",
                worker, rcfg.MaxTotalRestarts)
            m.updatePhase(worker, PhaseFailed)
            return
        }

        // Phase 1: Start the worker
        m.updatePhase(worker, PhaseStarting)
        err := m.StartWorker(string(worker))
        if err != nil {
            log.Printf("[ralph/%s] Failed to start: %v", worker, err)
            consecutiveFailures++
            totalRestarts++
            m.updatePhase(worker, PhaseFailed)

            select {
            case <-time.After(rcfg.CooldownDuration):
            case <-ctx.Done():
                return
            }
            continue
        }

        // Phase 2: Monitor until timeout or crash
        m.updatePhase(worker, PhaseRunning)
        sessionStart := time.Now()
        ticker := time.NewTicker(rcfg.HealthCheckInterval)

        workerDone := false
        for !workerDone {
            select {
            case <-ctx.Done():
                ticker.Stop()
                return

            case <-ticker.C:
                // Check if still alive
                sessionName := fmt.Sprintf("quant-%s", worker)
                if !m.tmux.SessionExists(sessionName) {
                    log.Printf("[ralph/%s] Session died", worker)
                    consecutiveFailures++
                    workerDone = true
                    continue
                }

                // Check timeout
                if time.Since(sessionStart) > rcfg.SessionTimeout {
                    log.Printf("[ralph/%s] Session timeout (%s), restarting",
                        worker, rcfg.SessionTimeout)
                    m.tmux.KillSession(sessionName)
                    consecutiveFailures = 0 // Timeout is not a failure
                    workerDone = true
                    continue
                }

                // Update task count from pane output
                m.refreshWorkerStats(worker)
            }
        }

        ticker.Stop()
        totalRestarts++

        // Phase 3: Cooldown before restart
        m.updatePhase(worker, PhaseCooldown)
        select {
        case <-time.After(rcfg.CooldownDuration):
        case <-ctx.Done():
            return
        }
    }
}

func (m *Manager) updatePhase(worker WorkerType, phase WorkerPhase) {
    m.mu.Lock()
    defer m.mu.Unlock()
    if s, ok := m.states[worker]; ok {
        s.Phase = phase
    }
}

func (m *Manager) refreshWorkerStats(worker WorkerType) {
    m.mu.Lock()
    defer m.mu.Unlock()
    if s, ok := m.states[worker]; ok {
        sessionName := fmt.Sprintf("quant-%s", worker)
        if out, err := m.tmux.CapturePaneOutput(sessionName, 0, 1); err == nil {
            s.LastOutput = out
        }
        s.Running = m.tmux.IsPaneAlive(sessionName, 0)
    }
}
```

### 5.5 Log Capture

```go
// internal/agent/log.go
package agent

import (
    "fmt"
    "os"
    "path/filepath"
    "strings"
    "time"
)

// LogCapture manages log file writing for each worker.
type LogCapture struct {
    logDir string
    files  map[WorkerType]*os.File
}

// NewLogCapture creates a log capture system.
func NewLogCapture(projectRoot string) *LogCapture {
    logDir := filepath.Join(projectRoot, "output", "research-logs")
    os.MkdirAll(logDir, 0755)
    return &LogCapture{
        logDir: logDir,
        files:  make(map[WorkerType]*os.File),
    }
}

// CaptureSnapshot captures current pane output and appends to log file.
func (lc *LogCapture) CaptureSnapshot(tmux *TmuxClient, session string, worker WorkerType, paneIndex int) error {
    output, err := tmux.CapturePaneOutput(session, paneIndex, 50)
    if err != nil {
        return fmt.Errorf("capture failed: %w", err)
    }

    if strings.TrimSpace(output) == "" {
        return nil
    }

    f, ok := lc.files[worker]
    if !ok {
        filename := fmt.Sprintf("%s-%s.log", worker,
            time.Now().Format("2006-01-02T15-04-05"))
        path := filepath.Join(lc.logDir, filename)
        f, err = os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
        if err != nil {
            return err
        }
        lc.files[worker] = f
    }

    timestamp := time.Now().Format("15:04:05")
    _, err = fmt.Fprintf(f, "\n--- %s ---\n%s\n", timestamp, output)
    return err
}

// Close closes all open log files.
func (lc *LogCapture) Close() {
    for _, f := range lc.files {
        f.Close()
    }
}
```

---

## 6. Python Integration Layer

The Go CLI delegates computation-heavy work to existing Python scripts. This layer provides structured subprocess management with output parsing and error handling.

### 6.1 Generic Python Runner

```go
// internal/python/runner.go
package python

import (
    "bytes"
    "context"
    "fmt"
    "os"
    "os/exec"
    "path/filepath"
    "strings"
    "time"
)

// Runner executes Python scripts with structured output capture.
type Runner struct {
    pythonPath  string // Path to python3 binary
    projectRoot string // Project root for relative script paths
    envVars     map[string]string
    timeout     time.Duration
}

// NewRunner creates a Python runner, locating the interpreter.
func NewRunner(projectRoot string) (*Runner, error) {
    // Check for venv first, then system python
    candidates := []string{
        filepath.Join(projectRoot, ".venv", "bin", "python3"),
        filepath.Join(projectRoot, ".venv", "bin", "python"),
        "python3",
        "python",
    }

    var pythonPath string
    for _, c := range candidates {
        if p, err := exec.LookPath(c); err == nil {
            pythonPath = p
            break
        }
    }

    if pythonPath == "" {
        return nil, fmt.Errorf("python3 not found; install Python 3.11+")
    }

    return &Runner{
        pythonPath:  pythonPath,
        projectRoot: projectRoot,
        envVars:     make(map[string]string),
        timeout:     5 * time.Minute,
    }, nil
}

// SetEnv adds an environment variable for all script executions.
func (r *Runner) SetEnv(key, value string) {
    r.envVars[key] = value
}

// LoadEnvFile reads .env and populates environment variables.
func (r *Runner) LoadEnvFile() error {
    envPath := filepath.Join(r.projectRoot, ".env")
    data, err := os.ReadFile(envPath)
    if err != nil {
        if os.IsNotExist(err) {
            return nil // .env is optional
        }
        return err
    }

    for _, line := range strings.Split(string(data), "\n") {
        line = strings.TrimSpace(line)
        if line == "" || strings.HasPrefix(line, "#") {
            continue
        }
        parts := strings.SplitN(line, "=", 2)
        if len(parts) == 2 {
            key := strings.TrimSpace(parts[0])
            val := strings.Trim(strings.TrimSpace(parts[1]), `"'`)
            r.envVars[key] = val
        }
    }
    return nil
}

// RunResult contains the output of a Python script execution.
type RunResult struct {
    Stdout   string
    Stderr   string
    ExitCode int
    Duration time.Duration
}

// RunScript executes a Python script with arguments.
func (r *Runner) RunScript(scriptPath string, args ...string) (*RunResult, error) {
    // Resolve relative paths against project root
    if !filepath.IsAbs(scriptPath) {
        scriptPath = filepath.Join(r.projectRoot, scriptPath)
    }

    ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
    defer cancel()

    cmdArgs := append([]string{scriptPath}, args...)
    cmd := exec.CommandContext(ctx, r.pythonPath, cmdArgs...)
    cmd.Dir = r.projectRoot

    // Build environment
    cmd.Env = os.Environ()
    for k, v := range r.envVars {
        cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
    }

    var stdout, stderr bytes.Buffer
    cmd.Stdout = &stdout
    cmd.Stderr = &stderr

    start := time.Now()
    err := cmd.Run()
    duration := time.Since(start)

    result := &RunResult{
        Stdout:   stdout.String(),
        Stderr:   stderr.String(),
        Duration: duration,
    }

    if err != nil {
        if exitErr, ok := err.(*exec.ExitError); ok {
            result.ExitCode = exitErr.ExitCode()
        } else {
            return result, fmt.Errorf("execution failed: %w", err)
        }
    }

    return result, nil
}

// RunScriptStreaming executes a script and streams output line by line.
// The callback is called for each line of stdout.
func (r *Runner) RunScriptStreaming(
    ctx context.Context,
    scriptPath string,
    onLine func(line string),
    args ...string,
) error {
    if !filepath.IsAbs(scriptPath) {
        scriptPath = filepath.Join(r.projectRoot, scriptPath)
    }

    cmdArgs := append([]string{scriptPath}, args...)
    cmd := exec.CommandContext(ctx, r.pythonPath, cmdArgs...)
    cmd.Dir = r.projectRoot

    cmd.Env = os.Environ()
    for k, v := range r.envVars {
        cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
    }

    pipe, err := cmd.StdoutPipe()
    if err != nil {
        return err
    }

    if err := cmd.Start(); err != nil {
        return err
    }

    buf := make([]byte, 4096)
    for {
        n, readErr := pipe.Read(buf)
        if n > 0 {
            lines := strings.Split(string(buf[:n]), "\n")
            for _, line := range lines {
                if line != "" {
                    onLine(line)
                }
            }
        }
        if readErr != nil {
            break
        }
    }

    return cmd.Wait()
}
```

### 6.2 Backtest Integration

```go
// internal/python/backtest.go
package python

import (
    "encoding/json"
    "fmt"
    "strings"
)

// BacktestRequest defines parameters for a backtest run.
type BacktestRequest struct {
    Strategy    string `json:"strategy"`
    Bars        int    `json:"bars"`
    Timeframe   string `json:"timeframe"`
    WalkForward bool   `json:"walk_forward"`
    CostsAlways bool   `json:"costs_always"`
    Profile     string `json:"profile"` // "futures", "crypto-cex", etc.
}

// BacktestResult is the parsed output of backtest_runner.py.
type BacktestResult struct {
    Strategy     string  `json:"strategy"`
    Sharpe       float64 `json:"sharpe_ratio"`
    WinRate      float64 `json:"win_rate"`
    MaxDrawdown  float64 `json:"max_drawdown"`
    TotalTrades  int     `json:"total_trades"`
    ProfitFactor float64 `json:"profit_factor"`
    OOSDecay     float64 `json:"oos_decay"`
    Grade        string  `json:"grade"`
    Passed       bool    `json:"passed"`
    RejectReason string  `json:"reject_reason,omitempty"`
}

// RunBacktest invokes lib/backtest_runner.py and parses the result.
func (r *Runner) RunBacktest(req BacktestRequest) (*BacktestResult, error) {
    args := []string{
        "--strategy", req.Strategy,
        "--bars", fmt.Sprintf("%d", req.Bars),
        "--timeframe", req.Timeframe,
        "--profile", req.Profile,
    }

    if req.WalkForward {
        args = append(args, "--walk-forward")
    }
    if req.CostsAlways {
        args = append(args, "--costs", "always")
    }

    result, err := r.RunScript("lib/backtest_runner.py", args...)
    if err != nil {
        return nil, fmt.Errorf("backtest execution failed: %w", err)
    }

    if result.ExitCode != 0 {
        return nil, fmt.Errorf("backtest failed (exit %d): %s",
            result.ExitCode, result.Stderr)
    }

    // Parse JSON from the last line of stdout (backtest_runner outputs JSON)
    lines := strings.Split(strings.TrimSpace(result.Stdout), "\n")
    if len(lines) == 0 {
        return nil, fmt.Errorf("no output from backtest")
    }

    // Find the JSON line (may be preceded by log output)
    var jsonLine string
    for i := len(lines) - 1; i >= 0; i-- {
        if strings.HasPrefix(strings.TrimSpace(lines[i]), "{") {
            jsonLine = lines[i]
            break
        }
    }

    if jsonLine == "" {
        return nil, fmt.Errorf("no JSON output found in backtest results")
    }

    var btResult BacktestResult
    if err := json.Unmarshal([]byte(jsonLine), &btResult); err != nil {
        return nil, fmt.Errorf("failed to parse backtest output: %w", err)
    }

    return &btResult, nil
}
```

### 6.3 Data Download Integration

```go
// internal/python/data.go
package python

import (
    "context"
    "fmt"
)

// DataDownloadRequest defines parameters for market data download.
type DataDownloadRequest struct {
    Provider  string // "databento", "ccxt", "hyperliquid"
    Exchange  string // For crypto: "binance", "bybit", etc.
    Symbol    string // "ES", "BTCUSDT", etc.
    Timeframe string // "5m", "1h", etc.
    Bars      int    // Number of bars to download
}

// DownloadData invokes scripts/download-data.py with progress streaming.
func (r *Runner) DownloadData(
    ctx context.Context,
    req DataDownloadRequest,
    onProgress func(line string),
) error {
    args := []string{
        "--provider", req.Provider,
        "--symbol", req.Symbol,
        "--timeframe", req.Timeframe,
        "--bars", fmt.Sprintf("%d", req.Bars),
    }

    if req.Exchange != "" {
        args = append(args, "--exchange", req.Exchange)
    }

    return r.RunScriptStreaming(ctx, "scripts/download-data.py", onProgress, args...)
}
```

### 6.4 Prop Firm Validation Integration

```go
// internal/python/propfirm.go
package python

import (
    "encoding/json"
    "fmt"
    "strings"
)

// PropFirmResult is the output of prop-firm-validator.py.
type PropFirmResult struct {
    Strategy    string           `json:"strategy"`
    FirmResults []FirmTestResult `json:"firm_results"`
    TotalPassed int              `json:"total_passed"`
    TotalFirms  int              `json:"total_firms"`
}

// FirmTestResult is one firm's pass/fail result.
type FirmTestResult struct {
    Firm         string  `json:"firm"`
    Passed       bool    `json:"passed"`
    MaxDrawdown  float64 `json:"max_drawdown"`
    DailyLoss    float64 `json:"daily_loss"`
    FailReason   string  `json:"fail_reason,omitempty"`
}

// RunPropFirmValidation invokes scripts/prop-firm-validator.py.
func (r *Runner) RunPropFirmValidation(strategy string, accountSizes []int) (*PropFirmResult, error) {
    sizeStrs := make([]string, len(accountSizes))
    for i, s := range accountSizes {
        sizeStrs[i] = fmt.Sprintf("%d", s)
    }

    args := []string{
        "--strategy", strategy,
        "--account-sizes", strings.Join(sizeStrs, ","),
        "--firms", "all",
        "--output", "json",
    }

    result, err := r.RunScript("scripts/prop-firm-validator.py", args...)
    if err != nil {
        return nil, err
    }

    lines := strings.Split(strings.TrimSpace(result.Stdout), "\n")
    var jsonLine string
    for i := len(lines) - 1; i >= 0; i-- {
        if strings.HasPrefix(strings.TrimSpace(lines[i]), "{") {
            jsonLine = lines[i]
            break
        }
    }

    if jsonLine == "" {
        return nil, fmt.Errorf("no JSON output from prop firm validator")
    }

    var pfResult PropFirmResult
    if err := json.Unmarshal([]byte(jsonLine), &pfResult); err != nil {
        return nil, fmt.Errorf("failed to parse prop firm results: %w", err)
    }

    return &pfResult, nil
}
```

---

## 7. Configuration Management (Viper)

### 7.1 Config Types

```go
// internal/config/types.go
package config

import "time"

// Config is the top-level configuration structure, mirroring config.json.
type Config struct {
    Name        string `json:"name" mapstructure:"name"`
    Version     string `json:"version" mapstructure:"version"`
    Description string `json:"description" mapstructure:"description"`

    ActiveProfile string                    `json:"activeProfile" mapstructure:"activeProfile"`
    MarketProfiles map[string]MarketProfile `json:"marketProfiles" mapstructure:"marketProfiles"`

    Defaults  Defaults            `json:"defaults" mapstructure:"defaults"`
    Modes     map[string]ModeConfig `json:"modes" mapstructure:"modes"`
    Workers   WorkersConfig       `json:"workers" mapstructure:"workers"`
    Queues    QueuesConfig        `json:"queues" mapstructure:"queues"`
    Patterns  PatternsConfig      `json:"patterns" mapstructure:"patterns"`
    Validation ValidationConfig   `json:"validation" mapstructure:"validation"`
    Output    OutputConfig        `json:"output" mapstructure:"output"`
    Recovery  RecoveryConfig      `json:"recovery" mapstructure:"recovery"`
    Notifications NotifyConfig    `json:"notifications" mapstructure:"notifications"`

    // Computed at load time (not in JSON)
    projectRoot string
    userPath    string // "developer" or "trader"
}

// MarketProfile references a profile file.
type MarketProfile struct {
    Path        string `json:"path" mapstructure:"path"`
    DisplayName string `json:"displayName" mapstructure:"displayName"`
    MarketType  string `json:"marketType" mapstructure:"marketType"`
}

// Defaults are the top-level default settings.
type Defaults struct {
    Panes    int    `json:"panes" mapstructure:"panes"`
    Mode     string `json:"mode" mapstructure:"mode"`
    MaxHours int    `json:"maxHours" mapstructure:"maxHours"`
    Notify   string `json:"notify" mapstructure:"notify"`
}

// ModeConfig is per-mode settings (research vs production).
type ModeConfig struct {
    SessionTimeout int     `json:"sessionTimeout" mapstructure:"sessionTimeout"`
    BudgetCap      float64 `json:"budgetCap" mapstructure:"budgetCap"`
    DataSource     string  `json:"dataSource" mapstructure:"dataSource"`
}

// WorkersConfig defines worker layout.
type WorkersConfig struct {
    Count   int               `json:"count" mapstructure:"count"`
    Types   []string          `json:"types" mapstructure:"types"`
    Layout  map[string]string `json:"layout" mapstructure:"layout"`
    Prompts map[string]string `json:"prompts" mapstructure:"prompts"`
}

// QueuesConfig defines queue directory paths.
type QueuesConfig struct {
    Hypotheses string `json:"hypotheses" mapstructure:"hypotheses"`
    ToConvert  string `json:"toConvert" mapstructure:"toConvert"`
    ToBacktest string `json:"toBacktest" mapstructure:"toBacktest"`
    ToOptimize string `json:"toOptimize" mapstructure:"toOptimize"`
}

// PatternsConfig defines pattern file paths.
type PatternsConfig struct {
    WhatWorks      string `json:"whatWorks" mapstructure:"whatWorks"`
    WhatFails      string `json:"whatFails" mapstructure:"whatFails"`
    IndicatorCombos string `json:"indicatorCombos" mapstructure:"indicatorCombos"`
    PropFirmGotchas string `json:"propFirmGotchas" mapstructure:"propFirmGotchas"`
}

// ValidationConfig defines strategy validation thresholds.
type ValidationConfig struct {
    Strategy StrategyThresholds `json:"strategy" mapstructure:"strategy"`
    PropFirmMinPassing int     `json:"propFirmMinPassing" mapstructure:"propFirmMinPassing"`
}

// StrategyThresholds are the numerical gates for strategy grading.
type StrategyThresholds struct {
    MinSharpe       float64 `json:"minSharpe" mapstructure:"minSharpe"`
    GoodSharpe      float64 `json:"goodSharpe" mapstructure:"goodSharpe"`
    MaxSharpe       float64 `json:"maxSharpe" mapstructure:"maxSharpe"`
    MaxDrawdown     float64 `json:"maxDrawdown" mapstructure:"maxDrawdown"`
    GoodMaxDrawdown float64 `json:"goodMaxDrawdown" mapstructure:"goodMaxDrawdown"`
    RejectMaxDrawdown float64 `json:"rejectMaxDrawdown" mapstructure:"rejectMaxDrawdown"`
    MinTrades       int     `json:"minTrades" mapstructure:"minTrades"`
    GoodMinTrades   int     `json:"goodMinTrades" mapstructure:"goodMinTrades"`
    MaxWinRate      float64 `json:"maxWinRate" mapstructure:"maxWinRate"`
    MaxOosDecay     float64 `json:"maxOosDecay" mapstructure:"maxOosDecay"`
    RejectOosDecay  float64 `json:"rejectOosDecay" mapstructure:"rejectOosDecay"`
}

// OutputConfig defines output directory structure.
type OutputConfig struct {
    Directories OutputDirs      `json:"directories" mapstructure:"directories"`
    RetentionDays RetentionDays `json:"retentionDays" mapstructure:"retentionDays"`
}

type OutputDirs struct {
    Strategies StrategyDirs `json:"strategies" mapstructure:"strategies"`
}

type StrategyDirs struct {
    Good         string `json:"good" mapstructure:"good"`
    UnderReview  string `json:"underReview" mapstructure:"underReview"`
    Rejected     string `json:"rejected" mapstructure:"rejected"`
    PropFirmReady string `json:"propFirmReady" mapstructure:"propFirmReady"`
}

type RetentionDays struct {
    Rejected     int `json:"rejected" mapstructure:"rejected"`
    UnderReview  int `json:"underReview" mapstructure:"underReview"`
    ResearchLogs int `json:"researchLogs" mapstructure:"researchLogs"`
}

// RecoveryConfig defines crash recovery behavior.
type RecoveryConfig struct {
    CheckpointAfterEachSession bool   `json:"checkpointAfterEachSession" mapstructure:"checkpointAfterEachSession"`
    CheckpointDir              string `json:"checkpointDir" mapstructure:"checkpointDir"`
    MaxConsecutiveFailures     int    `json:"maxConsecutiveFailures" mapstructure:"maxConsecutiveFailures"`
    AutoResume                 bool   `json:"autoResume" mapstructure:"autoResume"`
}

// NotifyConfig defines notification settings.
type NotifyConfig struct {
    ElevenLabs ElevenLabsConfig `json:"elevenlabs" mapstructure:"elevenlabs"`
    Fallback   string           `json:"fallback" mapstructure:"fallback"`
}

type ElevenLabsConfig struct {
    Enabled bool     `json:"enabled" mapstructure:"enabled"`
    Voice   string   `json:"voice" mapstructure:"voice"`
    Events  []string `json:"events" mapstructure:"events"`
}

// ProjectRoot returns the resolved project root path.
func (c *Config) ProjectRoot() string { return c.projectRoot }

// SessionTimeout returns the timeout for the current mode.
func (c *Config) SessionTimeout() time.Duration {
    mode := c.Defaults.Mode
    if mc, ok := c.Modes[mode]; ok {
        return time.Duration(mc.SessionTimeout) * time.Second
    }
    return 30 * time.Minute
}

// BudgetCap returns the budget cap for the current mode.
func (c *Config) BudgetCap() float64 {
    mode := c.Defaults.Mode
    if mc, ok := c.Modes[mode]; ok {
        return mc.BudgetCap
    }
    return 50.0
}
```

### 7.2 Config Loader

```go
// internal/config/config.go
package config

import (
    "encoding/json"
    "fmt"
    "os"
    "path/filepath"

    "github.com/spf13/viper"
)

// Load reads config.json and returns a structured Config.
// Precedence: CLI flags > environment variables > config.json > defaults.
func Load() (*Config, error) {
    var cfg Config

    if err := viper.Unmarshal(&cfg); err != nil {
        return nil, fmt.Errorf("failed to unmarshal config: %w", err)
    }

    // Resolve project root
    root := viper.GetString("root")
    if root == "" {
        // Auto-detect: walk up from CWD looking for config.json
        cwd, _ := os.Getwd()
        root = findProjectRoot(cwd)
    }
    cfg.projectRoot = root

    return &cfg, nil
}

// Save writes the current config back to config.json.
func Save(cfg *Config) error {
    path := filepath.Join(cfg.projectRoot, "config.json")

    data, err := json.MarshalIndent(cfg, "", "  ")
    if err != nil {
        return fmt.Errorf("failed to marshal config: %w", err)
    }

    return os.WriteFile(path, append(data, '\n'), 0644)
}

// SetDotNotation sets a value in the config using dot notation (e.g., "defaults.mode").
func SetDotNotation(cfg *Config, key string, value interface{}) error {
    viper.Set(key, value)
    return Save(cfg)
}

// findProjectRoot walks up the directory tree looking for config.json.
func findProjectRoot(start string) string {
    dir := start
    for {
        if _, err := os.Stat(filepath.Join(dir, "config.json")); err == nil {
            return dir
        }
        parent := filepath.Dir(dir)
        if parent == dir {
            return start // Fallback to CWD
        }
        dir = parent
    }
}
```

### 7.3 Profile Management

```go
// internal/config/profile.go
package config

import (
    "encoding/json"
    "fmt"
    "os"
    "path/filepath"
)

// ActiveProfile represents a loaded market profile JSON file.
type ActiveProfile struct {
    ProfileID    string            `json:"profileId"`
    DisplayName  string            `json:"displayName"`
    MarketType   string            `json:"marketType"`
    DataProvider DataProviderConfig `json:"dataProvider"`
    Symbols      SymbolsConfig     `json:"symbols"`
    Costs        CostsConfig       `json:"costs"`
    Compliance   ComplianceConfig  `json:"compliance"`
}

type DataProviderConfig struct {
    Adapter      string `json:"adapter"`
    APIKeyEnv    string `json:"apiKeyEnv"`
    SampleDataDir string `json:"sampleDataDir"`
    Exchange     string `json:"exchange,omitempty"`
}

type SymbolsConfig struct {
    Mode    string   `json:"mode"`
    Pinned  []string `json:"pinned"`
    Current []string `json:"current"`
}

type CostsConfig struct {
    Model         string  `json:"model"`
    Commission    float64 `json:"commission"`
    Slippage      float64 `json:"slippage"`
    SlippageUnit  string  `json:"slippageUnit"`
    AlwaysInclude bool    `json:"alwaysInclude"`
}

type ComplianceConfig struct {
    Type       string   `json:"type"`
    Firms      []string `json:"firms,omitempty"`
    MinPassing int      `json:"minPassing"`
}

// LoadActiveProfile loads the currently active market profile.
func LoadActiveProfile(cfg *Config) (*ActiveProfile, error) {
    profilePath := filepath.Join(cfg.projectRoot, cfg.ActiveProfile)

    data, err := os.ReadFile(profilePath)
    if err != nil {
        return nil, fmt.Errorf("profile not found: %s", profilePath)
    }

    var profile ActiveProfile
    if err := json.Unmarshal(data, &profile); err != nil {
        return nil, fmt.Errorf("invalid profile JSON: %w", err)
    }

    return &profile, nil
}

// SwitchProfile changes the active profile in config.json.
func (cfg *Config) SwitchProfile(profileName string) error {
    mp, ok := cfg.MarketProfiles[profileName]
    if !ok {
        return fmt.Errorf("unknown profile: %s", profileName)
    }

    // Verify profile file exists
    profilePath := filepath.Join(cfg.projectRoot, mp.Path)
    if _, err := os.Stat(profilePath); err != nil {
        return fmt.Errorf("profile file not found: %s", profilePath)
    }

    cfg.ActiveProfile = mp.Path
    return Save(cfg)
}
```

### 7.4 Environment File Operations

```go
// internal/config/env.go
package config

import (
    "fmt"
    "os"
    "path/filepath"
    "sort"
    "strings"
)

// WriteEnvKeys writes or updates keys in the .env file.
func (cfg *Config) WriteEnvKeys(keys map[string]string) error {
    envPath := filepath.Join(cfg.projectRoot, ".env")

    existing := make(map[string]string)
    if data, err := os.ReadFile(envPath); err == nil {
        for _, line := range strings.Split(string(data), "\n") {
            line = strings.TrimSpace(line)
            if line == "" || strings.HasPrefix(line, "#") {
                continue
            }
            parts := strings.SplitN(line, "=", 2)
            if len(parts) == 2 {
                existing[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
            }
        }
    }

    // Merge
    for k, v := range keys {
        if v != "" {
            existing[k] = v
        }
    }

    // Write sorted
    var lines []string
    lines = append(lines, "# Sigma-Quant Stream Environment Configuration", "")

    sortedKeys := make([]string, 0, len(existing))
    for k := range existing {
        sortedKeys = append(sortedKeys, k)
    }
    sort.Strings(sortedKeys)

    for _, k := range sortedKeys {
        lines = append(lines, fmt.Sprintf("%s=%s", k, existing[k]))
    }
    lines = append(lines, "")

    return os.WriteFile(envPath, []byte(strings.Join(lines, "\n")), 0600)
}

// ReadEnvKey reads a single key from .env or OS environment.
func (cfg *Config) ReadEnvKey(key string) string {
    // OS env takes precedence
    if v := os.Getenv(key); v != "" {
        return v
    }

    envPath := filepath.Join(cfg.projectRoot, ".env")
    data, err := os.ReadFile(envPath)
    if err != nil {
        return ""
    }

    for _, line := range strings.Split(string(data), "\n") {
        line = strings.TrimSpace(line)
        if strings.HasPrefix(line, key+"=") {
            parts := strings.SplitN(line, "=", 2)
            if len(parts) == 2 {
                return strings.Trim(strings.TrimSpace(parts[1]), `"'`)
            }
        }
    }
    return ""
}
```

---

## 8. Queue System

### 8.1 Queue Item

```go
// internal/queue/item.go
package queue

import "time"

// Priority levels for queue items.
type Priority string

const (
    PriorityHigh   Priority = "high"
    PriorityMedium Priority = "medium"
    PriorityLow    Priority = "low"
)

// Status values for queue items.
type Status string

const (
    StatusPending    Status = "pending"
    StatusInProgress Status = "in_progress"
    StatusCompleted  Status = "completed"
    StatusFailed     Status = "failed"
)

// QueueItem is the JSON schema for files in queue directories.
type QueueItem struct {
    ID        string                 `json:"id"`
    CreatedAt time.Time              `json:"created_at"`
    CreatedBy string                 `json:"created_by"`
    Priority  Priority               `json:"priority"`
    Status    Status                 `json:"status"`
    ClaimedBy *string                `json:"claimed_by"`
    Payload   map[string]interface{} `json:"payload"`
}
```

### 8.2 Queue Reader

```go
// internal/queue/queue.go
package queue

import (
    "encoding/json"
    "fmt"
    "os"
    "path/filepath"
    "sort"
    "strings"
    "time"

    "github.com/sigma-algo/sigma-quant-cli/internal/tui"
)

// Reader reads queue directories and computes statistics.
type Reader struct {
    projectRoot string
    queues      map[string]string // name -> relative path
}

// NewReader creates a queue reader from config.
func NewReader(projectRoot string, queuePaths map[string]string) *Reader {
    return &Reader{
        projectRoot: projectRoot,
        queues:      queuePaths,
    }
}

// GetStats returns current queue depths.
func (r *Reader) GetStats() tui.QueueStatsMsg {
    return tui.QueueStatsMsg{
        Hypotheses: r.countItems("hypotheses"),
        ToConvert:  r.countItems("toConvert"),
        ToBacktest: r.countItems("toBacktest"),
        ToOptimize: r.countItems("toOptimize"),
        Completed:  r.countCompleted(),
        Failed:     r.countFailed(),
    }
}

// countItems counts pending JSON files in a queue directory.
func (r *Reader) countItems(queueName string) int {
    relPath, ok := r.queues[queueName]
    if !ok {
        return 0
    }

    dir := filepath.Join(r.projectRoot, relPath)
    entries, err := os.ReadDir(dir)
    if err != nil {
        return 0
    }

    count := 0
    for _, e := range entries {
        if !e.IsDir() && strings.HasSuffix(e.Name(), ".json") &&
            !strings.Contains(e.Name(), ".claimed") {
            count++
        }
    }
    return count
}

// countCompleted counts items in completed/ subdirectories.
func (r *Reader) countCompleted() int {
    total := 0
    for _, relPath := range r.queues {
        completedDir := filepath.Join(r.projectRoot, relPath, "completed")
        if entries, err := os.ReadDir(completedDir); err == nil {
            for _, e := range entries {
                if strings.HasSuffix(e.Name(), ".json") {
                    total++
                }
            }
        }
    }
    return total
}

// countFailed counts items in failed/ subdirectories.
func (r *Reader) countFailed() int {
    total := 0
    for _, relPath := range r.queues {
        failedDir := filepath.Join(r.projectRoot, relPath, "failed")
        if entries, err := os.ReadDir(failedDir); err == nil {
            for _, e := range entries {
                if strings.HasSuffix(e.Name(), ".json") {
                    total++
                }
            }
        }
    }
    return total
}

// ListItems returns all items in a queue, sorted by priority then creation time.
func (r *Reader) ListItems(queueName string) ([]QueueItem, error) {
    relPath, ok := r.queues[queueName]
    if !ok {
        return nil, fmt.Errorf("unknown queue: %s", queueName)
    }

    dir := filepath.Join(r.projectRoot, relPath)
    entries, err := os.ReadDir(dir)
    if err != nil {
        return nil, err
    }

    var items []QueueItem
    for _, e := range entries {
        if e.IsDir() || !strings.HasSuffix(e.Name(), ".json") {
            continue
        }

        data, err := os.ReadFile(filepath.Join(dir, e.Name()))
        if err != nil {
            continue
        }

        var item QueueItem
        if err := json.Unmarshal(data, &item); err != nil {
            continue
        }
        items = append(items, item)
    }

    // Sort: high > medium > low, then by created_at ascending
    priorityOrder := map[Priority]int{
        PriorityHigh:   0,
        PriorityMedium: 1,
        PriorityLow:    2,
    }

    sort.Slice(items, func(i, j int) bool {
        pi := priorityOrder[items[i].Priority]
        pj := priorityOrder[items[j].Priority]
        if pi != pj {
            return pi < pj
        }
        return items[i].CreatedAt.Before(items[j].CreatedAt)
    })

    return items, nil
}

// Push atomically writes a new item to a queue.
// Uses write-to-temp-then-rename for atomicity.
func (r *Reader) Push(queueName string, item QueueItem) error {
    relPath, ok := r.queues[queueName]
    if !ok {
        return fmt.Errorf("unknown queue: %s", queueName)
    }

    dir := filepath.Join(r.projectRoot, relPath)
    if err := os.MkdirAll(dir, 0755); err != nil {
        return err
    }

    data, err := json.MarshalIndent(item, "", "  ")
    if err != nil {
        return err
    }

    // Write to temp file first
    tmpFile := filepath.Join(dir, fmt.Sprintf(".tmp-%s-%d.json",
        item.ID, time.Now().UnixNano()))
    if err := os.WriteFile(tmpFile, data, 0644); err != nil {
        return err
    }

    // Atomic rename
    finalPath := filepath.Join(dir, item.ID+".json")
    return os.Rename(tmpFile, finalPath)
}
```

### 8.3 Queue Watcher (fsnotify)

```go
// internal/queue/watcher.go
package queue

import (
    "log"
    "path/filepath"

    "github.com/fsnotify/fsnotify"
)

// WatcherCallback is called when queue contents change.
type WatcherCallback func(queueName string, event string)

// Watcher monitors queue directories for changes using fsnotify.
type Watcher struct {
    watcher    *fsnotify.Watcher
    projectRoot string
    queues     map[string]string
    callback   WatcherCallback
    done       chan struct{}
}

// NewWatcher creates a filesystem watcher for queue directories.
func NewWatcher(projectRoot string, queues map[string]string, cb WatcherCallback) (*Watcher, error) {
    w, err := fsnotify.NewWatcher()
    if err != nil {
        return nil, err
    }

    qw := &Watcher{
        watcher:     w,
        projectRoot: projectRoot,
        queues:      queues,
        callback:    cb,
        done:        make(chan struct{}),
    }

    // Add queue directories to watch
    for name, relPath := range queues {
        dir := filepath.Join(projectRoot, relPath)
        if err := w.Add(dir); err != nil {
            log.Printf("Warning: cannot watch queue %s (%s): %v", name, dir, err)
        }
    }

    return qw, nil
}

// Start begins watching for changes in a goroutine.
func (w *Watcher) Start() {
    go func() {
        for {
            select {
            case event, ok := <-w.watcher.Events:
                if !ok {
                    return
                }
                // Determine which queue this belongs to
                for name, relPath := range w.queues {
                    dir := filepath.Join(w.projectRoot, relPath)
                    if filepath.Dir(event.Name) == dir {
                        w.callback(name, event.Op.String())
                        break
                    }
                }

            case err, ok := <-w.watcher.Errors:
                if !ok {
                    return
                }
                log.Printf("Queue watcher error: %v", err)

            case <-w.done:
                return
            }
        }
    }()
}

// Stop stops the watcher.
func (w *Watcher) Stop() {
    close(w.done)
    w.watcher.Close()
}
```

---

## 9. Dual-Path Onboarding Design

The onboarding flow adapts based on whether the user selects Developer or Trader path. This is not two separate code paths; it is a single onboarding model with a `userPath` flag that controls three things: information density, default values, and step visibility.

### 9.1 Path Differences Matrix

| Dimension | Developer Path | Trader Path |
|-----------|---------------|-------------|
| **Information density** | Full technical explanations, code snippets, architecture details | Plain-English summaries, outcome-focused |
| **Config defaults** | Minimal defaults, user sets everything | Curated defaults, auto-pilot mode |
| **Step visibility** | All steps shown, no skipping | Non-essential steps auto-completed |
| **Mode default** | `research` (manual control) | `production` (auto-pilot) |
| **Workers shown** | All 4 with individual launch option | "Start research" button (launches all) |
| **Queue visibility** | Full queue browser with JSON preview | Summary counts only |
| **Strategy detail** | All metrics, raw JSON, backtest curves | Grade + Sharpe + Pass/Fail |
| **Error display** | Full stack trace, stderr, exit code | "Something went wrong, retry?" |
| **Keyboard shortcuts** | Vim bindings active by default | Arrow keys only, no modal navigation |
| **Explain panels** | Shown if `--explain` flag | Always shown (simplified) |

### 9.2 Implementation Pattern

The path selection is stored in config and propagated as a context value through every TUI model.

```go
// internal/config/defaults.go
package config

// PathDefaults returns the default configuration overrides for a user path.
func PathDefaults(path string) map[string]interface{} {
    switch path {
    case "developer":
        return map[string]interface{}{
            "defaults.mode":    "research",
            "defaults.notify":  "say",          // Simple terminal bell
            "defaults.maxHours": 24,
        }
    case "trader":
        return map[string]interface{}{
            "defaults.mode":    "production",
            "defaults.notify":  "elevenlabs",   // Voice notifications
            "defaults.maxHours": 8,             // Shorter sessions
        }
    default:
        return nil
    }
}

// StepVisibility returns which onboarding steps are visible for a path.
func StepVisibility(path string) map[string]bool {
    switch path {
    case "developer":
        return map[string]bool{
            "welcome":  true,
            "path":     true,
            "market":   true,
            "apikeys":  true,
            "data":     true,
            "verify":   true,
            "complete": true,
        }
    case "trader":
        return map[string]bool{
            "welcome":  true,
            "path":     true,
            "market":   true,
            "apikeys":  true,
            "data":     false, // Auto-select sample data
            "verify":   false, // Auto-run health check
            "complete": true,
        }
    default:
        return nil
    }
}
```

### 9.3 Adaptive UI Rendering

Each TUI component checks the user path to adjust its rendering.

```go
// internal/tui/theme/adaptive.go
package theme

import "github.com/charmbracelet/lipgloss"

// DetailLevel controls how much information a component shows.
type DetailLevel int

const (
    DetailMinimal DetailLevel = iota // Trader path: just the essentials
    DetailStandard                    // Default
    DetailFull                        // Developer path: everything
)

// DetailLevelForPath returns the detail level for a user path.
func DetailLevelForPath(path string) DetailLevel {
    switch path {
    case "developer":
        return DetailFull
    case "trader":
        return DetailMinimal
    default:
        return DetailStandard
    }
}

// ExplainPanelStyle returns a styled panel for educational content.
// Returns an empty string if the detail level is too low.
func ExplainPanel(title, body string, level DetailLevel) string {
    if level < DetailStandard {
        return "" // Traders see simplified inline text instead
    }

    style := lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(CyanDim).
        Foreground(LightGray).
        Padding(1, 2).
        MarginBottom(1)

    titleStr := lipgloss.NewStyle().
        Foreground(CyanDim).
        Italic(true).
        Render(title)

    return style.Render(titleStr + "\n\n" + body)
}

// ErrorDisplay formats an error based on detail level.
func ErrorDisplay(err error, stderr string, level DetailLevel) string {
    switch level {
    case DetailFull:
        // Developer: show everything
        return lipgloss.NewStyle().Foreground(Red).Render(
            "Error: " + err.Error() + "\n\n" +
            "Stderr:\n" + stderr)
    case DetailMinimal:
        // Trader: friendly message
        return lipgloss.NewStyle().Foreground(Yellow).Render(
            "Something went wrong. Try running 'sigma-quant health' to diagnose.")
    default:
        return lipgloss.NewStyle().Foreground(Red).Render(
            "Error: " + err.Error())
    }
}
```

### 9.4 Progressive Disclosure

For the Trader path, complex features are hidden behind explicit actions rather than shown upfront.

```go
// Example: Dashboard view adapts to user path.
// In the Dashboard model's View() method:

func (m DashboardModel) View() string {
    level := theme.DetailLevelForPath(m.cfg.UserPath())

    switch level {
    case theme.DetailFull:
        // Developer: 4-panel layout with all metrics
        return m.renderFullDashboard()
    case theme.DetailMinimal:
        // Trader: simplified 2-panel (status + strategies)
        return m.renderSimpleDashboard()
    default:
        return m.renderFullDashboard()
    }
}

func (m DashboardModel) renderSimpleDashboard() string {
    // Only two sections: are things running? + how many strategies found?
    header := theme.TitleStyle.Render(" SIGMA-QUANT")

    // Simple running/stopped indicator
    anyRunning := false
    for _, w := range m.workers {
        if w.Running {
            anyRunning = true
            break
        }
    }

    var statusLine string
    if anyRunning {
        statusLine = theme.RunningStyle.Render("  Research in progress...")
    } else {
        statusLine = theme.StoppedStyle.Render("  Workers stopped. Run 'sigma-quant start' to begin.")
    }

    // Strategy summary (just counts)
    pfCount := 0
    goodCount := 0
    for _, s := range m.strategies {
        switch s.Grade {
        case "prop_firm_ready":
            pfCount++
        case "good":
            goodCount++
        }
    }

    stratLine := fmt.Sprintf("  %d strategies ready | %d under validation",
        pfCount+goodCount, len(m.strategies)-pfCount-goodCount)

    return lipgloss.JoinVertical(lipgloss.Left,
        header, "", statusLine, "", stratLine, "",
        theme.MutedStyle.Render("  Press 'q' to quit | 'tab' for details"),
    )
}
```

---

## 10. Cross-Compilation and Distribution

### 10.1 Build Targets

| OS | Architecture | Binary Name | Primary Users |
|----|-------------|-------------|---------------|
| macOS | arm64 (Apple Silicon) | `sigma-quant` | Primary development |
| macOS | amd64 (Intel) | `sigma-quant` | Older Macs |
| Linux | amd64 | `sigma-quant` | CI/CD, servers |

### 10.2 Makefile

```makefile
# Makefile
BINARY_NAME := sigma-quant
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
LDFLAGS := -s -w \
    -X main.version=$(VERSION) \
    -X main.commit=$(COMMIT) \
    -X main.buildTime=$(BUILD_TIME)

.PHONY: build install clean test lint

build:
	go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY_NAME) ./cmd/sigma-quant/

install:
	go install -ldflags "$(LDFLAGS)" ./cmd/sigma-quant/

clean:
	rm -rf bin/ dist/

test:
	go test ./... -race -coverprofile=coverage.out

test-short:
	go test ./... -short

lint:
	golangci-lint run ./...

# Cross-compilation
build-all:
	GOOS=darwin GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY_NAME)-darwin-arm64 ./cmd/sigma-quant/
	GOOS=darwin GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY_NAME)-darwin-amd64 ./cmd/sigma-quant/
	GOOS=linux GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY_NAME)-linux-amd64 ./cmd/sigma-quant/
```

### 10.3 goreleaser Configuration

```yaml
# .goreleaser.yaml
version: 2
project_name: sigma-quant

builds:
  - id: sigma-quant
    main: ./cmd/sigma-quant/
    binary: sigma-quant
    env:
      - CGO_ENABLED=0
    goos:
      - darwin
      - linux
    goarch:
      - amd64
      - arm64
    ldflags:
      - -s -w
      - -X main.version={{.Version}}
      - -X main.commit={{.ShortCommit}}
      - -X main.buildTime={{.Date}}

archives:
  - id: default
    format: tar.gz
    name_template: "{{ .ProjectName }}_{{ .Version }}_{{ .Os }}_{{ .Arch }}"
    files:
      - README.md
      - LICENSE

brews:
  - name: sigma-quant
    repository:
      owner: Sigma-Algo
      name: homebrew-tap
    homepage: "https://github.com/Sigma-Algo/sigma-quant-stream"
    description: "Autonomous strategy research factory CLI"
    license: "MIT"
    install: |
      bin.install "sigma-quant"
    test: |
      system "#{bin}/sigma-quant", "--version"

checksum:
  name_template: "checksums.txt"
  algorithm: sha256

changelog:
  sort: asc
  filters:
    exclude:
      - "^docs:"
      - "^test:"
      - "^chore:"

release:
  github:
    owner: Sigma-Algo
    name: sigma-quant-stream
  draft: false
  prerelease: auto
```

### 10.4 Install Script

```bash
#!/bin/bash
# install.sh -- Install sigma-quant CLI
set -euo pipefail

REPO="Sigma-Algo/sigma-quant-stream"
BINARY="sigma-quant"

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
    x86_64)  ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

echo "Detected: ${OS}/${ARCH}"

# Get latest release
LATEST=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$LATEST" ]; then
    echo "Failed to fetch latest release."
    exit 1
fi

echo "Latest version: ${LATEST}"

# Download
URL="https://github.com/${REPO}/releases/download/${LATEST}/${BINARY}_${LATEST#v}_${OS}_${ARCH}.tar.gz"
echo "Downloading ${URL}..."

TMPDIR=$(mktemp -d)
curl -sL "$URL" -o "${TMPDIR}/release.tar.gz"
tar -xzf "${TMPDIR}/release.tar.gz" -C "${TMPDIR}"

# Install
INSTALL_DIR="/usr/local/bin"
if [ ! -w "$INSTALL_DIR" ]; then
    echo "Installing to ${INSTALL_DIR} (requires sudo)..."
    sudo mv "${TMPDIR}/${BINARY}" "${INSTALL_DIR}/"
else
    mv "${TMPDIR}/${BINARY}" "${INSTALL_DIR}/"
fi

rm -rf "$TMPDIR"

echo "sigma-quant ${LATEST} installed to ${INSTALL_DIR}/${BINARY}"
echo "Run 'sigma-quant --help' to get started."
```

### 10.5 Version Embedding

```go
// cmd/sigma-quant/main.go
package main

import (
    "fmt"
    "os"

    "github.com/sigma-algo/sigma-quant-cli/internal/cmd"
)

// Set by goreleaser ldflags
var (
    version   = "dev"
    commit    = "unknown"
    buildTime = "unknown"
)

func main() {
    cmd.SetVersionInfo(version, commit, buildTime)
    cmd.Execute()
}
```

```go
// internal/cmd/root.go (addition for version command)

var versionStr, commitStr, buildTimeStr string

func SetVersionInfo(v, c, b string) {
    versionStr = v
    commitStr = c
    buildTimeStr = b
}

var versionCmd = &cobra.Command{
    Use:   "version",
    Short: "Print version information",
    Run: func(cmd *cobra.Command, args []string) {
        fmt.Printf("sigma-quant %s (commit: %s, built: %s)\n",
            versionStr, commitStr, buildTimeStr)
    },
}

func init() {
    rootCmd.AddCommand(versionCmd)
}
```

---

## 11. Testing Strategy

### 11.1 Testing Layers

| Layer | What to Test | Approach | Coverage Target |
|-------|-------------|----------|-----------------|
| **Config** | Load, save, merge, dot-notation set | Unit tests with temp files | 90% |
| **Queue** | Push, list, count, claim, atomic rename | Unit tests with temp dirs | 90% |
| **Strategy** | Load, metrics extraction, grading | Unit tests with fixture JSON | 85% |
| **Health** | Individual check functions | Unit tests with mocks | 80% |
| **Agent/tmux** | Session create, pane checks | Integration tests (require tmux) | 60% |
| **Python runner** | Script execution, output parsing | Integration tests (require Python) | 70% |
| **TUI models** | Update() state transitions | Unit tests (no rendering) | 75% |
| **TUI views** | View() output | Golden file snapshot tests | 60% |

### 11.2 Testing TUI Models

Bubble Tea models are pure functions: `Update(msg) -> (model, cmd)`. This makes them highly testable without rendering.

```go
// internal/tui/models/dashboard_test.go
package models_test

import (
    "testing"
    "time"

    tea "github.com/charmbracelet/bubbletea"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui/models"
)

func TestDashboardUpdate_WindowResize(t *testing.T) {
    m := models.NewDashboardModel(nil, nil, nil, nil)

    msg := tea.WindowSizeMsg{Width: 120, Height: 40}
    updated, _ := m.Update(msg)
    dashboard := updated.(models.DashboardModel)

    if dashboard.Width() != 120 {
        t.Errorf("expected width 120, got %d", dashboard.Width())
    }
    if dashboard.Height() != 40 {
        t.Errorf("expected height 40, got %d", dashboard.Height())
    }
}

func TestDashboardUpdate_WorkerStatus(t *testing.T) {
    m := models.NewDashboardModel(nil, nil, nil, nil)

    msg := tui.WorkerStatusMsg{
        Workers: []tui.WorkerState{
            {Name: "researcher", Running: true, TaskCount: 5},
            {Name: "converter", Running: false},
        },
    }

    updated, _ := m.Update(msg)
    dashboard := updated.(models.DashboardModel)

    workers := dashboard.Workers()
    if len(workers) != 2 {
        t.Fatalf("expected 2 workers, got %d", len(workers))
    }
    if !workers[0].Running {
        t.Error("expected researcher to be running")
    }
    if workers[0].TaskCount != 5 {
        t.Errorf("expected 5 tasks, got %d", workers[0].TaskCount)
    }
}

func TestDashboardUpdate_TabSwitchesPanel(t *testing.T) {
    m := models.NewDashboardModel(nil, nil, nil, nil)

    // Tab should cycle through panels 0 -> 1 -> 2 -> 3 -> 0
    for expected := 1; expected <= 4; expected++ {
        msg := tea.KeyMsg{Type: tea.KeyTab}
        updated, _ := m.Update(msg)
        m = updated.(models.DashboardModel)

        if m.ActivePanel() != expected%4 {
            t.Errorf("after %d tabs, expected panel %d, got %d",
                expected, expected%4, m.ActivePanel())
        }
    }
}

func TestDashboardUpdate_QuitKey(t *testing.T) {
    m := models.NewDashboardModel(nil, nil, nil, nil)

    msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}}
    _, cmd := m.Update(msg)

    // cmd should be tea.Quit
    if cmd == nil {
        t.Error("expected quit command, got nil")
    }
}
```

### 11.3 Testing Queue Operations

```go
// internal/queue/queue_test.go
package queue_test

import (
    "os"
    "path/filepath"
    "testing"
    "time"

    "github.com/sigma-algo/sigma-quant-cli/internal/queue"
)

func TestPushAndList(t *testing.T) {
    tmpDir := t.TempDir()
    queueDir := filepath.Join(tmpDir, "hypotheses")
    os.MkdirAll(queueDir, 0755)

    r := queue.NewReader(tmpDir, map[string]string{
        "hypotheses": "hypotheses",
    })

    item := queue.QueueItem{
        ID:        "hyp-test-001",
        CreatedAt: time.Now(),
        CreatedBy: "test",
        Priority:  queue.PriorityHigh,
        Status:    queue.StatusPending,
        Payload:   map[string]interface{}{"name": "Test Hypothesis"},
    }

    if err := r.Push("hypotheses", item); err != nil {
        t.Fatalf("Push failed: %v", err)
    }

    items, err := r.ListItems("hypotheses")
    if err != nil {
        t.Fatalf("ListItems failed: %v", err)
    }

    if len(items) != 1 {
        t.Fatalf("expected 1 item, got %d", len(items))
    }

    if items[0].ID != "hyp-test-001" {
        t.Errorf("expected ID hyp-test-001, got %s", items[0].ID)
    }
}

func TestGetStats(t *testing.T) {
    tmpDir := t.TempDir()

    queues := map[string]string{
        "hypotheses": "hypotheses",
        "toConvert":  "to-convert",
        "toBacktest": "to-backtest",
        "toOptimize": "to-optimize",
    }

    for _, dir := range queues {
        os.MkdirAll(filepath.Join(tmpDir, dir), 0755)
    }

    r := queue.NewReader(tmpDir, queues)

    // Push 3 items to hypotheses
    for i := 0; i < 3; i++ {
        item := queue.QueueItem{
            ID:        fmt.Sprintf("hyp-%d", i),
            CreatedAt: time.Now(),
            Priority:  queue.PriorityMedium,
            Status:    queue.StatusPending,
        }
        r.Push("hypotheses", item)
    }

    stats := r.GetStats()
    if stats.Hypotheses != 3 {
        t.Errorf("expected 3 hypotheses, got %d", stats.Hypotheses)
    }
    if stats.ToConvert != 0 {
        t.Errorf("expected 0 to-convert, got %d", stats.ToConvert)
    }
}

func TestPriorityOrdering(t *testing.T) {
    tmpDir := t.TempDir()
    os.MkdirAll(filepath.Join(tmpDir, "q"), 0755)

    r := queue.NewReader(tmpDir, map[string]string{"test": "q"})

    // Push items in reverse priority order
    priorities := []queue.Priority{
        queue.PriorityLow,
        queue.PriorityHigh,
        queue.PriorityMedium,
    }

    for i, p := range priorities {
        r.Push("test", queue.QueueItem{
            ID:        fmt.Sprintf("item-%d", i),
            CreatedAt: time.Now(),
            Priority:  p,
            Status:    queue.StatusPending,
        })
    }

    items, _ := r.ListItems("test")

    if items[0].Priority != queue.PriorityHigh {
        t.Errorf("expected first item to be high priority, got %s", items[0].Priority)
    }
    if items[1].Priority != queue.PriorityMedium {
        t.Errorf("expected second item to be medium priority, got %s", items[1].Priority)
    }
    if items[2].Priority != queue.PriorityLow {
        t.Errorf("expected third item to be low priority, got %s", items[2].Priority)
    }
}
```

### 11.4 Golden File Tests for Views

```go
// internal/tui/models/strategy_browser_view_test.go
package models_test

import (
    "os"
    "path/filepath"
    "testing"

    "github.com/sigma-algo/sigma-quant-cli/internal/tui"
    "github.com/sigma-algo/sigma-quant-cli/internal/tui/models"
)

func TestStrategyBrowserView_Golden(t *testing.T) {
    loader := &mockLoader{
        strategies: []tui.StrategyEntry{
            {Name: "FundingReversion", Grade: "good", Sharpe: 1.8,
             WinRate: 0.55, MaxDrawdown: 0.12, Trades: 234, ProfitFactor: 1.4},
            {Name: "ORBMomentum", Grade: "prop_firm_ready", Sharpe: 2.1,
             WinRate: 0.48, MaxDrawdown: 0.08, Trades: 456, ProfitFactor: 1.7,
             PropFirmsPassed: []string{"Apex", "Topstep", "FTMO"}},
        },
    }

    m := models.NewStrategyBrowserModel(loader, "")
    // Simulate window size
    m, _ = m.Update(tea.WindowSizeMsg{Width: 100, Height: 30})
    // Simulate data load
    m, _ = m.Update(tui.StrategyListMsg{Strategies: loader.strategies})

    got := m.View()

    golden := filepath.Join("testdata", "strategy_browser.golden")
    if os.Getenv("UPDATE_GOLDEN") != "" {
        os.MkdirAll("testdata", 0755)
        os.WriteFile(golden, []byte(got), 0644)
        return
    }

    expected, err := os.ReadFile(golden)
    if err != nil {
        t.Fatalf("Golden file not found. Run with UPDATE_GOLDEN=1 to create.")
    }

    if got != string(expected) {
        t.Errorf("View output differs from golden file.\nGot:\n%s\n\nExpected:\n%s", got, string(expected))
    }
}
```

---

## 12. Architecture Decision Records

### ADR-001: Go Over Python for CLI

- **Status:** Accepted
- **Context:** The existing CLI is Python/Typer/Rich. It works but requires Python + pip on the user's machine, has no real-time TUI capabilities (Rich tables are static), and cannot be distributed as a single binary. The target users include traders who may not have Python installed.
- **Decision:** Rewrite the CLI in Go using Cobra + Bubble Tea. Keep all Python computation code (backtest_runner.py, crypto modules, validators) and invoke them via subprocess.
- **Consequences:**
  - (+) Single binary distribution, no runtime dependencies
  - (+) Real-time TUI with composable models
  - (+) Cross-platform builds via goreleaser
  - (+) Fast startup (<50ms vs ~500ms for Python)
  - (-) Two languages in the project (Go for CLI, Python for computation)
  - (-) Learning curve for team members unfamiliar with Go
  - (-) Subprocess overhead for Python calls (acceptable since they are infrequent, long-running operations)

### ADR-002: Bubble Tea Over Other TUI Libraries

- **Status:** Accepted
- **Context:** Alternatives considered: tview (immediate mode), termui (widget-based), tcell (low-level). The CLI requires composable components, form input, animations, and a consistent theme.
- **Decision:** Use Bubble Tea (Elm architecture) with Huh for forms, Lipgloss for styling, and Bubbles for standard components.
- **Consequences:**
  - (+) Elm architecture (Model/Update/View) makes state management predictable and testable
  - (+) Huh provides accessible form components out of the box
  - (+) Lipgloss CSS-like API enables the Sharian theme system
  - (+) Active ecosystem maintained by Charm.sh
  - (-) Elm architecture has a learning curve for developers used to imperative TUI code
  - (-) Complex layouts require manual composition (no automatic flexbox until Stickers matures)

### ADR-003: File-Based Queues Over Message Brokers

- **Status:** Accepted (inherited from existing architecture)
- **Context:** Workers need to communicate. Options: Redis, RabbitMQ, NATS, or file-based IPC. The system runs on a single machine.
- **Decision:** Keep file-based queues with JSON files. Add fsnotify for real-time change detection in the Go dashboard.
- **Consequences:**
  - (+) No external dependencies (no Redis/RabbitMQ to install)
  - (+) Human-readable (users can inspect queue files)
  - (+) Atomic via write-temp-then-rename
  - (+) Works when the Go CLI is not running (agents write directly)
  - (-) No guaranteed ordering under concurrent writes (mitigated by timestamps)
  - (-) fsnotify has platform-specific edge cases
  - (-) No built-in retry/dead-letter (implemented manually)

### ADR-004: Python Subprocess Over Go-Native Backtesting

- **Status:** Accepted
- **Context:** The backtesting engine, crypto modules, and validators are written in Python (28k lines in lib/). Rewriting in Go would take months and lose the pandas-ta, ccxt, and vectorbt ecosystem.
- **Decision:** Keep all computation in Python. The Go CLI invokes Python scripts via `os/exec` and parses JSON output.
- **Consequences:**
  - (+) Preserves existing validated Python code
  - (+) Python ecosystem (pandas, numpy, ccxt) is irreplaceable for quant work
  - (+) Clear separation: Go handles UX, Python handles computation
  - (-) Requires Python 3.11+ on the user's machine
  - (-) Subprocess startup latency (~200ms per invocation)
  - (-) Error handling requires parsing stderr strings

### ADR-005: Viper for Configuration

- **Status:** Accepted
- **Context:** The existing config.json is a flat JSON file. The Go CLI needs to support CLI flags, environment variables, and file-based config with clear precedence.
- **Decision:** Use Viper with precedence: CLI flags > environment variables > config.json > compiled defaults.
- **Consequences:**
  - (+) Industry standard, well-documented
  - (+) Automatic environment variable binding with SIGMA_QUANT_ prefix
  - (+) Supports `mapstructure` tags for clean struct mapping
  - (+) File watcher for live reload (useful in dashboard)
  - (-) Viper uses global state internally (mitigated by wrapping in config package)

### ADR-006: Sharian Theme as a Separate Package

- **Status:** Accepted
- **Context:** The visual theme needs to be consistent across all TUI views, and swappable in the future.
- **Decision:** Isolate all color definitions, border styles, and named styles in `internal/tui/theme/`. No component should use raw lipgloss colors directly.
- **Consequences:**
  - (+) Theme changes propagate automatically to all components
  - (+) Enables future light/dark/custom theme switching
  - (+) Centralizes accessibility concerns (contrast ratios)
  - (-) Slight indirection when styling components

---

## Open Questions

- [ ] **iTerm2 integration**: The `scripts/iterm-quant-launcher.js` uses OSA/JXA to create iTerm2 panes. Should the Go CLI support iTerm2 as a first-class alternative to tmux, or always go through tmux?
- [ ] **Cost tracking precision**: The current `cost-tracker.json` is updated by agents via file writes. Should the Go dashboard poll this file, or should agents write to a Unix socket that the Go process listens on?
- [ ] **ElevenLabs notifications**: The Python `scripts/notify.py` handles voice synthesis. Should this move to Go (via HTTP API calls), or remain as a Python subprocess?
- [ ] **CI/CD testing**: Integration tests require tmux and Python. Should CI use a Docker image with both installed, or should integration tests be excluded from CI?
- [ ] **Plugin system**: Should the CLI support user-defined commands or custom market profiles beyond the three built-in ones? If so, what extension mechanism (Go plugins, subprocess, config-driven)?

---

## Appendix: Go Module Dependencies

```
require (
    github.com/charmbracelet/bubbletea v1.x
    github.com/charmbracelet/bubbles v0.x
    github.com/charmbracelet/lipgloss v1.x
    github.com/charmbracelet/huh v0.x
    github.com/spf13/cobra v1.x
    github.com/spf13/viper v1.x
    github.com/fsnotify/fsnotify v1.x
)
```

These are the only direct dependencies. The total binary size with all dependencies is expected to be approximately 15-20 MB.
