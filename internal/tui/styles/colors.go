package styles

import "github.com/charmbracelet/lipgloss"

// Gotham Night -- Dark Palette
// Deep midnight backgrounds with electric cyan accents.

var (
	// Backgrounds (darkest to lightest)
	BgDeep    = lipgloss.Color("#0a0e14") // Deepest -- main background
	BgPanel   = lipgloss.Color("#11151c") // Panel/card background
	BgSurface = lipgloss.Color("#1a1f2e") // Elevated surface
	BgHover   = lipgloss.Color("#232a3b") // Hover/selected row

	// Accents
	AccentPrimary   = lipgloss.Color("#4fc1ff") // Cyan -- primary actions, focused borders
	AccentSecondary = lipgloss.Color("#39c5bb") // Teal -- secondary info
	AccentTertiary  = lipgloss.Color("#7c3aed") // Purple -- special/premium
	AccentGold      = lipgloss.Color("#f5a623") // Gold -- profit, highlights

	// Status
	StatusOK    = lipgloss.Color("#22c55e") // Green
	StatusWarn  = lipgloss.Color("#f59e0b") // Amber
	StatusError = lipgloss.Color("#ef4444") // Red
	StatusInfo  = lipgloss.Color("#4fc1ff") // Cyan

	// Text
	TextPrimary   = lipgloss.Color("#e2e8f0") // High contrast
	TextSecondary = lipgloss.Color("#94a3b8") // Dimmed
	TextMuted     = lipgloss.Color("#64748b") // Very dim

	// Borders
	BorderNormal  = lipgloss.Color("#2d3748") // Subtle
	BorderFocused = lipgloss.Color("#4fc1ff") // Cyan focus ring
)
