"""Market Impact Simulator.

Walks the order book to simulate the impact of a large market order.
Reports levels consumed, average fill price, worst fill price,
slippage percentage, and total cost.
"""

from typing import Any

from ..client import BinanceClient


async def simulate_market_impact(
    client: BinanceClient,
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    amount_usd: float = 100_000,
) -> dict[str, Any]:
    """Simulate placing a large market order and compute impact.

    Walks the order book (asks for BUY, bids for SELL) accumulating
    quantity until amount_usd is filled.
    """
    try:
        book = await client.depth(symbol, 1000)
    except Exception as e:
        return {"tool": "simulate_market_impact", "symbol": symbol, "error": str(e)}

    # Select the appropriate side of the book
    if side.upper() == "BUY":
        levels = book.get("asks", [])
    else:
        levels = book.get("bids", [])

    if not levels:
        return {
            "tool": "simulate_market_impact",
            "symbol": symbol,
            "error": "empty order book",
        }

    best_price = float(levels[0][0])
    remaining_usd = amount_usd
    total_qty = 0.0
    total_cost = 0.0
    levels_consumed = 0
    worst_fill = best_price

    for price_str, qty_str in levels:
        if remaining_usd <= 0:
            break

        price = float(price_str)
        qty = float(qty_str)
        level_value = price * qty

        if level_value <= remaining_usd:
            # Consume entire level
            total_qty += qty
            total_cost += level_value
            remaining_usd -= level_value
        else:
            # Partial fill at this level
            fill_qty = remaining_usd / price
            total_qty += fill_qty
            total_cost += remaining_usd
            remaining_usd = 0

        worst_fill = price
        levels_consumed += 1

    avg_fill = total_cost / total_qty if total_qty > 0 else best_price
    slippage_pct = ((avg_fill - best_price) / best_price) * 100 if side.upper() == "BUY" else ((best_price - avg_fill) / best_price) * 100
    filled_usd = amount_usd - remaining_usd

    return {
        "tool": "simulate_market_impact",
        "symbol": symbol,
        "side": side.upper(),
        "requested_usd": amount_usd,
        "filled_usd": round(filled_usd, 2),
        "fully_filled": remaining_usd <= 0,
        "levels_consumed": levels_consumed,
        "best_price": best_price,
        "avg_fill_price": round(avg_fill, 4),
        "worst_fill_price": worst_fill,
        "slippage_pct": round(abs(slippage_pct), 4),
        "total_qty": round(total_qty, 6),
        "total_cost_usd": round(total_cost, 2),
        "impact_rating": (
            "NEGLIGIBLE" if abs(slippage_pct) < 0.01
            else "LOW" if abs(slippage_pct) < 0.05
            else "MODERATE" if abs(slippage_pct) < 0.2
            else "HIGH" if abs(slippage_pct) < 1.0
            else "SEVERE"
        ),
    }
