#!/usr/bin/env python3
"""
QuantStream Data Downloader
============================
Standalone data download utility for multiple providers.

Usage:
    python download-data.py --provider ccxt --exchange binance --symbol BTCUSDT --timeframe 5m --bars 5000
    python download-data.py --provider databento --symbol ES --timeframe 5m --bars 1000
    python download-data.py --provider hyperliquid --symbol BTC --timeframe 5m --bars 5000
    python download-data.py --from-profile  # Use active profile settings
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STREAM_QUANT = PROJECT_ROOT / "stream-quant"
DATA_DIR = STREAM_QUANT / "data"
ACTIVE_PROFILE = STREAM_QUANT / "profiles" / "active-profile.json"

# ---------------------------------------------------------------------------
# Terminal colours
# ---------------------------------------------------------------------------
class C:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    NC = "\033[0m"


def ok(msg: str):
    print(f"  {C.GREEN}\u2713{C.NC} {msg}")


def warn(msg: str):
    print(f"  {C.YELLOW}\u26a0{C.NC} {msg}")


def fail(msg: str):
    print(f"  {C.RED}\u2717{C.NC} {msg}")


def progress_bar(current: int, total: int, width: int = 40):
    """Print a simple progress bar without tqdm."""
    pct = current / total if total else 0
    filled = int(width * pct)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    sys.stdout.write(f"\r  [{bar}] {current}/{total} bars ({pct:.0%})")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# CCXT provider
# ---------------------------------------------------------------------------
TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def download_ccxt(exchange: str, symbol: str, timeframe: str, bars: int, api_key: str = "", secret: str = "") -> list[list]:
    """Download OHLCV data via CCXT with pagination."""
    try:
        import ccxt  # type: ignore
    except ImportError:
        fail("ccxt not installed. Run: pip install ccxt")
        sys.exit(1)

    cls = getattr(ccxt, exchange, None)
    if cls is None:
        fail(f"Unknown exchange: {exchange}")
        sys.exit(1)

    params: dict = {"enableRateLimit": True}
    if api_key:
        params["apiKey"] = api_key
        params["secret"] = secret

    ex = cls(params)
    ex.load_markets()

    # Normalise symbol
    if "/" not in symbol:
        symbol = symbol.replace("USDT", "/USDT").replace("USD", "/USD")
        if "/" not in symbol:
            symbol = f"{symbol}/USDT"

    if symbol not in ex.markets:
        fail(f"Symbol {symbol} not found on {exchange}")
        available = [s for s in ex.markets if "USDT" in s][:10]
        print(f"  {C.DIM}Available (sample): {', '.join(available)}{C.NC}")
        sys.exit(1)

    print(f"  {C.BLUE}Downloading {bars} bars of {symbol} {timeframe} from {exchange}...{C.NC}")

    all_bars: list = []
    batch_size = 1000
    since = None  # fetch most recent first, then page backwards

    # Calculate start time: bars * timeframe_ms ago from now
    tf_ms = TIMEFRAME_MS.get(timeframe, 300_000)
    now_ms = int(time.time() * 1000)
    since = now_ms - (bars * tf_ms)

    while len(all_bars) < bars:
        remaining = bars - len(all_bars)
        limit = min(batch_size, remaining)

        ohlcv = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        if not ohlcv:
            break

        all_bars.extend(ohlcv)
        progress_bar(len(all_bars), bars)

        # Move since forward past the last candle
        since = ohlcv[-1][0] + tf_ms

        if len(ohlcv) < limit:
            break  # No more data available

        # Rate limit courtesy
        time.sleep(ex.rateLimit / 1000)

    print()  # Newline after progress bar
    return all_bars[:bars]


# ---------------------------------------------------------------------------
# Hyperliquid provider
# ---------------------------------------------------------------------------
def download_hyperliquid(symbol: str, timeframe: str, bars: int) -> list[list]:
    """Download OHLCV from Hyperliquid public API."""
    try:
        import requests
    except ImportError:
        fail("requests not available")
        sys.exit(1)

    # Map timeframe to Hyperliquid interval
    hl_tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
    interval = hl_tf_map.get(timeframe, "5m")

    tf_ms = TIMEFRAME_MS.get(timeframe, 300_000)
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (bars * tf_ms)

    print(f"  {C.BLUE}Downloading {bars} bars of {symbol} {timeframe} from Hyperliquid...{C.NC}")

    all_bars: list = []
    batch_size = 5000
    since = start_ms

    while len(all_bars) < bars:
        resp = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={
                "type": "candleSnapshot",
                "req": {
                    "coin": symbol,
                    "interval": interval,
                    "startTime": since,
                    "endTime": now_ms,
                },
            },
            timeout=30,
        )

        if resp.status_code != 200:
            warn(f"API returned {resp.status_code}")
            break

        candles = resp.json()
        if not candles:
            break

        for c in candles:
            ts = c.get("t", c.get("T", 0))
            all_bars.append([
                ts,
                float(c.get("o", 0)),
                float(c.get("h", 0)),
                float(c.get("l", 0)),
                float(c.get("c", 0)),
                float(c.get("v", 0)),
            ])

        progress_bar(len(all_bars), bars)
        since = all_bars[-1][0] + tf_ms

        if len(candles) < batch_size:
            break

        time.sleep(0.5)

    print()
    return all_bars[:bars]


# ---------------------------------------------------------------------------
# Databento provider
# ---------------------------------------------------------------------------
def download_databento(symbol: str, timeframe: str, bars: int) -> list[list]:
    """Download OHLCV from Databento (requires API key)."""
    api_key = os.environ.get("DATABENTO_API_KEY", "")
    if not api_key:
        fail("DATABENTO_API_KEY not set. Export it or add to stream-quant/.env")
        print(f"  {C.DIM}Falling back to sample data if available.{C.NC}")
        return _load_sample_data(symbol, bars)

    # Cost preview
    _databento_cost_preview(api_key, symbol, timeframe, bars)

    try:
        import requests
    except ImportError:
        fail("requests not available")
        sys.exit(1)

    # Databento historical API
    tf_map = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1hour", "1d": "1day"}
    schema = f"ohlcv-{tf_map.get(timeframe, '5min')}"

    # Calculate date range from bar count
    tf_ms = TIMEFRAME_MS.get(timeframe, 300_000)
    end_dt = datetime.now(timezone.utc)
    start_dt = datetime.fromtimestamp(
        (end_dt.timestamp() * 1000 - bars * tf_ms) / 1000, tz=timezone.utc
    )

    dataset = "GLBX.MDP3"
    symbol_query = f"{symbol}.FUT" if "." not in symbol else symbol

    print(f"  {C.BLUE}Downloading {bars} bars of {symbol} {timeframe} from Databento...{C.NC}")
    print(f"  {C.DIM}Dataset: {dataset}, Schema: {schema}{C.NC}")
    print(f"  {C.DIM}Range: {start_dt.date()} to {end_dt.date()}{C.NC}")

    try:
        resp = requests.get(
            f"https://hist.databento.com/v0/timeseries.get_range",
            params={
                "dataset": dataset,
                "symbols": symbol_query,
                "schema": schema,
                "start": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "encoding": "json",
                "limit": bars,
            },
            auth=(api_key, ""),
            timeout=60,
            stream=True,
        )

        if resp.status_code != 200:
            warn(f"Databento API returned {resp.status_code}: {resp.text[:200]}")
            warn("Falling back to sample data")
            return _load_sample_data(symbol, bars)

        all_bars = []
        for line in resp.iter_lines():
            if not line:
                continue
            rec = json.loads(line)
            all_bars.append([
                rec.get("ts_event", 0) // 1_000_000,  # ns to ms
                float(rec.get("open", 0)) / 1e9,
                float(rec.get("high", 0)) / 1e9,
                float(rec.get("low", 0)) / 1e9,
                float(rec.get("close", 0)) / 1e9,
                int(rec.get("volume", 0)),
            ])
            if len(all_bars) % 100 == 0:
                progress_bar(len(all_bars), bars)

        print()
        return all_bars[:bars]

    except Exception as e:
        warn(f"Databento download failed: {e}")
        warn("Falling back to sample data")
        return _load_sample_data(symbol, bars)


def _databento_cost_preview(api_key: str, symbol: str, timeframe: str, bars: int):
    """Show estimated cost before downloading from Databento."""
    try:
        import requests
        tf_map = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1hour", "1d": "1day"}
        schema = f"ohlcv-{tf_map.get(timeframe, '5min')}"
        tf_ms = TIMEFRAME_MS.get(timeframe, 300_000)
        end_dt = datetime.now(timezone.utc)
        start_dt = datetime.fromtimestamp(
            (end_dt.timestamp() * 1000 - bars * tf_ms) / 1000, tz=timezone.utc
        )

        resp = requests.get(
            "https://hist.databento.com/v0/metadata.get_cost",
            params={
                "dataset": "GLBX.MDP3",
                "symbols": f"{symbol}.FUT",
                "schema": schema,
                "start": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            auth=(api_key, ""),
            timeout=10,
        )
        if resp.status_code == 200:
            cost = resp.json()
            dollars = cost / 100 if isinstance(cost, (int, float)) else 0
            if dollars > 0:
                print(f"  {C.YELLOW}Estimated cost: ${dollars:.2f}{C.NC}")
    except Exception:
        pass  # Cost preview is best-effort


def _load_sample_data(symbol: str, bars: int) -> list[list]:
    """Load from sample CSV files as fallback."""
    candidates = [
        DATA_DIR / f"{symbol}_5min_sample.csv",
        DATA_DIR / f"{symbol.upper()}_5min_sample.csv",
    ]
    for path in candidates:
        if path.exists():
            ok(f"Loading sample data from {path.name}")
            all_bars = []
            with open(path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        ts_str = row.get("timestamp", "")
                        ts = int(datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp() * 1000)
                    except (ValueError, TypeError):
                        ts = 0
                    all_bars.append([
                        ts,
                        float(row.get("open", 0)),
                        float(row.get("high", 0)),
                        float(row.get("low", 0)),
                        float(row.get("close", 0)),
                        int(float(row.get("volume", 0))),
                    ])
            return all_bars[:bars]

    warn(f"No sample data found for {symbol}")
    return []


# ---------------------------------------------------------------------------
# Save to CSV
# ---------------------------------------------------------------------------
def save_csv(bars: list[list], provider: str, symbol: str, timeframe: str):
    """Save OHLCV bars to CSV. Merges with existing data if present."""
    out_dir = DATA_DIR / provider
    out_dir.mkdir(parents=True, exist_ok=True)

    clean_symbol = symbol.replace("/", "")
    filename = f"{clean_symbol}_{timeframe}.csv"
    filepath = out_dir / filename

    # Load existing data for idempotent merge
    existing_ts: set = set()
    existing_rows: list = []
    if filepath.exists():
        with open(filepath) as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row:
                    existing_ts.add(row[0])
                    existing_rows.append(row)

    # Merge new bars
    new_count = 0
    for bar in bars:
        ts_iso = datetime.fromtimestamp(bar[0] / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        if ts_iso not in existing_ts:
            existing_rows.append([
                ts_iso,
                f"{bar[1]:.6f}",
                f"{bar[2]:.6f}",
                f"{bar[3]:.6f}",
                f"{bar[4]:.6f}",
                str(int(bar[5])),
            ])
            new_count += 1

    # Sort by timestamp
    existing_rows.sort(key=lambda r: r[0])

    # Write
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        writer.writerows(existing_rows)

    total = len(existing_rows)
    ok(f"Saved {filepath.relative_to(PROJECT_ROOT)} ({total} bars total, {new_count} new)")


# ---------------------------------------------------------------------------
# Profile-based download
# ---------------------------------------------------------------------------
def download_from_profile():
    """Download data for all pinned symbols in the active profile."""
    if not ACTIVE_PROFILE.exists():
        fail("No active profile found. Run setup-wizard.py first.")
        sys.exit(1)

    with open(ACTIVE_PROFILE) as f:
        profile = json.load(f)

    provider = profile.get("dataProvider", {})
    adapter = provider.get("adapter", "")
    exchange = provider.get("exchange", "")
    symbols = profile.get("symbols", {}).get("pinned", [])

    if not symbols:
        warn("No pinned symbols in profile")
        return

    print(f"\n  {C.BOLD}Downloading data for {len(symbols)} symbols...{C.NC}")
    print(f"  {C.DIM}Provider: {adapter}, Exchange: {exchange or 'N/A'}{C.NC}\n")

    for symbol in symbols:
        try:
            if adapter == "ccxt":
                bars = download_ccxt(exchange, symbol, "5m", 5000)
                save_csv(bars, "ccxt", symbol, "5m")
            elif adapter == "databento":
                bars = download_databento(symbol, "5m", 1000)
                save_csv(bars, "databento", symbol, "5m")
            elif adapter == "hyperliquid":
                bars = download_hyperliquid(symbol, "5m", 5000)
                save_csv(bars, "hyperliquid", symbol, "5m")
        except Exception as e:
            warn(f"Failed to download {symbol}: {e}")

    print(f"\n  {C.GREEN}\u2713 Download complete{C.NC}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="QuantStream Data Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download-data.py --provider ccxt --exchange binance --symbol BTCUSDT --timeframe 5m --bars 5000
  python download-data.py --provider databento --symbol ES --timeframe 5m --bars 1000
  python download-data.py --provider hyperliquid --symbol BTC --timeframe 5m --bars 5000
  python download-data.py --from-profile
        """,
    )
    parser.add_argument("--provider", choices=["ccxt", "databento", "hyperliquid"], help="Data provider")
    parser.add_argument("--exchange", default="binance", help="Exchange for CCXT (default: binance)")
    parser.add_argument("--symbol", help="Trading symbol (e.g., BTCUSDT, ES, BTC)")
    parser.add_argument("--timeframe", default="5m", choices=["1m", "5m", "15m", "1h", "4h", "1d"], help="Bar timeframe (default: 5m)")
    parser.add_argument("--bars", type=int, default=5000, help="Number of bars to download (default: 5000)")
    parser.add_argument("--from-profile", action="store_true", help="Download for all symbols in active profile")
    args = parser.parse_args()

    print(f"\n{C.CYAN}{C.BOLD}  QuantStream Data Downloader{C.NC}\n")

    if args.from_profile:
        download_from_profile()
        return

    if not args.provider or not args.symbol:
        parser.print_help()
        print(f"\n  {C.YELLOW}Tip: Use --from-profile to download based on your active profile.{C.NC}")
        sys.exit(1)

    # Download
    bars: list = []
    if args.provider == "ccxt":
        api_key = os.environ.get(f"{args.exchange.upper()}_API_KEY", "")
        secret = os.environ.get(f"{args.exchange.upper()}_SECRET", "")
        bars = download_ccxt(args.exchange, args.symbol, args.timeframe, args.bars, api_key, secret)
    elif args.provider == "databento":
        bars = download_databento(args.symbol, args.timeframe, args.bars)
    elif args.provider == "hyperliquid":
        bars = download_hyperliquid(args.symbol, args.timeframe, args.bars)

    if bars:
        save_csv(bars, args.provider, args.symbol, args.timeframe)
    else:
        fail("No data downloaded")
        sys.exit(1)


if __name__ == "__main__":
    main()
