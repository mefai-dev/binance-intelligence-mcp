"""Spot-Futures Basis Spread Scanner.

Uses premiumIndex (all symbols) to compute the basis spread between mark price
and index price for every futures pair. Identifies contango, backwardation,
and flat states with annualized basis estimates.
"""

from typing import Any

from ..client import BinanceClient


async def scan_basis_spread(
    client: BinanceClient,
    top_n: int = 20,
) -> dict[str, Any]:
    """Scan all futures pairs for basis spread (mark vs index).

    Returns ranked list sorted by absolute basis spread.
    """
    premium_data = await client.premium_index_all()

    results = []

    for item in premium_data:
        symbol = item.get("symbol", "")
        mark = float(item.get("markPrice", 0))
        index_price = float(item.get("indexPrice", 0))
        rate = float(item.get("lastFundingRate", 0))

        if index_price == 0 or mark == 0:
            continue

        # Basis = (mark - index) / index * 100
        basis_pct = (mark - index_price) / index_price * 100

        # State classification
        if basis_pct > 0.01:
            state = "CONTANGO"
        elif basis_pct < -0.01:
            state = "BACKWARDATION"
        else:
            state = "FLAT"

        # Annualized basis = funding_rate * 3 * 365 * 100
        # (assuming 8h funding → 3 per day)
        annualized_basis = rate * 3 * 365 * 100

        results.append({
            "symbol": symbol,
            "mark_price": round(mark, 4),
            "index_price": round(index_price, 4),
            "basis_pct": round(basis_pct, 6),
            "state": state,
            "funding_rate_pct": round(rate * 100, 6),
            "annualized_basis_pct": round(annualized_basis, 2),
        })

    # Sort by absolute basis descending
    results.sort(key=lambda x: abs(x["basis_pct"]), reverse=True)

    # Summary
    contango_count = sum(1 for r in results if r["state"] == "CONTANGO")
    backwardation_count = sum(1 for r in results if r["state"] == "BACKWARDATION")
    flat_count = sum(1 for r in results if r["state"] == "FLAT")
    basis_values = [r["basis_pct"] for r in results]
    avg_basis = sum(basis_values) / len(basis_values) if basis_values else 0

    # Find max contango and max backwardation
    contango_items = [r for r in results if r["state"] == "CONTANGO"]
    backwardation_items = [r for r in results if r["state"] == "BACKWARDATION"]
    max_contango = max(contango_items, key=lambda x: x["basis_pct"])["symbol"] if contango_items else None
    max_backwardation = min(backwardation_items, key=lambda x: x["basis_pct"])["symbol"] if backwardation_items else None

    top_results = results[:top_n]

    return {
        "tool": "scan_basis_spread",
        "total_symbols": len(results),
        "showing": len(top_results),
        "summary": {
            "avg_basis_pct": round(avg_basis, 6),
            "contango_count": contango_count,
            "backwardation_count": backwardation_count,
            "flat_count": flat_count,
            "max_contango_symbol": max_contango,
            "max_backwardation_symbol": max_backwardation,
        },
        "results": top_results,
    }
