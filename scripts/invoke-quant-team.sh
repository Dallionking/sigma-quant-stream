#!/bin/bash
# =============================================================================
# Quant Team Invoker
# =============================================================================
# Simple entry point for @quant-team Cursor command.
# Parses arguments and launches the appropriate configuration.
#
# Usage: ./invoke-quant-team.sh [preset|iterations|command]
#
# Examples:
#   ./invoke-quant-team.sh                 # Default launch
#   ./invoke-quant-team.sh research        # Research-heavy preset
#   ./invoke-quant-team.sh 100             # 100 iterations
#   ./invoke-quant-team.sh status          # Check status
#   ./invoke-quant-team.sh stop            # Stop team
#   ./invoke-quant-team.sh research 150    # Research-heavy, 150 iterations
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults
PRESET="balanced"
ITERATIONS="50"
BUDGET="unlimited"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# -----------------------------------------------------------------------------
# Status Command
# -----------------------------------------------------------------------------
show_status() {
    echo ""
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║             🧪 QUANT TEAM STATUS                               ║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Check if tmux session exists
    if tmux has-session -t quant-team 2>/dev/null; then
        echo -e "${GREEN}✓ Team is RUNNING${NC}"
        echo ""
        
        # Show pane status
        local checkpoint_dir="$SCRIPT_DIR/../../stream-quant/checkpoints"
        if [[ -d "$checkpoint_dir" ]]; then
            echo -e "${BOLD}Pane Status:${NC}"
            for pane in 1 2 3 4 5 6; do
                local status_file="$checkpoint_dir/pane-${pane}.status"
                if [[ -f "$status_file" ]]; then
                    local worker=$(python3 -c "import json; print(json.load(open('$status_file')).get('worker','?'))" 2>/dev/null || echo "?")
                    local step=$(python3 -c "import json; print(json.load(open('$status_file')).get('step','?'))" 2>/dev/null || echo "?")
                    local iter=$(python3 -c "import json; print(json.load(open('$status_file')).get('iteration',0))" 2>/dev/null || echo "0")
                    local completed=$(python3 -c "import json; print(json.load(open('$status_file')).get('completed',0))" 2>/dev/null || echo "0")
                    echo -e "  Pane $pane: ${CYAN}$worker${NC} - $step (iter $iter, ${GREEN}$completed done${NC})"
                fi
            done
        fi
        
        echo ""
        echo -e "${BOLD}Commands:${NC}"
        echo -e "  ${CYAN}tmux attach -t quant-team${NC}  - Reattach to view"
        echo -e "  ${CYAN}@quant-team stop${NC}           - Stop the team"
    else
        echo -e "${YELLOW}✗ Team is NOT running${NC}"
        echo ""
        echo -e "Start with: ${CYAN}@quant-team${NC}"
    fi
    echo ""
}

# -----------------------------------------------------------------------------
# Stop Command
# -----------------------------------------------------------------------------
stop_team() {
    echo ""
    if tmux has-session -t quant-team 2>/dev/null; then
        tmux kill-session -t quant-team
        echo -e "${GREEN}✓ Quant team stopped${NC}"
    else
        echo -e "${YELLOW}No quant team session found${NC}"
    fi
    echo ""
}

# -----------------------------------------------------------------------------
# Results Command
# -----------------------------------------------------------------------------
show_results() {
    local output_dir="$SCRIPT_DIR/../../stream-quant/output"
    
    echo ""
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║             🧪 QUANT TEAM RESULTS                              ║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${BOLD}Good Strategies:${NC}"
    if [[ -d "$output_dir/strategies/good" ]]; then
        ls -la "$output_dir/strategies/good/" 2>/dev/null | tail -10 || echo "  (none yet)"
    else
        echo "  (directory not found)"
    fi
    
    echo ""
    echo -e "${BOLD}Prop Firm Ready:${NC}"
    if [[ -d "$output_dir/strategies/prop_firm_ready" ]]; then
        ls -la "$output_dir/strategies/prop_firm_ready/" 2>/dev/null | tail -10 || echo "  (none yet)"
    else
        echo "  (directory not found)"
    fi
    
    echo ""
    echo -e "${BOLD}Recent Research:${NC}"
    if [[ -d "$output_dir/research-logs" ]]; then
        find "$output_dir/research-logs" -type f -name "*.md" -mtime -1 2>/dev/null | head -5 || echo "  (none in last 24h)"
    else
        echo "  (directory not found)"
    fi
    echo ""
}

# -----------------------------------------------------------------------------
# Parse Arguments
# -----------------------------------------------------------------------------
parse_args() {
    for arg in "$@"; do
        case "$arg" in
            # Presets
            research|research_heavy|research-heavy)
                PRESET="research_heavy"
                ;;
            backtest|backtest_heavy|backtest-heavy)
                PRESET="backtest_heavy"
                ;;
            full|full_cycle|full-cycle)
                PRESET="full_cycle"
                ;;
            balanced)
                PRESET="balanced"
                ;;
            # Commands
            status|--status|-s)
                show_status
                exit 0
                ;;
            stop|--stop|kill)
                stop_team
                exit 0
                ;;
            results|--results|-r)
                show_results
                exit 0
                ;;
            help|--help|-h)
                cat << EOF
Quant Team Invoker

Usage: @quant-team [preset] [iterations] [command]

Presets:
  balanced       One of each worker (default)
  research       Focus on research (2 researchers)
  backtest       Focus on backtesting (2 backtesters, 2 optimizers)
  full           Full pipeline focus (2 backtesters)

Commands:
  status         Check if team is running
  stop           Stop the team
  results        View latest results

Examples:
  @quant-team                    # Default launch
  @quant-team research           # Research-heavy
  @quant-team 100                # 100 iterations
  @quant-team research 100       # Research-heavy, 100 iterations
  @quant-team status             # Check status
  @quant-team stop               # Stop team

EOF
                exit 0
                ;;
            # Iterations (numeric)
            [0-9]*)
                ITERATIONS="$arg"
                ;;
            *)
                echo -e "${YELLOW}Unknown argument: $arg${NC}" >&2
                ;;
        esac
    done
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    parse_args "$@"
    
    echo ""
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║             🧪 LAUNCHING QUANT TEAM                            ║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Preset:${NC}     ${CYAN}$PRESET${NC}"
    echo -e "  ${BOLD}Iterations:${NC} ${CYAN}$ITERATIONS${NC}"
    echo -e "  ${BOLD}Budget:${NC}     ${GREEN}$BUDGET${NC}"
    echo ""
    echo -e "${YELLOW}Launching in iTerm...${NC}"
    echo ""
    
    # Launch the team in iTerm (opens new iTerm window with tmux)
    "$SCRIPT_DIR/iterm-tmux-launcher.sh" "$PRESET" "$ITERATIONS"
}

main "$@"
