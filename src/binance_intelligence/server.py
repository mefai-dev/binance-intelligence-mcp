"""FastMCP server with 12 computed intelligence tools for Binance."""

from mcp.server.fastmcp import FastMCP

from .client import BinanceClient
from .tools.accumulation import detect_accumulation
from .tools.whale import scan_whale_trades
from .tools.impact import simulate_market_impact
from .tools.smart_money import smart_money_radar
from .tools.patterns import scan_candlestick_patterns
from .tools.correlation import compute_correlation_matrix
from .tools.regime import classify_market_regime
from .tools.dca import backtest_dca
from .tools.funding_scan import scan_funding_rates
from .tools.funding_extremes import detect_funding_extremes
from .tools.funding_history import analyze_funding_history
from .tools.basis_spread import scan_basis_spread

mcp = FastMCP("binance-intelligence")


def _get_client() -> BinanceClient:
    return BinanceClient()


@mcp.tool()
async def detect_accumulation_tool(
    symbols: list[str] | None = None,
) -> dict:
    """Detect smart accumulation across Binance futures symbols.

    Combines volume analysis, open interest trends, funding rate proximity,
    and taker buy/sell ratio into a composite accumulation score (0-100).

    Each symbol receives 4 sub-scores:
    - volume_surge: Current volume vs 20-period average
    - oi_buildup: Open interest linear regression trend
    - stealth_mode: Funding rate closeness to zero (quiet accumulation)
    - buyer_aggression: Taker buy ratio above neutral

    Args:
        symbols: List of trading pairs (default: top 12 futures pairs)

    Returns:
        Ranked list of symbols with accumulation scores and signal strength.
    """
    client = _get_client()
    try:
        return await detect_accumulation(client, symbols)
    finally:
        await client.close()


@mcp.tool()
async def scan_whale_trades_tool(
    symbols: list[str] | None = None,
    min_usd: float = 50000,
) -> dict:
    """Scan for large whale trades on Binance futures.

    Analyzes recent aggregate trades to identify large orders.
    Classifies by tier: Dolphin ($50K-$250K), Whale ($250K-$1M), Mega (>$1M).
    Computes net buy/sell pressure and highlights the biggest trade.

    Args:
        symbols: List of trading pairs (default: top 6 pairs)
        min_usd: Minimum trade size in USD to flag (default: 50000)

    Returns:
        Per-symbol whale activity with net pressure direction and tier counts.
    """
    client = _get_client()
    try:
        return await scan_whale_trades(client, symbols, min_usd)
    finally:
        await client.close()


@mcp.tool()
async def simulate_market_impact_tool(
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    amount_usd: float = 100000,
) -> dict:
    """Simulate the market impact of a large order on Binance.

    Walks the live order book to calculate how a large market order would
    execute: levels consumed, average fill price, worst fill, slippage,
    and total cost.

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        side: Order side ··· BUY or SELL
        amount_usd: Order size in USD

    Returns:
        Impact analysis with slippage percentage and severity rating.
    """
    client = _get_client()
    try:
        return await simulate_market_impact(client, symbol, side, amount_usd)
    finally:
        await client.close()


@mcp.tool()
async def smart_money_radar_tool(
    symbols: list[str] | None = None,
) -> dict:
    """Analyze smart money positioning across Binance futures symbols.

    Combines 6 independent data factors into a composite score (0-100):
    1. Top trader position ratio (long/short by positions)
    2. Top trader account ratio (long/short by accounts)
    3. Global long/short account ratio (retail sentiment)
    4. Taker buy/sell ratio (aggressive order flow)
    5. Open interest trend (money flow direction)
    6. Price momentum (recent price trajectory)

    Each factor is scored from -1 (bearish) to +1 (bullish).

    Args:
        symbols: List of trading pairs (default: top 12 futures pairs)

    Returns:
        Per-symbol factor breakdown, composite score, and bias label.
    """
    client = _get_client()
    try:
        return await smart_money_radar(client, symbols)
    finally:
        await client.close()


@mcp.tool()
async def scan_candlestick_patterns_tool(
    symbols: list[str] | None = None,
    interval: str = "4h",
) -> dict:
    """Scan for candlestick patterns across Binance futures symbols.

    Detects classic patterns with confidence scores:
    - Hammer / Inverted Hammer (reversal)
    - Bullish / Bearish Engulfing (reversal)
    - Doji (indecision)
    - Morning Star / Evening Star (reversal)
    - Three White Soldiers / Three Black Crows (continuation)

    Args:
        symbols: List of trading pairs (default: top 12 futures pairs)
        interval: Candlestick interval ··· "1h" or "4h" (default: "4h")

    Returns:
        Per-symbol detected patterns with type, direction, and confidence.
    """
    client = _get_client()
    try:
        return await scan_candlestick_patterns(client, symbols, interval)
    finally:
        await client.close()


@mcp.tool()
async def compute_correlation_matrix_tool(
    symbols: list[str] | None = None,
    interval: str = "4h",
    limit: int = 90,
) -> dict:
    """Compute price correlation matrix between Binance trading pairs.

    Calculates Pearson correlation coefficients between close prices
    of multiple symbols. Identifies strongly correlated and inversely
    correlated pairs.

    Args:
        symbols: List of 2-20 trading pairs (default: top 8)
        interval: Candlestick interval (default: "4h")
        limit: Number of periods to look back (default: 90)

    Returns:
        Full correlation matrix and list of strong correlations (|r| >= 0.7).
    """
    client = _get_client()
    try:
        return await compute_correlation_matrix(client, symbols, interval, limit)
    finally:
        await client.close()


@mcp.tool()
async def classify_market_regime_tool(
    symbols: list[str] | None = None,
) -> dict:
    """Classify the current market regime for Binance futures symbols.

    Uses ADX, ATR, and volume analysis to classify each symbol into:
    - TRENDING: Strong directional movement (ADX >= 25)
    - RANGING: Low directional movement, contained price action
    - VOLATILE_BREAKOUT: High ADX + high ATR, explosive movement
    - LOW_ACTIVITY: Low volume and volatility

    Also reports direction (UP/DOWN) for trending regimes.

    Args:
        symbols: List of trading pairs (default: top 12 futures pairs)

    Returns:
        Per-symbol regime classification with ADX, ATR, and volume data.
    """
    client = _get_client()
    try:
        return await classify_market_regime(client, symbols)
    finally:
        await client.close()


@mcp.tool()
async def backtest_dca_tool(
    symbol: str = "BTCUSDT",
    amount_per_interval: float = 100.0,
    interval_days: int = 7,
    total_days: int = 365,
) -> dict:
    """Backtest a DCA (Dollar-Cost Averaging) strategy vs lump-sum investing.

    Simulates periodic fixed-amount purchases over a historical period
    and compares the result to investing the same total amount at the start.

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        amount_per_interval: USD amount per purchase (default: 100)
        interval_days: Days between purchases (default: 7 = weekly)
        total_days: Historical lookback in days (default: 365)

    Returns:
        DCA and lump-sum performance comparison with ROI, P&L, and winner.
    """
    client = _get_client()
    try:
        return await backtest_dca(client, symbol, amount_per_interval, interval_days, total_days)
    finally:
        await client.close()


@mcp.tool()
async def scan_funding_rates_tool(
    top_n: int = 20,
) -> dict:
    """Scan all Binance futures pairs for current funding rates.

    Produces a funding rate heatmap combining premiumIndex + fundingInfo data.
    Each symbol shows: rate%, annualized APR, mark/index premium, time to next
    funding, and payment direction (LONGS_PAY / SHORTS_PAY / NEUTRAL).

    Results are sorted by absolute funding rate (most extreme first).

    Args:
        top_n: Number of top results to return (default: 20)

    Returns:
        Ranked funding rate data with market-wide summary statistics.
    """
    client = _get_client()
    try:
        return await scan_funding_rates(client, top_n)
    finally:
        await client.close()


@mcp.tool()
async def detect_funding_extremes_tool() -> dict:
    """Detect extreme funding rates that may signal arbitrage opportunities.

    Scans all Binance futures pairs and filters for abnormal funding rates:
    - ELEVATED: |rate| > 0.03%
    - HIGH: |rate| > 0.05% or negative < -0.02%
    - EXTREME: |rate| > 0.1% or negative < -0.05%

    Each extreme includes an opportunity score, urgency rating (IMMINENT/SOON/
    UPCOMING based on time to next funding), and an arbitrage hint.

    Returns:
        Filtered list of extreme-rate symbols with severity and arb suggestions.
    """
    client = _get_client()
    try:
        return await detect_funding_extremes(client)
    finally:
        await client.close()


@mcp.tool()
async def analyze_funding_history_tool(
    symbol: str = "BTCUSDT",
    limit: int = 500,
) -> dict:
    """Analyze historical funding rates for a single Binance futures symbol.

    Fetches up to 500 historical funding rate records and computes:
    - Statistics: average, median, std dev, min, max
    - Trend: INCREASING/DECREASING/STABLE (recent vs old quarter comparison)
    - Cumulative cost: total funding paid/received, annualized cost
    - Extremes: count of periods with |rate| > 0.05%
    - Volatility score (0-100) and distribution (positive/negative/zero)

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        limit: Number of historical periods (default: 500, max: 1000)

    Returns:
        Comprehensive funding rate analysis with trend and cost projections.
    """
    client = _get_client()
    try:
        return await analyze_funding_history(client, symbol, limit)
    finally:
        await client.close()


@mcp.tool()
async def scan_basis_spread_tool(
    top_n: int = 20,
) -> dict:
    """Scan spot-futures basis spread across all Binance futures pairs.

    Computes the basis (mark price vs index price) for every pair and
    classifies as CONTANGO (futures premium), BACKWARDATION (futures discount),
    or FLAT. Includes annualized basis estimate from funding rates.

    Args:
        top_n: Number of top results to return (default: 20)

    Returns:
        Ranked basis spread data with contango/backwardation summary.
    """
    client = _get_client()
    try:
        return await scan_basis_spread(client, top_n)
    finally:
        await client.close()
