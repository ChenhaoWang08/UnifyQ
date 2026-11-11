
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
        "page": page,
        "pages": pages,
        "total": len(rows) if total is None else total,
        "sourceid": "2",
        "lastupdated": "2026-10-08",
    }, rows]


class FetchTests(unittest.TestCase):
    NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)

    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeSession([
                payload([
                    row(2025, 20),
                    row(2024, 19),
                    row(2023, None),
                ])
            ])
            result = fetch.run(
                output_root=Path(tmp),
                session=fake,
                now=self.NOW,
            )

            with Path(result["validated_file"]).open(
                newline="", encoding="utf-8"
            ) as f:
                records = list(csv.DictReader(f))

            self.assertEqual(
                [r["observation_year"] for r in records],
                ["2024", "2025"],
            )
            self.assertEqual(
                [r["unit"] for r in records],
                ["constant_2015_USD"] * 2,
            )
            self.assertEqual(
                [r["indicator_id"] for r in records],
                ["NY.GDP.MKTP.KD"] * 2,
            )
            self.assertEqual(
                result["quality_metrics"]["source_null_years"],
                [2023],
            )
            self.assertEqual(result["base_year"], 2015)
            self.assertTrue(Path(result["raw_file"]).exists())
            self.assertTrue(
                (
                    Path(tmp)
                    / "metadata/macro/gdp/real/china.json"
                ).exists()
            )
            self.assertIn("/CHN/", fake.calls[0][0])
            self.assertIn("NY.GDP.MKTP.KD", fake.calls[0][0])
            self.assertEqual(
                fake.calls[0][1]["date"],
                "1960:2026",
            )

    def test_pagination(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeSession([
                payload([row(2024, 19)], page=1, pages=2, total=2),
                payload([row(2025, 20)], page=2, pages=2, total=2),
            ])
            result = fetch.run(
                output_root=Path(tmp),
                session=fake,
                now=self.NOW,
            )
            self.assertEqual(
                result["quality_metrics"]["validated_row_count"],
                2,
            )
            self.assertEqual(len(fake.calls), 2)

    def test_incomplete_pagination(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(fetch.DataValidationError):
                fetch.run(
                    output_root=Path(tmp),
                    session=FakeSession([
                        payload([row(2025, 20)], total=2)
                    ]),
                    now=self.NOW,
                )

    def test_bad_data_preserves_last_good_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = fetch.run(
                output_root=root,
                session=FakeSession([
                    payload([row(2025, 20)])
                ]),
                now=self.NOW,
            )
            previous = Path(good["validated_file"]).read_bytes()

            with self.assertRaises(fetch.DataValidationError):
                fetch.run(
                    output_root=root,
                    session=FakeSession([
                        payload([row(2025, 20, country="USA")])
                    ]),
                    now=self.NOW,
                )

            self.assertEqual(
                Path(good["validated_file"]).read_bytes(),
                previous,
            )

    def test_raw_deduplicated_by_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            first = fetch.run(
                output_root=root,
                session=FakeSession([
                    payload([row(2025, 20)])
                ]),
                now=self.NOW,
            )
            second = fetch.run(
                output_root=root,
                session=FakeSession([
                    payload([row(2025, 20)])
                ]),
                now=self.NOW,
            )

            self.assertEqual(
                first["source_snapshot_sha256"],
                second["source_snapshot_sha256"],
            )
            self.assertEqual(
                len(list((
                    root / "raw/world_bank/NY.GDP.MKTP.KD/CHN"
                ).glob("*.json"))),
                1,
            )

    def test_config_has_real_gdp_indicator(self):
        cfg = fetch.load_config()
        self.assertEqual(cfg["indicator_code"], "NY.GDP.MKTP.KD")
        self.assertEqual(cfg["base_year"], 2015)


if __name__ == "__main__":
    unittest.main()
