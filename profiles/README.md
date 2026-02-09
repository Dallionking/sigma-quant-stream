# Market Profiles

Market profiles define everything market-specific: symbols, costs, compliance rules, data providers, and research sources. The core `config.json` stays market-agnostic.

## Active Profile

Set in `config.json`:
```json
{
  "activeProfile": "profiles/futures.json"
}
```

## Available Profiles

| Profile | File | Market | Data Source | Trading Hours |
|---------|------|--------|-------------|---------------|
| CME Futures | `futures.json` | Futures | Databento | CME schedule |
| Crypto CEX | `crypto-cex.json` | Crypto (centralized) | CCXT/Binance | 24/7 |
| Crypto DEX | `crypto-dex-hyperliquid.json` | Crypto (decentralized) | Hyperliquid API | 24/7 |

## Profile Schema

Every profile must contain these top-level keys:

| Key | Type | Description |
|-----|------|-------------|
| `profileId` | string | Unique identifier (used in file naming, routing) |
| `displayName` | string | Human-readable name |
| `marketType` | string | One of: `futures`, `crypto-cex`, `crypto-dex` |
| `dataProvider` | object | Adapter config, API keys, sample data paths |
| `symbols` | object | Discovery mode, pinned/excluded symbols |
| `costs` | object | Fee model (per-contract or percentage) |
| `compliance` | object | Market-specific rules (prop firm, exchange, protocol) |
| `researchSources` | object | People, websites, books for research context |
| `tradingHours` | string | `"CME"`, `"24/7"`, or custom schedule |
| `specificFeatures` | object | Market-specific feature flags |
| `output` | object | Where validated strategies land |

### Optional Keys

| Key | Type | Description |
|-----|------|-------------|
| `paperTrading` | object | Paper trading engine config |

## Cost Models

### Per-Contract (Futures)
```json
{
  "model": "per_contract",
  "commission": 2.50,
  "slippage": 0.5,
  "slippageUnit": "ticks",
  "alwaysInclude": true
}
```

### Percentage (Crypto)
```json
{
  "model": "percentage",
  "makerFee": 0.0002,
  "takerFee": 0.0005,
  "slippageBps": 5,
  "fundingRateAvg": 0.0001,
  "alwaysInclude": true
}
```

## Compliance Types

| Type | Used By | Key Rules |
|------|---------|-----------|
| `prop-firm` | Futures | 14 firms, daily loss limits, trailing DD, consistency |
| `exchange-rules` | Crypto CEX | Leverage tiers, liquidation buffer, position limits |
| `protocol-rules` | Crypto DEX | Max leverage, vault interaction, builder codes |

## Creating a Custom Profile

1. Copy the closest existing profile as a template
2. Update `profileId`, `displayName`, and `marketType`
3. Configure `dataProvider` with the correct adapter and credentials
4. Set `symbols` discovery or pin specific instruments
5. Define the `costs` model matching the market
6. Set `compliance` rules for the target venue
7. Add the profile path to `config.json` under `marketProfiles`
8. Set `activeProfile` to switch to it

## Switching Profiles

Update `activeProfile` in `config.json`:
```json
{
  "activeProfile": "profiles/crypto-cex.json"
}
```

All workers, sub-agents, and validation gates will automatically use the new profile's costs, symbols, and compliance rules.
