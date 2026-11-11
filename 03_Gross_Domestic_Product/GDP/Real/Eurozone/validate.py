
"""Validate Euro area real GDP from World Bank WDI (constant 2015 USD)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class DataValidationError(ValueError):
    """A source response must not be published as validated data."""


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
    if region_code != "EMU" or indicator_code != "NY.GDP.MKTP.KD":
        raise DataValidationError("Wrong region or GDP indicator")
    if not responses or earliest_year > latest_year:
        raise DataValidationError("Empty response or invalid year range")

    observations: dict[int, GDPObservation] = {}
    missing_years: set[int] = set()
    forecast_years: set[int] = set()
    seen_years: set[int] = set()
    total_rows = 0

    for response in responses:
        if (not isinstance(response, list) or len(response) != 2
                or not isinstance(response[0], dict)
                or not isinstance(response[1], list)):
            raise DataValidationError("Expected [metadata, observations]")

        for record in response[1]:
            total_rows += 1
            if not isinstance(record, dict):
                raise DataValidationError("Observation must be a JSON object")

            area = record.get("country")
            if (not isinstance(area, dict) or area.get("id") != "XC"
                    or area.get("value") != "Euro area"):
                raise DataValidationError("Expected Euro area aggregate (XC)")
            if record.get("countryiso3code") not in (None, "", "EMU"):
                raise DataValidationError("Unexpected countryiso3code")

            indicator = record.get("indicator")
            if (not isinstance(indicator, dict)
                    or indicator.get("id") != indicator_code):
                raise DataValidationError("Wrong indicator: expected NY.GDP.MKTP.KD")

            raw_year = record.get("date")
            if (not isinstance(raw_year, str)
                    or re.fullmatch(r"[0-9]{4}", raw_year) is None):
                raise DataValidationError(f"Invalid observation year: {raw_year!r}")
            year = int(raw_year)
            if not earliest_year <= year <= latest_year:
                raise DataValidationError(f"Year outside interval: {year}")
            if year in seen_years:
                raise DataValidationError(f"Duplicate year: {year}")
            seen_years.add(year)

            status = str(record.get("obs_status") or "").strip().upper()
            if status == "F":
                forecast_years.add(year)
                continue
            raw_value = record.get("value")
            if raw_value is None:
                missing_years.add(year)
                continue
            if isinstance(raw_value, bool):
                raise DataValidationError(f"Boolean GDP in {year}")
            try:
                value = Decimal(str(raw_value))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise DataValidationError(f"Invalid GDP in {year}") from exc
            if not value.is_finite() or value <= 0:
                raise DataValidationError(f"GDP must be finite and positive: {year}")
            observations[year] = GDPObservation(year, value, status)

    if not observations:
        raise DataValidationError("No valid historical Euro area GDP observations")
    series = [observations[year] for year in sorted(observations)]
    return series, {
        "source_row_count": total_rows,
        "validated_row_count": len(series),
        "source_null_years": sorted(missing_years),
        "skipped_forecast_years": sorted(forecast_years),
        "first_year": series[0].year,
        "last_year": series[-1].year,
    }
