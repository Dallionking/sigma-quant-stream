---
name: quant-prop-firm-compliance
description: "Rules and validation for all 14 supported prop firms and exchange risk compliance"
version: "2.0.0"
triggers:
  - "when validating prop firm compliance"
  - "when testing drawdown rules"
  - "when selecting prop firms for strategy"
  - "when dispatching compliance by market type"
---

# Quant Prop Firm Compliance

## Purpose

Validates strategy performance against compliance rules. For futures: prop firm rules (14 firms supported). For crypto: exchange risk rules (leverage tiers, liquidation buffers). Dispatches to the correct validator based on `profile.compliance.type`.

## Compliance Dispatch

```python
from abc import ABC, abstractmethod
import pandas as pd

class ComplianceValidator(ABC):
    """Abstract interface for all compliance validation."""

    @abstractmethod
    def validate(
        self,
        equity_curve: pd.Series,
        daily_pnl: pd.Series,
        positions: pd.DataFrame = None
    ) -> dict:
        """
        Validate strategy against compliance rules.
        Returns: {passes: bool, violations: list, details: dict}
        """
        ...

    @abstractmethod
    def get_rules_summary(self) -> dict:
        """Return human-readable rules summary."""
        ...


def get_compliance_validator(profile: dict) -> ComplianceValidator:
    """
    Dispatch to correct validator based on trading profile.

    Usage:
        validator = get_compliance_validator(profile)
        result = validator.validate(equity_curve, daily_pnl)
    """
    compliance_type = profile.get("compliance", {}).get("type", "prop_firm")

    if compliance_type == "prop_firm":
        return PropFirmValidator()  # This skill (below)
    elif compliance_type == "exchange":
        # See quant-exchange-compliance skill for ExchangeRiskValidator
        raise ImportError("Use ExchangeRiskValidator from quant-exchange-compliance skill")
    else:
        raise ValueError(f"Unknown compliance type: {compliance_type}")
```

> **For crypto exchange compliance**: See `quant-exchange-compliance` skill for `ExchangeRiskValidator`, leverage tier tables, liquidation buffer rules, and margin mode validation.

## When to Use

- After strategy passes robustness testing
- Before deploying to live prop accounts
- When selecting which firms to trade with
- When `profile.compliance.type == "prop_firm"` (futures)

## Supported Prop Firms (14)

| Firm | Daily Loss | Trailing DD | Consistency | Platform |
|------|------------|-------------|-------------|----------|
| **Apex 3.0** | None | 4% intraday | 30% windfall | Tradovate |
| **Topstep** | $1-3K | 3% (reduced) | 50% max/day | ProjectX |
| **TakeProfitTrader** | None | 8% EOD | 50% max/day | Tradovate |
| **Tradeify** | $1.25-3.75K | Varies | 35% standard | Tradovate |
| **Bulenox** | $1.5-2K | $2.5-3K | Varies | Tradovate |
| **Earn2Trade** | $2K | $2.5K | 50% | Tradovate |
| **MyFundedFX** | $2K | $3K | 50% | Tradovate |
| **Leeloo** | $1.5K | 6% | 50% | Tradovate |
| **OneUp Trader** | $1.5K | 6% | 50% | Tradovate |
| **The Funded Trader** | Varies | Varies | 50% | Tradovate |
| **BluSky** | Varies | Varies | Varies | Tradovate |
| **Funded Trading Plus** | Varies | Varies | Varies | Tradovate |
| **True Trader** | Varies | Varies | Varies | Tradovate |
| **FTMO** | N/A | N/A | N/A | **Not supported** (forex) |

## Rule Types

### 1. Daily Loss Limit
Maximum loss allowed in a single day. Breach = account violation.

### 2. Trailing Drawdown
- **Intraday trailing**: Moves with unrealized equity
- **EOD trailing**: Only locks at end of day
- **Fixed**: Static from starting balance

### 3. Consistency Rules
- **Windfall rule**: No single day > X% of total profit
- **Max daily profit**: Caps daily gains counting toward target

## Implementation

```python
from dataclasses import dataclass
from enum import Enum

class PropFirm(Enum):
    APEX = "apex"
    TOPSTEP = "topstep"
    TAKE_PROFIT = "take_profit_trader"
    BULENOX = "bulenox"
    EARN2TRADE = "earn2trade"
    # ... etc

@dataclass
class PropFirmRules:
    """Rules for a specific prop firm."""
    name: str
    daily_loss_limit: float | None  # $ or None
    trailing_dd_pct: float          # Percentage
    trailing_type: str              # 'intraday' | 'eod' | 'fixed'
    consistency_pct: float | None   # Max single day %
    account_size: float
    platform: str

PROP_FIRM_RULES = {
    PropFirm.APEX: PropFirmRules(
        name="Apex 3.0",
        daily_loss_limit=None,  # No daily limit
        trailing_dd_pct=0.04,   # 4% intraday
        trailing_type="intraday",
        consistency_pct=0.30,   # 30% windfall
        account_size=50000,
        platform="Tradovate"
    ),
    PropFirm.TOPSTEP: PropFirmRules(
        name="Topstep",
        daily_loss_limit=2000,  # $2K daily
        trailing_dd_pct=0.03,   # 3% reduced
        trailing_type="intraday",
        consistency_pct=0.50,   # 50% max/day
        account_size=50000,
        platform="ProjectX"
    ),
    # ... more firms
}

def validate_against_firm(
    equity_curve: pd.Series,
    daily_pnl: pd.Series,
    rules: PropFirmRules
) -> dict:
    """
    Validate strategy against a specific prop firm's rules.
    """
    violations = []

    # Check daily loss limit
    if rules.daily_loss_limit:
        worst_day = daily_pnl.min()
        if worst_day < -rules.daily_loss_limit:
            violations.append({
                'rule': 'daily_loss',
                'limit': rules.daily_loss_limit,
                'actual': worst_day
            })

    # Check trailing drawdown
    if rules.trailing_type == 'intraday':
        peak = equity_curve.expanding().max()
        dd = (equity_curve - peak) / rules.account_size
        max_dd = dd.min()
    else:  # EOD
        daily_equity = equity_curve.resample('D').last()
        peak = daily_equity.expanding().max()
        dd = (daily_equity - peak) / rules.account_size
        max_dd = dd.min()

    if abs(max_dd) > rules.trailing_dd_pct:
        violations.append({
            'rule': 'trailing_dd',
            'limit': rules.trailing_dd_pct,
            'actual': abs(max_dd)
        })

    # Check consistency
    if rules.consistency_pct:
        total_profit = max(0, equity_curve.iloc[-1] - rules.account_size)
        best_day = daily_pnl.max()
        if total_profit > 0 and best_day / total_profit > rules.consistency_pct:
            violations.append({
                'rule': 'consistency',
                'limit': rules.consistency_pct,
                'actual': best_day / total_profit
            })

    return {
        'firm': rules.name,
        'passes': len(violations) == 0,
        'violations': violations,
        'max_dd': abs(max_dd),
        'worst_day': daily_pnl.min(),
        'best_day': daily_pnl.max()
    }

def validate_all_firms(
    equity_curve: pd.Series,
    daily_pnl: pd.Series
) -> dict:
    """Validate against all 14 prop firms."""
    results = {}

    for firm, rules in PROP_FIRM_RULES.items():
        results[firm.value] = validate_against_firm(
            equity_curve, daily_pnl, rules
        )

    passed = [k for k, v in results.items() if v['passes']]

    return {
        'firms_tested': len(results),
        'firms_passed': len(passed),
        'passed_firms': passed,
        'results': results,
        'prop_firm_ready': len(passed) >= 3
    }
```

## Output Routing

| Result | Destination | Criteria |
|--------|-------------|----------|
| >= 3 firms pass | `prop_firm_ready/` | Production ready |
| 1-2 firms pass | `good/` | Needs adjustment |
| 0 firms pass | `rejected/` | Too risky |

## Common Gotchas

1. **Intraday vs EOD trailing**: Apex uses intraday (stricter)
2. **Consistency rules**: Single big day can violate
3. **Platform differences**: Topstep uses ProjectX, not Tradovate
4. **Account size matters**: Rules scale with account

---

## Multi-Market Compliance Abstraction

### Abstract ComplianceValidator Interface

Both prop firm validation (futures) and exchange risk validation (crypto) share a common interface:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd

@dataclass
class ComplianceResult:
    """Result from a compliance validation run."""
    passes: bool
    validator_name: str
    violations: list[dict]
    max_drawdown: float
    worst_day: float
    details: dict

class ComplianceValidator(ABC):
    """Abstract base for all compliance validators."""

    @abstractmethod
    def validate(
        self,
        equity_curve: pd.Series,
        daily_pnl: pd.Series
    ) -> ComplianceResult:
        """Validate strategy against compliance rules."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable validator name."""
        ...
```

### PropFirmValidator (Wraps Existing Logic)

The existing prop firm validation logic is wrapped in the `ComplianceValidator` interface:

```python
class PropFirmValidator(ComplianceValidator):
    """Validates against all 14 supported prop firm rule sets."""

    def validate(
        self,
        equity_curve: pd.Series,
        daily_pnl: pd.Series
    ) -> ComplianceResult:
        result = validate_all_firms(equity_curve, daily_pnl)
        return ComplianceResult(
            passes=result["prop_firm_ready"],
            validator_name=self.name(),
            violations=[v for r in result["results"].values() for v in r.get("violations", [])],
            max_drawdown=min(r["max_dd"] for r in result["results"].values()),
            worst_day=min(r["worst_day"] for r in result["results"].values()),
            details=result
        )

    def name(self) -> str:
        return "PropFirmValidator (14 firms)"
```

### ExchangeRiskValidator (Crypto)

Validates crypto strategies against exchange-specific risk rules:

```python
@dataclass
class ExchangeLeverageTier:
    """Exchange leverage tier (position size -> max leverage)."""
    max_notional_usd: float
    max_leverage: int
    maintenance_margin_pct: float

BINANCE_BTC_TIERS = [
    ExchangeLeverageTier(50_000, 125, 0.40),
    ExchangeLeverageTier(250_000, 100, 0.50),
    ExchangeLeverageTier(1_000_000, 50, 1.00),
    ExchangeLeverageTier(5_000_000, 20, 2.50),
    ExchangeLeverageTier(20_000_000, 10, 5.00),
]

class ExchangeRiskValidator(ComplianceValidator):
    """Validates against exchange leverage tiers and liquidation rules."""

    def __init__(
        self,
        exchange: str,
        leverage_tiers: list[ExchangeLeverageTier],
        max_leverage_used: int = 10,
        liquidation_buffer_pct: float = 5.0,
    ):
        self.exchange = exchange
        self.leverage_tiers = leverage_tiers
        self.max_leverage_used = max_leverage_used
        self.liquidation_buffer_pct = liquidation_buffer_pct

    def validate(
        self,
        equity_curve: pd.Series,
        daily_pnl: pd.Series
    ) -> ComplianceResult:
        violations = []

        # Check leverage is within allowed tier
        peak_notional = equity_curve.max() * self.max_leverage_used
        allowed_leverage = self._get_max_leverage(peak_notional)
        if self.max_leverage_used > allowed_leverage:
            violations.append({
                "rule": "leverage_tier",
                "limit": allowed_leverage,
                "actual": self.max_leverage_used,
            })

        # Check liquidation buffer
        peak = equity_curve.expanding().max()
        dd_pct = ((equity_curve - peak) / peak * 100).min()
        liquidation_pct = 100 / self.max_leverage_used
        buffer = liquidation_pct - abs(dd_pct)

        if buffer < self.liquidation_buffer_pct:
            violations.append({
                "rule": "liquidation_buffer",
                "limit": self.liquidation_buffer_pct,
                "actual": buffer,
            })

        return ComplianceResult(
            passes=len(violations) == 0,
            validator_name=self.name(),
            violations=violations,
            max_drawdown=abs(dd_pct),
            worst_day=daily_pnl.min(),
            details={"exchange": self.exchange, "leverage_used": self.max_leverage_used}
        )

    def _get_max_leverage(self, notional: float) -> int:
        for tier in self.leverage_tiers:
            if notional <= tier.max_notional_usd:
                return tier.max_leverage
        return self.leverage_tiers[-1].max_leverage

    def name(self) -> str:
        return f"ExchangeRiskValidator ({self.exchange})"
```

### Profile-Dispatched Validator Factory

```python
def get_validator(profile: dict) -> ComplianceValidator:
    """Return the correct ComplianceValidator based on the active profile."""
    market_type = profile.get("market_type", "futures")

    if market_type == "futures":
        return PropFirmValidator()
    elif market_type in ("crypto_cex", "crypto_dex"):
        exchange = profile.get("exchange", "binance")
        tiers = EXCHANGE_TIERS.get(exchange, BINANCE_BTC_TIERS)
        return ExchangeRiskValidator(
            exchange=exchange,
            leverage_tiers=tiers,
            max_leverage_used=profile.get("max_leverage", 10),
            liquidation_buffer_pct=profile.get("liquidation_buffer_pct", 5.0),
        )
    else:
        raise ValueError(f"Unknown market_type: {market_type}")
```

### Compliance Comparison

| Rule | Futures (Prop Firm) | Crypto CEX | Crypto DEX |
|------|---------------------|------------|------------|
| Daily Loss Limit | $1.5K-$3K (firm-specific) | N/A (exchange liquidates) | N/A |
| Trailing Drawdown | 3-8% (intraday or EOD) | N/A | N/A |
| Leverage Limit | Fixed by firm | Tiered by notional size | Fixed max (50x typical) |
| Liquidation Risk | Account violation | Auto-liquidation | Auto-liquidation |
| Consistency Rule | 30-50% max single day | N/A | N/A |

## Related Skills

- `quant-robustness-testing` -- Strategy stability
- `quant-metrics-calculation` -- Performance metrics
- `quant-exchange-compliance` -- Detailed exchange rule reference
- `quant-liquidation-analysis` -- EVT risk and cascade modeling
- `quant-crypto-cost-modeling` -- Crypto fee structure
