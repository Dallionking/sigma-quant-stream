package styles

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// ---------------------------------------------------------------------------
// Panel styles
// ---------------------------------------------------------------------------

// Panel is the default panel style: BgPanel background, rounded border in
// BorderNormal, with 1-cell padding on all sides.
var Panel = lipgloss.NewStyle().
	Background(BgPanel).
	Border(RoundedBorder).
	BorderForeground(BorderNormal).
	Padding(1)

// PanelFocused is identical to Panel but uses the cyan focus border.
var PanelFocused = lipgloss.NewStyle().
	Background(BgPanel).
	Border(RoundedBorder).
	BorderForeground(BorderFocused).
	Padding(1)

// Card is a compact elevated surface with a thin border and horizontal
// padding only.
var Card = lipgloss.NewStyle().
	Background(BgSurface).
	Border(ThinBorder).
	BorderForeground(BorderNormal).
	PaddingLeft(1).
	PaddingRight(1)

// ---------------------------------------------------------------------------
// Header / Footer
// ---------------------------------------------------------------------------

// Header spans the full width with bold cyan text on the deepest background.
var Header = lipgloss.NewStyle().
	Background(BgDeep).
	Foreground(AccentPrimary).
	Bold(true).
	Width(80).
	PaddingLeft(1).
	PaddingRight(1)

// Footer spans the full width with muted text on the deepest background.
var Footer = lipgloss.NewStyle().
	Background(BgDeep).
	Foreground(TextMuted).
	Width(80).
	PaddingLeft(1).
	PaddingRight(1)

// ---------------------------------------------------------------------------
// Badge helpers
// ---------------------------------------------------------------------------

// Badge returns an inline colored badge such as "● RUNNING" in the given
// color.
func Badge(text string, color lipgloss.Color) string {
	dot := lipgloss.NewStyle().Foreground(color).Render("●")
	label := lipgloss.NewStyle().
		Foreground(color).
		Bold(true).
		Render(text)
	return dot + " " + label
}

// StatusBadge returns a pre-styled badge for common status values.
// Recognized statuses: "ok", "warn", "error", "info". Anything else
// falls back to the "info" style.
func StatusBadge(status string) string {
	switch strings.ToLower(status) {
	case "ok":
		return Badge("OK", StatusOK)
	case "warn":
		return Badge("WARN", StatusWarn)
	case "error":
		return Badge("ERROR", StatusError)
	case "info":
		return Badge("INFO", StatusInfo)
	default:
		return Badge(strings.ToUpper(status), StatusInfo)
	}
}

// ---------------------------------------------------------------------------
// Typography styles
// ---------------------------------------------------------------------------

// Title is bold AccentPrimary text for section headings.
var Title = lipgloss.NewStyle().
	Foreground(AccentPrimary).
	Bold(true)

// Subtitle is regular TextSecondary text for secondary headings.
var Subtitle = lipgloss.NewStyle().
	Foreground(TextSecondary)

// Label is TextMuted text for field labels. Pass uppercase strings for the
// conventional LABEL look (lipgloss does not provide an uppercase transform).
var Label = lipgloss.NewStyle().
	Foreground(TextMuted)

// Value is bold TextPrimary text for data values.
var Value = lipgloss.NewStyle().
	Foreground(TextPrimary).
	Bold(true)

// ProfitText is bold green for positive P&L.
var ProfitText = lipgloss.NewStyle().
	Foreground(StatusOK).
	Bold(true)

// LossText is bold red for negative P&L.
var LossText = lipgloss.NewStyle().
	Foreground(StatusError).
	Bold(true)

// ---------------------------------------------------------------------------
// Table helpers
// ---------------------------------------------------------------------------

// TableHeader is bold, underlined, TextSecondary for column headings.
var TableHeader = lipgloss.NewStyle().
	Foreground(TextSecondary).
	Bold(true).
	Underline(true)

// TableRow returns a style for a table row. Pass an even (true) or odd
// (false) flag to get alternating zebra-stripe backgrounds.
func TableRow(even bool) lipgloss.Style {
	bg := BgPanel
	if !even {
		bg = BgSurface
	}
	return lipgloss.NewStyle().
		Foreground(TextPrimary).
		Background(bg)
}

// ---------------------------------------------------------------------------
// Divider
// ---------------------------------------------------------------------------

// Divider returns a horizontal rule of the given width using the ─ character
// rendered in BorderNormal color.
func Divider(width int) string {
	if width <= 0 {
		return ""
	}
	line := strings.Repeat("─", width)
	return lipgloss.NewStyle().Foreground(BorderNormal).Render(line)
}
