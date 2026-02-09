package styles

import (
	"math"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// ---------------------------------------------------------------------------
// Convenience color helpers
// ---------------------------------------------------------------------------

// Cyan renders s in AccentPrimary (electric cyan).
func Cyan(s string) string {
	return lipgloss.NewStyle().Foreground(AccentPrimary).Render(s)
}

// Gold renders s in AccentGold.
func Gold(s string) string {
	return lipgloss.NewStyle().Foreground(AccentGold).Render(s)
}

// Green renders s in StatusOK.
func Green(s string) string {
	return lipgloss.NewStyle().Foreground(StatusOK).Render(s)
}

// Red renders s in StatusError.
func Red(s string) string {
	return lipgloss.NewStyle().Foreground(StatusError).Render(s)
}

// Dim renders s in TextMuted.
func Dim(s string) string {
	return lipgloss.NewStyle().Foreground(TextMuted).Render(s)
}

// Bold renders s in bold TextPrimary.
func Bold(s string) string {
	return lipgloss.NewStyle().Bold(true).Foreground(TextPrimary).Render(s)
}

// ---------------------------------------------------------------------------
// Sparkline
// ---------------------------------------------------------------------------

// brailleRamp maps normalized 0..7 buckets to braille bar characters.
var brailleRamp = []rune{'⡀', '⡄', '⡆', '⡇', '⣇', '⣧', '⣷', '⣿'}

// Sparkline produces a compact braille bar chart that fits in width columns.
// If values is empty or width is <= 0 an empty string is returned.
func Sparkline(values []float64, width int) string {
	if len(values) == 0 || width <= 0 {
		return ""
	}

	// Resample values to requested width using nearest-neighbour.
	sampled := make([]float64, width)
	for i := range width {
		idx := i * len(values) / width
		if idx >= len(values) {
			idx = len(values) - 1
		}
		sampled[i] = values[idx]
	}

	// Find min/max for normalization.
	lo, hi := sampled[0], sampled[0]
	for _, v := range sampled {
		if v < lo {
			lo = v
		}
		if v > hi {
			hi = v
		}
	}

	span := hi - lo
	if span == 0 {
		span = 1 // avoid division by zero; all values identical
	}

	var b strings.Builder
	b.Grow(width * 4) // braille chars can be multi-byte
	for _, v := range sampled {
		norm := (v - lo) / span                         // 0..1
		bucket := int(math.Round(norm * float64(len(brailleRamp)-1)))
		if bucket < 0 {
			bucket = 0
		}
		if bucket >= len(brailleRamp) {
			bucket = len(brailleRamp) - 1
		}
		b.WriteRune(brailleRamp[bucket])
	}

	return lipgloss.NewStyle().Foreground(AccentPrimary).Render(b.String())
}

// ---------------------------------------------------------------------------
// Text utilities
// ---------------------------------------------------------------------------

// TruncateWithEllipsis shortens s to max runes, appending "..." when
// truncation occurs. If max is less than 4 the string is simply cut.
func TruncateWithEllipsis(s string, max int) string {
	runes := []rune(s)
	if len(runes) <= max {
		return s
	}
	if max < 4 {
		return string(runes[:max])
	}
	return string(runes[:max-3]) + "..."
}
