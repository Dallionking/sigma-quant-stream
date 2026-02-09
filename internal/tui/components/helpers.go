package components

import "strings"

// splitLines splits a rendered string on newlines.
func splitLines(s string) []string {
	return strings.Split(s, "\n")
}

// joinLines joins lines back with newlines.
func joinLines(lines []string) string {
	return strings.Join(lines, "\n")
}
