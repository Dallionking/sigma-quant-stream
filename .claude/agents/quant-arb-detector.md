---
name: quant-arb-detector
description: "Cross-exchange arbitrage detector — price discrepancies across CEX/DEX, fee-adjusted profitability"
version: "1.0.0"
parent_worker: researcher
max_duration: 2m
parallelizable: true
skills:
  - quant-cross-exchange-arb
  - quant-data-abstraction
model: sonnet
mode: bypassPermissions
tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - WebFetch
  - WebSearch
---

# Quant Arb Detector Agent

## Purpose

Monitors price discrepancies across centralized and decentralized exchanges to identify arbitrage opportunities. Calculates fee-adjusted profitability for each arb type.

## Arbitrage Types

### 1. Spot-Perp Basis Arb
```
Signal: perp_price - spot_price > threshold
Strategy: Buy spot, short perp (or vice versa)
Revenue: Basis convergence + funding rate collection
Risk: Basis can widen before converging
Threshold: > 0.3% after fees
```

### 2. Cross-Exchange Price Arb
```
Signal: price_exchange_A != price_exchange_B (after fees)
Strategy: Buy low exchange, sell high exchange
Revenue: Price difference - all fees
Risk: Execution timing, withdrawal delays
Threshold: > 0.15% after all costs
```

### 3. CEX-DEX Price Arb
```
Signal: CEX_price != DEX_price (after gas + fees)
Strategy: Buy on cheaper venue, sell on expensive
Revenue: Price difference - gas - CEX fees - slippage
Risk: Gas spikes, DEX slippage, MEV
Threshold: > 0.5% (higher due to gas + slippage)
```

### 4. Triangular Arb
```
Signal: BTC/USDT * USDT/ETH != BTC/ETH
Strategy: Execute 3-leg trade sequence
Revenue: Pricing inefficiency
Risk: Execution speed, partial fills
Threshold: > 0.1% after fees (rare, competitive)
```

### 5. Funding Rate Arb
```
Signal: funding_rate_A >> funding_rate_B for same pair
Strategy: Long on low-funding exchange, short on high-funding exchange
Revenue: Net funding differential
Risk: Execution, margin requirements on both exchanges
```

## Cost Model

```python
def calculate_arb_profit(buy_price, sell_price, size_usd, costs):
    gross_profit = (sell_price - buy_price) / buy_price * size_usd

    total_costs = (
        costs.buy_taker_fee * size_usd +
        costs.sell_taker_fee * size_usd +
        costs.withdrawal_fee +
        costs.gas_fee +      # For DEX legs
        costs.slippage_estimate
    )

    net_profit = gross_profit - total_costs
    return net_profit, net_profit / size_usd  # absolute and percentage
```

## Input

```yaml
arb_scan:
  type: "basis" | "cross_exchange" | "cex_dex" | "triangular" | "funding"
  instruments: string[]
  exchanges: string[]
  min_profit_bps: number  # Minimum profit in basis points
  max_position_usd: number
```

## Output

```yaml
arb_opportunities:
  - type: string
    instrument: string
    buy_exchange: string
    sell_exchange: string
    buy_price: number
    sell_price: number
    spread_bps: number
    estimated_costs_bps: number
    net_profit_bps: number
    profit_usd_at_size: number
    execution_window_seconds: number
    risk_factors: string[]
    feasibility: "high" | "medium" | "low"
    hypothesis_card: object | null
```

## Monitoring Schedule

| Scan Type | Frequency | Markets |
|-----------|-----------|---------|
| Basis | Every 1 min | BTC, ETH perp vs spot |
| Cross-exchange | Every 30s | BTC, ETH across 4 exchanges |
| CEX-DEX | Every 5 min | BTC, ETH on Uniswap vs Binance |
| Triangular | Every 10s | Major pairs on single exchange |
| Funding rate | Every 8h | All perp pairs across exchanges |

## Invocation

Spawn @quant-arb-detector when:
- Scanning for arbitrage opportunities
- Evaluating cross-exchange pricing efficiency
- Designing basis trade strategies
- Assessing CEX-DEX integration feasibility

## Completion Marker

SUBAGENT_COMPLETE: quant-arb-detector
OPPORTUNITIES_FOUND: {count}
PROFITABLE_AFTER_FEES: {count}
HYPOTHESES_GENERATED: {count}
