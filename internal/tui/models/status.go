package models

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
	"github.com/Dallionking/sigma-quant-stream/internal/tui/components"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

// SessionInfo tracks runtime, cost, and progress for the current session.
type SessionInfo struct {
	StartedAt       time.Time
	TasksCompleted  int
	CurrentCost     float64
	BudgetCap       float64
	PatternsLearned int
}

// ActivityEntry represents a single line in the activity feed.
type ActivityEntry struct {
	Time    time.Time
	Source  string
	Message string
	Level   string // "info", "warn", "error", "success"
}

// StrategyStats aggregates strategy counts by output classification.
type StrategyStats struct {
	Total    int
	Good     int
	Review   int
	Rejected int
	PropFirm int
	Recent   []components.StrategyCard
}

// TickMsg triggers a periodic data refresh.
type TickMsg time.Time

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// workerMeta provides display name and icon for each worker position.
var workerMeta = [4]struct {
	Name string
	Icon string
}{
	{Name: "Researcher", Icon: "\U0001F52C"},
	{Name: "Converter", Icon: "\U0001F504"},
	{Name: "Backtester", Icon: "\U0001F4CA"},
	{Name: "Optimizer", Icon: "\u26A1"},
}

const logBufferMax = 200

var dashboardTabs = []string{"Dashboard", "Workers", "Strategies", "Logs"}

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// StatusModel is the full-screen Bubble Tea dashboard implementing
// Init/Update/View. It composes sub-components into a 4-quadrant layout
// with header, tabs, and footer. Polls the agent manager and queue watcher
// for live data every 2 seconds.
type StatusModel struct {
	// Sub-components
	header       components.Header
	workerPanels [4]components.WorkerPanel
	queueBar     components.QueueBar
	costTracker  components.CostTracker
	logStream    components.LogStream
	tabBar       components.TabBar
	footer       components.Footer

	// Data
	strategies StrategyStats
	session    SessionInfo
	activity   []ActivityEntry

	// State
	activeTab int
	width     int
	height    int
	ready     bool
	quitting  bool

	// Log buffer preserved across LogStream resizes.
	logBuffer []components.LogLine

	// Previous state for change-detection logging.
	prevWorkerStates map[agent.WorkerType]string
	prevQueueDepths  map[queue.QueueName]int

	// Services
	agentMgr    *agent.Manager
	queueWatch  *queue.Watcher
	projectRoot string
	profile     string
}

// NewStatusModel creates a StatusModel wired to the given services.
// mgr and qw may be nil for gracefully degraded display.
func NewStatusModel(
	mgr *agent.Manager,
	qw *queue.Watcher,
	projectRoot string,
	profile string,
) StatusModel {
	var panels [4]components.WorkerPanel
	for i := range panels {
		panels[i] = components.WorkerPanel{
			Name:  workerMeta[i].Name,
			Icon:  workerMeta[i].Icon,
			State: "stopped",
			Width: 36,
		}
	}

	budgetCap := getBudgetCap(projectRoot)

	return StatusModel{
		workerPanels: panels,
		logStream:    components.NewLogStream(60, 10),
		tabBar: components.TabBar{
			Tabs:      dashboardTabs,
			ActiveTab: 0,
		},
		session: SessionInfo{
			StartedAt: time.Now(),
			BudgetCap: budgetCap,
		},
		costTracker: components.CostTracker{
			BudgetCap: budgetCap,
		},
		prevWorkerStates: make(map[agent.WorkerType]string),
		prevQueueDepths:  make(map[queue.QueueName]int),
		agentMgr:         mgr,
		queueWatch:       qw,
		projectRoot:      projectRoot,
		profile:          profile,
	}
}

// tickCmd returns a tea.Cmd that fires TickMsg after 2 seconds.
func tickCmd() tea.Cmd {
	return tea.Tick(2*time.Second, func(t time.Time) tea.Msg {
		return TickMsg(t)
	})
}

// ---------------------------------------------------------------------------
// Bubble Tea interface
// ---------------------------------------------------------------------------

// Init starts with a fast initial tick for immediate data display,
// then transitions to 2-second intervals.
func (m StatusModel) Init() tea.Cmd {
	return tea.Tick(200*time.Millisecond, func(t time.Time) tea.Msg {
		return TickMsg(t)
	})
}

// Update handles all incoming messages: window resize, keyboard, tick.
func (m StatusModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.ready = true
		m.reflow()

	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			m.quitting = true
			return m, tea.Quit
		case "r":
			m.refresh()
			m.addLog("info", "DASHBOARD", "Manual refresh triggered")
		case "w":
			m.activeTab = 1
			m.tabBar.ActiveTab = 1
		case "s":
			m.activeTab = 2
			m.tabBar.ActiveTab = 2
		case "l":
			m.activeTab = 3
			m.tabBar.ActiveTab = 3
		case "d":
			m.activeTab = 0
			m.tabBar.ActiveTab = 0
		case "tab":
			m.activeTab = (m.activeTab + 1) % len(dashboardTabs)
			m.tabBar.ActiveTab = m.activeTab
		case "shift+tab":
			m.activeTab--
			if m.activeTab < 0 {
				m.activeTab = len(dashboardTabs) - 1
			}
			m.tabBar.ActiveTab = m.activeTab
		}

	case TickMsg:
		m.refresh()
		cmds = append(cmds, tickCmd())
	}

	// Forward to LogStream for viewport scroll handling when on logs tab.
	if m.activeTab == 3 {
		var logCmd tea.Cmd
		m.logStream, logCmd = m.logStream.Update(msg)
		if logCmd != nil {
			cmds = append(cmds, logCmd)
		}
	}

	return m, tea.Batch(cmds...)
}

// View renders the full dashboard layout. The active tab determines
// which view is shown between the header/tabs and footer.
func (m StatusModel) View() string {
	if m.quitting {
		return ""
	}
	if !m.ready {
		return "\n  Loading dashboard..."
	}

	sections := []string{
		m.header.Render(),
		m.tabBar.Render(),
	}

	switch m.activeTab {
	case 0:
		sections = append(sections, m.renderDashboard())
	case 1:
		sections = append(sections, m.renderWorkersExpanded())
	case 2:
		sections = append(sections, m.renderStrategiesExpanded())
	case 3:
		sections = append(sections, m.renderLogsExpanded())
	}

	sections = append(sections, m.footer.Render())

	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}

// ---------------------------------------------------------------------------
// Dashboard view (4-quadrant layout)
// ---------------------------------------------------------------------------

// renderDashboard renders the main 4-quadrant view:
//
//	[Workers      | Queue Pipeline ]
//	[Strategies   | Session        ]
//	[Recent Activity -- full width ]
func (m StatusModel) renderDashboard() string {
	if m.width < 80 {
		return m.renderDashboardNarrow()
	}

	halfWidth := m.width / 2
	leftW := halfWidth
	rightW := m.width - halfWidth

	// Top row: Workers (left) + Queue Pipeline (right).
	workersPanel := m.renderWorkersQuadrant(leftW)
	queuePanel := m.renderQueueQuadrant(rightW)
	topRow := lipgloss.JoinHorizontal(lipgloss.Top, workersPanel, queuePanel)

	// Bottom row: Strategies (left) + Session (right).
	stratPanel := m.renderStrategiesQuadrant(leftW)
	sessionPanel := m.renderSessionQuadrant(rightW)
	bottomRow := lipgloss.JoinHorizontal(lipgloss.Top, stratPanel, sessionPanel)

	// Activity log spans full width.
	activityPanel := m.renderActivityPanel(m.width)

	return lipgloss.JoinVertical(lipgloss.Left, topRow, bottomRow, activityPanel)
}

// renderDashboardNarrow stacks all panels vertically for narrow terminals.
func (m StatusModel) renderDashboardNarrow() string {
	w := m.width
	sections := []string{
		m.renderWorkersQuadrant(w),
		m.renderQueueQuadrant(w),
		m.renderStrategiesQuadrant(w),
		m.renderSessionQuadrant(w),
		m.renderActivityPanel(w),
	}
	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}

// ---------------------------------------------------------------------------
// Quadrant renderers
// ---------------------------------------------------------------------------

// renderWorkersQuadrant shows compact worker state lines in a bordered panel.
func (m StatusModel) renderWorkersQuadrant(width int) string {
	var lines []string
	for _, wp := range m.workerPanels {
		nameStr := lipgloss.NewStyle().
			Foreground(styles.TextPrimary).
			Bold(true).
			Render(wp.Icon + " " + wp.Name)

		dotColor := workerStateColor(wp.State)
		dot := lipgloss.NewStyle().Foreground(dotColor).Render("●")
		label := lipgloss.NewStyle().Foreground(dotColor).Bold(true).
			Render(workerStateLabel(wp.State))

		// Right-align state within the available inner width.
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

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return renderQuadrantPanel("Workers", content, width)
}

// renderQueueQuadrant shows pipeline stage bars with fill proportions.
func (m StatusModel) renderQueueQuadrant(width int) string {
	barWidth := 14
	if width > 50 {
		barWidth = width - 30
	}
	if barWidth < 6 {
		barWidth = 6
	}

	maxCount := max(
		m.queueBar.Hypotheses,
		m.queueBar.ToConvert,
		m.queueBar.ToBacktest,
		m.queueBar.ToOptimize,
	)
	if maxCount < 1 {
		maxCount = 20 // default scale when empty
	}

	lines := []string{
		renderQueueLine("hypotheses", m.queueBar.Hypotheses, maxCount, barWidth),
		renderQueueLine("to-convert", m.queueBar.ToConvert, maxCount, barWidth),
		renderQueueLine("to-backtest", m.queueBar.ToBacktest, maxCount, barWidth),
		renderQueueLine("to-optimize", m.queueBar.ToOptimize, maxCount, barWidth),
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return renderQuadrantPanel("Queue Pipeline", content, width)
}

// renderStrategiesQuadrant shows strategy counts with proportional mini-bars.
func (m StatusModel) renderStrategiesQuadrant(width int) string {
	s := m.strategies
	total := s.Total
	if total < 1 {
		total = 1 // avoid division by zero
	}

	lines := []string{
		renderStratLine("Total", s.Total, total, styles.TextPrimary),
		renderStratLine("Good", s.Good, total, styles.StatusOK),
		renderStratLine("Review", s.Review, total, styles.StatusWarn),
		renderStratLine("Rejected", s.Rejected, total, styles.StatusError),
		renderStratLine("PropFirm", s.PropFirm, total, styles.AccentGold),
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return renderQuadrantPanel("Strategies", content, width)
}

// renderSessionQuadrant shows runtime, tasks, cost progress, and patterns.
func (m StatusModel) renderSessionQuadrant(width int) string {
	runtime := formatDuration(time.Since(m.session.StartedAt))

	costLine := m.renderCostText()
	innerBarW := width - 10
	if innerBarW < 10 {
		innerBarW = 10
	}
	costBar := m.renderCostBar(innerBarW)

	patternsStr := lipgloss.NewStyle().
		Foreground(styles.AccentSecondary).
		Bold(true).
		Render(fmt.Sprintf("+%d learned", m.session.PatternsLearned))

	lines := []string{
		styles.Label.Render("Runtime:  ") + styles.Value.Render(runtime),
		styles.Label.Render("Tasks:    ") + styles.Value.Render(fmt.Sprintf("%d completed", m.session.TasksCompleted)),
		styles.Label.Render("Cost:     ") + costLine,
		costBar,
		styles.Label.Render("Patterns: ") + patternsStr,
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return renderQuadrantPanel("Session", content, width)
}

// renderActivityPanel shows the most recent activity entries in a full-width panel.
func (m StatusModel) renderActivityPanel(width int) string {
	// Compute how many entries fit. Reserve lines for panel border and title.
	maxEntries := 5
	availH := m.height - 24
	if availH > 3 && availH < maxEntries {
		maxEntries = availH
	}
	if maxEntries < 1 {
		maxEntries = 1
	}

	start := 0
	if len(m.activity) > maxEntries {
		start = len(m.activity) - maxEntries
	}

	var lines []string
	for _, entry := range m.activity[start:] {
		ts := lipgloss.NewStyle().Foreground(styles.TextMuted).
			Render(entry.Time.Format("15:04"))
		src := lipgloss.NewStyle().Foreground(styles.AccentSecondary).
			Render(fmt.Sprintf("[%-10s]", entry.Source))
		msg := lipgloss.NewStyle().Foreground(activityLevelColor(entry.Level)).
			Render(entry.Message)
		lines = append(lines, ts+"  "+src+" "+msg)
	}

	if len(lines) == 0 {
		lines = append(lines, styles.Dim("  No recent activity"))
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return renderQuadrantPanel("Recent Activity", content, width)
}

// ---------------------------------------------------------------------------
// Expanded tab views
// ---------------------------------------------------------------------------

// renderWorkersExpanded shows full WorkerPanel components in a 2x2 grid.
func (m StatusModel) renderWorkersExpanded() string {
	halfWidth := m.width / 2
	if m.width < 80 {
		halfWidth = m.width - 2
	}

	// Copy panels with updated width.
	panels := m.workerPanels
	for i := range panels {
		panels[i].Width = halfWidth
	}

	if m.width < 80 {
		var rows []string
		for _, p := range panels {
			rows = append(rows, p.Render())
		}
		return lipgloss.JoinVertical(lipgloss.Left, rows...)
	}

	topRow := lipgloss.JoinHorizontal(lipgloss.Top,
		panels[0].Render(), panels[1].Render(),
	)
	botRow := lipgloss.JoinHorizontal(lipgloss.Top,
		panels[2].Render(), panels[3].Render(),
	)

	// Pipeline bar below the worker grid.
	barCopy := m.queueBar
	barCopy.Width = m.width - 2
	pipelineRow := barCopy.Render()

	// Cost tracker.
	costPanel := lipgloss.NewStyle().
		Background(styles.BgPanel).
		Border(styles.RoundedBorder).
		BorderForeground(styles.BorderNormal).
		Padding(0, 1).
		Width(m.width - 4)

	costTitle := styles.Title.Render("Cost Tracker")
	costContent := costPanel.Render(costTitle + "\n" + m.costTracker.Render())

	return lipgloss.JoinVertical(lipgloss.Left, topRow, botRow, pipelineRow, costContent)
}

// renderStrategiesExpanded shows strategy stats with recent strategy cards.
func (m StatusModel) renderStrategiesExpanded() string {
	s := m.strategies

	// Stats summary.
	statsTitle := styles.Title.Render("Strategy Counts")
	total := s.Total
	if total < 1 {
		total = 1
	}

	statsLines := []string{
		statsTitle,
		"",
		renderStratLine("Total", s.Total, total, styles.TextPrimary),
		renderStratLine("Good", s.Good, total, styles.StatusOK),
		renderStratLine("Review", s.Review, total, styles.StatusWarn),
		renderStratLine("Rejected", s.Rejected, total, styles.StatusError),
		renderStratLine("PropFirm", s.PropFirm, total, styles.AccentGold),
	}

	statsContent := lipgloss.JoinVertical(lipgloss.Left, statsLines...)
	statsPanel := lipgloss.NewStyle().
		Background(styles.BgPanel).
		Border(styles.RoundedBorder).
		BorderForeground(styles.BorderNormal).
		Padding(0, 1).
		Width(m.width - 4)

	sections := []string{statsPanel.Render(statsContent)}

	// Recent strategy cards.
	if len(s.Recent) > 0 {
		sections = append(sections, "")
		sections = append(sections, styles.Title.Render("  Recent Strategies"))
		sections = append(sections, styles.Divider(m.width))
		for _, card := range s.Recent {
			sections = append(sections, "  "+card.RenderCompact())
		}
	}

	if s.Total == 0 {
		sections = append(sections, "")
		empty := lipgloss.NewStyle().
			Foreground(styles.TextMuted).
			PaddingLeft(2).
			Render("No strategies found. Run the pipeline to generate strategies.")
		sections = append(sections, empty)
	}

	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}

// renderLogsExpanded gives the LogStream full available height.
func (m StatusModel) renderLogsExpanded() string {
	return m.logStream.View()
}

// ---------------------------------------------------------------------------
// Cost rendering helpers
// ---------------------------------------------------------------------------

// renderCostText produces the "$X.XX / $Y.YY" cost display.
func (m StatusModel) renderCostText() string {
	color := costColor(m.session.CurrentCost, m.session.BudgetCap)

	return lipgloss.NewStyle().Foreground(color).Bold(true).
		Render(fmt.Sprintf("$%.2f", m.session.CurrentCost)) +
		lipgloss.NewStyle().Foreground(styles.TextMuted).
			Render(fmt.Sprintf(" / $%.2f", m.session.BudgetCap))
}

// renderCostBar draws a horizontal progress bar with percentage.
func (m StatusModel) renderCostBar(barWidth int) string {
	if barWidth < 4 {
		barWidth = 4
	}
	ratio := 0.0
	if m.session.BudgetCap > 0 {
		ratio = m.session.CurrentCost / m.session.BudgetCap
	}

	filled := int(math.Round(ratio * float64(barWidth)))
	if filled > barWidth {
		filled = barWidth
	}
	if filled < 0 {
		filled = 0
	}
	empty := barWidth - filled

	color := costColor(m.session.CurrentCost, m.session.BudgetCap)

	filledStr := lipgloss.NewStyle().Foreground(color).Render(strings.Repeat("\u2588", filled))
	emptyStr := lipgloss.NewStyle().Foreground(styles.TextMuted).Render(strings.Repeat("\u2591", empty))
	pct := lipgloss.NewStyle().Foreground(styles.TextSecondary).
		Render(fmt.Sprintf(" %.1f%%", ratio*100))

	return filledStr + emptyStr + pct
}

// ---------------------------------------------------------------------------
// Reflow
// ---------------------------------------------------------------------------

// reflow recalculates all component dimensions after a terminal resize.
func (m *StatusModel) reflow() {
	w := m.width

	// Full-width components.
	m.header.Width = w
	m.tabBar.Width = w
	m.footer = components.Footer{
		Hints: []components.KeyHint{
			{Key: "q", Desc: "quit"},
			{Key: "r", Desc: "refresh"},
			{Key: "w", Desc: "workers"},
			{Key: "s", Desc: "strategies"},
			{Key: "l", Desc: "logs"},
		},
		Width: w,
	}

	// Worker panels: half-width in expanded view.
	if w < 80 {
		for i := range m.workerPanels {
			m.workerPanels[i].Width = w - 2
		}
	} else {
		pw := (w - 4) / 2
		for i := range m.workerPanels {
			m.workerPanels[i].Width = pw
		}
	}

	// Queue bar.
	m.queueBar.Width = w - 2

	// LogStream: recreate with new dimensions and replay buffered lines.
	logContentW := w - 8
	logH := m.height - 6
	if logContentW < 20 {
		logContentW = 20
	}
	if logH < 5 {
		logH = 5
	}

	m.logStream = components.NewLogStream(logContentW, logH)
	for _, line := range m.logBuffer {
		m.logStream.AddLine(line)
	}
}

// ---------------------------------------------------------------------------
// Data refresh
// ---------------------------------------------------------------------------

// refresh polls all services and updates component data.
func (m *StatusModel) refresh() {
	if len(m.logBuffer) == 0 {
		m.addLog("info", "DASHBOARD", "Dashboard started -- refreshing every 2s")
	}
	m.refreshWorkers()
	m.refreshQueues()
	m.refreshStrategies()
	m.refreshSession()
	m.refreshActivity()
	m.refreshHeader()
}

// refreshWorkers updates worker panels from the agent manager.
func (m *StatusModel) refreshWorkers() {
	if m.agentMgr == nil {
		return
	}

	states := m.agentMgr.GetWorkerStates()
	workerTypes := agent.AllWorkerTypes()

	for i, wt := range workerTypes {
		if i >= 4 {
			break
		}
		if rw, ok := states[wt]; ok {
			newState := rw.State.String()

			// Log state transitions.
			if prev, exists := m.prevWorkerStates[wt]; exists && prev != newState {
				m.addLog("info", strings.ToUpper(string(wt)),
					fmt.Sprintf("State changed: %s -> %s", prev, newState))
			}
			m.prevWorkerStates[wt] = newState

			m.workerPanels[i].State = newState
			m.workerPanels[i].Sessions = rw.SessionsRun
			m.workerPanels[i].Tasks = rw.TasksCompleted
			m.workerPanels[i].CurrentTask = rw.CurrentTask
		} else {
			m.workerPanels[i].State = "stopped"
			m.workerPanels[i].Sessions = 0
			m.workerPanels[i].Tasks = 0
			m.workerPanels[i].CurrentTask = ""
		}
	}
}

// refreshQueues updates the pipeline bar from queue depths.
func (m *StatusModel) refreshQueues() {
	if m.queueWatch == nil {
		return
	}

	depths, err := m.queueWatch.GetAllDepths()
	if err != nil {
		return
	}

	for _, d := range depths {
		count := d.Pending

		if prev, exists := m.prevQueueDepths[d.Name]; exists && prev != count {
			m.addLog("info", "PIPELINE",
				fmt.Sprintf("%s: %d -> %d pending", d.Name, prev, count))
		}
		m.prevQueueDepths[d.Name] = count

		switch d.Name {
		case queue.QueueHypotheses:
			m.queueBar.Hypotheses = count
		case queue.QueueToConvert:
			m.queueBar.ToConvert = count
		case queue.QueueToBacktest:
			m.queueBar.ToBacktest = count
		case queue.QueueToOptimize:
			m.queueBar.ToOptimize = count
		}
	}
}

// refreshStrategies scans output directories for strategy file counts.
func (m *StatusModel) refreshStrategies() {
	m.strategies.Good = countJSONFiles(filepath.Join(m.projectRoot, "output", "strategies", "good"))
	m.strategies.Review = countJSONFiles(filepath.Join(m.projectRoot, "output", "strategies", "under_review"))
	m.strategies.Rejected = countJSONFiles(filepath.Join(m.projectRoot, "output", "strategies", "rejected"))
	m.strategies.PropFirm = countJSONFiles(filepath.Join(m.projectRoot, "output", "strategies", "prop_firm_ready"))
	m.strategies.Total = m.strategies.Good + m.strategies.Review + m.strategies.Rejected + m.strategies.PropFirm
	m.strategies.Recent = m.loadRecentStrategies(5)
}

// refreshSession updates session runtime, cost, task count, and patterns.
func (m *StatusModel) refreshSession() {
	// Tasks: aggregate from worker panels.
	totalTasks := 0
	for _, wp := range m.workerPanels {
		totalTasks += wp.Tasks
	}
	m.session.TasksCompleted = totalTasks

	// Cost: sync from the cost tracker component.
	m.session.CurrentCost = m.costTracker.CurrentCost

	// Patterns: count markdown files in the patterns directory.
	m.session.PatternsLearned = countPatterns(m.projectRoot)
}

// refreshActivity syncs the activity feed from the log buffer.
func (m *StatusModel) refreshActivity() {
	m.activity = make([]ActivityEntry, 0, len(m.logBuffer))
	for _, line := range m.logBuffer {
		m.activity = append(m.activity, ActivityEntry{
			Time:    line.Time,
			Source:  line.Source,
			Message: line.Message,
			Level:   line.Level,
		})
	}
}

// refreshHeader updates the header bar with live worker counts and cost.
func (m *StatusModel) refreshHeader() {
	runningCount := 0
	if m.agentMgr != nil {
		for _, rw := range m.agentMgr.GetWorkerStates() {
			if rw.State == agent.StateRunning || rw.State == agent.StateIdle {
				runningCount++
			}
		}
	}

	m.header = components.Header{
		Profile:      m.profile,
		Workers:      runningCount,
		TotalWorkers: 4,
		Cost:         m.costTracker.CurrentCost,
		Width:        m.width,
	}
}

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

// addLog appends a log line to both the persistent buffer and the LogStream.
func (m *StatusModel) addLog(level, source, message string) {
	line := components.LogLine{
		Time:    time.Now(),
		Level:   level,
		Source:  source,
		Message: message,
	}

	m.logBuffer = append(m.logBuffer, line)
	if len(m.logBuffer) > logBufferMax {
		m.logBuffer = m.logBuffer[len(m.logBuffer)-logBufferMax:]
	}

	m.logStream.AddLine(line)
}

// ---------------------------------------------------------------------------
// Panel rendering helpers
// ---------------------------------------------------------------------------

// renderQuadrantPanel wraps content in a bordered panel with a styled title.
func renderQuadrantPanel(title string, content string, width int) string {
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

// renderQueueLine draws a single queue stage with a progress bar.
func renderQueueLine(label string, count, maxCount, barWidth int) string {
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

// renderStratLine draws a strategy count line with a proportional mini-bar.
func renderStratLine(label string, count, total int, color lipgloss.Color) string {
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

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

// workerStateColor returns the display color for a worker state string.
func workerStateColor(state string) lipgloss.Color {
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

// workerStateLabel returns a short display label for a worker state.
func workerStateLabel(state string) string {
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

// activityLevelColor maps an activity level to a display color.
func activityLevelColor(level string) lipgloss.Color {
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

// costColor returns the color for a cost/budget ratio.
func costColor(current, cap float64) lipgloss.Color {
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

// formatDuration formats a time.Duration as "Xh Ym" or "Xm Ys" or "Xs".
func formatDuration(d time.Duration) string {
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

// ---------------------------------------------------------------------------
// Filesystem helpers
// ---------------------------------------------------------------------------

// countJSONFiles returns the number of .json files in dir (non-recursive).
func countJSONFiles(dir string) int {
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

// countPatterns counts .md files in the project's patterns directory.
func countPatterns(root string) int {
	patternsDir := filepath.Join(root, "patterns")
	entries, err := os.ReadDir(patternsDir)
	if err != nil {
		return 0
	}
	count := 0
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".md") {
			count++
		}
	}
	return count
}

// getBudgetCap reads the budget cap from config, defaulting to 50.0.
func getBudgetCap(projectRoot string) float64 {
	var cfg *config.Config
	func() {
		defer func() { recover() }()
		cfg = config.Get()
	}()
	if cfg != nil {
		if mode, ok := cfg.Modes[cfg.Defaults.Mode]; ok && mode.BudgetCap > 0 {
			return mode.BudgetCap
		}
	}
	return 50.0
}

// loadRecentStrategies collects up to n strategy cards from output directories,
// prioritising good and prop-firm-ready strategies.
func (m *StatusModel) loadRecentStrategies(n int) []components.StrategyCard {
	type scanDir struct {
		path   string
		status string
	}
	dirs := []scanDir{
		{filepath.Join(m.projectRoot, "output", "strategies", "prop_firm_ready"), "prop_firm_ready"},
		{filepath.Join(m.projectRoot, "output", "strategies", "good"), "good"},
		{filepath.Join(m.projectRoot, "output", "strategies", "under_review"), "under_review"},
	}

	var cards []components.StrategyCard
	for _, d := range dirs {
		entries, err := os.ReadDir(d.path)
		if err != nil {
			continue
		}
		for _, e := range entries {
			if e.IsDir() || !strings.HasSuffix(e.Name(), ".json") {
				continue
			}
			name := strings.TrimSuffix(e.Name(), ".json")
			cards = append(cards, components.StrategyCard{
				Name:   name,
				Status: d.status,
				Market: "futures",
			})
			if len(cards) >= n {
				return cards
			}
		}
	}
	return cards
}
