from __future__ import annotations

import json

import httpx

_CHECK_LOGIN_TRUE_BODY = '{"d": true}'
_CHECK_LOGIN_FALSE_BODY = '{"d": false}'
_LOGIN_SUCCESS_BODY = '{"d": "{ \\"success\\": true }"}'
_LOGIN_FAIL_BODY = (
    '{"d": "{ \\"success\\": false, \\"msg\\": \\"Invalid Username or Password\\" }"}'
)


def _make_login_transport(
    *,
    success: bool,
    set_auth_cookie: bool = True,
) -> httpx.MockTransport:
    if success:
        body = _LOGIN_SUCCESS_BODY
        cookie = (
            ".ASPXAUTH=test_auth_token; path=/; HttpOnly" if set_auth_cookie else ""
        )
    else:
        body = _LOGIN_FAIL_BODY
        cookie = ""

    def handler(request: httpx.Request) -> httpx.Response:
        if "CheckLogin" in str(request.url):
            check_body = _CHECK_LOGIN_TRUE_BODY if success else _CHECK_LOGIN_FALSE_BODY
            return httpx.Response(
                200,
                content=check_body,
                headers={"content-type": "application/json"},
            )
        headers: dict[str, str] = {"content-type": "application/json"}
        if cookie:
            headers["set-cookie"] = cookie
        return httpx.Response(200, content=body, headers=headers)

    return httpx.MockTransport(handler)


def _make_chart_data_transport(
    *,
    error: bool = False,
    units: str = "m3",
    data: list[float] | None = None,
) -> httpx.MockTransport:
    if data is None:
        data = [1.5, 2.0, 0.5]
    inner = json.dumps({"error": error, "units": units, "graphData": data})
    body = json.dumps({"d": inner})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=body,
            headers={"content-type": "application/json"},
        )

    return httpx.MockTransport(handler)
