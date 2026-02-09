# QuantStream Quick Start

Autonomous multi-market strategy research factory. Discover, validate, and integrate profitable trading strategies overnight.

## Prerequisites

| Tool | Required? | Install |
|------|-----------|---------|
| Python 3.8+ | Yes | [python.org](https://python.org) |
| Claude CLI | Yes | `npm install -g @anthropic-ai/claude-code` |
| tmux | Yes | `brew install tmux` (macOS) / `apt install tmux` (Linux) |
| `ANTHROPIC_API_KEY` | Yes | [console.anthropic.com](https://console.anthropic.com) |
| ccxt (Python) | Optional | `pip install ccxt` (needed for crypto CEX) |
| requests (Python) | Optional | `pip install requests` (usually pre-installed) |

## Setup (5 minutes)

### 1. Clone and navigate

```bash
cd stream-quant
```

### 2. Copy environment file

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run the setup wizard

```bash
python scripts/quant-team/setup-wizard.py
```

The wizard walks you through:
1. **Market selection** - Futures, Crypto CEX, Crypto DEX, or multiple
2. **Exchange/provider** - Configure and validate your data source
3. **Symbol discovery** - Auto-fetch top symbols by volume, pin your favourites
4. **Mode** - Research (sample data) or Production (live feeds)
5. **Compliance** - Prop firm selection (futures) or risk limits (crypto)

### 4. Run health check

```bash
python scripts/quant-team/health-check.py
```

Fix any blockers (red). Warnings (yellow) are optional.

Auto-fix soft dependencies:
```bash
python scripts/quant-team/health-check.py --fix
```

### 5. Download data (optional)

```bash
# Download from your configured profile
python scripts/quant-team/download-data.py --from-profile

# Or download specific data
python scripts/quant-team/download-data.py --provider ccxt --exchange binance --symbol BTCUSDT --timeframe 5m --bars 5000
python scripts/quant-team/download-data.py --provider databento --symbol ES --timeframe 5m --bars 1000
python scripts/quant-team/download-data.py --provider hyperliquid --symbol BTC --timeframe 5m --bars 5000
```

### 6. Launch the team

```bash
./scripts/quant-team/spawn-quant-team.sh
```

### 7. Monitor

```bash
# Reattach to tmux session
tmux attach -t quant-team

# Quick status
./scripts/quant-team/quant-control.sh status
```

## tmux Controls

| Shortcut | Action |
|----------|--------|
| `Ctrl-b d` | Detach (keeps running in background) |
| `Ctrl-b [` | Scroll mode (`q` to exit) |
| `Ctrl-b arrow` | Navigate between panes |
| `Ctrl-b z` | Zoom/unzoom current pane |

## Switching Markets

```bash
# Switch to an existing profile
python scripts/quant-team/setup-wizard.py --profile crypto-cex

# Re-run full wizard
python scripts/quant-team/setup-wizard.py --reconfigure
```

## Available Profiles

| Profile | File | Market |
|---------|------|--------|
| Futures | `profiles/futures.json` | CME (ES, NQ, YM, GC) |
| Crypto CEX | `profiles/crypto-cex.json` | Binance, Bybit, OKX |
| Crypto DEX | `profiles/crypto-dex.json` | Hyperliquid |

## Output Locations

| What | Where |
|------|-------|
| Validated strategies | `output/strategies/prop_firm_ready/` |
| Good strategies | `output/strategies/good/` |
| Rejected | `output/strategies/rejected/` |
| Converted indicators | `output/indicators/converted/` |
| Research logs | `output/research-logs/` |
| Downloaded data | `data/{provider}/{symbol}_{timeframe}.csv` |

## Troubleshooting

### "ccxt not installed"
```bash
pip install ccxt
```

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Or add to stream-quant/.env
```

### "tmux session already exists"
```bash
# Reattach to existing session
tmux attach -t quant-team

# Or kill and restart
tmux kill-session -t quant-team
./scripts/quant-team/spawn-quant-team.sh
```

### "Databento API returned 4xx"
Your Databento key may be invalid or expired. The system falls back to sample data automatically. Check your key at [databento.com](https://databento.com).

### "No data downloaded"
- Futures: Requires `DATABENTO_API_KEY` or uses sample data
- Crypto CEX: Requires `ccxt` installed; no API key needed for market data
- Crypto DEX: Requires internet access to Hyperliquid API

### Health check shows warnings
Warnings are non-blocking. Run `health-check.py --fix` to auto-install soft dependencies.
