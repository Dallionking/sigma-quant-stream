# Sample Market Data

This directory contains sample OHLCV data for local testing without requiring Databento API calls.

## Files

| File | Instrument | Timeframe | Rows | Period |
|------|------------|-----------|------|--------|
| `ES_5min_sample.csv` | E-mini S&P 500 | 5 minutes | 1000 | ~3 trading days |
| `NQ_5min_sample.csv` | E-mini Nasdaq | 5 minutes | 1000 | ~3 trading days |

## Format

All files use standard OHLCV format:
```csv
timestamp,open,high,low,close,volume
2024-01-15T09:30:00Z,4850.25,4852.00,4849.50,4851.75,12345
```

## Column Definitions

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | ISO 8601 | Bar open time in UTC |
| `open` | float | Opening price |
| `high` | float | Highest price in bar |
| `low` | float | Lowest price in bar |
| `close` | float | Closing price |
| `volume` | int | Number of contracts traded |

## Usage

### Python (pandas)
```python
import pandas as pd

df = pd.read_csv('stream-quant/data/ES_5min_sample.csv', parse_dates=['timestamp'])
df.set_index('timestamp', inplace=True)
```

### Backtesting Context
- Use for quick iteration during development
- Production backtests should use Databento for full historical data
- Sample data is synthetic but follows realistic price patterns

## Modes

The quant-ralph.sh script supports two modes:

| Mode | Data Source | Timeout | Budget Cap |
|------|-------------|---------|------------|
| `research` | These sample files | 30 min | $50 |
| `production` | Databento API | 60 min | $100 |

## Notes

- Sample data simulates typical ES/NQ futures behavior
- Includes realistic gaps, trends, and consolidation periods
- Volume patterns follow US market hours
- Not suitable for final strategy validation (use Databento)
