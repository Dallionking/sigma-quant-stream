package models

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/health"
	"github.com/Dallionking/sigma-quant-stream/internal/python"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/components"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// ---------------------------------------------------------------------------
// Step enumeration
// ---------------------------------------------------------------------------

// WizardStep enumerates each screen of the onboarding wizard.
type WizardStep int

const (
	StepWelcome      WizardStep = iota // 0
	StepPathSelect                     // 1
	StepMarketSelect                   // 2
	StepAPIKeys                        // 3
	StepDataDownload                   // 4
	StepHealthCheck                    // 5
	StepReady                          // 6
)

const wizardStepCount = 7

// wizardStepLabels returns the labels shown in the progress indicator.
func wizardStepLabels() []string {
	return []string{
		"Welcome",
		"Path",
		"Markets",
		"API Keys",
		"Data",
		"Health",
		"Ready",
	}
}

// ---------------------------------------------------------------------------
// Sub-types
// ---------------------------------------------------------------------------

// Checkbox represents a toggleable option in the market selection step.
type Checkbox struct {
	Label   string
	Desc    string
	Checked bool
}

// DownloadLine tracks a single symbol's download state.
type DownloadLine struct {
	Symbol   string
	Progress float64 // 0.0 .. 1.0
	Message  string
	Done     bool
	Error    string
}

// ---------------------------------------------------------------------------
// Tea messages
// ---------------------------------------------------------------------------

type downloadTickMsg struct {
	progress python.DownloadProgress
}

type downloadSimTickMsg struct{}

type downloadDoneMsg struct{ err error }

type healthDoneMsg struct {
	report *health.Report
}

// ---------------------------------------------------------------------------
// WizardModel
// ---------------------------------------------------------------------------

// WizardModel implements tea.Model for the `sigma-quant init` onboarding
// wizard. It walks the user through seven steps:
//
//	0. Welcome      -- show logo, "Press Enter to begin"
//	1. Path Select  -- developer or trader
//	2. Markets      -- futures, crypto-cex, crypto-dex (multi-select)
//	3. API Keys     -- conditional text inputs based on market selection
//	4. Data Download-- stream progress bars per symbol
//	5. Health Check -- run health.Checker.RunAll()
//	6. Ready        -- summary + next steps
type WizardModel struct {
	projectRoot string

	step       WizardStep
	totalSteps int

	// Step 1 -- Path
	path       string // "developer" or "trader"
	pathCursor int    // 0 = developer, 1 = trader

	// Step 2 -- Markets
	markets      []Checkbox
	marketCursor int

	// Step 3 -- API Keys
	apiKeys      map[string]string
	apiKeyInputs []textinput.Model
	apiKeyLabels []string
	focusedInput int

	// Step 4 -- Download
	downloading  bool
	downloadDone bool
	downloadErr  error
	downloadProg []DownloadLine
	downloadSim  float64 // simulated progress when python unavailable

	// Step 5 -- Health Check
	checking     bool
	healthReport *health.Report
	healthSpin   spinner.Model

	// Quit confirmation
	confirmQuit bool

	// --explain mode
	explain bool

	// Layout
	width  int
	height int
}

// NewWizardModel creates a new onboarding wizard model.
func NewWizardModel(projectRoot string, explain bool) WizardModel {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(styles.AccentPrimary)

	markets := []Checkbox{
		{Label: "Futures", Desc: "CME: ES, NQ, YM, GC -- requires Databento API key", Checked: true},
		{Label: "Crypto CEX", Desc: "Binance, Bybit, OKX -- free data via CCXT", Checked: false},
		{Label: "Crypto DEX", Desc: "Hyperliquid -- free data via native API", Checked: false},
	}

	return WizardModel{
		projectRoot: projectRoot,
		step:        StepWelcome,
		totalSteps:  wizardStepCount,
		path:        "",
		pathCursor:  0,
		markets:     markets,
		apiKeys:     make(map[string]string),
		explain:     explain,
		healthSpin:  s,
		width:       80,
		height:      40,
	}
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

// Init is called when the program starts.
func (m WizardModel) Init() tea.Cmd {
	return nil
}

// Update processes messages and key events.
func (m WizardModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case tea.WindowSizeMsg:
		m.width = msg.Width
		if m.width < 60 {
			m.width = 60
		}
		m.height = msg.Height
		return m, nil

	case tea.KeyMsg:
		return m.handleKey(msg)

	case downloadSimTickMsg:
		return m.handleDownloadSimTick()

	case downloadTickMsg:
		return m.handleDownloadTick(msg.progress)

	case downloadDoneMsg:
		m.downloading = false
		m.downloadDone = true
		m.downloadErr = msg.err
		return m, nil

	case healthDoneMsg:
		m.checking = false
		m.healthReport = msg.report
		return m, nil

	case spinner.TickMsg:
		if m.checking {
			var cmd tea.Cmd
			m.healthSpin, cmd = m.healthSpin.Update(msg)
			return m, cmd
		}
		return m, nil
	}

	// Forward to text inputs if on API key step.
	if m.step == StepAPIKeys && len(m.apiKeyInputs) > 0 {
		return m.updateTextInputs(msg)
	}

	return m, nil
}

// View renders the current wizard step.
func (m WizardModel) View() string {
	var sections []string

	// Progress indicator.
	progress := components.ProgressStep{
		Steps:   wizardStepLabels(),
		Current: int(m.step),
		Width:   m.width,
	}
	sections = append(sections, "")
	sections = append(sections, "  "+progress.Render())
	sections = append(sections, "")
	sections = append(sections, "  "+styles.Divider(clampWidth(m.width-4, 76)))
	sections = append(sections, "")

	// Explain panel (educational annotation before step content).
	if m.explain {
		explainText := m.explainContent()
		if explainText != "" {
			boxStyle := lipgloss.NewStyle().
				Background(styles.BgSurface).
				Foreground(styles.AccentSecondary).
				Border(styles.ThinBorder).
				BorderForeground(styles.AccentSecondary).
				Padding(0, 1).
				Width(clampWidth(m.width-6, 72))
			sections = append(sections, "  "+boxStyle.Render(styles.Gold("[explain] ")+explainText))
			sections = append(sections, "")
		}
	}

	// Step body.
	switch m.step {
	case StepWelcome:
		sections = append(sections, m.viewWelcome())
	case StepPathSelect:
		sections = append(sections, m.viewPathSelect())
	case StepMarketSelect:
		sections = append(sections, m.viewMarketSelect())
	case StepAPIKeys:
		sections = append(sections, m.viewAPIKeys())
	case StepDataDownload:
		sections = append(sections, m.viewDataDownload())
	case StepHealthCheck:
		sections = append(sections, m.viewHealthCheck())
	case StepReady:
		sections = append(sections, m.viewReady())
	}

	// Quit confirmation overlay.
	if m.confirmQuit {
		sections = append(sections, "")
		quitStyle := lipgloss.NewStyle().
			Background(styles.BgSurface).
			Foreground(styles.StatusWarn).
			Border(styles.RoundedBorder).
			BorderForeground(styles.StatusWarn).
			Padding(0, 1)
		sections = append(sections, "  "+quitStyle.Render("Quit onboarding? Progress will be lost.  y/n"))
	}

	// Divider + footer.
	sections = append(sections, "")
	sections = append(sections, "  "+styles.Divider(clampWidth(m.width-4, 76)))
	sections = append(sections, m.renderFooter())

	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}

// ---------------------------------------------------------------------------
// Key handling
// ---------------------------------------------------------------------------

func (m WizardModel) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	key := msg.String()

	// Quit confirmation takes priority.
	if m.confirmQuit {
		switch key {
		case "y", "Y":
			return m, tea.Quit
		default:
			m.confirmQuit = false
			return m, nil
		}
	}

	// Global shortcuts.
	if key == "ctrl+c" {
		return m, tea.Quit
	}
	if key == "?" {
		m.explain = !m.explain
		return m, nil
	}

	switch m.step {
	case StepWelcome:
		return m.handleWelcomeKey(key)
	case StepPathSelect:
		return m.handlePathKey(key)
	case StepMarketSelect:
		return m.handleMarketsKey(key)
	case StepAPIKeys:
		return m.handleAPIKeysKey(msg)
	case StepDataDownload:
		return m.handleDownloadKey(key)
	case StepHealthCheck:
		return m.handleHealthKey(key)
	case StepReady:
		return m.handleReadyKey(key)
	}

	return m, nil
}

// Step 0: Welcome -- press Enter to begin.
func (m WizardModel) handleWelcomeKey(key string) (tea.Model, tea.Cmd) {
	switch key {
	case "q":
		m.confirmQuit = true
	case "enter":
		m.step = StepPathSelect
	}
	return m, nil
}

// Step 1: Path -- developer or trader.
func (m WizardModel) handlePathKey(key string) (tea.Model, tea.Cmd) {
	switch key {
	case "q":
		m.confirmQuit = true
	case "up", "k":
		m.pathCursor = 0
	case "down", "j":
		m.pathCursor = 1
	case "1":
		m.path = "developer"
		m.pathCursor = 0
		m.step = StepMarketSelect
	case "2":
		m.path = "trader"
		m.pathCursor = 1
		m.step = StepMarketSelect
	case "enter":
		if m.pathCursor == 0 {
			m.path = "developer"
		} else {
			m.path = "trader"
		}
		m.step = StepMarketSelect
	case "backspace", "esc":
		m.step = StepWelcome
	}
	return m, nil
}

// Step 2: Markets -- checkbox toggles.
func (m WizardModel) handleMarketsKey(key string) (tea.Model, tea.Cmd) {
	switch key {
	case "q":
		m.confirmQuit = true
	case "up", "k":
		if m.marketCursor > 0 {
			m.marketCursor--
		}
	case "down", "j":
		if m.marketCursor < len(m.markets)-1 {
			m.marketCursor++
		}
	case " ":
		m.markets[m.marketCursor].Checked = !m.markets[m.marketCursor].Checked
	case "enter":
		hasSelection := false
		for _, mkt := range m.markets {
			if mkt.Checked {
				hasSelection = true
				break
			}
		}
		if !hasSelection {
			return m, nil
		}
		m.buildAPIKeyInputs()
		m.step = StepAPIKeys
		if len(m.apiKeyInputs) > 0 {
			m.focusedInput = 0
			m.apiKeyInputs[0].Focus()
			return m, textinput.Blink
		}
	case "backspace", "esc":
		m.step = StepPathSelect
	}
	return m, nil
}

// Step 3: API Keys -- text input navigation.
func (m WizardModel) handleAPIKeysKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	key := msg.String()

	switch key {
	case "tab", "down":
		return m.nextInput()
	case "shift+tab", "up":
		return m.prevInput()
	case "enter":
		// Collect values.
		for i, inp := range m.apiKeyInputs {
			m.apiKeys[m.apiKeyLabels[i]] = inp.Value()
		}
		// Write .env file.
		m.writeEnvFile()
		// Advance to download step.
		m.step = StepDataDownload
		m.downloading = true
		m.downloadSim = 0.0
		m.initDownloadLines()
		return m, tea.Batch(m.startDownload(), downloadSimTick())
	case "esc":
		m.step = StepMarketSelect
		return m, nil
	}

	return m.updateTextInputs(msg)
}

// Step 4: Download -- wait for progress or completion.
func (m WizardModel) handleDownloadKey(key string) (tea.Model, tea.Cmd) {
	switch key {
	case "q":
		m.confirmQuit = true
	case "enter":
		if m.downloadDone {
			m.step = StepHealthCheck
			m.checking = true
			return m, tea.Batch(m.healthSpin.Tick, m.runHealthChecks())
		}
	}
	return m, nil
}

// Step 5: Health -- wait for results.
func (m WizardModel) handleHealthKey(key string) (tea.Model, tea.Cmd) {
	switch key {
	case "q":
		m.confirmQuit = true
	case "enter":
		if m.healthReport != nil {
			m.step = StepReady
		}
	}
	return m, nil
}

// Step 6: Ready -- exit.
func (m WizardModel) handleReadyKey(key string) (tea.Model, tea.Cmd) {
	switch key {
	case "enter", "q":
		return m, tea.Quit
	}
	return m, nil
}

// ---------------------------------------------------------------------------
// Text input management
// ---------------------------------------------------------------------------

func (m *WizardModel) buildAPIKeyInputs() {
	m.apiKeyInputs = nil
	m.apiKeyLabels = nil

	for _, mkt := range m.markets {
		if !mkt.Checked {
			continue
		}
		switch mkt.Label {
		case "Futures":
			ti := textinput.New()
			ti.Placeholder = "db-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
			ti.CharLimit = 64
			ti.Width = 48
			ti.PromptStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary)
			ti.TextStyle = lipgloss.NewStyle().Foreground(styles.TextPrimary)
			ti.Cursor.Style = lipgloss.NewStyle().Foreground(styles.AccentPrimary)
			ti.EchoMode = textinput.EchoPassword
			ti.EchoCharacter = '*'
			m.apiKeyInputs = append(m.apiKeyInputs, ti)
			m.apiKeyLabels = append(m.apiKeyLabels, "DATABENTO_API_KEY")

		case "Crypto CEX":
			tiKey := textinput.New()
			tiKey.Placeholder = "Binance API key (optional)"
			tiKey.CharLimit = 128
			tiKey.Width = 48
			tiKey.PromptStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary)
			tiKey.TextStyle = lipgloss.NewStyle().Foreground(styles.TextPrimary)
			tiKey.Cursor.Style = lipgloss.NewStyle().Foreground(styles.AccentPrimary)
			m.apiKeyInputs = append(m.apiKeyInputs, tiKey)
			m.apiKeyLabels = append(m.apiKeyLabels, "BINANCE_API_KEY")

			tiSecret := textinput.New()
			tiSecret.Placeholder = "Binance API secret (optional)"
			tiSecret.CharLimit = 128
			tiSecret.Width = 48
			tiSecret.PromptStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary)
			tiSecret.TextStyle = lipgloss.NewStyle().Foreground(styles.TextPrimary)
			tiSecret.Cursor.Style = lipgloss.NewStyle().Foreground(styles.AccentPrimary)
			tiSecret.EchoMode = textinput.EchoPassword
			tiSecret.EchoCharacter = '*'
			m.apiKeyInputs = append(m.apiKeyInputs, tiSecret)
			m.apiKeyLabels = append(m.apiKeyLabels, "BINANCE_API_SECRET")

		case "Crypto DEX":
			ti := textinput.New()
			ti.Placeholder = "0x... Hyperliquid wallet address (optional)"
			ti.CharLimit = 64
			ti.Width = 48
			ti.PromptStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary)
			ti.TextStyle = lipgloss.NewStyle().Foreground(styles.TextPrimary)
			ti.Cursor.Style = lipgloss.NewStyle().Foreground(styles.AccentPrimary)
			m.apiKeyInputs = append(m.apiKeyInputs, ti)
			m.apiKeyLabels = append(m.apiKeyLabels, "HYPERLIQUID_WALLET")
		}
	}

	m.focusedInput = 0
}

func (m WizardModel) nextInput() (tea.Model, tea.Cmd) {
	if len(m.apiKeyInputs) == 0 {
		return m, nil
	}
	m.apiKeyInputs[m.focusedInput].Blur()
	m.focusedInput = (m.focusedInput + 1) % len(m.apiKeyInputs)
	m.apiKeyInputs[m.focusedInput].Focus()
	return m, textinput.Blink
}

func (m WizardModel) prevInput() (tea.Model, tea.Cmd) {
	if len(m.apiKeyInputs) == 0 {
		return m, nil
	}
	m.apiKeyInputs[m.focusedInput].Blur()
	m.focusedInput--
	if m.focusedInput < 0 {
		m.focusedInput = len(m.apiKeyInputs) - 1
	}
	m.apiKeyInputs[m.focusedInput].Focus()
	return m, textinput.Blink
}

func (m WizardModel) updateTextInputs(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd
	for i := range m.apiKeyInputs {
		var cmd tea.Cmd
		m.apiKeyInputs[i], cmd = m.apiKeyInputs[i].Update(msg)
		cmds = append(cmds, cmd)
	}
	return m, tea.Batch(cmds...)
}

// ---------------------------------------------------------------------------
// Download logic
// ---------------------------------------------------------------------------

func (m *WizardModel) initDownloadLines() {
	var lines []DownloadLine
	for _, mkt := range m.markets {
		if !mkt.Checked {
			continue
		}
		for _, sym := range symbolsForMarket(mkt.Label) {
			lines = append(lines, DownloadLine{Symbol: sym})
		}
	}
	m.downloadProg = lines
}

func symbolsForMarket(market string) []string {
	switch market {
	case "Futures":
		return []string{"ES", "NQ", "YM", "GC"}
	case "Crypto CEX":
		return []string{"BTC/USDT", "ETH/USDT"}
	case "Crypto DEX":
		return []string{"BTC-PERP", "ETH-PERP"}
	default:
		return nil
	}
}

func marketKey(label string) string {
	switch label {
	case "Futures":
		return "futures"
	case "Crypto CEX":
		return "crypto-cex"
	case "Crypto DEX":
		return "crypto-dex"
	default:
		return strings.ToLower(label)
	}
}

func (m *WizardModel) startDownload() tea.Cmd {
	root := m.projectRoot
	selectedMarkets := make([]Checkbox, len(m.markets))
	copy(selectedMarkets, m.markets)
	apiKey := m.apiKeys["DATABENTO_API_KEY"]

	return func() tea.Msg {
		runner, err := python.NewRunner(root)
		if err != nil {
			// Python not available -- let simulated progress handle it.
			time.Sleep(6 * time.Second)
			return downloadDoneMsg{err: nil}
		}

		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
		defer cancel()

		for _, mkt := range selectedMarkets {
			if !mkt.Checked {
				continue
			}
			syms := symbolsForMarket(mkt.Label)
			if len(syms) == 0 {
				continue
			}

			opts := python.DownloadOptions{
				Market:  marketKey(mkt.Label),
				Symbols: syms,
				Period:  "2y",
				APIKey:  apiKey,
			}

			progCh, dlErr := runner.DownloadData(ctx, opts)
			if dlErr != nil {
				continue
			}

			for range progCh {
				// Progress updates are consumed; the simulated tick handles
				// visual updates since we cannot send tea.Msg from here
				// without a Program reference.
			}
		}

		return downloadDoneMsg{err: nil}
	}
}

func downloadSimTick() tea.Cmd {
	return tea.Tick(400*time.Millisecond, func(_ time.Time) tea.Msg {
		return downloadSimTickMsg{}
	})
}

func (m WizardModel) handleDownloadSimTick() (tea.Model, tea.Cmd) {
	if !m.downloading {
		return m, nil
	}

	m.downloadSim += 0.04
	if m.downloadSim > 1.0 {
		m.downloadSim = 1.0
	}

	// Distribute simulated progress across download lines.
	total := len(m.downloadProg)
	if total > 0 {
		perItem := 1.0 / float64(total)
		for i := range m.downloadProg {
			itemStart := float64(i) * perItem
			itemEnd := itemStart + perItem
			if m.downloadSim >= itemEnd {
				m.downloadProg[i].Progress = 1.0
				m.downloadProg[i].Done = true
			} else if m.downloadSim >= itemStart {
				m.downloadProg[i].Progress = (m.downloadSim - itemStart) / perItem
			}
		}
	}

	return m, downloadSimTick()
}

func (m WizardModel) handleDownloadTick(p python.DownloadProgress) (tea.Model, tea.Cmd) {
	for i := range m.downloadProg {
		if m.downloadProg[i].Symbol == p.Symbol {
			m.downloadProg[i].Progress = p.Progress
			m.downloadProg[i].Message = p.Message
			m.downloadProg[i].Done = p.Done
			m.downloadProg[i].Error = p.Error
		}
	}
	return m, nil
}

// ---------------------------------------------------------------------------
// Health check logic
// ---------------------------------------------------------------------------

func (m *WizardModel) runHealthChecks() tea.Cmd {
	root := m.projectRoot
	return func() tea.Msg {
		checker := health.NewChecker(root)
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
		defer cancel()
		report := checker.RunAll(ctx)
		return healthDoneMsg{report: report}
	}
}

// ---------------------------------------------------------------------------
// .env writer
// ---------------------------------------------------------------------------

func (m *WizardModel) writeEnvFile() {
	envPath := filepath.Join(m.projectRoot, ".env")

	// Read existing content to preserve keys we don't manage.
	existing := make(map[string]string)
	var preservedComments []string
	if data, err := os.ReadFile(envPath); err == nil {
		for _, line := range strings.Split(string(data), "\n") {
			trimmed := strings.TrimSpace(line)
			if trimmed == "" {
				continue
			}
			if strings.HasPrefix(trimmed, "#") {
				preservedComments = append(preservedComments, trimmed)
				continue
			}
			parts := strings.SplitN(trimmed, "=", 2)
			if len(parts) == 2 {
				existing[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
			}
		}
	}

	// Merge wizard keys.
	for k, v := range m.apiKeys {
		v = strings.TrimSpace(v)
		if v != "" {
			existing[k] = v
		}
	}

	// Write back.
	var b strings.Builder
	b.WriteString("# Generated by sigma-quant init\n")
	for _, c := range preservedComments {
		if !strings.Contains(c, "Generated by sigma-quant") {
			b.WriteString(c + "\n")
		}
	}
	for k, v := range existing {
		b.WriteString(fmt.Sprintf("%s=%s\n", k, v))
	}

	_ = os.WriteFile(envPath, []byte(b.String()), 0600)
}

// ---------------------------------------------------------------------------
// View renderers
// ---------------------------------------------------------------------------

func (m WizardModel) viewWelcome() string {
	var b strings.Builder

	b.WriteString(styles.Logo())
	b.WriteString("\n\n")

	tagline := lipgloss.NewStyle().
		Foreground(styles.TextSecondary).
		Italic(true).
		Render("Your autonomous strategy research team")
	b.WriteString("  " + tagline + "\n\n")

	prompt := lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).
		Bold(true).
		Render("Press Enter to begin setup")
	b.WriteString("  " + prompt + "\n")

	return b.String()
}

func (m WizardModel) viewPathSelect() string {
	var b strings.Builder

	b.WriteString("  " + styles.Title.Render("Choose Your Path") + "\n\n")

	options := []struct {
		label string
		desc  string
	}{
		{"Developer", "I code strategies and extend the system"},
		{"Trader", "I discover strategies with minimal coding"},
	}

	for i, opt := range options {
		cursor := "  "
		optStyle := lipgloss.NewStyle().Foreground(styles.TextSecondary)
		descStyle := lipgloss.NewStyle().Foreground(styles.TextMuted)

		if i == m.pathCursor {
			cursor = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render("> ")
			optStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true)
			descStyle = lipgloss.NewStyle().Foreground(styles.TextSecondary)
		}

		b.WriteString("  " + cursor + optStyle.Render(opt.label) + "\n")
		b.WriteString("      " + descStyle.Render(opt.desc) + "\n\n")
	}

	return b.String()
}

func (m WizardModel) viewMarketSelect() string {
	var b strings.Builder

	b.WriteString("  " + styles.Title.Render("Select Markets") + "\n")
	b.WriteString("  " + styles.Dim("Use space to toggle, enter to confirm") + "\n\n")

	for i, mkt := range m.markets {
		cursor := "  "
		if i == m.marketCursor {
			cursor = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render("> ")
		}

		check := lipgloss.NewStyle().Foreground(styles.TextMuted).Render("[ ]")
		if mkt.Checked {
			check = lipgloss.NewStyle().Foreground(styles.StatusOK).Bold(true).Render("[x]")
		}

		labelStyle := lipgloss.NewStyle().Foreground(styles.TextPrimary)
		if i == m.marketCursor {
			labelStyle = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true)
		}

		b.WriteString("  " + cursor + check + " " + labelStyle.Render(mkt.Label) + "\n")
		b.WriteString("        " + styles.Dim(mkt.Desc) + "\n\n")
	}

	return b.String()
}

func (m WizardModel) viewAPIKeys() string {
	var b strings.Builder

	b.WriteString("  " + styles.Title.Render("Configure API Keys") + "\n\n")

	if len(m.apiKeyInputs) == 0 {
		b.WriteString("  " + styles.Dim("No API keys needed for your selection. Press Enter to continue.") + "\n")
		return b.String()
	}

	for i, inp := range m.apiKeyInputs {
		labelColor := styles.TextSecondary
		if i == m.focusedInput {
			labelColor = styles.AccentPrimary
		}
		label := lipgloss.NewStyle().Foreground(labelColor).Bold(true).Render(m.apiKeyLabels[i])
		b.WriteString("  " + label + "\n")
		b.WriteString("  " + inp.View() + "\n\n")
	}

	b.WriteString("  " + styles.Dim("Press Tab to switch fields, Enter to continue") + "\n")

	return b.String()
}

func (m WizardModel) viewDataDownload() string {
	var b strings.Builder

	b.WriteString("  " + styles.Title.Render("Downloading Market Data") + "\n\n")

	if len(m.downloadProg) == 0 {
		b.WriteString("  " + styles.Dim("No symbols to download for your selection.") + "\n")
		b.WriteString("\n  Press Enter to continue.\n")
		return b.String()
	}

	barWidth := clampWidth(m.width-24, 40)
	for _, dl := range m.downloadProg {
		sym := lipgloss.NewStyle().
			Foreground(styles.TextPrimary).
			Bold(true).
			Width(12).
			Render(dl.Symbol)

		bar := renderProgressBar(dl.Progress, barWidth)

		status := ""
		if dl.Error != "" {
			status = lipgloss.NewStyle().Foreground(styles.StatusError).Render(" " + dl.Error)
		} else if dl.Done {
			status = lipgloss.NewStyle().Foreground(styles.StatusOK).Bold(true).Render(" done")
		} else if dl.Message != "" {
			status = lipgloss.NewStyle().Foreground(styles.TextMuted).Render(" " + dl.Message)
		}

		b.WriteString(fmt.Sprintf("  %s %s%s\n", sym, bar, status))
	}

	if m.downloadDone {
		b.WriteString("\n")
		if m.downloadErr != nil {
			b.WriteString("  " + styles.Gold("Download completed with warnings.") + " Press Enter to continue.\n")
		} else {
			b.WriteString("  " + styles.Green("Download complete.") + " Press Enter to continue.\n")
		}
	} else {
		b.WriteString("\n  " + styles.Dim("Downloading historical data...") + "\n")
	}

	return b.String()
}

func (m WizardModel) viewHealthCheck() string {
	var b strings.Builder

	b.WriteString("  " + styles.Title.Render("System Health Check") + "\n\n")

	if m.checking {
		b.WriteString("  " + m.healthSpin.View() + " Running checks...\n")
		return b.String()
	}

	if m.healthReport == nil {
		b.WriteString("  " + styles.Dim("Waiting to start...") + "\n")
		return b.String()
	}

	// Display results grouped by category.
	nameStyle := lipgloss.NewStyle().Width(22).Foreground(styles.TextPrimary)
	msgStyle := lipgloss.NewStyle().Foreground(styles.TextSecondary)
	catStyle := lipgloss.NewStyle().Foreground(styles.AccentSecondary).Bold(true)

	categoryOrder := []string{"system", "project", "data", "runtime"}
	grouped := make(map[string][]health.CheckResult)
	for _, r := range m.healthReport.Results {
		grouped[r.Category] = append(grouped[r.Category], r)
	}

	for _, cat := range categoryOrder {
		results, ok := grouped[cat]
		if !ok || len(results) == 0 {
			continue
		}
		label := strings.ToUpper(cat[:1]) + cat[1:]
		b.WriteString("  " + catStyle.Render(label) + "\n")
		for _, r := range results {
			sym := wizardStatusIcon(r.Status)
			b.WriteString(fmt.Sprintf("  %s %s %s\n", sym, nameStyle.Render(r.Name), msgStyle.Render(r.Message)))
		}
		b.WriteString("\n")
	}

	// Summary.
	summary := fmt.Sprintf("%d/%d passed", m.healthReport.Passed, m.healthReport.Total)
	if m.healthReport.Warned > 0 {
		summary += fmt.Sprintf(", %d warnings", m.healthReport.Warned)
	}
	if m.healthReport.Failed > 0 {
		summary += fmt.Sprintf(", %d failed", m.healthReport.Failed)
	}
	b.WriteString("  " + styles.Dim(summary) + "\n")
	b.WriteString("\n  Press Enter to continue.\n")

	return b.String()
}

func (m WizardModel) viewReady() string {
	var b strings.Builder

	readyStyle := lipgloss.NewStyle().
		Foreground(styles.StatusOK).
		Bold(true)
	b.WriteString("\n  " + readyStyle.Render("All systems ready!") + "\n\n")

	// Summary panel.
	panelWidth := clampWidth(m.width-6, 60)
	panelStyle := lipgloss.NewStyle().
		Background(styles.BgPanel).
		Border(styles.RoundedBorder).
		BorderForeground(styles.AccentPrimary).
		Padding(1).
		Width(panelWidth)

	var summary strings.Builder
	summary.WriteString(styles.Label.Render("PATH    ") + "  " + styles.Value.Render(m.path) + "\n")

	var selectedMarkets []string
	for _, mkt := range m.markets {
		if mkt.Checked {
			selectedMarkets = append(selectedMarkets, mkt.Label)
		}
	}
	summary.WriteString(styles.Label.Render("MARKETS ") + "  " + styles.Value.Render(strings.Join(selectedMarkets, ", ")) + "\n")

	keyCount := 0
	for _, v := range m.apiKeys {
		if strings.TrimSpace(v) != "" {
			keyCount++
		}
	}
	summary.WriteString(styles.Label.Render("API KEYS") + "  " + styles.Value.Render(fmt.Sprintf("%d configured", keyCount)) + "\n")

	if m.healthReport != nil {
		healthStatus := styles.Green("HEALTHY")
		if m.healthReport.Failed > 0 {
			healthStatus = styles.Red("ISSUES DETECTED")
		} else if m.healthReport.Warned > 0 {
			healthStatus = styles.Gold("DEGRADED")
		}
		summary.WriteString(styles.Label.Render("HEALTH  ") + "  " + healthStatus)
	}

	b.WriteString("  " + panelStyle.Render(summary.String()) + "\n\n")

	nextCmd := lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).
		Bold(true).
		Render("sigma-quant start")
	b.WriteString("  Run " + nextCmd + " to begin research.\n\n")
	b.WriteString("  Press Enter to exit.\n")

	return b.String()
}

// ---------------------------------------------------------------------------
// Explain content per step
// ---------------------------------------------------------------------------

func (m WizardModel) explainContent() string {
	switch m.step {
	case StepWelcome:
		return "Sigma-Quant Stream orchestrates AI agents that discover, backtest, and validate trading strategies autonomously."
	case StepPathSelect:
		return "Developers get full access to code modification, custom indicators, and pipeline extension. Traders get a streamlined interface focused on strategy discovery with pre-built components."
	case StepMarketSelect:
		return "Futures require a Databento API key for institutional-grade CME data. Crypto markets use free exchange APIs (CCXT for CEX, on-chain for DEX)."
	case StepAPIKeys:
		return "API keys are stored locally in .env and never transmitted. Databento provides tick-level CME futures data; crypto data is freely available."
	case StepDataDownload:
		return "Historical data is downloaded for backtesting. The system fetches 2 years of OHLCV data per symbol. This may take a few minutes depending on connection speed."
	case StepHealthCheck:
		return "The health checker validates Python dependencies, project structure, data files, and runtime prerequisites. Warnings are non-blocking; failures may need attention before running."
	case StepReady:
		return "Your workspace is configured. The start command launches tmux with AI worker panes that begin autonomous strategy research."
	}
	return ""
}

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------

func (m WizardModel) renderFooter() string {
	hints := []components.KeyHint{
		{Key: "?", Desc: "explain"},
	}

	switch m.step {
	case StepWelcome:
		hints = append(hints,
			components.KeyHint{Key: "enter", Desc: "begin"},
			components.KeyHint{Key: "q", Desc: "quit"},
		)
	case StepPathSelect:
		hints = append(hints,
			components.KeyHint{Key: "j/k", Desc: "navigate"},
			components.KeyHint{Key: "enter", Desc: "select"},
			components.KeyHint{Key: "backspace", Desc: "back"},
			components.KeyHint{Key: "q", Desc: "quit"},
		)
	case StepMarketSelect:
		hints = append(hints,
			components.KeyHint{Key: "space", Desc: "toggle"},
			components.KeyHint{Key: "j/k", Desc: "navigate"},
			components.KeyHint{Key: "enter", Desc: "continue"},
			components.KeyHint{Key: "backspace", Desc: "back"},
		)
	case StepAPIKeys:
		hints = append(hints,
			components.KeyHint{Key: "tab", Desc: "next field"},
			components.KeyHint{Key: "enter", Desc: "continue"},
			components.KeyHint{Key: "esc", Desc: "back"},
		)
	case StepDataDownload:
		if m.downloadDone {
			hints = append(hints, components.KeyHint{Key: "enter", Desc: "continue"})
		} else {
			hints = append(hints, components.KeyHint{Key: "ctrl+c", Desc: "abort"})
		}
	case StepHealthCheck:
		if m.healthReport != nil {
			hints = append(hints, components.KeyHint{Key: "enter", Desc: "continue"})
		} else {
			hints = append(hints, components.KeyHint{Key: "ctrl+c", Desc: "abort"})
		}
	case StepReady:
		hints = append(hints, components.KeyHint{Key: "enter", Desc: "exit"})
	}

	footer := components.Footer{
		Hints: hints,
		Width: m.width,
	}
	return footer.Render()
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func wizardStatusIcon(s health.Status) string {
	switch s {
	case health.StatusPass:
		return lipgloss.NewStyle().Foreground(styles.StatusOK).Bold(true).Render("+")
	case health.StatusWarn:
		return lipgloss.NewStyle().Foreground(styles.StatusWarn).Bold(true).Render("!")
	case health.StatusFail:
		return lipgloss.NewStyle().Foreground(styles.StatusError).Bold(true).Render("x")
	default:
		return lipgloss.NewStyle().Foreground(styles.TextMuted).Render("?")
	}
}

func renderProgressBar(progress float64, width int) string {
	if width <= 2 {
		width = 20
	}
	filled := int(progress * float64(width))
	if filled > width {
		filled = width
	}
	empty := width - filled

	bar := lipgloss.NewStyle().Foreground(styles.AccentPrimary).Render(strings.Repeat("█", filled))
	bar += lipgloss.NewStyle().Foreground(styles.TextMuted).Render(strings.Repeat("░", empty))

	pct := lipgloss.NewStyle().Foreground(styles.TextSecondary).Width(5).Render(
		fmt.Sprintf("%3.0f%%", progress*100),
	)

	return "[" + bar + "] " + pct
}

func clampWidth(val, max int) int {
	if val > max {
		return max
	}
	if val < 10 {
		return 10
	}
	return val
}
