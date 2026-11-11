
"""Compute GES from four local validated nominal-GDP datasets. No fetches.

Usage (from UnifyQ/macro):
    python3 03_Gross_Domestic_Product/GDP/Global_Economic_Share/calculate.py
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from load import LoadedGDP, load_all
from publish import publish
from validate import GESValidationError, validate_share_inputs

MODULE_DIR = Path(__file__).resolve().parent
MACRO_ROOT = MODULE_DIR.parents[2]

LOG = logging.getLogger(
    "unifyq.macro.gdp.global_economic_share"
)

SERIES = (
    ("GES_USA", "USA"),
    ("GES_CHN", "CHN"),
    ("GES_EMU", "EMU"),
    ("GES_COMBINED", "COMBINED"),
    ("GES_REST", "REST"),
)


def load_config() -> dict[str, Any]:
    config = json.loads(
        (MODULE_DIR / "config.json").read_text(
            encoding="utf-8"
        )
    )

    expected = {
        "asset_id": "macro.gdp.global_economic_share",
        "source_indicator": "NY.GDP.MKTP.CD",
        "expected_source": "World Bank WDI",
        "input_unit": "USD",
        "input_frequency": "A",
        "output_unit": "percent",
        "start_year": 1960,
        "decimal_places": 6,
        "input_files": {
            "CHN": "china",
            "USA": "us",
            "EMU": "eurozone",
            "WLD": "global",
        },
    }

    if config != expected:
        raise GESValidationError(
            "config.json does not match the GES data contract"
        )

    return config


def calculate_rows(
    inputs: dict[str, LoadedGDP],
    *,
    calculated_at: str,
    places: int = 6,
) -> tuple[list[dict[str, str]], dict[str, Any]]:

    if set(inputs) != {"CHN", "USA", "EMU", "WLD"}:
        raise GESValidationError(
            "Need CHN, USA, EMU and WLD inputs"
        )

    years = {
        code: set(item.values)
        for code, item in inputs.items()
    }

    common_years = sorted(
        set.intersection(*years.values())
    )

    all_years = set.union(*years.values())

    if not common_years:
        raise GESValidationError(
            "No shared GDP observation years"
        )

    quantum = Decimal(1).scaleb(-places)
    hundred = Decimal(100)

    result: list[dict[str, str]] = []

    for year in common_years:

        us = inputs["USA"].values[year]
        china = inputs["CHN"].values[year]
        euro = inputs["EMU"].values[year]
        world = inputs["WLD"].values[year]

        validate_share_inputs(
            year=year,
            us=us,
            china=china,
            eurozone=euro,
            world=world,
        )

        combined = us + china + euro

        amounts = {
            "USA": us,
            "CHN": china,
            "EMU": euro,
            "COMBINED": combined,
            "REST": world - combined,
        }

        for series_id, key in SERIES:

            numerator = amounts[key]

            percentage = (
                numerator / world * hundred
            ).quantize(
                quantum,
                rounding=ROUND_HALF_UP,
            )

            result.append({
                "observation_year": str(year),
                "series_id": series_id,
                "value": format(percentage, "f"),
                "unit": "percent",
                "frequency": "A",
                "source": "UnifyQ derived from World Bank WDI",
                "numerator_gdp_usd": format(
                    numerator, "f"
                ),
                "world_gdp_usd": format(
                    world, "f"
                ),
                "calculated_at": calculated_at,
            })

    info = {
        "common_year_count": len(common_years),
        "first_year": common_years[0],
        "last_year": common_years[-1],
        "dropped_years": sorted(
            all_years.difference(common_years)
        ),
        "missing_by_economy": {
            code: sorted(
                all_years.difference(covered)
            )
            for code, covered in years.items()
        },
        "series_count": len(SERIES),
        "derived_row_count": len(result),
    }

    return result, info


def run(
    *,
    data_root: Path,
    now: datetime | None = None,
) -> dict[str, Any]:

    config = load_config()

    now = now or datetime.now(timezone.utc)

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    now = now.astimezone(timezone.utc)

    calculated_at = (
        now.isoformat().replace("+00:00", "Z")
    )

    inputs = load_all(data_root, now.year)

    rows, stats = calculate_rows(
        inputs,
        calculated_at=calculated_at,
    )

    source_dates = {
        code: item.source_lastupdated
        for code, item in inputs.items()
    }

    distinct_dates = {
        x for x in source_dates.values()
        if x is not None
    }

    manifest = {
        "asset_id": config["asset_id"],
        "asset_type": "derived",
        "formula": (
            "country_nominal_gdp_usd / "
            "world_nominal_gdp_usd * 100"
        ),
        "source_indicator": "NY.GDP.MKTP.CD",
        "unit": "percent",
        "frequency": "A",
        "calculated_at": calculated_at,
        "data_quality": stats,
        "source_lastupdated_dates": source_dates,
        "source_lastupdated_aligned": (
            len(distinct_dates) == 1
            and len(source_dates) == 4
            and all(source_dates.values())
        ),
        "point_in_time_vintages_guaranteed": False,
        "inputs": {
            code: {
                "validated_file": item.csv_path,
                "metadata_file": item.metadata_path,
                "validated_csv_sha256": item.csv_sha256,
                "source_snapshot_sha256": (
                    item.source_snapshot_sha256
                ),
                "retrieved_at": item.retrieved_at,
            }
            for code, item in inputs.items()
        },
    }

    result = publish(
        data_root=data_root,
        rows=rows,
        manifest=manifest,
    )

    LOG.info(
        "Published %d GES rows, %d years",
        len(rows),
        stats["common_year_count"],
    )

    if not result["source_lastupdated_aligned"]:
        LOG.warning(
            "Input World Bank lastupdated dates "
            "differ or are unavailable"
        )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute PTM Global Economic Share"
    )

    parser.add_argument(
        "--data-root",
        type=Path,
        default=MACRO_ROOT / "data",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        result = run(
            data_root=args.data_root.expanduser().resolve()
        )

    except (
        GESValidationError,
        OSError,
        ValueError,
    ) as exc:

        LOG.error(
            "GES calculation failed: %s",
            exc,
        )

        raise SystemExit(1) from exc

    print(json.dumps({
        "status": result["quality_status"],
        "asset_id": result["asset_id"],
        "derived_file": result["derived_file"],
        "years": (
            result["data_quality"]["common_year_count"]
        ),
        "rows": (
            result["data_quality"]["derived_row_count"]
        ),
        "source_lastupdated_aligned": (
            result["source_lastupdated_aligned"]
        ),
    }, indent=2))


if __name__ == "__main__":
    main()
