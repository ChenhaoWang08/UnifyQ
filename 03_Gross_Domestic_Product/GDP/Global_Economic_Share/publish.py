
"""Atomically publish GES rows and a metadata manifest."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any


CSV_COLUMNS = [
    "observation_year",
    "series_id",
    "value",
    "unit",
    "frequency",
    "source",
    "numerator_gdp_usd",
    "world_gdp_usd",
    "calculated_at",
]


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=".tmp-",
            delete=False,
        ) as out:

            temp = Path(out.name)
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())

        os.replace(temp, path)

    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def publish(
    *,
    data_root: Path,
    rows: list[dict[str, str]],
    manifest: dict[str, Any],
) -> dict[str, Any]:

    if not rows:
        raise ValueError(
            "Refusing to publish an empty GES dataset"
        )

    output = io.StringIO(newline="")

    writer = csv.DictWriter(
        output,
        fieldnames=CSV_COLUMNS,
    )

    writer.writeheader()
    writer.writerows(rows)

    csv_bytes = output.getvalue().encode("utf-8")

    csv_sha = hashlib.sha256(
        csv_bytes
    ).hexdigest()

    csv_path = (
        data_root
        / "derived"
        / "macro"
        / "gdp"
        / "global_economic_share"
        / "global_economic_share.csv"
    )

    manifest_path = (
        data_root
        / "metadata"
        / "macro"
        / "gdp"
        / "global_economic_share.json"
    )

    result = {
        **manifest,
        "derived_csv_sha256": csv_sha,
        "derived_file": str(
            csv_path.resolve()
        ),
        "quality_status": "passed",
    }

    atomic_write(
        csv_path,
        csv_bytes,
    )

    atomic_write(
        manifest_path,
        (
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ) + "\n"
        ).encode("utf-8"),
    )

    return result
