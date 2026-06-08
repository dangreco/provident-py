from __future__ import annotations

import json

import httpx
import pytest

from provident._response import handle_response, unwrap_response
from provident.errors import ProvidentServerError


def _make_response(
    status_code: int = 200,
    json_data: object | None = None,
    text: str | None = None,
) -> httpx.Response:
    if json_data is not None:
        return httpx.Response(status_code, json=json_data)
    return httpx.Response(status_code, text=text or "")


class TestUnwrapResponse:
    def test_double_serialized_json_string(self) -> None:
        inner = json.dumps({"success": True, "msg": "ok"})
        response = _make_response(json_data={"d": inner})
        result = unwrap_response(response)
        assert result == {"success": True, "msg": "ok"}

    def test_primitive_bool(self) -> None:
        response = _make_response(json_data={"d": True})
        result = unwrap_response(response)
        assert result is True

    def test_primitive_false(self) -> None:
        response = _make_response(json_data={"d": False})
        result = unwrap_response(response)
        assert result is False

    def test_primitive_number(self) -> None:
        response = _make_response(json_data={"d": 42})
        result = unwrap_response(response)
        assert result == 42

    def test_no_d_field(self) -> None:
        response = _make_response(json_data={"status": "ok"})
        result = unwrap_response(response)
        assert result == {"status": "ok"}

    def test_d_is_none(self) -> None:
        response = _make_response(json_data={"d": None})
        result = unwrap_response(response)
        assert result is None

    def test_d_is_nested_object(self) -> None:
        response = _make_response(json_data={"d": {"key": "value"}})
        result = unwrap_response(response)
        assert result == {"key": "value"}

    def test_d_is_list(self) -> None:
        response = _make_response(json_data={"d": [1, 2, 3]})
        result = unwrap_response(response)
        assert result == [1, 2, 3]

    def test_non_dict_response(self) -> None:
        response = _make_response(json_data=[1, 2, 3])
        result = unwrap_response(response)
        assert result == [1, 2, 3]


class TestHandleResponseAspNetErrors:
    def test_500_parses_aspnet_error_json(self) -> None:
        body = json.dumps(
            {
                "Message": "Invalid web service call, missing value for parameter: 'username'.",
                "StackTrace": "   at System.Web.Script.Services...",
                "ExceptionType": "System.InvalidOperationException",
            }
        )
        response = _make_response(status_code=500, text=body)
        with pytest.raises(ProvidentServerError) as exc_info:
            handle_response(response)
        err = exc_info.value
        assert err.status_code == 500
        assert (
            err.message
            == "Invalid web service call, missing value for parameter: 'username'."
        )
        assert err.stack_trace == "   at System.Web.Script.Services..."
        assert err.exception_type == "System.InvalidOperationException"

    def test_500_non_json_falls_back_to_body(self) -> None:
        response = _make_response(status_code=500, text="Internal Server Error")
        with pytest.raises(ProvidentServerError) as exc_info:
            handle_response(response)
        err = exc_info.value
        assert err.message == "Internal Server Error"
        assert err.stack_trace is None
        assert err.exception_type is None

    def test_500_incomplete_json_uses_defaults(self) -> None:
        body = json.dumps({"Message": "Something went wrong"})
        response = _make_response(status_code=500, text=body)
        with pytest.raises(ProvidentServerError) as exc_info:
            handle_response(response)
        err = exc_info.value
        assert err.message == "Something went wrong"
        assert err.stack_trace is None
        assert err.exception_type is None

    def test_success_response_does_not_raise(self) -> None:
        response = _make_response(status_code=200, json_data={"d": True})
        handle_response(response)
