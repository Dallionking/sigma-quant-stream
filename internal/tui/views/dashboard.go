package views

import (
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/agent"
	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/queue"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/models"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// ---------------------------------------------------------------------------
// Standalone types for non-interactive rendering
// ---------------------------------------------------------------------------
//
// These types mirror the models package equivalents but are defined here so
// callers can render individual dashboard quadrants without constructing a
// full Bubble Tea StatusModel.  Useful for `sigma-quant status --once` or
// embedding dashboard snippets in other CLI output.

// DashboardWorker holds the display state of a single pipeline worker.
type DashboardWorker struct {
	Name        string // "Researcher", "Converter", "Backtester", "Optimizer"
	Icon        string // e.g. "\U0001F52C"
	State       string // "running", "idle", "stopped", "error", "starting", "stopping"
	Sessions    int
	Tasks       int
	CurrentTask string
}

// DashboardQueue holds pipeline stage depths.
type DashboardQueue struct {
	Hypotheses int
	ToConvert  int
	ToBacktest int
	ToOptimize int
}

// DashboardStrategies aggregates strategy classification counts.
type DashboardStrategies struct {
	Total    int
	Good     int
	Review   int
	Rejected int
	PropFirm int
}

// DashboardSession holds session runtime and cost information.
type DashboardSession struct {
	StartedAt       time.Time
	TasksCompleted  int
	CurrentCost     float64
	BudgetCap       float64
	PatternsLearned int
}

// DashboardActivity represents a single line in the activity feed.
type DashboardActivity struct {
	Time    time.Time
	Source  string
	Message string
	Level   string // "info", "warn", "error", "success"
}

// ---------------------------------------------------------------------------
// RunDashboard -- interactive full-screen TUI entry point
// ---------------------------------------------------------------------------

// RunDashboard launches the full-screen interactive dashboard TUI.
//
// It creates an agent.Manager in read-only mode (no workers are started)
// and a queue.Watcher for live pipeline depth updates, then runs a
// Bubble Tea program with the StatusModel in alt-screen mode.
func RunDashboard(projectRoot string) error {
	// Load config (idempotent -- may already be cached from the CLI layer).
	cfg, _ := config.Load(projectRoot)

	profile := "futures"
	if cfg != nil && cfg.ActiveProfile != "" {
		profile = cfg.ActiveProfile
	}

	// Create agent.Manager -- read-only, does not start any workers.
	mgr := agent.NewManager(projectRoot, "sigma-quant")

	// Create queue.Watcher. If queue directories cannot be watched
	// (e.g., first run before any session), proceed without live queue data.
	queuesRoot := filepath.Join(projectRoot, "queues")
	qw, err := queue.NewWatcher(queuesRoot)
	if err != nil {
		qw = nil
	}
	if qw != nil {
		defer qw.Close()
	}

	model := models.NewStatusModel(mgr, qw, projectRoot, profile)

	p := tea.NewProgram(model, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		return fmt.Errorf("running dashboard: %w", err)
	}

	return nil
}

// ---------------------------------------------------------------------------
// RunDashboardOnce -- non-interactive single-frame render
// ---------------------------------------------------------------------------

// RunDashboardOnce renders one frame of the dashboard to stdout and returns.
// Suitable for `sigma-quant status --once` or piping to other tools.
func RunDashboardOnce(projectRoot string, width int) string {
	if width < 40 {
		width = 80
	}

	workers := snapshotWorkers(projectRoot)
	queues := snapshotQueues(projectRoot)
	strats := snapshotStrategies(projectRoot)
	session := DashboardSession{
		StartedAt: time.Now(),
		BudgetCap: 50.0,
	}

	halfW := width / 2
	leftW := halfW
	rightW := width - halfW

	topRow := lipgloss.JoinHorizontal(lipgloss.Top,
		RenderWorkerQuadrant(workers, leftW),
		RenderQueueQuadrant(queues, rightW),
	)
	bottomRow := lipgloss.JoinHorizontal(lipgloss.Top,
		RenderStrategyQuadrant(strats, leftW),
		RenderSessionQuadrant(session, rightW),
	)

	return lipgloss.JoinVertical(lipgloss.Left, topRow, bottomRow)
}

// ---------------------------------------------------------------------------
// Exported standalone renderers
// ---------------------------------------------------------------------------

// RenderWorkerQuadrant renders a bordered panel with compact worker state lines.
func RenderWorkerQuadrant(workers []DashboardWorker, width int) string {
	var lines []string
	for _, w := range workers {
		nameStr := lipgloss.NewStyle().
			Foreground(styles.TextPrimary).
			Bold(true).
			Render(w.Icon + " " + w.Name)

		dotColor := dashWorkerStateColor(w.State)
		dot := lipgloss.NewStyle().Foreground(dotColor).Render("\u25CF")
		label := lipgloss.NewStyle().Foreground(dotColor).Bold(true).
			Render(dashWorkerStateLabel(w.State))

		innerW := width - 6 // border + padding
		nameLen := lipgloss.Width(nameStr)
		stateStr := dot + " " + label
		stateLen := lipgloss.Width(stateStr)
		gap := innerW - nameLen - stateLen
		if gap < 1 {
			gap = 1
		}

		lines = append(lines, nameStr+strings.Repeat(" ", gap)+stateStr)
	}

	if len(lines) == 0 {
		lines = append(lines, styles.Dim("  No workers configured"))
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return dashQuadrantPanel("Workers", content, width)
}

// RenderQueueQuadrant renders pipeline stage progress bars in a bordered panel.
func RenderQueueQuadrant(q DashboardQueue, width int) string {
	barWidth := 14
	if width > 50 {
		barWidth = width - 30
	}
	if barWidth < 6 {
		barWidth = 6
	}

	maxCount := maxInt(q.Hypotheses, q.ToConvert, q.ToBacktest, q.ToOptimize)
	if maxCount < 1 {
		maxCount = 20
	}

	lines := []string{
		dashQueueLine("hypotheses", q.Hypotheses, maxCount, barWidth),
		dashQueueLine("to-convert", q.ToConvert, maxCount, barWidth),
		dashQueueLine("to-backtest", q.ToBacktest, maxCount, barWidth),
		dashQueueLine("to-optimize", q.ToOptimize, maxCount, barWidth),
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return dashQuadrantPanel("Queue Pipeline", content, width)
}

// RenderStrategyQuadrant renders strategy counts with proportional mini-bars.
func RenderStrategyQuadrant(s DashboardStrategies, width int) string {
	total := s.Total
	if total < 1 {
		total = 1
	}

	lines := []string{
		dashStratLine("Total", s.Total, total, styles.TextPrimary),
		dashStratLine("Good", s.Good, total, styles.StatusOK),
		dashStratLine("Review", s.Review, total, styles.StatusWarn),
		dashStratLine("Rejected", s.Rejected, total, styles.StatusError),
		dashStratLine("PropFirm", s.PropFirm, total, styles.AccentGold),
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return dashQuadrantPanel("Strategies", content, width)
}

// RenderSessionQuadrant renders runtime, tasks, cost progress bar, and patterns.
func RenderSessionQuadrant(s DashboardSession, width int) string {
	runtime := dashFormatDuration(time.Since(s.StartedAt))

	costLine := dashCostText(s.CurrentCost, s.BudgetCap)
	innerBarW := width - 10
	if innerBarW < 10 {
		innerBarW = 10
	}
	costBar := dashCostBar(s.CurrentCost, s.BudgetCap, innerBarW)

	patternsStr := lipgloss.NewStyle().
		Foreground(styles.AccentSecondary).
		Bold(true).
		Render(fmt.Sprintf("+%d learned", s.PatternsLearned))

	lines := []string{
		styles.Label.Render("Runtime:  ") + styles.Value.Render(runtime),
		styles.Label.Render("Tasks:    ") + styles.Value.Render(fmt.Sprintf("%d completed", s.TasksCompleted)),
		styles.Label.Render("Cost:     ") + costLine,
		costBar,
		styles.Label.Render("Patterns: ") + patternsStr,
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return dashQuadrantPanel("Session", content, width)
}

// RenderActivityLog renders the most recent activity entries in a full-width panel.
func RenderActivityLog(entries []DashboardActivity, width, maxEntries int) string {
	if maxEntries < 1 {
		maxEntries = 5
	}

	start := 0
	if len(entries) > maxEntries {
		start = len(entries) - maxEntries
	}

	var lines []string
	for _, entry := range entries[start:] {
		ts := lipgloss.NewStyle().Foreground(styles.TextMuted).
			Render(entry.Time.Format("15:04"))
		src := lipgloss.NewStyle().Foreground(styles.AccentSecondary).
			Render(fmt.Sprintf("[%-10s]", entry.Source))
		msg := lipgloss.NewStyle().Foreground(dashActivityColor(entry.Level)).
			Render(entry.Message)
		lines = append(lines, ts+"  "+src+" "+msg)
	}

	if len(lines) == 0 {
		lines = append(lines, styles.Dim("  No recent activity"))
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return dashQuadrantPanel("Recent Activity", content, width)
}

// RenderCompactStatus returns a compact one-line status summary suitable
// for embedding in shell prompts or other minimal contexts.
func RenderCompactStatus(workers []DashboardWorker, q DashboardQueue, s DashboardStrategies) string {
	running := 0
	for _, w := range workers {
		if strings.ToLower(w.State) == "running" || strings.ToLower(w.State) == "idle" {
			running++
		}
	}

	totalQueue := q.Hypotheses + q.ToConvert + q.ToBacktest + q.ToOptimize

	workerStr := lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).
		Render(fmt.Sprintf("W:%d/%d", running, len(workers)))
	queueStr := lipgloss.NewStyle().Foreground(styles.AccentSecondary).Bold(true).
		Render(fmt.Sprintf("Q:%d", totalQueue))
	stratStr := lipgloss.NewStyle().Foreground(styles.StatusOK).Bold(true).
		Render(fmt.Sprintf("S:%d", s.Total))
	goodStr := lipgloss.NewStyle().Foreground(styles.StatusOK).
		Render(fmt.Sprintf("(%d good)", s.Good))

	sep := lipgloss.NewStyle().Foreground(styles.TextMuted).Render(" | ")

	return workerStr + sep + queueStr + sep + stratStr + " " + goodStr
}

// ---------------------------------------------------------------------------
// Data snapshot helpers (read-only filesystem queries)
// ---------------------------------------------------------------------------

// snapshotWorkers reads current worker states from the agent manager.
func snapshotWorkers(projectRoot string) []DashboardWorker {
	mgr := agent.NewManager(projectRoot, "sigma-quant")
	states := mgr.GetWorkerStates()
	workerTypes := agent.AllWorkerTypes()

	meta := [4]struct {
		Name string
		Icon string
	}{
		{"Researcher", "\U0001F52C"},
		{"Converter", "\U0001F504"},
		{"Backtester", "\U0001F4CA"},
		{"Optimizer", "\u26A1"},
	}

	workers := make([]DashboardWorker, 0, 4)
	for i, wt := range workerTypes {
		if i >= 4 {
			break
		}
		w := DashboardWorker{
			Name:  meta[i].Name,
			Icon:  meta[i].Icon,
			State: "stopped",
		}
		if rw, ok := states[wt]; ok {
			w.State = rw.State.String()
			w.Sessions = rw.SessionsRun
			w.Tasks = rw.TasksCompleted
			w.CurrentTask = rw.CurrentTask
		}
		workers = append(workers, w)
	}
	return workers
}

// snapshotQueues reads current queue depths from the filesystem.
func snapshotQueues(projectRoot string) DashboardQueue {
	queuesRoot := filepath.Join(projectRoot, "queues")
	qw, err := queue.NewWatcher(queuesRoot)
	if err != nil {
		return DashboardQueue{}
	}
	defer qw.Close()

	depths, err := qw.GetAllDepths()
	if err != nil {
		return DashboardQueue{}
	}

	var q DashboardQueue
	for _, d := range depths {
		switch d.Name {
		case queue.QueueHypotheses:
			q.Hypotheses = d.Pending
		case queue.QueueToConvert:
			q.ToConvert = d.Pending
		case queue.QueueToBacktest:
			q.ToBacktest = d.Pending
		case queue.QueueToOptimize:
			q.ToOptimize = d.Pending
		}
	}
	return q
}

// snapshotStrategies counts strategies from output directories.
func snapshotStrategies(projectRoot string) DashboardStrategies {
	base := filepath.Join(projectRoot, "output", "strategies")
	s := DashboardStrategies{
		Good:     countJSONInDir(filepath.Join(base, "good")),
		Review:   countJSONInDir(filepath.Join(base, "under_review")),
		Rejected: countJSONInDir(filepath.Join(base, "rejected")),
		PropFirm: countJSONInDir(filepath.Join(base, "prop_firm_ready")),
	}
	s.Total = s.Good + s.Review + s.Rejected + s.PropFirm
	return s
}

// countJSONInDir counts .json files in a directory (non-recursive).
func countJSONInDir(dir string) int {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return 0
	}
	n := 0
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".json") {
			n++
		}
	}
	return n
}

// ---------------------------------------------------------------------------
// Internal rendering helpers
// ---------------------------------------------------------------------------

// dashQuadrantPanel wraps content in a bordered panel with a styled title.
func dashQuadrantPanel(title string, content string, width int) string {
	titleStr := lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).
		Bold(true).
		Render(title)

	fullContent := titleStr + "\n" + content

	innerWidth := width - 4 // border (2) + padding (2)
	if innerWidth < 10 {
		innerWidth = 10
	}

	return lipgloss.NewStyle().
		Background(styles.BgPanel).
		Border(styles.RoundedBorder).
		BorderForeground(styles.BorderNormal).
		Padding(0, 1).
		Width(innerWidth).
		Render(fullContent)
}

// dashQueueLine draws a single queue stage with a proportional progress bar.
func dashQueueLine(label string, count, maxCount, barWidth int) string {
	filled := 0
	if maxCount > 0 {
		filled = int(math.Round(float64(count) / float64(maxCount) * float64(barWidth)))
	}
	if filled > barWidth {
		filled = barWidth
	}
	if filled < 0 {
		filled = 0
	}
	empty := barWidth - filled

	color := styles.AccentPrimary
	if count == 0 {
		color = styles.TextMuted
	}

	labelStr := lipgloss.NewStyle().Foreground(styles.TextSecondary).Width(12).Render(label)
	filledStr := lipgloss.NewStyle().Foreground(color).Render(strings.Repeat("\u2588", filled))
	emptyStr := lipgloss.NewStyle().Foreground(styles.TextMuted).Render(strings.Repeat("\u2591", empty))
	countStr := lipgloss.NewStyle().Foreground(styles.TextPrimary).Bold(true).
		Render(fmt.Sprintf("%3d", count))

	return labelStr + " [" + filledStr + emptyStr + "] " + countStr
}

// dashStratLine draws a strategy count line with a proportional mini-bar.
func dashStratLine(label string, count, total int, color lipgloss.Color) string {
	maxBarWidth := 10
	barLen := 0
	if total > 0 && count > 0 {
		barLen = int(math.Round(float64(count) / float64(total) * float64(maxBarWidth)))
		if barLen < 1 {
			barLen = 1
		}
	}

	bar := lipgloss.NewStyle().Foreground(color).Render(strings.Repeat("\u2588", barLen))
	labelStr := styles.Label.Width(10).Render(label + ":")
	countStr := lipgloss.NewStyle().Foreground(color).Bold(true).
		Width(4).Align(lipgloss.Right).Render(fmt.Sprintf("%d", count))

	return labelStr + countStr + "  " + bar
}

// dashCostText produces the "$X.XX / $Y.YY" cost display.
func dashCostText(current, cap float64) string {
	color := dashCostColor(current, cap)

	return lipgloss.NewStyle().Foreground(color).Bold(true).
		Render(fmt.Sprintf("$%.2f", current)) +
		lipgloss.NewStyle().Foreground(styles.TextMuted).
			Render(fmt.Sprintf(" / $%.2f", cap))
}

// dashCostBar draws a horizontal progress bar for cost/budget.
func dashCostBar(current, cap float64, barWidth int) string {
	if barWidth < 4 {
		barWidth = 4
	}
	ratio := 0.0
	if cap > 0 {
		ratio = current / cap
	}

	filled := int(math.Round(ratio * float64(barWidth)))
	if filled > barWidth {
		filled = barWidth
	}
	if filled < 0 {
		filled = 0
	}
	empty := barWidth - filled

	color := dashCostColor(current, cap)

	filledStr := lipgloss.NewStyle().Foreground(color).Render(strings.Repeat("\u2588", filled))
	emptyStr := lipgloss.NewStyle().Foreground(styles.TextMuted).Render(strings.Repeat("\u2591", empty))
	pct := lipgloss.NewStyle().Foreground(styles.TextSecondary).
		Render(fmt.Sprintf(" %.1f%%", ratio*100))

	return filledStr + emptyStr + pct
}

// ---------------------------------------------------------------------------
// Color and label helpers
// ---------------------------------------------------------------------------

// dashWorkerStateColor returns the display color for a worker state string.
func dashWorkerStateColor(state string) lipgloss.Color {
	switch strings.ToLower(state) {
	case "running":
		return styles.StatusOK
	case "idle":
		return styles.StatusWarn
	case "stopped":
		return styles.TextMuted
	case "error":
		return styles.StatusError
	case "starting":
		return styles.AccentSecondary
	case "stopping":
		return styles.StatusWarn
	default:
		return styles.TextMuted
	}
}

// dashWorkerStateLabel returns a short display label for a worker state.
func dashWorkerStateLabel(state string) string {
	switch strings.ToLower(state) {
	case "running":
		return "RUN"
	case "idle":
		return "IDLE"
	case "stopped":
		return "STOP"
	case "error":
		return "ERR"
	case "starting":
		return "START"
	case "stopping":
		return "HALT"
	default:
		return strings.ToUpper(state)
	}
}

// dashActivityColor maps an activity level to a display color.
func dashActivityColor(level string) lipgloss.Color {
	switch strings.ToLower(level) {
	case "info":
		return styles.TextPrimary
	case "warn":
		return styles.StatusWarn
	case "error":
		return styles.StatusError
	case "success":
		return styles.StatusOK
	default:
		return styles.TextSecondary
	}
}

// dashCostColor returns the color for a cost/budget ratio.
func dashCostColor(current, cap float64) lipgloss.Color {
	if cap <= 0 {
		return styles.StatusOK
	}
	ratio := current / cap
	if ratio >= 0.80 {
		return styles.StatusError
	}
	if ratio >= 0.50 {
		return styles.StatusWarn
	}
	return styles.StatusOK
}

// dashFormatDuration formats a time.Duration as "Xh Ym" or "Xm Ys" or "Xs".
func dashFormatDuration(d time.Duration) string {
	if d < 0 {
		d = 0
	}
	h := int(d.Hours())
	m := int(d.Minutes()) % 60
	s := int(d.Seconds()) % 60
	if h > 0 {
		return fmt.Sprintf("%dh %dm", h, m)
	}
	if m > 0 {
		return fmt.Sprintf("%dm %ds", m, s)
	}
	return fmt.Sprintf("%ds", s)
}

// maxInt returns the largest of the given integers.
func maxInt(vals ...int) int {
	m := 0
	for _, v := range vals {
		if v > m {
			m = v
		}
	}
	return m
}
