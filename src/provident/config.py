from __future__ import annotations

from dataclasses import dataclass, field

import httpx


@dataclass(frozen=True)
class ProvidentConfig:
    base_url: str
    timeout: httpx.Timeout = field(default_factory=lambda: httpx.Timeout(30.0))
    headers: dict[str, str] = field(default_factory=dict)
    follow_redirects: bool = True
    transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None
