---
name: quant-exchange-compliance
description: "Exchange risk rules, leverage tiers, liquidation buffers, and position limits for crypto"
version: "1.0.0"
triggers:
  - "when validating crypto exchange risk rules"
  - "when checking leverage tier limits"
  - "when calculating liquidation distance"
  - "when setting position size limits for crypto"
---

# Quant Exchange Compliance

## Purpose

Replaces the prop firm compliance gate for crypto markets. Instead of prop firm rules (daily loss, trailing DD, consistency), crypto compliance validates against exchange-specific risk limits: leverage tiers, liquidation distance, position caps, and margin mode requirements.

## When to Use

- Before deploying any crypto strategy to an exchange
- When validating position sizing
- When checking leverage tier constraints
- When `profile.compliance.type == "exchange"`

## Leverage Tier Tables

### Binance Perpetuals (BTC/USDT)

| Position Size (USDT) | Max Leverage | Initial Margin | Maint. Margin |
|-----------------------|--------------|----------------|---------------|
| 0 - 50,000 | 125x | 0.80% | 0.40% |
| 50,000 - 250,000 | 100x | 1.00% | 0.50% |
| 250,000 - 1,000,000 | 50x | 2.00% | 1.00% |
| 1,000,000 - 5,000,000 | 20x | 5.00% | 2.50% |
| 5,000,000 - 20,000,000 | 10x | 10.00% | 5.00% |

### Hyperliquid (BTC)

| Position Size (USD) | Max Leverage |
|---------------------|--------------|
| 0 - 500,000 | 50x |
| 500,000 - 2,000,000 | 25x |
| 2,000,000 - 10,000,000 | 10x |
| 10,000,000+ | 5x |

### Bybit (BTC/USDT)

| Position Size (USDT) | Max Leverage |
|-----------------------|--------------|
| 0 - 100,000 | 100x |
| 100,000 - 500,000 | 50x |
| 500,000 - 2,000,000 | 25x |
| 2,000,000+ | 10x |

## Implementation

### Exchange Risk Validator

```python
from dataclasses import dataclass, field
from typing import Literal
import pandas as pd

@dataclass
class LeverageTier:
    """Single leverage tier for an exchange."""
    max_position_usd: float
    max_leverage: int
    initial_margin_pct: float
    maintenance_margin_pct: float

@dataclass
class ExchangeRiskRules:
    """Risk rules for a specific exchange."""
    name: str
    leverage_tiers: list[LeverageTier]
    margin_mode: Literal["cross", "isolated", "both"]
    min_liquidation_buffer_pct: float  # Minimum distance to liquidation
    max_position_usd: float            # Hard cap
    max_open_orders: int = 200
    funding_interval_h: int = 8

    def get_max_leverage(self, position_usd: float) -> int:
        """Get max allowed leverage for a given position size."""
        for tier in self.leverage_tiers:
            if position_usd <= tier.max_position_usd:
                return tier.max_leverage
        return self.leverage_tiers[-1].max_leverage

    def get_maintenance_margin(self, position_usd: float) -> float:
        """Get maintenance margin % for position size."""
        for tier in self.leverage_tiers:
            if position_usd <= tier.max_position_usd:
                return tier.maintenance_margin_pct
        return self.leverage_tiers[-1].maintenance_margin_pct


# Preset exchange rules
EXCHANGE_RULES = {
    "binance": ExchangeRiskRules(
        name="Binance",
        leverage_tiers=[
            LeverageTier(50000, 125, 0.80, 0.40),
            LeverageTier(250000, 100, 1.00, 0.50),
            LeverageTier(1000000, 50, 2.00, 1.00),
            LeverageTier(5000000, 20, 5.00, 2.50),
            LeverageTier(20000000, 10, 10.00, 5.00),
        ],
        margin_mode="both",
        min_liquidation_buffer_pct=0.5,
        max_position_usd=20000000
    ),
    "hyperliquid": ExchangeRiskRules(
        name="Hyperliquid",
        leverage_tiers=[
            LeverageTier(500000, 50, 2.00, 1.00),
            LeverageTier(2000000, 25, 4.00, 2.00),
            LeverageTier(10000000, 10, 10.00, 5.00),
            LeverageTier(50000000, 5, 20.00, 10.00),
        ],
        margin_mode="cross",  # Hyperliquid uses cross margin
        min_liquidation_buffer_pct=0.5,
        max_position_usd=50000000,
        funding_interval_h=1
    ),
    "bybit": ExchangeRiskRules(
        name="Bybit",
        leverage_tiers=[
            LeverageTier(100000, 100, 1.00, 0.50),
            LeverageTier(500000, 50, 2.00, 1.00),
            LeverageTier(2000000, 25, 4.00, 2.00),
            LeverageTier(10000000, 10, 10.00, 5.00),
        ],
        margin_mode="both",
        min_liquidation_buffer_pct=0.5,
        max_position_usd=10000000
    ),
}


class ExchangeRiskValidator:
    """
    Validates strategy against exchange-specific risk rules.
    Crypto equivalent of PropFirmValidator.
    """

    def __init__(self, exchange: str):
        if exchange not in EXCHANGE_RULES:
            raise ValueError(f"Exchange {exchange} not configured")
        self.rules = EXCHANGE_RULES[exchange]

    def validate_position(
        self,
        position_usd: float,
        leverage: int,
        entry_price: float,
        margin_mode: str = "isolated"
    ) -> dict:
        """Validate a single position against exchange rules."""
        violations = []

        # Check position size limit
        if position_usd > self.rules.max_position_usd:
            violations.append({
                "rule": "max_position",
                "limit": self.rules.max_position_usd,
                "actual": position_usd
            })

        # Check leverage tier
        max_lev = self.rules.get_max_leverage(position_usd)
        if leverage > max_lev:
            violations.append({
                "rule": "leverage_tier",
                "limit": max_lev,
                "actual": leverage
            })

        # Check liquidation distance
        maint_margin = self.rules.get_maintenance_margin(position_usd)
        liq_distance_pct = (1 / leverage - maint_margin / 100) * 100
        if liq_distance_pct < self.rules.min_liquidation_buffer_pct:
            violations.append({
                "rule": "liquidation_buffer",
                "limit": self.rules.min_liquidation_buffer_pct,
                "actual": liq_distance_pct
            })

        # Check margin mode
        if margin_mode not in ("cross", "isolated") or \
           (self.rules.margin_mode != "both" and margin_mode != self.rules.margin_mode):
            violations.append({
                "rule": "margin_mode",
                "required": self.rules.margin_mode,
                "actual": margin_mode
            })

        return {
            "exchange": self.rules.name,
            "passes": len(violations) == 0,
            "violations": violations,
            "max_leverage": max_lev,
            "liq_distance_pct": round(liq_distance_pct, 2),
            "maint_margin_pct": maint_margin
        }

    def validate_backtest(
        self,
        equity_curve: pd.Series,
        positions: pd.DataFrame,
        initial_balance: float
    ) -> dict:
        """
        Validate full backtest against exchange rules.

        Args:
            equity_curve: Equity over time
            positions: DataFrame with 'size_usd', 'leverage', 'entry_price'
        """
        violations = []
        max_drawdown_pct = 0.0

        # Check each position
        for _, pos in positions.iterrows():
            result = self.validate_position(
                pos["size_usd"], pos["leverage"], pos["entry_price"]
            )
            if not result["passes"]:
                violations.extend(result["violations"])

        # Check max drawdown vs margin
        peak = equity_curve.expanding().max()
        dd = (equity_curve - peak) / peak * 100
        max_drawdown_pct = abs(dd.min())

        return {
            "exchange": self.rules.name,
            "passes": len(violations) == 0,
            "violation_count": len(violations),
            "violations": violations[:10],  # Top 10
            "max_drawdown_pct": round(max_drawdown_pct, 2)
        }
```

### Margin Mode Implications

```python
def margin_mode_comparison(
    position_usd: float,
    leverage: int,
    account_balance: float
) -> dict:
    """
    Compare cross vs isolated margin for a position.
    """
    margin_required = position_usd / leverage

    return {
        "isolated": {
            "margin_locked": margin_required,
            "max_loss": margin_required,  # Liquidation = lose margin only
            "remaining_balance": account_balance - margin_required,
            "can_open_new": True
        },
        "cross": {
            "margin_locked": margin_required,
            "max_loss": account_balance,  # Entire account at risk
            "remaining_balance": 0,  # All margin shared
            "can_open_new": True,  # Uses same margin pool
            "note": "Liquidation uses full account balance"
        }
    }
```

## Common Pitfalls

1. **Leverage tiers are tiered, not flat** — 125x only applies to first 50K on Binance
2. **Cross margin = full account risk** — One position can liquidate entire account
3. **Funding rate spikes** — High leverage + adverse funding can approach liquidation
4. **ADL (Auto-Deleveraging)** — Profitable positions can be force-closed in extreme markets
5. **Exchange maintenance windows** — Binance has scheduled downtime; Hyperliquid doesn't

## Related Skills

- `quant-prop-firm-compliance` — Abstract ComplianceValidator interface
- `quant-crypto-cost-modeling` — Fee structure per exchange
- `quant-liquidation-analysis` — Cascade risk modeling
