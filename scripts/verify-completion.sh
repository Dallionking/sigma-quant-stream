#!/bin/bash
# verify-completion.sh - Claude Code Stop Hook for Quant Ralph
# This script runs when Claude attempts to stop, verifying task completion
#
# Exit codes:
#   0 = Allow stop (task complete)
#   1 = Block stop (task not complete, continue working)
#   2 = Error (allow stop anyway)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STREAM_QUANT="${SCRIPT_DIR}/../../stream-quant"
OUTPUT_DIR="$STREAM_QUANT/output"
CHECKPOINT_DIR="$STREAM_QUANT/checkpoints"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[STOP-HOOK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[STOP-HOOK]${NC} $1"
}

log_error() {
    echo -e "${RED}[STOP-HOOK]${NC} $1"
}

# Get current task from most recent checkpoint
get_current_task() {
    local latest_checkpoint=$(ls -t "$CHECKPOINT_DIR"/pane-*.status 2>/dev/null | head -1)
    if [[ -f "$latest_checkpoint" ]]; then
        jq -r '.current_task // empty' "$latest_checkpoint" 2>/dev/null
    fi
}

# Check if completion markers are present in recent output
check_completion_markers() {
    local task_id="$1"
    
    # Check for completion markers in recent Claude output
    if grep -rq "QUANT_TASK_COMPLETE" "$OUTPUT_DIR" 2>/dev/null; then
        return 0
    fi
    
    if grep -rq '<promise>COMPLETE</promise>' "$OUTPUT_DIR" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Check if output files were created recently (last 10 minutes)
check_recent_output() {
    local recent_count=$(find "$OUTPUT_DIR" -type f -mmin -10 2>/dev/null | wc -l)
    if [[ "$recent_count" -gt 0 ]]; then
        log_info "Found $recent_count files created in last 10 minutes"
        return 0
    fi
    return 1
}

# Main verification logic
main() {
    log_info "Stop hook triggered - verifying task completion..."
    
    # Get current task
    local current_task=$(get_current_task)
    
    if [[ -z "$current_task" ]]; then
        log_warn "No current task found in checkpoints"
        exit 0  # Allow stop if we can't determine task
    fi
    
    log_info "Current task: $current_task"
    
    # Check for explicit completion markers
    if check_completion_markers "$current_task"; then
        log_info "✓ Completion marker found - allowing stop"
        exit 0
    fi
    
    # Check for recent output files
    if check_recent_output; then
        log_info "✓ Recent output files found - allowing stop"
        exit 0
    fi
    
    # No completion evidence found
    log_warn "⚠️ No completion evidence found"
    log_warn "Task may not be complete. Please ensure you output:"
    log_warn "  QUANT_TASK_COMPLETE: $current_task"
    log_warn "  OUTPUT: <path_to_file>"
    
    # Block stop to encourage completion
    # Note: Exit 1 blocks the stop in Claude Code hooks
    exit 1
}

main "$@"
