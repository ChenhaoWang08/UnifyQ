
"""Validation rules for UnifyQ Global Economic Share (GES)."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


class GESValidationError(ValueError):
    """Reject inputs or calculated results that cannot be trusted."""


CSV_COLUMNS = [
    "observation_year", "country_iso3", "indicator_id", "value",
    "unit", "frequency", "source", "obs_status", "retrieved_at",
]


def parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise GESValidationError("Missing retrieved_at timestamp")

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise GESValidationError(
            f"Invalid timestamp: {value!r}"
        ) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GESValidationError(
            "retrieved_at must include a time zone"
        )

    return parsed


def parse_gdp_record(
    record: dict[str, str],
    *,
    economy_code: str,
    latest_year: int,
) -> tuple[int, Decimal]:

    if record.get("country_iso3") != economy_code:
        raise GESValidationError(
            f"Wrong economy in {economy_code} CSV"
        )

    for field, expected in (
        ("indicator_id", "NY.GDP.MKTP.CD"),
        ("unit", "USD"),
        ("frequency", "A"),
        ("source", "World Bank WDI"),
    ):
        if record.get(field) != expected:
            raise GESValidationError(
                f"{economy_code}: {field} must be {expected!r}"
            )

    if str(record.get("obs_status") or "").upper() == "F":
        raise GESValidationError(
            f"Forecast in validated {economy_code} CSV"
        )

    year_text = record.get("observation_year")

    if (
        not isinstance(year_text, str)
        or re.fullmatch(r"[0-9]{4}", year_text) is None
    ):
        raise GESValidationError(
            f"Invalid year in {economy_code}: {year_text!r}"
        )

    year = int(year_text)

    if not 1960 <= year <= latest_year:
        raise GESValidationError(
            f"Year out of bounds in {economy_code}: {year}"
        )

    raw_value = record.get("value")

    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise GESValidationError(
            f"Invalid GDP for {economy_code} in {year}"
        ) from exc

    if not value.is_finite() or value <= 0:
        raise GESValidationError(
            f"GDP must be positive and finite: "
            f"{economy_code}/{year}"
        )

    parse_timestamp(record.get("retrieved_at"))

    return year, value


def validate_share_inputs(
    *,
    year: int,
    us: Decimal,
    china: Decimal,
    eurozone: Decimal,
    world: Decimal,
) -> None:

    values = {
        "USA": us,
        "CHN": china,
        "EMU": eurozone,
        "WLD": world,
    }

    for economy, value in values.items():
        if not value.is_finite() or value <= 0:
            raise GESValidationError(
                f"Invalid {economy} GDP in {year}"
            )

    combined = us + china + eurozone

    if combined > world:
        raise GESValidationError(
            f"Combined GDP exceeds World GDP in {year}: "
            f"{combined} > {world}"
        )
