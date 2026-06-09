from __future__ import annotations

from pydantic import BaseModel, Field


class ProvidentModel(BaseModel):
    """Base model for all Provident API response objects."""

    model_config = {"frozen": True}


class LoginResult(ProvidentModel):
    success: bool
    msg: str | None = None


class ChartDataResult(ProvidentModel):
    model_config = {"frozen": True, "populate_by_name": True}

    error: bool = False
    units: str | None = None
    data: list[float] = Field(alias="graphData", default_factory=list)
