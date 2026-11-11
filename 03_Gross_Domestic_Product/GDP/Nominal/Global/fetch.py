
"""Fetch annual World nominal GDP (WLD) from World Bank WDI."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import logging
import os
import re
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
API_URL = "https://api.worldbank.org/v2/country/{area}/indicator/{indicator}"
LOG = logging.getLogger("unifyq.macro.gdp.nominal.global")


def load_config() -> dict[str, Any]:
    with (MODULE_DIR / "config.json").open(encoding="utf-8") as stream:
        cfg = json.load(stream)
    if (cfg.get("region_code") != "WLD"
            or cfg.get("region_wb2_code") != "1W"
            or cfg.get("region_name") != "World"
            or cfg.get("indicator_code") != "NY.GDP.MKTP.CD"):
        raise ValueError("Expected World/WLD/1W and NY.GDP.MKTP.CD")
    if (type(cfg.get("start_year")) is not int
            or not 1900 <= cfg["start_year"] <= 2100
            or cfg.get("frequency") != "A"
            or cfg.get("unit") != "USD"):
        raise ValueError("Invalid start year, frequency or unit")
    return cfg


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4, connect=4, read=4, status=4,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "UnifyQ-Research/0.1 (World-GDP-WDI)"})
    return session


def pagination_integer(value: Any, name: str, minimum: int) -> int:
    if (isinstance(value, bool)
            or not isinstance(value, (int, str))
            or re.fullmatch(r"[0-9]+", str(value)) is None):
        raise DataValidationError(f"Invalid pagination {name}: {value!r}")
    parsed = int(value)
    if parsed < minimum:
        raise DataValidationError(f"Pagination {name} below {minimum}")
    return parsed


def fetch_pages(session: requests.Session, cfg: dict[str, Any], latest_year: int) -> dict[str, Any]:
    url = API_URL.format(area="WLD", indicator=cfg["indicator_code"])
    params = {
        "format": "json", "source": 2, "per_page": 20000,
        "date": f"{cfg['start_year']}:{latest_year}",
    }
    responses: list[list[Any]] = []
    expected_pages: int | None = None
    expected_total: int | None = None
    observed = 0
    page = 1

    while True:
        res = session.get(url, params={**params, "page": page}, timeout=(5, 25))
        res.raise_for_status()
        try:
            payload = res.json()
        except ValueError as exc:
            raise DataValidationError("Invalid API JSON") from exc
        if (not isinstance(payload, list) or len(payload) != 2
                or not isinstance(payload[0], dict)
                or not isinstance(payload[1], list)):
            raise DataValidationError("Unexpected World Bank API response")

        meta, rows = payload
        current = pagination_integer(meta.get("page"), "page", 1)
        pages = pagination_integer(meta.get("pages"), "pages", 1)
        total = pagination_integer(meta.get("total"), "total", 0)
        if current != page or pages > 100:
            raise DataValidationError("Inconsistent pagination")
        if expected_pages is None:
            expected_pages, expected_total = pages, total
        elif pages != expected_pages or total != expected_total:
            raise DataValidationError("Pagination changed during fetch")
        responses.append(payload)
        observed += len(rows)
        LOG.info("Fetched page %d / %d", page, pages)
        if page == pages:
            break
        page += 1

    if observed != expected_total:
        raise DataValidationError(
            f"Incomplete pagination: expected {expected_total}, got {observed}"
        )
    return {"request": {"url": url, "params": params}, "responses": responses}


def atomic_write(destination: Path, content: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, prefix=".tmp-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_csv(destination: Path, observations: list[GDPObservation], retrieved_at: str) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow([
        "observation_year", "country_iso3", "indicator_id", "value", "unit",
        "frequency", "source", "obs_status", "retrieved_at",
    ])
    for obs in observations:
        writer.writerow([
            obs.year, "WLD", "NY.GDP.MKTP.CD", format(obs.value_usd, "f"),
            "USD", "A", "World Bank WDI", obs.obs_status, retrieved_at,
        ])
    atomic_write(destination, buffer.getvalue().encode("utf-8"))


def run(*, output_root: Path, session: requests.Session | None = None,
        now: datetime | None = None) -> dict[str, Any]:
    cfg = load_config()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    if cfg["start_year"] > now.year:
        raise ValueError("start_year exceeds current year")
    retrieved_at = now.isoformat().replace("+00:00", "Z")

    owns_session = session is None
    if owns_session:
        session = build_session()
    assert session is not None
    try:
        payload = fetch_pages(session, cfg, now.year)
    finally:
        if owns_session:
            session.close()

    raw_bytes = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    raw_file = (
        output_root / "raw" / "world_bank" / cfg["indicator_code"]
        / "WLD" / f"{digest}.json"
    )
    if not raw_file.exists():
        atomic_write(raw_file, raw_bytes)

    observations, quality = validate_and_normalize(
        payload["responses"], region_code="WLD",
        indicator_code=cfg["indicator_code"],
        earliest_year=cfg["start_year"], latest_year=now.year,
    )
    csv_file = output_root / "validated" / "macro" / "gdp" / "nominal" / "global.csv"
    metadata_file = output_root / "metadata" / "macro" / "gdp" / "nominal" / "global.json"
    manifest = {
        "asset_id": cfg["asset_id"],
        "dataset_contract_version": 1,
        "aggregation_type": "world_aggregate",
        "region_name": "World",
        "region_code": "WLD",
        "region_wb2_code": "1W",
        "csv_country_iso3_column_is_aggregate_code": True,
        "indicator_id": cfg["indicator_code"],
        "source": cfg["source"],
        "unit": "USD",
        "frequency": "A",
        "retrieved_at": retrieved_at,
        "source_lastupdated": payload["responses"][0][0].get("lastupdated"),
        "source_snapshot_sha256": digest,
        "raw_file": str(raw_file.resolve()),
        "validated_file": str(csv_file.resolve()),
        "quality_status": "passed",
        "historical_vintage_guaranteed": False,
        "release_timestamp_available": False,
        "quality_metrics": quality,
    }
    write_csv(csv_file, observations, retrieved_at)
    atomic_write(
        metadata_file,
        (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"),
    )
    LOG.info(
        "Published %d observations (%d-%d)",
        quality["validated_row_count"], quality["first_year"], quality["last_year"],
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch World nominal GDP from WDI")
    parser.add_argument("--output-root", type=Path, default=MACRO_ROOT / "data")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    try:
        manifest = run(output_root=args.output_root.expanduser().resolve())
    except (requests.RequestException, DataValidationError, ValueError, OSError) as exc:
        LOG.error("Global GDP fetch failed: %s", exc)
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
