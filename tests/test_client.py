"""Tests for the Binance API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp

from binance_intelligence.client import BinanceClient, SPOT_BASE, FUTURES_BASE


class TestBinanceClient:
    """Tests for BinanceClient."""

    def test_init_defaults(self):
        client = BinanceClient()
        assert client._session is None

    def test_init_custom_concurrency(self):
        client = BinanceClient(max_concurrent=5)
        assert client._semaphore._value == 5

    @pytest.mark.asyncio
    async def test_get_session_creates_session(self):
        client = BinanceClient()
        session = await client._get_session()
        assert session is not None
        assert not session.closed
        await client.close()

    @pytest.mark.asyncio
    async def test_close_session(self):
        client = BinanceClient()
        await client._get_session()
        await client.close()
        assert client._session.closed

    @pytest.mark.asyncio
    async def test_close_without_session(self):
        client = BinanceClient()
        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_klines_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.klines("BTCUSDT", "4h", 30)
        client._request.assert_called_once_with(
            FUTURES_BASE, "/fapi/v1/klines",
            {"symbol": "BTCUSDT", "interval": "4h", "limit": 30},
        )

    @pytest.mark.asyncio
    async def test_spot_klines_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.spot_klines("BTCUSDT", "1h", 50)
        client._request.assert_called_once_with(
            SPOT_BASE, "/api/v3/klines",
            {"symbol": "BTCUSDT", "interval": "1h", "limit": 50},
        )

    @pytest.mark.asyncio
    async def test_agg_trades_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.agg_trades("ETHUSDT", 200)
        client._request.assert_called_once_with(
            FUTURES_BASE, "/fapi/v1/aggTrades",
            {"symbol": "ETHUSDT", "limit": 200},
        )

    @pytest.mark.asyncio
    async def test_depth_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value={})
        await client.depth("BTCUSDT", 500)
        client._request.assert_called_once_with(
            FUTURES_BASE, "/fapi/v1/depth",
            {"symbol": "BTCUSDT", "limit": 500},
        )

    @pytest.mark.asyncio
    async def test_premium_index_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value={})
        await client.premium_index("SOLUSDT")
        client._request.assert_called_once_with(
            FUTURES_BASE, "/fapi/v1/premiumIndex",
            {"symbol": "SOLUSDT"},
        )

    @pytest.mark.asyncio
    async def test_open_interest_hist_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.open_interest_hist("BTCUSDT", "1h", 10)
        client._request.assert_called_once_with(
            FUTURES_BASE, "/futures/data/openInterestHist",
            {"symbol": "BTCUSDT", "period": "1h", "limit": 10},
        )

    @pytest.mark.asyncio
    async def test_top_long_short_position_ratio_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.top_long_short_position_ratio("BTCUSDT")
        client._request.assert_called_once_with(
            FUTURES_BASE, "/futures/data/topLongShortPositionRatio",
            {"symbol": "BTCUSDT", "period": "4h", "limit": 30},
        )

    @pytest.mark.asyncio
    async def test_taker_buy_sell_ratio_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.taker_buy_sell_ratio("BTCUSDT")
        client._request.assert_called_once_with(
            FUTURES_BASE, "/futures/data/takerlongshortRatio",
            {"symbol": "BTCUSDT", "period": "4h", "limit": 30},
        )

    @pytest.mark.asyncio
    async def test_global_long_short_account_ratio_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.global_long_short_account_ratio("BTCUSDT", "1h", 5)
        client._request.assert_called_once_with(
            FUTURES_BASE, "/futures/data/globalLongShortAccountRatio",
            {"symbol": "BTCUSDT", "period": "1h", "limit": 5},
        )

    @pytest.mark.asyncio
    async def test_top_long_short_account_ratio_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.top_long_short_account_ratio("BTCUSDT", "1h", 5)
        client._request.assert_called_once_with(
            FUTURES_BASE, "/futures/data/topLongShortAccountRatio",
            {"symbol": "BTCUSDT", "period": "1h", "limit": 5},
        )

    @pytest.mark.asyncio
    async def test_premium_index_all_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.premium_index_all()
        client._request.assert_called_once_with(
            FUTURES_BASE, "/fapi/v1/premiumIndex", {},
        )

    @pytest.mark.asyncio
    async def test_funding_info_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.funding_info()
        client._request.assert_called_once_with(
            FUTURES_BASE, "/fapi/v1/fundingInfo", {},
        )

    @pytest.mark.asyncio
    async def test_funding_rate_history_params(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.funding_rate_history("BTCUSDT", 500)
        client._request.assert_called_once_with(
            FUTURES_BASE, "/fapi/v1/fundingRate",
            {"symbol": "BTCUSDT", "limit": 500},
        )

    @pytest.mark.asyncio
    async def test_funding_rate_history_custom_limit(self):
        client = BinanceClient()
        client._request = AsyncMock(return_value=[])
        await client.funding_rate_history("ETHUSDT", 100)
        client._request.assert_called_once_with(
            FUTURES_BASE, "/fapi/v1/fundingRate",
            {"symbol": "ETHUSDT", "limit": 100},
        )
