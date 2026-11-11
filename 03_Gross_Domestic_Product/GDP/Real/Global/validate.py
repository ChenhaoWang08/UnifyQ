
"""Strict validation for World real GDP (WDI, constant 2015 US$)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class DataValidationError(ValueError):
    """An API response is not safe to publish."""


@dataclass(frozen=True)
class GDPObservation:
    year: int
    value_usd: Decimal
    obs_status: str


def validate_and_normalize(
    responses: list[list[Any]],
    *,
    region_code: str,
    indicator_code: str,
    earliest_year: int,
    latest_year: int,
) -> tuple[list[GDPObservation], dict[str, Any]]:
    """Return validated observations in ascending year order, without imputation."""
    if region_code != "WLD" or indicator_code != "NY.GDP.MKTP.KD":
        raise DataValidationError("Expected WLD / NY.GDP.MKTP.KD")
    if not responses or earliest_year > latest_year:
        raise DataValidationError("Empty API response or invalid year range")

    values: dict[int, GDPObservation] = {}
    seen: set[int] = set()
    missing: set[int] = set()
    forecasts: set[int] = set()
    row_count = 0

    for page in responses:
        if (not isinstance(page, list) or len(page) != 2
                or not isinstance(page[0], dict)
                or not isinstance(page[1], list)):
            raise DataValidationError("Expected API page [metadata, rows]")

        for record in page[1]:
            row_count += 1
            if not isinstance(record, dict):
                raise DataValidationError("Observation is not a JSON object")

            area = record.get("country")
            if (not isinstance(area, dict)
                    or area.get("id") != "1W"
                    or area.get("value") != "World"):
                raise DataValidationError("Expected World aggregate (1W)")
            if record.get("countryiso3code") not in (None, "", "WLD"):
                raise DataValidationError("Unexpected countryiso3code")

            indicator = record.get("indicator")
            if (not isinstance(indicator, dict)
                    or indicator.get("id") != indicator_code):
                raise DataValidationError("Wrong GDP indicator")

            raw_year = record.get("date")
            if (not isinstance(raw_year, str)
                    or re.fullmatch(r"[0-9]{4}", raw_year) is None):
                raise DataValidationError(f"Invalid observation year: {raw_year!r}")
            year = int(raw_year)
            if not earliest_year <= year <= latest_year:
                raise DataValidationError(f"Year {year} outside requested range")
            if year in seen:
                raise DataValidationError(f"Duplicate observation year: {year}")
            seen.add(year)

            status = str(record.get("obs_status") or "").strip().upper()
            if status == "F":
                forecasts.add(year)
                continue

            raw_value = record.get("value")
            if raw_value is None:
                missing.add(year)
                continue
            if isinstance(raw_value, bool):
                raise DataValidationError(f"Boolean GDP value in {year}")
            try:
                number = Decimal(str(raw_value))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise DataValidationError(f"Invalid GDP value in {year}") from exc
            if not number.is_finite() or number <= 0:
                raise DataValidationError(f"Nonpositive or nonfinite GDP in {year}")
            values[year] = GDPObservation(year, number, status)

    if not values:
        raise DataValidationError("No valid non-null historical World GDP data")

    result = [values[year] for year in sorted(values)]
    return result, {
        "source_row_count": row_count,
        "validated_row_count": len(result),
        "source_null_years": sorted(missing),
        "skipped_forecast_years": sorted(forecasts),
        "first_year": result[0].year,
        "last_year": result[-1].year,
    }
