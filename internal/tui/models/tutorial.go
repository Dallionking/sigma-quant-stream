package models

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/glamour"
	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/python"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/components"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// ---------------------------------------------------------------------------
// Step Constants
// ---------------------------------------------------------------------------

// TutorialStep represents the current phase of the tutorial.
type TutorialStep int

const (
	TutStepHypothesis TutorialStep = iota
	TutStepStrategy
	TutStepBacktest
	TutStepOptimize
	TutStepValidate
	TutStepDeploy
)

const tutorialTotalSteps = 6

var tutorialStepLabels = [tutorialTotalSteps]string{
	"Hypothesis", "Strategy", "Backtest", "Optimize", "Validate", "Deploy",
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

type stepEnteredMsg struct{}
type backtestOutputMsg string
type backtestFinishedMsg struct{}
type simulatedTickMsg int
type hypothesisCreatedMsg string

// ---------------------------------------------------------------------------
// TutorialModel
// ---------------------------------------------------------------------------

// TutorialModel is the Bubble Tea model for the 6-step interactive tutorial.
type TutorialModel struct {
	step TutorialStep

	// Backtest state.
	backtestResult  *python.BacktestResult
	backtestRunning bool
	backtestDone    bool
	backtestCancel  context.CancelFunc
	outputLines     []string
	linesCh         <-chan string
	errCh           <-chan error

	// Simulated output (when Python is unavailable).
	simulating bool
	simLines   []string

	// Hypothesis state.
	hypothesisCreated bool
	hypothesisPath    string

	// Validation state.
	validationFailures []string
	validationRan      bool

	// Config.
	projectRoot  string
	pythonRunner *python.Runner

	// Layout.
	width  int
	height int
}

// NewTutorialModel creates a tutorial model starting at the given step (0-5).
func NewTutorialModel(startStep int, projectRoot string) TutorialModel {
	runner, _ := python.NewRunner(projectRoot)

	step := TutorialStep(startStep)
	if step < 0 || int(step) >= tutorialTotalSteps {
		step = TutStepHypothesis
	}

	return TutorialModel{
		step:        step,
		projectRoot: projectRoot,
		pythonRunner: runner,
		width:       80,
		height:      24,
	}
}

// ---------------------------------------------------------------------------
// Bubble Tea Interface
// ---------------------------------------------------------------------------

// Init triggers the initial step action.
func (m TutorialModel) Init() tea.Cmd {
	return func() tea.Msg { return stepEnteredMsg{} }
}

// Update handles all messages for the tutorial.
func (m TutorialModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		return m, nil

	case tea.KeyMsg:
		// While a backtest is running, only allow quit.
		if m.backtestRunning {
			switch msg.String() {
			case "q", "ctrl+c":
				if m.backtestCancel != nil {
					m.backtestCancel()
				}
				return m, tea.Quit
			default:
				return m, nil
			}
		}
		switch msg.String() {
		case "q", "ctrl+c":
			return m, tea.Quit
		case "enter", "right", "l":
			return m.advance()
		case "backspace", "left", "h":
			return m.goBack()
		}

	case stepEnteredMsg:
		return m.handleStepEntry()

	case backtestOutputMsg:
		m.outputLines = append(m.outputLines, string(msg))
		return m, waitForLine(m.linesCh)

	case backtestFinishedMsg:
		m.backtestRunning = false
		m.backtestDone = true
		if m.errCh != nil {
			select {
			case err := <-m.errCh:
				if err != nil {
					m.outputLines = append(m.outputLines, "Error: "+err.Error())
				}
			default:
			}
		}
		result := m.parseOutputAsResult()
		if result != nil {
			m.backtestResult = result
		} else {
			m.backtestResult = simulatedResult()
			m.outputLines = append(m.outputLines, "", "[Using simulated results]")
		}
		return m, nil

	case simulatedTickMsg:
		idx := int(msg)
		if idx < len(m.simLines) {
			m.outputLines = append(m.outputLines, m.simLines[idx])
			if idx+1 < len(m.simLines) {
				return m, tickSimulatedLine(idx + 1)
			}
			m.backtestRunning = false
			m.backtestDone = true
			m.backtestResult = simulatedResult()
		}
		return m, nil

	case hypothesisCreatedMsg:
		m.hypothesisCreated = true
		m.hypothesisPath = string(msg)
		return m, nil
	}

	return m, nil
}

// View renders the full tutorial screen.
func (m TutorialModel) View() string {
	progress := m.renderProgress()
	left := m.renderLeftPanel()
	right := m.renderRightPanel()
	footer := m.renderFooter()

	body := lipgloss.JoinHorizontal(lipgloss.Top, left, " ", right)

	return lipgloss.JoinVertical(lipgloss.Left,
		progress,
		"",
		body,
		"",
		footer,
	)
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

func (m TutorialModel) advance() (tea.Model, tea.Cmd) {
	if int(m.step) >= tutorialTotalSteps-1 {
		return m, tea.Quit
	}
	m.step++
	return m.handleStepEntry()
}

func (m TutorialModel) goBack() (tea.Model, tea.Cmd) {
	if m.step <= TutStepHypothesis {
		return m, nil
	}
	m.step--
	return m, nil
}

func (m TutorialModel) handleStepEntry() (tea.Model, tea.Cmd) {
	switch m.step {
	case TutStepHypothesis:
		if !m.hypothesisCreated {
			return m, m.createHypothesisCmd()
		}
	case TutStepBacktest:
		if !m.backtestDone && !m.backtestRunning {
			return m.startBacktest()
		}
	case TutStepValidate:
		if !m.validationRan {
			m.validationRan = true
			if m.backtestResult == nil {
				m.backtestResult = simulatedResult()
			}
			m.validationFailures = m.backtestResult.ValidateResult(
				0.5,  // minSharpe
				3.0,  // maxSharpe
				25.0, // maxDD
				100,  // minTrades
				80.0, // maxWinRate
				50.0, // maxOOSDecay
			)
		}
	}
	return m, nil
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

func (m TutorialModel) createHypothesisCmd() tea.Cmd {
	root := m.projectRoot
	return func() tea.Msg {
		dir := filepath.Join(root, "queues", "hypotheses")
		_ = os.MkdirAll(dir, 0o755)
		path := filepath.Join(dir, "tutorial_sma_crossover.json")
		_ = os.WriteFile(path, []byte(tutorialHypothesisJSON), 0o644)
		return hypothesisCreatedMsg(path)
	}
}

func (m TutorialModel) startBacktest() (TutorialModel, tea.Cmd) {
	m.backtestRunning = true
	m.outputLines = nil

	if m.pythonRunner == nil {
		m.simulating = true
		m.simLines = simulatedOutputLines()
		return m, tickSimulatedLine(0)
	}

	ctx, cancel := context.WithCancel(context.Background())
	m.backtestCancel = cancel
	lines, errc := m.pythonRunner.ExecStreaming(ctx, "lib/backtest_runner.py",
		[]string{"--strategy", "tutorial"})
	m.linesCh = lines
	m.errCh = errc
	return m, waitForLine(lines)
}

func (m TutorialModel) parseOutputAsResult() *python.BacktestResult {
	if len(m.outputLines) == 0 {
		return nil
	}
	last := m.outputLines[len(m.outputLines)-1]
	var result python.BacktestResult
	if err := json.Unmarshal([]byte(last), &result); err == nil {
		return &result
	}
	full := strings.Join(m.outputLines, "\n")
	if err := json.Unmarshal([]byte(full), &result); err == nil {
		return &result
	}
	start := max(0, len(m.outputLines)-20)
	chunk := strings.Join(m.outputLines[start:], "\n")
	if err := json.Unmarshal([]byte(strings.TrimSpace(chunk)), &result); err == nil {
		return &result
	}
	return nil
}

// ---------------------------------------------------------------------------
// Tea Commands
// ---------------------------------------------------------------------------

func waitForLine(ch <-chan string) tea.Cmd {
	return func() tea.Msg {
		line, ok := <-ch
		if !ok {
			return backtestFinishedMsg{}
		}
		return backtestOutputMsg(line)
	}
}

func tickSimulatedLine(idx int) tea.Cmd {
	return tea.Tick(120*time.Millisecond, func(_ time.Time) tea.Msg {
		return simulatedTickMsg(idx)
	})
}

// ---------------------------------------------------------------------------
// View: Progress
// ---------------------------------------------------------------------------

func (m TutorialModel) renderProgress() string {
	labels := make([]string, tutorialTotalSteps)
	copy(labels, tutorialStepLabels[:])
	p := components.ProgressStep{
		Steps:   labels,
		Current: int(m.step),
		Width:   m.width,
	}
	return p.Render()
}

// ---------------------------------------------------------------------------
// View: Footer
// ---------------------------------------------------------------------------

func (m TutorialModel) renderFooter() string {
	hints := []components.KeyHint{
		{Key: "enter/->", Desc: "next"},
		{Key: "backspace/<-", Desc: "back"},
		{Key: "q", Desc: "quit"},
	}
	if m.backtestRunning {
		hints = []components.KeyHint{
			{Key: "q", Desc: "quit (cancel backtest)"},
		}
	}
	if int(m.step) == tutorialTotalSteps-1 {
		hints = []components.KeyHint{
			{Key: "enter", Desc: "finish"},
			{Key: "backspace/<-", Desc: "back"},
			{Key: "q", Desc: "quit"},
		}
	}
	f := components.Footer{
		Hints: hints,
		Width: m.width,
	}
	return f.Render()
}

// ---------------------------------------------------------------------------
// View: Left Panel (Explanations)
// ---------------------------------------------------------------------------

func (m TutorialModel) leftPanelWidth() int {
	return max((m.width-1)/2, 30)
}

func (m TutorialModel) rightPanelWidth() int {
	return max(m.width-m.leftPanelWidth()-1, 30)
}

func (m TutorialModel) contentHeight() int {
	return max(m.height-6, 10)
}

func (m TutorialModel) renderLeftPanel() string {
	w := m.leftPanelWidth()
	h := m.contentHeight()
	innerW := max(w-4, 20)
	innerH := max(h-4, 5)

	title := styles.Title.Render(fmt.Sprintf("Step %d: %s", int(m.step)+1, tutorialStepLabels[m.step]))
	explanation := renderMarkdown(stepExplanations[m.step], innerW)

	content := title + "\n\n" + explanation
	content = truncateToHeight(content, innerH)

	return styles.PanelFocused.
		Width(w).
		Height(h).
		Render(content)
}

// ---------------------------------------------------------------------------
// View: Right Panel (Output / Results)
// ---------------------------------------------------------------------------

func (m TutorialModel) renderRightPanel() string {
	w := m.rightPanelWidth()
	h := m.contentHeight()
	innerW := max(w-4, 20)
	innerH := max(h-4, 5)

	var content string
	switch m.step {
	case TutStepHypothesis:
		content = m.renderHypothesisRight(innerW)
	case TutStepStrategy:
		content = m.renderStrategyRight(innerW)
	case TutStepBacktest:
		content = m.renderBacktestRight(innerW, innerH)
	case TutStepOptimize:
		content = m.renderOptimizeRight(innerW)
	case TutStepValidate:
		content = m.renderValidateRight(innerW)
	case TutStepDeploy:
		content = m.renderDeployRight(innerW)
	}

	content = truncateToHeight(content, innerH)

	return styles.Panel.
		Width(w).
		Height(h).
		Render(content)
}

func (m TutorialModel) renderHypothesisRight(w int) string {
	title := styles.Bold("Hypothesis Card") + "\n\n"

	md := "```json\n" + tutorialHypothesisJSON + "\n```"
	rendered := renderMarkdown(md, w)

	result := title + rendered
	if m.hypothesisCreated {
		result += "\n" + styles.Green("Created: ") + styles.Dim(m.hypothesisPath)
	}
	return result
}

func (m TutorialModel) renderStrategyRight(w int) string {
	title := styles.Bold("Strategy Template") + "\n\n"

	md := "```python\n" + tutorialStrategyCode + "\n```"
	rendered := renderMarkdown(md, w)

	return title + rendered
}

func (m TutorialModel) renderBacktestRight(w int, h int) string {
	if m.backtestRunning {
		title := styles.Cyan("Running Backtest...") + "\n\n"
		maxLines := max(h-4, 3)
		lines := m.outputLines
		if len(lines) > maxLines {
			lines = lines[len(lines)-maxLines:]
		}
		var b strings.Builder
		for _, line := range lines {
			b.WriteString(lipgloss.NewStyle().Foreground(styles.TextSecondary).Render(line))
			b.WriteString("\n")
		}
		return title + b.String()
	}
	if m.backtestResult != nil {
		return m.renderResultsTable(w)
	}
	return styles.Dim("Press Enter to run the backtest")
}

func (m TutorialModel) renderResultsTable(w int) string {
	r := m.backtestResult
	title := styles.Bold("Backtest Results") + "\n"
	title += styles.Divider(min(w, 30)) + "\n\n"

	labelStyle := lipgloss.NewStyle().Foreground(styles.TextSecondary).Width(16)
	valStyle := lipgloss.NewStyle().Foreground(styles.TextPrimary).Bold(true)

	rows := []struct {
		label string
		value string
		color lipgloss.Color
	}{
		{"Strategy", r.StrategyName, styles.TextPrimary},
		{"Sharpe Ratio", fmt.Sprintf("%.2f", r.Sharpe), colorForSharpe(r.Sharpe)},
		{"Max Drawdown", fmt.Sprintf("-%.2f%%", r.MaxDrawdown), styles.StatusError},
		{"Win Rate", fmt.Sprintf("%.1f%%", r.WinRate), styles.TextPrimary},
		{"Trades", fmt.Sprintf("%d", r.TradeCount), styles.TextPrimary},
		{"Profit Factor", fmt.Sprintf("%.2f", r.ProfitFactor), colorForPF(r.ProfitFactor)},
		{"Total Return", fmt.Sprintf("+%.2f%%", r.TotalReturn), styles.StatusOK},
		{"Avg Trade", fmt.Sprintf("$%.2f", r.AvgTrade), colorForAvgTrade(r.AvgTrade)},
	}

	var b strings.Builder
	b.WriteString(title)
	for _, row := range rows {
		label := labelStyle.Render(row.label)
		val := valStyle.Foreground(row.color).Render(row.value)
		b.WriteString(label + " " + val + "\n")
	}
	return b.String()
}

func (m TutorialModel) renderOptimizeRight(w int) string {
	title := styles.Bold("Walk-Forward Results") + "\n"
	title += styles.Divider(min(w, 30)) + "\n\n"

	paramStyle := lipgloss.NewStyle().Foreground(styles.AccentSecondary)
	title += paramStyle.Render("Parameter Grid:") + "\n"
	title += styles.Dim("  fast_period: [10, 15, 20, 25, 30]") + "\n"
	title += styles.Dim("  slow_period: [30, 40, 50, 60, 80]") + "\n\n"

	windowStyle := lipgloss.NewStyle().Foreground(styles.TextSecondary)
	trainStyle := lipgloss.NewStyle().Foreground(styles.AccentPrimary)
	testStyle := lipgloss.NewStyle().Foreground(styles.AccentGold)

	title += windowStyle.Render("Walk-Forward (4 windows):") + "\n"
	windows := []struct {
		train float64
		test  float64
	}{
		{1.82, 1.35},
		{1.91, 1.48},
		{1.74, 1.29},
		{2.01, 1.56},
	}
	for i, win := range windows {
		title += fmt.Sprintf("  Window %d: ", i+1)
		title += trainStyle.Render(fmt.Sprintf("Train %.2f", win.train))
		title += styles.Dim(" -> ")
		title += testStyle.Render(fmt.Sprintf("Test %.2f", win.test))
		title += "\n"
	}
	title += "\n"
	title += styles.Dim("Avg OOS Decay: ") + styles.Green("18.2%") + "\n"
	title += styles.Dim("Best Params:   ") + styles.Cyan("fast=20, slow=50") + "\n"
	return title
}

func (m TutorialModel) renderValidateRight(w int) string {
	title := styles.Bold("Anti-Overfitting Gates") + "\n"
	title += styles.Divider(min(w, 30)) + "\n\n"

	if m.backtestResult == nil {
		return title + styles.Dim("No backtest results available")
	}

	r := m.backtestResult
	type gate struct {
		name   string
		value  string
		thresh string
		pass   bool
	}

	gates := []gate{
		{
			name:   "Sharpe < 3.0",
			value:  fmt.Sprintf("%.2f", r.Sharpe),
			thresh: "not too good to be true",
			pass:   r.Sharpe < 3.0,
		},
		{
			name:   "Win Rate < 80%",
			value:  fmt.Sprintf("%.1f%%", r.WinRate),
			thresh: "realistic win rate",
			pass:   r.WinRate < 80.0,
		},
		{
			name:   "Trades >= 100",
			value:  fmt.Sprintf("%d", r.TradeCount),
			thresh: "statistically significant",
			pass:   r.TradeCount >= 100,
		},
		{
			name:   "OOS Decay < 50%",
			value:  fmt.Sprintf("%.1f%%", r.OOSDecay),
			thresh: "holds on unseen data",
			pass:   r.OOSDecay < 50.0,
		},
	}

	passed := 0
	var b strings.Builder
	b.WriteString(title)

	for _, g := range gates {
		var icon, status string
		if g.pass {
			icon = lipgloss.NewStyle().Foreground(styles.StatusOK).Render("PASS")
			status = styles.Green(g.value)
			passed++
		} else {
			icon = lipgloss.NewStyle().Foreground(styles.StatusError).Render("FAIL")
			status = styles.Red(g.value)
		}
		gateLabel := lipgloss.NewStyle().Foreground(styles.TextSecondary).Width(18).Render(g.name)
		reason := styles.Dim("(" + g.thresh + ")")
		b.WriteString(icon + "  " + gateLabel + " " + status + " " + reason + "\n")
	}

	b.WriteString("\n" + styles.Divider(min(w, 30)) + "\n")

	total := len(gates)
	summary := fmt.Sprintf("%d/%d PASSED", passed, total)
	if passed == total {
		b.WriteString(styles.Green("Result: "+summary) + " -- Strategy ")
		b.WriteString(lipgloss.NewStyle().Foreground(styles.StatusOK).Bold(true).Render("APPROVED"))
	} else {
		b.WriteString(styles.Red("Result: "+summary) + " -- Strategy ")
		b.WriteString(lipgloss.NewStyle().Foreground(styles.StatusError).Bold(true).Render("REJECTED"))
	}
	b.WriteString("\n")
	return b.String()
}

func (m TutorialModel) renderDeployRight(w int) string {
	titleStyle := lipgloss.NewStyle().Foreground(styles.AccentGold).Bold(true)

	var b strings.Builder
	b.WriteString(titleStyle.Render("Tutorial Complete!") + "\n\n")

	b.WriteString(styles.Bold("Pipeline Learned:") + "\n")
	pipelineSteps := []string{
		"Hypothesis  - Define your trading idea",
		"Strategy    - Code the entry/exit logic",
		"Backtest    - Replay on historical data",
		"Optimize    - Walk-forward parameter search",
		"Validate    - Anti-overfitting gates",
		"Deploy      - Export to Freqtrade",
	}
	for i, ps := range pipelineSteps {
		num := lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).
			Render(fmt.Sprintf("%d.", i+1))
		b.WriteString("  " + num + " " + styles.Dim(ps) + "\n")
	}

	b.WriteString("\n" + styles.Divider(min(w, 30)) + "\n\n")
	b.WriteString(styles.Bold("Next Steps:") + "\n")
	b.WriteString("  " + styles.Cyan("$ sigma-quant start") + "\n")
	b.WriteString("    " + styles.Dim("Launch the full research pipeline") + "\n")
	b.WriteString("  " + styles.Cyan("$ sigma-quant status") + "\n")
	b.WriteString("    " + styles.Dim("Check pipeline health and queue depths") + "\n")
	b.WriteString("  " + styles.Cyan("$ sigma-quant strategies list") + "\n")
	b.WriteString("    " + styles.Dim("Browse validated strategies") + "\n")
	b.WriteString("\n")
	b.WriteString(lipgloss.NewStyle().Foreground(styles.AccentGold).
		Render("Press Enter to exit the tutorial."))
	return b.String()
}

// ---------------------------------------------------------------------------
// Step Content: Explanations (Markdown)
// ---------------------------------------------------------------------------

var stepExplanations = [tutorialTotalSteps]string{
	// 0: Hypothesis
	`## What is a Hypothesis?

A **hypothesis** is a testable trading idea. Before
writing any code, you define:

- **Market** -- Which instrument (ES, NQ, BTC/USDT)
- **Timeframe** -- Bar interval (5m, 15m, 1h)
- **Edge** -- Why this should work
- **Entry/Exit** -- Rough conditions

The Sigma-Quant pipeline starts with hypothesis cards
in ` + "`queues/hypotheses/`" + `. An AI researcher
evaluates each one and routes promising ideas to
strategy conversion.

A sample hypothesis has been created for you.`,

	// 1: Strategy
	`## Strategy Structure

A strategy is a Python class in Freqtrade format
with standardized methods:

- **populate_indicators()** -- Add technical indicators
- **populate_entry_trend()** -- Define entry conditions
- **populate_exit_trend()** -- Define exit conditions
- **config** -- Parameters (SMA period, risk, etc.)

Strategies are portable: the same class can run
backtests or live trading on Freqtrade.

The panel on the right shows a complete strategy
template using SMA crossover logic.`,

	// 2: Backtest
	`## Backtesting

Backtesting replays historical data through your
strategy to measure performance **before risking
real capital**.

### Key Metrics

- **Sharpe Ratio** -- Risk-adjusted return (1.0-3.0)
- **Max Drawdown** -- Worst peak-to-trough decline
- **Win Rate** -- Percentage of winning trades
- **Trade Count** -- Sample size (min 100)
- **Profit Factor** -- Gross profit / gross loss

Higher Sharpe is better, but suspiciously high
values (>3.0) often indicate overfitting.

The backtest is running now. Watch the output
on the right panel.`,

	// 3: Optimize
	`## Walk-Forward Optimization

Optimization finds the best parameters, but
**overfitting is the number one risk**.

Walk-forward validation fights this:

1. Split data into windows
   (e.g. 6 months train, 2 months test)
2. Optimize parameters on the train window
3. Validate on the unseen test window
4. Slide forward and repeat

### OOS Decay

**Out-of-Sample Decay** measures how much
performance drops on unseen data. High decay
(>50%) signals overfitting.

The right panel shows walk-forward results
from a 4-window analysis.`,

	// 4: Validate
	`## Anti-Overfitting Gates

Before any strategy goes live, it must pass
these automated validation gates:

| Gate | Why |
|------|-----|
| Sharpe < 3.0 | Too-good = overfit |
| Win Rate < 80% | Unrealistic rate |
| Trades >= 100 | Statistical significance |
| OOS Decay < 50% | Must hold OOS |

Strategies failing **any** gate are rejected.
This prevents curve-fitted strategies from
reaching production.

The right panel shows validation results
from your backtest.`,

	// 5: Deploy
	`## Deployment

Validated strategies are exported to Freqtrade
format for live or paper trading:

1. **Strategy class** with optimized parameters
2. **Config JSON** with exchange/pair settings
3. **Docker compose** for containerized execution

### The Full Pipeline

You have now seen the complete Sigma-Quant
workflow:

> Hypothesis -> Strategy -> Backtest ->
> Optimize -> Validate -> Deploy

Each step is automated by AI agents that run
continuously. You define the hypotheses; the
agents do the rest.`,
}

// ---------------------------------------------------------------------------
// Sample Data
// ---------------------------------------------------------------------------

const tutorialHypothesisJSON = `{
  "id": "tutorial-sma-crossover",
  "market": "ES",
  "timeframe": "15m",
  "hypothesis": "SMA 20/50 crossover captures trend on ES during NY session",
  "edge": "Trend-following with dual moving average in high-volume hours",
  "entry_rule": "Fast SMA(20) crosses above Slow SMA(50)",
  "exit_rule": "Fast SMA crosses below Slow SMA OR 2% trailing stop",
  "risk_per_trade": "1%",
  "confidence": "medium",
  "source": "tutorial",
  "created_by": "sigma-quant tutorial"
}`

const tutorialStrategyCode = `class TutorialSMACrossover(IStrategy):
    """SMA crossover -- Sigma-Quant tutorial."""

    INTERFACE_VERSION = 3
    minimal_roi = {"0": 0.05, "30": 0.025}
    stoploss = -0.02
    timeframe = "15m"

    fast_period = IntParameter(10, 30, default=20)
    slow_period = IntParameter(30, 100, default=50)

    def populate_indicators(self, df, metadata):
        df["sma_fast"] = ta.sma(
            df["close"], self.fast_period.value
        )
        df["sma_slow"] = ta.sma(
            df["close"], self.slow_period.value
        )
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[
            (df["sma_fast"] > df["sma_slow"])
            & (df["sma_fast"].shift(1)
               <= df["sma_slow"].shift(1)),
            "enter_long",
        ] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        df.loc[
            (df["sma_fast"] < df["sma_slow"])
            & (df["sma_fast"].shift(1)
               >= df["sma_slow"].shift(1)),
            "exit_long",
        ] = 1
        return df`

// ---------------------------------------------------------------------------
// Simulated Data
// ---------------------------------------------------------------------------

func simulatedOutputLines() []string {
	return []string{
		"Loading strategy: Tutorial_SMA_Crossover",
		"Loading data: ES mini futures, 15m bars",
		"Date range: 2023-01-01 to 2024-01-01",
		"Initializing backtest engine...",
		"Computing indicators: SMA(20), SMA(50)",
		"Simulating trades...",
		"  Bar  1000/5040 [====              ] 20%",
		"  Bar  2000/5040 [========          ] 40%",
		"  Bar  3000/5040 [============      ] 60%",
		"  Bar  4000/5040 [================  ] 80%",
		"  Bar  5040/5040 [==================] 100%",
		"Computing performance metrics...",
		"Backtest complete. 247 trades executed.",
	}
}

func simulatedResult() *python.BacktestResult {
	return &python.BacktestResult{
		StrategyName: "Tutorial_SMA_Crossover",
		Sharpe:       1.42,
		MaxDrawdown:  12.50,
		WinRate:      55.30,
		TradeCount:   247,
		ProfitFactor: 1.68,
		OOSDecay:     18.2,
		TotalReturn:  34.70,
		AvgTrade:     42.15,
	}
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

func renderMarkdown(md string, width int) string {
	r, err := glamour.NewTermRenderer(
		glamour.WithAutoStyle(),
		glamour.WithWordWrap(width),
	)
	if err != nil {
		return md
	}
	out, err := r.Render(md)
	if err != nil {
		return md
	}
	return strings.TrimSpace(out)
}

func truncateToHeight(s string, maxLines int) string {
	lines := strings.Split(s, "\n")
	if len(lines) <= maxLines {
		return s
	}
	return strings.Join(lines[:maxLines], "\n")
}

func colorForSharpe(v float64) lipgloss.Color {
	if v >= 1.0 && v <= 3.0 {
		return styles.StatusOK
	}
	if v < 1.0 {
		return styles.StatusWarn
	}
	return styles.StatusError
}

func colorForPF(v float64) lipgloss.Color {
	if v >= 1.5 {
		return styles.StatusOK
	}
	if v >= 1.0 {
		return styles.StatusWarn
	}
	return styles.StatusError
}

func colorForAvgTrade(v float64) lipgloss.Color {
	if v > 0 {
		return styles.StatusOK
	}
	return styles.StatusError
}
