
"""Fetch and publish annual US nominal GDP from World Bank WDI."""
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

MODULE_DIR = Path(__file__).resolve().parent
MACRO_ROOT = MODULE_DIR.parents[3]
API_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
LOG = logging.getLogger("unifyq.macro.gdp.nominal.us")


def load_config() -> dict[str, Any]:
    with (MODULE_DIR / "config.json").open(encoding="utf-8") as file:
        config = json.load(file)

    if config.get("country_iso3") != "USA":
        raise ValueError("Expected country_iso3='USA'")

    if config.get("indicator_code") != "NY.GDP.MKTP.CD":
        raise ValueError("Expected nominal GDP indicator NY.GDP.MKTP.CD")

    if (
        type(config.get("start_year")) is not int
        or not 1900 <= config["start_year"] <= 2100
    ):
        raise ValueError("Invalid start_year")

    return config


def build_session() -> requests.Session:
    session = requests.Session()

    retries = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )

    session.mount("https://", HTTPAdapter(max_retries=retries))

    session.headers.update({
        "User-Agent": "UnifyQ-Research/0.1 (WDI-GDP-Collector)"
    })

    return session


def fetch_pages(
    session: requests.Session,
    config: dict[str, Any],
    latest_year: int,
) -> dict[str, Any]:

    url = API_URL.format(
        country=config["country_iso3"],
        indicator=config["indicator_code"],
    )

    params = {
        "format": "json",
        "per_page": 20000,
        "date": f"{config['start_year']}:{latest_year}",
    }

    pages: list[list[Any]] = []
    total_pages: int | None = None
    page_number = 1

    while True:
        response = session.get(
            url,
            params={**params, "page": page_number},
            timeout=(5, 25),
        )

        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            raise DataValidationError(
                "Invalid JSON returned by World Bank"
            ) from exc

        if (
            not isinstance(payload, list)
            or len(payload) != 2
            or not isinstance(payload[0], dict)
            or not isinstance(payload[1], list)
        ):
            raise DataValidationError(
                "Invalid World Bank API response"
            )

        metadata = payload[0]

        try:
            current = int(metadata["page"])
            count = int(metadata["pages"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(
                "Invalid pagination metadata"
            ) from exc

        if current != page_number or not 1 <= count <= 100:
            raise DataValidationError(
                "Unexpected pagination metadata"
            )

        if total_pages is None:
            total_pages = count
        elif count != total_pages:
            raise DataValidationError(
                "Pagination changed during collection"
            )

        pages.append(payload)

        LOG.info(
            "Fetched page %d / %d",
            page_number,
            total_pages,
        )

        if page_number == total_pages:
            break

        page_number += 1

    return {
        "request": {
            "url": url,
            "params": params,
        },
        "responses": pages,
    }


def atomic_write(destination: Path, content: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=".tmp-",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, destination)

    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_csv(
    destination: Path,
    rows: list[GDPObservation],
    retrieved_at: str,
) -> None:

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)

    writer.writerow([
        "observation_year",
        "country_iso3",
        "indicator_id",
        "value",
        "unit",
        "frequency",
        "source",
        "obs_status",
        "retrieved_at",
    ])

    for item in rows:
        writer.writerow([
            item.year,
            "USA",
            "NY.GDP.MKTP.CD",
            format(item.value_usd, "f"),
            "USD",
            "A",
            "World Bank WDI",
            item.obs_status,
            retrieved_at,
        ])

    atomic_write(
        destination,
        buffer.getvalue().encode("utf-8"),
    )


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

    if config["start_year"] > now.year:
        raise ValueError("start_year exceeds current year")

    retrieved_at = now.isoformat().replace("+00:00", "Z")

    owns_session = session is None
    session = session or build_session()

    try:
        payload = fetch_pages(session, config, now.year)
    finally:
        if owns_session:
            session.close()

    raw_content = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ) + "\n"
    ).encode("utf-8")

    digest = hashlib.sha256(raw_content).hexdigest()

    raw_file = (
        output_root
        / "raw"
        / "world_bank"
        / config["indicator_code"]
        / "USA"
        / f"{digest}.json"
    )

    if not raw_file.exists():
        atomic_write(raw_file, raw_content)

    observations, quality = validate_and_normalize(
        payload["responses"],
        country_iso3="USA",
        indicator_code="NY.GDP.MKTP.CD",
        earliest_year=config["start_year"],
        latest_year=now.year,
    )

    csv_file = (
        output_root
        / "validated"
        / "macro"
        / "gdp"
        / "nominal"
        / "us.csv"
    )

    metadata_file = (
        output_root
        / "metadata"
        / "macro"
        / "gdp"
        / "nominal"
        / "us.json"
    )

    manifest = {
        "asset_id": config["asset_id"],
        "dataset_contract_version": 1,
        "country_iso3": "USA",
        "indicator_id": "NY.GDP.MKTP.CD",
        "source": config["source"],
        "unit": "USD",
        "frequency": "A",
        "retrieved_at": retrieved_at,
        "source_lastupdated": payload["responses"][0][0].get(
            "lastupdated"
        ),
        "source_snapshot_sha256": digest,
        "raw_file": str(raw_file.resolve()),
        "validated_file": str(csv_file.resolve()),
        "quality_status": "passed",
        "historical_vintage_guaranteed": False,
        "release_timestamp_available": False,
        "quality_metrics": quality,
    }

    save_csv(
        csv_file,
        observations,
        retrieved_at,
    )

    atomic_write(
        metadata_file,
        (
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            ) + "\n"
        ).encode("utf-8"),
    )

    LOG.info(
        "Published %d observations (%d-%d)",
        quality["validated_row_count"],
        quality["first_year"],
        quality["last_year"],
    )

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch US nominal GDP (WDI)"
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=MACRO_ROOT / "data",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        manifest = run(
            output_root=args.output_root.expanduser().resolve()
        )

    except (
        requests.RequestException,
        DataValidationError,
        ValueError,
        OSError,
    ) as exc:
        LOG.error(
            "US nominal GDP collection failed: %s",
            exc,
        )
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
