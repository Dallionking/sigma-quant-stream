# Prop Firm Gotchas - Compliance Issues & Lessons

> Document issues discovered during prop firm validation.
> Critical for ensuring strategies are actually tradeable.

---

## Format

```
### [TIMESTAMP] Gotcha Title
**Firms Affected**: Apex, Topstep, FTMO, etc.
**Rule Violated**: Which specific rule
**Strategy Impact**: How it affects the strategy

Description and solution.
```

---

## Common Gotchas by Firm

### Apex Trader Funding
- **Trailing Max Drawdown**: Trails from highest equity, not balance
- **Daily Loss Limit**: 2.5% of account max
- **Consistency Rule**: 30% max profit from single day

### Topstep
- **Profit Target**: Must hit before withdrawal
- **Trading Days**: Minimum number required
- **Position Limits**: Max contracts varies by account size

### FTMO
- **Max Daily Loss**: 5% hard limit
- **Max Total Loss**: 10% hard limit
- **Trading Days**: 4 minimum per challenge phase

### Earn2Trade
- **Trailing Drawdown**: EOD trailing
- **Scaling**: Start with fewer contracts

---

## Entries

<!-- New entries are prepended below this line -->

