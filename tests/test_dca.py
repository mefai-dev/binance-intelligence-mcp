"""Tests for the DCA Backtester."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.tools.dca import backtest_dca
from tests.conftest import make_klines


class TestBacktestDCA:
    @pytest.mark.asyncio
    async def test_basic_output_structure(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(365, 100, 0.1))
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 365)
        assert result["tool"] == "backtest_dca"
        assert result["symbol"] == "BTCUSDT"
        assert "period" in result
        assert "dca" in result
        assert "lump_sum" in result
        assert "comparison" in result
        assert "price_stats" in result

    @pytest.mark.asyncio
    async def test_dca_fields(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(365, 100, 0.1))
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 365)
        dca = result["dca"]
        assert "total_invested" in dca
        assert "total_units" in dca
        assert "avg_buy_price" in dca
        assert "current_value" in dca
        assert "profit_loss" in dca
        assert "roi_pct" in dca

    @pytest.mark.asyncio
    async def test_lump_sum_fields(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(365, 100, 0.1))
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 365)
        ls = result["lump_sum"]
        assert "total_invested" in ls
        assert "buy_price" in ls
        assert "total_units" in ls
        assert "current_value" in ls
        assert "roi_pct" in ls

    @pytest.mark.asyncio
    async def test_same_total_invested(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(365, 100, 0.1))
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 365)
        assert result["dca"]["total_invested"] == result["lump_sum"]["total_invested"]

    @pytest.mark.asyncio
    async def test_winner_is_valid(self, mock_client):
        mock_client.klines = AsyncMock(return_value=make_klines(365, 100, 0.1))
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 365)
        assert result["comparison"]["winner"] in ("DCA", "LUMP_SUM", "TIE")

    @pytest.mark.asyncio
    async def test_uptrend_lump_sum_wins(self, mock_client):
        # In a strong uptrend, lump sum should beat DCA
        klines = make_klines(100, 100, 1.0)
        mock_client.klines = AsyncMock(return_value=klines)
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 100)
        assert result["comparison"]["winner"] == "LUMP_SUM"

    @pytest.mark.asyncio
    async def test_downtrend_dca_wins(self, mock_client):
        # In a downtrend, DCA should beat lump sum
        klines = make_klines(100, 200, -1.0)
        mock_client.klines = AsyncMock(return_value=klines)
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 100)
        assert result["comparison"]["winner"] == "DCA"

    @pytest.mark.asyncio
    async def test_daily_interval(self, mock_client):
        klines = make_klines(30, 100, 0.5)
        mock_client.klines = AsyncMock(return_value=klines)
        result = await backtest_dca(mock_client, "BTCUSDT", 50, 1, 30)
        assert result["period"]["total_buys"] == 30

    @pytest.mark.asyncio
    async def test_price_stats(self, mock_client):
        klines = make_klines(100, 100, 0.5)
        mock_client.klines = AsyncMock(return_value=klines)
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 100)
        stats = result["price_stats"]
        assert stats["start_price"] > 0
        assert stats["current_price"] > 0
        assert stats["min_price"] <= stats["start_price"]
        assert stats["max_price"] >= stats["start_price"]

    @pytest.mark.asyncio
    async def test_invalid_interval(self, mock_client):
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 0, 30)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_total_days_less_than_interval(self, mock_client):
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 30, 7)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_api_error(self, mock_client):
        mock_client.klines = AsyncMock(side_effect=Exception("fail"))
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 30)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_insufficient_data(self, mock_client):
        mock_client.klines = AsyncMock(return_value=[make_klines(1)[0]])
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 365)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_positive_roi(self, mock_client):
        # Uptrend should give positive ROI for both strategies
        klines = make_klines(100, 100, 0.5)
        mock_client.klines = AsyncMock(return_value=klines)
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 100)
        assert result["dca"]["roi_pct"] > 0
        assert result["lump_sum"]["roi_pct"] > 0

    @pytest.mark.asyncio
    async def test_advantage_pct_positive(self, mock_client):
        klines = make_klines(100, 100, 0.5)
        mock_client.klines = AsyncMock(return_value=klines)
        result = await backtest_dca(mock_client, "BTCUSDT", 100, 7, 100)
        assert result["comparison"]["advantage_pct"] >= 0
