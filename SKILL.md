---
name: binance-intelligence-mcp
description: |
  MCP server providing 8 computed intelligence tools for Binance futures markets.
  Unlike raw API wrappers, each tool combines multiple public endpoints into
  derived analytics: accumulation detection, whale tracking, market impact
  simulation, smart money radar, pattern scanning, correlation matrix,
  regime classification, and DCA backtesting. Install via pip, no API keys needed.
metadata:
  version: "1.0.0"
  author: mefai-dev
license: MIT
---

# binance-intelligence-mcp

A Python MCP server that provides **8 computed intelligence tools** for Binance futures markets. Each tool combines 2-6 Binance API endpoints into derived analytics with composite scoring algorithms — not just raw data forwarding.

## Why This Is Different

Existing Binance MCP servers forward raw API responses. This package computes **derived intelligence**:

- **Accumulation Detector**: 4-factor composite score from volume, OI, funding, and taker ratios
- **Whale Scanner**: Trade classification by tier ($50K/$250K/$1M) with net pressure analysis
- **Impact Simulator**: Order book walk computing slippage, levels consumed, average fill
- **Smart Money Radar**: 6-factor weighted score from positioning, sentiment, and momentum
- **Pattern Scanner**: Candlestick pattern recognition with confidence scoring
- **Correlation Matrix**: Pearson correlation coefficients across trading pairs
- **Regime Classifier**: ADX/ATR-based market regime labeling
- **DCA Backtester**: Dollar-cost averaging vs lump-sum historical comparison

## Installation

```bash
pip install binance-intelligence-mcp
```

## Usage

### As MCP Server

```bash
binance-intelligence-mcp
```

### MCP Client Configuration

```json
{
  "mcpServers": {
    "binance-intelligence": {
      "command": "binance-intelligence-mcp"
    }
  }
}
```

## Tools Reference

### `detect_accumulation`

Combines klines, open interest history, premium index, and taker buy/sell ratio to detect smart accumulation.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbols` | list[str] | top 12 | Trading pairs to analyze |

**Output:** Per-symbol scores (volume_surge, oi_buildup, stealth_mode, buyer_aggression) and composite 0-100.

### `scan_whale_trades`

Scans aggregate trades for large orders, classifies by tier, computes net pressure.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbols` | list[str] | top 6 | Trading pairs to scan |
| `min_usd` | float | 50000 | Minimum trade size in USD |

**Output:** Classified trades (Dolphin/Whale/Mega), net buy/sell pressure, biggest trade.

### `simulate_market_impact`

Walks the order book to simulate large order execution impact.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbol` | str | BTCUSDT | Trading pair |
| `side` | str | BUY | BUY or SELL |
| `amount_usd` | float | 100000 | Order size in USD |

**Output:** Levels consumed, avg/worst fill, slippage %, impact rating.

### `smart_money_radar`

6-factor composite analysis of smart money positioning.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbols` | list[str] | top 12 | Trading pairs to analyze |

**Output:** Per-factor scores (-1 to +1), composite 0-100, bias label (BULLISH/BEARISH/NEUTRAL).

### `scan_candlestick_patterns`

Detects classic candlestick patterns with confidence scoring.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbols` | list[str] | top 12 | Trading pairs |
| `interval` | str | 4h | Candlestick interval (1h/4h) |

**Output:** Detected patterns (Hammer, Engulfing, Doji, Morning Star, etc.) with confidence 0-100.

### `compute_correlation_matrix`

Computes Pearson correlation coefficients between trading pair prices.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbols` | list[str] | top 8 | 2-20 trading pairs |
| `interval` | str | 4h | Candlestick interval |
| `limit` | int | 90 | Lookback periods |

**Output:** Full correlation matrix, strongly correlated pairs (|r| >= 0.7).

### `classify_market_regime`

Classifies market regime using ADX, ATR, and volume analysis.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbols` | list[str] | top 12 | Trading pairs |

**Output:** Regime label (TRENDING/RANGING/VOLATILE_BREAKOUT/LOW_ACTIVITY), direction, ADX/ATR values.

### `backtest_dca`

Backtests DCA strategy vs lump-sum investing over historical data.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `symbol` | str | BTCUSDT | Trading pair |
| `amount_per_interval` | float | 100 | USD per purchase |
| `interval_days` | int | 7 | Days between purchases |
| `total_days` | int | 365 | Historical lookback |

**Output:** DCA vs lump-sum ROI comparison with winner declaration.

## Binance Endpoints

All endpoints are public (no API key required):

- `/fapi/v1/klines` — Candlestick/kline data
- `/fapi/v1/aggTrades` — Aggregate trades
- `/fapi/v1/depth` — Order book
- `/fapi/v1/premiumIndex` — Funding rate
- `/futures/data/openInterestHist` — Open interest history
- `/futures/data/topLongShortPositionRatio` — Top trader positions
- `/futures/data/topLongShortAccountRatio` — Top trader accounts
- `/futures/data/globalLongShortAccountRatio` — Global sentiment
- `/futures/data/takerlongshortRatio` — Taker buy/sell volume

## Testing

```bash
pytest tests/ -v
```

142 mock-based tests, zero API keys needed. Tests cover all 8 tools, the API client, helper functions, edge cases, and error handling.

## Architecture

```
MCP Client → stdio → server.py (FastMCP, 8 tools)
                        → tools/*.py (scoring algorithms)
                          → client.py (async aiohttp)
                            → Binance Public API
```

Each tool module is a pure async function: `(client, params) → dict`. The server module wraps these with `@mcp.tool()` decorators and manages client lifecycle.

## Use Cases

1. **Pre-trade analysis**: Run accumulation detector + smart money radar before entering a position
2. **Whale monitoring**: Track large trade flow to identify institutional activity
3. **Risk assessment**: Simulate market impact before placing large orders
4. **Portfolio diversification**: Use correlation matrix to avoid over-correlated positions
5. **Strategy backtesting**: Compare DCA vs lump-sum for any trading pair
6. **Market context**: Classify current regime to select appropriate trading strategy

## License

MIT
