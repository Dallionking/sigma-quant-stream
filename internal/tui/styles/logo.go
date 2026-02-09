package styles

import "github.com/charmbracelet/lipgloss"

// logoRaw is the ASCII art used on the splash screen.
const logoRaw = `
  ███████╗██╗ ██████╗ ███╗   ███╗ █████╗
  ██╔════╝██║██╔════╝ ████╗ ████║██╔══██╗
  ███████╗██║██║  ███╗██╔████╔██║███████║
  ╚════██║██║██║   ██║██║╚██╔╝██║██╔══██║
  ███████║██║╚██████╔╝██║ ╚═╝ ██║██║  ██║
  ╚══════╝╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝
       Q U A N T   S T R E A M`

// CompactLogo is the single-line logo for headers and narrow spaces.
const CompactLogo = "⚡ SIGMA-QUANT"

// Logo returns the full ASCII art logo rendered in AccentPrimary on a
// BgPanel background panel.
func Logo() string {
	return lipgloss.NewStyle().
		Foreground(AccentPrimary).
		Background(BgPanel).
		Padding(1, 2).
		Render(logoRaw)
}
