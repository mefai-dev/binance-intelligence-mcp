"""Tests for the funding rate scanner tool."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.client import BinanceClient
from binance_intelligence.tools.funding_scan import scan_funding_rates


@pytest.fixture
def scan_client(mock_client):
    """Client with funding scan data."""
    return mock_client


class TestScanFundingRates:
    """Tests for scan_funding_rates."""

    @pytest.mark.asyncio
    async def test_returns_tool_name(self, scan_client):
        result = await scan_funding_rates(scan_client)
        assert result["tool"] == "scan_funding_rates"

    @pytest.mark.asyncio
    async def test_returns_total_symbols(self, scan_client):
        result = await scan_funding_rates(scan_client)
        assert result["total_symbols"] == 5

    @pytest.mark.asyncio
    async def test_respects_top_n(self, scan_client):
        result = await scan_funding_rates(scan_client, top_n=2)
        assert result["showing"] == 2
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_sorted_by_absolute_rate(self, scan_client):
        result = await scan_funding_rates(scan_client)
        rates = [abs(r["funding_rate"]) for r in result["results"]]
        assert rates == sorted(rates, reverse=True)

    @pytest.mark.asyncio
    async def test_result_fields(self, scan_client):
        result = await scan_funding_rates(scan_client)
        item = result["results"][0]
        assert "symbol" in item
        assert "funding_rate" in item
        assert "annualized_apr" in item
        assert "mark_price" in item
        assert "index_price" in item
        assert "premium_pct" in item
        assert "mins_to_next_funding" in item
        assert "interval_hours" in item
        assert "direction" in item

    @pytest.mark.asyncio
    async def test_direction_longs_pay(self, scan_client):
        result = await scan_funding_rates(scan_client)
        # DOGEUSDT has rate 0.0012 → LONGS_PAY
        doge = next(r for r in result["results"] if r["symbol"] == "DOGEUSDT")
        assert doge["direction"] == "LONGS_PAY"

    @pytest.mark.asyncio
    async def test_direction_shorts_pay(self, scan_client):
        result = await scan_funding_rates(scan_client)
        xrp = next(r for r in result["results"] if r["symbol"] == "XRPUSDT")
        assert xrp["direction"] == "SHORTS_PAY"

    @pytest.mark.asyncio
    async def test_summary_counts(self, scan_client):
        result = await scan_funding_rates(scan_client)
        s = result["summary"]
        assert s["positive_count"] + s["negative_count"] + s["neutral_count"] == 5

    @pytest.mark.asyncio
    async def test_annualized_apr_calculation(self, scan_client):
        result = await scan_funding_rates(scan_client)
        # DOGEUSDT: rate=0.0012, interval=4h → 6/day → 0.0012*6*365*100
        doge = next(r for r in result["results"] if r["symbol"] == "DOGEUSDT")
        expected = 0.0012 * 6 * 365 * 100
        assert abs(doge["annualized_apr"] - expected) < 0.1

    @pytest.mark.asyncio
    async def test_premium_pct_calculation(self, scan_client):
        result = await scan_funding_rates(scan_client)
        btc = next(r for r in result["results"] if r["symbol"] == "BTCUSDT")
        # mark=100.05, index=100.0 → premium = 0.05%
        assert abs(btc["premium_pct"] - 0.05) < 0.01

    @pytest.mark.asyncio
    async def test_empty_data(self):
        client = BinanceClient()
        client.premium_index_all = AsyncMock(return_value=[])
        client.funding_info = AsyncMock(return_value=[])
        client.close = AsyncMock()
        result = await scan_funding_rates(client)
        assert result["total_symbols"] == 0
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_skips_zero_price(self):
        client = BinanceClient()
        client.premium_index_all = AsyncMock(return_value=[
            {"symbol": "BADUSDT", "lastFundingRate": "0.0001",
             "markPrice": "0", "indexPrice": "0", "nextFundingTime": "0"},
        ])
        client.funding_info = AsyncMock(return_value=[])
        client.close = AsyncMock()
        result = await scan_funding_rates(client)
        assert result["total_symbols"] == 0
