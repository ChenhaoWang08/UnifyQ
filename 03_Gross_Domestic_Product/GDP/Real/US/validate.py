
"""Strict validation of US real GDP (World Bank, constant 2015 US$)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class DataValidationError(ValueError):
    """Unreliable source data must not enter the validated layer."""


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
    if country_iso3 != "USA" or indicator_code != "NY.GDP.MKTP.KD":
        raise DataValidationError("Expected USA / NY.GDP.MKTP.KD")
    if not responses or earliest_year > latest_year:
        raise DataValidationError("Empty responses or invalid year interval")

    observations: dict[int, GDPObservation] = {}
    missing_years: set[int] = set()
    forecast_years: set[int] = set()
    seen_years: set[int] = set()
    source_rows = 0

    for response in responses:
        if (not isinstance(response, list) or len(response) != 2
                or not isinstance(response[0], dict)
                or not isinstance(response[1], list)):
            raise DataValidationError("Expected [metadata, observations]")
        for row in response[1]:
            source_rows += 1
            if not isinstance(row, dict):
                raise DataValidationError("Invalid observation row")
            country = row.get("country")
            if (row.get("countryiso3code") != "USA"
                    or not isinstance(country, dict)
                    or country.get("id") != "US"
                    or country.get("value") != "United States"):
                raise DataValidationError("Expected United States (USA / US)")
            indicator = row.get("indicator")
            if (not isinstance(indicator, dict)
                    or indicator.get("id") != indicator_code):
                raise DataValidationError("Unexpected GDP indicator")

            raw_year = row.get("date")
            if (not isinstance(raw_year, str)
                    or re.fullmatch(r"[0-9]{4}", raw_year) is None):
                raise DataValidationError(f"Invalid year: {raw_year!r}")
            year = int(raw_year)
            if not earliest_year <= year <= latest_year:
                raise DataValidationError(f"Year outside range: {year}")
            if year in seen_years:
                raise DataValidationError(f"Duplicate GDP year: {year}")
            seen_years.add(year)

            status = str(row.get("obs_status") or "").strip().upper()
            if status == "F":
                forecast_years.add(year)
                continue
            raw_value = row.get("value")
            if raw_value is None:
                missing_years.add(year)
                continue
            if isinstance(raw_value, bool):
                raise DataValidationError(f"Boolean GDP value in {year}")
            try:
                value = Decimal(str(raw_value))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise DataValidationError(f"Invalid GDP value in {year}") from exc
            if not value.is_finite() or value <= 0:
                raise DataValidationError(f"GDP must be positive and finite: {year}")
            observations[year] = GDPObservation(year, value, status)

    if not observations:
        raise DataValidationError("No valid historical US real GDP observations")
    series = [observations[y] for y in sorted(observations)]
    return series, {
        "source_row_count": source_rows,
        "validated_row_count": len(series),
        "source_null_years": sorted(missing_years),
        "skipped_forecast_years": sorted(forecast_years),
        "first_year": series[0].year,
        "last_year": series[-1].year,
    }
