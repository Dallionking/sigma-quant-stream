#!/bin/bash
# =============================================================================
# Tmux Quant Team Launcher (Mission-Based Architecture)
# =============================================================================
# Creates a 4-pane tmux layout for the Quant Research Team.
# Each pane runs an infinite mission loop with Claude Code.
#
# Layout:
# ┌─────────┬─────────┐
# │ Pane 0  │ Pane 2  │
# │RESEARCH │BACKTEST │
# ├─────────┼─────────┤
# │ Pane 1  │ Pane 3  │
# │CONVERTER│OPTIMIZE │
# └─────────┴─────────┘
#
# Workers:
#   Pane 0 - Researcher: Hunt for trading edges, generate hypotheses
#   Pane 1 - Converter: PineScript → Python translation
#   Pane 2 - Backtester: Walk-forward validation, anti-overfit gates
#   Pane 3 - Optimizer: Parameter optimization, prop firm validation
#
# Usage: ./tmux-quant-launcher.sh [--mode=research|production]
#
# Modes:
#   research (default) - 30min timeout, sample data, $50 budget cap
#   production         - 60min timeout, Databento data, $100 budget cap
#
# Controls:
#   Ctrl-b d     - Detach (keeps running in background)
#   tmux attach -t quant-team  - Reattach
#   tmux kill-session -t quant-team  - Stop all
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STREAM_QUANT="$PROJECT_ROOT/stream-quant"
CHECKPOINT_DIR="$STREAM_QUANT/checkpoints"
SESSION="quant-team"

# Default mode
MODE="research"

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --mode=*)
            MODE="${arg#*=}"
            if [[ "$MODE" != "research" && "$MODE" != "production" ]]; then
                echo "Error: Invalid mode '$MODE'. Use 'research' or 'production'" >&2
                exit 1
            fi
            ;;
        -h|--help)
            # Will be handled below
            ;;
    esac
done

# Mode-specific configuration
case "$MODE" in
    research)
        SESSION_TIMEOUT=1800      # 30 minutes
        BUDGET_CAP=50             # $50 max
        DATA_SOURCE="sample"      # Use sample CSV files
        ;;
    production)
        SESSION_TIMEOUT=3600      # 60 minutes
        BUDGET_CAP=100            # $100 max
        DATA_SOURCE="databento"   # Use Databento API
        ;;
esac

# Worker configuration (fixed 4 workers)
WORKERS=("researcher" "converter" "backtester" "optimizer")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------
check_dependencies() {
    local missing=()

    if ! command -v tmux &> /dev/null; then
        missing+=("tmux")
    fi

    if ! command -v claude &> /dev/null; then
        missing+=("claude (Claude Code CLI)")
    fi

    if [[ ! -d "$STREAM_QUANT" ]]; then
        echo -e "${RED}stream-quant directory not found: $STREAM_QUANT${NC}" >&2
        exit 1
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo -e "${RED}Missing dependencies:${NC}" >&2
        for dep in "${missing[@]}"; do
            echo "  - $dep" >&2
        done
        exit 1
    fi
}

check_api_keys() {
    local missing_keys=()

    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        missing_keys+=("ANTHROPIC_API_KEY")
    fi

    if [[ "$MODE" == "production" ]]; then
        if [[ -z "${DATABENTO_API_KEY:-}" ]]; then
            missing_keys+=("DATABENTO_API_KEY (required for production mode)")
        fi
    fi

    # EXA_API_KEY is optional but recommended
    if [[ -z "${EXA_API_KEY:-}" ]]; then
        echo -e "${YELLOW}Warning: EXA_API_KEY not set - research capabilities may be limited${NC}"
    fi

    if [[ ${#missing_keys[@]} -gt 0 ]]; then
        echo -e "${RED}Missing required API keys:${NC}" >&2
        for key in "${missing_keys[@]}"; do
            echo "  - $key" >&2
        done
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Create Status Bar Script
# -----------------------------------------------------------------------------
create_status_script() {
    mkdir -p "$CHECKPOINT_DIR"

    cat > "$CHECKPOINT_DIR/tmux-status.sh" << 'STATUSEOF'
#!/bin/bash
# Reads status from all pane status files and formats for tmux status bar

CHECKPOINT_DIR="${1:-stream-quant/checkpoints}"
OUTPUT=""

# 4-pane layout: 0=Researcher, 1=Converter, 2=Backtester, 3=Optimizer
workers=("RES" "CNV" "BCK" "OPT")

for pane in 0 1 2 3; do
    status_file="$CHECKPOINT_DIR/pane-${pane}.status"
    if [[ -f "$status_file" ]]; then
        state=$(python3 -c "import json; d=json.load(open('$status_file')); print(d.get('state','?')[:6])" 2>/dev/null || echo "?")
        session=$(python3 -c "import json; d=json.load(open('$status_file')); print(d.get('session_number',0))" 2>/dev/null || echo "0")
        spent=$(python3 -c "import json; d=json.load(open('$status_file')); print(f\"{d.get('total_cost',0):.2f}\")" 2>/dev/null || echo "0.00")
        files=$(python3 -c "import json; d=json.load(open('$status_file')); print(d.get('files_created',0))" 2>/dev/null || echo "0")

        # Color based on state
        case "$state" in
            runnin*) color="#[fg=cyan]" ;;
            paused) color="#[fg=yellow]" ;;
            comple*) color="#[fg=green]" ;;
            failed) color="#[fg=red]" ;;
            budget) color="#[fg=magenta]" ;;
            *) color="#[fg=white]" ;;
        esac

        OUTPUT+=" ${color}${workers[$pane]}:S${session}/\$${spent}#[default]"
    else
        OUTPUT+=" #[fg=colour240]${workers[$pane]}:--#[default]"
    fi
done

# Calculate totals
total_spent=0
total_files=0
for pane in 0 1 2 3; do
    status_file="$CHECKPOINT_DIR/pane-${pane}.status"
    if [[ -f "$status_file" ]]; then
        s=$(python3 -c "import json; d=json.load(open('$status_file')); print(d.get('total_cost',0))" 2>/dev/null || echo "0")
        f=$(python3 -c "import json; d=json.load(open('$status_file')); print(d.get('files_created',0))" 2>/dev/null || echo "0")
        total_spent=$(python3 -c "print(${total_spent} + ${s})" 2>/dev/null || echo "$total_spent")
        total_files=$((total_files + f))
    fi
done

echo "#[fg=white,bold]🧪 QUANT#[default]$OUTPUT #[fg=green]📁$total_files#[default] #[fg=yellow]\$$(printf '%.2f' $total_spent)#[default]"
STATUSEOF

    chmod +x "$CHECKPOINT_DIR/tmux-status.sh"
    echo -e "${GREEN}✓ Created status bar script${NC}"
}

# -----------------------------------------------------------------------------
# Create Tmux Session with 4 Panes (2x2)
# -----------------------------------------------------------------------------
create_tmux_session() {
    echo -e "${BLUE}Creating tmux session: ${CYAN}$SESSION${NC}"

    # Kill existing session if any
    tmux kill-session -t "$SESSION" 2>/dev/null || true

    # Create new session (detached) with first pane
    tmux new-session -d -s "$SESSION" -c "$PROJECT_ROOT" -x 200 -y 50

    # Export API keys to tmux environment
    echo -e "${BLUE}Exporting API keys to tmux environment...${NC}"

    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        tmux set-environment -t "$SESSION" ANTHROPIC_API_KEY "$ANTHROPIC_API_KEY"
        echo -e "  ${GREEN}✓${NC} ANTHROPIC_API_KEY"
    fi

    if [[ -n "${DATABENTO_API_KEY:-}" ]]; then
        tmux set-environment -t "$SESSION" DATABENTO_API_KEY "$DATABENTO_API_KEY"
        echo -e "  ${GREEN}✓${NC} DATABENTO_API_KEY"
    fi

    if [[ -n "${EXA_API_KEY:-}" ]]; then
        tmux set-environment -t "$SESSION" EXA_API_KEY "$EXA_API_KEY"
        echo -e "  ${GREEN}✓${NC} EXA_API_KEY"
    fi

    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        tmux set-environment -t "$SESSION" OPENAI_API_KEY "$OPENAI_API_KEY"
        echo -e "  ${GREEN}✓${NC} OPENAI_API_KEY"
    fi

    if [[ -n "${PERPLEXITY_API_KEY:-}" ]]; then
        tmux set-environment -t "$SESSION" PERPLEXITY_API_KEY "$PERPLEXITY_API_KEY"
        echo -e "  ${GREEN}✓${NC} PERPLEXITY_API_KEY"
    fi

    # Export mode configuration
    tmux set-environment -t "$SESSION" QUANT_MODE "$MODE"
    tmux set-environment -t "$SESSION" QUANT_SESSION_TIMEOUT "$SESSION_TIMEOUT"
    tmux set-environment -t "$SESSION" QUANT_BUDGET_CAP "$BUDGET_CAP"
    tmux set-environment -t "$SESSION" QUANT_DATA_SOURCE "$DATA_SOURCE"
    echo -e "  ${GREEN}✓${NC} QUANT_MODE=$MODE"

    # Export market profile if set
    if [[ -n "${QUANT_PROFILE:-}" ]]; then
        tmux set-environment -t "$SESSION" QUANT_PROFILE "$QUANT_PROFILE"
        local profile_id
        profile_id=$(python3 -c "import json; print(json.load(open('$QUANT_PROFILE'))['profileId'])" 2>/dev/null || echo "unknown")
        echo -e "  ${GREEN}✓${NC} QUANT_PROFILE=$profile_id"
    fi

    # Name the window
    tmux rename-window -t "$SESSION:0" "quant-team"

    # Configure status bar with live updates
    tmux set-option -t "$SESSION" status on
    tmux set-option -t "$SESSION" status-interval 5
    tmux set-option -t "$SESSION" status-style "bg=colour235,fg=white"
    tmux set-option -t "$SESSION" status-left-length 60
    tmux set-option -t "$SESSION" status-right-length 140

    # Mode indicator in status
    local mode_color
    if [[ "$MODE" == "production" ]]; then
        mode_color="fg=red,bold"
    else
        mode_color="fg=cyan,bold"
    fi
    tmux set-option -t "$SESSION" status-left "#[${mode_color}] 🧪 QUANT [${MODE^^}] #[default]│ "
    tmux set-option -t "$SESSION" status-right "#($CHECKPOINT_DIR/tmux-status.sh $CHECKPOINT_DIR) │ %H:%M "

    # Pane border styling
    tmux set-option -t "$SESSION" pane-border-style "fg=colour240"
    tmux set-option -t "$SESSION" pane-active-border-style "fg=cyan,bold"
    tmux set-option -t "$SESSION" pane-border-status top
    tmux set-option -t "$SESSION" pane-border-format "#[fg=cyan,bold] 🧪 PANE #P #[fg=green,bold]#{pane_title} #[default]"

    # Create 2x2 grid layout
    # Start: 1 pane (pane 0)

    # Split horizontally to get 2 columns
    tmux split-window -h -t "$SESSION:0.0" -c "$PROJECT_ROOT"
    # Now: pane 0 | pane 1

    # Split each column vertically
    tmux split-window -v -t "$SESSION:0.0" -c "$PROJECT_ROOT"
    # Now: pane 0    | pane 2
    #      pane 1    |

    tmux split-window -v -t "$SESSION:0.2" -c "$PROJECT_ROOT"
    # Now: pane 0    | pane 2
    #      pane 1    | pane 3

    # Final layout (tiled makes it even 2x2):
    # ┌─────────┬─────────┐
    # │ Pane 0  │ Pane 2  │
    # │RESEARCH │BACKTEST │
    # ├─────────┼─────────┤
    # │ Pane 1  │ Pane 3  │
    # │CONVERTER│OPTIMIZE │
    # └─────────┴─────────┘
    tmux select-layout -t "$SESSION:0" tiled

    echo -e "${GREEN}✓ Created 4-pane 2x2 layout${NC}"
}

# -----------------------------------------------------------------------------
# Launch Ralph Loop in Each Pane
# -----------------------------------------------------------------------------
launch_workers() {
    echo -e "${BLUE}Launching workers (mode: ${CYAN}$MODE${BLUE})${NC}"

    # Pane mapping after splits (tiled layout):
    # 0=top-left (RESEARCHER), 1=bottom-left (CONVERTER)
    # 2=top-right (BACKTESTER), 3=bottom-right (OPTIMIZER)
    local pane_map=(0 1 2 3)
    local worker_titles=("RESEARCHER" "CONVERTER" "BACKTESTER" "OPTIMIZER")

    for i in {0..3}; do
        local worker="${WORKERS[$i]}"
        local pane="${pane_map[$i]}"
        local title="${worker_titles[$i]}"

        echo -e "  ${CYAN}Pane $pane${NC}: $title"

        # Set pane title for status bar display
        tmux select-pane -t "$SESSION:0.$pane" -T "$title"

        # Send command to the pane
        # Pass: pane_number worker_type
        # The ralph.sh script reads mode config from tmux environment
        tmux send-keys -t "$SESSION:0.$pane" \
            "cd '$PROJECT_ROOT' && '$SCRIPT_DIR/quant-ralph.sh' $pane $worker" Enter
    done

    echo -e "${GREEN}✓ All workers launched${NC}"
}

# -----------------------------------------------------------------------------
# Show Instructions
# -----------------------------------------------------------------------------
show_instructions() {
    echo ""
    echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║           🧪 QUANT TEAM LAUNCHED (Mission-Based)               ║${NC}"
    echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}Session:${NC} $SESSION"
    echo -e "${BOLD}Mode:${NC}    $MODE"
    echo ""
    echo -e "${BOLD}Configuration (${MODE}):${NC}"
    echo -e "  Session Timeout: ${CYAN}$SESSION_TIMEOUT${NC} seconds"
    echo -e "  Budget Cap:      ${CYAN}\$$BUDGET_CAP${NC}"
    echo -e "  Data Source:     ${CYAN}$DATA_SOURCE${NC}"
    echo ""
    echo -e "${BOLD}Layout (2x2):${NC}"
    echo -e "  ┌─────────┬─────────┐"
    echo -e "  │${CYAN} Pane 0 ${NC} │${CYAN} Pane 2 ${NC}│"
    echo -e "  │${GREEN}RESEARCH ${NC}│${GREEN}BACKTEST ${NC}│"
    echo -e "  ├─────────┼─────────┤"
    echo -e "  │${CYAN} Pane 1 ${NC} │${CYAN} Pane 3 ${NC}│"
    echo -e "  │${GREEN}CONVERTER${NC}│${GREEN}OPTIMIZE ${NC}│"
    echo -e "  └─────────┴─────────┘"
    echo ""
    echo -e "${BOLD}Inter-Agent Communication:${NC}"
    echo -e "  Researcher → ${MAGENTA}queues/hypotheses/${NC} → Backtester"
    echo -e "  Researcher → ${MAGENTA}queues/to-convert/${NC} → Converter"
    echo -e "  Converter  → ${MAGENTA}queues/to-backtest/${NC} → Backtester"
    echo -e "  Backtester → ${MAGENTA}queues/to-optimize/${NC} → Optimizer"
    echo ""
    echo -e "${BOLD}Tmux Controls:${NC}"
    echo -e "  ${CYAN}Ctrl-b d${NC}     - Detach (keeps running overnight)"
    echo -e "  ${CYAN}Ctrl-b [${NC}     - Scroll mode (q to exit)"
    echo -e "  ${CYAN}Ctrl-b arrow${NC} - Navigate between panes"
    echo -e "  ${CYAN}Ctrl-b z${NC}     - Zoom/unzoom current pane"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${CYAN}tmux attach -t $SESSION${NC}  - Reattach to session"
    echo -e "  ${CYAN}tmux kill-session -t $SESSION${NC}  - Stop all workers"
    echo ""
    echo -e "${YELLOW}Attaching to session in 2 seconds...${NC}"
    echo -e "${YELLOW}(Press Ctrl-C now to stay detached)${NC}"
    echo ""
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    echo ""
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║         🧪 TMUX QUANT TEAM LAUNCHER (Mission-Based)            ║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Pre-flight
    check_dependencies
    check_api_keys

    # Create status bar script
    create_status_script

    # Create session and panes
    create_tmux_session

    # Launch workers
    launch_workers

    # Show instructions
    show_instructions

    # Give user a moment to read, then attach
    sleep 2
    tmux attach -t "$SESSION"
}

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat << EOF
Tmux Quant Team Launcher (Mission-Based Architecture)

Usage: ./tmux-quant-launcher.sh [--mode=research|production]

Modes:
  research (default)  - 30min session timeout, sample data, \$50 budget cap
  production          - 60min session timeout, Databento data, \$100 budget cap

Layout (2x2):
  ┌─────────┬─────────┐
  │ Pane 0  │ Pane 2  │
  │RESEARCH │BACKTEST │
  ├─────────┼─────────┤
  │ Pane 1  │ Pane 3  │
  │CONVERTER│OPTIMIZE │
  └─────────┴─────────┘

Workers:
  Pane 0 - Researcher: Hunt for trading edges, generate hypotheses
  Pane 1 - Converter:  PineScript → Python translation
  Pane 2 - Backtester: Walk-forward validation, anti-overfit gates
  Pane 3 - Optimizer:  Parameter optimization, prop firm validation

Required Environment Variables:
  ANTHROPIC_API_KEY   - Required for Claude Code

Optional Environment Variables:
  DATABENTO_API_KEY   - Required for production mode
  EXA_API_KEY         - Recommended for research capabilities
  OPENAI_API_KEY      - Optional for additional LLM features
  PERPLEXITY_API_KEY  - Optional backup research

Inter-Agent Communication:
  Workers communicate via queue directories in stream-quant/queues/:
  - hypotheses/   : Researcher → Backtester
  - to-convert/   : Researcher → Converter
  - to-backtest/  : Converter → Backtester
  - to-optimize/  : Backtester → Optimizer

Shared Learning:
  Pattern files in stream-quant/patterns/ accumulate cross-session knowledge:
  - what-works.md       : Validated approaches
  - what-fails.md       : Documented failures
  - indicator-combos.md : Tested combinations
  - prop-firm-gotchas.md: Compliance issues

Examples:
  ./tmux-quant-launcher.sh                    # research mode (default)
  ./tmux-quant-launcher.sh --mode=research    # explicit research mode
  ./tmux-quant-launcher.sh --mode=production  # production mode

Tmux Controls:
  Ctrl-b d       - Detach (keeps running overnight)
  Ctrl-b [       - Scroll mode (q to exit)
  Ctrl-b arrow   - Navigate between panes
  Ctrl-b z       - Zoom/unzoom current pane

Status Bar:
  Shows real-time progress of all 4 panes:
  - RES:S#/\$X.XX - Researcher session count and spend
  - CNV:S#/\$X.XX - Converter session count and spend
  - BCK:S#/\$X.XX - Backtester session count and spend
  - OPT:S#/\$X.XX - Optimizer session count and spend
  - 📁N - Total files created
  - \$X.XX - Total spend across all workers

EOF
    exit 0
fi

main "$@"
