"""Tests for the funding history analyzer tool."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.client import BinanceClient
from binance_intelligence.tools.funding_history import analyze_funding_history


@pytest.fixture
def history_client(mock_client):
    """Client with funding history data."""
    return mock_client


class TestAnalyzeFundingHistory:
    """Tests for analyze_funding_history."""

    @pytest.mark.asyncio
    async def test_returns_tool_name(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        assert result["tool"] == "analyze_funding_history"

    @pytest.mark.asyncio
    async def test_returns_symbol(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        assert result["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_periods_analyzed(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        assert result["periods_analyzed"] == 100

    @pytest.mark.asyncio
    async def test_statistics_fields(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        stats = result["statistics"]
        assert "average_pct" in stats
        assert "median_pct" in stats
        assert "std_dev_pct" in stats
        assert "min_pct" in stats
        assert "max_pct" in stats

    @pytest.mark.asyncio
    async def test_trend_fields(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        trend = result["trend"]
        assert trend["direction"] in ("INCREASING", "DECREASING", "STABLE")
        assert "old_quarter_avg_pct" in trend
        assert "new_quarter_avg_pct" in trend

    @pytest.mark.asyncio
    async def test_cumulative_fields(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        cum = result["cumulative"]
        assert "total_funding_pct" in cum
        assert "annualized_cost_pct" in cum

    @pytest.mark.asyncio
    async def test_extremes_fields(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        ext = result["extremes"]
        assert "extreme_positive_count" in ext
        assert "extreme_negative_count" in ext
        assert "total_extreme" in ext
        assert ext["total_extreme"] == ext["extreme_positive_count"] + ext["extreme_negative_count"]

    @pytest.mark.asyncio
    async def test_volatility_score_range(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        assert 0 <= result["volatility_score"] <= 100

    @pytest.mark.asyncio
    async def test_distribution_adds_up(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        dist = result["distribution"]
        total = dist["positive_periods"] + dist["negative_periods"] + dist["zero_periods"]
        assert total == 100

    @pytest.mark.asyncio
    async def test_time_range(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT")
        tr = result["time_range"]
        assert tr["start_ms"] < tr["end_ms"]

    @pytest.mark.asyncio
    async def test_empty_history(self):
        client = BinanceClient()
        client.funding_rate_history = AsyncMock(return_value=[])
        client.close = AsyncMock()
        result = await analyze_funding_history(client, "BTCUSDT")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_custom_limit(self, history_client):
        result = await analyze_funding_history(history_client, "BTCUSDT", limit=100)
        history_client.funding_rate_history.assert_called_once_with("BTCUSDT", 100)

    @pytest.mark.asyncio
    async def test_stable_trend(self):
        """Constant rates should give STABLE trend."""
        client = BinanceClient()
        client.funding_rate_history = AsyncMock(return_value=[
            {"fundingRate": "0.0001", "fundingTime": str(1700000000000 + i * 28800000),
             "symbol": "BTCUSDT"}
            for i in range(100)
        ])
        client.close = AsyncMock()
        result = await analyze_funding_history(client, "BTCUSDT")
        assert result["trend"]["direction"] == "STABLE"

    @pytest.mark.asyncio
    async def test_increasing_trend(self):
        """Rates that increase over time should give INCREASING trend."""
        client = BinanceClient()
        client.funding_rate_history = AsyncMock(return_value=[
            {"fundingRate": str(0.0001 + i * 0.0001), "fundingTime": str(1700000000000 + i * 28800000),
             "symbol": "BTCUSDT"}
            for i in range(100)
        ])
        client.close = AsyncMock()
        result = await analyze_funding_history(client, "BTCUSDT")
        assert result["trend"]["direction"] == "INCREASING"

    @pytest.mark.asyncio
    async def test_decreasing_trend(self):
        """Rates that decrease over time should give DECREASING trend."""
        client = BinanceClient()
        client.funding_rate_history = AsyncMock(return_value=[
            {"fundingRate": str(0.001 - i * 0.0001), "fundingTime": str(1700000000000 + i * 28800000),
             "symbol": "BTCUSDT"}
            for i in range(100)
        ])
        client.close = AsyncMock()
        result = await analyze_funding_history(client, "BTCUSDT")
        assert result["trend"]["direction"] == "DECREASING"

    @pytest.mark.asyncio
    async def test_min_max_correct(self):
        """Min and max should match actual data range."""
        client = BinanceClient()
        rates = [0.0001, 0.0005, -0.0002, 0.001, -0.001]
        client.funding_rate_history = AsyncMock(return_value=[
            {"fundingRate": str(rates[i % len(rates)]),
             "fundingTime": str(1700000000000 + i * 28800000),
             "symbol": "BTCUSDT"}
            for i in range(50)
        ])
        client.close = AsyncMock()
        result = await analyze_funding_history(client, "BTCUSDT")
        assert result["statistics"]["min_pct"] == round(-0.001 * 100, 6)
        assert result["statistics"]["max_pct"] == round(0.001 * 100, 6)
