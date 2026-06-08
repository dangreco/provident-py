# provident-py

[![CI](https://github.com/dangreco/provident-py/actions/workflows/ci.yml/badge.svg)](https://github.com/dangreco/provident-py/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/provident)](https://pypi.org/project/provident/)
[![Python](https://img.shields.io/pypi/pyversions/provident)](https://pypi.org/project/provident/)
[![License](https://img.shields.io/pypi/l/provident)](https://github.com/dangreco/provident-py/blob/main/LICENSE)

Python client library for the [Provident](https://provident.meterconnex.com) (MeterConnex) utility monitoring API. Supports both synchronous and asynchronous usage with full type safety.

## Installation

```bash
pip install provident
```

## Quick Start

```python
from datetime import date

from provident import MeterType, Period, ProvidentClient, ProvidentConfig

config = ProvidentConfig(base_url="https://provident.meterconnex.com")

with ProvidentClient(config) as client:
    # Authenticate
    result = client.login("account-id", "password")
    if not result.success:
        print(result.msg)
        return

    # Read meter data
    electricity = client.get_chart_data(
        MeterType.ELECTRICITY, Period.MONTH, date(2026, 1, 1)
    )
    print(f"Units: {electricity.units}")  # kWh
    print(f"Data: {electricity.data}")     # [1.79, 2.76, ...]

    # Read all meter types
    for meter in [MeterType.COLD_WATER, MeterType.HOT_WATER, MeterType.ELECTRICITY]:
        data = client.get_chart_data(meter, Period.YEAR, date(2026, 1, 1))
        print(f"{meter.value}: {len(data.data)} data points in {data.units}")
```

## Async Usage

```python
from datetime import date

from provident import AsyncProvidentClient, MeterType, Period, ProvidentConfig

config = ProvidentConfig(base_url="https://provident.meterconnex.com")

async with AsyncProvidentClient(config) as client:
    await client.login("account-id", "password")

    result = await client.get_chart_data(
        MeterType.ELECTRICITY, Period.DAY, date(2026, 6, 1)
    )
    print(result.data)
```

## API Reference

### Client Classes

| Class | Description |
|---|---|
| `ProvidentClient(config)` | Synchronous client. Use as a context manager. |
| `AsyncProvidentClient(config)` | Asynchronous client. Use as an async context manager. |

### Authentication

| Method | Returns | Description |
|---|---|---|
| `login(username, password, *, remember_me=False)` | `LoginResult` | Authenticate with the API. Session is persisted via cookies. |
| `check_login()` | `bool` | Check if the current session is still authenticated. |
| `is_authenticated` | `bool` | Property — checks if the auth cookie is present. |

### Meter Data

| Method | Returns | Description |
|---|---|---|
| `get_chart_data(meter_type, period, start)` | `ChartDataResult` | Fetch usage data for a meter type and time period. |

### Enums

#### `MeterType`

| Value | API String |
|---|---|
| `COLD_WATER` | `"Cold Water"` |
| `ELECTRICITY` | `"Electricity"` |
| `HOT_WATER` | `"Hot Water"` |

#### `Period`

| Value | Data Points |
|---|---|
| `DAY` | 24 (hourly) |
| `MONTH` | 28–31 (daily) |
| `YEAR` | 12 (monthly) |

### Models

| Model | Fields |
|---|---|
| `LoginResult` | `success: bool`, `msg: str \| None` |
| `ChartDataResult` | `error: bool`, `units: str \| None`, `data: list[float]` |

### Errors

All exceptions inherit from `ProvidentError`.

| Exception | HTTP Status | Description |
|---|---|---|
| `ProvidentAPIError` | 4xx | Base class for API errors. Includes `status_code`, `message`, `headers`, `body`. |
| `ProvidentAuthenticationError` | 401 | Invalid or expired credentials. |
| `ProvidentNotFoundError` | 404 | Requested resource not found. |
| `ProvidentRateLimitError` | 429 | Rate limit exceeded. Includes `retry_after`. |
| `ProvidentServerError` | 5xx | Server error. Includes `stack_trace`, `exception_type` from ASP.NET. |
| `ProvidentConnectionError` | N/A | Network-level failure (timeout, DNS, etc.). |

## Requirements

- Python 3.12+
- [httpx](https://www.python-httpx.org/)
- [pydantic](https://docs.pydantic.dev/) v2

## Support

If this project saved you some time, consider [buying me a beer 🍺](https://buymeacoffee.com/dangreco)!

## License

[MIT](https://github.com/dangreco/provident-py/blob/main/LICENSE)
