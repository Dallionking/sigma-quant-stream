---
name: quant-market-making
description: "Avellaneda-Stoikov market making model for crypto perpetuals"
version: "1.0.0"
triggers:
  - "when building market making strategies"
  - "when calculating optimal bid-ask spreads"
  - "when managing inventory risk"
  - "when implementing crypto MM logic"
---

# Quant Market Making

## Purpose

Implements the Avellaneda-Stoikov framework for market making on crypto perpetual contracts. Crypto perps are ideal MM targets: 24/7 liquidity, tight spreads on major pairs, and funding rate provides carry.

## When to Use

- When building a market making strategy for crypto perps
- When optimizing bid/ask placement
- When managing inventory risk in MM
- When incorporating funding rate into MM P&L

## Core Model: Avellaneda-Stoikov

### Theory

The optimal bid/ask quotes minimize inventory risk while maximizing spread capture:

```
reservation_price = mid_price - q * gamma * sigma^2 * (T - t)
optimal_spread = gamma * sigma^2 * (T - t) + (2/gamma) * ln(1 + gamma/k)
```

Where:
- `q` = current inventory (positive = long, negative = short)
- `gamma` = risk aversion parameter (higher = tighter inventory control)
- `sigma` = volatility
- `T - t` = time horizon
- `k` = order arrival rate parameter

### Implementation

```python
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class MMConfig:
    """Market making configuration."""
    gamma: float = 0.1          # Risk aversion (0.01-1.0)
    sigma_window: int = 100     # Volatility lookback (bars)
    time_horizon: float = 1.0   # Horizon in hours
    k: float = 1.5              # Order arrival intensity
    max_inventory: float = 10.0 # Max position size (base units)
    min_spread_bps: float = 2.0 # Minimum spread in basis points
    max_spread_bps: float = 50.0  # Max spread cap
    skew_factor: float = 0.5    # Inventory skew aggressiveness

class AvellanedaStoikov:
    """
    Avellaneda-Stoikov market maker for crypto perps.
    Adapted for 24/7 crypto markets with funding rate carry.
    """

    def __init__(self, config: MMConfig):
        self.config = config
        self.inventory = 0.0

    def calculate_volatility(self, prices: np.ndarray) -> float:
        """Realized volatility from recent prices."""
        returns = np.diff(np.log(prices[-self.config.sigma_window:]))
        return float(np.std(returns))

    def reservation_price(
        self,
        mid_price: float,
        sigma: float,
        time_remaining: float = 1.0
    ) -> float:
        """
        Calculate reservation (indifference) price.
        Shifts away from mid based on inventory.
        Long inventory -> lower reservation price (want to sell).
        """
        q = self.inventory
        gamma = self.config.gamma
        return mid_price - q * gamma * (sigma ** 2) * time_remaining

    def optimal_spread(
        self,
        sigma: float,
        time_remaining: float = 1.0
    ) -> float:
        """
        Calculate optimal total spread (bid-ask width).
        Higher volatility or risk aversion -> wider spread.
        """
        gamma = self.config.gamma
        k = self.config.k

        spread = gamma * (sigma ** 2) * time_remaining + \
                 (2 / gamma) * np.log(1 + gamma / k)

        # Apply min/max bounds
        min_spread = self.config.min_spread_bps / 10000
        max_spread = self.config.max_spread_bps / 10000
        return np.clip(spread, min_spread, max_spread)

    def calculate_quotes(
        self,
        mid_price: float,
        prices: np.ndarray,
        funding_rate: float = 0.0
    ) -> dict:
        """
        Calculate optimal bid and ask prices.

        Args:
            mid_price: Current mid price
            prices: Recent price array for volatility
            funding_rate: Current funding rate (positive = longs pay shorts)

        Returns:
            dict with bid_price, ask_price, spread, reservation_price
        """
        sigma = self.calculate_volatility(prices)
        res_price = self.reservation_price(mid_price, sigma)
        spread = self.optimal_spread(sigma)

        # Inventory skew: shift quotes to reduce position
        skew = self.config.skew_factor * self.inventory / self.config.max_inventory
        # Positive inventory -> lower both quotes (incentivize selling)
        skew_adjustment = skew * spread

        # Funding rate adjustment: if longs pay, bias short
        funding_bias = 0.0
        if abs(funding_rate) > 0.001:  # Only adjust for significant funding
            funding_bias = -np.sign(funding_rate) * abs(funding_rate) * mid_price * 0.1

        bid_price = res_price - spread / 2 - skew_adjustment + funding_bias
        ask_price = res_price + spread / 2 - skew_adjustment + funding_bias

        return {
            "bid_price": round(bid_price, 2),
            "ask_price": round(ask_price, 2),
            "spread_bps": spread * 10000,
            "reservation_price": round(res_price, 2),
            "inventory": self.inventory,
            "sigma": sigma,
            "funding_adjustment": funding_bias
        }

    def on_fill(self, side: str, size: float, price: float):
        """Update inventory on fill."""
        if side == "buy":
            self.inventory += size
        else:
            self.inventory -= size

        # Inventory limit check
        if abs(self.inventory) > self.config.max_inventory:
            raise ValueError(
                f"Inventory {self.inventory} exceeds max {self.config.max_inventory}"
            )
```

### Funding Rate as Carry

```python
def calculate_mm_pnl(
    trades: list[dict],
    funding_payments: list[dict],
    hours: float
) -> dict:
    """
    MM P&L decomposition:
    1. Spread capture (primary)
    2. Inventory P&L (secondary, ideally flat)
    3. Funding carry (bonus for short bias in positive funding)
    """
    spread_pnl = sum(
        t["spread_captured"] for t in trades
    )
    inventory_pnl = sum(
        t["inventory_pnl"] for t in trades
    )
    funding_pnl = sum(
        f["payment"] for f in funding_payments
    )

    return {
        "total_pnl": spread_pnl + inventory_pnl + funding_pnl,
        "spread_pnl": spread_pnl,
        "inventory_pnl": inventory_pnl,
        "funding_pnl": funding_pnl,
        "spread_pnl_pct": spread_pnl / (spread_pnl + abs(inventory_pnl) + abs(funding_pnl)) * 100,
        "trades_per_hour": len(trades) / hours
    }
```

## Gamma Parameter Tuning

| Gamma | Behavior | Use Case |
|-------|----------|----------|
| 0.01 | Very aggressive (tight spread, large inventory) | High-volume, low-vol markets |
| 0.1 | Balanced | Most crypto perps |
| 0.5 | Conservative (wide spread, low inventory) | Volatile / thin markets |
| 1.0 | Very conservative | Altcoin / low liquidity |

## Risk Management

```python
def mm_risk_check(inventory: float, config: MMConfig, current_price: float) -> dict:
    """Pre-trade risk checks for market making."""
    inventory_usd = abs(inventory) * current_price
    utilization = abs(inventory) / config.max_inventory

    return {
        "inventory_usd": inventory_usd,
        "utilization_pct": utilization * 100,
        "should_widen_spread": utilization > 0.7,
        "should_skip_side": "bid" if inventory > config.max_inventory * 0.8
                           else "ask" if inventory < -config.max_inventory * 0.8
                           else None,
        "emergency_flatten": utilization > 0.95
    }
```

## Common Pitfalls

1. **Gamma too low** — Accumulates dangerous inventory in trending markets
2. **Ignoring funding** — In positive funding regimes, short bias is free carry
3. **No inventory limits** — Must hard-cap position size
4. **Symmetric quotes in trends** — Skew quotes based on short-term momentum
5. **Latency matters** — Even 100ms delay loses edge on liquid pairs
6. **Fee tier matters** — Maker rebates (Hyperliquid: 0.2bps) change optimal spread

## Reference: Jump Crypto Approach

Jump's public market making approach emphasizes:
- Inventory mean-reversion on 1-5 second timescales
- Multi-venue quoting with cross-exchange inventory netting
- Adaptive gamma based on realized volatility regime
- Hardware-level latency optimization

## Related Skills

- `quant-crypto-cost-modeling` — Fee structure for MM profitability
- `quant-order-flow-analysis` — Reading the tape for MM positioning
- `quant-cross-exchange-arb` — Multi-venue spread capture
