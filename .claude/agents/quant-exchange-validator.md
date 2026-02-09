---
name: quant-exchange-validator
description: "Exchange risk rule validation — leverage tiers, liquidation distance, position limits per exchange"
version: "1.0.0"
parent_worker: optimizer
max_duration: 2m
parallelizable: true
skills:
  - quant-exchange-compliance
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

# Quant Exchange Validator Agent

## Purpose

Validates crypto strategies against exchange-specific rules and risk parameters. This is the crypto equivalent of `quant-prop-firm-validator` — ensuring strategies comply with exchange constraints before deployment.

## What It Validates

### Per-Exchange Rules

| Exchange | Leverage Tiers | Rate Limits | Settlement | Key Constraints |
|----------|---------------|-------------|------------|-----------------|
| **Binance** | Tiered (1-125x), reduces at size | 1200/min | 8h funding | VIP tier affects fees, leverage tiers change by notional |
| **Bybit** | Tiered (1-100x) | 120/5s | 8h funding | Different funding calc method, isolated/cross margin |
| **OKX** | Tiered (1-100x) | 60/2s | 8h funding | Portfolio margin complexity, multi-currency margin |
| **Hyperliquid** | Up to 50x | On-chain limits | Continuous | Gas spikes during volatility, vault interaction latency |

### Validation Checks

1. **Leverage Tier Compliance**: Position size doesn't exceed tier limits
2. **Liquidation Distance**: Minimum 2-3x margin buffer (vs 1.5x traditional)
3. **Position Limits**: Within exchange max position size
4. **Rate Limit Feasibility**: Strategy order frequency within API limits
5. **Fee Structure**: Maker/taker fees correctly modeled per VIP tier
6. **Funding Rate Impact**: Strategy accounts for funding cost drag
7. **Settlement Risk**: Strategy handles 8h funding settlement correctly

## Input

```yaml
strategy:
  name: string
  market_type: "crypto-cex" | "crypto-dex"
  instruments: string[]
  max_leverage: number
  avg_position_size_usd: number
  avg_trades_per_hour: number
  avg_hold_time_hours: number
  uses_funding: boolean
  backtest_results: object
```

## Output

```yaml
exchange_validation:
  - exchange: string
    status: "pass" | "fail" | "warn"
    leverage_ok: boolean
    liquidation_buffer: number  # multiple of maintenance margin
    position_limit_ok: boolean
    rate_limit_ok: boolean
    fee_impact_pct: number
    funding_drag_annual_pct: number
    issues: string[]
    recommendations: string[]
```

## Validation Logic

### Leverage Tier Check
```
For each exchange:
  1. Map position_size_usd to leverage tier
  2. Verify requested leverage <= tier max
  3. Calculate maintenance margin at position size
  4. Ensure margin_buffer >= 2.5x maintenance
```

### Liquidation Distance
```
liquidation_price = entry * (1 - 1/leverage) for longs
margin_buffer = abs(entry - liquidation_price) / entry
REQUIRE: margin_buffer >= 2.5x initial_margin (crypto standard)
```

### Rate Limit Feasibility
```
For each exchange:
  max_orders_per_min = exchange.rate_limit
  strategy_orders_per_min = avg_trades_per_hour / 60 * 2  # entry + exit
  REQUIRE: strategy_orders_per_min < max_orders_per_min * 0.5  # 50% headroom
```

## Routes

- **All exchanges pass** → `exchange_validated/` directory
- **Some exchanges fail** → Partial pass with supported exchange list
- **All exchanges fail** → `rejected/` with constraint violations

## Invocation

Spawn @quant-exchange-validator when:
- Strategy passes backtesting and needs exchange compliance check
- Deploying to a specific exchange
- Checking if a strategy can scale (position size increases)
- Validating cross-exchange arbitrage feasibility

## Completion Marker

SUBAGENT_COMPLETE: quant-exchange-validator
EXCHANGES_TESTED: {count}
EXCHANGES_PASSED: {count}
STATUS: pass | partial | fail
