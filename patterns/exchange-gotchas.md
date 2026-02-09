# Exchange Gotchas - Per-Exchange Compliance Issues

> Documented exchange-specific quirks, pitfalls, and compliance issues.
> Updated automatically by @sigma-distiller after each session.

---

## Format

Each entry should follow this structure:
```
### [TIMESTAMP] Entry Title
**Exchange**: Binance/Bybit/OKX/Hyperliquid/etc.
**Category**: Leverage/Settlement/Margin/Gas/Withdrawal/API/Other
**Severity**: Critical/High/Medium/Low

Description of the gotcha and how to handle it.

**Impact**: What goes wrong if ignored
**Mitigation**: How to avoid/handle
```

---

## Entries

<!-- New entries are prepended below this line -->

### [2026-02-08] Binance Leverage Tier Changes (Seed Entry)
**Exchange**: Binance
**Category**: Leverage
**Severity**: Critical

Binance dynamically adjusts maximum leverage based on position notional size. A position that opens at 20x may be forced to reduce leverage as it grows. Tier boundaries change without notice. During high volatility, Binance may reduce max leverage for all users temporarily.

Tier example (BTC):
- 0-50K USDT: 125x max
- 50K-250K: 100x max
- 250K-1M: 50x max
- 1M-5M: 20x max
- 5M+: 10x max

**Impact**: Strategy sized for 10x leverage may be forced to reduce mid-trade if tier boundary changes. Auto-deleveraging (ADL) can close profitable positions without consent.
**Mitigation**: Always target 2 tiers below maximum. Monitor Binance announcements for tier changes. Build ADL detection into monitoring. Never use more than 50% of tier-allowed leverage.

---

### [2026-02-08] Bybit Settlement Times (Seed Entry)
**Exchange**: Bybit
**Category**: Settlement
**Severity**: High

Bybit settles PnL at 00:00 UTC, 08:00 UTC, and 16:00 UTC. During settlement windows (approximately 1-2 minutes), order placement may fail or experience high latency. Unrealized PnL fluctuates during settlement recalculation.

Additional quirks:
- Funding rate snapshots at settlement time, not order time
- Position value recalculated with new mark price
- Insurance fund contributions deducted during settlement
- Historical PnL API may show gaps during settlement windows

**Impact**: Strategies that trade around settlement times may experience unexpected order rejections or PnL jumps. Backtests that don't model settlement windows overestimate fill quality.
**Mitigation**: Avoid placing orders within 2 minutes of settlement times. Account for settlement timing in backtest cost models. Monitor funding rate snapshot timing for carry strategies.

---

### [2026-02-08] OKX Margin Mode Quirks (Seed Entry)
**Exchange**: OKX
**Category**: Margin
**Severity**: High

OKX has three margin modes (isolated, cross, portfolio margin) with non-obvious interactions:
- Switching margin mode requires closing all positions in the instrument first
- Cross margin shares collateral across all positions -- one bad trade liquidates everything
- Portfolio margin requires minimum account equity ($10K) and whitelisting
- Margin ratio calculation differs between modes -- same position can show different health
- Auto-borrow in cross margin can create unexpected liabilities

**Impact**: Strategy that works in isolated margin may behave completely differently in cross margin. Portfolio margin can create systemic risk if not properly monitored. Switching modes mid-strategy is disruptive.
**Mitigation**: Always use isolated margin for strategy testing. Never switch margin modes with open positions. If using cross margin, size each position as if it were the only one. Build margin mode check into pre-trade validation.

---

### [2026-02-08] Hyperliquid Gas Spikes (Seed Entry)
**Exchange**: Hyperliquid
**Category**: Gas
**Severity**: Medium

Hyperliquid runs on its own L1 chain. During high-activity periods (major liquidation events, token launches), gas costs spike significantly. API order placement may time out or require higher gas. Vault operations (deposits/withdrawals) compete for same block space as trades.

Specific issues:
- Order cancellation can fail during congestion (orders stay open longer than intended)
- Batch operations more gas-efficient but have higher failure rate during spikes
- Historical gas data not readily available for backtesting
- Maker/taker fee structure different from CEX (0.02%/0.05% base)

**Impact**: Market making strategies on Hyperliquid face unpredictable execution costs. Cancel-replace patterns may leave stale orders. Gas costs can eat into thin-edge strategies.
**Mitigation**: Add gas cost buffer (2-3x normal) to cost models. Implement retry logic with exponential backoff for order operations. Avoid market making during high-volume events. Pre-fund gas wallet separately from trading capital.

---

### [2026-02-08] Cross-Exchange Withdrawal Delays Affecting Arb (Seed Entry)
**Exchange**: All
**Category**: Withdrawal
**Severity**: Critical

Cross-exchange arbitrage assumes funds can move between venues. Reality:
- Binance: 30min-2h for BTC, 5-15min for USDT (TRC20), up to 24h during maintenance
- Bybit: 15min-1h for most assets, longer for new deposits
- OKX: Similar to Binance, but withdrawal limits are lower for unverified accounts
- Hyperliquid: Bridge from Arbitrum, 10-30min typical but hours during L1 congestion
- All exchanges: May suspend withdrawals without notice during volatility

Network-specific delays:
- BTC: 3-6 confirmations (30-60 min)
- ETH: 12-64 confirmations (3-15 min)
- USDT TRC20: 19 confirmations (1-2 min)
- USDT ERC20: 12 confirmations (3-5 min)
- Arbitrum: Usually fast but L1 batching delays possible

**Impact**: Basis arbitrage with expected 0.3% edge can turn negative if transfer takes too long and price converges before capital arrives. Capital locked in transit is unproductive.
**Mitigation**: Pre-fund both exchanges (eliminate transfer need). Use delta-neutral positions to lock in basis without moving funds. Factor worst-case transfer time into arb profitability calculation. Maintain withdrawal whitelist addresses pre-approved to avoid manual review delays.

---

## Per-Exchange API Quirks

| Exchange | Rate Limit | WebSocket | Order Types | Gotcha |
|----------|-----------|-----------|-------------|--------|
| Binance | 1200 req/min | 5 streams/conn | Market, Limit, Stop, OCO | IP-based limits, not key-based |
| Bybit | 120 req/min | 20 topics/conn | Market, Limit, Conditional | Different limits for different endpoints |
| OKX | 60 req/2s per endpoint | 300 topics/conn | Market, Limit, Algo | Each endpoint has own rate limit |
| Hyperliquid | 1200 req/min | Unlimited topics | Market, Limit, TP/SL | On-chain confirmation delay |

---

## Red Flags Checklist (Exchange-Specific)

Before deploying to any exchange:

- [ ] Leverage tier limits verified for target position size
- [ ] Settlement/funding times accounted for in strategy timing
- [ ] Margin mode explicitly set and tested
- [ ] Gas/fee model includes worst-case costs
- [ ] Withdrawal timing modeled for cross-exchange strategies
- [ ] API rate limits will not be hit at planned order frequency
- [ ] Auto-deleveraging (ADL) scenario considered
- [ ] Exchange maintenance windows identified and handled

---

*Last Updated: 2026-02-08 (Seeded)*
*Next distillation will add live-encountered issues*
