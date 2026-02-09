package styles

import "github.com/charmbracelet/lipgloss"

// RoundedBorder uses rounded corners for general panels.
var RoundedBorder = lipgloss.Border{
	Top:         "─",
	Bottom:      "─",
	Left:        "│",
	Right:       "│",
	TopLeft:     "╭",
	TopRight:    "╮",
	BottomLeft:  "╰",
	BottomRight: "╯",
}

// DoubleBorder uses double-line characters for focused or important panels.
var DoubleBorder = lipgloss.Border{
	Top:         "═",
	Bottom:      "═",
	Left:        "║",
	Right:       "║",
	TopLeft:     "╔",
	TopRight:    "╗",
	BottomLeft:  "╚",
	BottomRight: "╝",
}

// ThinBorder uses standard single-line characters.
var ThinBorder = lipgloss.Border{
	Top:         "─",
	Bottom:      "─",
	Left:        "│",
	Right:       "│",
	TopLeft:     "┌",
	TopRight:    "┐",
	BottomLeft:  "└",
	BottomRight: "┘",
}
