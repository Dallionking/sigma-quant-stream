#!/bin/bash
# =============================================================================
# iTerm + Tmux Quant Team Launcher
# =============================================================================
# Opens iTerm and launches the tmux quant team session inside it.
# This ensures the visual tmux panes appear in iTerm, not Cursor.
#
# Usage: ./iterm-tmux-launcher.sh [preset] [max_iterations]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PRESET="${1:-balanced}"
MAX_ITERATIONS="${2:-50}"
RETRY_DELAY="${3:-5}"
MAX_RETRIES="${4:-3}"

# The command to run inside iTerm
TMUX_CMD="cd '$PROJECT_ROOT' && ./scripts/quant-team/tmux-quant-launcher.sh '$PRESET' '$MAX_ITERATIONS' '$RETRY_DELAY' '$MAX_RETRIES'"

echo "🚀 Opening iTerm and launching Quant Team..."
echo "   Preset: $PRESET"
echo "   Iterations: $MAX_ITERATIONS"
echo ""

# Use AppleScript to open iTerm and run the tmux launcher
osascript << EOF
tell application "iTerm"
    activate
    
    -- Create a new window
    create window with default profile
    
    tell current session of current window
        write text "$TMUX_CMD"
    end tell
end tell
EOF

echo "✅ Quant team launched in iTerm!"
echo ""
echo "The tmux session is now running in iTerm."
echo "Look for the new iTerm window with 6 panes."
echo ""
echo "Controls:"
echo "  Ctrl-b d     - Detach (keeps running overnight)"
echo "  Ctrl-b z     - Zoom current pane"
echo "  Ctrl-b arrow - Navigate between panes"
echo ""
echo "To reattach later: tmux attach -t quant-team"
