
"""Fixture and input-integrity tests; no real user data is touched."""
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from load import load_all
from validate import CSV_COLUMNS, GESValidationError


NAMES = {
    "CHN": "china",
    "USA": "us",
    "EMU": "eurozone",
    "WLD": "global",
}

AMOUNTS = {
    "CHN": {2024: "20", 2025: "25"},
    "USA": {2024: "30", 2025: "35"},
    "EMU": {2024: "15", 2025: "20"},
    "WLD": {2024: "100", 2025: "120"},
}


def create_inputs(root: Path, values=None):
    values = values or AMOUNTS

    for code, name in NAMES.items():
        rows = values[code]

        raw_file = (
            root / "raw" / "world_bank"
            / "NY.GDP.MKTP.CD"
            / code / "snapshot.json"
        )

        raw_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        raw_file.write_text(
            json.dumps({
                "economy": code,
                "values": rows,
            }),
            encoding="utf-8",
        )

        snapshot_hash = hashlib.sha256(
            raw_file.read_bytes()
        ).hexdigest()

        csv_file = (
            root / "validated" / "macro"
            / "gdp" / "nominal"
            / f"{name}.csv"
        )

        csv_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with csv_file.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as out:

            writer = csv.DictWriter(
                out,
                fieldnames=CSV_COLUMNS,
            )

            writer.writeheader()

            for year, amount in sorted(rows.items()):
                writer.writerow({
                    "observation_year": year,
                    "country_iso3": code,
                    "indicator_id": "NY.GDP.MKTP.CD",
                    "value": amount,
                    "unit": "USD",
                    "frequency": "A",
                    "source": "World Bank WDI",
                    "obs_status": "",
                    "retrieved_at": "2026-11-11T08:47:25Z",
                })

        metadata = {
            "quality_status": "passed",
            "asset_id": f"macro.gdp.nominal.{name}",
            "indicator_id": "NY.GDP.MKTP.CD",
            "unit": "USD",
            "frequency": "A",
            "country_iso3": (
                code if code in {"CHN", "USA"} else None
            ),
            "region_code": (
                code if code in {"EMU", "WLD"} else None
            ),
            "validated_file": str(
                csv_file.resolve()
            ),
            "raw_file": str(
                raw_file.resolve()
            ),
            "source_snapshot_sha256": snapshot_hash,
            "retrieved_at": "2026-11-11T08:47:25Z",
            "source_lastupdated": "2026-10-08",
            "quality_metrics": {
                "validated_row_count": len(rows)
            },
        }

        metadata_file = (
            root / "metadata" / "macro"
            / "gdp" / "nominal"
            / f"{name}.json"
        )

        metadata_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        metadata_file.write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )


class LoadTests(unittest.TestCase):

    def test_load_four_valid_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_inputs(root)

            inputs = load_all(root, 2026)

            self.assertEqual(
                set(inputs),
                set(NAMES),
            )

            self.assertEqual(
                str(inputs["CHN"].values[2025]),
                "25",
            )

    def test_missing_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_inputs(root)

            (
                root / "validated/macro/gdp/nominal/us.csv"
            ).unlink()

            with self.assertRaises(GESValidationError):
                load_all(root, 2026)

    def test_manifest_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_inputs(root)

            path = (
                root / "metadata/macro/gdp/nominal/china.json"
            )

            obj = json.loads(
                path.read_text()
            )

            obj["quality_status"] = "failed"

            path.write_text(
                json.dumps(obj)
            )

            with self.assertRaises(GESValidationError):
                load_all(root, 2026)

    def test_raw_snapshot_tampered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_inputs(root)

            path = (
                root
                / "raw/world_bank/NY.GDP.MKTP.CD/CHN/snapshot.json"
            )

            path.write_text("modified")

            with self.assertRaises(GESValidationError):
                load_all(root, 2026)

    def test_wrong_currency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_inputs(root)

            path = (
                root / "validated/macro/gdp/nominal/us.csv"
            )

            path.write_text(
                path.read_text().replace(
                    ",USD,", ",EUR,"
                )
            )

            with self.assertRaises(GESValidationError):
                load_all(root, 2026)

    def test_duplicate_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_inputs(root)

            path = (
                root / "validated/macro/gdp/nominal/us.csv"
            )

            lines = path.read_text().splitlines()

            path.write_text(
                "\n".join(
                    lines + [lines[-1]]
                ) + "\n"
            )

            with self.assertRaises(GESValidationError):
                load_all(root, 2026)


if __name__ == "__main__":
    unittest.main()
