---
name: quant-hyperliquid-adapter
description: "Hyperliquid SDK patterns, on-chain CLOB specifics, vault interaction, and testnet/mainnet configuration"
version: "1.0.0"
tags:
  - crypto
  - hyperliquid
  - dex
  - on-chain
  - clob
  - sdk
triggers:
  - "when integrating with Hyperliquid"
  - "when building strategies for Hyperliquid"
  - "when fetching Hyperliquid market data"
  - "when placing orders on Hyperliquid"
---

# Quant Hyperliquid Adapter

## Purpose

Provides SDK patterns and domain knowledge for interacting with Hyperliquid, a fully on-chain central limit order book (CLOB) built on its own L1 (HyperEVM). Hyperliquid is unique among crypto exchanges: it combines the transparency of on-chain execution with the performance of a centralized orderbook. No API key is needed for data access -- only a wallet signature for trading.

## When to Use

- When building strategies that execute on Hyperliquid
- When fetching candle, orderbook, or trade data from Hyperliquid
- When managing positions, orders, or vault interactions
- When configuring testnet vs mainnet environments

## Key Architecture Facts

| Property | Value |
|----------|-------|
| Type | On-chain CLOB (L1 blockchain) |
| Block time | 400-600ms (sub-second finality) |
| Settlement | Instant (same block) |
| Data access | Free, no API key required |
| Trading auth | Wallet signature (EIP-712) |
| Margin mode | Cross (default), Isolated |
| Funding | Every 1 hour |
| Maker fee | -0.02% (REBATE) |
| Taker fee | 0.025% |
| Max leverage | 50x BTC/ETH, 3-20x altcoins |
| Testnet | Fully functional, separate L1 |

## SDK Installation and Setup

```bash
pip install hyperliquid-python-sdk
# or
pip install hyperliquid
```

### Environment Configuration

```python
import os
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Endpoints
MAINNET_URL = "https://api.hyperliquid.xyz"
TESTNET_URL = "https://api.hyperliquid-testnet.xyz"

# Data access (no auth needed)
info = Info(constants.MAINNET_API_URL)  # or constants.TESTNET_API_URL

# Trading (wallet auth required)
# Private key from env -- NEVER hardcode
PRIVATE_KEY = os.environ.get("HYPERLIQUID_PRIVATE_KEY")
WALLET_ADDRESS = os.environ.get("HYPERLIQUID_WALLET_ADDRESS")

exchange = Exchange(
    wallet=PRIVATE_KEY,
    base_url=constants.MAINNET_API_URL,
    # Optional: vault_address for trading through a vault
    # vault_address="0x..."
)
```

### Testnet vs Mainnet

| Aspect | Testnet | Mainnet |
|--------|---------|---------|
| URL | `api.hyperliquid-testnet.xyz` | `api.hyperliquid.xyz` |
| Funds | Faucet (free test USDC) | Real USDC on Arbitrum bridge |
| Liquidity | Thin, simulated | Deep, real |
| Use case | Strategy testing, dev | Live trading |
| Block time | Same (~500ms) | Same (~500ms) |
| Contract specs | Same as mainnet | Production |

## Data Access Patterns (Info API)

### Fetching Candle Data

```python
from hyperliquid.info import Info
from hyperliquid.utils import constants
import pandas as pd
from datetime import datetime, timedelta

info = Info(constants.MAINNET_API_URL)

def get_candles(
    symbol: str = "BTC",
    interval: str = "5m",
    lookback_hours: int = 24
) -> pd.DataFrame:
    """
    Fetch OHLCV candles from Hyperliquid.

    Supported intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 3d, 1w, 1M
    """
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=lookback_hours)).timestamp() * 1000)

    candles = info.candles_snapshot(
        coin=symbol,
        interval=interval,
        startTime=start_time,
        endTime=end_time
    )

    df = pd.DataFrame(candles)
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")

    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df


def get_all_mids() -> dict[str, float]:
    """Get current mid prices for all listed assets."""
    all_mids = info.all_mids()
    return {k: float(v) for k, v in all_mids.items()}
```

### Orderbook Data

```python
def get_orderbook(symbol: str = "BTC", depth: int = 20) -> dict:
    """
    Fetch L2 orderbook snapshot.

    Returns:
        {"bids": [[price, size], ...], "asks": [[price, size], ...]}
    """
    book = info.l2_snapshot(coin=symbol)

    bids = [[float(level["px"]), float(level["sz"])] for level in book["levels"][0][:depth]]
    asks = [[float(level["px"]), float(level["sz"])] for level in book["levels"][1][:depth]]

    return {
        "bids": bids,
        "asks": asks,
        "mid": (bids[0][0] + asks[0][0]) / 2 if bids and asks else None
    }
```

### Funding Rate Data

```python
def get_funding_rates() -> dict[str, dict]:
    """
    Get current funding rates for all assets.
    Hyperliquid funding is every 1 hour (not 8h like CEXs).
    """
    meta = info.meta()
    funding_data = {}

    for asset_info in meta["universe"]:
        symbol = asset_info["name"]
        funding_data[symbol] = {
            "funding_rate": float(asset_info.get("funding", 0)),
            "open_interest": float(asset_info.get("openInterest", 0)),
            "mark_price": float(asset_info.get("markPx", 0)),
            "max_leverage": int(asset_info.get("maxLeverage", 50)),
        }

    return funding_data


def get_funding_history(symbol: str = "BTC", hours: int = 168) -> pd.DataFrame:
    """Get historical funding rates (default 7 days)."""
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

    history = info.funding_history(
        coin=symbol,
        startTime=start_time,
        endTime=end_time
    )

    df = pd.DataFrame(history)
    df["timestamp"] = pd.to_datetime(df["time"], unit="ms")
    df["funding_rate"] = df["fundingRate"].astype(float)
    return df[["timestamp", "funding_rate"]].set_index("timestamp")
```

### User State (Positions and Balances)

```python
def get_user_state(wallet_address: str) -> dict:
    """
    Get full account state: positions, balances, margin info.
    No API key needed -- all on-chain data is public.
    """
    state = info.user_state(wallet_address)

    positions = []
    for pos in state.get("assetPositions", []):
        p = pos["position"]
        positions.append({
            "symbol": p["coin"],
            "side": "long" if float(p["szi"]) > 0 else "short",
            "size": abs(float(p["szi"])),
            "entry_price": float(p["entryPx"]),
            "mark_price": float(p.get("markPx", 0)),
            "unrealized_pnl": float(p["unrealizedPnl"]),
            "leverage": float(p.get("leverage", {}).get("value", 1)),
            "liquidation_price": float(p.get("liquidationPx", 0)),
            "margin_used": float(p.get("marginUsed", 0)),
        })

    return {
        "account_value": float(state.get("marginSummary", {}).get("accountValue", 0)),
        "total_margin_used": float(state.get("marginSummary", {}).get("totalMarginUsed", 0)),
        "withdrawable": float(state.get("withdrawable", 0)),
        "positions": positions
    }
```

## Trading Patterns (Exchange API)

### Placing Orders

```python
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import os

exchange = Exchange(
    wallet=os.environ["HYPERLIQUID_PRIVATE_KEY"],
    base_url=constants.MAINNET_API_URL,
)

def place_limit_order(
    symbol: str,
    side: str,  # "buy" or "sell"
    size: float,
    price: float,
    reduce_only: bool = False,
    post_only: bool = True,
) -> dict:
    """
    Place a limit order on Hyperliquid.

    post_only=True ensures maker fee (rebate of -0.02%).
    """
    is_buy = side.lower() == "buy"

    order_result = exchange.order(
        coin=symbol,
        is_buy=is_buy,
        sz=size,
        limit_px=price,
        order_type={"limit": {"tif": "Gtc"}},
        reduce_only=reduce_only,
    )

    return {
        "status": order_result.get("status", "unknown"),
        "order_id": order_result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting", {}).get("oid"),
        "filled": order_result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("filled"),
    }


def place_market_order(
    symbol: str,
    side: str,
    size: float,
    slippage_pct: float = 0.5,
) -> dict:
    """
    Place a market order (aggressive limit with slippage tolerance).

    Hyperliquid has no true market order type.
    Instead, use a limit order with generous price and IOC time-in-force.
    """
    mids = Info(constants.MAINNET_API_URL).all_mids()
    mid_price = float(mids[symbol])

    is_buy = side.lower() == "buy"
    # Set price with slippage buffer
    if is_buy:
        limit_px = mid_price * (1 + slippage_pct / 100)
    else:
        limit_px = mid_price * (1 - slippage_pct / 100)

    # Round to tick size
    limit_px = round(limit_px, 1)

    order_result = exchange.order(
        coin=symbol,
        is_buy=is_buy,
        sz=size,
        limit_px=limit_px,
        order_type={"limit": {"tif": "Ioc"}},  # Immediate-or-cancel
    )

    return order_result


def place_stop_order(
    symbol: str,
    side: str,
    size: float,
    trigger_price: float,
    limit_price: float = None,
) -> dict:
    """
    Place a stop-loss or take-profit trigger order.
    """
    is_buy = side.lower() == "buy"

    # Determine trigger type
    current_mid = float(Info(constants.MAINNET_API_URL).all_mids()[symbol])
    if is_buy:
        tp_sl = "tp" if trigger_price > current_mid else "sl"
    else:
        tp_sl = "sl" if trigger_price > current_mid else "tp"

    trigger_order = {
        "triggerPx": str(trigger_price),
        "isMarket": limit_price is None,
        "tpsl": tp_sl,
    }

    order_result = exchange.order(
        coin=symbol,
        is_buy=is_buy,
        sz=size,
        limit_px=limit_price or trigger_price,
        order_type={"trigger": trigger_order},
        reduce_only=True,
    )

    return order_result
```

### Position Management

```python
def close_position(symbol: str) -> dict:
    """Close entire position for a symbol."""
    wallet = os.environ["HYPERLIQUID_WALLET_ADDRESS"]
    state = info.user_state(wallet)

    for pos in state.get("assetPositions", []):
        p = pos["position"]
        if p["coin"] == symbol:
            size = abs(float(p["szi"]))
            is_long = float(p["szi"]) > 0

            return place_market_order(
                symbol=symbol,
                side="sell" if is_long else "buy",
                size=size,
            )

    return {"status": "no_position"}


def set_leverage(symbol: str, leverage: int, margin_mode: str = "isolated") -> dict:
    """
    Set leverage for a symbol. Must be done before opening position.

    Args:
        margin_mode: "cross" or "isolated"
    """
    is_cross = margin_mode.lower() == "cross"

    result = exchange.update_leverage(
        leverage=leverage,
        coin=symbol,
        is_cross=is_cross,
    )

    return result


def cancel_all_orders(symbol: str = None) -> dict:
    """Cancel all open orders, optionally filtered by symbol."""
    wallet = os.environ["HYPERLIQUID_WALLET_ADDRESS"]
    open_orders = info.open_orders(wallet)

    if symbol:
        open_orders = [o for o in open_orders if o["coin"] == symbol]

    cancels = []
    for order in open_orders:
        cancels.append({
            "coin": order["coin"],
            "oid": order["oid"],
        })

    if not cancels:
        return {"status": "no_orders"}

    result = exchange.cancel(cancels)
    return result
```

### Vault Interaction

```python
def deposit_to_vault(vault_address: str, amount_usd: float) -> dict:
    """
    Deposit USDC into a Hyperliquid vault.
    Vaults are on-chain managed accounts (like copy trading).
    """
    result = exchange.vault_transfer(
        vault_address=vault_address,
        is_deposit=True,
        usd=amount_usd,
    )
    return result


def withdraw_from_vault(vault_address: str, amount_usd: float) -> dict:
    """Withdraw USDC from a vault."""
    result = exchange.vault_transfer(
        vault_address=vault_address,
        is_deposit=False,
        usd=amount_usd,
    )
    return result


def get_vault_details(vault_address: str) -> dict:
    """Get vault PnL, followers, and position details."""
    details = info.vault_details(vault_address)
    return details
```

## Builder Codes

Builder codes are Hyperliquid's referral/integration system. They route a portion of taker fees to the builder (integrator).

```python
# Set builder code when creating exchange instance
exchange = Exchange(
    wallet=PRIVATE_KEY,
    base_url=constants.MAINNET_API_URL,
)

# Builder code is set per-order (optional)
# This adds a "builder" field to the order
# The builder receives a fee rebate from Hyperliquid
```

## Rate Limits and Performance

| Endpoint | Rate Limit | Notes |
|----------|-----------|-------|
| Info (data) | 1200 req/min | No auth needed |
| Exchange (trading) | 100 req/min per wallet | Wallet-signed |
| WebSocket | 1 connection per IP | Subscribe to multiple channels |
| Candle history | 500 candles per request | Paginate for more |

### WebSocket Streaming

```python
import json
import websocket

def stream_trades(symbol: str, callback):
    """Stream real-time trades via WebSocket."""
    ws_url = "wss://api.hyperliquid.xyz/ws"

    def on_open(ws):
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {"type": "trades", "coin": symbol}
        }
        ws.send(json.dumps(subscribe_msg))

    def on_message(ws, message):
        data = json.loads(message)
        if data.get("channel") == "trades":
            for trade in data.get("data", []):
                callback({
                    "price": float(trade["px"]),
                    "size": float(trade["sz"]),
                    "side": trade["side"],
                    "timestamp": trade["time"],
                })

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
    )
    ws.run_forever()


def stream_orderbook(symbol: str, callback):
    """Stream L2 orderbook updates."""
    ws_url = "wss://api.hyperliquid.xyz/ws"

    def on_open(ws):
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {"type": "l2Book", "coin": symbol}
        }
        ws.send(json.dumps(subscribe_msg))

    def on_message(ws, message):
        data = json.loads(message)
        if data.get("channel") == "l2Book":
            book = data["data"]
            callback(book)

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
    )
    ws.run_forever()
```

## On-Chain CLOB Specifics

| Property | Detail |
|----------|--------|
| Order matching | Price-time priority (same as CEX) |
| Block finality | 400-600ms (sub-second) |
| Cancellation | Same block possible |
| MEV risk | Minimal (dedicated L1, not shared Ethereum) |
| Oracle | Chainlink + internal composite |
| Mark price | Median of oracle, Binance, OKX mark prices |
| Insurance fund | On-chain, publicly auditable |
| Liquidation | Engine sells at oracle mark price |

## Common Pitfalls

1. **No true market orders** -- Use IOC limit with slippage buffer. A "market" order is a limit at worst acceptable price.
2. **Tick size varies by asset** -- BTC uses $1 ticks, ETH uses $0.1, altcoins vary. Check `meta()` for each asset's `szDecimals`.
3. **Wallet auth, not API keys** -- Private key signs every order. Never expose the key. Use a dedicated trading wallet, not your main wallet.
4. **Testnet data is thin** -- Orderbooks on testnet have minimal depth. Slippage estimates from testnet are unreliable.
5. **1-hour funding** -- Hyperliquid settles funding every hour, not every 8 hours. Annualized carry calculations must account for 24 intervals/day.
6. **Position updates are async** -- After an order fills, position state may take 1-2 blocks (~1s) to reflect in `user_state()`.
7. **Gas is negligible but non-zero** -- Each order costs a tiny amount of gas on HyperEVM. For HFT-level frequency, this adds up.

## Reference Sources

- Hyperliquid Python SDK: `https://github.com/hyperliquid-dex/hyperliquid-python-sdk`
- Hyperliquid API Docs: `https://hyperliquid.gitbook.io/hyperliquid-docs`
- MoonDev Hyperliquid tutorials: automated alpha pipeline patterns

## Related Skills

- `quant-exchange-compliance` -- Leverage tier rules for Hyperliquid
- `quant-crypto-cost-modeling` -- Fee model (maker rebate -0.02%, taker 0.025%)
- `quant-cross-exchange-arb` -- Using Hyperliquid as one leg of arb
- `quant-order-flow-analysis` -- Transparent on-chain orderbook analysis
