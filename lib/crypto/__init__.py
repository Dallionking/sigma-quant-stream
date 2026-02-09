"""
Crypto exchange adapters, cost modeling, and signal services.

Standalone package for the Sigma-Quant research pipeline
(standalone package for the Sigma-Quant research pipeline).

Provides:
- Unified exchange adapters (Binance, Bybit, OKX, Hyperliquid)
- Round-trip cost modeling for perpetual futures
- Funding rate analysis and mean-reversion signals
- Liquidation cascade detection
- On-chain analytics (SOPR, MVRV, exchange flows)
- Crypto risk modeling (EVT VaR, cascade risk)
- Exchange compliance validation
- Cross-exchange arbitrage detection
- Avellaneda-Stoikov market making engine
- Hypothesis bridge for quant pipeline
- Freqtrade strategy bridge

Usage::

    from lib.crypto import (
        CryptoExchangeFactory,
        UnifiedCryptoClient,
        calculate_round_trip_cost,
        FundingRateService,
    )

    # Create adapters
    adapter = CryptoExchangeFactory.create("binance")
    ticker = await adapter.get_ticker("BTC/USDT:USDT")

    # Cost modeling
    cost = calculate_round_trip_cost(
        exchange="binance",
        symbol="BTC/USDT:USDT",
        size_usd=10_000,
    )
"""

# Local data models
from .models import (
    CryptoBalance,
    CryptoOrder,
    CryptoPosition,
    OrderSide,
    OrderType,
    PositionStatus,
)

# Exchange adapters (Module 1)
from .exchange_adapters import (
    CircuitBreaker,
    CryptoExchangeAdapter,
    CryptoExchangeFactory,
    ExchangeUnavailableError,
    FundingRateData,
    HyperliquidAdapter,
    OHLCVBar,
    TickerData,
    UnifiedCryptoClient,
)

# Cost model (Module 2)
from .cost_model import (
    EXCHANGE_FEES,
    TradeCostBreakdown,
    calculate_funding_drag,
    calculate_round_trip_cost,
    get_fee_schedule,
)

# Funding rate service (Module 3)
from .funding_rate_service import (
    CarryOpportunity,
    FundingRateService,
    MeanReversionSignal,
)

# On-chain analytics (Module 6)
from .onchain_service import (
    CompositeSignal,
    ExchangeFlowData,
    MVRVData,
    OnChainService,
    SOPRData,
    StablecoinSupplyData,
)

# Risk modeling (Module 7)
from .risk_modeler import (
    CryptoRiskModeler,
    EmergencyAction,
    RiskReport,
)

# Exchange validator (Module 8)
from .exchange_validator import (
    ExchangeValidator,
)

# Arbitrage detector (Module 9)
from .arbitrage_detector import (
    ArbitrageDetector,
)

# Market maker engine (Module 10)
from .market_maker_engine import (
    AvellanedaStoikovEngine,
    MMParameters,
    Quote,
)

# Liquidation service (Module 5 -- optional)
try:
    from .liquidation_service import (
        CascadeSignal,
        HeatmapLevel,
        LiquidationService,
        OIDivergence,
    )

    _LIQUIDATION_AVAILABLE = True
except ImportError:
    _LIQUIDATION_AVAILABLE = False

# Hypothesis bridge (Phase 3)
from .hypothesis_bridge import (
    CryptoHypothesisProducer,
    HypothesisCard,
)

# Freqtrade bridge (Phase 3)
from .freqtrade_bridge import (
    ConversionResult,
    FreqtradeBridge,
    FreqtradeConfig,
)

__all__ = [
    # Local models
    "CryptoPosition",
    "CryptoOrder",
    "CryptoBalance",
    "OrderSide",
    "OrderType",
    "PositionStatus",
    # Exchange adapters
    "CryptoExchangeAdapter",
    "CryptoExchangeFactory",
    "HyperliquidAdapter",
    "UnifiedCryptoClient",
    # Data classes
    "TickerData",
    "FundingRateData",
    "OHLCVBar",
    # Circuit breaker
    "CircuitBreaker",
    "ExchangeUnavailableError",
    # Cost model
    "TradeCostBreakdown",
    "calculate_round_trip_cost",
    "calculate_funding_drag",
    "get_fee_schedule",
    "EXCHANGE_FEES",
    # Funding rate service
    "FundingRateService",
    "MeanReversionSignal",
    "CarryOpportunity",
    # On-chain analytics
    "OnChainService",
    "SOPRData",
    "MVRVData",
    "ExchangeFlowData",
    "StablecoinSupplyData",
    "CompositeSignal",
    # Risk modeling
    "CryptoRiskModeler",
    "RiskReport",
    "EmergencyAction",
    # Exchange validator
    "ExchangeValidator",
    # Arbitrage detector
    "ArbitrageDetector",
    # Market maker engine
    "AvellanedaStoikovEngine",
    "MMParameters",
    "Quote",
    # Hypothesis bridge
    "CryptoHypothesisProducer",
    "HypothesisCard",
    # Freqtrade bridge
    "FreqtradeBridge",
    "FreqtradeConfig",
    "ConversionResult",
]

if _LIQUIDATION_AVAILABLE:
    __all__.extend([
        "LiquidationService",
        "CascadeSignal",
        "OIDivergence",
        "HeatmapLevel",
    ])
