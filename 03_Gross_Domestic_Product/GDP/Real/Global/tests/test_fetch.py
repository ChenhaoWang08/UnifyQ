
import csv
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fetch


def row(year, value, *, wb2="1W", indicator="NY.GDP.MKTP.KD"):
    return {
        "country": {"id": wb2, "value": "World"},
        "countryiso3code": "",
        "indicator": {"id": indicator},
        "date": str(year), "value": value, "obs_status": "",
    }


def payload(rows, *, page=1, pages=1, total=None):
    return [{
        "page": page, "pages": pages,
        "total": len(rows) if total is None else total,
        "sourceid": "2", "lastupdated": "2026-10-08",
    }, rows]


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def raise_for_status(self):
        pass

    def json(self):
        return self.value


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        return FakeResponse(self.pages[len(self.calls) - 1])


class FetchTests(unittest.TestCase):
    NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)

    def test_end_to_end_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeSession([payload([
                row(2025, 100_000_000_000_000),
                row(2024, 96_000_000_000_000),
                row(2023, None),
            ])])
            result = fetch.run(output_root=Path(tmp), session=fake, now=self.NOW)
            with Path(result["validated_file"]).open(newline="", encoding="utf-8") as f:
                csv_rows = list(csv.DictReader(f))
            self.assertEqual([r["observation_year"] for r in csv_rows], ["2024", "2025"])
            self.assertEqual({r["country_iso3"] for r in csv_rows}, {"WLD"})
            self.assertEqual({r["indicator_id"] for r in csv_rows}, {"NY.GDP.MKTP.KD"})
            self.assertEqual({r["unit"] for r in csv_rows}, {"constant_2015_USD"})
            self.assertEqual(result["base_year"], 2015)
            self.assertEqual(result["quality_metrics"]["source_null_years"], [2023])
            self.assertTrue(Path(result["raw_file"]).exists())
            self.assertTrue((Path(tmp) / "metadata/macro/gdp/real/global.json").exists())
            self.assertEqual(fake.calls[0][1]["date"], "1960:2026")
            self.assertEqual(fake.calls[0][1]["source"], 2)
            self.assertIn("/WLD/", fake.calls[0][0])

    def test_two_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeSession([
                payload([row(2024, 96)], page=1, pages=2, total=2),
                payload([row(2025, 100)], page=2, pages=2, total=2),
            ])
            result = fetch.run(output_root=Path(tmp), session=fake, now=self.NOW)
            self.assertEqual(result["quality_metrics"]["validated_row_count"], 2)
            self.assertEqual(len(fake.calls), 2)

    def test_incomplete_pagination_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(fetch.DataValidationError):
                fetch.run(
                    output_root=Path(tmp),
                    session=FakeSession([payload([row(2025, 100)], total=2)]),
                    now=self.NOW,
                )

    def test_invalid_response_preserves_last_good_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = fetch.run(
                output_root=root,
                session=FakeSession([payload([row(2025, 100)])]), now=self.NOW,
            )
            csv_file = Path(first["validated_file"])
            original = csv_file.read_bytes()
            with self.assertRaises(fetch.DataValidationError):
                fetch.run(
                    output_root=root,
                    session=FakeSession([payload([row(2025, 100, wb2="XC")])]),
                    now=self.NOW,
                )
            self.assertEqual(csv_file.read_bytes(), original)

    def test_raw_snapshot_hash_deduplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = [fetch.run(
                output_root=root,
                session=FakeSession([payload([row(2025, 100)])]), now=self.NOW,
            ) for _ in range(2)]
            self.assertEqual(runs[0]["source_snapshot_sha256"], runs[1]["source_snapshot_sha256"])
            snapshots = list((root / "raw/world_bank/NY.GDP.MKTP.KD/WLD").glob("*.json"))
            self.assertEqual(len(snapshots), 1)

    def test_config_matches_world_real_gdp(self):
        cfg = fetch.load_config()
        self.assertEqual(cfg["region_code"], "WLD")
        self.assertEqual(cfg["region_wb2_code"], "1W")
        self.assertEqual(cfg["indicator_code"], "NY.GDP.MKTP.KD")
        self.assertEqual(cfg["base_year"], 2015)


if __name__ == "__main__":
    unittest.main()
