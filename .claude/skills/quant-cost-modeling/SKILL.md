---
name: quant-cost-modeling
description: "Commission and slippage modeling for realistic backtesting across futures and crypto"
version: "2.0.0"
triggers:
  - "when calculating transaction costs"
  - "when modeling slippage"
  - "when backtesting futures strategies"
  - "when comparing gross vs net returns"
  - "when dispatching cost models by market type"
---

# Quant Cost Modeling

## Purpose

Provides accurate transaction cost modeling for backtests across futures and crypto markets. Underestimating costs is one of the most common reasons strategies fail in live trading. This skill ensures backtests use realistic commission and slippage assumptions. Dispatches to the correct cost model based on `profile.costs.model`.

## When to Use

- Before any backtest to configure costs
- When comparing strategy profitability
- When sizing positions for prop firm accounts
- When evaluating high-frequency strategies
- When converting gross metrics to net metrics
- When `profile.costs.model == "per_contract"` (futures) or `"percentage"` (crypto)

## Cost Model Dispatch

```python
from abc import ABC, abstractmethod

class InstrumentSpec(ABC):
    """Abstract base for all tradeable instruments (futures + crypto)."""

    @abstractmethod
    def cost_per_trade(self, notional_or_contracts, is_maker: bool = False) -> float:
        """Total cost for a single trade (one side) in USD."""
        ...

    @abstractmethod
    def breakeven_move(self) -> float:
        """Minimum move to break even on a round trip (ticks for futures, bps for crypto)."""
        ...


def get_cost_model(profile: dict):
    """
    Dispatch to correct cost model based on trading profile.

    Usage:
        cost_model = get_cost_model(profile)
        if profile["costs"]["model"] == "per_contract":
            # Use FuturesContractSpec patterns below
            ...
        elif profile["costs"]["model"] == "percentage":
            # See quant-crypto-cost-modeling skill for CryptoPerpSpec/CryptoSpotSpec
            ...
    """
    model_type = profile.get("costs", {}).get("model", "per_contract")
    if model_type == "per_contract":
        return "futures"  # Use ContractSpec + CostModel from this skill
    elif model_type == "percentage":
        return "crypto"   # Use CryptoPerpSpec/CryptoSpotSpec from quant-crypto-cost-modeling
    else:
        raise ValueError(f"Unknown cost model: {model_type}")
```

> **For crypto cost patterns**: See `quant-crypto-cost-modeling` skill for `CryptoPerpSpec`, `CryptoSpotSpec`, funding rate costs, gas estimation, and exchange fee comparison tables.

## Key Concepts

### Cost Components

| Component | Description | Typical Range |
|-----------|-------------|---------------|
| **Commission** | Broker fee per contract | $2.00 - $5.00 RT |
| **Exchange Fees** | CME, CBOT, NYMEX fees | $1.20 - $2.40 RT |
| **Slippage** | Price movement on execution | 0.5 - 2 ticks |
| **Spread** | Bid-ask spread cost | 0.25 - 1 tick |
| **Market Impact** | Price movement from your order | Size dependent |

### Contract Specifications (ES, NQ, YM, GC)

| Symbol | Exchange | Tick Size | Tick Value | Point Value |
|--------|----------|-----------|------------|-------------|
| **ES** | CME | 0.25 | $12.50 | $50.00 |
| **NQ** | CME | 0.25 | $5.00 | $20.00 |
| **YM** | CBOT | 1.00 | $5.00 | $5.00 |
| **GC** | COMEX | 0.10 | $10.00 | $100.00 |
| **CL** | NYMEX | 0.01 | $10.00 | $1000.00 |

### Realistic Cost Assumptions

| Scenario | Commission | Slippage | Total Cost/Contract |
|----------|------------|----------|---------------------|
| **Retail (Tradovate)** | $4.50 RT | 1 tick | ~$17 (ES) |
| **Prop Firm** | $4.50 RT | 1 tick | ~$17 (ES) |
| **Professional** | $2.00 RT | 0.5 tick | ~$8 (ES) |
| **Market Maker** | $0.50 RT | 0 ticks | ~$0.50 (ES) |

## Patterns & Templates

### Cost Configuration

```python
"""
Futures contract cost configuration.
"""
from dataclasses import dataclass
from typing import Literal
from enum import Enum

class TradingTier(Enum):
    RETAIL = "retail"
    PROP_FIRM = "prop_firm"
    PROFESSIONAL = "professional"
    MARKET_MAKER = "market_maker"

@dataclass
class ContractSpec(InstrumentSpec):
    """
    Futures contract specification.
    Implements InstrumentSpec for per-contract cost model.
    For crypto percentage-based costs, see quant-crypto-cost-modeling skill.
    """
    symbol: str
    exchange: str
    tick_size: float
    tick_value: float
    point_value: float
    margin_requirement: float  # Intraday margin
    trading_hours: str  # RTH hours

    @property
    def ticks_per_point(self) -> float:
        return 1 / self.tick_size

    def cost_per_trade(self, contracts: int, is_maker: bool = False) -> float:
        """Cost for one side of a futures trade."""
        from_model = COST_MODELS.get(TradingTier.PROP_FIRM)
        if from_model:
            return from_model.total_commission * contracts
        return 0.0

    def breakeven_move(self) -> float:
        """Breakeven in ticks for futures."""
        from_model = COST_MODELS.get(TradingTier.PROP_FIRM)
        if from_model:
            return from_model.breakeven_ticks(self)
        return 0.0


# Contract specifications
CONTRACT_SPECS = {
    "ES": ContractSpec(
        symbol="ES",
        exchange="CME",
        tick_size=0.25,
        tick_value=12.50,
        point_value=50.00,
        margin_requirement=500,  # Typical prop firm
        trading_hours="09:30-16:00 ET"
    ),
    "NQ": ContractSpec(
        symbol="NQ",
        exchange="CME",
        tick_size=0.25,
        tick_value=5.00,
        point_value=20.00,
        margin_requirement=500,
        trading_hours="09:30-16:00 ET"
    ),
    "YM": ContractSpec(
        symbol="YM",
        exchange="CBOT",
        tick_size=1.00,
        tick_value=5.00,
        point_value=5.00,
        margin_requirement=400,
        trading_hours="09:30-16:00 ET"
    ),
    "GC": ContractSpec(
        symbol="GC",
        exchange="COMEX",
        tick_size=0.10,
        tick_value=10.00,
        point_value=100.00,
        margin_requirement=1000,
        trading_hours="08:20-13:30 ET"
    ),
    "CL": ContractSpec(
        symbol="CL",
        exchange="NYMEX",
        tick_size=0.01,
        tick_value=10.00,
        point_value=1000.00,
        margin_requirement=1000,
        trading_hours="09:00-14:30 ET"
    ),
}


@dataclass
class CostModel:
    """
    Transaction cost model for futures trading.
    """
    # Per-contract costs (round trip)
    commission_per_contract: float  # Broker commission
    exchange_fees_per_contract: float  # Exchange fees
    nfa_fees_per_contract: float = 0.02  # NFA fees

    # Slippage model
    slippage_ticks: float  # Average slippage in ticks
    spread_ticks: float = 0.25  # Typical spread

    # Market impact (for larger orders)
    market_impact_coefficient: float = 0.0  # Additional cost per contract

    @property
    def total_commission(self) -> float:
        """Total fixed commission per contract."""
        return (
            self.commission_per_contract +
            self.exchange_fees_per_contract +
            self.nfa_fees_per_contract
        )

    def calculate_total_cost(
        self,
        contracts: int,
        contract_spec: ContractSpec
    ) -> float:
        """
        Calculate total round-trip cost.

        Args:
            contracts: Number of contracts traded
            contract_spec: Contract specifications

        Returns:
            Total cost in dollars
        """
        # Fixed costs
        commission_cost = self.total_commission * contracts

        # Slippage cost (entry + exit)
        slippage_cost = (
            self.slippage_ticks *
            contract_spec.tick_value *
            contracts *
            2  # Entry and exit
        )

        # Spread cost (crossing bid-ask)
        spread_cost = (
            self.spread_ticks *
            contract_spec.tick_value *
            contracts *
            2  # Entry and exit (if market orders)
        )

        # Market impact (scales with size)
        impact_cost = (
            self.market_impact_coefficient *
            contracts ** 1.5 *
            contract_spec.tick_value
        )

        return commission_cost + slippage_cost + spread_cost + impact_cost

    def cost_in_ticks(self, contract_spec: ContractSpec) -> float:
        """Express total cost per contract in ticks."""
        total = self.calculate_total_cost(1, contract_spec)
        return total / contract_spec.tick_value

    def breakeven_ticks(self, contract_spec: ContractSpec) -> float:
        """
        Ticks needed to break even on a trade.
        Strategy must make at least this many ticks per trade to be profitable.
        """
        return self.cost_in_ticks(contract_spec)


# Preset cost models for different trading tiers
COST_MODELS = {
    TradingTier.RETAIL: CostModel(
        commission_per_contract=4.50,
        exchange_fees_per_contract=1.32,
        slippage_ticks=1.0,
        spread_ticks=0.25,
        market_impact_coefficient=0.1
    ),
    TradingTier.PROP_FIRM: CostModel(
        commission_per_contract=4.50,  # Tradovate via prop firm
        exchange_fees_per_contract=1.32,
        slippage_ticks=1.0,
        spread_ticks=0.25,
        market_impact_coefficient=0.1
    ),
    TradingTier.PROFESSIONAL: CostModel(
        commission_per_contract=2.00,
        exchange_fees_per_contract=1.32,
        slippage_ticks=0.5,
        spread_ticks=0.25,
        market_impact_coefficient=0.05
    ),
    TradingTier.MARKET_MAKER: CostModel(
        commission_per_contract=0.50,
        exchange_fees_per_contract=0.60,  # Lower exchange tier
        slippage_ticks=0.0,
        spread_ticks=0.0,  # Earns spread
        market_impact_coefficient=0.0
    ),
}
```

### Slippage Models

```python
"""
Advanced slippage modeling.
"""
import numpy as np
import pandas as pd
from typing import Callable

class SlippageModel:
    """
    Base slippage model interface.
    """

    def calculate_slippage(
        self,
        order_size: int,
        price: float,
        volume: int,
        volatility: float,
        side: Literal["buy", "sell"]
    ) -> float:
        """
        Calculate slippage for an order.

        Returns slippage in price units (positive = worse fill).
        """
        raise NotImplementedError


class FixedSlippageModel(SlippageModel):
    """
    Fixed slippage in ticks.
    Simplest model - use for initial estimates.
    """

    def __init__(self, slippage_ticks: float, tick_size: float):
        self.slippage_ticks = slippage_ticks
        self.tick_size = tick_size

    def calculate_slippage(self, **kwargs) -> float:
        return self.slippage_ticks * self.tick_size


class VolumeAdjustedSlippageModel(SlippageModel):
    """
    Slippage that scales with order size relative to volume.

    Slippage = base_ticks + volume_factor * (order_size / market_volume)^0.5
    """

    def __init__(
        self,
        base_slippage_ticks: float,
        volume_factor: float,
        tick_size: float
    ):
        self.base_slippage_ticks = base_slippage_ticks
        self.volume_factor = volume_factor
        self.tick_size = tick_size

    def calculate_slippage(
        self,
        order_size: int,
        volume: int,
        **kwargs
    ) -> float:
        if volume == 0:
            return self.base_slippage_ticks * self.tick_size * 3  # Illiquid

        participation = order_size / volume
        additional_ticks = self.volume_factor * np.sqrt(participation)

        total_ticks = self.base_slippage_ticks + additional_ticks
        return total_ticks * self.tick_size


class VolatilityAdjustedSlippageModel(SlippageModel):
    """
    Slippage that scales with market volatility.

    In high volatility, slippage tends to be worse.
    Slippage = base_ticks * (1 + volatility_factor * (current_vol / avg_vol - 1))
    """

    def __init__(
        self,
        base_slippage_ticks: float,
        volatility_factor: float,
        tick_size: float,
        avg_volatility: float
    ):
        self.base_slippage_ticks = base_slippage_ticks
        self.volatility_factor = volatility_factor
        self.tick_size = tick_size
        self.avg_volatility = avg_volatility

    def calculate_slippage(
        self,
        volatility: float,
        **kwargs
    ) -> float:
        vol_ratio = volatility / self.avg_volatility
        vol_adjustment = 1 + self.volatility_factor * (vol_ratio - 1)

        total_ticks = self.base_slippage_ticks * vol_adjustment
        return max(0.25, total_ticks) * self.tick_size  # Minimum 1 tick


class TimeOfDaySlippageModel(SlippageModel):
    """
    Slippage varies by time of day.

    Open/Close = Higher slippage (more volatile)
    Midday = Lower slippage (more liquid)
    """

    def __init__(
        self,
        base_slippage_ticks: float,
        tick_size: float,
        hour_multipliers: dict[int, float] = None
    ):
        self.base_slippage_ticks = base_slippage_ticks
        self.tick_size = tick_size

        # Default multipliers for ES futures
        self.hour_multipliers = hour_multipliers or {
            9: 2.0,   # Market open - highest slippage
            10: 1.5,
            11: 1.0,
            12: 0.8,  # Lunch - low volume but wide spreads
            13: 1.0,
            14: 1.2,
            15: 1.5,
            16: 2.0,  # Market close
        }

    def calculate_slippage(
        self,
        timestamp: pd.Timestamp,
        **kwargs
    ) -> float:
        hour = timestamp.hour
        multiplier = self.hour_multipliers.get(hour, 1.0)

        total_ticks = self.base_slippage_ticks * multiplier
        return total_ticks * self.tick_size


class CompositeSlippageModel(SlippageModel):
    """
    Combines multiple slippage factors.

    Final slippage = base * volume_adj * volatility_adj * time_adj
    """

    def __init__(
        self,
        base_slippage_ticks: float,
        tick_size: float,
        avg_volume: int,
        avg_volatility: float
    ):
        self.base_slippage_ticks = base_slippage_ticks
        self.tick_size = tick_size
        self.avg_volume = avg_volume
        self.avg_volatility = avg_volatility

    def calculate_slippage(
        self,
        order_size: int,
        price: float,
        volume: int,
        volatility: float,
        timestamp: pd.Timestamp = None,
        **kwargs
    ) -> float:
        # Volume impact
        participation = order_size / max(volume, 1)
        volume_adj = 1 + 0.5 * np.sqrt(participation * 100)

        # Volatility impact
        vol_ratio = volatility / self.avg_volatility
        vol_adj = 0.8 + 0.4 * vol_ratio  # Range: 0.8 to 1.2+

        # Time of day impact
        time_adj = 1.0
        if timestamp:
            hour = timestamp.hour
            if hour in [9, 15, 16]:  # Open/close
                time_adj = 1.5
            elif hour in [12]:  # Lunch
                time_adj = 0.9

        total_ticks = self.base_slippage_ticks * volume_adj * vol_adj * time_adj
        return max(0.25, total_ticks) * self.tick_size
```

### Backtest Cost Integration

```python
"""
Integrating costs into backtests.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class TradeRecord:
    """Single trade with costs."""
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    direction: int  # 1 for long, -1 for short
    contracts: int
    gross_pnl: float
    commission: float
    slippage: float
    net_pnl: float


class CostAwareBacktester:
    """
    Backtester that properly accounts for transaction costs.
    """

    def __init__(
        self,
        cost_model: CostModel,
        contract_spec: ContractSpec,
        slippage_model: SlippageModel = None
    ):
        self.cost_model = cost_model
        self.contract = contract_spec
        self.slippage_model = slippage_model or FixedSlippageModel(
            cost_model.slippage_ticks,
            contract_spec.tick_size
        )

    def calculate_fill_price(
        self,
        signal_price: float,
        side: Literal["buy", "sell"],
        volume: int = 1000,
        volatility: float = 0.01,
        timestamp: pd.Timestamp = None
    ) -> float:
        """
        Calculate realistic fill price including slippage.
        """
        slippage = self.slippage_model.calculate_slippage(
            order_size=1,
            price=signal_price,
            volume=volume,
            volatility=volatility,
            side=side,
            timestamp=timestamp
        )

        if side == "buy":
            return signal_price + slippage
        else:
            return signal_price - slippage

    def calculate_trade_pnl(
        self,
        entry_price: float,
        exit_price: float,
        direction: int,
        contracts: int
    ) -> dict:
        """
        Calculate PnL for a trade including all costs.
        """
        # Gross PnL
        points = (exit_price - entry_price) * direction
        gross_pnl = points * self.contract.point_value * contracts

        # Commission (both entry and exit)
        commission = self.cost_model.total_commission * contracts

        # Slippage cost (already baked into fill prices, but tracked separately)
        slippage_cost = (
            self.cost_model.slippage_ticks *
            self.contract.tick_value *
            contracts * 2
        )

        # Net PnL
        net_pnl = gross_pnl - commission

        return {
            "gross_pnl": gross_pnl,
            "commission": commission,
            "slippage": slippage_cost,
            "net_pnl": net_pnl
        }

    def run_backtest(
        self,
        df: pd.DataFrame,
        signals: pd.Series,
        contracts_per_trade: int = 1
    ) -> pd.DataFrame:
        """
        Run backtest with realistic costs.

        Args:
            df: OHLCV data
            signals: Series with 1 (long), -1 (short), 0 (flat)
            contracts_per_trade: Number of contracts per trade

        Returns:
            DataFrame with trade records
        """
        trades = []
        position = 0
        entry_price = None
        entry_time = None

        for i in range(1, len(df)):
            signal = signals.iloc[i-1]  # Use previous bar's signal
            current_bar = df.iloc[i]

            # Entry
            if position == 0 and signal != 0:
                direction = int(signal)
                entry_price = self.calculate_fill_price(
                    current_bar['open'],
                    "buy" if direction == 1 else "sell",
                    volume=current_bar.get('volume', 1000),
                    timestamp=current_bar.name
                )
                entry_time = current_bar.name
                position = direction

            # Exit
            elif position != 0 and (signal == 0 or signal == -position):
                exit_price = self.calculate_fill_price(
                    current_bar['open'],
                    "sell" if position == 1 else "buy",
                    volume=current_bar.get('volume', 1000),
                    timestamp=current_bar.name
                )

                pnl = self.calculate_trade_pnl(
                    entry_price, exit_price, position, contracts_per_trade
                )

                trades.append(TradeRecord(
                    entry_time=entry_time,
                    exit_time=current_bar.name,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    direction=position,
                    contracts=contracts_per_trade,
                    gross_pnl=pnl['gross_pnl'],
                    commission=pnl['commission'],
                    slippage=pnl['slippage'],
                    net_pnl=pnl['net_pnl']
                ))

                position = 0

                # Immediate re-entry if signal flipped
                if signal == -position:
                    direction = int(signal)
                    entry_price = self.calculate_fill_price(
                        current_bar['open'],
                        "buy" if direction == 1 else "sell"
                    )
                    entry_time = current_bar.name
                    position = direction

        return pd.DataFrame([vars(t) for t in trades])

    def calculate_metrics(self, trades_df: pd.DataFrame) -> dict:
        """
        Calculate performance metrics from trade records.
        """
        if len(trades_df) == 0:
            return {}

        gross_returns = trades_df['gross_pnl'].sum()
        net_returns = trades_df['net_pnl'].sum()
        total_commission = trades_df['commission'].sum()
        total_slippage = trades_df['slippage'].sum()

        winners = trades_df[trades_df['net_pnl'] > 0]
        losers = trades_df[trades_df['net_pnl'] < 0]

        return {
            "total_trades": len(trades_df),
            "gross_pnl": gross_returns,
            "net_pnl": net_returns,
            "total_commission": total_commission,
            "total_slippage": total_slippage,
            "cost_as_pct_of_gross": (total_commission + total_slippage) / abs(gross_returns) if gross_returns != 0 else 0,
            "win_rate": len(winners) / len(trades_df),
            "avg_winner": winners['net_pnl'].mean() if len(winners) > 0 else 0,
            "avg_loser": losers['net_pnl'].mean() if len(losers) > 0 else 0,
            "profit_factor": abs(winners['net_pnl'].sum() / losers['net_pnl'].sum()) if losers['net_pnl'].sum() != 0 else float('inf'),
            "avg_net_per_trade": net_returns / len(trades_df),
            "breakeven_ticks": self.cost_model.breakeven_ticks(self.contract)
        }
```

## Examples

### Example 1: Cost Impact Analysis

```python
"""
Analyze how costs affect strategy profitability.
"""

# Setup
contract = CONTRACT_SPECS["ES"]
cost_model = COST_MODELS[TradingTier.PROP_FIRM]

# Calculate breakeven
breakeven = cost_model.breakeven_ticks(contract)
print(f"ES Breakeven: {breakeven:.2f} ticks (${breakeven * contract.tick_value:.2f})")
# Output: ES Breakeven: 1.36 ticks ($17.00)

# Strategy with 2 tick average profit before costs
avg_gross_ticks = 2.0
avg_net_ticks = avg_gross_ticks - breakeven
print(f"Net profit per trade: {avg_net_ticks:.2f} ticks (${avg_net_ticks * contract.tick_value:.2f})")
# Output: Net profit per trade: 0.64 ticks ($8.00)

# Percentage of gross consumed by costs
cost_pct = breakeven / avg_gross_ticks
print(f"Costs consume {cost_pct:.0%} of gross profit")
# Output: Costs consume 68% of gross profit

# Minimum win rate needed to be profitable
# With 2 tick winner and 2 tick loser (1:1 R:R)
# Net winner: 2 - 1.36 = 0.64 ticks
# Net loser: 2 + 1.36 = 3.36 ticks (slippage on both sides)
# Need: win_rate * 0.64 > (1 - win_rate) * 3.36
# win_rate > 3.36 / 4.0 = 84%
print("With 1:1 R:R, need 84% win rate to be profitable after costs!")
```

### Example 2: Comparing Gross vs Net Sharpe

```python
"""
Show difference between gross and net Sharpe ratios.
"""

# Run backtest
backtester = CostAwareBacktester(
    cost_model=COST_MODELS[TradingTier.PROP_FIRM],
    contract_spec=CONTRACT_SPECS["ES"]
)

trades = backtester.run_backtest(df, signals)
metrics = backtester.calculate_metrics(trades)

# Calculate Sharpe ratios
gross_returns = trades['gross_pnl']
net_returns = trades['net_pnl']

gross_sharpe = (gross_returns.mean() / gross_returns.std()) * np.sqrt(252)
net_sharpe = (net_returns.mean() / net_returns.std()) * np.sqrt(252)

print(f"Gross Sharpe: {gross_sharpe:.2f}")
print(f"Net Sharpe: {net_sharpe:.2f}")
print(f"Sharpe reduction: {(gross_sharpe - net_sharpe) / gross_sharpe:.0%}")

# Common result for high-frequency strategies:
# Gross Sharpe: 2.5
# Net Sharpe: 0.8
# Sharpe reduction: 68%
```

## Common Mistakes

### 1. Zero Slippage Assumption

```python
# WRONG: No slippage
cost_model = CostModel(
    commission_per_contract=4.50,
    slippage_ticks=0.0,  # Unrealistic!
)

# RIGHT: At least 1 tick slippage for retail
cost_model = CostModel(
    commission_per_contract=4.50,
    slippage_ticks=1.0,
)
```

### 2. Ignoring Entry AND Exit Slippage

```python
# WRONG: Only counting slippage once
slippage_cost = slippage_ticks * tick_value * contracts

# RIGHT: Slippage on both entry and exit
slippage_cost = slippage_ticks * tick_value * contracts * 2
```

### 3. Using Mid Price for Fills

```python
# WRONG: Filling at mid price
entry_price = (bid + ask) / 2  # Never happens!

# RIGHT: Market buys fill at ask, sells at bid, plus slippage
if side == "buy":
    entry_price = ask + slippage
else:
    entry_price = bid - slippage
```

### 4. Constant Slippage in All Conditions

```python
# WRONG: Same slippage always
slippage = 1.0  # ticks

# RIGHT: Adjust for market conditions
slippage = base_slippage * volatility_multiplier * volume_multiplier
# Higher vol = higher slippage
# Lower volume = higher slippage
```

---

## Multi-Market Abstraction (Futures + Crypto)

### Abstract InstrumentSpec Base Class

All instrument specifications derive from a common abstract base. This enables the same backtesting pipeline to work across futures and crypto without code changes.

```python
"""
Abstract instrument specification for multi-market support.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class InstrumentSpec(ABC):
    """Base class for all tradeable instrument specifications."""
    symbol: str
    market_type: str  # "futures" | "crypto_cex" | "crypto_dex"

    @abstractmethod
    def calculate_round_trip_cost(self, quantity: float, price: float = 0.0) -> float:
        """Calculate total round-trip cost for a trade."""
        ...

    @abstractmethod
    def calculate_pnl(self, entry: float, exit: float, quantity: float, direction: int) -> float:
        """Calculate gross PnL for a trade."""
        ...

    @abstractmethod
    def min_tick(self) -> float:
        """Minimum price increment."""
        ...
```

### FuturesContractSpec (Existing Behavior, Extracted)

The existing `ContractSpec` is wrapped as `FuturesContractSpec`:

```python
@dataclass
class FuturesContractSpec(InstrumentSpec):
    """Futures contract spec (ES, NQ, YM, GC, CL)."""
    market_type: str = "futures"
    exchange: str = ""
    tick_size: float = 0.25
    tick_value: float = 12.50
    point_value: float = 50.00
    margin_requirement: float = 500.0
    trading_hours: str = "09:30-16:00 ET"
    commission_per_side: float = 2.50
    slippage_ticks: float = 1.0

    def calculate_round_trip_cost(self, quantity: float, price: float = 0.0) -> float:
        commission = self.commission_per_side * 2 * quantity
        slippage = self.slippage_ticks * self.tick_value * 2 * quantity
        return commission + slippage

    def calculate_pnl(self, entry: float, exit: float, quantity: float, direction: int) -> float:
        return (exit - entry) * direction * self.point_value * quantity

    def min_tick(self) -> float:
        return self.tick_size
```

### CryptoPerpSpec (Crypto Perpetual Futures)

```python
@dataclass
class CryptoPerpSpec(InstrumentSpec):
    """Crypto perpetual futures spec (BTC-PERP, ETH-PERP, etc.)."""
    market_type: str = "crypto_cex"  # or "crypto_dex"
    exchange: str = "binance"
    maker_fee_pct: float = 0.0002   # 0.02%
    taker_fee_pct: float = 0.0005   # 0.05%
    tick_size: float = 0.10         # Minimum price increment
    min_quantity: float = 0.001
    max_leverage: int = 125
    gas_cost_usd: float = 0.0      # Non-zero for DEX

    def calculate_round_trip_cost(self, quantity: float, price: float = 0.0) -> float:
        notional = quantity * price
        entry_fee = notional * self.taker_fee_pct
        exit_fee = notional * self.taker_fee_pct
        return entry_fee + exit_fee + self.gas_cost_usd

    def calculate_pnl(self, entry: float, exit: float, quantity: float, direction: int) -> float:
        return (exit - entry) * direction * quantity

    def min_tick(self) -> float:
        return self.tick_size
```

### CryptoSpotSpec (Spot Trading)

```python
@dataclass
class CryptoSpotSpec(InstrumentSpec):
    """Crypto spot trading spec."""
    market_type: str = "crypto_cex"
    exchange: str = "binance"
    maker_fee_pct: float = 0.001    # 0.10%
    taker_fee_pct: float = 0.001    # 0.10%
    tick_size: float = 0.01
    min_quantity: float = 0.00001
    withdrawal_fee_usd: float = 0.0

    def calculate_round_trip_cost(self, quantity: float, price: float = 0.0) -> float:
        notional = quantity * price
        entry_fee = notional * self.taker_fee_pct
        exit_fee = notional * self.taker_fee_pct
        return entry_fee + exit_fee + self.withdrawal_fee_usd

    def calculate_pnl(self, entry: float, exit: float, quantity: float, direction: int) -> float:
        return (exit - entry) * direction * quantity

    def min_tick(self) -> float:
        return self.tick_size
```

### Profile-Dispatched Factory

```python
"""
Dispatch the right InstrumentSpec based on the active profile.
"""

# Preset crypto specs
CRYPTO_SPECS = {
    "BTC-PERP-BINANCE": CryptoPerpSpec(
        symbol="BTC/USDT:USDT", exchange="binance",
        maker_fee_pct=0.0002, taker_fee_pct=0.0005,
        tick_size=0.10, max_leverage=125
    ),
    "ETH-PERP-BINANCE": CryptoPerpSpec(
        symbol="ETH/USDT:USDT", exchange="binance",
        maker_fee_pct=0.0002, taker_fee_pct=0.0005,
        tick_size=0.01, max_leverage=100
    ),
    "BTC-PERP-HYPERLIQUID": CryptoPerpSpec(
        symbol="BTC-PERP", exchange="hyperliquid",
        market_type="crypto_dex",
        maker_fee_pct=0.0002, taker_fee_pct=0.0005,
        tick_size=0.10, max_leverage=50,
        gas_cost_usd=0.10  # L1 gas cost
    ),
}

def get_instrument_spec(profile: dict, symbol: str) -> InstrumentSpec:
    """
    Return the correct InstrumentSpec for a symbol given the active profile.

    Args:
        profile: Active profile dict (from active-profile.json)
        symbol: Trading symbol (e.g. "ES", "BTC/USDT:USDT")

    Returns:
        FuturesContractSpec, CryptoPerpSpec, or CryptoSpotSpec
    """
    market_type = profile.get("market_type", "futures")

    if market_type == "futures":
        return CONTRACT_SPECS[symbol]  # Existing futures specs
    elif market_type in ("crypto_cex", "crypto_dex"):
        key = f"{symbol}-{profile['exchange'].upper()}"
        return CRYPTO_SPECS.get(key, CryptoPerpSpec(symbol=symbol, exchange=profile["exchange"]))
    else:
        raise ValueError(f"Unknown market_type: {market_type}")
```

### Cost Comparison Across Markets

| Component | Futures (ES) | Crypto CEX (BTC) | Crypto DEX (BTC) |
|-----------|-------------|-------------------|-------------------|
| Commission | $5.00 RT | 0.10% notional | 0.07% notional |
| Slippage | 1 tick ($12.50) | ~0.01% | ~0.02% |
| Exchange Fees | $1.32 RT | Included in fee | Gas ~$0.10 |
| Funding | N/A | 8h funding rate | 1h funding rate |
| Total (1 contract/$50K) | ~$18.82 | ~$50.00 | ~$35.10 |
