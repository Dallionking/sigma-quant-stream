# Contributing to Sigma-Quant Stream

Thank you for your interest in contributing. This project benefits from community additions -- new exchange adapters, market profiles, agent skills, seed hypotheses, and pattern knowledge all make the research factory more powerful.

---

## Ways to Contribute

| Area | Directory | Impact |
|------|-----------|--------|
| Exchange adapters | `lib/crypto/` | Support new exchanges |
| Market profiles | `profiles/` | Enable new markets |
| Agent skills | `.claude/skills/` | Improve agent capabilities |
| Agent definitions | `.claude/agents/` | Add specialized sub-agents |
| Pattern knowledge | `patterns/` | Share what works and what fails |
| Seed hypotheses | `seed/hypotheses/` | Prime the research queue |
| Documentation | `docs/` | Help others get started |
| Bug fixes and tests | `tests/`, `lib/` | Improve reliability |

---

## Development Setup

### Prerequisites

- Python 3.11+
- Git

### Installation

```bash
# Clone the repo
git clone https://github.com/Dallionking/sigma-quant-stream.git
cd sigma-quant-stream

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
sigma-quant health
```

### Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=cli --cov=lib -v

# Run specific test file
pytest tests/test_backtest_runner.py -v
```

### Linting

```bash
# Check for lint errors
ruff check .

# Auto-format
ruff format .

# Type checking
mypy cli/ lib/ --ignore-missing-imports
```

---

## Adding a New Exchange Adapter

Exchange adapters live in `lib/crypto/exchange_adapters.py`. To add support for a new exchange:

### Step 1: Create the adapter class

```python
# In lib/crypto/exchange_adapters.py

class NewExchangeAdapter(BaseExchangeAdapter):
    """Adapter for NewExchange API."""

    EXCHANGE_ID = "newexchange"

    def __init__(self, api_key: str | None = None, secret: str | None = None) -> None:
        super().__init__(api_key=api_key, secret=secret)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "5m",
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Fetch OHLCV candle data."""
        # Implementation using ccxt or native API
        ...

    async def fetch_funding_rate(self, symbol: str) -> float:
        """Fetch current funding rate."""
        ...

    async def fetch_open_interest(self, symbol: str) -> float:
        """Fetch current open interest in USD."""
        ...
```

### Step 2: Register the adapter

Add your adapter to the adapter registry in `lib/crypto/exchange_adapters.py`:

```python
ADAPTER_REGISTRY = {
    "binance": BinanceAdapter,
    "bybit": BybitAdapter,
    "okx": OKXAdapter,
    "hyperliquid": HyperliquidAdapter,
    "newexchange": NewExchangeAdapter,  # Add here
}
```

### Step 3: Create a market profile

Create `profiles/crypto-cex-newexchange.json`:

```json
{
  "profileId": "crypto-cex-newexchange",
  "displayName": "Crypto CEX (NewExchange)",
  "marketType": "crypto-cex",
  "dataProvider": {
    "adapter": "ccxt",
    "exchange": "newexchange",
    "apiKeyEnv": "NEWEXCHANGE_API_KEY",
    "secretEnv": "NEWEXCHANGE_SECRET"
  },
  "costs": {
    "model": "percentage",
    "makerFee": 0.0002,
    "takerFee": 0.0005,
    "slippageBps": 5,
    "fundingRateAvg": 0.0001,
    "alwaysInclude": true
  },
  "compliance": {
    "type": "exchange-rules",
    "maxLeverage": 100,
    "liquidationBuffer": 0.005,
    "positionLimitUSD": 100000
  }
}
```

### Step 4: Add to config.json

```json
"marketProfiles": {
  "crypto-cex-newexchange": {
    "path": "profiles/crypto-cex-newexchange.json",
    "displayName": "Crypto CEX (NewExchange)",
    "marketType": "crypto-cex"
  }
}
```

### Step 5: Write tests

Add tests in `tests/test_newexchange_adapter.py` covering:
- OHLCV data fetching
- Cost calculation accuracy
- Error handling for API failures

---

## Adding a New Market Profile

Market profiles control how the system interacts with a specific market or exchange.

### Step 1: Create the profile JSON

```json
{
  "profileId": "your-profile-id",
  "displayName": "Human-readable name",
  "marketType": "futures | crypto-cex | crypto-dex",
  "dataProvider": {
    "adapter": "databento | ccxt | hyperliquid",
    "apiKeyEnv": "YOUR_API_KEY_ENV_VAR"
  },
  "symbols": {
    "mode": "static | dynamic",
    "pinned": ["SYMBOL1", "SYMBOL2"]
  },
  "costs": {
    "model": "per_contract | percentage",
    "alwaysInclude": true
  },
  "compliance": {
    "type": "prop-firm | exchange-rules"
  }
}
```

### Step 2: Test the profile

```bash
sigma-quant config profiles  # Verify it appears
sigma-quant health           # Verify data provider works
```

---

## Adding a New Skill

Skills provide domain expertise to sub-agents. They live in `.claude/skills/`.

### Step 1: Create the skill directory and file

```bash
mkdir -p .claude/skills/your-skill-name
```

### Step 2: Write the skill file

Create `.claude/skills/your-skill-name/SKILL.md`:

```markdown
# Your Skill Name

## When to Use This Skill

- [Describe when agents should invoke this skill]

## Key Patterns

[Provide concrete patterns, templates, or rules the agent should follow]

## Examples

[Show input/output examples]

## Quality Gates

- [ ] [Checklist items for the agent to verify]
```

### Step 3: Register in the skills index

Add your skill to `.claude/skills/INDEX.md`.

---

## Adding Seed Hypotheses

Seed hypotheses prime the research queue so the Researcher worker has ideas to start with.

### Step 1: Create a hypothesis file

Create `seed/hypotheses/hyp-your-idea.json`:

```json
{
  "id": "hyp-your-idea",
  "title": "Mean-Reversion After Extreme Funding Rates",
  "hypothesis": "When 8-hour funding rates exceed 0.1%, price tends to mean-revert within 24 hours as overleveraged positions unwind.",
  "market": "crypto-cex",
  "symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
  "indicators": ["funding_rate", "open_interest"],
  "timeframe": "1h",
  "expected_edge": "Short when funding > 0.1%, close after mean reversion",
  "source": "Community contribution",
  "priority": "medium"
}
```

---

## Code Style

### Python

- **Formatter:** Ruff (`ruff format`)
- **Linter:** Ruff (`ruff check`)
- **Line length:** 120 characters
- **Type hints:** Required on all function signatures
- **Docstrings:** Required on all public functions and classes

```python
def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    annualization_factor: int = 252,
) -> float:
    """Calculate annualized Sharpe ratio from a return series.

    Args:
        returns: Daily return series.
        risk_free_rate: Annual risk-free rate (default 0).
        annualization_factor: Trading days per year.

    Returns:
        Annualized Sharpe ratio.
    """
    excess = returns - risk_free_rate / annualization_factor
    if excess.std() == 0:
        return 0.0
    return float(excess.mean() / excess.std() * (annualization_factor ** 0.5))
```

### Markdown

- Line limit: 80 characters where practical (tables and code blocks excepted)
- Use ATX-style headers (`#`, `##`, `###`)
- One blank line between sections

---

## Pull Request Process

1. **Fork** the repository
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/add-kraken-adapter
   ```
3. **Write tests** for your changes
4. **Run quality checks**:
   ```bash
   ruff check .
   ruff format --check .
   pytest -v
   ```
5. **Submit a PR** with a clear description:
   - What you changed and why
   - How to test the change
   - Any breaking changes

### PR Checklist

- [ ] Tests pass (`pytest -v`)
- [ ] Lint passes (`ruff check .`)
- [ ] Format passes (`ruff format --check .`)
- [ ] Type hints on all new functions
- [ ] Documentation updated if needed
- [ ] No secrets or API keys in the diff

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive experience for everyone. We pledge to act and interact in ways that contribute to an open, respectful, and harassment-free community.

### Expected Behavior

- Be respectful and constructive in discussions
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment, trolling, or personal attacks
- Publishing others' private information
- Any conduct that would be considered inappropriate in a professional setting

### Enforcement

Instances of unacceptable behavior may be reported to the project maintainers. All complaints will be reviewed and investigated, and will result in a response deemed appropriate to the circumstances.

---

## Questions?

Open a [GitHub Discussion](https://github.com/Dallionking/sigma-quant-stream/discussions) or file an issue. We are happy to help.
