from __future__ import annotations

import httpx
import pytest

from provident.config import ProvidentConfig


@pytest.fixture
def base_url() -> str:
    return "https://api.test.provident.example"


@pytest.fixture
def success_transport() -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda request: httpx.Response(200, json={"status": "ok"})
    )


@pytest.fixture
def aspnet_string_transport() -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content='{"d": "{ \\"success\\": true, \\"msg\\": \\"ok\\" }"}',
            headers={"content-type": "application/json"},
        )
    )


@pytest.fixture
def aspnet_bool_transport() -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: httpx.Response(200, json={"d": True}))


@pytest.fixture
def aspnet_500_transport() -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda request: httpx.Response(
            500,
            json={
                "Message": "Invalid web service call, missing value for parameter: 'username'.",
                "StackTrace": "   at System.Web.Script.Services...",
                "ExceptionType": "System.InvalidOperationException",
            },
        )
    )


@pytest.fixture
def config(base_url: str, success_transport: httpx.MockTransport) -> ProvidentConfig:
    return ProvidentConfig(
        base_url=base_url,
        transport=success_transport,
    )
