---
name: quant-funding-rate-strategies
description: "Funding rate mean-reversion, basis trades, and delta-neutral carry strategies"
version: "1.0.0"
triggers:
  - "when building funding rate strategies"
  - "when implementing delta-neutral carry"
  - "when analyzing basis trades"
  - "when calculating annualized funding yield"
---

# Quant Funding Rate Strategies

## Purpose

Implements strategies that exploit the perpetual swap funding mechanism. Funding rates are one of crypto's most reliable edges: they mean-revert, are observable in real-time, and offer carry opportunities unavailable in traditional markets.

## When to Use

- When building funding rate mean-reversion strategies
- When setting up delta-neutral carry trades
- When analyzing cross-exchange funding divergence
- When calculating risk-adjusted yield from funding

## Core Concepts

### How Funding Works

```
Every 8h (Binance/Bybit) or 1h (Hyperliquid):
  - If funding rate > 0: longs PAY shorts
  - If funding rate < 0: shorts PAY longs
  - Payment = position_size * funding_rate
  - Funding rate ≈ (perp_price - spot_price) / spot_price + interest
```

### Historical Funding Rate Stats

| Asset | Avg Funding (8h) | Annualized | Std Dev | Skew |
|-------|-------------------|------------|---------|------|
| BTC | +0.010% | +13.1% | 0.03% | +2.1 (right) |
| ETH | +0.012% | +15.7% | 0.04% | +2.5 |
| SOL | +0.015% | +19.7% | 0.06% | +3.0 |
| Altcoins | +0.02-0.05% | +26-65% | 0.1%+ | +4.0+ |

*Positive skew = more extreme positive than negative, favoring short-side carry*

## Strategy 1: Funding Rate Mean-Reversion

```python
import pandas as pd
import numpy as np

class FundingRateMeanReversion:
    """
    Fade extreme funding rates.
    When funding is extremely positive (longs paying), go short.
    When extremely negative (shorts paying), go long.
    Funding mean-reverts within 1-3 days typically.
    """

    def __init__(
        self,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5,
        lookback: int = 42,  # 42 x 8h = 14 days
        max_holding_periods: int = 9  # 9 x 8h = 3 days
    ):
        self.entry_zscore = entry_zscore
        self.exit_zscore = exit_zscore
        self.lookback = lookback
        self.max_holding_periods = max_holding_periods

    def generate_signals(
        self,
        funding_rates: pd.Series,
        prices: pd.Series
    ) -> pd.DataFrame:
        """
        Generate trading signals from funding rate data.

        Args:
            funding_rates: Series of funding rates (one per interval)
            prices: Price series aligned with funding rates
        """
        # Z-score of funding rate
        rolling_mean = funding_rates.rolling(self.lookback).mean()
        rolling_std = funding_rates.rolling(self.lookback).std()
        z_score = (funding_rates - rolling_mean) / rolling_std

        signals = pd.Series(0, index=funding_rates.index)
        position = 0
        entry_idx = 0

        for i in range(self.lookback, len(funding_rates)):
            z = z_score.iloc[i]

            if position == 0:
                # Entry
                if z > self.entry_zscore:
                    signals.iloc[i] = -1  # Short (fade positive funding)
                    position = -1
                    entry_idx = i
                elif z < -self.entry_zscore:
                    signals.iloc[i] = 1   # Long (fade negative funding)
                    position = 1
                    entry_idx = i
            else:
                # Exit conditions
                bars_held = i - entry_idx
                should_exit = (
                    abs(z) < self.exit_zscore or  # Mean reverted
                    bars_held >= self.max_holding_periods or  # Time stop
                    (position == 1 and z > self.entry_zscore) or  # Reverse signal
                    (position == -1 and z < -self.entry_zscore)
                )
                if should_exit:
                    signals.iloc[i] = 0
                    position = 0
                else:
                    signals.iloc[i] = position

        return pd.DataFrame({
            "signal": signals,
            "z_score": z_score,
            "funding_rate": funding_rates
        })
```

## Strategy 2: Delta-Neutral Carry

```python
class DeltaNeutralCarry:
    """
    Long spot + short perp (or vice versa) to earn funding.
    Direction risk is hedged; profit comes from funding payments.

    Best when: funding is consistently positive (contango = longs pay shorts)
    Setup: Buy 1 BTC spot, Short 1 BTC perp → collect funding as short
    """

    def __init__(
        self,
        min_funding_rate: float = 0.01,  # 0.01% per interval minimum
        entry_basis_bps: float = 5.0,    # Minimum perp premium to enter
        exit_basis_bps: float = -2.0,    # Exit if basis inverts
        funding_interval_h: int = 8
    ):
        self.min_funding_rate = min_funding_rate
        self.entry_basis_bps = entry_basis_bps
        self.exit_basis_bps = exit_basis_bps
        self.funding_interval_h = funding_interval_h

    def calculate_basis(
        self,
        spot_price: float,
        perp_price: float
    ) -> float:
        """Basis in bps. Positive = perp premium (contango)."""
        return (perp_price - spot_price) / spot_price * 10000

    def calculate_yield(
        self,
        funding_rates: pd.Series,
        holding_days: int = 30
    ) -> dict:
        """
        Calculate expected yield from carry trade.
        """
        intervals_per_day = 24 / self.funding_interval_h
        total_intervals = holding_days * intervals_per_day

        avg_funding = funding_rates.tail(int(total_intervals)).mean()
        total_yield = avg_funding * total_intervals
        annualized = avg_funding * intervals_per_day * 365

        return {
            "avg_funding_rate_pct": round(avg_funding, 4),
            "total_yield_pct": round(total_yield, 2),
            "annualized_yield_pct": round(annualized, 2),
            "holding_days": holding_days,
            "funding_payments": int(total_intervals)
        }

    def generate_signals(
        self,
        spot_prices: pd.Series,
        perp_prices: pd.Series,
        funding_rates: pd.Series
    ) -> pd.DataFrame:
        """
        Generate carry trade entry/exit signals.
        """
        basis = (perp_prices - spot_prices) / spot_prices * 10000

        signals = pd.Series(0, index=spot_prices.index)
        position = 0

        for i in range(1, len(spot_prices)):
            if position == 0:
                # Enter when basis is positive and funding is high
                if (basis.iloc[i] > self.entry_basis_bps and
                    funding_rates.iloc[i] > self.min_funding_rate):
                    signals.iloc[i] = 1  # 1 = carry active (long spot, short perp)
                    position = 1
            else:
                # Exit when basis inverts or funding turns negative
                if (basis.iloc[i] < self.exit_basis_bps or
                    funding_rates.iloc[i] < -self.min_funding_rate):
                    signals.iloc[i] = 0
                    position = 0
                else:
                    signals.iloc[i] = 1

        return pd.DataFrame({
            "signal": signals,
            "basis_bps": basis,
            "funding_rate": funding_rates
        })
```

## Strategy 3: Cross-Exchange Funding Arb

```python
def cross_exchange_funding_opportunity(
    funding_rates: dict[str, float],
    fee_table: dict[str, dict],
    position_usd: float = 10000
) -> list[dict]:
    """
    Find funding rate discrepancies across exchanges.
    Go long on exchange with lower funding, short on higher.

    Example: Binance funding = +0.05%, Bybit = +0.01%
    → Short Binance (receive 0.05%), Long Bybit (pay 0.01%) = net +0.04%
    """
    exchanges = list(funding_rates.keys())
    opportunities = []

    for i, ex_short in enumerate(exchanges):
        for j, ex_long in enumerate(exchanges):
            if i == j:
                continue

            # Short on ex_short, long on ex_long
            funding_received = funding_rates[ex_short]  # Positive = shorts receive
            funding_paid = funding_rates[ex_long]        # Positive = longs pay

            net_funding = funding_received - funding_paid

            if net_funding <= 0:
                continue

            # Deduct trading costs (entry only; hold until funding normalizes)
            entry_cost_bps = (
                fee_table[ex_short]["taker"] * 10000 +
                fee_table[ex_long]["taker"] * 10000
            )
            net_funding_bps = net_funding * 100  # Convert % to bps

            if net_funding_bps > entry_cost_bps * 0.5:  # Need to cover costs fast
                annualized = net_funding * (24 / 8) * 365  # Assuming 8h intervals
                opportunities.append({
                    "short_exchange": ex_short,
                    "long_exchange": ex_long,
                    "net_funding_pct": round(net_funding, 4),
                    "annualized_pct": round(annualized, 2),
                    "entry_cost_bps": round(entry_cost_bps, 2),
                    "breakeven_intervals": round(entry_cost_bps / net_funding_bps, 1)
                })

    return sorted(opportunities, key=lambda x: -x["annualized_pct"])
```

## Risk: Funding Rate Spike Scenarios

```python
def funding_spike_risk(
    position_usd: float,
    leverage: int,
    worst_case_funding_pct: float = 0.3,  # Extreme: 0.3% per 8h
    intervals_per_day: float = 3
) -> dict:
    """
    Calculate worst-case funding cost.
    During extreme volatility, funding can spike to 0.1-0.5% per interval.
    """
    daily_cost_worst = position_usd * worst_case_funding_pct / 100 * intervals_per_day
    margin = position_usd / leverage
    days_to_liquidation = margin / daily_cost_worst

    return {
        "daily_funding_cost_usd": round(daily_cost_worst, 2),
        "margin_usd": round(margin, 2),
        "days_to_margin_erosion": round(days_to_liquidation, 1),
        "warning": days_to_liquidation < 7,
        "recommendation": "Reduce leverage" if days_to_liquidation < 7 else "OK"
    }
```

## Common Pitfalls

1. **Funding rate != guaranteed income** — Adverse price moves can exceed funding earned
2. **Delta-neutral isn't risk-free** — Execution slippage on both legs, basis risk remains
3. **Funding frequency changes** — Binance moved some pairs to 4h; Hyperliquid is 1h
4. **Exchange counterparty risk** — Funds locked on exchange; not your keys, not your coins
5. **Carry crowding** — When too many do delta-neutral carry, funding compresses to zero

## Related Skills

- `quant-crypto-indicators` — Funding rate oscillator indicator
- `quant-crypto-cost-modeling` — Funding as cost component
- `quant-cross-exchange-arb` — Cross-exchange basis trading
