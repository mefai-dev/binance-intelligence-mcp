"""Tests for the basis spread scanner tool."""

import pytest
from unittest.mock import AsyncMock

from binance_intelligence.client import BinanceClient
from binance_intelligence.tools.basis_spread import scan_basis_spread


@pytest.fixture
def basis_client(mock_client):
    """Client with basis spread data."""
    return mock_client


class TestScanBasisSpread:
    """Tests for scan_basis_spread."""

    @pytest.mark.asyncio
    async def test_returns_tool_name(self, basis_client):
        result = await scan_basis_spread(basis_client)
        assert result["tool"] == "scan_basis_spread"

    @pytest.mark.asyncio
    async def test_returns_total_symbols(self, basis_client):
        result = await scan_basis_spread(basis_client)
        assert result["total_symbols"] == 5

    @pytest.mark.asyncio
    async def test_respects_top_n(self, basis_client):
        result = await scan_basis_spread(basis_client, top_n=2)
        assert result["showing"] == 2
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_sorted_by_absolute_basis(self, basis_client):
        result = await scan_basis_spread(basis_client)
        basis = [abs(r["basis_pct"]) for r in result["results"]]
        assert basis == sorted(basis, reverse=True)

    @pytest.mark.asyncio
    async def test_contango_detected(self, basis_client):
        result = await scan_basis_spread(basis_client)
        # BTCUSDT: mark=100.05, index=100.0 → basis=0.05% → CONTANGO
        btc = next(r for r in result["results"] if r["symbol"] == "BTCUSDT")
        assert btc["state"] == "CONTANGO"

    @pytest.mark.asyncio
    async def test_backwardation_detected(self, basis_client):
        result = await scan_basis_spread(basis_client)
        # SOLUSDT: mark=19.95, index=20.0 → basis=-0.25% → BACKWARDATION
        sol = next(r for r in result["results"] if r["symbol"] == "SOLUSDT")
        assert sol["state"] == "BACKWARDATION"

    @pytest.mark.asyncio
    async def test_result_fields(self, basis_client):
        result = await scan_basis_spread(basis_client)
        item = result["results"][0]
        assert "symbol" in item
        assert "mark_price" in item
        assert "index_price" in item
        assert "basis_pct" in item
        assert "state" in item
        assert "funding_rate_pct" in item
        assert "annualized_basis_pct" in item

    @pytest.mark.asyncio
    async def test_summary_counts(self, basis_client):
        result = await scan_basis_spread(basis_client)
        s = result["summary"]
        total = s["contango_count"] + s["backwardation_count"] + s["flat_count"]
        assert total == 5

    @pytest.mark.asyncio
    async def test_annualized_basis(self, basis_client):
        result = await scan_basis_spread(basis_client)
        btc = next(r for r in result["results"] if r["symbol"] == "BTCUSDT")
        # rate=0.0001 → annualized = 0.0001 * 3 * 365 * 100 = 10.95
        expected = 0.0001 * 3 * 365 * 100
        assert abs(btc["annualized_basis_pct"] - expected) < 0.1

    @pytest.mark.asyncio
    async def test_max_contango_symbol(self, basis_client):
        result = await scan_basis_spread(basis_client)
        assert result["summary"]["max_contango_symbol"] is not None

    @pytest.mark.asyncio
    async def test_max_backwardation_symbol(self, basis_client):
        result = await scan_basis_spread(basis_client)
        assert result["summary"]["max_backwardation_symbol"] is not None

    @pytest.mark.asyncio
    async def test_empty_data(self):
        client = BinanceClient()
        client.premium_index_all = AsyncMock(return_value=[])
        client.close = AsyncMock()
        result = await scan_basis_spread(client)
        assert result["total_symbols"] == 0
        assert result["results"] == []
