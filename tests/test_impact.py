"""Tests for the Market Impact Simulator."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.tools.impact import simulate_market_impact


class TestSimulateMarketImpact:
    @pytest.mark.asyncio
    async def test_basic_output_structure(self, mock_client):
        result = await simulate_market_impact(mock_client, "BTCUSDT", "BUY", 1000)
        assert result["tool"] == "simulate_market_impact"
        assert result["symbol"] == "BTCUSDT"
        assert result["side"] == "BUY"
        assert "levels_consumed" in result
        assert "avg_fill_price" in result
        assert "worst_fill_price" in result
        assert "slippage_pct" in result
        assert "impact_rating" in result

    @pytest.mark.asyncio
    async def test_small_buy_single_level(self, mock_client):
        # $500 buy should only consume part of first level (100*10=1000 available)
        result = await simulate_market_impact(mock_client, "BTCUSDT", "BUY", 500)
        assert result["levels_consumed"] == 1
        assert result["avg_fill_price"] == 100.0
        assert result["slippage_pct"] == 0.0
        assert result["fully_filled"] is True

    @pytest.mark.asyncio
    async def test_multi_level_buy(self, mock_client):
        # $5000 buy: first level 100*10=1000, need more levels
        result = await simulate_market_impact(mock_client, "BTCUSDT", "BUY", 5000)
        assert result["levels_consumed"] > 1
        assert result["avg_fill_price"] > 100.0
        assert result["worst_fill_price"] >= result["avg_fill_price"]

    @pytest.mark.asyncio
    async def test_sell_side(self, mock_client):
        result = await simulate_market_impact(mock_client, "BTCUSDT", "SELL", 500)
        assert result["side"] == "SELL"
        assert result["best_price"] == 99.9

    @pytest.mark.asyncio
    async def test_sell_slippage(self, mock_client):
        # For sells, slippage is best - avg (price goes down)
        result = await simulate_market_impact(mock_client, "BTCUSDT", "SELL", 5000)
        assert result["slippage_pct"] >= 0

    @pytest.mark.asyncio
    async def test_impact_ratings(self, mock_client):
        result = await simulate_market_impact(mock_client, "BTCUSDT", "BUY", 100)
        assert result["impact_rating"] in ("NEGLIGIBLE", "LOW", "MODERATE", "HIGH", "SEVERE")

    @pytest.mark.asyncio
    async def test_large_order_high_impact(self, mock_client):
        # Very large order consumes many levels
        result = await simulate_market_impact(mock_client, "BTCUSDT", "BUY", 50000)
        assert result["levels_consumed"] > 3
        assert result["slippage_pct"] > 0

    @pytest.mark.asyncio
    async def test_empty_orderbook(self, mock_client):
        mock_client.depth = AsyncMock(return_value={"asks": [], "bids": []})
        result = await simulate_market_impact(mock_client, "BTCUSDT", "BUY", 1000)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_api_error(self, mock_client):
        mock_client.depth = AsyncMock(side_effect=Exception("API error"))
        result = await simulate_market_impact(mock_client, "BTCUSDT", "BUY", 1000)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_total_cost_matches(self, mock_client):
        result = await simulate_market_impact(mock_client, "BTCUSDT", "BUY", 1000)
        assert result["total_cost_usd"] <= 1000
        assert result["filled_usd"] <= 1000

    @pytest.mark.asyncio
    async def test_partial_fill(self, mock_client):
        # Order larger than entire book
        mock_client.depth = AsyncMock(return_value={
            "asks": [["100.0", "1"]],  # Only $100 available
            "bids": [],
        })
        result = await simulate_market_impact(mock_client, "BTCUSDT", "BUY", 1000)
        assert result["fully_filled"] is False
        assert result["filled_usd"] < 1000

    @pytest.mark.asyncio
    async def test_case_insensitive_side(self, mock_client):
        result = await simulate_market_impact(mock_client, "BTCUSDT", "buy", 500)
        assert result["side"] == "BUY"
