#!/bin/bash
# =============================================================================
# Quant Ralph Loop Runner - MISSION-BASED ARCHITECTURE
# =============================================================================
# Runs infinite autonomous research sessions with inter-agent communication.
# Each session operates on a STANDING MISSION, not pre-generated tasks.
#
# Key differences from task-based version:
# - Infinite loop (runs until budget or manual stop)
# - Mission prompts with injected context (patterns, previous session)
# - SESSION_COMPLETE marker (not task completion)
# - @sigma-distiller invocation for knowledge synthesis
# - Inter-agent communication via queue directories
#
# Usage: ./quant-ralph.sh <pane_id> <worker_type> [mode]
#
# Modes:
#   research   - 30min timeout, sample data, $50 cap (default)
#   production - 60min timeout, Databento, $100 cap
#
# Example: ./quant-ralph.sh 0 researcher research
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STREAM_QUANT="$PROJECT_ROOT/stream-quant"

# Market Profile
PROFILE_FILE="${QUANT_PROFILE:-$STREAM_QUANT/profiles/active-profile.json}"
if [[ ! -f "$PROFILE_FILE" ]]; then
    # Fallback to futures profile
    PROFILE_FILE="$STREAM_QUANT/profiles/futures.json"
fi

# Directories
QUEUES_DIR="$STREAM_QUANT/queues"
PATTERNS_DIR="$STREAM_QUANT/patterns"
PROMPTS_DIR="$STREAM_QUANT/prompts"
OUTPUT_DIR="$STREAM_QUANT/output"
SESSION_DIR="$STREAM_QUANT/session-summaries"
CHECKPOINT_DIR="$STREAM_QUANT/checkpoints"
DATA_DIR="$STREAM_QUANT/data"

# Ensure all directories exist
mkdir -p "$QUEUES_DIR"/{hypotheses,to-convert,to-backtest,to-optimize}
mkdir -p "$PATTERNS_DIR"
mkdir -p "$OUTPUT_DIR"/{strategies/{good,rejected,prop_firm_ready,GOOD},indicators/{converted,created},backtests,research-logs/daily}
mkdir -p "$SESSION_DIR"
mkdir -p "$CHECKPOINT_DIR"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Arguments
# -----------------------------------------------------------------------------
PANE_ID="${1:-0}"
WORKER_TYPE="${2:-researcher}"
MODE="${3:-research}"

# Session tracking
SESSION_NUMBER=0
SESSIONS_COMPLETED=0
SESSIONS_FAILED=0
TOTAL_FILES_CREATED=0
TOTAL_INPUT_TOKENS=0
TOTAL_OUTPUT_TOKENS=0

# Mode-specific configuration
case "$MODE" in
    research)
        SESSION_TIMEOUT=1800    # 30 minutes
        BUDGET_CAP=50           # $50
        DATA_SOURCE="sample"
        ;;
    production)
        SESSION_TIMEOUT=3600    # 60 minutes
        BUDGET_CAP=100          # $100
        DATA_SOURCE="databento"
        ;;
    *)
        echo -e "${RED}Invalid mode: $MODE${NC}" >&2
        echo "Valid modes: research, production" >&2
        exit 1
        ;;
esac

# Checkpoint and status files
CHECKPOINT_FILE="$CHECKPOINT_DIR/pane-${PANE_ID}.checkpoint"
STATUS_FILE="$CHECKPOINT_DIR/pane-${PANE_ID}.status"
SESSION_START_MARKER="/tmp/session-start-pane-${PANE_ID}"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[PANE-$PANE_ID]${NC} ${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${BLUE}[PANE-$PANE_ID]${NC} ${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${BLUE}[PANE-$PANE_ID]${NC} ${RED}[ERROR]${NC} $1"
}

log_session() {
    echo -e "${BLUE}[PANE-$PANE_ID]${NC} ${MAGENTA}[SESSION]${NC} $1"
}

# -----------------------------------------------------------------------------
# Status Management
# -----------------------------------------------------------------------------
update_status_file() {
    local step="${1:-Running}"
    local detail="${2:-}"
    cat > "$STATUS_FILE" << EOF
{
    "pane_id": $PANE_ID,
    "worker": "$WORKER_TYPE",
    "mode": "$MODE",
    "step": "$step",
    "session": $SESSION_NUMBER,
    "completed": $SESSIONS_COMPLETED,
    "failed": $SESSIONS_FAILED,
    "files_created": $TOTAL_FILES_CREATED,
    "detail": "$detail",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
}

# -----------------------------------------------------------------------------
# Budget Check
# -----------------------------------------------------------------------------
check_budget() {
    # Simple cost estimation: ~$0.042 per session (Claude Sonnet 4)
    local estimated_cost=$(echo "scale=2; $SESSION_NUMBER * 0.042" | bc 2>/dev/null || echo "0")

    if command -v python3 &> /dev/null && [[ -f "$SCRIPT_DIR/cost-tracker.py" ]]; then
        if ! python3 "$SCRIPT_DIR/cost-tracker.py" --check 2>/dev/null; then
            log_error "Budget exceeded! Stopping loop."
            return 1
        fi
    fi

    # Fallback: simple session count check
    local max_sessions=$((BUDGET_CAP * 24))  # ~24 sessions per dollar
    if [[ $SESSION_NUMBER -gt $max_sessions ]]; then
        log_error "Estimated budget cap reached (~$BUDGET_CAP). Stopping."
        return 1
    fi

    return 0
}

# -----------------------------------------------------------------------------
# Build Mission Prompt
# -----------------------------------------------------------------------------
build_mission_prompt() {
    local worker_prompt_file="$PROMPTS_DIR/${WORKER_TYPE}.md"

    if [[ ! -f "$worker_prompt_file" ]]; then
        log_error "Worker prompt not found: $worker_prompt_file"
        return 1
    fi

    # Read base worker prompt
    local base_prompt
    base_prompt=$(cat "$worker_prompt_file")

    # Get previous session summary (last 30 lines)
    local pane_summary_file="$SESSION_DIR/pane-${PANE_ID}.md"
    local previous_session=""
    if [[ -f "$pane_summary_file" ]]; then
        previous_session=$(tail -50 "$pane_summary_file" 2>/dev/null || echo "No previous sessions.")
    fi

    # Get recent pattern entries (what's working, what's failing)
    local what_works=""
    local what_fails=""
    if [[ -f "$PATTERNS_DIR/what-works.md" ]]; then
        what_works=$(tail -30 "$PATTERNS_DIR/what-works.md" 2>/dev/null || echo "No entries yet.")
    fi
    if [[ -f "$PATTERNS_DIR/what-fails.md" ]]; then
        what_fails=$(tail -20 "$PATTERNS_DIR/what-fails.md" 2>/dev/null || echo "No entries yet.")
    fi

    # Get queue status
    local queue_status=""
    queue_status="Hypotheses: $(ls -1 "$QUEUES_DIR/hypotheses/" 2>/dev/null | wc -l | tr -d ' ')
To-Convert: $(ls -1 "$QUEUES_DIR/to-convert/" 2>/dev/null | wc -l | tr -d ' ')
To-Backtest: $(ls -1 "$QUEUES_DIR/to-backtest/" 2>/dev/null | wc -l | tr -d ' ')
To-Optimize: $(ls -1 "$QUEUES_DIR/to-optimize/" 2>/dev/null | wc -l | tr -d ' ')"

    # Read active profile and extract fields
    local profile_id=""
    local profile_display=""
    local profile_market_type=""
    local profile_symbols=""
    local profile_costs_model=""
    local profile_costs_info=""
    local profile_compliance_type=""
    local profile_research_people=""
    local profile_research_web=""
    local profile_data_adapter=""
    local profile_sample_dir=""
    local profile_sample_files=""
    local profile_validated_dir=""

    if [[ -f "$PROFILE_FILE" ]]; then
        profile_id=$(python3 -c "import json; print(json.load(open('$PROFILE_FILE'))['profileId'])" 2>/dev/null || echo "unknown")
        profile_display=$(python3 -c "import json; print(json.load(open('$PROFILE_FILE'))['displayName'])" 2>/dev/null || echo "Unknown Profile")
        profile_market_type=$(python3 -c "import json; print(json.load(open('$PROFILE_FILE'))['marketType'])" 2>/dev/null || echo "futures")
        profile_symbols=$(python3 -c "import json; p=json.load(open('$PROFILE_FILE')); print(', '.join(p['symbols'].get('pinned', []) or ['dynamic from volume/OI rank']))" 2>/dev/null || echo "ES, NQ, YM, GC")
        profile_costs_model=$(python3 -c "import json; print(json.load(open('$PROFILE_FILE'))['costs']['model'])" 2>/dev/null || echo "per_contract")
        profile_costs_info=$(python3 -c "
import json
p = json.load(open('$PROFILE_FILE'))
c = p['costs']
if c['model'] == 'per_contract':
    print(f\"Commission: \${c['commission']}/contract/side, Slippage: {c['slippage']} {c.get('slippageUnit','ticks')}\")
elif c['model'] == 'percentage':
    maker = c.get('makerFee', 0) * 100
    taker = c.get('takerFee', 0) * 100
    slip = c.get('slippageBps', 0)
    funding = c.get('fundingRateAvg', 0) * 100
    parts = [f'Maker: {maker:.2f}%', f'Taker: {taker:.2f}%', f'Slippage: {slip}bps']
    if funding: parts.append(f'Avg Funding: {funding:.2f}%')
    print(', '.join(parts))
" 2>/dev/null || echo "See profile for cost details")
        profile_compliance_type=$(python3 -c "import json; print(json.load(open('$PROFILE_FILE'))['compliance']['type'])" 2>/dev/null || echo "prop-firm")
        profile_research_people=$(python3 -c "import json; print(', '.join(json.load(open('$PROFILE_FILE'))['researchSources']['people']))" 2>/dev/null || echo "")
        profile_research_web=$(python3 -c "import json; print(', '.join(json.load(open('$PROFILE_FILE'))['researchSources']['web']))" 2>/dev/null || echo "")
        profile_data_adapter=$(python3 -c "import json; print(json.load(open('$PROFILE_FILE'))['dataProvider']['adapter'])" 2>/dev/null || echo "databento")
        profile_sample_dir=$(python3 -c "import json; print(json.load(open('$PROFILE_FILE'))['dataProvider'].get('sampleDataDir', 'data/'))" 2>/dev/null || echo "data/")
        profile_sample_files=$(python3 -c "import json; print(', '.join(json.load(open('$PROFILE_FILE'))['dataProvider'].get('sampleFiles', [])))" 2>/dev/null || echo "ES_5min_sample.csv")
        profile_validated_dir=$(python3 -c "import json; print(json.load(open('$PROFILE_FILE'))['output']['validatedDir'])" 2>/dev/null || echo "output/strategies/prop_firm_ready")
    fi

    # Build the full mission prompt with injected context
    cat << PROMPT
$base_prompt

---

## INJECTED CONTEXT (Session #$SESSION_NUMBER)

### Active Market Profile
- **Profile**: $profile_display ($profile_id)
- **Market Type**: $profile_market_type
- **Symbols**: $profile_symbols
- **Data Provider**: $profile_data_adapter
- **Costs Model**: $profile_costs_model — $profile_costs_info
- **Compliance Type**: $profile_compliance_type
- **Validated Output**: $profile_validated_dir

### Research Context
- **Key People**: $profile_research_people
- **Web Sources**: $profile_research_web

### Mode: $MODE
- Timeout: $((SESSION_TIMEOUT / 60)) minutes
- Data Source: $DATA_SOURCE
- Sample Data: $STREAM_QUANT/$profile_sample_dir ($profile_sample_files)

### Queue Status
\`\`\`
$queue_status
\`\`\`

### Recent What-Works Patterns
\`\`\`
$what_works
\`\`\`

### Recent What-Fails Patterns
\`\`\`
$what_fails
\`\`\`

### Previous Session Summary
\`\`\`
$previous_session
\`\`\`

---

## SESSION REQUIREMENTS

1. **Create at least 1 output file** (strategy, indicator, hypothesis, backtest result)
2. **Check queues** for work before generating new items
3. **Update patterns** if you discover something new
4. **Use the active profile** for symbols, costs, compliance, and data paths
5. At session end, invoke: \`@sigma-distiller\`
6. End with marker: \`SESSION_COMPLETE\`

**BEGIN YOUR MISSION NOW**
PROMPT
}

# -----------------------------------------------------------------------------
# Validate Session Output
# -----------------------------------------------------------------------------
FAILURE_LOG_DIR="$OUTPUT_DIR/research-logs"

log_failure_jsonl() {
    local failure_type="$1"
    local detail="$2"
    local session_num="$3"
    local failure_log="$FAILURE_LOG_DIR/failures-$(date +%Y-%m-%d).jsonl"
    mkdir -p "$FAILURE_LOG_DIR"

    python3 -c "
import json, datetime
entry = {
    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
    'pane_id': $PANE_ID,
    'worker': '$WORKER_TYPE',
    'session': $session_num,
    'failure_type': '$failure_type',
    'detail': '''$detail''',
    'mode': '$MODE'
}
print(json.dumps(entry))
" >> "$failure_log" 2>/dev/null || \
    echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"pane_id\":$PANE_ID,\"worker\":\"$WORKER_TYPE\",\"session\":$session_num,\"failure_type\":\"$failure_type\",\"detail\":\"$detail\"}" >> "$failure_log"
}

validate_json_artifact() {
    # Validate a single JSON file has required metrics and trade count > 0
    local json_file="$1"

    if [[ ! -f "$json_file" ]]; then
        return 1
    fi

    # Check file is valid JSON with required backtest fields
    python3 -c "
import json, sys
try:
    with open('$json_file') as f:
        data = json.load(f)
except (json.JSONDecodeError, IOError):
    sys.exit(1)

# Check for backtest result structure (in-sample or out-of-sample or flat)
def get_trades(d):
    for key in ['outOfSample', 'out_of_sample', 'oos']:
        if key in d and 'trades' in d[key]:
            return d[key]['trades']
    for key in ['inSample', 'in_sample', 'is']:
        if key in d and 'trades' in d[key]:
            return d[key]['trades']
    if 'trades' in d:
        return d['trades']
    if 'trade_count' in d:
        return d['trade_count']
    if 'total_trades' in d:
        return d['total_trades']
    return None

trades = get_trades(data)
if trades is None:
    # Not a backtest result file -- may be a hypothesis or config
    # Accept non-backtest JSON as valid artifact
    sys.exit(0)

if int(trades) <= 0:
    sys.exit(2)  # Zero trades

sys.exit(0)
" 2>/dev/null
    return $?
}

validate_session_output() {
    local output_file="$1"
    local session_start_time="$2"

    # Step 1: Check for SESSION_COMPLETE marker
    if ! grep -q "SESSION_COMPLETE" "$output_file" 2>/dev/null; then
        log_warn "SESSION_COMPLETE marker not found"
        log_failure_jsonl "no_output" "SESSION_COMPLETE marker missing from session output" "$SESSION_NUMBER"
        return 1
    fi

    # Step 2: Check for files created since session start
    local files_created=0
    local new_output_files=""
    local new_queue_files=""
    if [[ -f "$SESSION_START_MARKER" ]]; then
        new_output_files=$(find "$OUTPUT_DIR" -type f -newer "$SESSION_START_MARKER" 2>/dev/null)
        new_queue_files=$(find "$QUEUES_DIR" -type f -newer "$SESSION_START_MARKER" 2>/dev/null)
        files_created=$(echo -e "${new_output_files}\n${new_queue_files}" | grep -c '.' 2>/dev/null || echo 0)
    fi

    if [[ $files_created -eq 0 ]]; then
        log_warn "No output files created during session"
        log_failure_jsonl "no_output" "Session completed with SESSION_COMPLETE but produced zero files" "$SESSION_NUMBER"
        return 1
    fi

    # Step 3: Validate JSON artifacts have real content
    local valid_artifacts=0
    local zero_trade_files=0
    local invalid_json_files=0

    while IFS= read -r fpath; do
        [[ -z "$fpath" ]] && continue
        if [[ "$fpath" == *.json ]]; then
            validate_json_artifact "$fpath"
            local vresult=$?
            if [[ $vresult -eq 0 ]]; then
                ((valid_artifacts++))
            elif [[ $vresult -eq 2 ]]; then
                ((zero_trade_files++))
                log_warn "Zero trades in backtest: $fpath"
            else
                ((invalid_json_files++))
                log_warn "Invalid JSON artifact: $fpath"
            fi
        elif [[ "$fpath" == *.py ]] || [[ "$fpath" == *.md ]] || [[ "$fpath" == *.csv ]]; then
            # Python files, markdown docs, CSV results count as valid
            ((valid_artifacts++))
        fi
    done <<< "$(echo -e "${new_output_files}\n${new_queue_files}")"

    if [[ $valid_artifacts -eq 0 ]]; then
        log_warn "No valid artifacts produced (invalid JSON: $invalid_json_files, zero trades: $zero_trade_files)"
        if [[ $zero_trade_files -gt 0 ]]; then
            log_failure_jsonl "no_trades" "Backtest results contain zero trades ($zero_trade_files files)" "$SESSION_NUMBER"
        elif [[ $invalid_json_files -gt 0 ]]; then
            log_failure_jsonl "invalid_output" "JSON artifacts failed validation ($invalid_json_files files)" "$SESSION_NUMBER"
        else
            log_failure_jsonl "no_output" "Files created but none are valid artifacts" "$SESSION_NUMBER"
        fi
        return 1
    fi

    TOTAL_FILES_CREATED=$((TOTAL_FILES_CREATED + files_created))
    log_info "Session created $files_created files ($valid_artifacts valid artifacts, total: $TOTAL_FILES_CREATED)"

    return 0
}

# -----------------------------------------------------------------------------
# Categorize Failure
# -----------------------------------------------------------------------------
categorize_failure() {
    local output_file="$1"
    local exit_code="$2"

    # Timeout (exit code 124 from timeout command)
    if [[ $exit_code -eq 124 ]]; then
        echo "timeout"
        return
    fi

    # Rate limit detection
    if grep -qiE "(rate.?limit|too.?many.?requests|quota.?exceeded|capacity|overloaded)" "$output_file" 2>/dev/null; then
        echo "rate_limit"
        return
    fi

    # Data file not found
    if grep -qiE "(data.?not.?found|file.?not.?found|no.?such.?file|missing.?data|FileNotFoundError|csv.*not found)" "$output_file" 2>/dev/null; then
        echo "no_data"
        return
    fi

    # Python import errors
    if grep -qiE "(ImportError|ModuleNotFoundError|No module named|cannot import)" "$output_file" 2>/dev/null; then
        echo "import_error"
        return
    fi

    # Strategy code errors (syntax, attribute, type errors in strategy logic)
    if grep -qiE "(SyntaxError|AttributeError|TypeError|ValueError|KeyError|IndexError|ZeroDivisionError)" "$output_file" 2>/dev/null; then
        echo "strategy_error"
        return
    fi

    # API / connection error
    if grep -qiE "(api.?error|connection.?refused|network.?error|ConnectionError|TimeoutError)" "$output_file" 2>/dev/null; then
        echo "api_error"
        return
    fi

    # No output files produced (SESSION_COMPLETE but nothing saved)
    if grep -q "SESSION_COMPLETE" "$output_file" 2>/dev/null; then
        echo "no_output"
        return
    fi

    # Generic error
    echo "unknown_error"
}

# -----------------------------------------------------------------------------
# Handle Failure
# -----------------------------------------------------------------------------
handle_failure() {
    local failure_type="$1"
    local output_file="$2"

    # Log every failure to structured JSONL
    local detail=""
    if [[ -f "$output_file" ]]; then
        detail=$(tail -5 "$output_file" 2>/dev/null | tr '\n' ' ' | head -c 200)
    fi
    log_failure_jsonl "$failure_type" "$detail" "$SESSION_NUMBER"

    case "$failure_type" in
        rate_limit)
            local pause_time=$((300 + RANDOM % 300))  # 5-10 minutes
            log_warn "Rate limit detected! Pausing for $((pause_time/60)) minutes..."
            update_status_file "Rate Limited" "Waiting $((pause_time/60))m"
            sleep "$pause_time"
            return 0  # Retry
            ;;
        no_data)
            log_warn "Data file not found - check data/ directory and active profile"
            echo "$(date): Pane $PANE_ID - Data not found" >> "$STREAM_QUANT/errors.log"
            return 0  # Continue with next session
            ;;
        import_error)
            log_warn "Python import failed - check dependencies (pip install)"
            echo "$(date): Pane $PANE_ID - Import error" >> "$STREAM_QUANT/errors.log"
            return 0  # Continue
            ;;
        strategy_error)
            log_warn "Strategy code error - see failure log for traceback"
            if [[ -f "$output_file" ]]; then
                echo "=== Strategy Error: $(date) ===" >> "$STREAM_QUANT/errors.log"
                grep -A3 -E "(Error|Traceback)" "$output_file" 2>/dev/null | tail -20 >> "$STREAM_QUANT/errors.log"
                echo "" >> "$STREAM_QUANT/errors.log"
            fi
            return 0  # Continue
            ;;
        timeout)
            log_warn "Session timed out - increasing timeout for next session"
            SESSION_TIMEOUT=$((SESSION_TIMEOUT + 600))  # Add 10 minutes
            if [[ $SESSION_TIMEOUT -gt 7200 ]]; then
                SESSION_TIMEOUT=7200  # Cap at 2 hours
            fi
            return 0  # Continue
            ;;
        no_output)
            log_warn "Session completed but produced no valid output files"
            return 0  # Continue
            ;;
        api_error)
            log_warn "API error - waiting 60 seconds"
            sleep 60
            return 0  # Retry
            ;;
        *)
            log_error "Unknown error type: $failure_type"
            # Log stack trace
            if [[ -f "$output_file" ]]; then
                echo "=== Error Log: $(date) ===" >> "$STREAM_QUANT/errors.log"
                tail -50 "$output_file" >> "$STREAM_QUANT/errors.log" 2>/dev/null
                echo "" >> "$STREAM_QUANT/errors.log"
            fi
            return 0  # Continue
            ;;
    esac
}

# -----------------------------------------------------------------------------
# Run Single Session
# -----------------------------------------------------------------------------
run_session() {
    local output_file=$(mktemp)
    local exit_code=0

    # Mark session start for file creation tracking
    touch "$SESSION_START_MARKER"

    # Build mission prompt
    local mission_prompt
    mission_prompt=$(build_mission_prompt) || return 1

    # Save prompt to temp file
    local prompt_file=$(mktemp)
    echo "$mission_prompt" > "$prompt_file"

    log_session "Starting session #$SESSION_NUMBER (timeout: $((SESSION_TIMEOUT/60))m)"
    update_status_file "Running" "Session #$SESSION_NUMBER"

    # Execute Claude with mission prompt
    local start_time=$(date +%s)

    if command -v claude &> /dev/null; then
        timeout "$SESSION_TIMEOUT" claude --dangerously-skip-permissions \
            -p "$(cat "$prompt_file")" \
            2>&1 | tee "$output_file" || exit_code=$?
    else
        log_error "Claude Code CLI not found!"
        rm -f "$prompt_file" "$output_file"
        return 1
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    rm -f "$prompt_file"

    # Check for successful completion
    if validate_session_output "$output_file" "$start_time"; then
        ((SESSIONS_COMPLETED++))
        log_session "✅ Session #$SESSION_NUMBER completed ($((duration/60))m $((duration%60))s)"

        # Parse token usage
        local result_line=$(grep '"type":"result"' "$output_file" 2>/dev/null | tail -1)
        if [[ -n "$result_line" ]]; then
            local input_tokens=$(echo "$result_line" | python3 -c "import json,sys; print(json.load(sys.stdin).get('usage',{}).get('input_tokens',0))" 2>/dev/null || echo "0")
            local output_tokens=$(echo "$result_line" | python3 -c "import json,sys; print(json.load(sys.stdin).get('usage',{}).get('output_tokens',0))" 2>/dev/null || echo "0")
            TOTAL_INPUT_TOKENS=$((TOTAL_INPUT_TOKENS + input_tokens))
            TOTAL_OUTPUT_TOKENS=$((TOTAL_OUTPUT_TOKENS + output_tokens))
        fi

        rm -f "$output_file"
        return 0
    else
        ((SESSIONS_FAILED++))

        # Categorize and handle failure
        local failure_type
        failure_type=$(categorize_failure "$output_file" "$exit_code")
        log_session "❌ Session #$SESSION_NUMBER failed: $failure_type"

        handle_failure "$failure_type" "$output_file"

        rm -f "$output_file"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Save Checkpoint
# -----------------------------------------------------------------------------
save_checkpoint() {
    local status="${1:-running}"
    cat > "$CHECKPOINT_FILE" << EOF
{
    "pane_id": $PANE_ID,
    "worker_type": "$WORKER_TYPE",
    "mode": "$MODE",
    "session_number": $SESSION_NUMBER,
    "sessions_completed": $SESSIONS_COMPLETED,
    "sessions_failed": $SESSIONS_FAILED,
    "files_created": $TOTAL_FILES_CREATED,
    "status": "$status",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
}

# -----------------------------------------------------------------------------
# Load Checkpoint
# -----------------------------------------------------------------------------
load_checkpoint() {
    if [[ -f "$CHECKPOINT_FILE" ]]; then
        SESSION_NUMBER=$(python3 -c "import json; print(json.load(open('$CHECKPOINT_FILE'))['session_number'])" 2>/dev/null || echo "0")
        SESSIONS_COMPLETED=$(python3 -c "import json; print(json.load(open('$CHECKPOINT_FILE'))['sessions_completed'])" 2>/dev/null || echo "0")
        SESSIONS_FAILED=$(python3 -c "import json; print(json.load(open('$CHECKPOINT_FILE'))['sessions_failed'])" 2>/dev/null || echo "0")
        TOTAL_FILES_CREATED=$(python3 -c "import json; print(json.load(open('$CHECKPOINT_FILE'))['files_created'])" 2>/dev/null || echo "0")
        log_info "📂 Resumed from checkpoint: session $SESSION_NUMBER"
        return 0
    fi
    return 1
}

# -----------------------------------------------------------------------------
# Main Loop
# -----------------------------------------------------------------------------
main() {
    local WORKER_UPPER
    WORKER_UPPER=$(echo "$WORKER_TYPE" | tr '[:lower:]' '[:upper:]')

    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  🧪 ${BOLD}QUANT RALPH - PANE $PANE_ID - ${GREEN}$WORKER_UPPER${NC}${CYAN}                      ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}MISSION-BASED INFINITE LOOP${NC}                                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Mode: ${BOLD}$MODE${NC} | Timeout: ${BOLD}$((SESSION_TIMEOUT/60))m${NC} | Budget: ${BOLD}\$$BUDGET_CAP${NC}        ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local profile_name
    profile_name=$(python3 -c "import json; print(json.load(open('$PROFILE_FILE'))['profileId'])" 2>/dev/null || echo "futures")
    log_info "Worker:    $WORKER_TYPE"
    log_info "Profile:   $profile_name ($PROFILE_FILE)"
    log_info "Mode:      $MODE"
    log_info "Timeout:   $((SESSION_TIMEOUT/60)) minutes"
    log_info "Data:      $DATA_SOURCE"
    log_info "Budget:    \$$BUDGET_CAP"
    echo ""

    # Try to resume from checkpoint
    load_checkpoint || true

    # Initial budget check
    if ! check_budget; then
        exit 1
    fi

    # Notify start
    if [[ -f "$SCRIPT_DIR/notify.py" ]]; then
        python3 "$SCRIPT_DIR/notify.py" --event=startup --pane="$PANE_ID" \
            "Pane $PANE_ID ($WORKER_TYPE) starting MISSION-BASED loop" 2>/dev/null || true
    fi

    log_info "🚀 Starting infinite mission loop..."
    echo ""

    # =========================================================================
    # INFINITE MISSION LOOP
    # =========================================================================
    while true; do
        SESSION_NUMBER=$((SESSION_NUMBER + 1))

        log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "SESSION $SESSION_NUMBER | Completed: $SESSIONS_COMPLETED | Failed: $SESSIONS_FAILED"
        log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # Check budget before each session
        if ! check_budget; then
            log_error "Budget limit reached after $SESSION_NUMBER sessions"
            break
        fi

        # Run the session
        if run_session; then
            log_info "Session successful - continuing mission"
        else
            log_warn "Session had issues - continuing after recovery"
        fi

        # Save checkpoint after each session
        save_checkpoint "running"

        # Brief pause between sessions (avoid rate limits)
        log_info "⏳ Cooling down for 5 seconds..."
        sleep 5
    done

    # Loop ended (budget or manual stop)
    save_checkpoint "complete"
    update_status_file "Complete" "Loop finished"

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ✅ ${BOLD}MISSION LOOP COMPLETE${NC} - Pane $PANE_ID                       ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Worker:${NC}          $WORKER_TYPE"
    echo -e "  ${BOLD}Mode:${NC}            $MODE"
    echo -e "  ${BOLD}Sessions:${NC}        $SESSION_NUMBER"
    echo -e "  ${BOLD}Completed:${NC}       ${GREEN}$SESSIONS_COMPLETED${NC}"
    echo -e "  ${BOLD}Failed:${NC}          ${RED}$SESSIONS_FAILED${NC}"
    echo -e "  ${BOLD}Files Created:${NC}   $TOTAL_FILES_CREATED"
    echo ""
    echo -e "  ${BOLD}>>> Token Usage${NC}"
    echo -e "  ${BOLD}Input:${NC}           $TOTAL_INPUT_TOKENS"
    echo -e "  ${BOLD}Output:${NC}          $TOTAL_OUTPUT_TOKENS"
    if command -v bc &> /dev/null; then
        local est_cost=$(echo "scale=4; ($TOTAL_INPUT_TOKENS * 0.000003) + ($TOTAL_OUTPUT_TOKENS * 0.000015)" | bc)
        echo -e "  ${BOLD}Est. Cost:${NC}       \$$est_cost"
    fi
    echo ""

    # Notify completion
    if [[ -f "$SCRIPT_DIR/notify.py" ]]; then
        python3 "$SCRIPT_DIR/notify.py" --event=all_complete --pane="$PANE_ID" \
            "Pane $PANE_ID completed $SESSION_NUMBER sessions" 2>/dev/null || true
    fi

    # Final markers for orchestrator
    echo "RALPH_MISSION_COMPLETE: pane-$PANE_ID"
    echo "SESSIONS: $SESSION_NUMBER"
    echo "WORKER: $WORKER_TYPE"
    echo "COMPLETED: $SESSIONS_COMPLETED"
    echo "FAILED: $SESSIONS_FAILED"
    echo "FILES_CREATED: $TOTAL_FILES_CREATED"
}

# -----------------------------------------------------------------------------
# Signal Handlers
# -----------------------------------------------------------------------------
cleanup() {
    log_warn "Received interrupt signal - saving checkpoint"
    save_checkpoint "interrupted"
    if [[ -f "$SCRIPT_DIR/notify.py" ]]; then
        python3 "$SCRIPT_DIR/notify.py" --event=error --pane="$PANE_ID" \
            "Pane $PANE_ID interrupted at session $SESSION_NUMBER" 2>/dev/null || true
    fi
    exit 130
}

trap cleanup SIGINT SIGTERM

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
main "$@"
