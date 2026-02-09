"""
Unified crypto exchange adapters for the quant pipeline.

Wraps CCXT (Binance, Bybit, OKX) and a native Hyperliquid SDK pattern
behind a single interface so the rest of the codebase never touches
raw exchange APIs.

All symbols use CCXT perpetual format: "BTC/USDT:USDT"

API keys are loaded exclusively from environment variables -- never
hardcoded.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy CCXT import -- allow module to load even when ccxt is not installed
# (e.g. during lightweight test collection).
# ---------------------------------------------------------------------------
try:
    import ccxt.async_support as ccxt_async  # type: ignore[import-untyped]

    CCXT_AVAILABLE = True
except ImportError:  # pragma: no cover
    ccxt_async = None  # type: ignore[assignment]
    CCXT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TickerData:
    """Snapshot ticker for a single symbol on a single exchange."""

    symbol: str
    exchange: str
    bid: float
    ask: float
    last: float
    volume_24h: float
    open_interest: Optional[float]
    timestamp: float


@dataclass(frozen=True)
class FundingRateData:
    """8-hour funding rate for a perpetual contract."""

    symbol: str
    exchange: str
    rate_8h: float
    next_settlement: float  # unix timestamp
    annualized: float


@dataclass(frozen=True)
class OHLCVBar:
    """Single OHLCV candle."""

    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Simple circuit-breaker for exchange API calls.

    After ``failure_threshold`` consecutive failures the circuit *opens*
    and all calls are rejected for ``recovery_timeout`` seconds.  After
    that window one probe call is allowed (half-open).  If it succeeds
    the circuit closes; if it fails the circuit reopens.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPEN after %d failures (recovery in %.0fs)",
                self._failure_count,
                self.recovery_timeout,
            )

    def allow_request(self) -> bool:
        return self.state != CircuitState.OPEN


class ExchangeUnavailableError(Exception):
    """Raised when the circuit breaker is open."""


# ---------------------------------------------------------------------------
# CryptoExchangeAdapter -- wraps a single CCXT exchange
# ---------------------------------------------------------------------------


class CryptoExchangeAdapter:
    """Base adapter wrapping CCXT async for a single CEX.

    Supported exchange IDs: ``binance``, ``bybit``, ``okx``.
    """

    def __init__(
        self,
        exchange_id: str,
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",
        testnet: bool = False,
    ) -> None:
        if not CCXT_AVAILABLE:
            raise ImportError(
                "ccxt is required for CryptoExchangeAdapter. "
                "Install with: pip install 'ccxt>=5.0.0'"
            )

        self.exchange_id = exchange_id

        # Resolve credentials from env when not supplied explicitly.
        prefix = exchange_id.upper()
        resolved_key = api_key or os.environ.get(f"{prefix}_API_KEY", "")
        resolved_secret = api_secret or os.environ.get(f"{prefix}_API_SECRET", "")
        resolved_pass = passphrase or os.environ.get(f"{prefix}_PASSPHRASE", "")

        exchange_class = getattr(ccxt_async, exchange_id, None)
        if exchange_class is None:
            raise ValueError(f"Unsupported exchange: {exchange_id}")

        config: dict[str, Any] = {
            "apiKey": resolved_key,
            "secret": resolved_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        }
        if resolved_pass:
            config["password"] = resolved_pass
        if testnet:
            config["sandbox"] = True

        self._exchange: Any = exchange_class(config)
        self._breaker = CircuitBreaker()

    # -- helpers ------------------------------------------------------------

    async def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a CCXT method with circuit-breaker and logging."""
        if not self._breaker.allow_request():
            raise ExchangeUnavailableError(
                f"{self.exchange_id} circuit breaker is OPEN"
            )
        logger.debug(
            "CCXT call %s.%s args=%s kwargs=%s",
            self.exchange_id,
            method,
            args,
            kwargs,
        )
        try:
            result = await getattr(self._exchange, method)(*args, **kwargs)
            self._breaker.record_success()
            return result
        except Exception:
            self._breaker.record_failure()
            raise

    # -- public API ---------------------------------------------------------

    async def get_ticker(self, symbol: str) -> TickerData:
        """Fetch the latest ticker for *symbol*.

        Args:
            symbol: CCXT unified symbol, e.g. ``"BTC/USDT:USDT"``.

        Returns:
            A ``TickerData`` snapshot.
        """
        raw: dict[str, Any] = await self._call("fetch_ticker", symbol)
        return TickerData(
            symbol=symbol,
            exchange=self.exchange_id,
            bid=float(raw.get("bid") or 0),
            ask=float(raw.get("ask") or 0),
            last=float(raw.get("last") or 0),
            volume_24h=float(raw.get("quoteVolume") or raw.get("baseVolume") or 0),
            open_interest=None,  # populated separately if needed
            timestamp=float(raw.get("timestamp") or time.time() * 1000),
        )

    async def get_orderbook(self, symbol: str, depth: int = 20) -> dict[str, Any]:
        """Fetch the L2 order-book up to *depth* levels.

        Returns a dict with keys ``"bids"``, ``"asks"``, ``"timestamp"``,
        and ``"nonce"``.
        """
        raw: dict[str, Any] = await self._call(
            "fetch_order_book", symbol, depth
        )
        return {
            "bids": raw.get("bids", []),
            "asks": raw.get("asks", []),
            "timestamp": raw.get("timestamp"),
            "nonce": raw.get("nonce"),
        }

    async def get_funding_rate(self, symbol: str) -> FundingRateData:
        """Fetch the current funding rate for a perpetual *symbol*."""
        raw: dict[str, Any] = await self._call("fetch_funding_rate", symbol)
        rate_8h = float(raw.get("fundingRate") or 0)
        next_ts = float(raw.get("fundingDatetime") or raw.get("nextFundingDatetime") or 0)
        if isinstance(next_ts, str):
            # Some exchanges return ISO string; keep as-is for downstream.
            next_ts = 0.0
        annualized = rate_8h * 3 * 365  # 3 settlements/day * 365 days
        return FundingRateData(
            symbol=symbol,
            exchange=self.exchange_id,
            rate_8h=rate_8h,
            next_settlement=next_ts,
            annualized=annualized,
        )

    async def get_funding_history(
        self,
        symbol: str,
        since: Optional[int] = None,
        limit: int = 500,
    ) -> list[FundingRateData]:
        """Fetch historical funding-rate records.

        Args:
            symbol: CCXT unified symbol.
            since:  Start timestamp in milliseconds (CCXT convention).
            limit:  Maximum records to return.
        """
        raw_list: list[dict[str, Any]] = await self._call(
            "fetch_funding_rate_history", symbol, since, limit
        )
        results: list[FundingRateData] = []
        for entry in raw_list:
            rate_8h = float(entry.get("fundingRate") or 0)
            ts = float(entry.get("timestamp") or 0)
            results.append(
                FundingRateData(
                    symbol=symbol,
                    exchange=self.exchange_id,
                    rate_8h=rate_8h,
                    next_settlement=ts,
                    annualized=rate_8h * 3 * 365,
                )
            )
        return results

    async def get_open_interest(self, symbol: str) -> float:
        """Return the aggregate open interest in contracts for *symbol*."""
        raw: dict[str, Any] = await self._call("fetch_open_interest", symbol)
        return float(raw.get("openInterestAmount") or raw.get("openInterestValue") or 0)

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
    ) -> list[OHLCVBar]:
        """Fetch OHLCV candles.

        Args:
            symbol:    CCXT unified symbol.
            timeframe: CCXT timeframe string (``"1m"``, ``"5m"``, ``"1h"``, etc.).
            limit:     Number of candles.
        """
        raw_list: list[list[float]] = await self._call(
            "fetch_ohlcv", symbol, timeframe, None, limit
        )
        return [
            OHLCVBar(
                timestamp=float(bar[0]),
                open=float(bar[1]),
                high=float(bar[2]),
                low=float(bar[3]),
                close=float(bar[4]),
                volume=float(bar[5]),
            )
            for bar in raw_list
        ]

    async def close(self) -> None:
        """Release the underlying CCXT exchange connection."""
        try:
            await self._exchange.close()
        except Exception:
            logger.debug("Error closing %s exchange connection", self.exchange_id, exc_info=True)


# ---------------------------------------------------------------------------
# HyperliquidAdapter -- native SDK (no CCXT)
# ---------------------------------------------------------------------------


class HyperliquidAdapter:
    """Native Hyperliquid L1 adapter.

    Hyperliquid is an on-chain DEX with a custom REST + WebSocket API.
    Authentication uses wallet signing rather than API key/secret.

    This adapter exposes the same interface as ``CryptoExchangeAdapter``
    so it can be used interchangeably in ``UnifiedCryptoClient``.
    """

    # Hyperliquid REST base URL
    BASE_URL = "https://api.hyperliquid.xyz"
    INFO_URL = f"{BASE_URL}/info"

    def __init__(
        self,
        wallet_address: str = "",
        **_kwargs: Any,
    ) -> None:
        self.exchange_id = "hyperliquid"
        self.wallet_address = wallet_address or os.environ.get(
            "HYPERLIQUID_WALLET_ADDRESS", ""
        )
        self._breaker = CircuitBreaker()

        # We use httpx for async HTTP calls -- imported lazily so the
        # module loads even if httpx is not installed.
        try:
            import httpx  # type: ignore[import-untyped]

            self._client = httpx.AsyncClient(timeout=30.0)
        except ImportError:  # pragma: no cover
            self._client = None  # type: ignore[assignment]

    async def _post(self, payload: dict[str, Any]) -> Any:
        """Issue a POST to the Hyperliquid info endpoint."""
        if self._client is None:
            raise ImportError("httpx is required for HyperliquidAdapter")
        if not self._breaker.allow_request():
            raise ExchangeUnavailableError(
                "hyperliquid circuit breaker is OPEN"
            )
        logger.debug("Hyperliquid POST %s", payload.get("type"))
        try:
            resp = await self._client.post(self.INFO_URL, json=payload)
            resp.raise_for_status()
            self._breaker.record_success()
            return resp.json()
        except Exception:
            self._breaker.record_failure()
            raise

    # -- Helpers to map Hyperliquid coin names to CCXT-style symbols --------

    @staticmethod
    def _coin_from_symbol(symbol: str) -> str:
        """Extract the base coin from ``"BTC/USDT:USDT"`` -> ``"BTC"``."""
        return symbol.split("/")[0]

    # -- Public API (same surface as CryptoExchangeAdapter) -----------------

    async def get_ticker(self, symbol: str) -> TickerData:
        """Fetch the latest mid-market tick from Hyperliquid."""
        coin = self._coin_from_symbol(symbol)
        metas_and_ctxs = await self._post({"type": "metaAndAssetCtxs"})
        # Response is [meta, [asset_ctx, ...]]
        if not isinstance(metas_and_ctxs, list) or len(metas_and_ctxs) < 2:
            raise ValueError("Unexpected Hyperliquid metaAndAssetCtxs response")

        meta = metas_and_ctxs[0]
        ctxs = metas_and_ctxs[1]
        universe = meta.get("universe", [])

        for idx, asset_meta in enumerate(universe):
            if asset_meta.get("name") == coin and idx < len(ctxs):
                ctx = ctxs[idx]
                mid = float(ctx.get("midPx") or ctx.get("markPx") or 0)
                return TickerData(
                    symbol=symbol,
                    exchange="hyperliquid",
                    bid=mid,  # Hyperliquid mid approximation
                    ask=mid,
                    last=mid,
                    volume_24h=float(ctx.get("dayNtlVlm") or 0),
                    open_interest=float(ctx.get("openInterest") or 0),
                    timestamp=time.time() * 1000,
                )

        raise ValueError(f"Coin {coin} not found on Hyperliquid")

    async def get_orderbook(self, symbol: str, depth: int = 20) -> dict[str, Any]:
        """Fetch L2 book from Hyperliquid."""
        coin = self._coin_from_symbol(symbol)
        raw = await self._post({"type": "l2Book", "coin": coin})
        levels = raw.get("levels", [[], []])
        bids = [[float(l["px"]), float(l["sz"])] for l in levels[0][:depth]]
        asks = [[float(l["px"]), float(l["sz"])] for l in levels[1][:depth]]
        return {
            "bids": bids,
            "asks": asks,
            "timestamp": time.time() * 1000,
            "nonce": None,
        }

    async def get_funding_rate(self, symbol: str) -> FundingRateData:
        """Fetch current funding rate for a perpetual on Hyperliquid."""
        coin = self._coin_from_symbol(symbol)
        metas_and_ctxs = await self._post({"type": "metaAndAssetCtxs"})
        meta = metas_and_ctxs[0]
        ctxs = metas_and_ctxs[1]
        universe = meta.get("universe", [])

        for idx, asset_meta in enumerate(universe):
            if asset_meta.get("name") == coin and idx < len(ctxs):
                ctx = ctxs[idx]
                rate_hourly = float(ctx.get("funding") or 0)
                rate_8h = rate_hourly * 8
                return FundingRateData(
                    symbol=symbol,
                    exchange="hyperliquid",
                    rate_8h=rate_8h,
                    next_settlement=0.0,
                    annualized=rate_8h * 3 * 365,
                )

        raise ValueError(f"Coin {coin} not found on Hyperliquid")

    async def get_funding_history(
        self,
        symbol: str,
        since: Optional[int] = None,
        limit: int = 500,
    ) -> list[FundingRateData]:
        """Fetch historical funding on Hyperliquid.

        The Hyperliquid info API exposes ``"fundingHistory"`` per coin.
        """
        coin = self._coin_from_symbol(symbol)
        payload: dict[str, Any] = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": since or 0,
        }
        raw_list: list[dict[str, Any]] = await self._post(payload)
        results: list[FundingRateData] = []
        for entry in raw_list[:limit]:
            rate = float(entry.get("fundingRate") or 0)
            ts = float(entry.get("time") or 0)
            results.append(
                FundingRateData(
                    symbol=symbol,
                    exchange="hyperliquid",
                    rate_8h=rate,
                    next_settlement=ts,
                    annualized=rate * 3 * 365,
                )
            )
        return results

    async def get_open_interest(self, symbol: str) -> float:
        """Return aggregate open interest for *symbol* on Hyperliquid."""
        coin = self._coin_from_symbol(symbol)
        metas_and_ctxs = await self._post({"type": "metaAndAssetCtxs"})
        meta = metas_and_ctxs[0]
        ctxs = metas_and_ctxs[1]
        universe = meta.get("universe", [])

        for idx, asset_meta in enumerate(universe):
            if asset_meta.get("name") == coin and idx < len(ctxs):
                return float(ctxs[idx].get("openInterest") or 0)

        raise ValueError(f"Coin {coin} not found on Hyperliquid")

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
    ) -> list[OHLCVBar]:
        """Fetch OHLCV candles from Hyperliquid.

        Hyperliquid uses ``"candleSnapshot"`` with interval strings like
        ``"1m"``, ``"5m"``, ``"1h"``, ``"4h"``, ``"1d"``.
        """
        coin = self._coin_from_symbol(symbol)
        # Hyperliquid expects endTime as current ms and computes back.
        now_ms = int(time.time() * 1000)
        # Rough estimation: duration per candle in ms.
        _interval_ms_map: dict[str, int] = {
            "1m": 60_000,
            "5m": 300_000,
            "15m": 900_000,
            "1h": 3_600_000,
            "4h": 14_400_000,
            "1d": 86_400_000,
        }
        interval_ms = _interval_ms_map.get(timeframe, 3_600_000)
        start_ms = now_ms - (limit * interval_ms)

        payload: dict[str, Any] = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": timeframe,
                "startTime": start_ms,
                "endTime": now_ms,
            },
        }
        raw_list: list[dict[str, Any]] = await self._post(payload)
        bars: list[OHLCVBar] = []
        for candle in raw_list[-limit:]:
            bars.append(
                OHLCVBar(
                    timestamp=float(candle.get("t") or candle.get("T") or 0),
                    open=float(candle.get("o") or 0),
                    high=float(candle.get("h") or 0),
                    low=float(candle.get("l") or 0),
                    close=float(candle.get("c") or 0),
                    volume=float(candle.get("v") or 0),
                )
            )
        return bars

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class CryptoExchangeFactory:
    """Factory for creating exchange adapters."""

    SUPPORTED: frozenset[str] = frozenset({"binance", "bybit", "okx", "hyperliquid"})

    @staticmethod
    def create(
        exchange_id: str,
        **kwargs: Any,
    ) -> CryptoExchangeAdapter | HyperliquidAdapter:
        """Instantiate the correct adapter for *exchange_id*.

        Raises ``ValueError`` if the exchange is not supported.
        """
        if exchange_id not in CryptoExchangeFactory.SUPPORTED:
            raise ValueError(
                f"Unsupported exchange '{exchange_id}'. "
                f"Supported: {sorted(CryptoExchangeFactory.SUPPORTED)}"
            )
        if exchange_id == "hyperliquid":
            return HyperliquidAdapter(**kwargs)
        return CryptoExchangeAdapter(exchange_id, **kwargs)


# ---------------------------------------------------------------------------
# UnifiedCryptoClient -- single interface across all exchanges
# ---------------------------------------------------------------------------


class UnifiedCryptoClient:
    """Single interface across all configured exchanges.

    Example::

        client = UnifiedCryptoClient({
            "binance": CryptoExchangeFactory.create("binance"),
            "bybit": CryptoExchangeFactory.create("bybit"),
        })
        best = await client.get_best_price("BTC/USDT:USDT")
        spreads = await client.get_cross_exchange_spread("ETH/USDT:USDT")
        await client.close_all()
    """

    def __init__(
        self,
        exchanges: dict[str, CryptoExchangeAdapter | HyperliquidAdapter],
    ) -> None:
        self.exchanges = exchanges

    async def get_best_price(self, symbol: str) -> dict[str, Any]:
        """Find the best bid/ask across all exchanges for *symbol*.

        Returns a dict with ``"best_bid"``, ``"best_ask"``, ``"best_bid_exchange"``,
        ``"best_ask_exchange"``, and ``"tickers"`` (per-exchange).
        """
        tasks = {
            name: adapter.get_ticker(symbol)
            for name, adapter in self.exchanges.items()
        }
        results: dict[str, TickerData] = {}
        for name, coro in tasks.items():
            try:
                results[name] = await coro
            except Exception:
                logger.warning("Failed to get ticker from %s for %s", name, symbol, exc_info=True)

        if not results:
            return {
                "best_bid": 0.0,
                "best_ask": 0.0,
                "best_bid_exchange": "",
                "best_ask_exchange": "",
                "tickers": {},
            }

        best_bid_exchange = max(results, key=lambda n: results[n].bid)
        best_ask_exchange = min(results, key=lambda n: results[n].ask if results[n].ask > 0 else float("inf"))

        return {
            "best_bid": results[best_bid_exchange].bid,
            "best_ask": results[best_ask_exchange].ask,
            "best_bid_exchange": best_bid_exchange,
            "best_ask_exchange": best_ask_exchange,
            "tickers": {name: ticker for name, ticker in results.items()},
        }

    async def get_funding_across_exchanges(
        self,
        symbol: str,
    ) -> dict[str, FundingRateData]:
        """Fetch funding rates for *symbol* from all exchanges.

        Returns a mapping of ``exchange_id -> FundingRateData``.
        """
        results: dict[str, FundingRateData] = {}
        for name, adapter in self.exchanges.items():
            try:
                results[name] = await adapter.get_funding_rate(symbol)
            except Exception:
                logger.warning(
                    "Failed to get funding rate from %s for %s",
                    name,
                    symbol,
                    exc_info=True,
                )
        return results

    async def get_cross_exchange_spread(self, symbol: str) -> dict[str, Any]:
        """Compute the cross-exchange spread for *symbol*.

        Useful for stat-arb and funding-arb strategies.

        Returns a dict containing the best bid/ask, the spread in
        absolute and basis-point terms, and per-exchange tickers.
        """
        best = await self.get_best_price(symbol)
        best_bid = best["best_bid"]
        best_ask = best["best_ask"]
        spread_abs = best_bid - best_ask  # positive => arb opportunity
        mid = (best_bid + best_ask) / 2 if (best_bid + best_ask) > 0 else 1
        spread_bps = (spread_abs / mid) * 10_000

        return {
            "symbol": symbol,
            "best_bid": best_bid,
            "best_bid_exchange": best["best_bid_exchange"],
            "best_ask": best_ask,
            "best_ask_exchange": best["best_ask_exchange"],
            "spread_abs": spread_abs,
            "spread_bps": round(spread_bps, 2),
            "tickers": best["tickers"],
        }

    async def close_all(self) -> None:
        """Close all exchange connections."""
        close_tasks = [adapter.close() for adapter in self.exchanges.values()]
        await asyncio.gather(*close_tasks, return_exceptions=True)
