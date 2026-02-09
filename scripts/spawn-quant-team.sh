#!/bin/bash
# =============================================================================
# Spawn Quant Research Team
# =============================================================================
# Main entry point for launching the autonomous Quant Research Team.
# Creates 6 iTerm2 panes, each running a Claude Code instance with Ralph Loop.
#
# Usage:
#   ./spawn-quant-team.sh [preset] [max_iterations] [budget]
#
# Examples:
#   ./spawn-quant-team.sh                      # balanced, 50 iterations, $15
#   ./spawn-quant-team.sh research_heavy 100   # research focus, 100 iterations
#   ./spawn-quant-team.sh full_cycle 75 25     # full cycle, 75 iterations, $25
#
# Presets:
#   balanced       - One of each worker type
#   research_heavy - Extra researchers
#   backtest_heavy - Extra backtesters + optimizers
#   full_cycle     - Balanced with extra backtesters
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STREAM_QUANT="$PROJECT_ROOT/stream-quant"

# Arguments (positional for backwards compatibility)
PRESET="${1:-balanced}"
MAX_ITERATIONS="${2:-50}"
DAILY_BUDGET="${3:-unlimited}"  # Set to "unlimited" for Claude Max users, or a number like "15.00"
NOTIFY_METHOD="${4:-elevenlabs}"  # elevenlabs, say, none
USE_TMUX=true  # Default to tmux for visible output; use --iterm to switch
QUANT_PROFILE=""  # Market profile name (e.g., futures, crypto-cex, crypto-dex-hyperliquid)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------
validate_preset() {
    case "$PRESET" in
        balanced|research_heavy|backtest_heavy|full_cycle)
            return 0
            ;;
        *)
            echo -e "${RED}Invalid preset: $PRESET${NC}"
            echo "Valid presets: balanced, research_heavy, backtest_heavy, full_cycle"
            exit 1
            ;;
    esac
}

check_dependencies() {
    local missing=()

    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    fi

    # Check for Claude Code CLI
    if ! command -v claude &> /dev/null; then
        missing+=("claude (Claude Code CLI)")
    fi

    # Check launcher-specific dependencies
    if [[ "$USE_TMUX" == "true" ]]; then
        # Check for tmux
        if ! command -v tmux &> /dev/null; then
            missing+=("tmux (install with: brew install tmux)")
        fi
    else
        # Check for Node.js (needed for iTerm launcher)
        if ! command -v node &> /dev/null; then
            missing+=("node")
        fi
        # Check for iTerm
        if ! osascript -e 'tell application "System Events" to (name of processes) contains "iTerm2"' &> /dev/null; then
            # iTerm may not be running, but should be installed
            if [[ ! -d "/Applications/iTerm.app" ]]; then
                missing+=("iTerm2")
            fi
        fi
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo -e "${RED}Missing dependencies:${NC}"
        for dep in "${missing[@]}"; do
            echo "  - $dep"
        done
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
resolve_profile() {
    echo -e "${BLUE}Resolving market profile...${NC}"

    local profiles_dir="$STREAM_QUANT/profiles"
    local active_profile="$profiles_dir/active-profile.json"

    # If --profile was specified, resolve it
    if [[ -n "$QUANT_PROFILE" ]]; then
        local profile_path="$profiles_dir/${QUANT_PROFILE}.json"
        if [[ ! -f "$profile_path" ]]; then
            echo -e "${RED}Profile not found: $profile_path${NC}"
            echo -e "Available profiles:"
            ls -1 "$profiles_dir"/*.json 2>/dev/null | while read -r f; do
                local name
                name=$(basename "$f" .json)
                [[ "$name" == "active-profile" ]] && continue
                local display
                display=$(python3 -c "import json; print(json.load(open('$f'))['displayName'])" 2>/dev/null || echo "$name")
                echo -e "  ${CYAN}$name${NC} — $display"
            done
            exit 1
        fi
        # Copy selected profile as active
        cp "$profile_path" "$active_profile"
        echo -e "${GREEN}✓ Profile set: $QUANT_PROFILE${NC}"
        export QUANT_PROFILE="$active_profile"
        return 0
    fi

    # If active-profile.json exists, use it
    if [[ -f "$active_profile" ]]; then
        local current_id
        current_id=$(python3 -c "import json; print(json.load(open('$active_profile'))['profileId'])" 2>/dev/null || echo "unknown")
        echo -e "${GREEN}✓ Using active profile: ${CYAN}$current_id${NC}"
        export QUANT_PROFILE="$active_profile"
        return 0
    fi

    # No profile set — run interactive setup wizard
    echo -e "${YELLOW}No active profile found. Running setup wizard...${NC}"
    echo ""
    echo -e "${BOLD}Select a market profile:${NC}"

    local profiles=()
    local idx=1
    for f in "$profiles_dir"/*.json; do
        local name
        name=$(basename "$f" .json)
        [[ "$name" == "active-profile" ]] && continue
        local display
        display=$(python3 -c "import json; print(json.load(open('$f'))['displayName'])" 2>/dev/null || echo "$name")
        echo -e "  ${CYAN}[$idx]${NC} $name — $display"
        profiles+=("$f")
        ((idx++))
    done

    if [[ ${#profiles[@]} -eq 0 ]]; then
        echo -e "${RED}No profile files found in $profiles_dir${NC}"
        echo -e "Create one from the templates or run the setup wizard: python3 scripts/quant-team/setup-wizard.py"
        exit 1
    fi

    echo ""
    read -rp "  Enter number [1]: " choice
    choice="${choice:-1}"

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [[ "$choice" -lt 1 ]] || [[ "$choice" -gt ${#profiles[@]} ]]; then
        echo -e "${RED}Invalid selection${NC}"
        exit 1
    fi

    local selected="${profiles[$((choice-1))]}"
    cp "$selected" "$active_profile"
    local selected_id
    selected_id=$(python3 -c "import json; print(json.load(open('$active_profile'))['profileId'])" 2>/dev/null)
    echo -e "${GREEN}✓ Active profile set: ${CYAN}$selected_id${NC}"
    export QUANT_PROFILE="$active_profile"
}

setup_directories() {
    echo -e "${BLUE}Setting up directories...${NC}"

    mkdir -p "$STREAM_QUANT/backlog"
    mkdir -p "$STREAM_QUANT/output/strategies/good"
    mkdir -p "$STREAM_QUANT/output/strategies/rejected"
    mkdir -p "$STREAM_QUANT/output/strategies/prop_firm_ready"
    mkdir -p "$STREAM_QUANT/output/indicators/created"
    mkdir -p "$STREAM_QUANT/output/indicators/converted"
    mkdir -p "$STREAM_QUANT/output/backtests"
    mkdir -p "$STREAM_QUANT/output/research-logs/daily"
    mkdir -p "$STREAM_QUANT/output/research-logs/patterns"
    mkdir -p "$STREAM_QUANT/checkpoints"

    echo -e "${GREEN}✓ Directories ready${NC}"
}

setup_budget() {
    if [[ "$DAILY_BUDGET" == "unlimited" ]]; then
        echo -e "${BLUE}Budget: ${GREEN}UNLIMITED${NC} (Claude Max subscription)"
        # Set a very high budget to effectively disable tracking
        python3 "$SCRIPT_DIR/cost-tracker.py" --set-budget="999999" --unlimited 2>/dev/null || true
        echo -e "${GREEN}✓ Budget tracking disabled${NC}"
    else
        echo -e "${BLUE}Setting daily budget: \$$DAILY_BUDGET${NC}"
        python3 "$SCRIPT_DIR/cost-tracker.py" --set-budget="$DAILY_BUDGET" 2>/dev/null || true
        echo -e "${GREEN}✓ Budget configured${NC}"
    fi
}

reset_claimed_ideas() {
    echo -e "${BLUE}Resetting claimed ideas registry...${NC}"

    local claimed_file="$STREAM_QUANT/claimed-ideas.json"

    if [[ -f "$claimed_file" ]]; then
        # Archive old claims
        local archive_dir="$STREAM_QUANT/.archives"
        mkdir -p "$archive_dir"
        cp "$claimed_file" "$archive_dir/claimed-ideas-$(date +%Y%m%d-%H%M%S).json"
    fi

    # Create fresh registry
    echo '{"ideas": [], "last_updated": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}' > "$claimed_file"

    echo -e "${GREEN}✓ Claimed ideas registry reset${NC}"
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------
preflight_checks() {
    echo -e "\n${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║             🧪 QUANT RESEARCH TEAM PRE-FLIGHT                  ║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

    echo -e "${BOLD}Configuration:${NC}"
    echo -e "  Preset:         ${CYAN}$PRESET${NC}"
    echo -e "  Max Iterations: ${CYAN}$MAX_ITERATIONS${NC}"
    if [[ "$DAILY_BUDGET" == "unlimited" ]]; then
        echo -e "  Daily Budget:   ${GREEN}UNLIMITED (Claude Max)${NC}"
    else
        echo -e "  Daily Budget:   ${CYAN}\$$DAILY_BUDGET${NC}"
    fi
    echo -e "  Profile:        ${CYAN}${QUANT_PROFILE:-auto-detect}${NC}"
    if [[ "$USE_TMUX" == "true" ]]; then
        echo -e "  Launcher:       ${GREEN}tmux (visible 6-pane layout)${NC}"
    else
        echo -e "  Launcher:       ${CYAN}iTerm AppleScript${NC}"
    fi
    echo -e "  Notifications:  ${CYAN}$NOTIFY_METHOD${NC}"
    echo -e "  Project Root:   ${CYAN}$PROJECT_ROOT${NC}"
    echo ""

    echo -e "${BOLD}Pre-flight Checks:${NC}"

    # Validate preset
    echo -n "  Preset valid... "
    validate_preset && echo -e "${GREEN}✓${NC}"

    # Check dependencies
    echo -n "  Dependencies... "
    check_dependencies && echo -e "${GREEN}✓${NC}"

    # Check if already running
    echo -n "  Not already running... "
    local already_running=false
    
    # Check for existing tmux session
    if tmux has-session -t quant-team 2>/dev/null; then
        already_running=true
        echo -e "${YELLOW}⚠ tmux session 'quant-team' already exists${NC}"
    # Check for quant-ralph processes
    elif pgrep -f "quant-ralph.sh" > /dev/null 2>&1; then
        already_running=true
        echo -e "${YELLOW}⚠ quant-ralph.sh processes detected${NC}"
    fi
    
    if [[ "$already_running" == "true" ]]; then
        read -rp "  Continue anyway? [y/N] " response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "Aborting."
            echo -e "  ${CYAN}Tip: tmux attach -t quant-team${NC} to reattach to existing session"
            exit 0
        fi
    else
        echo -e "${GREEN}✓${NC}"
    fi

    echo ""
}

# -----------------------------------------------------------------------------
# Launch
# -----------------------------------------------------------------------------
launch_team() {
    echo -e "${BOLD}Launching Quant Research Team...${NC}\n"

    # Setup
    resolve_profile
    setup_directories
    setup_budget
    reset_claimed_ideas

    echo ""

    # Launch via tmux (default) or iTerm
    if [[ "$USE_TMUX" == "true" ]]; then
        echo -e "${BLUE}Using tmux for visible Claude output...${NC}"
        # tmux launcher will attach to session, so we exit after
        QUANT_PROFILE="$QUANT_PROFILE" "$SCRIPT_DIR/tmux-quant-launcher.sh" "$PRESET" "$MAX_ITERATIONS"
        # If we get here, user detached from tmux
        echo ""
        echo -e "${GREEN}Detached from tmux session.${NC}"
        echo -e "Reattach with: ${CYAN}tmux attach -t quant-team${NC}"
        exit 0
    else
        echo -e "${BLUE}Using iTerm AppleScript launcher...${NC}"
        # Launch via Node.js launcher (handles iTerm AppleScript)
        node "$SCRIPT_DIR/iterm-quant-launcher.js" "$PRESET" "$MAX_ITERATIONS"
    fi

    echo ""
    echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║                    TEAM LAUNCHED SUCCESSFULLY                  ║${NC}"
    echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}Quick Commands:${NC}"
    echo -e "  ${CYAN}./scripts/quant-team/quant-control.sh status${NC}      - View team status"
    echo -e "  ${CYAN}./scripts/quant-team/quant-control.sh pause${NC}       - Pause all panes"
    echo -e "  ${CYAN}./scripts/quant-team/quant-control.sh resume${NC}      - Resume panes"
    echo -e "  ${CYAN}./scripts/quant-team/quant-control.sh stop${NC}        - Stop all panes"
    echo -e "  ${CYAN}./scripts/quant-team/quant-control.sh strategies${NC}  - View strategies"
    echo -e "  ${CYAN}./scripts/quant-team/quant-control.sh logs${NC}        - View logs"
    echo ""
    echo -e "${BOLD}Output Locations:${NC}"
    echo -e "  Strategies: ${CYAN}$STREAM_QUANT/output/strategies/${NC}"
    echo -e "  Research:   ${CYAN}$STREAM_QUANT/output/research-logs/${NC}"
    echo -e "  Indicators: ${CYAN}$STREAM_QUANT/output/indicators/${NC}"
    echo ""
}

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------
show_help() {
    echo -e "${BOLD}Spawn Quant Research Team${NC}"
    echo ""
    echo "Usage: ./spawn-quant-team.sh [options] [preset] [max_iterations] [budget]"
    echo ""
    echo "Options:"
    echo "  --profile <name>  Market profile (futures, crypto-cex, crypto-dex-hyperliquid)"
    echo "                    If omitted, uses active-profile.json or runs setup wizard"
    echo "  --tmux            Use tmux for visible 6-pane layout (default)"
    echo "  --iterm           Use iTerm AppleScript launcher (legacy)"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Arguments:"
    echo "  preset          Worker distribution preset (default: balanced)"
    echo "  max_iterations  Maximum iterations per pane (default: 50)"
    echo "  budget          Daily budget: 'unlimited' or amount in dollars (default: unlimited)"
    echo "                  Use 'unlimited' if you have Claude Max subscription"
    echo ""
    echo "Presets:"
    echo "  balanced       - One of each: researcher, converter, backtester,"
    echo "                   optimizer, prop_firm_validator, knowledge_distiller"
    echo "  research_heavy - 2 researchers, 1 each of other workers"
    echo "  backtest_heavy - 2 backtesters, 2 optimizers, 1 each of others"
    echo "  full_cycle     - 2 backtesters, 1 each of other workers"
    echo ""
    echo "Examples:"
    echo "  ./spawn-quant-team.sh                                 # balanced, tmux, unlimited"
    echo "  ./spawn-quant-team.sh --profile crypto-cex            # use crypto CEX profile"
    echo "  ./spawn-quant-team.sh --profile futures research_heavy 100  # futures, research focus"
    echo "  ./spawn-quant-team.sh --iterm balanced 50             # use iTerm instead of tmux"
    echo "  ./spawn-quant-team.sh full_cycle 75 25.00             # with \$25 budget limit"
    echo ""
    echo "Tmux Controls (when using --tmux, which is default):"
    echo "  Ctrl-b d       - Detach (keeps running in background overnight)"
    echo "  Ctrl-b [       - Scroll mode (q to exit)"
    echo "  Ctrl-b arrow   - Navigate between panes"
    echo "  Ctrl-b z       - Zoom/unzoom current pane"
    echo ""
    echo "Reattach: tmux attach -t quant-team"
    echo "Stop all: tmux kill-session -t quant-team"
    echo ""
    echo "The team will run autonomously until:"
    echo "  - Max iterations reached"
    echo "  - Budget exceeded (if budget limit set)"
    echo "  - Manually stopped via quant-control.sh or tmux kill-session"
    echo ""
}

# -----------------------------------------------------------------------------
# Parse Arguments
# -----------------------------------------------------------------------------
parse_args() {
    local positional_args=()
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help|help)
                show_help
                exit 0
                ;;
            --tmux)
                USE_TMUX=true
                shift
                ;;
            --iterm)
                USE_TMUX=false
                shift
                ;;
            --profile)
                QUANT_PROFILE="${2:-}"
                if [[ -z "$QUANT_PROFILE" ]]; then
                    echo -e "${RED}--profile requires a profile name${NC}"
                    exit 1
                fi
                shift 2
                ;;
            --profile=*)
                QUANT_PROFILE="${1#*=}"
                shift
                ;;
            *)
                positional_args+=("$1")
                shift
                ;;
        esac
    done
    
    # Assign positional arguments
    PRESET="${positional_args[0]:-balanced}"
    MAX_ITERATIONS="${positional_args[1]:-50}"
    DAILY_BUDGET="${positional_args[2]:-unlimited}"
    NOTIFY_METHOD="${positional_args[3]:-elevenlabs}"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    parse_args "$@"
    preflight_checks
    launch_team
}

main "$@"
