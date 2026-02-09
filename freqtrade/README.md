# Freqtrade Integration for QuantStream

Bridge between QuantStream-discovered strategies and the Freqtrade execution engine. Strategies validated by the Quant Research Team are converted into Freqtrade `IStrategy` classes and deployed for paper trading or live execution.

## What is Freqtrade?

[Freqtrade](https://www.freqtrade.io/) is an open-source cryptocurrency and futures trading bot written in Python. It provides:

- Backtesting with historical data
- Paper trading (dry-run mode) with simulated wallet
- Live trading against major exchanges via CCXT
- Hyperparameter optimisation (Hyperopt)
- Telegram and API-based monitoring

We use Freqtrade as the **execution layer** for QuantStream crypto strategies because it handles exchange connectivity, order management, and position tracking out of the box, letting us focus on signal generation.

## Installation

### Option A: pip (recommended for development)

```bash
# Create a virtualenv (keep it separate from the monorepo venv)
python -m venv ~/.venvs/freqtrade
source ~/.venvs/freqtrade/bin/activate

pip install freqtrade

# Verify installation
freqtrade --version
```

### Option B: Docker (recommended for deployment)

```bash
# Pull the stable image
docker pull freqtradeorg/freqtrade:stable

# Create user_data directory
docker run --rm -v ~/.freqtrade:/freqtrade/user_data \
  freqtradeorg/freqtrade:stable create-userdir --userdir /freqtrade/user_data
```

### Install pandas-ta (required by strategy template)

```bash
pip install pandas-ta
```

## Configuration

### 1. Copy the paper-trading config

```bash
cp stream-quant/freqtrade/config-paper.json ~/.freqtrade/config.json
```

### 2. Set exchange credentials

Edit `~/.freqtrade/config.json` and fill in the exchange section:

```json
{
  "exchange": {
    "name": "binance",
    "key": "YOUR_API_KEY",
    "secret": "YOUR_API_SECRET"
  }
}
```

For paper trading (`dry_run: true`), credentials are optional but recommended so that Freqtrade can fetch real-time orderbook data.

### 3. Configure pairs

Add a static pair list or use a dynamic volume filter:

```json
{
  "exchange": {
    "pair_whitelist": [
      "BTC/USDT:USDT",
      "ETH/USDT:USDT",
      "SOL/USDT:USDT"
    ]
  }
}
```

### 4. Telegram notifications (optional)

```json
{
  "telegram": {
    "enabled": true,
    "token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  }
}
```

## Deployment Flow

The end-to-end pipeline from QuantStream discovery to live execution:

```
1. QuantStream Researcher
   Discovers trading idea from papers, TradingView, or books

2. QuantStream Converter
   Translates PineScript / pseudocode to Python indicators

3. QuantStream Backtester
   Walk-forward validation on historical data (Databento or CCXT)

4. QuantStream Optimizer
   Hyperparameter tuning, Base Hit scoring

5. QuantStream Prop Firm Validator
   Tests against drawdown, daily loss, and consistency rules

6. Strategy Export
   Validated params written to stream-quant/output/strategies/good/

7. Freqtrade IStrategy Generation  <-- this integration
   strategy-template.py is populated with optimised params

8. Dry-Run Deployment
   freqtrade trade --strategy <Name> --config config-paper.json

9. Monitoring & Evaluation
   Track performance for N days before live deployment
```

### Quick deploy with the helper script

```bash
# Deploy a strategy for paper trading
./scripts/quant-team/freqtrade-deploy.sh stream-quant/output/strategies/good/my_strategy.py

# The script will:
#   - Validate Python syntax
#   - Copy to Freqtrade user_data/strategies/
#   - Generate config from active QuantStream profile
#   - Start Freqtrade in dry-run mode
#   - Tail the log
```

## Monitoring

### Check open trades

```bash
freqtrade show-trades --db-url sqlite:///~/.freqtrade/tradesv3.sqlite
```

### Check profit summary

```bash
freqtrade show-profit --db-url sqlite:///~/.freqtrade/tradesv3.sqlite
```

### API-based monitoring

Freqtrade exposes a REST API when started with `--api-server`:

```bash
freqtrade trade --strategy QuantStreamStrategy --config config-paper.json --api-server

# Default endpoint: http://localhost:8080/api/v1
# Endpoints:
#   GET /api/v1/status       - Open trades
#   GET /api/v1/profit       - Profit summary
#   GET /api/v1/balance      - Wallet balance
#   GET /api/v1/performance  - Per-pair performance
```

### FreqUI web dashboard

FreqUI is bundled with Freqtrade and provides a browser-based dashboard:

```bash
# Start with UI enabled
freqtrade trade --strategy QuantStreamStrategy --config config-paper.json \
  --api-server --api-server-config '{"enabled":true,"listen_ip_address":"0.0.0.0","listen_port":8080,"username":"sigma","password":"changeme"}'
```

Then open `http://localhost:8080` in a browser.

## Common Issues and Troubleshooting

### "No module named pandas_ta"

Install the dependency:

```bash
pip install pandas-ta
```

### "Exchange binance does not support futures trading"

Ensure the config has the correct trading mode:

```json
{
  "trading_mode": "futures",
  "margin_mode": "isolated"
}
```

And that pair names use the futures format with `:USDT` suffix: `BTC/USDT:USDT`.

### "Insufficient funds" in dry-run

Increase the simulated wallet:

```json
{
  "dry_run_wallet": 50000
}
```

### Strategy not found

Make sure the strategy file is in Freqtrade's `user_data/strategies/` directory and the class name matches what you pass to `--strategy`.

```bash
freqtrade list-strategies --userdir ~/.freqtrade
```

### Rate limiting errors from exchange

The config template already enables rate limiting. If you still hit limits, increase the delay:

```json
{
  "exchange": {
    "ccxt_config": {
      "enableRateLimit": true,
      "rateLimit": 200
    }
  }
}
```

### Backtest before dry-run

Always backtest a strategy before deploying it for paper trading:

```bash
freqtrade backtesting --strategy QuantStreamStrategy \
  --config config-paper.json \
  --timerange 20240101-20241231
```

## File Structure

```
stream-quant/freqtrade/
  config-paper.json          # Paper trading config template
  strategy-template.py       # IStrategy template with QuantStream hooks
  README.md                  # This file

scripts/quant-team/
  freqtrade-deploy.sh        # Automated deploy script
```

## Related Documentation

- [Freqtrade Documentation](https://www.freqtrade.io/en/stable/)
- [QuantStream CLAUDE.md](../CLAUDE.md) -- full quant team architecture
- [QuantStream Profiles](../profiles/) -- market profile configs
- [Prop Firm Validator](../../scripts/quant-team/prop-firm-validator.py)
