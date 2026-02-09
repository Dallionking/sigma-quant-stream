#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# freqtrade-deploy.sh
#
# Deploy a QuantStream strategy to Freqtrade for paper (dry-run) trading.
#
# Usage:
#   ./scripts/quant-team/freqtrade-deploy.sh <strategy_file> [--profile <name>]
#
# What it does:
#   1. Validates the strategy Python file (syntax check).
#   2. Copies it into the Freqtrade user_data/strategies/ directory.
#   3. Generates (or copies) a Freqtrade config from the active QuantStream
#      profile or the paper config template.
#   4. Starts Freqtrade in dry-run mode.
#   5. Tails the log so you can watch it live.
#
# Requirements:
#   - freqtrade installed and on PATH (or FREQTRADE_BIN set)
#   - Python 3.8+
# ---------------------------------------------------------------------------
set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
QUANT_DIR="$REPO_ROOT/stream-quant"
FREQTRADE_TEMPLATE="$QUANT_DIR/freqtrade/config-paper.json"
FREQTRADE_USER_DIR="${FREQTRADE_USER_DIR:-$HOME/.freqtrade}"
FREQTRADE_BIN="${FREQTRADE_BIN:-freqtrade}"
LOG_FILE="$FREQTRADE_USER_DIR/logs/freqtrade.log"

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }

cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        warn "Deploy script exited with code $exit_code"
    fi
    # Kill backgrounded Freqtrade if we started one
    if [[ -n "${FT_PID:-}" ]] && kill -0 "$FT_PID" 2>/dev/null; then
        info "Stopping Freqtrade (PID $FT_PID)..."
        kill "$FT_PID" 2>/dev/null || true
        wait "$FT_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

usage() {
    echo "Usage: $0 <strategy_file> [--profile <name>]"
    echo ""
    echo "Arguments:"
    echo "  strategy_file    Path to the Python strategy file to deploy"
    echo ""
    echo "Options:"
    echo "  --profile <name> QuantStream market profile (default: active profile)"
    echo "  --userdir <dir>  Freqtrade user_data directory (default: ~/.freqtrade)"
    echo "  --no-tail        Start Freqtrade but do not tail the log"
    echo "  -h, --help       Show this help message"
    exit 1
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
STRATEGY_FILE=""
PROFILE=""
NO_TAIL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --userdir)
            FREQTRADE_USER_DIR="$2"
            shift 2
            ;;
        --no-tail)
            NO_TAIL=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        -*)
            error "Unknown option: $1"
            usage
            ;;
        *)
            if [[ -z "$STRATEGY_FILE" ]]; then
                STRATEGY_FILE="$1"
            else
                error "Unexpected argument: $1"
                usage
            fi
            shift
            ;;
    esac
done

if [[ -z "$STRATEGY_FILE" ]]; then
    error "No strategy file provided."
    usage
fi

# ---------------------------------------------------------------------------
# Step 1: Validate strategy file exists and has valid Python syntax
# ---------------------------------------------------------------------------
info "Validating strategy file: $STRATEGY_FILE"

if [[ ! -f "$STRATEGY_FILE" ]]; then
    error "Strategy file not found: $STRATEGY_FILE"
    exit 1
fi

if ! python3 -c "
import ast, sys
try:
    with open(sys.argv[1], 'r') as f:
        ast.parse(f.read())
    print('Syntax OK')
except SyntaxError as e:
    print(f'Syntax Error: {e}', file=sys.stderr)
    sys.exit(1)
" "$STRATEGY_FILE"; then
    error "Strategy file has syntax errors. Fix them before deploying."
    exit 1
fi
ok "Syntax validation passed."

# Extract strategy class name from the file
STRATEGY_CLASS=$(python3 -c "
import ast, sys
with open(sys.argv[1], 'r') as f:
    tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        for base in node.bases:
            base_name = getattr(base, 'id', getattr(getattr(base, 'attr', None), '__str__', lambda: '')())
            if 'Strategy' in node.name or 'IStrategy' in str(getattr(base, 'id', '')):
                print(node.name)
                sys.exit(0)
# Fallback: first class
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        print(node.name)
        sys.exit(0)
print('')
" "$STRATEGY_FILE")

if [[ -z "$STRATEGY_CLASS" ]]; then
    error "Could not detect a strategy class in $STRATEGY_FILE"
    exit 1
fi
info "Detected strategy class: $STRATEGY_CLASS"

# ---------------------------------------------------------------------------
# Step 2: Ensure Freqtrade user_data directory exists
# ---------------------------------------------------------------------------
info "Freqtrade user directory: $FREQTRADE_USER_DIR"

mkdir -p "$FREQTRADE_USER_DIR/strategies"
mkdir -p "$FREQTRADE_USER_DIR/logs"

# ---------------------------------------------------------------------------
# Step 3: Copy strategy file
# ---------------------------------------------------------------------------
DEST="$FREQTRADE_USER_DIR/strategies/$(basename "$STRATEGY_FILE")"
cp "$STRATEGY_FILE" "$DEST"
ok "Copied strategy to $DEST"

# ---------------------------------------------------------------------------
# Step 4: Generate / copy config
# ---------------------------------------------------------------------------
CONFIG_DEST="$FREQTRADE_USER_DIR/config.json"

if [[ -n "$PROFILE" ]]; then
    PROFILE_FILE="$QUANT_DIR/profiles/$PROFILE.json"
    if [[ ! -f "$PROFILE_FILE" ]]; then
        warn "Profile '$PROFILE' not found at $PROFILE_FILE. Falling back to template."
        cp "$FREQTRADE_TEMPLATE" "$CONFIG_DEST"
    else
        info "Generating config from QuantStream profile: $PROFILE"
        # Use the template as base and overlay profile-specific values
        python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    config = json.load(f)

with open(sys.argv[2]) as f:
    profile = json.load(f)

# Map profile exchange to Freqtrade config
exchange_map = profile.get('dataProvider', {}).get('config', {})
if exchange_map.get('exchange'):
    config['exchange']['name'] = exchange_map['exchange']

# Map profile symbols to pair whitelist
symbols = profile.get('symbols', {}).get('pinned', [])
if symbols:
    fmt = profile.get('dataProvider', {}).get('pairFormat', '{symbol}/USDT:USDT')
    config['exchange']['pair_whitelist'] = [
        fmt.replace('{symbol}', s) for s in symbols
    ]

# Map profile timeframe
if profile.get('defaults', {}).get('timeframe'):
    config['timeframe'] = profile['defaults']['timeframe']

with open(sys.argv[3], 'w') as f:
    json.dump(config, f, indent=2)

print('Config generated with profile overrides.')
" "$FREQTRADE_TEMPLATE" "$PROFILE_FILE" "$CONFIG_DEST"
        ok "Config written to $CONFIG_DEST"
    fi
elif [[ -f "$QUANT_DIR/profiles/active-profile.json" ]]; then
    info "Using active QuantStream profile"
    # Re-run with the active profile name
    ACTIVE_NAME=$(python3 -c "
import json
with open('$QUANT_DIR/profiles/active-profile.json') as f:
    d = json.load(f)
print(d.get('name', d.get('profile', 'futures')))
" 2>/dev/null || echo "futures")
    PROFILE_FILE="$QUANT_DIR/profiles/$ACTIVE_NAME.json"
    if [[ -f "$PROFILE_FILE" ]]; then
        exec "$0" "$STRATEGY_FILE" --profile "$ACTIVE_NAME" --userdir "$FREQTRADE_USER_DIR" $([ "$NO_TAIL" = true ] && echo "--no-tail")
    else
        warn "Active profile file $PROFILE_FILE not found. Using template."
        cp "$FREQTRADE_TEMPLATE" "$CONFIG_DEST"
    fi
else
    info "No profile specified. Using paper-trading template."
    cp "$FREQTRADE_TEMPLATE" "$CONFIG_DEST"
fi

# ---------------------------------------------------------------------------
# Step 5: Check Freqtrade is installed
# ---------------------------------------------------------------------------
if ! command -v "$FREQTRADE_BIN" &>/dev/null; then
    error "Freqtrade not found on PATH."
    error "Install it: pip install freqtrade"
    error "Or set FREQTRADE_BIN to the path of the freqtrade binary."
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 6: Start Freqtrade in dry-run mode
# ---------------------------------------------------------------------------
info "Starting Freqtrade in dry-run mode..."
info "  Strategy: $STRATEGY_CLASS"
info "  Config:   $CONFIG_DEST"
info "  Log:      $LOG_FILE"

"$FREQTRADE_BIN" trade \
    --strategy "$STRATEGY_CLASS" \
    --config "$CONFIG_DEST" \
    --userdir "$FREQTRADE_USER_DIR" \
    --logfile "$LOG_FILE" \
    &
FT_PID=$!

ok "Freqtrade started (PID $FT_PID)"

# Give it a moment to initialise
sleep 3

# Check it is still running
if ! kill -0 "$FT_PID" 2>/dev/null; then
    error "Freqtrade exited immediately. Check the log:"
    tail -30 "$LOG_FILE" 2>/dev/null || true
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 7: Tail the log
# ---------------------------------------------------------------------------
if [[ "$NO_TAIL" = true ]]; then
    info "Freqtrade running in background. PID: $FT_PID"
    info "View logs: tail -f $LOG_FILE"
    # Detach: unset FT_PID so cleanup does not kill it
    FT_PID=""
    exit 0
fi

info "Tailing log (Ctrl+C to stop and shut down Freqtrade)..."
echo ""
tail -f "$LOG_FILE"
