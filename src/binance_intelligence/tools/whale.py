"""Whale Footprint Scanner.

Scans recent aggregate trades to identify large trades (whales).
Classifies trades by size: Dolphin ($50K-$250K), Whale ($250K-$1M), Mega (>$1M).
Computes net buy/sell pressure and identifies the single largest trade.
"""

import asyncio
from typing import Any

from ..client import BinanceClient, DEFAULT_SYMBOLS

TIER_DOLPHIN = 50_000
TIER_WHALE = 250_000
TIER_MEGA = 1_000_000


async def scan_whale_trades(
    client: BinanceClient,
    symbols: list[str] | None = None,
    min_usd: float = 50_000,
) -> dict[str, Any]:
    """Scan for large trades across symbols.

    Returns classified trades, net pressure, and biggest trade per symbol.
    """
    symbols = symbols or DEFAULT_SYMBOLS[:6]

    async def _scan(symbol: str) -> dict:
        try:
            trades = await client.agg_trades(symbol, 500)
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

        large_trades = []
        total_buy_usd = 0.0
        total_sell_usd = 0.0
        biggest_trade = None
        biggest_usd = 0.0

        for t in trades:
            price = float(t["p"])
            qty = float(t["q"])
            usd_value = price * qty
            is_buyer_maker = t.get("m", False)

            if usd_value < min_usd:
                continue

            # Classify tier
            if usd_value >= TIER_MEGA:
                tier = "MEGA"
            elif usd_value >= TIER_WHALE:
                tier = "WHALE"
            else:
                tier = "DOLPHIN"

            side = "SELL" if is_buyer_maker else "BUY"

            if side == "BUY":
                total_buy_usd += usd_value
            else:
                total_sell_usd += usd_value

            if usd_value > biggest_usd:
                biggest_usd = usd_value
                biggest_trade = {
                    "price": price,
                    "qty": qty,
                    "usd_value": round(usd_value, 2),
                    "side": side,
                    "tier": tier,
                    "timestamp": t.get("T", 0),
                }

            large_trades.append({
                "price": price,
                "qty": qty,
                "usd_value": round(usd_value, 2),
                "side": side,
                "tier": tier,
                "timestamp": t.get("T", 0),
            })

        net_pressure = total_buy_usd - total_sell_usd
        net_label = "BUY" if net_pressure > 0 else "SELL" if net_pressure < 0 else "NEUTRAL"

        return {
            "symbol": symbol,
            "trade_count": len(large_trades),
            "total_buy_usd": round(total_buy_usd, 2),
            "total_sell_usd": round(total_sell_usd, 2),
            "net_pressure_usd": round(net_pressure, 2),
            "net_direction": net_label,
            "biggest_trade": biggest_trade,
            "tiers": {
                "dolphin": sum(1 for t in large_trades if t["tier"] == "DOLPHIN"),
                "whale": sum(1 for t in large_trades if t["tier"] == "WHALE"),
                "mega": sum(1 for t in large_trades if t["tier"] == "MEGA"),
            },
        }

    results = await asyncio.gather(*[_scan(s) for s in symbols])
    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda x: abs(x["net_pressure_usd"]), reverse=True)

    return {
        "tool": "scan_whale_trades",
        "min_usd": min_usd,
        "count": len(valid),
        "results": valid,
        "errors": [r for r in results if "error" in r],
    }
