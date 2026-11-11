
import csv
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fetch


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        return FakeResponse(
            self.payloads[len(self.calls) - 1]
        )


def row(year, value, country="USA"):
    return {
        "countryiso3code": country,
        "indicator": {"id": "NY.GDP.MKTP.CD"},
        "date": str(year),
        "value": value,
        "obs_status": "",
    }


def payload(rows, page=1, pages=1):
    return [
        {
            "page": page,
            "pages": pages,
            "lastupdated": "2026-11-01",
        },
        rows,
    ]


class FetchTests(unittest.TestCase):

    NOW = datetime(
        2026, 11, 11,
        tzinfo=timezone.utc
    )

    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as root:

            fake = FakeSession([
                payload([
                    row(2025, 30_000_000_000_000),
                    row(2024, 29_000_000_000_000),
                    row(2023, None),
                ])
            ])

            result = fetch.run(
                output_root=Path(root),
                session=fake,
                now=self.NOW,
            )

            with Path(result["validated_file"]).open(
                newline="",
                encoding="utf-8",
            ) as f:
                entries = list(csv.DictReader(f))

            self.assertEqual(len(entries), 2)
            self.assertEqual(
                entries[0]["country_iso3"],
                "USA",
            )
            self.assertEqual(
                entries[0]["observation_year"],
                "2024",
            )
            self.assertEqual(
                entries[1]["value"],
                "30000000000000",
            )

            self.assertEqual(
                result["quality_metrics"]["source_null_years"],
                [2023],
            )

            self.assertTrue(
                Path(result["raw_file"]).exists()
            )

            self.assertEqual(
                fake.calls[0][1]["date"],
                "1960:2026",
            )

    def test_validation_failure_does_not_overwrite_csv(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)

            good = fetch.run(
                output_root=base,
                session=FakeSession([
                    payload([row(2025, 30)])
                ]),
                now=self.NOW,
            )

            file = Path(good["validated_file"])
            before = file.read_bytes()

            with self.assertRaises(fetch.DataValidationError):
                fetch.run(
                    output_root=base,
                    session=FakeSession([
                        payload([
                            row(2025, 30, "CHN")
                        ])
                    ]),
                    now=self.NOW,
                )

            self.assertEqual(
                file.read_bytes(),
                before,
            )

    def test_pagination(self):
        with tempfile.TemporaryDirectory() as root:

            fake = FakeSession([
                payload(
                    [row(2024, 29)],
                    page=1,
                    pages=2,
                ),
                payload(
                    [row(2025, 30)],
                    page=2,
                    pages=2,
                ),
            ])

            result = fetch.run(
                output_root=Path(root),
                session=fake,
                now=self.NOW,
            )

            self.assertEqual(
                result["quality_metrics"]["validated_row_count"],
                2,
            )

            self.assertEqual(len(fake.calls), 2)

            self.assertEqual(
                fake.calls[1][1]["page"],
                2,
            )


if __name__ == "__main__":
    unittest.main()
