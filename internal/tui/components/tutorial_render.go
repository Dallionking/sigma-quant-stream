package components

import (
	"fmt"
	"math"
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// ---------------------------------------------------------------------------
// View data types (shared between models and views without circular import)
// ---------------------------------------------------------------------------

// ViewHypothesisForm holds hypothesis step data for rendering.
type ViewHypothesisForm struct {
	Edge         string
	Counterparty string
	Metric       string
	Timeframe    string
	Filled       bool
}

// ViewStrategyPreview holds strategy step data for rendering.
type ViewStrategyPreview struct {
	Name     string
	Code     string
	Language string
	Template string
}

// ViewBacktestMetrics holds backtest result data for rendering.
type ViewBacktestMetrics struct {
	Sharpe     float64
	WinRate    float64
	MaxDD      float64
	TradeCount int
	PF         float64
	TotalPnL   float64
	Duration   string
	Complete   bool
	Progress   float64
}

// ViewOptimizeComparison holds before/after optimization data for rendering.
type ViewOptimizeComparison struct {
	Before   ViewBacktestMetrics
	After    ViewBacktestMetrics
	Splits   int
	Complete bool
	Progress float64
}

// ViewValidationCheck holds a single validation gate result for rendering.
type ViewValidationCheck struct {
	Name   string
	Rule   string
	Value  string
	Passed bool
}

// TutorialViewState bundles all state needed for tutorial rendering.
type TutorialViewState struct {
	Hypothesis       ViewHypothesisForm
	Strategy         ViewStrategyPreview
	BacktestResult   ViewBacktestMetrics
	OptimizeResult   ViewOptimizeComparison
	ValidationChecks []ViewValidationCheck
	DeployPreview    string
	Path             string
	Market           string
	Running          bool
	Explain          bool
	SpinnerView      string
}

// ---------------------------------------------------------------------------
// Top-level step dispatcher
// ---------------------------------------------------------------------------

// RenderTutorialStep dispatches rendering to the appropriate step renderer.
func RenderTutorialStep(step int, width int, state TutorialViewState) string {
	if width <= 0 {
		width = 76
	}

	switch step {
	case 0:
		return renderHypothesisStep(state.Hypothesis, state.Market, state.Explain, width)
	case 1:
		return renderStrategyStep(state.Strategy, state.Path, state.Explain, width)
	case 2:
		return renderBacktestStep(state.BacktestResult, state.Running, state.SpinnerView, state.Explain, width)
	case 3:
		return renderOptimizeStep(state.OptimizeResult, state.Running, state.SpinnerView, state.Explain, width)
	case 4:
		return renderValidateStep(state.ValidationChecks, state.Market, state.Explain, width)
	case 5:
		return renderDeployStep(state.DeployPreview, state.Strategy.Name, state.Explain, width)
	default:
		return styles.Dim("Unknown step.")
	}
}

// ---------------------------------------------------------------------------
// STEP 1: Hypothesis
// ---------------------------------------------------------------------------

func renderHypothesisStep(form ViewHypothesisForm, market string, explain bool, w int) string {
	var sections []string

	// Step title.
	sections = append(sections, stepTitle("HYPOTHESIS", "Let's create your first trading hypothesis."))
	sections = append(sections, "")

	if explain {
		explainBox := renderExplainBox(
			"What is a hypothesis?",
			"A trading hypothesis is a testable statement about market behavior.\n"+
				"Every good hypothesis needs three things:\n"+
				"  1. An edge   -- why you think this works\n"+
				"  2. A counterparty -- who is on the other side of your trade\n"+
				"  3. Expected metrics -- what success looks like (Sharpe, DD, etc.)",
			w,
		)
		sections = append(sections, explainBox)
		sections = append(sections, "")
	}

	// Market selector.
	marketLine := styles.Label.Render("  Market: ")
	markets := []struct {
		key   string
		label string
	}{
		{"futures", "Futures"},
		{"crypto-cex", "Crypto CEX"},
		{"crypto-dex", "Crypto DEX"},
	}
	var mParts []string
	for _, m := range markets {
		if m.key == market {
			mParts = append(mParts, lipgloss.NewStyle().
				Foreground(styles.AccentPrimary).Bold(true).
				Render("["+m.label+"]"))
		} else {
			mParts = append(mParts, styles.Dim(m.label))
		}
	}
	sections = append(sections, marketLine+strings.Join(mParts, styles.Dim("  |  ")))
	sections = append(sections, "")

	// Hypothesis form fields.
	fields := []struct {
		label string
		value string
	}{
		{"Edge", form.Edge},
		{"Counterparty", form.Counterparty},
		{"Target Metrics", form.Metric},
		{"Timeframe", form.Timeframe},
	}

	formStyle := lipgloss.NewStyle().
		Background(styles.BgSurface).
		Border(styles.RoundedBorder).
		BorderForeground(styles.BorderNormal).
		Padding(1).
		Width(w - 4)

	var formLines []string
	for _, f := range fields {
		label := lipgloss.NewStyle().
			Foreground(styles.AccentPrimary).
			Bold(true).
			Width(18).
			Render(f.label + ":")

		value := lipgloss.NewStyle().
			Foreground(styles.TextPrimary).
			Render(f.value)

		formLines = append(formLines, "  "+label+" "+value)
	}

	sections = append(sections, formStyle.Render(lipgloss.JoinVertical(lipgloss.Left, formLines...)))
	sections = append(sections, "")

	// Example callout.
	exampleStyle := lipgloss.NewStyle().
		Foreground(styles.TextMuted).
		Italic(true).
		PaddingLeft(2)
	sections = append(sections, exampleStyle.Render(
		"Example: Funding rate mean-reversion on BTC/USDT perps"))
	sections = append(sections, exampleStyle.Render(
		"Saved to: queues/hypotheses/funding_rate_mr.yaml"))

	if form.Filled {
		sections = append(sections, "")
		sections = append(sections, lipgloss.NewStyle().
			Foreground(styles.StatusOK).Bold(true).PaddingLeft(2).
			Render("Hypothesis saved. Press Enter to continue."))
	}

	return wrapStepContent(sections, w)
}

// ---------------------------------------------------------------------------
// STEP 2: Strategy
// ---------------------------------------------------------------------------

func renderStrategyStep(preview ViewStrategyPreview, path string, explain bool, w int) string {
	var sections []string

	sections = append(sections, stepTitle("STRATEGY", "Now let's write a strategy that tests this hypothesis."))
	sections = append(sections, "")

	if explain {
		explainBox := renderExplainBox(
			"Strategy Paths",
			"Developer Path: Write your own IStrategy class with full control.\n"+
				"Trader Path:    Choose from our template gallery, no coding required.\n\n"+
				"Both paths produce a Freqtrade-compatible strategy file.",
			w,
		)
		sections = append(sections, explainBox)
		sections = append(sections, "")
	}

	// Path selector.
	pathLine := styles.Label.Render("  Path: ")
	devStyle := styles.Dim("Developer")
	traderStyle := styles.Dim("Trader")
	if path == "developer" {
		devStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render("[Developer]")
	} else {
		traderStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render("[Trader]")
	}
	sections = append(sections, pathLine+devStyle+styles.Dim("  |  ")+traderStyle)
	sections = append(sections, "")

	if path == "developer" {
		// Show code preview.
		sections = append(sections, lipgloss.NewStyle().
			Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
			Render("Strategy Code Preview"))
		sections = append(sections, styles.Divider(w-4))

		codeStyle := lipgloss.NewStyle().
			Background(styles.BgSurface).
			Foreground(styles.TextPrimary).
			Border(styles.ThinBorder).
			BorderForeground(styles.BorderNormal).
			Padding(0, 1).
			Width(w - 6)

		// Syntax highlight keywords in cyan.
		code := highlightPython(preview.Code, w-8)
		sections = append(sections, codeStyle.Render(code))
	} else {
		// Template gallery for trader path.
		sections = append(sections, lipgloss.NewStyle().
			Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
			Render("Template Gallery"))
		sections = append(sections, styles.Divider(w-4))

		templates := []struct {
			name string
			desc string
		}{
			{"mean_reversion", "Funding rate / basis mean-reversion"},
			{"momentum", "Trend-following with ATR trailing stop"},
			{"breakout", "Bollinger Band squeeze breakout"},
			{"grid", "Grid trading with dynamic spacing"},
		}

		for i, t := range templates {
			marker := "  "
			nameStyle := lipgloss.NewStyle().Foreground(styles.TextPrimary)
			if t.name == preview.Template {
				marker = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render("> ")
				nameStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true)
			}
			desc := styles.Dim(t.desc)

			bg := styles.BgPanel
			if i%2 != 0 {
				bg = styles.BgSurface
			}
			row := lipgloss.NewStyle().Background(bg).Width(w - 6).Render(
				marker + nameStyle.Render(t.name) + "  " + desc,
			)
			sections = append(sections, row)
		}
	}

	sections = append(sections, "")
	sections = append(sections, lipgloss.NewStyle().
		Foreground(styles.TextMuted).Italic(true).PaddingLeft(2).
		Render(fmt.Sprintf("Strategy: %s  |  File: strategies/%s.py", preview.Name, preview.Name)))

	return wrapStepContent(sections, w)
}

// ---------------------------------------------------------------------------
// STEP 3: Backtest
// ---------------------------------------------------------------------------

func renderBacktestStep(result ViewBacktestMetrics, running bool, spinnerView string, explain bool, w int) string {
	var sections []string

	sections = append(sections, stepTitle("BACKTEST", "Running backtest on historical data..."))
	sections = append(sections, "")

	if explain {
		explainBox := renderExplainBox(
			"What is backtesting?",
			"Backtesting replays your strategy against historical market data.\n"+
				"It measures how the strategy would have performed in the past.\n\n"+
				"Key metrics:\n"+
				"  Sharpe Ratio -- risk-adjusted return (>1.0 is good, >2.0 is great)\n"+
				"  Win Rate     -- % of trades that are profitable\n"+
				"  Max Drawdown -- worst peak-to-trough decline\n"+
				"  Profit Factor -- gross profit / gross loss (>1.5 is good)",
			w,
		)
		sections = append(sections, explainBox)
		sections = append(sections, "")
	}

	if running || !result.Complete {
		// Simulation in progress.
		pct := int(result.Progress * 100)
		barWidth := w - 20
		if barWidth < 10 {
			barWidth = 10
		}
		filled := int(float64(barWidth) * result.Progress)
		empty := barWidth - filled

		bar := lipgloss.NewStyle().Foreground(styles.AccentPrimary).Render(strings.Repeat("━", filled)) +
			lipgloss.NewStyle().Foreground(styles.TextMuted).Render(strings.Repeat("─", empty))

		sections = append(sections, fmt.Sprintf("  %s Backtesting... %d%%", spinnerView, pct))
		sections = append(sections, "  "+bar)
		sections = append(sections, "")

		// Stream partial metrics as they "appear".
		if result.Progress > 0.3 {
			sections = append(sections, styles.Dim("  Trades processed: ")+
				styles.Bold(fmt.Sprintf("%d", int(float64(result.TradeCount)*result.Progress))))
		}
		if result.Progress > 0.6 {
			sections = append(sections, styles.Dim("  Current Sharpe: ")+
				styles.Cyan(fmt.Sprintf("%.2f", result.Sharpe*result.Progress*1.1)))
		}

		sections = append(sections, "")
		sections = append(sections, styles.Dim("  Press Enter to start backtest simulation."))
	} else {
		// Results complete.
		sections = append(sections, lipgloss.NewStyle().
			Foreground(styles.StatusOK).Bold(true).PaddingLeft(2).
			Render("Backtest Complete"))
		sections = append(sections, styles.Divider(w-4))
		sections = append(sections, "")

		// Metric gauges row.
		gauges := []MetricGauge{
			{Label: "Sharpe", Value: result.Sharpe, Format: "%.2f", Thresholds: [2]float64{1.0, 0.5}, HighIsGood: true},
			{Label: "Win Rate", Value: result.WinRate, Format: "%.1f%%", Thresholds: [2]float64{50.0, 40.0}, HighIsGood: true},
			{Label: "Max DD", Value: result.MaxDD, Format: "%.1f%%", Thresholds: [2]float64{10.0, 20.0}, HighIsGood: false},
			{Label: "Profit Factor", Value: result.PF, Format: "%.2f", Thresholds: [2]float64{1.5, 1.0}, HighIsGood: true},
		}

		var gaugeRendered []string
		for _, g := range gauges {
			gaugeRendered = append(gaugeRendered, lipgloss.NewStyle().
				Width(16).Align(lipgloss.Center).
				Render(g.Render()))
		}
		gaugeRow := lipgloss.JoinHorizontal(lipgloss.Top, gaugeRendered...)
		sections = append(sections, lipgloss.NewStyle().PaddingLeft(2).Render(gaugeRow))
		sections = append(sections, "")

		// Summary line.
		sep := styles.Dim("  |  ")
		summaryLine := "  " +
			styles.Label.Render("Trades: ") + styles.Bold(fmt.Sprintf("%d", result.TradeCount)) + sep +
			styles.Label.Render("PnL: ") + lipgloss.NewStyle().Foreground(styles.StatusOK).Bold(true).Render(fmt.Sprintf("$%.0f", result.TotalPnL)) + sep +
			styles.Label.Render("Duration: ") + styles.Bold(result.Duration)
		sections = append(sections, summaryLine)

		if explain {
			sections = append(sections, "")
			sections = append(sections, renderMetricExplanations(result, w))
		}
	}

	return wrapStepContent(sections, w)
}

// ---------------------------------------------------------------------------
// STEP 4: Optimize
// ---------------------------------------------------------------------------

func renderOptimizeStep(result ViewOptimizeComparison, running bool, spinnerView string, explain bool, w int) string {
	var sections []string

	sections = append(sections, stepTitle("OPTIMIZE", "Let's optimize parameters using walk-forward validation."))
	sections = append(sections, "")

	if explain {
		explainBox := renderExplainBox(
			"Walk-Forward Optimization",
			"Walk-forward splits data into train/test windows:\n"+
				"  1. Train on window 1 -> test on window 2\n"+
				"  2. Train on windows 1-2 -> test on window 3\n"+
				"  3. Continue expanding...\n\n"+
				"This detects overfitting by verifying out-of-sample performance.\n"+
				"If optimized params only work in-sample, they get flagged.",
			w,
		)
		sections = append(sections, explainBox)
		sections = append(sections, "")
	}

	if running || !result.Complete {
		// Simulation in progress.
		pct := int(result.Progress * 100)
		barWidth := w - 20
		if barWidth < 10 {
			barWidth = 10
		}
		filled := int(float64(barWidth) * result.Progress)
		empty := barWidth - filled

		bar := lipgloss.NewStyle().Foreground(styles.AccentGold).Render(strings.Repeat("━", filled)) +
			lipgloss.NewStyle().Foreground(styles.TextMuted).Render(strings.Repeat("─", empty))

		currentSplit := int(math.Ceil(float64(result.Splits) * result.Progress))
		if currentSplit > result.Splits {
			currentSplit = result.Splits
		}

		sections = append(sections, fmt.Sprintf("  %s Optimizing... %d%%  (Split %d/%d)",
			spinnerView, pct, currentSplit, result.Splits))
		sections = append(sections, "  "+bar)
		sections = append(sections, "")

		// Show train/test window visualization.
		if result.Progress > 0.2 {
			sections = append(sections, renderWalkForwardDiagram(currentSplit, result.Splits, w))
		}

		sections = append(sections, "")
		sections = append(sections, styles.Dim("  Press Enter to start optimization simulation."))
	} else {
		// Results complete.
		sections = append(sections, lipgloss.NewStyle().
			Foreground(styles.StatusOK).Bold(true).PaddingLeft(2).
			Render("Optimization Complete"))
		sections = append(sections, styles.Divider(w-4))
		sections = append(sections, "")

		// Before/After comparison table.
		sections = append(sections, renderComparisonTable(result.Before, result.After, w))
		sections = append(sections, "")

		// Walk-forward diagram.
		sections = append(sections, lipgloss.NewStyle().
			Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
			Render("Walk-Forward Splits"))
		sections = append(sections, renderWalkForwardDiagram(result.Splits, result.Splits, w))
	}

	return wrapStepContent(sections, w)
}

// ---------------------------------------------------------------------------
// STEP 5: Validate
// ---------------------------------------------------------------------------

func renderValidateStep(checks []ViewValidationCheck, market string, explain bool, w int) string {
	var sections []string

	sections = append(sections, stepTitle("VALIDATE", "Running anti-overfitting gates + compliance..."))
	sections = append(sections, "")

	if explain {
		explainBox := renderExplainBox(
			"Why Validation Gates?",
			"Anti-overfitting gates catch strategies that look too good:\n"+
				"  - Sharpe > 3.0 is suspicious (likely curve-fit)\n"+
				"  - Win rate > 80% is suspicious (likely curve-fit)\n"+
				"  - High OOS decay means it only works in-sample\n\n"+
				"Compliance checks ensure the strategy meets exchange/prop firm rules.",
			w,
		)
		sections = append(sections, explainBox)
		sections = append(sections, "")
	}

	// Validation checklist.
	sections = append(sections, lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
		Render("Anti-Overfitting Gates"))
	sections = append(sections, styles.Divider(w-4))

	allPassed := true
	for _, check := range checks {
		icon := lipgloss.NewStyle().Foreground(styles.StatusOK).Render("[PASS]")
		if !check.Passed {
			icon = lipgloss.NewStyle().Foreground(styles.StatusError).Render("[FAIL]")
			allPassed = false
		}

		name := lipgloss.NewStyle().Foreground(styles.TextPrimary).Bold(true).Width(18).Render(check.Name)
		rule := lipgloss.NewStyle().Foreground(styles.TextMuted).Width(20).Render(check.Rule)
		value := lipgloss.NewStyle().Foreground(styles.TextSecondary).Width(10).Render(check.Value)

		sections = append(sections, fmt.Sprintf("  %s  %s  %s  %s", icon, name, rule, value))
	}

	sections = append(sections, "")

	// Compliance validator.
	validatorName := "Prop Firm Validator"
	if strings.Contains(market, "crypto") {
		validatorName = "Exchange Validator"
	}

	sections = append(sections, lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
		Render(validatorName))
	sections = append(sections, styles.Divider(w-4))

	complianceChecks := getComplianceChecks(market)
	for _, check := range complianceChecks {
		icon := lipgloss.NewStyle().Foreground(styles.StatusOK).Render("[PASS]")
		name := lipgloss.NewStyle().Foreground(styles.TextPrimary).Bold(true).Width(22).Render(check.name)
		detail := lipgloss.NewStyle().Foreground(styles.TextMuted).Render(check.detail)
		sections = append(sections, fmt.Sprintf("  %s  %s  %s", icon, name, detail))
	}

	sections = append(sections, "")

	if allPassed {
		sections = append(sections, lipgloss.NewStyle().
			Foreground(styles.StatusOK).Bold(true).PaddingLeft(2).
			Render("All gates passed. Strategy is validated."))
	} else {
		sections = append(sections, lipgloss.NewStyle().
			Foreground(styles.StatusError).Bold(true).PaddingLeft(2).
			Render("Some gates failed. Review and adjust parameters."))
	}

	return wrapStepContent(sections, w)
}

// ---------------------------------------------------------------------------
// STEP 6: Deploy
// ---------------------------------------------------------------------------

func renderDeployStep(preview string, strategyName string, explain bool, w int) string {
	var sections []string

	sections = append(sections, stepTitle("DEPLOY", "Exporting to Freqtrade for paper trading..."))
	sections = append(sections, "")

	if explain {
		explainBox := renderExplainBox(
			"Paper Trading First",
			"Never go live without paper trading first.\n"+
				"Paper trading uses real market data with simulated execution.\n"+
				"Run for at least 2 weeks before considering live deployment.",
			w,
		)
		sections = append(sections, explainBox)
		sections = append(sections, "")
	}

	// Deploy preview.
	sections = append(sections, lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
		Render("Generated Files"))
	sections = append(sections, styles.Divider(w-4))

	codeStyle := lipgloss.NewStyle().
		Background(styles.BgSurface).
		Foreground(styles.TextSecondary).
		Border(styles.ThinBorder).
		BorderForeground(styles.BorderNormal).
		Padding(0, 1).
		Width(w - 6)

	sections = append(sections, codeStyle.Render(preview))
	sections = append(sections, "")

	// Next steps.
	sections = append(sections, lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
		Render("Next Steps"))
	sections = append(sections, styles.Divider(w-4))

	steps := []struct {
		cmd  string
		desc string
	}{
		{"sigma-quant deploy --strategy " + strategyName + " --mode paper", "Start paper trading"},
		{"sigma-quant monitor --strategy " + strategyName, "Monitor live performance"},
		{"sigma-quant report --strategy " + strategyName, "Generate performance report"},
		{"sigma-quant deploy --strategy " + strategyName + " --mode live", "Go live (when ready)"},
	}

	for i, s := range steps {
		num := lipgloss.NewStyle().Foreground(styles.AccentGold).Bold(true).
			Render(fmt.Sprintf("%d.", i+1))
		cmd := lipgloss.NewStyle().Foreground(styles.AccentPrimary).Render(s.cmd)
		desc := styles.Dim(s.desc)
		sections = append(sections, fmt.Sprintf("  %s %s", num, cmd))
		sections = append(sections, fmt.Sprintf("     %s", desc))
	}

	sections = append(sections, "")

	// Celebration.
	sections = append(sections, renderCelebration(w))

	return wrapStepContent(sections, w)
}

// ---------------------------------------------------------------------------
// Progress bar at the bottom of the tutorial
// ---------------------------------------------------------------------------

// RenderTutorialProgress renders the step indicator bar at the bottom.
func RenderTutorialProgress(step, total int, labels []string, w int) string {
	if w <= 0 {
		w = 80
	}

	// Build: STEP 3/6 ━━━━━━━━━━○○ BACKTEST
	prefix := lipgloss.NewStyle().
		Foreground(styles.TextSecondary).
		Bold(true).
		Render(fmt.Sprintf("STEP %d/%d ", step+1, total))

	// Progress dots.
	var dots []string
	for i := 0; i < total; i++ {
		switch {
		case i < step:
			dots = append(dots, lipgloss.NewStyle().Foreground(styles.StatusOK).Render("━━"))
		case i == step:
			dots = append(dots, lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render("━━"))
		default:
			dots = append(dots, lipgloss.NewStyle().Foreground(styles.TextMuted).Render("──"))
		}
	}
	bar := strings.Join(dots, "")

	// Current step label.
	label := ""
	if step < len(labels) {
		label = lipgloss.NewStyle().
			Foreground(styles.AccentPrimary).
			Bold(true).
			Render(" " + labels[step])
	}

	content := prefix + bar + label

	progressStyle := lipgloss.NewStyle().
		Background(styles.BgDeep).
		Width(w).
		PaddingLeft(1).
		PaddingRight(1)

	return progressStyle.Render(content)
}

// ---------------------------------------------------------------------------
// Helper renderers
// ---------------------------------------------------------------------------

// stepTitle renders a consistent step title block.
func stepTitle(name string, description string) string {
	title := lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).
		Bold(true).
		Render("  " + name)

	desc := lipgloss.NewStyle().
		Foreground(styles.TextSecondary).
		Render("  " + description)

	return lipgloss.JoinVertical(lipgloss.Left, title, desc)
}

// renderExplainBox renders an educational callout box.
func renderExplainBox(title string, body string, w int) string {
	headerStyle := lipgloss.NewStyle().
		Foreground(styles.AccentGold).
		Bold(true)

	bodyStyle := lipgloss.NewStyle().
		Foreground(styles.TextSecondary)

	content := headerStyle.Render(title) + "\n" + bodyStyle.Render(body)

	boxStyle := lipgloss.NewStyle().
		Background(styles.BgSurface).
		Border(styles.RoundedBorder).
		BorderForeground(styles.AccentGold).
		Padding(0, 1).
		Width(w - 6).
		MarginLeft(2)

	return boxStyle.Render(content)
}

// wrapStepContent wraps step content in a panel.
func wrapStepContent(sections []string, w int) string {
	content := lipgloss.JoinVertical(lipgloss.Left, sections...)

	panelStyle := lipgloss.NewStyle().
		Background(styles.BgPanel).
		Width(w).
		Padding(1, 0)

	return panelStyle.Render(content)
}

// highlightPython does minimal keyword highlighting for Python code.
func highlightPython(code string, maxWidth int) string {
	keywords := []string{
		"class", "def", "return", "import", "from", "if", "else", "elif",
		"for", "in", "True", "False", "None", "self",
	}

	lines := strings.Split(code, "\n")
	var highlighted []string

	for _, line := range lines {
		if maxWidth > 0 && len(line) > maxWidth {
			line = line[:maxWidth-3] + "..."
		}

		// Highlight comments in muted.
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "#") || strings.HasPrefix(trimmed, `"""`) {
			highlighted = append(highlighted, lipgloss.NewStyle().
				Foreground(styles.TextMuted).Render(line))
			continue
		}

		// Highlight keywords in cyan.
		result := line
		for _, kw := range keywords {
			// Only match whole words by checking boundaries.
			result = highlightKeyword(result, kw)
		}

		highlighted = append(highlighted, result)
	}

	return strings.Join(highlighted, "\n")
}

// highlightKeyword highlights a keyword in a line using cyan.
func highlightKeyword(line string, keyword string) string {
	// Simple boundary-aware replacement.
	boundaries := " \t(.,:=[]{})"
	idx := 0
	var result strings.Builder

	for idx < len(line) {
		pos := strings.Index(line[idx:], keyword)
		if pos == -1 {
			result.WriteString(line[idx:])
			break
		}

		absPos := idx + pos
		endPos := absPos + len(keyword)

		// Check boundaries.
		leftOK := absPos == 0 || strings.ContainsRune(boundaries, rune(line[absPos-1]))
		rightOK := endPos >= len(line) || strings.ContainsRune(boundaries, rune(line[endPos]))

		if leftOK && rightOK {
			result.WriteString(line[idx:absPos])
			result.WriteString(lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render(keyword))
			idx = endPos
		} else {
			result.WriteString(line[idx : absPos+1])
			idx = absPos + 1
		}
	}

	return result.String()
}

// renderMetricExplanations renders educational annotations for backtest metrics.
func renderMetricExplanations(result ViewBacktestMetrics, w int) string {
	var lines []string

	lines = append(lines, lipgloss.NewStyle().
		Foreground(styles.AccentGold).Bold(true).PaddingLeft(2).
		Render("What do these numbers mean?"))

	explanations := []struct {
		metric string
		value  string
		note   string
	}{
		{"Sharpe " + fmt.Sprintf("%.2f", result.Sharpe),
			"",
			"Risk-adjusted return. Above 1.0 is solid; your strategy earns more per unit of risk."},
		{"Win Rate " + fmt.Sprintf("%.0f%%", result.WinRate),
			"",
			"58% means roughly 3 in 5 trades are profitable. Good strategies can be 45-65%."},
		{"Max DD " + fmt.Sprintf("%.1f%%", result.MaxDD),
			"",
			"Worst drawdown from peak equity. 14% is acceptable for most prop firms (<15%)."},
		{"Profit Factor " + fmt.Sprintf("%.2f", result.PF),
			"",
			"Gross profit / gross loss. Above 1.5 means you earn $1.50 for every $1 risked."},
	}

	for _, e := range explanations {
		metricStyle := lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true)
		noteStyle := lipgloss.NewStyle().Foreground(styles.TextMuted).Italic(true)
		lines = append(lines, "  "+metricStyle.Render(e.metric))
		lines = append(lines, "    "+noteStyle.Render(e.note))
	}

	return lipgloss.JoinVertical(lipgloss.Left, lines...)
}

// renderComparisonTable renders a before/after optimization comparison.
func renderComparisonTable(before, after ViewBacktestMetrics, w int) string {
	var lines []string

	// Table header.
	hdrStyle := lipgloss.NewStyle().Foreground(styles.TextSecondary).Bold(true)
	lines = append(lines, fmt.Sprintf("  %-18s %12s %12s %12s",
		hdrStyle.Render("METRIC"),
		hdrStyle.Render("BEFORE"),
		hdrStyle.Render("AFTER"),
		hdrStyle.Render("CHANGE"),
	))
	lines = append(lines, "  "+styles.Divider(w-6))

	rows := []struct {
		label  string
		before string
		after  string
		better bool
	}{
		{"Sharpe Ratio",
			fmt.Sprintf("%.2f", before.Sharpe),
			fmt.Sprintf("%.2f", after.Sharpe),
			after.Sharpe > before.Sharpe},
		{"Win Rate",
			fmt.Sprintf("%.1f%%", before.WinRate),
			fmt.Sprintf("%.1f%%", after.WinRate),
			after.WinRate > before.WinRate},
		{"Max Drawdown",
			fmt.Sprintf("%.1f%%", before.MaxDD),
			fmt.Sprintf("%.1f%%", after.MaxDD),
			after.MaxDD < before.MaxDD},
		{"Profit Factor",
			fmt.Sprintf("%.2f", before.PF),
			fmt.Sprintf("%.2f", after.PF),
			after.PF > before.PF},
		{"Trade Count",
			fmt.Sprintf("%d", before.TradeCount),
			fmt.Sprintf("%d", after.TradeCount),
			true},
	}

	for i, r := range rows {
		changeColor := styles.StatusOK
		changeIcon := "^"
		if !r.better {
			changeColor = styles.StatusWarn
			changeIcon = "v"
		}

		label := lipgloss.NewStyle().Foreground(styles.TextPrimary).Width(18).Render(r.label)
		beforeVal := lipgloss.NewStyle().Foreground(styles.TextMuted).Width(12).Align(lipgloss.Right).Render(r.before)
		afterVal := lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Width(12).Align(lipgloss.Right).Render(r.after)
		change := lipgloss.NewStyle().Foreground(changeColor).Bold(true).Width(12).Align(lipgloss.Right).Render(changeIcon)

		bg := styles.BgPanel
		if i%2 != 0 {
			bg = styles.BgSurface
		}

		row := lipgloss.NewStyle().Background(bg).Width(w - 4).Render(
			"  " + label + " " + beforeVal + " " + afterVal + " " + change,
		)
		lines = append(lines, row)
	}

	return lipgloss.JoinVertical(lipgloss.Left, lines...)
}

// renderWalkForwardDiagram shows a visual representation of train/test splits.
func renderWalkForwardDiagram(current, total int, w int) string {
	var lines []string

	segW := (w - 20) / total
	if segW < 4 {
		segW = 4
	}

	trainStyle := lipgloss.NewStyle().Foreground(styles.AccentPrimary)
	testStyle := lipgloss.NewStyle().Foreground(styles.AccentGold)
	futureStyle := lipgloss.NewStyle().Foreground(styles.TextMuted)

	for i := 1; i <= total; i++ {
		label := lipgloss.NewStyle().Foreground(styles.TextMuted).Width(10).
			Render(fmt.Sprintf("Split %d:", i))

		trainLen := i
		testLen := 1
		futureLen := total - i

		var seg string
		if i <= current {
			seg = trainStyle.Render(strings.Repeat("=", trainLen*segW/total)) +
				testStyle.Render(strings.Repeat("#", testLen*segW/total))
			if futureLen > 0 {
				seg += futureStyle.Render(strings.Repeat(".", futureLen*segW/total))
			}
		} else {
			seg = futureStyle.Render(strings.Repeat(".", (trainLen+testLen+futureLen)*segW/total))
		}

		lines = append(lines, "  "+label+" "+seg)
	}

	// Legend.
	legend := "  " +
		trainStyle.Render("= train") + "  " +
		testStyle.Render("# test") + "  " +
		futureStyle.Render(". pending")

	lines = append(lines, "")
	lines = append(lines, legend)

	return lipgloss.JoinVertical(lipgloss.Left, lines...)
}

// complianceCheck is an internal type for rendering compliance results.
type complianceCheck struct {
	name   string
	detail string
}

// getComplianceChecks returns market-specific compliance checks.
func getComplianceChecks(market string) []complianceCheck {
	if strings.Contains(market, "crypto") {
		return []complianceCheck{
			{"API Rate Limits", "Within exchange rate limits (10 req/s)"},
			{"Position Size", "Max position < 5% of account equity"},
			{"Leverage Limit", "Max leverage 5x (within exchange limit)"},
			{"Symbol Whitelist", "BTC/USDT is an approved trading pair"},
			{"Fee Accounting", "Maker/taker fees included in backtest"},
		}
	}

	// Futures / prop firm.
	return []complianceCheck{
		{"Daily Loss Limit", "Max daily loss < 4% of account"},
		{"Trailing Drawdown", "Max trailing DD < 5% from HWM"},
		{"Position Size", "Max position size within contract limits"},
		{"Trading Hours", "Strategy respects CME market hours"},
		{"News Filter", "Pauses 5 min before high-impact news"},
		{"Scaling Rules", "Max 3 contracts per entry"},
	}
}

// renderCelebration renders a congratulations screen.
func renderCelebration(w int) string {
	var lines []string

	border := lipgloss.NewStyle().
		Foreground(styles.AccentGold).
		Render(strings.Repeat("*", w-8))

	lines = append(lines, "  "+border)
	lines = append(lines, "")

	congrats := lipgloss.NewStyle().
		Foreground(styles.AccentGold).
		Bold(true).
		Render("  CONGRATULATIONS!")

	lines = append(lines, congrats)
	lines = append(lines, "")

	msg := lipgloss.NewStyle().
		Foreground(styles.TextPrimary).
		Render("  You've completed the full sigma-quant pipeline:")

	lines = append(lines, msg)
	lines = append(lines, "")

	pipelineSteps := []string{
		"Hypothesis  ->  Strategy  ->  Backtest  ->  Optimize  ->  Validate  ->  Deploy",
	}
	for _, s := range pipelineSteps {
		lines = append(lines, lipgloss.NewStyle().
			Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(4).
			Render(s))
	}

	lines = append(lines, "")
	lines = append(lines, lipgloss.NewStyle().
		Foreground(styles.TextSecondary).PaddingLeft(2).
		Render("Your strategy is ready for paper trading. Press Enter to exit."))

	lines = append(lines, "")
	lines = append(lines, "  "+border)

	return lipgloss.JoinVertical(lipgloss.Left, lines...)
}

// ---------------------------------------------------------------------------
// Unused import guard.
// ---------------------------------------------------------------------------

var _ = math.Ceil
