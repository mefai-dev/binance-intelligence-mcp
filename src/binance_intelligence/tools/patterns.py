"""Candlestick Pattern Scanner.

Detects classic candlestick patterns from kline data:
  - Hammer / Inverted Hammer
  - Bullish / Bearish Engulfing
  - Doji
  - Morning Star / Evening Star
  - Three White Soldiers / Three Black Crows

Each pattern has a confidence score (0-100) and a direction (BULLISH/BEARISH).
"""

import asyncio
from typing import Any

from ..client import BinanceClient, DEFAULT_SYMBOLS


def _candle(k: list) -> dict:
    """Parse a kline array into a candle dict."""
    o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
    body = abs(c - o)
    full_range = h - l
    return {
        "open": o, "high": h, "low": l, "close": c,
        "body": body,
        "range": full_range,
        "upper_wick": h - max(o, c),
        "lower_wick": min(o, c) - l,
        "bullish": c > o,
        "bearish": c < o,
    }


def _detect_patterns(candles: list[dict]) -> list[dict]:
    """Detect patterns from a list of parsed candles."""
    patterns = []
    if len(candles) < 3:
        return patterns

    for i in range(2, len(candles)):
        curr = candles[i]
        prev = candles[i - 1]
        prev2 = candles[i - 2]

        body_ratio = curr["body"] / curr["range"] if curr["range"] > 0 else 0

        # Doji: very small body relative to range
        if curr["range"] > 0 and body_ratio < 0.1:
            patterns.append({
                "pattern": "DOJI",
                "index": i,
                "direction": "NEUTRAL",
                "confidence": round(min(100, (1 - body_ratio) * 60 + 40), 1),
            })

        # Hammer: small body at top, long lower wick (>2x body)
        if (curr["body"] > 0
                and curr["lower_wick"] > curr["body"] * 2
                and curr["upper_wick"] < curr["body"] * 0.5):
            conf = min(100, (curr["lower_wick"] / curr["body"]) * 25)
            patterns.append({
                "pattern": "HAMMER",
                "index": i,
                "direction": "BULLISH",
                "confidence": round(conf, 1),
            })

        # Inverted Hammer: small body at bottom, long upper wick
        if (curr["body"] > 0
                and curr["upper_wick"] > curr["body"] * 2
                and curr["lower_wick"] < curr["body"] * 0.5):
            conf = min(100, (curr["upper_wick"] / curr["body"]) * 25)
            patterns.append({
                "pattern": "INVERTED_HAMMER",
                "index": i,
                "direction": "BULLISH",
                "confidence": round(conf, 1),
            })

        # Bullish Engulfing: prev bearish, curr bullish, curr body engulfs prev body
        if (prev["bearish"] and curr["bullish"]
                and curr["close"] > prev["open"]
                and curr["open"] < prev["close"]):
            size_ratio = curr["body"] / prev["body"] if prev["body"] > 0 else 1
            conf = min(100, size_ratio * 40 + 30)
            patterns.append({
                "pattern": "BULLISH_ENGULFING",
                "index": i,
                "direction": "BULLISH",
                "confidence": round(conf, 1),
            })

        # Bearish Engulfing: prev bullish, curr bearish, curr body engulfs prev body
        if (prev["bullish"] and curr["bearish"]
                and curr["open"] > prev["close"]
                and curr["close"] < prev["open"]):
            size_ratio = curr["body"] / prev["body"] if prev["body"] > 0 else 1
            conf = min(100, size_ratio * 40 + 30)
            patterns.append({
                "pattern": "BEARISH_ENGULFING",
                "index": i,
                "direction": "BEARISH",
                "confidence": round(conf, 1),
            })

        # Morning Star: bearish prev2, small body prev, bullish curr
        if (prev2["bearish"] and prev["body"] < prev2["body"] * 0.3
                and curr["bullish"] and curr["close"] > (prev2["open"] + prev2["close"]) / 2):
            patterns.append({
                "pattern": "MORNING_STAR",
                "index": i,
                "direction": "BULLISH",
                "confidence": 75.0,
            })

        # Evening Star: bullish prev2, small body prev, bearish curr
        if (prev2["bullish"] and prev["body"] < prev2["body"] * 0.3
                and curr["bearish"] and curr["close"] < (prev2["open"] + prev2["close"]) / 2):
            patterns.append({
                "pattern": "EVENING_STAR",
                "index": i,
                "direction": "BEARISH",
                "confidence": 75.0,
            })

    # Three White Soldiers / Three Black Crows
    for i in range(2, len(candles)):
        c0, c1, c2 = candles[i - 2], candles[i - 1], candles[i]

        if (c0["bullish"] and c1["bullish"] and c2["bullish"]
                and c1["close"] > c0["close"] and c2["close"] > c1["close"]
                and c1["open"] > c0["open"] and c2["open"] > c1["open"]):
            patterns.append({
                "pattern": "THREE_WHITE_SOLDIERS",
                "index": i,
                "direction": "BULLISH",
                "confidence": 80.0,
            })

        if (c0["bearish"] and c1["bearish"] and c2["bearish"]
                and c1["close"] < c0["close"] and c2["close"] < c1["close"]
                and c1["open"] < c0["open"] and c2["open"] < c1["open"]):
            patterns.append({
                "pattern": "THREE_BLACK_CROWS",
                "index": i,
                "direction": "BEARISH",
                "confidence": 80.0,
            })

    return patterns


async def scan_candlestick_patterns(
    client: BinanceClient,
    symbols: list[str] | None = None,
    interval: str = "4h",
) -> dict[str, Any]:
    """Scan for candlestick patterns across symbols."""
    symbols = symbols or DEFAULT_SYMBOLS

    async def _scan(symbol: str) -> dict:
        try:
            klines = await client.klines(symbol, interval, 50)
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

        candles = [_candle(k) for k in klines]
        detected = _detect_patterns(candles)

        return {
            "symbol": symbol,
            "interval": interval,
            "candles_analyzed": len(candles),
            "patterns_found": len(detected),
            "patterns": detected,
        }

    results = await asyncio.gather(*[_scan(s) for s in symbols])
    valid = [r for r in results if "error" not in r]

    # Deduplicate: keep only most recent occurrence of each pattern type
    for r in valid:
        seen: dict[str, dict] = {}
        for p in r["patterns"]:
            key = p["pattern"]
            if key not in seen or p["index"] > seen[key]["index"]:
                seen[key] = p
        r["patterns"] = sorted(seen.values(), key=lambda x: x["index"], reverse=True)
        r["patterns_found"] = len(r["patterns"])

    valid.sort(key=lambda x: x["patterns_found"], reverse=True)

    return {
        "tool": "scan_candlestick_patterns",
        "interval": interval,
        "count": len(valid),
        "results": valid,
        "errors": [r for r in results if "error" in r],
    }
