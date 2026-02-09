package models

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/components"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
)

// ---------------------------------------------------------------------------
// Strategy entry — data model for a single discovered strategy
// ---------------------------------------------------------------------------

// StrategyEntry holds parsed data for a single strategy file.
type StrategyEntry struct {
	Name         string                 `json:"name"`
	Status       string                 `json:"status"`
	Sharpe       float64                `json:"sharpe"`
	MaxDD        float64                `json:"max_dd"`
	WinRate      float64                `json:"win_rate"`
	TradeCount   int                    `json:"trade_count"`
	Market       string                 `json:"market"`
	FilePath     string                 `json:"file_path"`
	ProfitFactor float64                `json:"profit_factor"`
	OOSDecay     float64                `json:"oos_decay"`
	TotalReturn  float64                `json:"total_return"`
	Parameters   map[string]interface{} `json:"parameters"`
}

// ---------------------------------------------------------------------------
// Filter / sort constants
// ---------------------------------------------------------------------------

var filterTabs = []string{"All", "Good", "Under Review", "Rejected", "Prop Firm Ready"}

// filterKey maps tab index to the internal status value used for filtering.
var filterKey = []string{"all", "good", "under_review", "rejected", "prop_firm_ready"}

var sortColumns = []struct {
	key   string
	label string
}{
	{"name", "Name"},
	{"sharpe", "Sharpe"},
	{"trades", "Trades"},
	{"maxdd", "MaxDD"},
}

// ---------------------------------------------------------------------------
// Bubble Tea model
// ---------------------------------------------------------------------------

// StrategiesModel is the main Bubble Tea model for the strategy browser TUI.
type StrategiesModel struct {
	// Data
	strategies []StrategyEntry
	filtered   []StrategyEntry

	// State
	cursor     int
	filterIdx  int    // index into filterTabs / filterKey
	sortBy     string // "name", "sharpe", "trades", "maxdd"
	sortAsc    bool
	detailView bool // showing detail for selected strategy
	searchMode bool
	searchTerm string

	// Components
	tabBar components.TabBar
	footer components.Footer
	header components.Header

	// Layout
	width  int
	height int

	// Config
	projectRoot string
}

// NewStrategiesModel creates a new model. filter should be one of the filterKey
// values (or empty/"all" for no filtering).
func NewStrategiesModel(filter string, projectRoot string) StrategiesModel {
	filterIdx := 0
	if filter != "" {
		for i, k := range filterKey {
			if k == filter || strings.ReplaceAll(k, "_", "-") == filter {
				filterIdx = i
				break
			}
		}
	}

	m := StrategiesModel{
		filterIdx:   filterIdx,
		sortBy:      "sharpe",
		sortAsc:     false,
		projectRoot: projectRoot,
		width:       100,
		height:      30,
	}

	m.tabBar = components.TabBar{
		Tabs:      filterTabs,
		ActiveTab: filterIdx,
		Width:     m.width,
	}

	m.footer = components.BrowserFooter(m.width)

	m.header = components.Header{
		Profile: "STRATEGIES",
		Width:   m.width,
	}

	return m
}

// ---------------------------------------------------------------------------
// Bubble Tea interface
// ---------------------------------------------------------------------------

// Init loads strategy data from disk on startup.
func (m StrategiesModel) Init() tea.Cmd {
	return func() tea.Msg {
		entries := loadStrategies(m.projectRoot)
		return strategiesLoadedMsg(entries)
	}
}

// strategiesLoadedMsg carries the loaded strategy entries back to Update.
type strategiesLoadedMsg []StrategyEntry

// Update handles keypresses and messages.
func (m StrategiesModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case strategiesLoadedMsg:
		m.strategies = []StrategyEntry(msg)
		m.applyFilter()
		return m, nil

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.tabBar.Width = m.width
		m.footer.Width = m.width
		m.header.Width = m.width
		return m, nil

	case tea.KeyMsg:
		return m.handleKey(msg)
	}

	return m, nil
}

// handleKey dispatches key events depending on the current view state.
func (m StrategiesModel) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	key := msg.String()

	// --- Global keys ---
	switch key {
	case "ctrl+c":
		return m, tea.Quit
	}

	// --- Search mode ---
	if m.searchMode {
		return m.handleSearchKey(msg)
	}

	// --- Detail view ---
	if m.detailView {
		return m.handleDetailKey(msg)
	}

	// --- List view ---
	return m.handleListKey(msg)
}

func (m StrategiesModel) handleSearchKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	key := msg.String()
	switch key {
	case "esc":
		m.searchMode = false
		m.searchTerm = ""
		m.applyFilter()
		return m, nil
	case "enter":
		m.searchMode = false
		// keep current filtered results
		return m, nil
	case "backspace":
		if len(m.searchTerm) > 0 {
			m.searchTerm = m.searchTerm[:len(m.searchTerm)-1]
			m.applyFilter()
		}
		return m, nil
	default:
		// Only accept printable runes.
		if len(key) == 1 && key[0] >= 32 && key[0] < 127 {
			m.searchTerm += key
			m.applyFilter()
			m.cursor = 0
		}
		return m, nil
	}
}

func (m StrategiesModel) handleDetailKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "q", "backspace", "esc":
		m.detailView = false
		m.footer = components.BrowserFooter(m.width)
		return m, nil
	}
	return m, nil
}

func (m StrategiesModel) handleListKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	key := msg.String()
	switch key {
	case "q":
		return m, tea.Quit

	case "up", "k":
		if m.cursor > 0 {
			m.cursor--
		}
		return m, nil

	case "down", "j":
		if m.cursor < len(m.filtered)-1 {
			m.cursor++
		}
		return m, nil

	case "enter":
		if len(m.filtered) > 0 {
			m.detailView = true
			m.footer = components.Footer{
				Hints: []components.KeyHint{
					{Key: "backspace", Desc: "back to list"},
					{Key: "q", Desc: "quit"},
				},
				Width: m.width,
			}
		}
		return m, nil

	case "tab", "right", "l":
		m.filterIdx = (m.filterIdx + 1) % len(filterTabs)
		m.tabBar.ActiveTab = m.filterIdx
		m.cursor = 0
		m.applyFilter()
		return m, nil

	case "shift+tab", "left", "h":
		m.filterIdx--
		if m.filterIdx < 0 {
			m.filterIdx = len(filterTabs) - 1
		}
		m.tabBar.ActiveTab = m.filterIdx
		m.cursor = 0
		m.applyFilter()
		return m, nil

	case "/":
		m.searchMode = true
		m.searchTerm = ""
		return m, nil

	case "s":
		m.cycleSort()
		m.sortFiltered()
		return m, nil

	case "r":
		// Reverse sort direction.
		m.sortAsc = !m.sortAsc
		m.sortFiltered()
		return m, nil

	case "home", "g":
		m.cursor = 0
		return m, nil

	case "end", "G":
		if len(m.filtered) > 0 {
			m.cursor = len(m.filtered) - 1
		}
		return m, nil
	}

	return m, nil
}

// ---------------------------------------------------------------------------
// View
// ---------------------------------------------------------------------------

// View renders the full TUI.
func (m StrategiesModel) View() string {
	if m.detailView {
		return m.renderDetailView()
	}
	return m.renderListView()
}

func (m StrategiesModel) renderListView() string {
	var sections []string

	// Header.
	sections = append(sections, m.header.Render())

	// Tab bar.
	sections = append(sections, m.tabBar.Render())

	// Search bar (when active).
	if m.searchMode {
		searchStyle := lipgloss.NewStyle().
			Foreground(styles.AccentPrimary).
			PaddingLeft(2)
		sections = append(sections, searchStyle.Render("/ "+m.searchTerm+"_"))
	}

	// Sort indicator.
	sortLabel := ""
	for _, sc := range sortColumns {
		if sc.key == m.sortBy {
			arrow := "v"
			if m.sortAsc {
				arrow = "^"
			}
			sortLabel = fmt.Sprintf("Sort: %s %s", sc.label, arrow)
			break
		}
	}
	sortLine := lipgloss.NewStyle().
		Foreground(styles.TextMuted).
		PaddingLeft(2).
		Render(sortLabel + "  " + styles.Dim("(s: cycle  r: reverse)"))
	sections = append(sections, sortLine)

	// Separator.
	sections = append(sections, styles.Divider(m.width))

	// Table header.
	hdr := fmt.Sprintf(
		"  %-24s %-13s %8s %8s %8s %7s %8s",
		"STRATEGY", "STATUS", "SHARPE", "MAX DD", "WIN RT", "TRADES", "MARKET",
	)
	sections = append(sections, lipgloss.NewStyle().
		Foreground(styles.TextSecondary).
		Bold(true).
		Render(hdr))

	sections = append(sections, styles.Divider(m.width))

	// Empty state.
	if len(m.filtered) == 0 {
		emptyMsg := "  No strategies found."
		if m.searchTerm != "" {
			emptyMsg = fmt.Sprintf("  No strategies matching %q.", m.searchTerm)
		} else if m.filterIdx > 0 {
			emptyMsg = fmt.Sprintf("  No %s strategies. Run the pipeline to generate strategies.", strings.ToLower(filterTabs[m.filterIdx]))
		}
		empty := lipgloss.NewStyle().
			Foreground(styles.TextMuted).
			PaddingTop(1).
			PaddingBottom(1).
			Render(emptyMsg)
		sections = append(sections, empty)
	}

	// Table rows.
	// Compute visible window based on terminal height. Reserve lines for
	// header (1), tab bar (1), search bar (0-1), sort line (1), dividers (2),
	// table header (1), footer (1), count line (1) = ~8-9 lines overhead.
	overhead := 9
	if m.searchMode {
		overhead++
	}
	maxVisible := m.height - overhead
	if maxVisible < 5 {
		maxVisible = 5
	}

	// Scroll offset so cursor stays visible.
	scrollOffset := 0
	if m.cursor >= maxVisible {
		scrollOffset = m.cursor - maxVisible + 1
	}

	for i := scrollOffset; i < len(m.filtered) && i < scrollOffset+maxVisible; i++ {
		e := m.filtered[i]
		selected := i == m.cursor

		row := m.renderTableRow(e, i, selected)
		sections = append(sections, row)
	}

	// Count line.
	countLine := lipgloss.NewStyle().
		Foreground(styles.TextMuted).
		PaddingLeft(2).
		Render(fmt.Sprintf("%d of %d strategies", len(m.filtered), len(m.strategies)))
	sections = append(sections, countLine)

	// Footer.
	sections = append(sections, m.footer.Render())

	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}

func (m StrategiesModel) renderTableRow(e StrategyEntry, idx int, selected bool) string {
	// Status badge.
	statusColor := statusColor(e.Status)
	dot := lipgloss.NewStyle().Foreground(statusColor).Render("●")
	statusLabel := lipgloss.NewStyle().Foreground(statusColor).Bold(true).
		Width(11).Render(statusDisplayName(e.Status))

	// Name.
	nameStyle := lipgloss.NewStyle().Foreground(styles.TextPrimary)
	if selected {
		nameStyle = nameStyle.Bold(true).Foreground(styles.AccentPrimary)
	}
	name := nameStyle.Width(22).Render(styles.TruncateWithEllipsis(e.Name, 22))

	// Metrics — color-coded.
	sharpeStyle := metricStyle(e.Sharpe, 1.0, 0.5, true)
	sharpe := sharpeStyle.Width(8).Align(lipgloss.Right).Render(fmt.Sprintf("%.2f", e.Sharpe))

	ddStyle := metricStyle(e.MaxDD, 5.0, 10.0, false)
	dd := ddStyle.Width(8).Align(lipgloss.Right).Render(fmt.Sprintf("%.1f%%", e.MaxDD))

	wrStyle := metricStyle(e.WinRate, 50.0, 40.0, true)
	wr := wrStyle.Width(8).Align(lipgloss.Right).Render(fmt.Sprintf("%.0f%%", e.WinRate))

	trades := lipgloss.NewStyle().Foreground(styles.TextSecondary).
		Width(7).Align(lipgloss.Right).Render(fmt.Sprintf("%d", e.TradeCount))

	market := lipgloss.NewStyle().Foreground(styles.TextMuted).
		Width(8).Render(strings.ToUpper(e.Market))

	// Row background.
	cursor := "  "
	if selected {
		cursor = lipgloss.NewStyle().Foreground(styles.AccentPrimary).Bold(true).Render("> ")
	}

	rowBg := styles.BgPanel
	if idx%2 != 0 {
		rowBg = styles.BgSurface
	}
	if selected {
		rowBg = styles.BgHover
	}

	row := fmt.Sprintf("%s%s %s %s %s %s %s %s %s",
		cursor, name, dot, statusLabel, sharpe, dd, wr, trades, market)

	return lipgloss.NewStyle().
		Background(rowBg).
		Width(m.width).
		Render(row)
}

func (m StrategiesModel) renderDetailView() string {
	if len(m.filtered) == 0 || m.cursor >= len(m.filtered) {
		return "No strategy selected."
	}

	e := m.filtered[m.cursor]
	var sections []string

	// Header.
	sections = append(sections, m.header.Render())

	// Strategy card at top.
	card := components.StrategyCard{
		Name:       e.Name,
		Status:     e.Status,
		Sharpe:     e.Sharpe,
		MaxDD:      e.MaxDD,
		WinRate:    e.WinRate,
		TradeCount: e.TradeCount,
		Market:     e.Market,
	}
	sections = append(sections, card.Render())
	sections = append(sections, "")

	// Title.
	sections = append(sections, lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
		Render("Strategy Details"))
	sections = append(sections, styles.Divider(m.width))

	// Metric gauges row.
	gauges := []components.MetricGauge{
		{
			Label:      "Sharpe",
			Value:      e.Sharpe,
			Format:     "%.2f",
			Thresholds: [2]float64{1.0, 0.5},
			HighIsGood: true,
		},
		{
			Label:      "Max DD",
			Value:      e.MaxDD,
			Format:     "%.1f%%",
			Thresholds: [2]float64{5.0, 10.0},
			HighIsGood: false,
		},
		{
			Label:      "Win Rate",
			Value:      e.WinRate,
			Format:     "%.1f%%",
			Thresholds: [2]float64{50.0, 40.0},
			HighIsGood: true,
		},
		{
			Label:      "Profit Factor",
			Value:      e.ProfitFactor,
			Format:     "%.2f",
			Thresholds: [2]float64{1.5, 1.0},
			HighIsGood: true,
		},
	}

	var gaugeRendered []string
	for _, g := range gauges {
		gaugeRendered = append(gaugeRendered, lipgloss.NewStyle().
			Width(16).
			Align(lipgloss.Center).
			Render(g.Render()))
	}
	gaugeRow := lipgloss.JoinHorizontal(lipgloss.Top, gaugeRendered...)
	sections = append(sections, lipgloss.NewStyle().PaddingLeft(2).Render(gaugeRow))
	sections = append(sections, "")

	// Extended metrics.
	sections = append(sections, lipgloss.NewStyle().
		Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
		Render("Extended Metrics"))
	sections = append(sections, styles.Divider(m.width))

	metricLines := []struct {
		label string
		value string
	}{
		{"Total Return", fmt.Sprintf("%.2f%%", e.TotalReturn)},
		{"OOS Decay", fmt.Sprintf("%.2f%%", e.OOSDecay)},
		{"Trade Count", fmt.Sprintf("%d", e.TradeCount)},
		{"Market", strings.ToUpper(e.Market)},
		{"File", e.FilePath},
	}

	for _, ml := range metricLines {
		line := lipgloss.NewStyle().PaddingLeft(4).Render(
			styles.Label.Width(16).Render(ml.label+":") + " " +
				styles.Value.Render(ml.value))
		sections = append(sections, line)
	}
	sections = append(sections, "")

	// Parameters section.
	if len(e.Parameters) > 0 {
		sections = append(sections, lipgloss.NewStyle().
			Foreground(styles.AccentPrimary).Bold(true).PaddingLeft(2).
			Render("Parameters"))
		sections = append(sections, styles.Divider(m.width))

		// Sort parameter keys for deterministic output.
		keys := make([]string, 0, len(e.Parameters))
		for k := range e.Parameters {
			keys = append(keys, k)
		}
		sort.Strings(keys)

		for _, k := range keys {
			v := fmt.Sprintf("%v", e.Parameters[k])
			line := lipgloss.NewStyle().PaddingLeft(4).Render(
				styles.Label.Width(20).Render(k+":") + " " +
					styles.Value.Render(v))
			sections = append(sections, line)
		}
		sections = append(sections, "")
	}

	// Hints.
	hintStyle := lipgloss.NewStyle().Foreground(styles.TextMuted).PaddingLeft(2)
	sections = append(sections, hintStyle.Render("Press 'd' to deploy  |  backspace to return to list"))

	// Footer.
	sections = append(sections, m.footer.Render())

	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}

// ---------------------------------------------------------------------------
// Filter / sort helpers
// ---------------------------------------------------------------------------

func (m *StrategiesModel) applyFilter() {
	activeFilter := filterKey[m.filterIdx]

	m.filtered = m.filtered[:0]
	for _, s := range m.strategies {
		// Category filter.
		if activeFilter != "all" && s.Status != activeFilter {
			continue
		}
		// Search filter.
		if m.searchTerm != "" {
			if !strings.Contains(strings.ToLower(s.Name), strings.ToLower(m.searchTerm)) {
				continue
			}
		}
		m.filtered = append(m.filtered, s)
	}

	m.sortFiltered()

	// Clamp cursor.
	if m.cursor >= len(m.filtered) {
		m.cursor = len(m.filtered) - 1
	}
	if m.cursor < 0 {
		m.cursor = 0
	}
}

func (m *StrategiesModel) sortFiltered() {
	sort.SliceStable(m.filtered, func(i, j int) bool {
		a, b := m.filtered[i], m.filtered[j]
		less := false
		switch m.sortBy {
		case "name":
			less = strings.ToLower(a.Name) < strings.ToLower(b.Name)
		case "sharpe":
			less = a.Sharpe < b.Sharpe
		case "trades":
			less = a.TradeCount < b.TradeCount
		case "maxdd":
			less = a.MaxDD < b.MaxDD
		default:
			less = strings.ToLower(a.Name) < strings.ToLower(b.Name)
		}
		if !m.sortAsc {
			return !less
		}
		return less
	})
}

func (m *StrategiesModel) cycleSort() {
	for i, sc := range sortColumns {
		if sc.key == m.sortBy {
			next := (i + 1) % len(sortColumns)
			m.sortBy = sortColumns[next].key
			return
		}
	}
	m.sortBy = sortColumns[0].key
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

// loadStrategies scans the output/strategies/ subdirectories and parses any
// JSON files found. Non-JSON files get a basic entry with just name/status.
func loadStrategies(projectRoot string) []StrategyEntry {
	paths := config.NewPaths(projectRoot)

	dirs := map[string]string{
		"good":            paths.Output.StrategiesGood,
		"under_review":    paths.Output.StrategiesReview,
		"rejected":        paths.Output.StrategiesRejected,
		"prop_firm_ready": paths.Output.StrategiesPropFirm,
	}

	var entries []StrategyEntry

	for status, dir := range dirs {
		files, err := os.ReadDir(dir)
		if err != nil {
			continue // Directory may not exist yet.
		}

		for _, f := range files {
			if f.IsDir() {
				continue
			}
			name := f.Name()
			lower := strings.ToLower(name)

			// Only include strategy-related files.
			if !strings.HasSuffix(lower, ".json") &&
				!strings.HasSuffix(lower, ".py") &&
				!strings.HasSuffix(lower, ".yaml") &&
				!strings.HasSuffix(lower, ".yml") {
				continue
			}

			fullPath := filepath.Join(dir, name)
			entry := StrategyEntry{
				Name:     trimExtension(name),
				Status:   status,
				FilePath: fullPath,
				Market:   "futures",
			}

			// Attempt to parse JSON for richer data.
			if strings.HasSuffix(lower, ".json") {
				if parsed, err := parseStrategyJSON(fullPath); err == nil {
					// Overlay parsed fields, keeping status from directory.
					parsed.Status = status
					parsed.FilePath = fullPath
					if parsed.Name == "" {
						parsed.Name = entry.Name
					}
					if parsed.Market == "" {
						parsed.Market = "futures"
					}
					entry = parsed
				}
			}

			entries = append(entries, entry)
		}
	}

	return entries
}

// parseStrategyJSON reads and decodes a JSON strategy file.
func parseStrategyJSON(path string) (StrategyEntry, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return StrategyEntry{}, err
	}

	var entry StrategyEntry
	if err := json.Unmarshal(data, &entry); err != nil {
		return StrategyEntry{}, err
	}
	return entry, nil
}

// trimExtension removes the file extension from a filename.
func trimExtension(name string) string {
	ext := filepath.Ext(name)
	if ext == "" {
		return name
	}
	return name[:len(name)-len(ext)]
}

// ---------------------------------------------------------------------------
// Style helpers
// ---------------------------------------------------------------------------

// statusColor returns the lipgloss color for a strategy status.
func statusColor(status string) lipgloss.Color {
	switch strings.ToLower(status) {
	case "good":
		return styles.StatusOK
	case "prop_firm_ready":
		return styles.AccentGold
	case "under_review":
		return styles.StatusWarn
	case "rejected":
		return styles.StatusError
	default:
		return styles.TextMuted
	}
}

// statusDisplayName returns a human-friendly label for the status.
func statusDisplayName(status string) string {
	switch strings.ToLower(status) {
	case "good":
		return "GOOD"
	case "prop_firm_ready":
		return "PROP READY"
	case "under_review":
		return "REVIEW"
	case "rejected":
		return "REJECTED"
	default:
		return strings.ToUpper(status)
	}
}

// metricStyle returns a color-coded style based on value vs thresholds.
// For HighIsGood metrics (Sharpe, WinRate): below warn = warn, below crit = error.
// For LowIsGood metrics (MaxDD): above warn = warn, above crit = error.
func metricStyle(value, warn, critical float64, highIsGood bool) lipgloss.Style {
	color := styles.StatusOK
	if highIsGood {
		if value <= critical {
			color = styles.StatusError
		} else if value <= warn {
			color = styles.StatusWarn
		}
	} else {
		if value >= critical {
			color = styles.StatusError
		} else if value >= warn {
			color = styles.StatusWarn
		}
	}
	return lipgloss.NewStyle().Foreground(color).Bold(true)
}
