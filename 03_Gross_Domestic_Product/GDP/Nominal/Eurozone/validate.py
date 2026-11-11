
"""Strict WDI Euro area nominal-GDP quality gate (regional aggregate)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class DataValidationError(ValueError):
    """Source data cannot be published as validated GDP."""


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
    """Validate every row and keep historical non-null observations."""

    if region_code != "EMU":
        raise DataValidationError(
            "This validator only supports EMU"
        )

    if not responses:
        raise DataValidationError("No World Bank responses")

    if earliest_year > latest_year:
        raise DataValidationError("Invalid year interval")

    values: dict[int, GDPObservation] = {}
    null_years: set[int] = set()
    forecast_years: set[int] = set()
    row_count = 0

    for response in responses:

        if not isinstance(response, list) or len(response) != 2:
            raise DataValidationError(
                "Expected [metadata, rows]"
            )

        metadata, rows = response

        if not isinstance(metadata, dict) or not isinstance(rows, list):
            raise DataValidationError(
                "Invalid World Bank page structure"
            )

        for row in rows:
            row_count += 1

            if not isinstance(row, dict):
                raise DataValidationError(
                    "Invalid GDP observation"
                )

            area = row.get("country")

            if not isinstance(area, dict) or area.get("id") != "XC":
                raise DataValidationError(
                    "Expected Euro area aggregate (XC)"
                )

            if area.get("value") != "Euro area":
                raise DataValidationError(
                    "Unexpected aggregate name"
                )

            if row.get("countryiso3code") not in (None, "", "EMU"):
                raise DataValidationError(
                    "Unexpected countryiso3code"
                )

            indicator = row.get("indicator")

            if (
                not isinstance(indicator, dict)
                or indicator.get("id") != indicator_code
            ):
                raise DataValidationError(
                    "Unexpected GDP indicator"
                )

            raw_year = row.get("date")

            if (
                not isinstance(raw_year, str)
                or re.fullmatch(r"[0-9]{4}", raw_year) is None
            ):
                raise DataValidationError(
                    f"Invalid year: {raw_year!r}"
                )

            year = int(raw_year)

            if not earliest_year <= year <= latest_year:
                raise DataValidationError(
                    f"Year {year} outside requested interval"
                )

            status = str(
                row.get("obs_status") or ""
            ).strip().upper()

            if status == "F":
                forecast_years.add(year)
                continue

            raw_value = row.get("value")

            if raw_value is None:
                null_years.add(year)
                continue

            if isinstance(raw_value, bool):
                raise DataValidationError(
                    f"Boolean GDP value in {year}"
                )

            try:
                value = Decimal(str(raw_value))

            except (InvalidOperation, ValueError, TypeError) as exc:
                raise DataValidationError(
                    f"Invalid GDP value in {year}"
                ) from exc

            if not value.is_finite() or value <= 0:
                raise DataValidationError(
                    f"Nonpositive/nonfinite GDP in {year}"
                )

            if year in values:
                raise DataValidationError(
                    f"Duplicate GDP observation for {year}"
                )

            values[year] = GDPObservation(
                year,
                value,
                status,
            )

    if not values:
        raise DataValidationError(
            "No valid Euro area GDP observations"
        )

    series = [values[y] for y in sorted(values)]

    null_years.difference_update(values)

    return series, {
        "source_row_count": row_count,
        "validated_row_count": len(series),
        "source_null_years": sorted(null_years),
        "skipped_forecast_years": sorted(forecast_years),
        "first_year": series[0].year,
        "last_year": series[-1].year,
    }
