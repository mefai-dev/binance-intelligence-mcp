"""Funding Rate History Analyzer.

Fetches historical funding rates for a single symbol and computes statistics:
average, median, std dev, min/max, trend analysis, cumulative costs,
extreme counts, volatility score, and distribution breakdowns.
"""

import statistics
from typing import Any

from ..client import BinanceClient


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


async def analyze_funding_history(
    client: BinanceClient,
    symbol: str = "BTCUSDT",
    limit: int = 500,
) -> dict[str, Any]:
    """Analyze historical funding rates for a symbol.

    Returns statistics, trend analysis, cumulative costs, and distribution.
    """
    history = await client.funding_rate_history(symbol, limit)

    if not history:
        return {
            "tool": "analyze_funding_history",
            "symbol": symbol,
            "error": "no funding rate data available",
        }

    # Extract rates as percentages
    rates = [float(h["fundingRate"]) * 100 for h in history]
    raw_rates = [float(h["fundingRate"]) for h in history]
    timestamps = [int(h.get("fundingTime", 0)) for h in history]

    n = len(rates)

    # Basic statistics
    avg = statistics.mean(rates)
    median = statistics.median(rates)
    std_dev = statistics.stdev(rates) if n >= 2 else 0.0
    min_rate = min(rates)
    max_rate = max(rates)

    # Trend: compare last 25% vs first 25%
    quarter = max(1, n // 4)
    old_quarter = rates[:quarter]
    new_quarter = rates[-quarter:]
    old_avg = statistics.mean(old_quarter)
    new_avg = statistics.mean(new_quarter)

    trend_diff = new_avg - old_avg
    if abs(trend_diff) < 0.001:
        trend = "STABLE"
    elif trend_diff > 0:
        trend = "INCREASING"
    else:
        trend = "DECREASING"

    # Cumulative funding cost (sum of raw rates)
    cumulative_raw = sum(raw_rates)
    cumulative_pct = cumulative_raw * 100

    # Annualized cost: assume 8h intervals → 3 per day → 1095 per year
    # Scale based on actual periods
    if n > 0:
        annualized_cost = (cumulative_raw / n) * 1095 * 100
    else:
        annualized_cost = 0

    # Extreme counts (|rate| > 0.05%)
    extreme_positive = sum(1 for r in rates if r > 0.05)
    extreme_negative = sum(1 for r in rates if r < -0.05)

    # Volatility score (0-100) based on std dev
    # 0.01% std = low, 0.05% std = moderate, 0.1%+ std = high
    volatility_score = _clamp(std_dev * 1000, 0, 100)

    # Distribution
    positive_count = sum(1 for r in rates if r > 0)
    negative_count = sum(1 for r in rates if r < 0)
    zero_count = sum(1 for r in rates if r == 0)

    # Time range
    time_start = timestamps[0] if timestamps else 0
    time_end = timestamps[-1] if timestamps else 0

    return {
        "tool": "analyze_funding_history",
        "symbol": symbol,
        "periods_analyzed": n,
        "time_range": {
            "start_ms": time_start,
            "end_ms": time_end,
        },
        "statistics": {
            "average_pct": round(avg, 6),
            "median_pct": round(median, 6),
            "std_dev_pct": round(std_dev, 6),
            "min_pct": round(min_rate, 6),
            "max_pct": round(max_rate, 6),
        },
        "trend": {
            "direction": trend,
            "old_quarter_avg_pct": round(old_avg, 6),
            "new_quarter_avg_pct": round(new_avg, 6),
        },
        "cumulative": {
            "total_funding_pct": round(cumulative_pct, 4),
            "annualized_cost_pct": round(annualized_cost, 4),
        },
        "extremes": {
            "extreme_positive_count": extreme_positive,
            "extreme_negative_count": extreme_negative,
            "total_extreme": extreme_positive + extreme_negative,
        },
        "volatility_score": round(volatility_score, 1),
        "distribution": {
            "positive_periods": positive_count,
            "negative_periods": negative_count,
            "zero_periods": zero_count,
        },
    }
