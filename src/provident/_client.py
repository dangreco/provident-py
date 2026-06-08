from __future__ import annotations

from datetime import date
from typing import Any, TypeVar, overload

import httpx

from provident._response import handle_response, unwrap_response
from provident.config import ProvidentConfig
from provident.enums import MeterType, Period
from provident.errors import ProvidentConnectionError
from provident.models import ChartDataResult, LoginResult, ProvidentModel
from provident.types import Headers, JsonDict, QueryParams

T = TypeVar("T", bound=ProvidentModel)


class ProvidentClient:
    """Synchronous client for the Provident API."""

    _DEFAULT_HEADERS: Headers = {"Content-Type": "application/json"}

    def __init__(self, config: ProvidentConfig) -> None:
        self._config = config
        transport = (
            config.transport
            if isinstance(config.transport, httpx.BaseTransport)
            else None
        )
        merged_headers = {**self._DEFAULT_HEADERS, **config.headers}
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers=merged_headers,
            transport=transport,
            follow_redirects=config.follow_redirects,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: QueryParams | None = None,
        headers: Headers | None = None,
        content: str | bytes | None = None,
        json: JsonDict | None = None,
    ) -> httpx.Response:
        try:
            response = self._client.request(
                method,
                path,
                params=params,
                headers=headers,
                content=content,
                json=json,
            )
        except httpx.HTTPError as exc:
            raise ProvidentConnectionError(str(exc)) from exc

        handle_response(response)
        return response

    @overload
    def _call(
        self,
        method: str,
        path: str,
        *,
        response_type: type[T],
        params: QueryParams | None = None,
        headers: Headers | None = None,
        content: str | bytes | None = None,
        json: JsonDict | None = None,
    ) -> T: ...

    @overload
    def _call(
        self,
        method: str,
        path: str,
        *,
        response_type: None = None,
        params: QueryParams | None = None,
        headers: Headers | None = None,
        content: str | bytes | None = None,
        json: JsonDict | None = None,
    ) -> Any: ...

    def _call(
        self,
        method: str,
        path: str,
        *,
        response_type: type[T] | None = None,
        params: QueryParams | None = None,
        headers: Headers | None = None,
        content: str | bytes | None = None,
        json: JsonDict | None = None,
    ) -> T | Any:
        response = self._request(
            method,
            path,
            params=params,
            headers=headers,
            content=content,
            json=json,
        )
        data = unwrap_response(response)
        if response_type is not None:
            return response_type.model_validate(data)
        return data

    def login(
        self, username: str, password: str, *, remember_me: bool = False
    ) -> LoginResult:
        return self._call(
            "POST",
            "/login/LoginService.aspx/ProcessLogin",
            response_type=LoginResult,
            json={
                "username": username,
                "password": password,
                "rememberMe": remember_me,
            },
        )

    def check_login(self) -> bool:
        result = self._call("GET", "/login/LoginService.aspx/CheckLogin")
        return bool(result)

    def get_chart_data(
        self, meter_type: MeterType, period: Period, start: date
    ) -> ChartDataResult:
        return self._call(
            "POST",
            "/secure/Dashboard/Default.aspx/GetChartData",
            response_type=ChartDataResult,
            json={
                "utility": str(meter_type),
                "period": str(period),
                "start": start.isoformat(),
            },
        )

    @property
    def is_authenticated(self) -> bool:
        return ".ASPXAUTH" in self._client.cookies

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ProvidentClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
