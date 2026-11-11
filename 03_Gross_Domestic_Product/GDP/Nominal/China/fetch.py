
"""Fetch, validate, and publish China's annual nominal GDP (World Bank WDI).

Usage:
    python 03_Gross_Domestic_Product/GDP/Nominal/China/fetch.py
    python 03_Gross_Domestic_Product/GDP/Nominal/China/fetch.py --output-root /tmp/unifyq-data

WDI history is not point-in-time vintage data; individual release times are unknown.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from validate import DataValidationError, GDPObservation, validate_and_normalize

LOG = logging.getLogger("unifyq.macro.gdp.nominal.china")
MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[3]
BASE_API_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"


def load_config() -> dict[str, Any]:
    with (MODULE_DIR / "config.json").open(encoding="utf-8") as file:
        config: dict[str, Any] = json.load(file)
    if (config.get("country_iso3"), config.get("indicator_code")) != (
        "CHN", "NY.GDP.MKTP.CD"
    ):
        raise ValueError("This module is strictly for CHN / NY.GDP.MKTP.CD")
    return config


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4, connect=4, read=4, status=4,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "UnifyQ-Research/0.1 (WorldBank-WDI-Collector)"
    })
    return session


def fetch_pages(
    session: requests.Session,
    config: dict[str, Any],
    latest_year: int,
) -> dict[str, Any]:
    url = BASE_API_URL.format(
        country=config["country_iso3"],
        indicator=config["indicator_code"],
    )
    params: dict[str, Any] = {
        "format": "json",
        "per_page": 20000,
        "date": f"{config['start_year']}:{latest_year}",
    }
    responses: list[list[Any]] = []
    expected_pages: int | None = None
    page = 1

    while True:
        response = session.get(
            url, params={**params, "page": page}, timeout=(5, 25)
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:  # Includes requests JSONDecodeError
            raise DataValidationError("World Bank returned invalid JSON") from exc

        if (
            not isinstance(payload, list)
            or len(payload) != 2
            or not isinstance(payload[0], dict)
        ):
            raise DataValidationError(
                "World Bank API returned an error or invalid response: "
                f"{str(payload)[:200]}"
            )

        metadata = payload[0]
        try:
            reported_pages = int(metadata["pages"])
            reported_page = int(metadata["page"])
        except (KeyError, ValueError, TypeError) as exc:
            raise DataValidationError(
                "Missing World Bank pagination metadata"
            ) from exc

        if reported_pages < 1 or reported_pages > 100 or reported_page != page:
            raise DataValidationError("Unexpected World Bank page metadata")
        if expected_pages is None:
            expected_pages = reported_pages
        elif expected_pages != reported_pages:
            raise DataValidationError("World Bank pagination changed during fetch")

        responses.append(payload)
        LOG.info("Fetched page %s / %s", page, expected_pages)
        if page >= expected_pages:
            break
        page += 1

    return {"request": {"url": url, "params": params}, "responses": responses}


def _atomic_write_bytes(destination: Path, payload: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, prefix=".tmp-", delete=False
        ) as temp:
            temporary = Path(temp.name)
            temp.write(payload)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_validated_csv(
    destination: Path,
    observations: list[GDPObservation],
    retrieved_at: str,
) -> None:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([
        "observation_year", "country_iso3", "indicator_id", "value", "unit",
        "frequency", "source", "obs_status", "retrieved_at",
    ])
    for observation in observations:
        writer.writerow([
            observation.year, "CHN", "NY.GDP.MKTP.CD",
            format(observation.value_usd, "f"), "USD", "A", "World Bank WDI",
            observation.obs_status, retrieved_at,
        ])
    _atomic_write_bytes(destination, stream.getvalue().encode("utf-8"))


def run(
    *,
    output_root: Path,
    session: requests.Session | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    config = load_config()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    if int(config["start_year"]) > now.year:
        raise ValueError("start_year must not exceed current year")
    retrieved_at = now.isoformat().replace("+00:00", "Z")

    owns_session = session is None
    if owns_session:
        session = build_session()
    assert session is not None
    try:
        payload = fetch_pages(session, config, now.year)
    finally:
        if owns_session:
            session.close()

    # Preserve exact raw formatting and content-based SHA-256 from original.
    raw_bytes = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    raw_file = (
        output_root / "raw" / "world_bank" / config["indicator_code"]
        / "CHN" / f"{digest}.json"
    )
    if not raw_file.exists():
        _atomic_write_bytes(raw_file, raw_bytes)

    observations, quality = validate_and_normalize(
        payload["responses"],
        country_iso3="CHN",
        indicator_code="NY.GDP.MKTP.CD",
        earliest_year=int(config["start_year"]),
        latest_year=now.year,
    )
    output_csv = output_root / "validated" / "macro" / "gdp" / "nominal" / "china.csv"
    manifest_path = output_root / "metadata" / "macro" / "gdp" / "nominal" / "china.json"
    manifest = {
        "asset_id": config["asset_id"],
        "dataset_contract_version": 1,
        "source": config["source"],
        "country_iso3": config["country_iso3"],
        "indicator_id": config["indicator_code"],
        "unit": "USD",
        "frequency": "A",
        "retrieved_at": retrieved_at,
        "source_lastupdated": payload["responses"][0][0].get("lastupdated"),
        "source_snapshot_sha256": digest,
        "raw_file": str(raw_file.resolve()),
        "validated_file": str(output_csv.resolve()),
        "quality_status": "passed",
        "historical_vintage_guaranteed": False,
        "release_timestamp_available": False,
        "quality_metrics": quality,
    }
    # The published CSV remains untouched if validation fails.
    write_validated_csv(output_csv, observations, retrieved_at)
    _atomic_write_bytes(
        manifest_path,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        .encode("utf-8"),
    )
    LOG.info(
        "Published %s observations (%s-%s)",
        quality["validated_row_count"], quality["first_year"], quality["last_year"],
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch China's nominal GDP from World Bank WDI"
    )
    parser.add_argument(
        "--output-root", type=Path, default=PROJECT_ROOT / "data",
        help="Root for raw/validated/metadata subfolders",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable detailed logs"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    try:
        manifest = run(output_root=args.output_root.expanduser().resolve())
    except (requests.RequestException, DataValidationError, ValueError, OSError) as exc:
        LOG.error("China nominal GDP collection failed: %s", exc)
        raise SystemExit(1) from exc
    print(json.dumps({
        "status": manifest["quality_status"],
        "asset_id": manifest["asset_id"],
        "validated_file": manifest["validated_file"],
        "rows": manifest["quality_metrics"]["validated_row_count"],
        "snapshot_sha256": manifest["source_snapshot_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
