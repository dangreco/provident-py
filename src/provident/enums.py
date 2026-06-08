from __future__ import annotations

from enum import StrEnum


class MeterType(StrEnum):
    COLD_WATER = "Cold Water"
    ELECTRICITY = "Electricity"
    HOT_WATER = "Hot Water"


class Period(StrEnum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"
