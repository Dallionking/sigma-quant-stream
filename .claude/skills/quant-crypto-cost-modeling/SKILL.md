---
name: quant-crypto-cost-modeling
description: "Percentage-based fee modeling for crypto perpetuals and spot markets"
version: "1.0.0"
triggers:
  - "when calculating crypto trading costs"
  - "when modeling crypto slippage in bps"
  - "when comparing exchange fee structures"
  - "when building crypto backtest cost models"
---

# Quant Crypto Cost Modeling

## Purpose

Provides cost modeling for crypto markets where fees are percentage-based (not per-contract). Covers maker/taker fees, funding rate costs, gas estimates, and slippage in basis points. Extends the abstract `InstrumentSpec` from `quant-cost-modeling`.

## When to Use

- When backtesting any crypto strategy
- When comparing profitability across exchanges
- When calculating break-even for crypto MM or arb
- When `profile.costs.model == "percentage"`

## Key Differences from Futures

| Aspect | Futures | Crypto |
|--------|---------|--------|
| Fee model | Per-contract fixed ($) | Percentage of notional (bps) |
| Slippage | Ticks | Basis points |
| Funding | N/A | Every 1-8h (positive or negative) |
| Gas | N/A | DEX only (variable) |
| Tick size | Fixed | Variable (price-dependent) |
| Trading hours | RTH / ETH | 24/7/365 |

## Exchange Fee Comparison

| Exchange | Maker | Taker | Funding Freq | Notes |
|----------|-------|-------|--------------|-------|
| **Binance** | 2 bps | 4 bps | 8h | VIP0; lower with BNB discount |
| **Bybit** | 2 bps | 5.5 bps | 8h | |
| **OKX** | 2 bps | 5 bps | 8h | |
| **Hyperliquid** | -0.2 bps | 2.5 bps | 1h | Maker REBATE |
| **dYdX v4** | 2 bps | 5 bps | 1h | Cosmos chain |
| **Kraken** | 2 bps | 5 bps | 4h | |

## Implementation

### Instrument Specs

```python
from dataclasses import dataclass
from abc import ABC, abstractmethod

class InstrumentSpec(ABC):
    """Abstract base for all tradeable instruments."""

    @abstractmethod
    def cost_per_trade(self, notional_usd: float, is_maker: bool = False) -> float:
        """Total cost for a single trade (one side) in USD."""
        ...

    @abstractmethod
    def breakeven_bps(self) -> float:
        """Minimum move in bps to break even on a round trip."""
        ...


@dataclass
class CryptoPerpSpec(InstrumentSpec):
    """Crypto perpetual contract specification."""
    symbol: str           # e.g., "BTC/USDT"
    exchange: str         # e.g., "binance"
    maker_fee_bps: float  # Maker fee in basis points
    taker_fee_bps: float  # Taker fee in basis points
    min_order_size: float # Minimum order in base currency
    tick_size: float      # Price tick (e.g., 0.1 for BTC)
    lot_size: float       # Size tick (e.g., 0.001 for BTC)
    max_leverage: int     # Maximum leverage
    funding_interval_h: int = 8  # Funding payment interval

    def cost_per_trade(self, notional_usd: float, is_maker: bool = False) -> float:
        fee_bps = self.maker_fee_bps if is_maker else self.taker_fee_bps
        return notional_usd * fee_bps / 10000

    def breakeven_bps(self) -> float:
        """Round trip cost assuming taker on both sides."""
        return self.taker_fee_bps * 2  # Entry + exit


@dataclass
class CryptoSpotSpec(InstrumentSpec):
    """Crypto spot market specification."""
    symbol: str
    exchange: str
    maker_fee_bps: float
    taker_fee_bps: float
    min_order_size: float
    tick_size: float
    lot_size: float
    withdrawal_fee: float = 0.0  # For cross-exchange arb

    def cost_per_trade(self, notional_usd: float, is_maker: bool = False) -> float:
        fee_bps = self.maker_fee_bps if is_maker else self.taker_fee_bps
        return notional_usd * fee_bps / 10000

    def breakeven_bps(self) -> float:
        return self.taker_fee_bps * 2
```

### Preset Instrument Specs

```python
CRYPTO_SPECS = {
    "BTC/USDT:binance": CryptoPerpSpec(
        symbol="BTC/USDT", exchange="binance",
        maker_fee_bps=2.0, taker_fee_bps=4.0,
        min_order_size=0.001, tick_size=0.1, lot_size=0.001,
        max_leverage=125, funding_interval_h=8
    ),
    "ETH/USDT:binance": CryptoPerpSpec(
        symbol="ETH/USDT", exchange="binance",
        maker_fee_bps=2.0, taker_fee_bps=4.0,
        min_order_size=0.01, tick_size=0.01, lot_size=0.01,
        max_leverage=100, funding_interval_h=8
    ),
    "BTC/USDC:hyperliquid": CryptoPerpSpec(
        symbol="BTC/USDC", exchange="hyperliquid",
        maker_fee_bps=-0.2, taker_fee_bps=2.5,
        min_order_size=0.001, tick_size=1.0, lot_size=0.001,
        max_leverage=50, funding_interval_h=1
    ),
    "SOL/USDT:bybit": CryptoPerpSpec(
        symbol="SOL/USDT", exchange="bybit",
        maker_fee_bps=2.0, taker_fee_bps=5.5,
        min_order_size=0.1, tick_size=0.01, lot_size=0.1,
        max_leverage=50, funding_interval_h=8
    ),
}
```

### Cost-Aware Crypto Backtester

```python
@dataclass
class CryptoCostModel:
    """
    Crypto-specific cost model with percentage fees.
    """
    spec: CryptoPerpSpec
    slippage_bps: float = 2.0      # Average slippage
    funding_rate_avg: float = 0.01  # Average funding rate per interval (%)

    def calculate_round_trip_cost(
        self,
        notional_usd: float,
        holding_hours: float = 1.0,
        is_maker: bool = False
    ) -> dict:
        """
        Total round-trip cost including funding.
        """
        # Trading fees (entry + exit)
        fee_bps = self.spec.maker_fee_bps if is_maker else self.spec.taker_fee_bps
        trading_fee = notional_usd * fee_bps * 2 / 10000

        # Slippage (entry + exit)
        slippage_cost = notional_usd * self.slippage_bps * 2 / 10000

        # Funding cost (proportional to holding time)
        funding_intervals = holding_hours / self.spec.funding_interval_h
        funding_cost = notional_usd * self.funding_rate_avg / 100 * funding_intervals

        total = trading_fee + slippage_cost + abs(funding_cost)

        return {
            "total_cost_usd": round(total, 4),
            "trading_fee_usd": round(trading_fee, 4),
            "slippage_usd": round(slippage_cost, 4),
            "funding_usd": round(funding_cost, 4),
            "total_cost_bps": round(total / notional_usd * 10000, 2),
            "breakeven_bps": round(total / notional_usd * 10000, 2)
        }
```

### Gas Cost Estimation (DEX)

```python
def estimate_gas_cost(
    chain: str = "ethereum",
    gas_price_gwei: float = 30.0,
    eth_price_usd: float = 3000.0
) -> dict:
    """
    Estimate gas costs for DEX trades.
    Only relevant for on-chain execution (Uniswap, etc).
    Hyperliquid has negligible gas (Arbitrum L2).
    """
    GAS_UNITS = {
        "ethereum": {"swap": 150000, "approve": 50000},
        "arbitrum": {"swap": 800000, "approve": 200000},  # L2 gas units differ
        "solana": {"swap": 5000, "approve": 0},  # Lamports
    }

    GAS_PRICE_MULTIPLIER = {
        "ethereum": gas_price_gwei * 1e-9,  # gwei -> ETH
        "arbitrum": 0.1 * 1e-9,  # ~0.1 gwei typical
        "solana": 0.000005,  # ~5000 lamports
    }

    if chain not in GAS_UNITS:
        return {"gas_cost_usd": 0.0, "note": "Chain not supported"}

    swap_gas = GAS_UNITS[chain]["swap"] * GAS_PRICE_MULTIPLIER[chain] * eth_price_usd
    approve_gas = GAS_UNITS[chain]["approve"] * GAS_PRICE_MULTIPLIER[chain] * eth_price_usd

    return {
        "swap_cost_usd": round(swap_gas, 4),
        "approve_cost_usd": round(approve_gas, 4),
        "total_round_trip_usd": round(swap_gas * 2, 4),
        "chain": chain
    }
```

## Common Pitfalls

1. **Maker vs taker matters enormously** — Hyperliquid maker rebate (-0.2 bps) vs taker (2.5 bps) is 2.7 bps difference per side
2. **Funding rate is NOT constant** — Can spike to 0.1%+ during volatility. Use historical average, not snapshot
3. **VIP tiers reduce fees** — High-volume accounts pay significantly less; backtest with realistic tier
4. **Gas costs only for DEX** — CEX has no gas. Don't add gas to Binance backtests
5. **Slippage in bps, not ticks** — Crypto has no fixed tick value; always express as percentage of price

## Related Skills

- `quant-cost-modeling` — Abstract InstrumentSpec base class, futures cost patterns
- `quant-exchange-compliance` — Risk limits per exchange
- `quant-cross-exchange-arb` — Fee-adjusted arb profitability
