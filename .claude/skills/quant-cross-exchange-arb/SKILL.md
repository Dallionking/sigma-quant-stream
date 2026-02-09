---
name: quant-cross-exchange-arb
description: "Cross-exchange price discrepancy detection, triangular arb, and latency-adjusted execution"
version: "1.0.0"
triggers:
  - "when building cross-exchange arbitrage"
  - "when detecting price discrepancies"
  - "when calculating arb profitability after fees"
  - "when implementing triangular arbitrage"
---

# Quant Cross-Exchange Arbitrage

## Purpose

Detects and evaluates cross-exchange arbitrage opportunities in crypto. Unlike traditional markets where arb is near-zero, crypto still has exploitable dislocations due to fragmented liquidity, varying fee tiers, and blockchain settlement latency.

## When to Use

- When building cross-exchange spread monitoring
- When evaluating arb opportunity viability after fees
- When implementing triangular arb paths
- When estimating execution risk for arb trades

## Core Concepts

### Price Discrepancy Detection

```python
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass
class ExchangePrice:
    """Price snapshot from one exchange."""
    exchange: str
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp_ms: int

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread_bps(self) -> float:
        return (self.ask - self.bid) / self.mid * 10000


@dataclass
class ArbOpportunity:
    """Identified arbitrage opportunity."""
    buy_exchange: str
    sell_exchange: str
    symbol: str
    buy_price: float   # ask on buy exchange
    sell_price: float   # bid on sell exchange
    gross_spread_bps: float
    net_spread_bps: float  # after fees
    max_size: float     # limited by thinner side
    estimated_profit_usd: float
    latency_risk_bps: float


def detect_cross_exchange_arb(
    prices: list[ExchangePrice],
    fee_table: dict[str, dict],
    min_spread_bps: float = 5.0
) -> list[ArbOpportunity]:
    """
    Detect arb opportunities across exchange price snapshots.

    Args:
        prices: List of ExchangePrice from different exchanges (same symbol)
        fee_table: {exchange: {"maker": 0.0002, "taker": 0.0005}}
        min_spread_bps: Minimum net spread to flag

    Returns:
        List of ArbOpportunity sorted by net spread
    """
    opportunities = []

    for i, buy in enumerate(prices):
        for j, sell in enumerate(prices):
            if i == j:
                continue

            # Buy at ask on exchange A, sell at bid on exchange B
            gross_spread = (sell.bid - buy.ask) / buy.ask * 10000

            if gross_spread <= 0:
                continue

            # Deduct fees (taker on both sides)
            buy_fee_bps = fee_table[buy.exchange]["taker"] * 10000
            sell_fee_bps = fee_table[sell.exchange]["taker"] * 10000
            net_spread = gross_spread - buy_fee_bps - sell_fee_bps

            if net_spread < min_spread_bps:
                continue

            max_size = min(buy.ask_size, sell.bid_size)
            avg_price = (buy.ask + sell.bid) / 2
            estimated_profit = max_size * avg_price * net_spread / 10000

            # Latency risk: estimate how much spread may decay
            latency_ms = abs(buy.timestamp_ms - sell.timestamp_ms)
            latency_risk = latency_ms * 0.01  # ~0.01 bps per ms of staleness

            opportunities.append(ArbOpportunity(
                buy_exchange=buy.exchange,
                sell_exchange=sell.exchange,
                symbol=buy.symbol,
                buy_price=buy.ask,
                sell_price=sell.bid,
                gross_spread_bps=gross_spread,
                net_spread_bps=net_spread - latency_risk,
                max_size=max_size,
                estimated_profit_usd=estimated_profit,
                latency_risk_bps=latency_risk
            ))

    return sorted(opportunities, key=lambda x: -x.net_spread_bps)
```

### Fee Table

```python
# Realistic fee comparison (as of 2025)
EXCHANGE_FEES = {
    "binance": {"maker": 0.0002, "taker": 0.0004},   # VIP0
    "bybit":   {"maker": 0.0002, "taker": 0.00055},
    "okx":     {"maker": 0.0002, "taker": 0.0005},
    "hyperliquid": {"maker": -0.00002, "taker": 0.00025},  # Maker REBATE
    "dydx":    {"maker": 0.0002, "taker": 0.0005},
    "kraken":  {"maker": 0.0002, "taker": 0.0005},
}
```

### Triangular Arbitrage

```python
def triangular_arb(
    prices: dict[str, dict],
    start_currency: str = "USDT",
    amount: float = 10000.0,
    fee_rate: float = 0.001
) -> list[dict]:
    """
    Find triangular arbitrage paths within a single exchange.

    Example path: USDT -> BTC -> ETH -> USDT
    If final amount > start amount after fees, it's profitable.

    Args:
        prices: {"BTC/USDT": {"bid": x, "ask": y}, "ETH/BTC": {...}, ...}
        start_currency: Starting and ending currency
        amount: Starting amount
        fee_rate: Fee per trade (taker)
    """
    # Build adjacency graph from available pairs
    pairs = {}
    for pair, price in prices.items():
        base, quote = pair.split("/")
        pairs[(quote, base)] = price["ask"]   # Buy base with quote
        pairs[(base, quote)] = 1 / price["bid"]  # Sell base for quote

    # Find 3-hop cycles starting/ending at start_currency
    profitable_paths = []
    currencies = set()
    for pair in prices:
        b, q = pair.split("/")
        currencies.add(b)
        currencies.add(q)

    for mid1 in currencies:
        if mid1 == start_currency:
            continue
        for mid2 in currencies:
            if mid2 in (start_currency, mid1):
                continue

            path = [
                (start_currency, mid1),
                (mid1, mid2),
                (mid2, start_currency)
            ]

            # Check all legs exist
            if not all(leg in pairs for leg in path):
                continue

            # Calculate final amount
            current = amount
            for leg in path:
                rate = pairs[leg]
                current = current / rate if leg[0] != start_currency or leg == path[0] else current * rate
                current *= (1 - fee_rate)

            # Recalculate properly
            current = amount
            for from_curr, to_curr in path:
                rate = pairs[(from_curr, to_curr)]
                current = current * rate * (1 - fee_rate)

            profit_pct = (current - amount) / amount * 100

            if profit_pct > 0:
                profitable_paths.append({
                    "path": f"{path[0][0]}->{path[0][1]}->{path[1][1]}->{path[2][1]}",
                    "start_amount": amount,
                    "end_amount": round(current, 2),
                    "profit_pct": round(profit_pct, 4),
                    "profit_usd": round(current - amount, 2)
                })

    return sorted(profitable_paths, key=lambda x: -x["profit_pct"])
```

### Execution Risk Model

```python
@dataclass
class ExecutionRisk:
    """Risk factors for arb execution."""
    latency_ms: float         # Time to execute both legs
    partial_fill_prob: float  # Probability of partial fill (0-1)
    spread_decay_bps: float   # Expected spread decay during execution
    funding_cost_bps: float   # If holding overnight

def assess_arb_risk(
    opportunity: ArbOpportunity,
    execution_latency_ms: float = 200,  # Typical for API trading
    book_depth_usd: float = 100000
) -> ExecutionRisk:
    """
    Assess execution risk for an arb opportunity.
    """
    # Partial fill probability increases with size relative to depth
    size_ratio = opportunity.max_size * opportunity.buy_price / book_depth_usd
    partial_fill_prob = min(0.9, size_ratio * 0.5)

    # Spread typically decays at ~0.05 bps/ms for liquid pairs
    spread_decay = execution_latency_ms * 0.05

    return ExecutionRisk(
        latency_ms=execution_latency_ms,
        partial_fill_prob=partial_fill_prob,
        spread_decay_bps=spread_decay,
        funding_cost_bps=0.0  # Only if holding position
    )
```

## Wintermute Dynamic Spread Reference

Key principles from Wintermute's public approach:
- Quote on 10+ venues simultaneously
- Inventory is netted across all venues (single risk book)
- Spreads dynamically widen when inventory builds
- Latency optimized per venue (co-location where possible)
- Gas cost amortization for DEX legs

## Profitability Thresholds

| Pair Liquidity | Min Net Spread (bps) | Typical Opportunity |
|----------------|----------------------|---------------------|
| BTC/USDT | 2-5 | CEX vs DEX |
| ETH/USDT | 3-8 | CEX vs CEX |
| Altcoins | 10-50 | Regional exchange delisting |
| Triangular | 1-3 | Within single exchange |

## Common Pitfalls

1. **Stale prices** — Arb disappears faster than you can execute. Need sub-100ms data.
2. **Partial fills** — Only leg 1 fills. Now you have directional risk.
3. **Withdrawal delays** — Cross-exchange arb requires pre-funded accounts on both sides.
4. **Fee tier assumptions** — VIP0 fees kill most arbs. Need volume-based tier discounts.
5. **Gas costs on DEX leg** — Ethereum gas can exceed arb profit on small trades.
6. **Funding rate divergence** — Holding perp position incurs funding every 1-8h.

## Related Skills

- `quant-crypto-cost-modeling` — Fee calculations per exchange
- `quant-hyperliquid-adapter` — DEX execution specifics
- `quant-market-making` — Spread capture as passive arb
