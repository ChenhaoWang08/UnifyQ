
"""Load and verify four existing nominal GDP assets. No HTTP requests."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from validate import (
    CSV_COLUMNS,
    GESValidationError,
    parse_gdp_record,
    parse_timestamp,
)


@dataclass(frozen=True)
class LoadedGDP:
    economy_code: str
    values: dict[int, Decimal]
    csv_sha256: str
    source_snapshot_sha256: str
    source_lastupdated: str | None
    retrieved_at: str
    csv_path: str
    metadata_path: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_one(
    data_root: Path,
    name: str,
    code: str,
    latest_year: int,
) -> LoadedGDP:

    csv_path = (
        data_root / "validated" / "macro"
        / "gdp" / "nominal" / f"{name}.csv"
    )

    metadata_path = (
        data_root / "metadata" / "macro"
        / "gdp" / "nominal" / f"{name}.json"
    )

    if not csv_path.is_file() or not metadata_path.is_file():
        raise GESValidationError(
            f"Missing validated CSV or metadata for {code}"
        )

    try:
        metadata = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise GESValidationError(
            f"Invalid manifest for {code}"
        ) from exc

    expected_asset = f"macro.gdp.nominal.{name}"

    for field, expected in (
        ("quality_status", "passed"),
        ("asset_id", expected_asset),
        ("indicator_id", "NY.GDP.MKTP.CD"),
        ("unit", "USD"),
        ("frequency", "A"),
    ):
        if metadata.get(field) != expected:
            raise GESValidationError(
                f"{code}: invalid manifest {field}"
            )

    if metadata.get("validated_file") and (
        Path(metadata["validated_file"]).resolve()
        != csv_path.resolve()
    ):
        raise GESValidationError(
            f"{code}: manifest points to another CSV"
        )

    snapshot_sha = metadata.get("source_snapshot_sha256")

    if (
        not isinstance(snapshot_sha, str)
        or not re.fullmatch(r"[0-9a-f]{64}", snapshot_sha)
    ):
        raise GESValidationError(
            f"{code}: missing/invalid source snapshot SHA-256"
        )

    raw_path = Path(str(metadata.get("raw_file") or ""))

    if (
        not raw_path.is_file()
        or _sha256_file(raw_path) != snapshot_sha
    ):
        raise GESValidationError(
            f"{code}: missing or modified raw source snapshot"
        )

    if (
        code in {"CHN", "USA"}
        and metadata.get("country_iso3") != code
    ):
        raise GESValidationError(
            f"{code}: wrong manifest country"
        )

    if (
        code in {"EMU", "WLD"}
        and metadata.get("region_code") != code
    ):
        raise GESValidationError(
            f"{code}: wrong manifest aggregate code"
        )

    values: dict[int, Decimal] = {}
    retrieval_times: set[str] = set()

    with csv_path.open(
        newline="",
        encoding="utf-8-sig",
    ) as stream:

        reader = csv.DictReader(stream)

        if reader.fieldnames != CSV_COLUMNS:
            raise GESValidationError(
                f"{code}: incompatible CSV schema"
            )

        for record in reader:
            year, value = parse_gdp_record(
                record,
                economy_code=code,
                latest_year=latest_year,
            )

            if year in values:
                raise GESValidationError(
                    f"{code}: duplicate year {year}"
                )

            values[year] = value
            retrieval_times.add(record["retrieved_at"])

    if not values or len(retrieval_times) != 1:
        raise GESValidationError(
            f"{code}: empty data or mixed retrieval timestamps"
        )

    retrieved_at = next(iter(retrieval_times))

    parse_timestamp(metadata.get("retrieved_at"))

    if retrieved_at != metadata["retrieved_at"]:
        raise GESValidationError(
            f"{code}: CSV timestamp does not match manifest"
        )

    quality = metadata.get("quality_metrics") or {}

    if quality.get("validated_row_count") != len(values):
        raise GESValidationError(
            f"{code}: CSV row count differs from manifest"
        )

    return LoadedGDP(
        economy_code=code,
        values=values,
        csv_sha256=_sha256_file(csv_path),
        source_snapshot_sha256=snapshot_sha,
        source_lastupdated=metadata.get("source_lastupdated"),
        retrieved_at=retrieved_at,
        csv_path=str(csv_path.resolve()),
        metadata_path=str(metadata_path.resolve()),
    )


def load_all(
    data_root: Path,
    latest_year: int,
) -> dict[str, LoadedGDP]:

    names = {
        "CHN": "china",
        "USA": "us",
        "EMU": "eurozone",
        "WLD": "global",
    }

    return {
        code: load_one(data_root, name, code, latest_year)
        for code, name in names.items()
    }
