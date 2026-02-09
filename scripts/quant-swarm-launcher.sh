#!/bin/bash
# =============================================================================
# Quant Swarm Launcher - Launch 4 Workers with Swarm Mode
# =============================================================================
# Spawns all 4 quant workers (researcher, converter, backtester, optimizer)
# in a tmux session with swarm mode enabled.
#
# Usage: ./quant-swarm-launcher.sh [mode]
#   mode: research (default) | production
#
# Example: ./quant-swarm-launcher.sh production
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

MODE="${1:-research}"
SESSION="quant-swarm"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  🐝 ${BOLD}QUANT SWARM LAUNCHER${NC}                                      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${MAGENTA}35 Sub-Agents • 4 Workers • Autonomous Research${NC}            ${CYAN}║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  Mode: ${BOLD}$MODE${NC}                                                   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Session: ${BOLD}$SESSION${NC}                                            ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if tmux session already exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo -e "${YELLOW}Warning: Session '$SESSION' already exists.${NC}"
    read -p "Kill existing session and restart? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        tmux kill-session -t "$SESSION"
        echo -e "${GREEN}Killed existing session.${NC}"
    else
        echo -e "${BLUE}Attaching to existing session...${NC}"
        tmux attach -t "$SESSION"
        exit 0
    fi
fi

# Create new tmux session with 4 panes
echo -e "${BLUE}Creating tmux session with 4 workers...${NC}"

# Create session with first pane (researcher)
tmux new-session -d -s "$SESSION" -x 200 -y 50

# Set up pane titles and colors
tmux select-pane -t "$SESSION:0" -T "Researcher"

# Split horizontally for converter (right)
tmux split-window -h -t "$SESSION:0"
tmux select-pane -t "$SESSION:0.1" -T "Converter"

# Split pane 0 vertically for backtester (bottom-left)
tmux split-window -v -t "$SESSION:0.0"
tmux select-pane -t "$SESSION:0.2" -T "Backtester"

# Split pane 1 vertically for optimizer (bottom-right)
tmux split-window -v -t "$SESSION:0.1"
tmux select-pane -t "$SESSION:0.3" -T "Optimizer"

# Change to project directory in all panes
tmux send-keys -t "$SESSION:0.0" "cd '$PROJECT_ROOT/scripts/quant-team'" Enter
tmux send-keys -t "$SESSION:0.1" "cd '$PROJECT_ROOT/scripts/quant-team'" Enter
tmux send-keys -t "$SESSION:0.2" "cd '$PROJECT_ROOT/scripts/quant-team'" Enter
tmux send-keys -t "$SESSION:0.3" "cd '$PROJECT_ROOT/scripts/quant-team'" Enter

# Small delay for cd to complete
sleep 0.5

# Launch workers with swarm mode
echo -e "${GREEN}Launching workers with swarm mode...${NC}"

# Pane 0: Researcher (top-left)
tmux send-keys -t "$SESSION:0.0" \
    "./quant-ralph.sh 0 researcher $MODE --swarm-mode" Enter

# Pane 1: Converter (top-right)
tmux send-keys -t "$SESSION:0.1" \
    "./quant-ralph.sh 1 converter $MODE --swarm-mode" Enter

# Pane 2: Backtester (bottom-left)
tmux send-keys -t "$SESSION:0.2" \
    "./quant-ralph.sh 2 backtester $MODE --swarm-mode" Enter

# Pane 3: Optimizer (bottom-right)
tmux send-keys -t "$SESSION:0.3" \
    "./quant-ralph.sh 3 optimizer $MODE --swarm-mode" Enter

# Configure tmux settings for the session
tmux set-option -t "$SESSION" -g mouse on
tmux set-option -t "$SESSION" -g status-style "bg=blue,fg=white"
tmux set-option -t "$SESSION" -g status-left "#[fg=yellow,bold][QUANT SWARM] "
tmux set-option -t "$SESSION" -g status-right "#[fg=cyan]%H:%M:%S"
tmux set-option -t "$SESSION" -g status-interval 1

# Set pane border style
tmux set-option -t "$SESSION" pane-border-style "fg=blue"
tmux set-option -t "$SESSION" pane-active-border-style "fg=green,bold"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ✅ ${BOLD}SWARM LAUNCHED SUCCESSFULLY${NC}                               ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Workers Running:${NC}                                              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  • Pane 0: Researcher  (8 sub-agents)                         ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  • Pane 1: Converter   (7 sub-agents)                         ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  • Pane 2: Backtester  (10 sub-agents)                        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  • Pane 3: Optimizer   (10 sub-agents)                        ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Commands:${NC}                                                     ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  • tmux attach -t $SESSION                                   ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  • ./quant-control.sh status                                  ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  • ./quant-control.sh pause                                   ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Ask to attach
read -p "Attach to session now? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    tmux attach -t "$SESSION"
fi
