
"""Fetch China real GDP (constant 2015 US$) from World Bank WDI.

Run from UnifyQ/macro:
    python3 03_Gross_Domestic_Product/GDP/Real/China/fetch.py
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
API_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
LOG = logging.getLogger("unifyq.macro.gdp.real.china")


def load_config() -> dict[str, Any]:
    cfg = json.loads((MODULE_DIR / "config.json").read_text(encoding="utf-8"))
    expected = {
        "asset_id": "macro.gdp.real.china",
        "country_iso3": "CHN",
        "indicator_code": "NY.GDP.MKTP.KD",
        "base_year": 2015,
        "frequency": "A",
        "unit": "constant_2015_USD",
        "data_kind": "real_gdp_constant_2015_usd",
    }
    for key, value in expected.items():
        if cfg.get(key) != value:
            raise ValueError(f"Invalid config {key}: expected {value!r}")
    if type(cfg.get("start_year")) is not int or not 1960 <= cfg["start_year"] <= 2100:
        raise ValueError("Invalid start_year")
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
    session.headers.update({"User-Agent": "UnifyQ-Research/0.1 (WDI-Real-GDP)"})
    return session


def _page_int(value: Any, name: str, minimum: int) -> int:
    if (isinstance(value, bool) or not isinstance(value, (int, str))
            or re.fullmatch(r"[0-9]+", str(value)) is None):
        raise DataValidationError(f"Invalid pagination {name}: {value!r}")
    parsed = int(value)
    if parsed < minimum:
        raise DataValidationError(f"Invalid pagination {name}: {parsed}")
    return parsed


def fetch_pages(session: requests.Session, cfg: dict[str, Any], latest_year: int) -> dict[str, Any]:
    url = API_URL.format(country="CHN", indicator=cfg["indicator_code"])
    params = {
        "format": "json", "source": 2, "per_page": 20000,
        "date": f"{cfg['start_year']}:{latest_year}",
    }
    pages: list[list[Any]] = []
    expected_pages: int | None = None
    expected_total: int | None = None
    received = 0
    page_number = 1

    while True:
        res = session.get(url, params={**params, "page": page_number}, timeout=(5, 25))
        res.raise_for_status()
        try:
            payload = res.json()
        except ValueError as exc:
            raise DataValidationError("World Bank returned invalid JSON") from exc
        if (not isinstance(payload, list) or len(payload) != 2
                or not isinstance(payload[0], dict)
                or not isinstance(payload[1], list)):
            raise DataValidationError("World Bank returned unexpected API response")
        meta, rows = payload
        page = _page_int(meta.get("page"), "page", 1)
        page_count = _page_int(meta.get("pages"), "pages", 1)
        total = _page_int(meta.get("total"), "total", 0)
        if page != page_number or page_count > 100:
            raise DataValidationError("Pagination page mismatch")
        if expected_pages is None:
            expected_pages, expected_total = page_count, total
        elif (page_count, total) != (expected_pages, expected_total):
            raise DataValidationError("Pagination changed during fetch")
        pages.append(payload)
        received += len(rows)
        LOG.info("Fetched page %d / %d", page_number, page_count)
        if page_number == page_count:
            break
        page_number += 1
    if received != expected_total:
        raise DataValidationError(f"Incomplete response: {received}/{expected_total} rows")
    return {"request": {"url": url, "params": params}, "responses": pages}


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".tmp-", delete=False) as f:
            temp = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def write_csv(path: Path, observations: list[GDPObservation], retrieved_at: str) -> None:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "observation_year", "country_iso3", "indicator_id", "value", "unit",
        "frequency", "source", "obs_status", "retrieved_at",
    ])
    for obs in observations:
        writer.writerow([
            obs.year, "CHN", "NY.GDP.MKTP.KD", format(obs.value_usd, "f"),
            "constant_2015_USD", "A", "World Bank WDI", obs.obs_status, retrieved_at,
        ])
    atomic_write(path, output.getvalue().encode("utf-8"))


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
    owned = session is None
    if owned:
        session = build_session()
    assert session is not None
    try:
        payload = fetch_pages(session, cfg, now.year)
    finally:
        if owned:
            session.close()

    raw_bytes = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    raw_path = (output_root / "raw" / "world_bank" / cfg["indicator_code"]
                / "CHN" / f"{digest}.json")
    if not raw_path.exists():
        atomic_write(raw_path, raw_bytes)

    observations, quality = validate_and_normalize(
        payload["responses"], country_iso3="CHN", indicator_code=cfg["indicator_code"],
        earliest_year=cfg["start_year"], latest_year=now.year,
    )
    csv_path = output_root / "validated" / "macro" / "gdp" / "real" / "china.csv"
    metadata_path = output_root / "metadata" / "macro" / "gdp" / "real" / "china.json"
    manifest = {
        "asset_id": cfg["asset_id"], "dataset_contract_version": 1,
        "country_iso3": "CHN", "indicator_id": cfg["indicator_code"],
        "indicator_name": cfg["indicator_name"], "base_year": cfg["base_year"],
        "unit": cfg["unit"], "frequency": "A", "source": cfg["source"],
        "retrieved_at": retrieved_at,
        "source_lastupdated": payload["responses"][0][0].get("lastupdated"),
        "source_snapshot_sha256": digest, "raw_file": str(raw_path.resolve()),
        "validated_file": str(csv_path.resolve()), "quality_status": "passed",
        "historical_vintage_guaranteed": False, "release_timestamp_available": False,
        "quality_metrics": quality,
    }
    # Publish only after every page and observation has passed validation.
    write_csv(csv_path, observations, retrieved_at)
    atomic_write(metadata_path, (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    LOG.info("Published %d observations (%d-%d)",
             quality["validated_row_count"], quality["first_year"], quality["last_year"])
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch China's real GDP from WDI")
    parser.add_argument("--output-root", type=Path, default=MACRO_ROOT / "data")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s: %(message)s")
    try:
        manifest = run(output_root=args.output_root.expanduser().resolve())
    except (requests.RequestException, DataValidationError, ValueError, OSError) as exc:
        LOG.error("China Real GDP fetch failed: %s", exc)
        raise SystemExit(1) from exc
    print(json.dumps({
        "status": manifest["quality_status"], "asset_id": manifest["asset_id"],
        "validated_file": manifest["validated_file"],
        "rows": manifest["quality_metrics"]["validated_row_count"],
        "snapshot_sha256": manifest["source_snapshot_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
