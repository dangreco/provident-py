from __future__ import annotations

from datetime import date

import httpx
import pytest

from provident import AsyncProvidentClient, MeterType, Period, ProvidentConfig
from provident.errors import (
    ProvidentAuthenticationError,
    ProvidentConnectionError,
    ProvidentNotFoundError,
    ProvidentRateLimitError,
    ProvidentServerError,
)
from provident.models import LoginResult, ProvidentModel
from tests._helpers import (
    _make_chart_data_transport,
    _make_empty_chart_data_transport,
    _make_login_transport,
)


class _SampleResult(ProvidentModel):
    success: bool
    msg: str | None = None


class TestAsyncClientInit:
    @pytest.mark.asyncio
    async def test_creates_with_config(self, config: ProvidentConfig) -> None:
        client = AsyncProvidentClient(config)
        assert client._config is config
        await client.close()

    @pytest.mark.asyncio
    async def test_close(self, config: ProvidentConfig) -> None:
        client = AsyncProvidentClient(config)
        await client.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, config: ProvidentConfig) -> None:
        async with AsyncProvidentClient(config) as client:
            assert client._config is config


class TestAsyncClientRequest:
    @pytest.mark.asyncio
    async def test_successful_request(
        self, base_url: str, success_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=success_transport)
        async with AsyncProvidentClient(config) as client:
            response = await client._request("GET", "/test")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_request_with_params(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"path": str(request.url)})
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            response = await client._request("GET", "/test", params={"key": "value"})
            assert "key=value" in response.json()["path"]


class TestAsyncClientCall:
    @pytest.mark.asyncio
    async def test_call_returns_unwrapped_string_d(
        self, base_url: str, aspnet_string_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=aspnet_string_transport)
        async with AsyncProvidentClient(config) as client:
            result = await client._call("POST", "/LoginService.aspx/ProcessLogin")
            assert result == {"success": True, "msg": "ok"}

    @pytest.mark.asyncio
    async def test_call_returns_unwrapped_bool_d(
        self, base_url: str, aspnet_bool_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=aspnet_bool_transport)
        async with AsyncProvidentClient(config) as client:
            result = await client._call("GET", "/LoginService.aspx/CheckLogin")
            assert result is True

    @pytest.mark.asyncio
    async def test_call_with_response_type(
        self, base_url: str, aspnet_string_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=aspnet_string_transport)
        async with AsyncProvidentClient(config) as client:
            result = await client._call(
                "POST",
                "/LoginService.aspx/ProcessLogin",
                response_type=_SampleResult,
            )
            assert isinstance(result, _SampleResult)
            assert result.success is True
            assert result.msg == "ok"

    @pytest.mark.asyncio
    async def test_call_propagates_errors(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(401, text="Unauthorized")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            with pytest.raises(ProvidentAuthenticationError):
                await client._call("GET", "/test")


class TestAsyncClientErrors:
    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(401, text="Unauthorized")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            with pytest.raises(ProvidentAuthenticationError) as exc_info:
                await client._request("GET", "/test")
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_404_raises_not_found_error(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(404, text="Not Found")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            with pytest.raises(ProvidentNotFoundError) as exc_info:
                await client._request("GET", "/test")
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                429,
                text="Too Many Requests",
                headers={"retry-after": "60"},
            )
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            with pytest.raises(ProvidentRateLimitError) as exc_info:
                await client._request("GET", "/test")
            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 60.0

    @pytest.mark.asyncio
    async def test_500_parses_aspnet_error(
        self, base_url: str, aspnet_500_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=aspnet_500_transport)
        async with AsyncProvidentClient(config) as client:
            with pytest.raises(ProvidentServerError) as exc_info:
                await client._request("GET", "/test")
            err = exc_info.value
            assert err.status_code == 500
            assert err.exception_type == "System.InvalidOperationException"

    @pytest.mark.asyncio
    async def test_connection_error(self, base_url: str) -> None:
        def raise_connect_error(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(raise_connect_error)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            with pytest.raises(ProvidentConnectionError):
                await client._request("GET", "/test")


class TestAsyncClientLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, base_url: str) -> None:
        transport = _make_login_transport(success=True)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            result = await client.login("user", "pass")
            assert isinstance(result, LoginResult)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_login_failure(self, base_url: str) -> None:
        transport = _make_login_transport(success=False)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            result = await client.login("user", "wrong")
            assert result.success is False
            assert result.msg == "Invalid Username or Password"

    @pytest.mark.asyncio
    async def test_login_sets_auth_cookie(self, base_url: str) -> None:
        transport = _make_login_transport(success=True)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            assert client.is_authenticated is False
            await client.login("user", "pass")
            assert client.is_authenticated is True

    @pytest.mark.asyncio
    async def test_check_login(self, base_url: str) -> None:
        transport = _make_login_transport(success=True)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            await client.login("user", "pass")
            assert await client.check_login() is True


class TestAsyncClientGetChartData:
    @pytest.mark.asyncio
    async def test_returns_chart_data(self, base_url: str) -> None:
        transport = _make_chart_data_transport(units="m3", data=[1.5, 2.0])
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            result = await client.get_chart_data(
                MeterType.HOT_WATER, Period.DAY, date(2026, 1, 1)
            )
            assert result.error is False
            assert result.units == "m3"
            assert result.data == [1.5, 2.0]

    @pytest.mark.asyncio
    async def test_error_response(self, base_url: str) -> None:
        transport = _make_chart_data_transport(error=True)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            result = await client.get_chart_data(
                MeterType.ELECTRICITY, Period.MONTH, date(2026, 6, 1)
            )
            assert result.error is True

    @pytest.mark.asyncio
    async def test_empty_api_response(self, base_url: str) -> None:
        transport = _make_empty_chart_data_transport()
        config = ProvidentConfig(base_url=base_url, transport=transport)
        async with AsyncProvidentClient(config) as client:
            result = await client.get_chart_data(
                MeterType.COLD_WATER, Period.DAY, date(2026, 1, 1)
            )
            assert result.error is False
            assert result.data == []
            assert result.units is None
