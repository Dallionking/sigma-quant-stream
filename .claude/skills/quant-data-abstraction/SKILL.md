---
name: quant-data-abstraction
description: "Unified data interface across Databento, CCXT, and Hyperliquid providers"
version: "1.0.0"
triggers:
  - "when fetching market data from multiple providers"
  - "when implementing data adapters"
  - "when switching between Databento and CCXT"
  - "when building provider-agnostic data pipelines"
---

# Quant Data Abstraction

## Purpose

Provides a unified interface for fetching OHLCV and orderbook data from three providers: Databento (futures), CCXT (crypto CEX), and Hyperliquid (crypto DEX). Strategy code should never import provider-specific libraries directly — always go through the abstraction layer.

## When to Use

- When building strategies that work across futures and crypto
- When implementing data fetching for backtests
- When adding a new data provider
- When profile.dataProvider changes require adapter dispatch

## Common DataFrame Schema

All providers must normalize to this schema:

```python
CANONICAL_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

# timestamp: pd.Timestamp (UTC, tz-aware)
# open/high/low/close: float64
# volume: float64 (base currency units for crypto, contracts for futures)
```

## Provider Adapters

### Abstract Base

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal
import pandas as pd

@dataclass
class DataRequest:
    """Unified data request across all providers."""
    symbol: str          # Canonical: "BTC/USDT", "ES", "NQ"
    timeframe: str       # "1m", "5m", "15m", "1h", "4h", "1d"
    bars: int            # Number of bars to fetch
    provider: Literal["databento", "ccxt", "hyperliquid"]
    exchange: str = ""   # For CCXT: "binance", "bybit", "okx"

class DataAdapter(ABC):
    """Abstract data adapter. All providers implement this."""

    @abstractmethod
    async def fetch_ohlcv(self, request: DataRequest) -> pd.DataFrame:
        """
        Fetch OHLCV data.
        Returns DataFrame with CANONICAL_COLUMNS, indexed by timestamp.
        """
        ...

    @abstractmethod
    async def fetch_orderbook(
        self, symbol: str, depth: int = 20
    ) -> dict:
        """
        Fetch current orderbook.
        Returns: {"bids": [[price, size], ...], "asks": [[price, size], ...]}
        """
        ...

    @abstractmethod
    async def fetch_funding_rate(self, symbol: str) -> float:
        """Fetch current funding rate (crypto only, raises for futures)."""
        ...

    def normalize_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure canonical schema."""
        df = df[CANONICAL_COLUMNS].copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df = df.set_index('timestamp').sort_index()
        df = df.astype({c: 'float64' for c in df.columns})
        return df
```

### Databento Adapter (Futures)

```python
import databento as db

class DatabentoAdapter(DataAdapter):
    """Databento adapter for CME/CBOT/NYMEX futures."""

    TIMEFRAME_MAP = {
        "1m": "1min", "5m": "5min", "15m": "15min",
        "1h": "1hour", "4h": "4hour", "1d": "1day"
    }
    SYMBOL_MAP = {
        "ES": "ES.FUT", "NQ": "NQ.FUT",
        "YM": "YM.FUT", "GC": "GC.FUT", "CL": "CL.FUT"
    }

    def __init__(self, api_key: str):
        self.client = db.Historical(api_key)

    async def fetch_ohlcv(self, request: DataRequest) -> pd.DataFrame:
        symbol = self.SYMBOL_MAP.get(request.symbol, request.symbol)
        schema = f"ohlcv-{self.TIMEFRAME_MAP[request.timeframe]}"

        # CRITICAL: Use bars count, never hardcoded dates
        data = self.client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=[symbol],
            schema=schema,
            limit=request.bars
        )
        df = data.to_df()
        df = df.rename(columns={
            "ts_event": "timestamp",
        })
        return self.normalize_df(df)

    async def fetch_orderbook(self, symbol: str, depth: int = 20) -> dict:
        raise NotImplementedError("Use live stream for Databento orderbook")

    async def fetch_funding_rate(self, symbol: str) -> float:
        raise NotImplementedError("Futures do not have funding rates")
```

### CCXT Adapter (Crypto CEX)

```python
import ccxt.async_support as ccxt

class CCXTAdapter(DataAdapter):
    """CCXT adapter for 100+ crypto exchanges."""

    TIMEFRAME_MAP = {
        "1m": "1m", "5m": "5m", "15m": "15m",
        "1h": "1h", "4h": "4h", "1d": "1d"
    }

    def __init__(self, exchange_id: str, api_key: str = "", secret: str = ""):
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,  # CRITICAL: respect rate limits
        })

    async def fetch_ohlcv(self, request: DataRequest) -> pd.DataFrame:
        timeframe = self.TIMEFRAME_MAP[request.timeframe]
        all_candles = []
        remaining = request.bars
        since = None

        # Paginate — most exchanges cap at 500-1000 candles per request
        while remaining > 0:
            limit = min(remaining, 500)
            candles = await self.exchange.fetch_ohlcv(
                request.symbol, timeframe, since=since, limit=limit
            )
            if not candles:
                break
            all_candles.extend(candles)
            remaining -= len(candles)
            since = candles[-1][0] + 1  # Next ms after last candle

        df = pd.DataFrame(
            all_candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return self.normalize_df(df)

    async def fetch_orderbook(self, symbol: str, depth: int = 20) -> dict:
        book = await self.exchange.fetch_order_book(symbol, limit=depth)
        return {"bids": book["bids"], "asks": book["asks"]}

    async def fetch_funding_rate(self, symbol: str) -> float:
        funding = await self.exchange.fetch_funding_rate(symbol)
        return funding["fundingRate"]

    async def close(self):
        await self.exchange.close()
```

### Hyperliquid Adapter (Crypto DEX)

```python
from hyperliquid.info import Info
from hyperliquid.utils import constants

class HyperliquidAdapter(DataAdapter):
    """Hyperliquid on-chain CLOB adapter."""

    TIMEFRAME_MAP = {
        "1m": "1m", "5m": "5m", "15m": "15m",
        "1h": "1h", "4h": "4h", "1d": "1d"
    }

    def __init__(self, testnet: bool = False):
        base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        self.info = Info(base_url, skip_ws=True)

    async def fetch_ohlcv(self, request: DataRequest) -> pd.DataFrame:
        # Hyperliquid uses coin name without /USDC suffix
        coin = request.symbol.split("/")[0] if "/" in request.symbol else request.symbol
        interval = self.TIMEFRAME_MAP[request.timeframe]

        # candles_snapshot returns most recent N candles
        candles = self.info.candles_snapshot(
            coin=coin,
            interval=interval,
            n=request.bars
        )
        df = pd.DataFrame(candles)
        df = df.rename(columns={
            "t": "timestamp", "o": "open", "h": "high",
            "l": "low", "c": "close", "v": "volume"
        })
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return self.normalize_df(df)

    async def fetch_orderbook(self, symbol: str, depth: int = 20) -> dict:
        coin = symbol.split("/")[0] if "/" in symbol else symbol
        book = self.info.l2_snapshot(coin)
        return {
            "bids": [[float(p), float(s)] for p, s in book["levels"][0][:depth]],
            "asks": [[float(p), float(s)] for p, s in book["levels"][1][:depth]]
        }

    async def fetch_funding_rate(self, symbol: str) -> float:
        coin = symbol.split("/")[0] if "/" in symbol else symbol
        meta = self.info.meta_and_asset_ctxs()
        for ctx in meta[1]:
            if ctx["coin"] == coin:
                return float(ctx["funding"])
        raise ValueError(f"Funding rate not found for {coin}")
```

## Provider Dispatch

```python
async def get_adapter(profile: dict) -> DataAdapter:
    """
    Dispatch to correct adapter based on trading profile.
    Profile comes from TradingProfile model.
    """
    provider = profile["dataProvider"]["adapter"]

    if provider == "databento":
        return DatabentoAdapter(api_key=profile["dataProvider"]["apiKey"])
    elif provider == "ccxt":
        return CCXTAdapter(
            exchange_id=profile["dataProvider"]["exchange"],
            api_key=profile["dataProvider"].get("apiKey", ""),
            secret=profile["dataProvider"].get("secret", "")
        )
    elif provider == "hyperliquid":
        testnet = profile["dataProvider"].get("testnet", False)
        return HyperliquidAdapter(testnet=testnet)
    else:
        raise ValueError(f"Unknown data provider: {provider}")
```

## Common Pitfalls

1. **CCXT rate limits** — Always set `enableRateLimit: True`. Binance = 1200 req/min.
2. **Databento bar counts** — NEVER hardcode dates. Use `limit=N` parameter.
3. **Hyperliquid no auth for data** — Only trading requires wallet signature.
4. **Timezone normalization** — Always convert to UTC before returning.
5. **Volume units differ** — Databento = contracts, CCXT = base currency, Hyperliquid = USD notional.
6. **Pagination required** — CCXT exchanges cap candles per request (typically 500-1000).

## Related Skills

- `quant-crypto-indicators` — Indicators computed on this data
- `quant-cost-modeling` — Cost model dispatch by provider type
- `quant-hyperliquid-adapter` — Deeper Hyperliquid patterns
