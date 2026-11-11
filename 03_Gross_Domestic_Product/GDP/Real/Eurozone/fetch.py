
"""Collect Euro area real GDP (constant 2015 US$) from World Bank WDI.

Run from UnifyQ/macro:
    python3 03_Gross_Domestic_Product/GDP/Real/Eurozone/fetch.py
"""
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
LOG = logging.getLogger("unifyq.macro.gdp.real.eurozone")


def load_config() -> dict[str, Any]:
    cfg = json.loads((MODULE_DIR / "config.json").read_text(encoding="utf-8"))
    expected = {
        "asset_id": "macro.gdp.real.eurozone",
        "region_name": "Euro area",
        "region_code": "EMU",
        "region_wb2_code": "XC",
        "indicator_code": "NY.GDP.MKTP.KD",
        "indicator_name": "GDP (constant 2015 US$)",
        "base_year": 2015,
        "frequency": "A",
        "unit": "constant_2015_USD",
        "aggregation_type": "regional_aggregate",
    }
    for field, value in expected.items():
        if cfg.get(field) != value:
            raise ValueError(f"Invalid config {field}: expected {value!r}")
    if type(cfg.get("start_year")) is not int or not 1960 <= cfg["start_year"] <= 2100:
        raise ValueError("Invalid start_year")
    return cfg


def build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=4, connect=4, read=4, status=4,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": "UnifyQ-Research/0.1 (WDI-Eurozone-Real-GDP)"})
    return session


def _nonnegative_int(value: Any, field: str, minimum: int = 0) -> int:
    if (isinstance(value, bool) or not isinstance(value, (str, int))
            or re.fullmatch(r"[0-9]+", str(value)) is None):
        raise DataValidationError(f"Invalid pagination {field}: {value!r}")
    result = int(value)
    if result < minimum:
        raise DataValidationError(f"Pagination {field} below {minimum}")
    return result


def fetch_pages(session: requests.Session, cfg: dict[str, Any], latest_year: int) -> dict[str, Any]:
    url = API_URL.format(area=cfg["region_code"], indicator=cfg["indicator_code"])
    params = {
        "format": "json", "source": 2, "per_page": 20000,
        "date": f"{cfg['start_year']}:{latest_year}",
    }
    responses: list[list[Any]] = []
    expected_pages: int | None = None
    expected_total: int | None = None
    observed_rows = 0
    page = 1

    while True:
        result = session.get(url, params={**params, "page": page}, timeout=(5, 25))
        result.raise_for_status()
        try:
            payload = result.json()
        except ValueError as exc:
            raise DataValidationError("World Bank returned invalid JSON") from exc
        if (not isinstance(payload, list) or len(payload) != 2
                or not isinstance(payload[0], dict) or not isinstance(payload[1], list)):
            raise DataValidationError("Unexpected World Bank response")
        metadata, rows = payload
        current_page = _nonnegative_int(metadata.get("page"), "page", minimum=1)
        total_pages = _nonnegative_int(metadata.get("pages"), "pages", minimum=1)
        total_rows = _nonnegative_int(metadata.get("total"), "total")
        if current_page != page or total_pages > 100:
            raise DataValidationError("Invalid pagination sequence")
        if expected_pages is None:
            expected_pages, expected_total = total_pages, total_rows
        elif (total_pages, total_rows) != (expected_pages, expected_total):
            raise DataValidationError("Pagination changed during fetch")
        responses.append(payload)
        observed_rows += len(rows)
        LOG.info("Fetched page %d / %d", page, total_pages)
        if page == total_pages:
            break
        page += 1

    if observed_rows != expected_total:
        raise DataValidationError(
            f"Incomplete response: expected {expected_total}, got {observed_rows}"
        )
    return {"request": {"url": url, "params": params}, "responses": responses}


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".tmp-", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_csv(path: Path, observations: list[GDPObservation], retrieved_at: str) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow([
        "observation_year", "country_iso3", "indicator_id", "value",
        "unit", "frequency", "source", "obs_status", "retrieved_at",
    ])
    for obs in observations:
        writer.writerow([
            obs.year, "EMU", "NY.GDP.MKTP.KD", format(obs.value_usd, "f"),
            "constant_2015_USD", "A", "World Bank WDI", obs.obs_status, retrieved_at,
        ])
    atomic_write(path, buffer.getvalue().encode("utf-8"))


def run(
    *, output_root: Path, session: requests.Session | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
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
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    raw_file = (
        output_root / "raw" / "world_bank" / cfg["indicator_code"]
        / "EMU" / f"{digest}.json"
    )
    if not raw_file.exists():
        atomic_write(raw_file, raw_bytes)

    observations, quality = validate_and_normalize(
        payload["responses"], region_code="EMU",
        indicator_code=cfg["indicator_code"],
        earliest_year=cfg["start_year"], latest_year=now.year,
    )
    csv_file = output_root / "validated" / "macro" / "gdp" / "real" / "eurozone.csv"
    metadata_file = output_root / "metadata" / "macro" / "gdp" / "real" / "eurozone.json"
    manifest = {
        "asset_id": cfg["asset_id"],
        "dataset_contract_version": 1,
        "aggregation_type": "regional_aggregate",
        "region_name": "Euro area",
        "region_code": "EMU",
        "region_wb2_code": "XC",
        "csv_country_iso3_column_is_aggregate_code": True,
        "indicator_id": cfg["indicator_code"],
        "indicator_name": cfg["indicator_name"],
        "base_year": cfg["base_year"],
        "unit": cfg["unit"],
        "frequency": "A",
        "source": cfg["source"],
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
        (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
    )
    LOG.info(
        "Published %d observations (%d-%d)",
        quality["validated_row_count"], quality["first_year"], quality["last_year"],
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Euro area real GDP from WDI")
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
        LOG.error("Eurozone Real GDP fetch failed: %s", exc)
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
