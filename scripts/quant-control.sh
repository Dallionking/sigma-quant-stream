#!/bin/bash
# =============================================================================
# Quant Team Control Interface
# =============================================================================
# Interactive control panel for monitoring and managing the Quant Research Team.
#
# Usage: ./quant-control.sh [command] [args...]
#
# Commands:
#   status      - Show team status
#   budget      - Show/set budget
#   pause       - Pause all panes
#   resume      - Resume all panes
#   stop        - Stop all panes
#   logs        - View recent logs
#   strategies  - List discovered strategies
#   help        - Show this help
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STREAM_QUANT="$PROJECT_ROOT/stream-quant"

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
# Helper Functions
# -----------------------------------------------------------------------------
print_header() {
    echo -e "\n${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║${NC}             ${BOLD}🧪 QUANT RESEARCH TEAM CONTROL${NC}                     ${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_section() {
    echo -e "\n${BOLD}${MAGENTA}━━━━ $1 ━━━━${NC}\n"
}

# -----------------------------------------------------------------------------
# Status Command
# -----------------------------------------------------------------------------
cmd_status() {
    print_header
    print_section "TEAM STATUS"

    # Read progress file
    if [[ -f "$STREAM_QUANT/progress.json" ]]; then
        python3 << 'EOF'
import json
from datetime import datetime

with open('$STREAM_QUANT/progress.json', 'r') as f:
    progress = json.load(f)

status = progress.get('status', 'unknown')
started = progress.get('started_at', 'N/A')
last_updated = progress.get('last_updated', 'N/A')

status_color = '\033[32m' if status == 'running' else '\033[33m'
print(f"Status: {status_color}{status.upper()}\033[0m")
print(f"Started: {started}")
print(f"Last Update: {last_updated}")
print()

print("\033[1mPane Status:\033[0m")
print("-" * 50)
for pane_id, pane_data in progress.get('panes', {}).items():
    worker = pane_data.get('worker_type', 'unknown')
    iteration = pane_data.get('current_iteration', 0)
    completed = pane_data.get('tasks_completed', 0)
    failed = pane_data.get('tasks_failed', 0)
    print(f"  {pane_id}: {worker:15} | Iter: {iteration:3} | Done: {completed:3} | Failed: {failed:3}")
EOF
    else
        echo -e "${YELLOW}No progress file found. Team may not be running.${NC}"
    fi

    # Show budget status
    print_section "BUDGET STATUS"
    python3 "$SCRIPT_DIR/cost-tracker.py" status 2>/dev/null || echo -e "${YELLOW}No budget data available.${NC}"

    # Show checkpoint status
    print_section "CHECKPOINTS"
    if [[ -d "$STREAM_QUANT/checkpoints" ]]; then
        local checkpoint_count=$(ls -1 "$STREAM_QUANT/checkpoints"/*.checkpoint 2>/dev/null | wc -l || echo "0")
        echo "Active checkpoints: $checkpoint_count"

        if [[ $checkpoint_count -gt 0 ]]; then
            for cp in "$STREAM_QUANT/checkpoints"/*.checkpoint; do
                if [[ -f "$cp" ]]; then
                    local pane=$(basename "$cp" .checkpoint)
                    local status=$(python3 -c "import json; print(json.load(open('$cp'))['status'])" 2>/dev/null || echo "unknown")
                    local iteration=$(python3 -c "import json; print(json.load(open('$cp'))['iteration'])" 2>/dev/null || echo "?")
                    echo "  - $pane: status=$status, iteration=$iteration"
                fi
            done
        fi
    else
        echo "No checkpoint directory found."
    fi
}

# -----------------------------------------------------------------------------
# Budget Command
# -----------------------------------------------------------------------------
cmd_budget() {
    print_header
    print_section "BUDGET MANAGEMENT"

    case "${1:-status}" in
        status)
            python3 "$SCRIPT_DIR/cost-tracker.py" status
            ;;
        set)
            if [[ -z "${2:-}" ]]; then
                echo -e "${RED}Usage: budget set <amount>${NC}"
                exit 1
            fi
            python3 "$SCRIPT_DIR/cost-tracker.py" --set-budget="$2"
            echo -e "${GREEN}Budget set to \$$2${NC}"
            ;;
        add)
            if [[ -z "${2:-}" || -z "${3:-}" || -z "${4:-}" ]]; then
                echo -e "${RED}Usage: budget add <service> <amount> <description>${NC}"
                exit 1
            fi
            python3 "$SCRIPT_DIR/cost-tracker.py" add "$2" "$3" "$4"
            echo -e "${GREEN}Added \$$3 to $2${NC}"
            ;;
        *)
            echo "Budget commands:"
            echo "  status    - Show current budget"
            echo "  set <amt> - Set daily budget"
            echo "  add <svc> <amt> <desc> - Add cost entry"
            ;;
    esac
}

# -----------------------------------------------------------------------------
# Pause/Resume Commands
# -----------------------------------------------------------------------------
cmd_pause() {
    print_header
    echo -e "${YELLOW}Pausing all panes...${NC}"

    python3 "$SCRIPT_DIR/cost-tracker.py" --pause --reason="Manual pause via control interface"
    echo -e "${GREEN}Cost tracking paused. Panes will stop at next iteration.${NC}"

    python3 "$SCRIPT_DIR/notify.py" system_event "Quant team paused" 2>/dev/null || echo "(Notification skipped)"
}

cmd_resume() {
    print_header
    echo -e "${GREEN}Resuming all panes...${NC}"

    python3 "$SCRIPT_DIR/cost-tracker.py" --resume
    echo -e "${GREEN}Cost tracking resumed. Panes will continue.${NC}"

    python3 "$SCRIPT_DIR/notify.py" system_event "Quant team resumed" 2>/dev/null || echo "(Notification skipped)"
}

# -----------------------------------------------------------------------------
# Add Pane Command
# -----------------------------------------------------------------------------
cmd_add_pane() {
    local worker_type="${1:-researcher}"
    
    print_header
    echo -e "${CYAN}Adding new pane: $worker_type${NC}"
    
    # Validate worker type
    case "$worker_type" in
        researcher|converter|backtester|optimizer|prop_firm_validator|knowledge_distiller)
            ;;
        *)
            echo -e "${RED}Invalid worker type: $worker_type${NC}"
            echo "Valid types: researcher, converter, backtester, optimizer, prop_firm_validator, knowledge_distiller"
            exit 1
            ;;
    esac
    
    # Get next pane number
    local checkpoint_count=$(ls -1 "$STREAM_QUANT/checkpoints"/*.checkpoint 2>/dev/null | wc -l || echo "0")
    local pane_num=$((checkpoint_count + 1))
    
    # Add pane via AppleScript
    osascript << APPLESCRIPT
tell application "iTerm"
    tell current window
        repeat with t in tabs
            if name of t contains "Quant" then
                tell t
                    tell current session
                        set newSession to (split vertically with default profile)
                    end tell
                    tell newSession
                        set name to "Pane-$pane_num-$worker_type"
                        write text "cd '$STREAM_QUANT' && claude --dangerously-skip-permissions -p 'Read CLAUDE.md. You are a $worker_type worker. Start your Ralph Loop with quant-ralph.sh'"
                    end tell
                end tell
                exit repeat
            end if
        end repeat
    end tell
end tell
APPLESCRIPT
    
    echo -e "${GREEN}✓ Added pane $pane_num as $worker_type${NC}"
    python3 "$SCRIPT_DIR/notify.py" system_event "Added new $worker_type pane"
}

# -----------------------------------------------------------------------------
# Stop Command
# -----------------------------------------------------------------------------
cmd_stop() {
    print_header
    echo -e "${RED}Stopping all panes...${NC}"

    # Signal stop by setting paused flag and sending notification
    python3 "$SCRIPT_DIR/cost-tracker.py" --pause --reason="Manual stop via control interface"

    # Kill any running claude processes in iTerm
    osascript << 'APPLESCRIPT'
tell application "iTerm"
    tell current window
        repeat with t in tabs
            if name of t contains "Quant" then
                repeat with s in sessions of t
                    tell s to close
                end repeat
            end if
        end repeat
    end tell
end tell
APPLESCRIPT

    echo -e "${GREEN}All panes signaled to stop.${NC}"
    python3 "$SCRIPT_DIR/notify.py" system_event "Quant team stopped" 2>/dev/null || echo "(Notification skipped)"
}

# -----------------------------------------------------------------------------
# Logs Command
# -----------------------------------------------------------------------------
cmd_logs() {
    print_header
    print_section "RECENT LOGS"

    local log_dir="$STREAM_QUANT/output/research-logs/daily"

    if [[ -d "$log_dir" ]]; then
        local latest=$(ls -1t "$log_dir"/*.md 2>/dev/null | head -1)
        if [[ -n "$latest" ]]; then
            echo -e "${CYAN}Latest log: $latest${NC}\n"
            head -50 "$latest"
            echo -e "\n${YELLOW}... (truncated, use 'cat $latest' for full log)${NC}"
        else
            echo "No log files found."
        fi
    else
        echo "Log directory not found."
    fi
}

# -----------------------------------------------------------------------------
# Strategies Command
# -----------------------------------------------------------------------------
cmd_strategies() {
    print_header

    print_section "STRATEGIES DISCOVERED"

    # Good strategies
    local good_dir="$STREAM_QUANT/output/strategies/good"
    if [[ -d "$good_dir" ]]; then
        local good_count=$(ls -1 "$good_dir"/*.json 2>/dev/null | wc -l || echo "0")
        echo -e "${GREEN}Good Strategies: $good_count${NC}"
        if [[ $good_count -gt 0 ]]; then
            for f in "$good_dir"/*.json; do
                local name=$(python3 -c "import json; print(json.load(open('$f')).get('name', 'unknown'))" 2>/dev/null || echo "unknown")
                local sharpe=$(python3 -c "import json; print(json.load(open('$f')).get('metrics', {}).get('sharpe_ratio', '?'))" 2>/dev/null || echo "?")
                echo "  - $name (Sharpe: $sharpe)"
            done
        fi
    fi
    echo

    # Prop firm ready
    local ready_dir="$STREAM_QUANT/output/strategies/prop_firm_ready"
    if [[ -d "$ready_dir" ]]; then
        local ready_count=$(ls -1 "$ready_dir"/*.json 2>/dev/null | wc -l || echo "0")
        echo -e "${CYAN}Prop Firm Ready: $ready_count${NC}"
        if [[ $ready_count -gt 0 ]]; then
            for f in "$ready_dir"/*.json; do
                local name=$(python3 -c "import json; print(json.load(open('$f')).get('name', 'unknown'))" 2>/dev/null || echo "unknown")
                local firms=$(python3 -c "import json; print(len(json.load(open('$f')).get('prop_firm_validation', {}).get('passingFirms', [])))" 2>/dev/null || echo "?")
                echo "  - $name (Passes $firms firms)"
            done
        fi
    fi
    echo

    # Rejected
    local reject_dir="$STREAM_QUANT/output/strategies/rejected"
    if [[ -d "$reject_dir" ]]; then
        local reject_count=$(ls -1 "$reject_dir"/*.json 2>/dev/null | wc -l || echo "0")
        echo -e "${RED}Rejected: $reject_count${NC}"
    fi
}

# -----------------------------------------------------------------------------
# Interactive Mode
# -----------------------------------------------------------------------------
cmd_interactive() {
    print_header

    while true; do
        echo -e "\n${BOLD}Commands:${NC} [s]tatus [b]udget [p]ause [r]esume [x]stop [a]dd-pane [l]ogs [g]strategies [q]uit"
        read -rp "> " cmd

        case "$cmd" in
            s|status) cmd_status ;;
            b|budget) cmd_budget ;;
            p|pause) cmd_pause ;;
            r|resume) cmd_resume ;;
            x|stop) cmd_stop ;;
            a|add-pane)
                echo -e "${CYAN}Worker types: researcher, converter, backtester, optimizer, prop_firm_validator, knowledge_distiller${NC}"
                read -rp "Worker type: " worker_type
                cmd_add_pane "$worker_type"
                ;;
            l|logs) cmd_logs ;;
            g|strategies) cmd_strategies ;;
            q|quit|exit) echo "Goodbye!"; exit 0 ;;
            *) echo -e "${YELLOW}Unknown command. Try again.${NC}" ;;
        esac
    done
}

# -----------------------------------------------------------------------------
# Help Command
# -----------------------------------------------------------------------------
cmd_help() {
    print_header
    cat << EOF
${BOLD}Usage:${NC} ./quant-control.sh [command] [args...]

${BOLD}Commands:${NC}
  status              Show team status, panes, budget
  budget [sub]        Budget management (status|set|add)
  pause               Pause all panes at next iteration
  resume              Resume paused panes
  stop                Stop all panes immediately
  add-pane <type>     Add a new worker pane mid-session
  logs                View recent research logs
  strategies          List discovered strategies
  interactive         Interactive control mode
  help                Show this help message

${BOLD}Worker Types (for add-pane):${NC}
  researcher, converter, backtester, optimizer, prop_firm_validator, knowledge_distiller

${BOLD}Examples:${NC}
  ./quant-control.sh status
  ./quant-control.sh budget set 25.00
  ./quant-control.sh pause
  ./quant-control.sh interactive

${BOLD}Environment:${NC}
  Project Root: $PROJECT_ROOT
  Stream Quant: $STREAM_QUANT
EOF
}

# -----------------------------------------------------------------------------
# Main Dispatch
# -----------------------------------------------------------------------------
main() {
    case "${1:-interactive}" in
        status) cmd_status ;;
        budget) shift; cmd_budget "$@" ;;
        pause) cmd_pause ;;
        resume) cmd_resume ;;
        stop) cmd_stop ;;
        add-pane) shift; cmd_add_pane "$@" ;;
        logs) cmd_logs ;;
        strategies) cmd_strategies ;;
        interactive) cmd_interactive ;;
        help|--help|-h) cmd_help ;;
        *) echo -e "${RED}Unknown command: $1${NC}"; cmd_help; exit 1 ;;
    esac
}

main "$@"
