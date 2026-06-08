from __future__ import annotations

import json
from typing import Any

import httpx

from provident.errors import (
    ProvidentAPIError,
    ProvidentAuthenticationError,
    ProvidentNotFoundError,
    ProvidentRateLimitError,
    ProvidentServerError,
)


def unwrap_response(response: httpx.Response) -> Any:
    data = response.json()
    if not isinstance(data, dict) or "d" not in data:
        return data
    inner = data["d"]
    if isinstance(inner, str):
        return json.loads(inner)
    return inner


def handle_response(response: httpx.Response) -> None:
    """Raise an appropriate exception if the response indicates an error."""
    if response.is_success:
        return

    status_code = response.status_code
    body = response.text

    if 500 <= status_code < 600:
        message = body
        stack_trace: str | None = None
        exception_type: str | None = None
        try:
            error_data = json.loads(body)
            message = error_data.get("Message", body)
            stack_trace = error_data.get("StackTrace")
            exception_type = error_data.get("ExceptionType")
        except (json.JSONDecodeError, ValueError):
            pass
        raise ProvidentServerError(
            status_code,
            message,
            stack_trace=stack_trace,
            exception_type=exception_type,
            headers=response.headers,
            body=body,
        )

    if status_code == 401:
        raise ProvidentAuthenticationError(
            status_code, body, headers=response.headers, body=body
        )
    elif status_code == 404:
        raise ProvidentNotFoundError(
            status_code, body, headers=response.headers, body=body
        )
    elif status_code == 429:
        retry_after = response.headers.get("retry-after")
        raise ProvidentRateLimitError(
            status_code,
            body,
            retry_after=float(retry_after) if retry_after else None,
            headers=response.headers,
            body=body,
        )
    elif 400 <= status_code < 500:
        raise ProvidentAPIError(status_code, body, headers=response.headers, body=body)
