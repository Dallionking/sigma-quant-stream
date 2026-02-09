package components

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// LogLine represents a single log entry.
type LogLine struct {
	Time    time.Time
	Level   string // "info", "warn", "error", "success"
	Source  string // "RESEARCHER", "CONVERTER", etc.
	Message string
}

// LogStream is a scrollable log viewer implementing the Bubble Tea Model interface.
type LogStream struct {
	lines      []LogLine
	viewport   viewport.Model
	autoScroll bool
	maxLines   int
	width      int
	height     int
}

// NewLogStream creates a new LogStream with the given dimensions.
func NewLogStream(width, height int) LogStream {
	vp := viewport.New(width, height)
	vp.Style = lipgloss.NewStyle().Background(styles.BgPanel)
	return LogStream{
		lines:      nil,
		viewport:   vp,
		autoScroll: true,
		maxLines:   500,
		width:      width,
		height:     height,
	}
}

// Init satisfies tea.Model. No initial command needed.
func (l LogStream) Init() tea.Cmd {
	return nil
}

// Update satisfies tea.Model. Handles keyboard input and viewport messages.
func (l LogStream) Update(msg tea.Msg) (LogStream, tea.Cmd) {
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "G":
			// Jump to bottom and re-enable auto-scroll.
			l.autoScroll = true
			l.viewport.GotoBottom()
			return l, nil
		case "up", "k":
			// Manual scroll pauses auto-scroll.
			l.autoScroll = false
		case "down", "j":
			// If at the bottom after scrolling down, re-enable auto-scroll.
			l.viewport, cmd = l.viewport.Update(msg)
			if l.viewport.AtBottom() {
				l.autoScroll = true
			}
			return l, cmd
		}
	}

	l.viewport, cmd = l.viewport.Update(msg)

	// If the user scrolled away from bottom, pause auto-scroll.
	if !l.viewport.AtBottom() {
		l.autoScroll = false
	}

	return l, cmd
}

// View satisfies tea.Model. Returns the rendered viewport.
func (l LogStream) View() string {
	titleStyle := lipgloss.NewStyle().
		Foreground(styles.TextSecondary).
		Bold(true)
	title := titleStyle.Render("Logs")

	scrollIndicator := ""
	if !l.autoScroll {
		scrollIndicator = lipgloss.NewStyle().
			Foreground(styles.StatusWarn).
			Render(" (paused -- press G to resume)")
	}

	header := title + scrollIndicator
	return header + "\n" + l.viewport.View()
}

// AddLine appends a log line and refreshes the viewport content.
func (l *LogStream) AddLine(line LogLine) {
	l.lines = append(l.lines, line)

	// Trim if over max.
	if len(l.lines) > l.maxLines {
		overflow := len(l.lines) - l.maxLines
		l.lines = l.lines[overflow:]
	}

	// Rebuild content.
	l.viewport.SetContent(l.renderLines())

	// Auto-scroll to bottom if enabled.
	if l.autoScroll {
		l.viewport.GotoBottom()
	}
}

// levelColor returns the foreground color for a log level.
func levelColor(level string) lipgloss.Color {
	switch strings.ToLower(level) {
	case "info":
		return styles.TextSecondary
	case "warn":
		return styles.StatusWarn
	case "error":
		return styles.StatusError
	case "success":
		return styles.StatusOK
	default:
		return styles.TextMuted
	}
}

// renderLines builds the full text content from all log lines.
func (l *LogStream) renderLines() string {
	var b strings.Builder
	for _, line := range l.lines {
		color := levelColor(line.Level)

		ts := lipgloss.NewStyle().Foreground(styles.TextMuted).
			Render(line.Time.Format("15:04:05"))
		lvl := lipgloss.NewStyle().Foreground(color).Bold(true).
			Render(fmt.Sprintf("%-7s", strings.ToUpper(line.Level)))
		src := lipgloss.NewStyle().Foreground(styles.AccentSecondary).
			Render(fmt.Sprintf("%-12s", line.Source))
		msg := lipgloss.NewStyle().Foreground(color).
			Render(line.Message)

		b.WriteString(ts + " " + lvl + " " + src + " " + msg + "\n")
	}
	return b.String()
}
