"""Local data models for crypto module -- standalone dataclass replacements for ORM models."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


@dataclass
class CryptoPosition:
    """Standalone position model for crypto trading."""

    symbol: str
    side: OrderSide
    size: Decimal
    entry_price: Decimal
    current_price: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    leverage: int = 1
    exchange: str = ""
    status: PositionStatus = PositionStatus.OPEN
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CryptoOrder:
    """Standalone order model for crypto trading."""

    symbol: str
    side: OrderSide
    order_type: OrderType
    size: Decimal
    price: Optional[Decimal] = None
    exchange: str = ""
    filled: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CryptoBalance:
    """Account balance on an exchange."""

    exchange: str
    currency: str
    total: Decimal
    available: Decimal
    in_positions: Decimal = Decimal("0")
    timestamp: datetime = field(default_factory=datetime.utcnow)
