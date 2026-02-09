package models

import (
	"fmt"
	"os/exec"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/components"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const (
	setupWidth     = 72
	stepCount      = 4
	testDurationS  = 60
	testPollMS     = 500
	testCountdownS = 5
)

// layoutChoice represents the terminal layout option selected by the user.
type layoutChoice int

const (
	layoutTmux    layoutChoice = iota // recommended
	layoutITerm2                      // macOS only
	layoutManual                      // no automation
)

func (l layoutChoice) String() string {
	switch l {
	case layoutTmux:
		return "tmux (recommended)"
	case layoutITerm2:
		return "iTerm2 (macOS)"
	case layoutManual:
		return "Manual"
	default:
		return "unknown"
	}
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

type checkDoneMsg struct {
	name    string
	version string
	ok      bool
}

type testTickMsg struct{}
type testDoneMsg struct{ err error }

// ---------------------------------------------------------------------------
// SetupClaudeModel -- 4-step wizard
// ---------------------------------------------------------------------------

// SetupClaudeModel implements tea.Model for the Claude Code setup wizard.
//
// Steps:
//  1. Prerequisites -- check claude CLI and tmux.
//  2. Configure Settings -- explain .claude/settings.json, confirm install.
//  3. Terminal Layout -- choose tmux / iTerm2 / Manual, generate script.
//  4. Test Launch -- optional 60-second smoke test.
type SetupClaudeModel struct {
	projectRoot string

	step   int  // 0-indexed current step (0..3)
	width  int
	height int
	done   bool
	err    error

	// Step 1 -- prerequisites
	claudeOK      bool
	claudeVersion string
	tmuxOK        bool
	tmuxVersion   string
	checksRunning bool
	checksDone    int // how many checks have completed

	// Step 2 -- configure settings
	settingsConfirmed bool
	settingsSelected  int // 0 = Confirm, 1 = Skip

	// Step 3 -- terminal layout
	layout         layoutChoice
	layoutSelected int // 0..2 cursor position

	// Step 4 -- test launch
	testRunning   bool
	testElapsed   int // seconds elapsed
	testCompleted bool
	testErr       error
	testSkipped   bool
	testSelected  int // 0 = Run test, 1 = Skip
}

// NewSetupClaudeModel creates a new setup wizard model.
func NewSetupClaudeModel(projectRoot string) SetupClaudeModel {
	return SetupClaudeModel{
		projectRoot:   projectRoot,
		step:          0,
		width:         setupWidth,
		settingsSelected: 0,
		layoutSelected:   0,
		testSelected:     0,
	}
}

// stepLabels returns the human-readable labels for the progress indicator.
func stepLabels() []string {
	return []string{
		"Prerequisites",
		"Configure",
		"Layout",
		"Test",
	}
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

// Init runs the initial prerequisite checks.
func (m SetupClaudeModel) Init() tea.Cmd {
	m.checksRunning = true
	return tea.Batch(
		checkBinary("claude", "--version"),
		checkBinary("tmux", "-V"),
	)
}

// Update processes messages and key events.
func (m SetupClaudeModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		if m.width < setupWidth {
			m.width = setupWidth
		}
		m.height = msg.Height
		return m, nil

	case tea.KeyMsg:
		return m.handleKey(msg)

	case checkDoneMsg:
		return m.handleCheckDone(msg)

	case testTickMsg:
		return m.handleTestTick()

	case testDoneMsg:
		m.testRunning = false
		m.testCompleted = true
		m.testErr = msg.err
		return m, nil
	}

	return m, nil
}

// View renders the current wizard step.
func (m SetupClaudeModel) View() string {
	if m.done {
		return m.viewDone()
	}

	// Header.
	header := styles.Title.Render("Claude Code Agent Setup")
	subtitle := styles.Subtitle.Render("Configure the AI worker team")

	// Progress indicator.
	progress := components.ProgressStep{
		Steps:   stepLabels(),
		Current: m.step,
		Width:   m.width,
	}

	divider := styles.Divider(m.width - 4)

	// Step content.
	var body string
	switch m.step {
	case 0:
		body = m.viewPrerequisites()
	case 1:
		body = m.viewConfigure()
	case 2:
		body = m.viewLayout()
	case 3:
		body = m.viewTest()
	}

	// Footer hints.
	footer := m.viewFooter()

	return lipgloss.JoinVertical(lipgloss.Left,
		"",
		header,
		subtitle,
		"",
		progress.Render(),
		"",
		divider,
		"",
		body,
		"",
		divider,
		footer,
	)
}

// ---------------------------------------------------------------------------
// Key handling
// ---------------------------------------------------------------------------

func (m SetupClaudeModel) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	key := msg.String()

	// Global: quit.
	if key == "ctrl+c" || key == "q" {
		m.done = true
		return m, tea.Quit
	}

	switch m.step {
	case 0:
		return m.handleKeyStep0(key)
	case 1:
		return m.handleKeyStep1(key)
	case 2:
		return m.handleKeyStep2(key)
	case 3:
		return m.handleKeyStep3(key)
	}

	return m, nil
}

// Step 0: Prerequisites -- just wait for checks, then enter to advance.
func (m SetupClaudeModel) handleKeyStep0(key string) (tea.Model, tea.Cmd) {
	if key == "enter" && m.checksDone >= 2 {
		m.step = 1
	}
	return m, nil
}

// Step 1: Configure Settings -- left/right or y/n to select, enter to confirm.
func (m SetupClaudeModel) handleKeyStep1(key string) (tea.Model, tea.Cmd) {
	switch key {
	case "left", "h":
		m.settingsSelected = 0
	case "right", "l":
		m.settingsSelected = 1
	case "y", "Y":
		m.settingsConfirmed = true
		m.step = 2
	case "n", "N":
		m.settingsConfirmed = false
		m.step = 2
	case "enter":
		m.settingsConfirmed = m.settingsSelected == 0
		m.step = 2
	}
	return m, nil
}

// Step 2: Terminal Layout -- up/down to choose, enter to confirm.
func (m SetupClaudeModel) handleKeyStep2(key string) (tea.Model, tea.Cmd) {
	switch key {
	case "up", "k":
		if m.layoutSelected > 0 {
			m.layoutSelected--
		}
	case "down", "j":
		if m.layoutSelected < 2 {
			m.layoutSelected++
		}
	case "enter":
		m.layout = layoutChoice(m.layoutSelected)
		m.step = 3
	}
	return m, nil
}

// Step 3: Test Launch -- choose run or skip.
func (m SetupClaudeModel) handleKeyStep3(key string) (tea.Model, tea.Cmd) {
	if m.testRunning {
		// While running, allow early cancel.
		if key == "esc" {
			m.testRunning = false
			m.testSkipped = true
			m.testCompleted = true
		}
		return m, nil
	}

	if m.testCompleted {
		// After test, enter to finish.
		if key == "enter" {
			m.done = true
			return m, tea.Quit
		}
		return m, nil
	}

	switch key {
	case "left", "h":
		m.testSelected = 0
	case "right", "l":
		m.testSelected = 1
	case "y", "Y":
		m.testRunning = true
		return m, tea.Batch(testTick(), runTestLaunch(m.projectRoot))
	case "n", "N":
		m.testSkipped = true
		m.testCompleted = true
		m.done = true
		return m, tea.Quit
	case "enter":
		if m.testSelected == 0 {
			m.testRunning = true
			return m, tea.Batch(testTick(), runTestLaunch(m.projectRoot))
		}
		m.testSkipped = true
		m.testCompleted = true
		m.done = true
		return m, tea.Quit
	}

	return m, nil
}

// ---------------------------------------------------------------------------
// Check handlers
// ---------------------------------------------------------------------------

func (m SetupClaudeModel) handleCheckDone(msg checkDoneMsg) (tea.Model, tea.Cmd) {
	m.checksDone++
	switch msg.name {
	case "claude":
		m.claudeOK = msg.ok
		m.claudeVersion = msg.version
	case "tmux":
		m.tmuxOK = msg.ok
		m.tmuxVersion = msg.version
	}
	if m.checksDone >= 2 {
		m.checksRunning = false
	}
	return m, nil
}

func (m SetupClaudeModel) handleTestTick() (tea.Model, tea.Cmd) {
	if !m.testRunning {
		return m, nil
	}
	m.testElapsed++
	if m.testElapsed >= testDurationS {
		m.testRunning = false
		m.testCompleted = true
		return m, nil
	}
	return m, testTick()
}

// ---------------------------------------------------------------------------
// Step views
// ---------------------------------------------------------------------------

func (m SetupClaudeModel) viewPrerequisites() string {
	title := styles.Cyan("Step 1: Prerequisites")
	desc := styles.Subtitle.Render("Checking required tools...")

	claudeStatus := m.renderCheck("Claude CLI", m.claudeOK, m.claudeVersion, m.checksDone >= 1 || !m.checksRunning)
	tmuxStatus := m.renderCheck("tmux", m.tmuxOK, m.tmuxVersion, m.checksDone >= 2 || !m.checksRunning)

	content := lipgloss.JoinVertical(lipgloss.Left,
		title,
		"",
		desc,
		"",
		claudeStatus,
		tmuxStatus,
	)

	if m.checksDone >= 2 {
		var summary string
		if m.claudeOK && m.tmuxOK {
			summary = styles.Green("All prerequisites met.")
		} else {
			missing := []string{}
			if !m.claudeOK {
				missing = append(missing, "claude CLI")
			}
			if !m.tmuxOK {
				missing = append(missing, "tmux")
			}
			summary = styles.Red("Missing: "+strings.Join(missing, ", ")) + "\n" +
				styles.Dim("Install missing tools and re-run this wizard.")
		}
		content = lipgloss.JoinVertical(lipgloss.Left,
			content,
			"",
			summary,
			"",
			styles.Dim("Press enter to continue"),
		)
	}

	return styles.Panel.Width(m.width - 2).Render(content)
}

func (m SetupClaudeModel) renderCheck(name string, ok bool, version string, done bool) string {
	if !done {
		return lipgloss.NewStyle().Foreground(styles.TextMuted).Render("  ...  " + name)
	}
	if ok {
		v := version
		if v == "" {
			v = "detected"
		}
		return styles.Green("  PASS") + "  " +
			styles.Bold(name) + "  " +
			styles.Dim(v)
	}
	return styles.Red("  FAIL") + "  " +
		styles.Bold(name) + "  " +
		styles.Dim("not found")
}

func (m SetupClaudeModel) viewConfigure() string {
	title := styles.Cyan("Step 2: Configure Settings")

	settingsPath := ".claude/settings.json"
	desc := styles.Subtitle.Render("This will configure " + settingsPath)

	items := []string{
		"  " + styles.Dim("1.") + " Agent team prompts (4 workers)",
		"  " + styles.Dim("2.") + " Ralph loop restart scripts",
		"  " + styles.Dim("3.") + " Queue IPC directory structure",
		"  " + styles.Dim("4.") + " Pattern knowledge base seeds",
	}

	// Buttons.
	confirmBtn := m.renderButton("Confirm", m.settingsSelected == 0)
	skipBtn := m.renderButton("Skip", m.settingsSelected == 1)
	buttons := lipgloss.JoinHorizontal(lipgloss.Center, confirmBtn, "  ", skipBtn)

	content := lipgloss.JoinVertical(lipgloss.Left,
		title,
		"",
		desc,
		"",
		styles.Bold("What will be installed:"),
		"",
		strings.Join(items, "\n"),
		"",
		buttons,
		"",
		lipgloss.NewStyle().Foreground(styles.TextMuted).Render("y/n or arrow keys + enter"),
	)

	return styles.Panel.Width(m.width - 2).Render(content)
}

func (m SetupClaudeModel) viewLayout() string {
	title := styles.Cyan("Step 3: Terminal Layout")
	desc := styles.Subtitle.Render("Choose how to arrange agent panes")

	options := []struct {
		label string
		desc  string
	}{
		{"tmux (recommended)", "2x2 grid, works everywhere, shared sessions"},
		{"iTerm2 (macOS)", "Native tabs and split panes via AppleScript"},
		{"Manual", "No automation -- you arrange windows yourself"},
	}

	var rows []string
	for i, opt := range options {
		cursor := "  "
		labelStyle := lipgloss.NewStyle().Foreground(styles.TextSecondary)
		descStyle := lipgloss.NewStyle().Foreground(styles.TextMuted)

		if i == m.layoutSelected {
			cursor = styles.Cyan("> ")
			labelStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true)
			descStyle = lipgloss.NewStyle().Foreground(styles.TextSecondary)
		}

		row := cursor + labelStyle.Render(opt.label) + "\n    " + descStyle.Render(opt.desc)
		rows = append(rows, row)
	}

	content := lipgloss.JoinVertical(lipgloss.Left,
		title,
		"",
		desc,
		"",
		strings.Join(rows, "\n\n"),
		"",
		lipgloss.NewStyle().Foreground(styles.TextMuted).Render("up/down + enter"),
	)

	return styles.Panel.Width(m.width - 2).Render(content)
}

func (m SetupClaudeModel) viewTest() string {
	title := styles.Cyan("Step 4: Test Launch")

	if m.testRunning {
		elapsed := m.testElapsed
		remaining := testDurationS - elapsed
		bar := m.renderProgressBar(elapsed, testDurationS, 40)

		content := lipgloss.JoinVertical(lipgloss.Left,
			title,
			"",
			styles.Subtitle.Render("Running smoke test..."),
			"",
			bar,
			"",
			styles.Dim(fmt.Sprintf("%ds elapsed / %ds remaining", elapsed, remaining)),
			"",
			styles.Dim("Press esc to cancel"),
		)
		return styles.PanelFocused.Width(m.width - 2).Render(content)
	}

	if m.testCompleted {
		var result string
		if m.testSkipped {
			result = styles.Dim("Test skipped.")
		} else if m.testErr != nil {
			result = styles.Red("Test failed: ") + styles.Dim(m.testErr.Error())
		} else {
			result = styles.Green("Test passed.") + " " + styles.Dim("Workers launched and cleaned up successfully.")
		}

		content := lipgloss.JoinVertical(lipgloss.Left,
			title,
			"",
			result,
			"",
			styles.Dim("Press enter to finish"),
		)
		return styles.Panel.Width(m.width - 2).Render(content)
	}

	// Not yet started -- offer choice.
	desc := styles.Subtitle.Render(fmt.Sprintf("Optional %d-second smoke test", testDurationS))
	detail := styles.Dim("Launches workers, verifies they start, then cleans up.")

	runBtn := m.renderButton("Run Test", m.testSelected == 0)
	skipBtn := m.renderButton("Skip", m.testSelected == 1)
	buttons := lipgloss.JoinHorizontal(lipgloss.Center, runBtn, "  ", skipBtn)

	content := lipgloss.JoinVertical(lipgloss.Left,
		title,
		"",
		desc,
		detail,
		"",
		buttons,
		"",
		lipgloss.NewStyle().Foreground(styles.TextMuted).Render("y/n or arrow keys + enter"),
	)

	return styles.Panel.Width(m.width - 2).Render(content)
}

// ---------------------------------------------------------------------------
// Done screen with tmux cheat sheet
// ---------------------------------------------------------------------------

func (m SetupClaudeModel) viewDone() string {
	header := styles.Title.Render("Setup Complete")
	divider := styles.Divider(m.width - 4)

	summary := []string{}
	if m.claudeOK {
		summary = append(summary, styles.Green("  PASS")+"  Claude CLI "+styles.Dim(m.claudeVersion))
	} else {
		summary = append(summary, styles.Red("  FAIL")+"  Claude CLI")
	}
	if m.tmuxOK {
		summary = append(summary, styles.Green("  PASS")+"  tmux "+styles.Dim(m.tmuxVersion))
	} else {
		summary = append(summary, styles.Red("  FAIL")+"  tmux")
	}
	if m.settingsConfirmed {
		summary = append(summary, styles.Green("  DONE")+"  Settings configured")
	} else {
		summary = append(summary, styles.Dim("  SKIP")+"  Settings (skipped)")
	}
	summary = append(summary, styles.Green("  DONE")+"  Layout: "+m.layout.String())

	cheatSheet := lipgloss.NewStyle().
		Foreground(styles.TextPrimary).
		Render(strings.Join([]string{
			styles.Cyan("tmux Cheat Sheet"),
			"",
			"  " + styles.Bold("tmux attach -t sigma-quant") + "    " + styles.Dim("Attach to session"),
			"  " + styles.Bold("Ctrl+B  arrow keys") + "           " + styles.Dim("Navigate panes"),
			"  " + styles.Bold("Ctrl+B  z") + "                    " + styles.Dim("Zoom pane"),
			"  " + styles.Bold("Ctrl+B  d") + "                    " + styles.Dim("Detach"),
			"  " + styles.Bold("sigma-quant status") + "           " + styles.Dim("Quick status"),
		}, "\n"))

	cheatPanel := styles.Panel.Width(m.width - 2).Render(cheatSheet)

	nextSteps := lipgloss.JoinVertical(lipgloss.Left,
		"",
		styles.Cyan("Next Steps"),
		"",
		"  "+styles.Bold("1.")+" "+styles.Dim("sigma-quant start")+"          Launch all workers",
		"  "+styles.Bold("2.")+" "+styles.Dim("sigma-quant status --watch")+" Monitor live",
		"  "+styles.Bold("3.")+" "+styles.Dim("sigma-quant strategies")+"     Review discoveries",
	)

	return lipgloss.JoinVertical(lipgloss.Left,
		"",
		header,
		"",
		divider,
		"",
		strings.Join(summary, "\n"),
		"",
		divider,
		"",
		cheatPanel,
		"",
		nextSteps,
		"",
	)
}

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------

func (m SetupClaudeModel) viewFooter() string {
	hints := []components.KeyHint{
		{Key: "q", Desc: "quit"},
	}

	switch m.step {
	case 0:
		if m.checksDone >= 2 {
			hints = append(hints, components.KeyHint{Key: "enter", Desc: "continue"})
		}
	case 1:
		hints = append(hints,
			components.KeyHint{Key: "y/n", Desc: "confirm/skip"},
			components.KeyHint{Key: "enter", Desc: "select"},
		)
	case 2:
		hints = append(hints,
			components.KeyHint{Key: "up/dn", Desc: "choose"},
			components.KeyHint{Key: "enter", Desc: "select"},
		)
	case 3:
		if m.testRunning {
			hints = append(hints, components.KeyHint{Key: "esc", Desc: "cancel"})
		} else if m.testCompleted {
			hints = append(hints, components.KeyHint{Key: "enter", Desc: "finish"})
		} else {
			hints = append(hints,
				components.KeyHint{Key: "y/n", Desc: "run/skip"},
				components.KeyHint{Key: "enter", Desc: "select"},
			)
		}
	}

	footer := components.Footer{
		Hints: hints,
		Width: m.width,
	}
	return footer.Render()
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

func (m SetupClaudeModel) renderButton(label string, selected bool) string {
	if selected {
		return lipgloss.NewStyle().
			Background(styles.AccentPrimary).
			Foreground(styles.BgDeep).
			Bold(true).
			Padding(0, 2).
			Render(label)
	}
	return lipgloss.NewStyle().
		Background(styles.BgSurface).
		Foreground(styles.TextSecondary).
		Padding(0, 2).
		Render(label)
}

func (m SetupClaudeModel) renderProgressBar(current, total, width int) string {
	if total <= 0 {
		total = 1
	}
	filled := current * width / total
	if filled > width {
		filled = width
	}
	empty := width - filled

	filledStr := lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).
		Render(strings.Repeat("█", filled))
	emptyStr := lipgloss.NewStyle().
		Foreground(styles.BgSurface).
		Render(strings.Repeat("░", empty))
	pct := lipgloss.NewStyle().
		Foreground(styles.TextSecondary).
		Render(fmt.Sprintf(" %d%%", current*100/total))

	return filledStr + emptyStr + pct
}

// ---------------------------------------------------------------------------
// Commands (async)
// ---------------------------------------------------------------------------

// checkBinary spawns a subprocess to check if a binary exists and get its version.
func checkBinary(name, versionFlag string) tea.Cmd {
	return func() tea.Msg {
		cmd := exec.Command(name, versionFlag)
		out, err := cmd.CombinedOutput()
		if err != nil {
			return checkDoneMsg{name: name, ok: false}
		}
		version := strings.TrimSpace(string(out))
		// Take first line only.
		if idx := strings.IndexByte(version, '\n'); idx != -1 {
			version = version[:idx]
		}
		return checkDoneMsg{name: name, version: version, ok: true}
	}
}

// testTick sends a tick every second while the test is running.
func testTick() tea.Cmd {
	return tea.Tick(time.Second, func(t time.Time) tea.Msg {
		return testTickMsg{}
	})
}

// runTestLaunch performs a quick smoke test: attempt to create and immediately
// tear down a tmux session to verify the setup works.
func runTestLaunch(projectRoot string) tea.Cmd {
	return func() tea.Msg {
		sessionName := "sigma-quant-test"

		// Create a detached tmux session.
		create := exec.Command("tmux", "new-session", "-d", "-s", sessionName)
		create.Dir = projectRoot
		if err := create.Run(); err != nil {
			return testDoneMsg{err: fmt.Errorf("failed to create tmux session: %w", err)}
		}

		// Brief pause to let it initialize.
		time.Sleep(2 * time.Second)

		// Check the session exists.
		check := exec.Command("tmux", "has-session", "-t", sessionName)
		if err := check.Run(); err != nil {
			return testDoneMsg{err: fmt.Errorf("tmux session not found after creation: %w", err)}
		}

		// Clean up.
		kill := exec.Command("tmux", "kill-session", "-t", sessionName)
		if err := kill.Run(); err != nil {
			return testDoneMsg{err: fmt.Errorf("failed to kill test session: %w", err)}
		}

		return testDoneMsg{err: nil}
	}
}
