
import csv
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fetch
from test_validate import row


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        return FakeResponse(self.payloads[len(self.calls) - 1])


def payload(rows, *, page=1, pages=1, total=None):
    return [{
        "page": page, "pages": pages,
        "total": len(rows) if total is None else total,
        "sourceid": "2", "lastupdated": "2026-10-08",
    }, rows]


class FetchTests(unittest.TestCase):
    NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)

    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeSession([payload([
                row(2025, 110_000_000_000_000),
                row(2024, 105_000_000_000_000),
                row(2023, None),
            ])])
            result = fetch.run(output_root=Path(tmp), session=fake, now=self.NOW)
            with Path(result["validated_file"]).open(newline="", encoding="utf-8") as f:
                records = list(csv.DictReader(f))
            self.assertEqual([x["observation_year"] for x in records], ["2024", "2025"])
            self.assertEqual([x["country_iso3"] for x in records], ["WLD", "WLD"])
            self.assertEqual(result["quality_metrics"]["source_null_years"], [2023])
            self.assertTrue(Path(result["raw_file"]).exists())
            self.assertTrue((Path(tmp) / "metadata/macro/gdp/nominal/global.json").exists())
            self.assertIn("/WLD/", fake.calls[0][0])
            self.assertEqual(fake.calls[0][1]["date"], "1960:2026")

    def test_two_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeSession([
                payload([row(2024, 105)], page=1, pages=2, total=2),
                payload([row(2025, 110)], page=2, pages=2, total=2),
            ])
            result = fetch.run(output_root=Path(tmp), session=fake, now=self.NOW)
            self.assertEqual(result["quality_metrics"]["validated_row_count"], 2)
            self.assertEqual(len(fake.calls), 2)

    def test_incomplete_pagination(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(fetch.DataValidationError):
                fetch.run(
                    output_root=Path(tmp),
                    session=FakeSession([payload([row(2025, 110)], total=2)]),
                    now=self.NOW,
                )

    def test_bad_data_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = fetch.run(
                output_root=root, session=FakeSession([payload([row(2025, 110)])]),
                now=self.NOW,
            )
            old_csv = Path(good["validated_file"]).read_bytes()
            with self.assertRaises(fetch.DataValidationError):
                fetch.run(
                    output_root=root,
                    session=FakeSession([payload([row(2025, 110, wb2="XC")])]),
                    now=self.NOW,
                )
            self.assertEqual(Path(good["validated_file"]).read_bytes(), old_csv)


if __name__ == "__main__":
    unittest.main()
