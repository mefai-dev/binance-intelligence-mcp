"""Tests for the Whale Footprint Scanner."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.tools.whale import scan_whale_trades, TIER_DOLPHIN, TIER_WHALE, TIER_MEGA


class TestScanWhaleTrades:
    @pytest.mark.asyncio
    async def test_basic_output_structure(self, mock_client):
        result = await scan_whale_trades(mock_client, ["BTCUSDT"])
        assert result["tool"] == "scan_whale_trades"
        assert result["min_usd"] == 50000
        assert result["count"] == 1
        assert "results" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_trade_classification(self, mock_client):
        result = await scan_whale_trades(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        tiers = r["tiers"]
        # From conftest: $60K (dolphin), $300K (whale), $5K (skip), $1.2M (mega), $80K (dolphin)
        assert tiers["dolphin"] == 2
        assert tiers["whale"] == 1
        assert tiers["mega"] == 1

    @pytest.mark.asyncio
    async def test_net_pressure(self, mock_client):
        result = await scan_whale_trades(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        # Buys: $60K + $1.2M = $1.26M, Sells: $300K + $80K = $380K
        assert r["net_direction"] == "BUY"
        assert r["net_pressure_usd"] > 0

    @pytest.mark.asyncio
    async def test_biggest_trade(self, mock_client):
        result = await scan_whale_trades(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert r["biggest_trade"] is not None
        assert r["biggest_trade"]["usd_value"] == 1200000.0
        assert r["biggest_trade"]["tier"] == "MEGA"
        assert r["biggest_trade"]["side"] == "BUY"

    @pytest.mark.asyncio
    async def test_custom_min_usd(self, mock_client):
        result = await scan_whale_trades(mock_client, ["BTCUSDT"], min_usd=100_000)
        r = result["results"][0]
        # Only $300K, $1.2M qualify
        assert r["trade_count"] == 2

    @pytest.mark.asyncio
    async def test_no_large_trades(self, mock_client):
        mock_client.agg_trades = AsyncMock(return_value=[
            {"p": "100.0", "q": "1", "m": False, "T": 1700000000000},
        ])
        result = await scan_whale_trades(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert r["trade_count"] == 0
        assert r["biggest_trade"] is None
        assert r["net_direction"] == "NEUTRAL"

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_client):
        mock_client.agg_trades = AsyncMock(side_effect=Exception("timeout"))
        result = await scan_whale_trades(mock_client, ["BTCUSDT"])
        assert result["count"] == 0
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, mock_client):
        result = await scan_whale_trades(mock_client, ["BTCUSDT", "ETHUSDT"])
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_all_sells(self, mock_client):
        mock_client.agg_trades = AsyncMock(return_value=[
            {"p": "100.0", "q": "1000", "m": True, "T": 1700000000000},
        ])
        result = await scan_whale_trades(mock_client, ["BTCUSDT"])
        r = result["results"][0]
        assert r["net_direction"] == "SELL"

    @pytest.mark.asyncio
    async def test_results_sorted_by_pressure(self, mock_client):
        result = await scan_whale_trades(mock_client, ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        pressures = [abs(r["net_pressure_usd"]) for r in result["results"]]
        assert pressures == sorted(pressures, reverse=True)

    @pytest.mark.asyncio
    async def test_tier_thresholds(self):
        assert TIER_DOLPHIN == 50_000
        assert TIER_WHALE == 250_000
        assert TIER_MEGA == 1_000_000
