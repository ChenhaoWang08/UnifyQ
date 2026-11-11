
"""Validate annual US nominal GDP from World Bank WDI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class DataValidationError(ValueError):
    """Source data failed validation."""


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

    if not responses:
        raise DataValidationError("No API responses received")

    observations: dict[int, GDPObservation] = {}
    missing_years: set[int] = set()
    skipped_forecast_years: set[int] = set()
    total_rows = 0

    for response in responses:

        if not isinstance(response, list) or len(response) != 2:
            raise DataValidationError(
                "Expected [metadata, observations]"
            )

        metadata, rows = response

        if not isinstance(metadata, dict) or not isinstance(rows, list):
            raise DataValidationError(
                "Invalid API response structure"
            )

        for record in rows:
            total_rows += 1

            if not isinstance(record, dict):
                raise DataValidationError("Invalid observation")

            if record.get("countryiso3code") != country_iso3:
                raise DataValidationError("Unexpected country")

            indicator = record.get("indicator")

            if (
                not isinstance(indicator, dict)
                or indicator.get("id") != indicator_code
            ):
                raise DataValidationError("Unexpected indicator")

            raw_year = record.get("date")

            if (
                not isinstance(raw_year, str)
                or re.fullmatch(r"[0-9]{4}", raw_year) is None
            ):
                raise DataValidationError(
                    f"Invalid observation year: {raw_year!r}"
                )

            year = int(raw_year)

            if not earliest_year <= year <= latest_year:
                raise DataValidationError(
                    f"Year {year} outside allowed range"
                )

            status = str(
                record.get("obs_status") or ""
            ).strip().upper()

            if status == "F":
                skipped_forecast_years.add(year)
                continue

            raw_value = record.get("value")

            if raw_value is None:
                missing_years.add(year)
                continue

            if isinstance(raw_value, bool):
                raise DataValidationError(
                    f"Boolean GDP value in {year}"
                )

            try:
                value = Decimal(str(raw_value))
            except (InvalidOperation, ValueError) as exc:
                raise DataValidationError(
                    f"Invalid GDP value in {year}"
                ) from exc

            if not value.is_finite() or value <= 0:
                raise DataValidationError(
                    f"Invalid non-positive GDP in {year}"
                )

            if year in observations:
                raise DataValidationError(
                    f"Duplicate observation for {year}"
                )

            observations[year] = GDPObservation(
                year=year,
                value_usd=value,
                obs_status=status,
            )

    if not observations:
        raise DataValidationError(
            "No valid historical GDP observations"
        )

    series = [
        observations[year]
        for year in sorted(observations)
    ]

    missing_years -= set(observations)

    quality = {
        "source_row_count": total_rows,
        "validated_row_count": len(series),
        "source_null_years": sorted(missing_years),
        "skipped_forecast_years": sorted(skipped_forecast_years),
        "first_year": series[0].year,
        "last_year": series[-1].year,
    }

    return series, quality
