
"""Strict validation for China's real GDP, constant 2015 US$ (WDI)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class DataValidationError(ValueError):
    """Data must not enter the validated layer."""


@dataclass(frozen=True)
class GDPObservation:
    year: int
    value_usd: Decimal
    obs_status: str


def validate_and_normalize(
    responses: list[list[Any]],
    *,
    country_iso3: str,
    indicator_code: str,
    earliest_year: int,
    latest_year: int,
) -> tuple[list[GDPObservation], dict[str, Any]]:
    if country_iso3 != "CHN" or indicator_code != "NY.GDP.MKTP.KD":
        raise DataValidationError("Unexpected data series")
    if not responses or earliest_year > latest_year:
        raise DataValidationError("No responses or invalid year range")

    values: dict[int, GDPObservation] = {}
    null_years: set[int] = set()
    forecast_years: set[int] = set()
    source_rows = 0

    for response in responses:
        if (not isinstance(response, list) or len(response) != 2
                or not isinstance(response[0], dict)
                or not isinstance(response[1], list)):
            raise DataValidationError("Expected [metadata, rows]")

        for row in response[1]:
            source_rows += 1
            if not isinstance(row, dict):
                raise DataValidationError("Invalid observation row")
            if row.get("countryiso3code") != "CHN":
                raise DataValidationError("Expected CHN country code")
            country = row.get("country")
            if not isinstance(country, dict) or country.get("id") != "CN":
                raise DataValidationError("Expected World Bank country code CN")
            indicator = row.get("indicator")
            if (not isinstance(indicator, dict)
                    or indicator.get("id") != indicator_code):
                raise DataValidationError("Wrong GDP indicator")

            raw_year = row.get("date")
            if (not isinstance(raw_year, str)
                    or re.fullmatch(r"[0-9]{4}", raw_year) is None):
                raise DataValidationError(f"Invalid year: {raw_year!r}")
            year = int(raw_year)
            if not earliest_year <= year <= latest_year:
                raise DataValidationError(f"Year outside interval: {year}")

            status = str(row.get("obs_status") or "").strip().upper()
            if year in values or year in null_years or year in forecast_years:
                raise DataValidationError(f"Duplicate year: {year}")
            if status == "F":
                forecast_years.add(year)
                continue
            raw_value = row.get("value")
            if raw_value is None:
                null_years.add(year)
                continue
            if isinstance(raw_value, bool):
                raise DataValidationError(f"Boolean GDP value in {year}")
            try:
                value = Decimal(str(raw_value))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise DataValidationError(f"Invalid GDP value in {year}") from exc
            if not value.is_finite() or value <= 0:
                raise DataValidationError(f"GDP must be finite and positive: {year}")
            values[year] = GDPObservation(year, value, status)

    if not values:
        raise DataValidationError("No valid historical GDP observations")
    observations = [values[y] for y in sorted(values)]
    return observations, {
        "source_row_count": source_rows,
        "validated_row_count": len(observations),
        "source_null_years": sorted(null_years),
        "skipped_forecast_years": sorted(forecast_years),
        "first_year": observations[0].year,
        "last_year": observations[-1].year,
    }
