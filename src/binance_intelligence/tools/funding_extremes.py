"""Funding Rate Extreme Detector.

Identifies symbols with extreme funding rates that may present arbitrage
opportunities. Combines premiumIndex (all) + fundingInfo to classify severity,
compute opportunity scores, and provide urgency ratings.
"""

import asyncio
import time
from typing import Any

from ..client import BinanceClient


# Severity thresholds (absolute funding rate as percentage)
_THRESHOLDS = [
    (0.1, "EXTREME"),
    (0.05, "HIGH"),
    (0.03, "ELEVATED"),
]

_NEGATIVE_THRESHOLDS = [
    (-0.05, "EXTREME"),
    (-0.02, "HIGH"),
]


def _classify_severity(rate_pct: float) -> str | None:
    """Classify funding rate severity. Returns None if within normal range."""
    if rate_pct > 0:
        for threshold, label in _THRESHOLDS:
            if rate_pct >= threshold:
                return label
        return None
    else:
        for threshold, label in _NEGATIVE_THRESHOLDS:
            if rate_pct <= threshold:
                return label
        return None


def _urgency(mins_to_next: float) -> str:
    """Classify urgency based on time to next funding."""
    if mins_to_next < 60:
        return "IMMINENT"
    elif mins_to_next < 240:
        return "SOON"
    else:
        return "UPCOMING"


async def detect_funding_extremes(
    client: BinanceClient,
) -> dict[str, Any]:
    """Detect extreme funding rates across all futures pairs.

    Returns filtered list of only extreme-rate symbols with arbitrage hints.
    """
    premium_data, funding_info_data = await asyncio.gather(
        client.premium_index_all(),
        client.funding_info(),
    )

    info_map: dict[str, dict] = {}
    for fi in funding_info_data:
        info_map[fi["symbol"]] = fi

    now_ms = int(time.time() * 1000)
    extremes = []

    for item in premium_data:
        symbol = item.get("symbol", "")
        rate = float(item.get("lastFundingRate", 0))
        mark = float(item.get("markPrice", 0))
        index_price = float(item.get("indexPrice", 0))
        next_funding_ms = int(item.get("nextFundingTime", 0))

        if mark == 0 or index_price == 0:
            continue

        rate_pct = rate * 100
        severity = _classify_severity(rate_pct)
        if severity is None:
            continue

        premium_pct = (mark - index_price) / index_price * 100
        mins_to_next = max(0, (next_funding_ms - now_ms) / 60000)

        # Opportunity score: higher = more interesting
        score = abs(rate) * 10000 + abs(premium_pct) * 10

        # Funding info
        info = info_map.get(symbol, {})
        interval_hours = int(info.get("fundingIntervalHours", 8))
        periods_per_day = 24 / interval_hours if interval_hours > 0 else 3
        annualized_apr = rate * periods_per_day * 365 * 100

        # Arbitrage hint
        if rate > 0:
            arb_hint = "Short perp + long spot to collect funding"
        else:
            arb_hint = "Long perp + short spot to collect funding"

        extremes.append({
            "symbol": symbol,
            "funding_rate_pct": round(rate_pct, 6),
            "severity": severity,
            "score": round(score, 2),
            "urgency": _urgency(mins_to_next),
            "mins_to_next_funding": round(mins_to_next, 1),
            "annualized_apr": round(annualized_apr, 2),
            "mark_price": round(mark, 4),
            "index_price": round(index_price, 4),
            "premium_pct": round(premium_pct, 4),
            "interval_hours": interval_hours,
            "arbitrage_hint": arb_hint,
        })

    # Sort by score descending
    extremes.sort(key=lambda x: x["score"], reverse=True)

    # Summary
    severity_counts = {}
    for e in extremes:
        severity_counts[e["severity"]] = severity_counts.get(e["severity"], 0) + 1

    return {
        "tool": "detect_funding_extremes",
        "total_extreme": len(extremes),
        "severity_counts": severity_counts,
        "results": extremes,
    }
