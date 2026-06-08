from __future__ import annotations

from datetime import date

import httpx
import pytest

from provident import MeterType, Period, ProvidentClient, ProvidentConfig
from provident.config import ProvidentConfig as ConfigDirect
from provident.enums import MeterType as MeterTypeDirect, Period as PeriodDirect
from provident.errors import (
    ProvidentAPIError,
    ProvidentAuthenticationError,
    ProvidentConnectionError,
    ProvidentError,
    ProvidentNotFoundError,
    ProvidentRateLimitError,
    ProvidentServerError,
)
from provident.models import ChartDataResult, LoginResult, ProvidentModel
from tests._helpers import _make_chart_data_transport, _make_login_transport


class _SampleResult(ProvidentModel):
    success: bool
    msg: str | None = None


class TestClientInit:
    def test_creates_with_config(self, config: ProvidentConfig) -> None:
        client = ProvidentClient(config)
        assert client._config is config
        client.close()

    def test_config_importable_from_top_level(self) -> None:
        assert ProvidentConfig is ConfigDirect

    def test_close(self, config: ProvidentConfig) -> None:
        client = ProvidentClient(config)
        client.close()

    def test_context_manager(self, config: ProvidentConfig) -> None:
        with ProvidentClient(config) as client:
            assert client._config is config


class TestClientRequest:
    def test_successful_request(
        self, base_url: str, success_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=success_transport)
        with ProvidentClient(config) as client:
            response = client._request("GET", "/test")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_request_with_params(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"path": str(request.url)})
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            response = client._request("GET", "/test", params={"key": "value"})
            assert "key=value" in response.json()["path"]


class TestClientCall:
    def test_call_returns_unwrapped_string_d(
        self, base_url: str, aspnet_string_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=aspnet_string_transport)
        with ProvidentClient(config) as client:
            result = client._call("POST", "/LoginService.aspx/ProcessLogin")
            assert result == {"success": True, "msg": "ok"}

    def test_call_returns_unwrapped_bool_d(
        self, base_url: str, aspnet_bool_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=aspnet_bool_transport)
        with ProvidentClient(config) as client:
            result = client._call("GET", "/LoginService.aspx/CheckLogin")
            assert result is True

    def test_call_with_response_type(
        self, base_url: str, aspnet_string_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=aspnet_string_transport)
        with ProvidentClient(config) as client:
            result = client._call(
                "POST",
                "/LoginService.aspx/ProcessLogin",
                response_type=_SampleResult,
            )
            assert isinstance(result, _SampleResult)
            assert result.success is True
            assert result.msg == "ok"

    def test_call_without_d_field(
        self, base_url: str, success_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=success_transport)
        with ProvidentClient(config) as client:
            result = client._call("GET", "/test")
            assert result == {"status": "ok"}

    def test_call_propagates_errors(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(401, text="Unauthorized")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentAuthenticationError):
                client._call("GET", "/test")

    def test_call_with_json_body(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content='{"d": "{ \\"success\\": false, \\"msg\\": \\"Invalid\\" }"}',
                headers={"content-type": "application/json"},
            )
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            result = client._call(
                "POST",
                "/LoginService.aspx/ProcessLogin",
                json={"username": "user", "password": "pass", "rememberMe": False},
            )
            assert result == {"success": False, "msg": "Invalid"}


class TestClientErrors:
    def test_401_raises_authentication_error(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(401, text="Unauthorized")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentAuthenticationError) as exc_info:
                client._request("GET", "/test")
            assert exc_info.value.status_code == 401

    def test_404_raises_not_found_error(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(404, text="Not Found")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentNotFoundError) as exc_info:
                client._request("GET", "/test")
            assert exc_info.value.status_code == 404

    def test_429_raises_rate_limit_error(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                429,
                text="Too Many Requests",
                headers={"retry-after": "60"},
            )
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentRateLimitError) as exc_info:
                client._request("GET", "/test")
            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 60.0

    def test_429_without_retry_after_header(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(429, text="Too Many Requests")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentRateLimitError) as exc_info:
                client._request("GET", "/test")
            assert exc_info.value.retry_after is None

    def test_400_raises_api_error(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(400, text="Bad Request")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentAPIError) as exc_info:
                client._request("GET", "/test")
            assert exc_info.value.status_code == 400

    def test_500_parses_aspnet_error(
        self, base_url: str, aspnet_500_transport: httpx.MockTransport
    ) -> None:
        config = ProvidentConfig(base_url=base_url, transport=aspnet_500_transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentServerError) as exc_info:
                client._request("GET", "/test")
            err = exc_info.value
            assert err.status_code == 500
            assert (
                err.message
                == "Invalid web service call, missing value for parameter: 'username'."
            )
            assert err.stack_trace == "   at System.Web.Script.Services..."
            assert err.exception_type == "System.InvalidOperationException"

    def test_500_non_json_body(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(500, text="Internal Server Error")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentServerError) as exc_info:
                client._request("GET", "/test")
            assert exc_info.value.stack_trace is None
            assert exc_info.value.exception_type is None

    def test_error_includes_headers_and_body(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                400,
                text="Bad Request",
                headers={"x-request-id": "abc123"},
            )
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentAPIError) as exc_info:
                client._request("GET", "/test")
            assert exc_info.value.body == "Bad Request"
            assert exc_info.value.headers is not None
            assert exc_info.value.headers.get("x-request-id") == "abc123"

    def test_connection_error(self, base_url: str) -> None:
        def raise_connect_error(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(raise_connect_error)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentConnectionError):
                client._request("GET", "/test")

    def test_error_str_format(self, base_url: str) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(404, text="Not Found")
        )
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            with pytest.raises(ProvidentAPIError) as exc_info:
                client._request("GET", "/test")
            assert str(exc_info.value) == "HTTP 404: Not Found"


class TestErrorHierarchy:
    def test_api_error_is_provident_error(self) -> None:
        assert issubclass(ProvidentAPIError, ProvidentError)

    def test_authentication_error_is_api_error(self) -> None:
        assert issubclass(ProvidentAuthenticationError, ProvidentAPIError)

    def test_not_found_error_is_api_error(self) -> None:
        assert issubclass(ProvidentNotFoundError, ProvidentAPIError)

    def test_rate_limit_error_is_api_error(self) -> None:
        assert issubclass(ProvidentRateLimitError, ProvidentAPIError)

    def test_server_error_is_api_error(self) -> None:
        assert issubclass(ProvidentServerError, ProvidentAPIError)

    def test_connection_error_is_provident_error(self) -> None:
        assert issubclass(ProvidentConnectionError, ProvidentError)

    def test_connection_error_is_not_api_error(self) -> None:
        assert not issubclass(ProvidentConnectionError, ProvidentAPIError)


class TestClientLogin:
    def test_login_success(self, base_url: str) -> None:
        transport = _make_login_transport(success=True)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            result = client.login("user", "pass")
            assert isinstance(result, LoginResult)
            assert result.success is True
            assert result.msg is None

    def test_login_failure(self, base_url: str) -> None:
        transport = _make_login_transport(success=False)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            result = client.login("user", "wrong")
            assert result.success is False
            assert result.msg == "Invalid Username or Password"

    def test_login_sets_auth_cookie(self, base_url: str) -> None:
        transport = _make_login_transport(success=True)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            assert client.is_authenticated is False
            client.login("user", "pass")
            assert client.is_authenticated is True

    def test_failed_login_does_not_set_auth_cookie(self, base_url: str) -> None:
        transport = _make_login_transport(success=False)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            assert client.is_authenticated is False
            client.login("user", "wrong")
            assert client.is_authenticated is False

    def test_check_login_true_after_login(self, base_url: str) -> None:
        transport = _make_login_transport(success=True)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            client.login("user", "pass")
            assert client.check_login() is True

    def test_check_login_false_before_login(self, base_url: str) -> None:
        transport = _make_login_transport(success=False)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            assert client.check_login() is False

    def test_login_with_remember_me(self, base_url: str) -> None:
        transport = _make_login_transport(success=True)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            result = client.login("user", "pass", remember_me=True)
            assert result.success is True

    def test_is_authenticated_reflects_cookie_presence(self, base_url: str) -> None:
        transport = _make_login_transport(success=True, set_auth_cookie=False)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            result = client.login("user", "pass")
            assert result.success is True
            assert client.is_authenticated is False


class TestClientGetChartData:
    def test_returns_chart_data(self, base_url: str) -> None:
        transport = _make_chart_data_transport(units="m3", data=[1.5, 2.0, 0.5])
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            result = client.get_chart_data(
                MeterType.HOT_WATER, Period.DAY, date(2026, 1, 1)
            )
            assert isinstance(result, ChartDataResult)
            assert result.error is False
            assert result.units == "m3"
            assert result.data == [1.5, 2.0, 0.5]

    def test_electricity_units(self, base_url: str) -> None:
        transport = _make_chart_data_transport(units="kWh", data=[10.0, 20.0])
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            result = client.get_chart_data(
                MeterType.ELECTRICITY, Period.MONTH, date(2026, 6, 1)
            )
            assert result.units == "kWh"

    def test_error_response(self, base_url: str) -> None:
        transport = _make_chart_data_transport(error=True)
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            result = client.get_chart_data(
                MeterType.COLD_WATER, Period.YEAR, date(2026, 1, 1)
            )
            assert result.error is True

    def test_empty_data(self, base_url: str) -> None:
        transport = _make_chart_data_transport(data=[])
        config = ProvidentConfig(base_url=base_url, transport=transport)
        with ProvidentClient(config) as client:
            result = client.get_chart_data(
                MeterType.COLD_WATER, Period.DAY, date(2026, 1, 1)
            )
            assert result.data == []


class TestEnums:
    def test_meter_type_values(self) -> None:
        assert MeterType.COLD_WATER == "Cold Water"
        assert MeterType.ELECTRICITY == "Electricity"
        assert MeterType.HOT_WATER == "Hot Water"

    def test_period_values(self) -> None:
        assert Period.YEAR == "year"
        assert Period.MONTH == "month"
        assert Period.DAY == "day"

    def test_meter_type_importable_from_top_level(self) -> None:
        assert MeterType is MeterTypeDirect

    def test_period_importable_from_top_level(self) -> None:
        assert Period is PeriodDirect

    def test_meter_type_str(self) -> None:
        assert str(MeterType.HOT_WATER) == "Hot Water"

    def test_period_str(self) -> None:
        assert str(Period.DAY) == "day"


class TestChartDataResult:
    def test_parses_from_graph_data_alias(self) -> None:
        result = ChartDataResult.model_validate(
            {"error": False, "units": "m3", "graphData": [1.0, 2.0]}
        )
        assert result.data == [1.0, 2.0]

    def test_defaults_optional_fields(self) -> None:
        result = ChartDataResult.model_validate({"error": True})
        assert result.units is None
        assert result.data == []


class TestConfig:
    def test_frozen(self, base_url: str) -> None:
        config = ProvidentConfig(base_url=base_url)
        with pytest.raises(AttributeError):
            config.base_url = "https://other.example"  # type: ignore[misc]  # ty: ignore[invalid-assignment]

    def test_default_timeout(self, base_url: str) -> None:
        config = ProvidentConfig(base_url=base_url)
        assert config.timeout.connect == 30.0

    def test_default_headers(self, base_url: str) -> None:
        config = ProvidentConfig(base_url=base_url)
        assert config.headers == {}

    def test_custom_headers(self, base_url: str) -> None:
        config = ProvidentConfig(
            base_url=base_url, headers={"Authorization": "Bearer token"}
        )
        assert config.headers == {"Authorization": "Bearer token"}
