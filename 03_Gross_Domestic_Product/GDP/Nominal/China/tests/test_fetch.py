
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fetch


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        return FakeResponse(self.data)


class CollectorTests(unittest.TestCase):

    @staticmethod
    def sample():
        return [
            {
                "page": 1,
                "pages": 1,
                "per_page": 20000,
                "total": 3,
                "lastupdated": "2026-10-01",
            },
            [
                {
                    "countryiso3code": "CHN",
                    "indicator": {"id": "NY.GDP.MKTP.CD"},
                    "date": "2025",
                    "value": 19500000000000,
                    "obs_status": "",
                },
                {
                    "countryiso3code": "CHN",
                    "indicator": {"id": "NY.GDP.MKTP.CD"},
                    "date": "2024",
                    "value": 18000000000000,
                    "obs_status": "",
                },
                {
                    "countryiso3code": "CHN",
                    "indicator": {"id": "NY.GDP.MKTP.CD"},
                    "date": "2023",
                    "value": None,
                    "obs_status": "",
                },
            ],
        ]

    def test_end_to_end_offline(self):
        with tempfile.TemporaryDirectory() as temp:
            fake = FakeSession(self.sample())

            manifest = fetch.run(
                output_root=Path(temp),
                session=fake,
                now=datetime(2026, 11, 11, tzinfo=timezone.utc),
            )

            output = Path(manifest["validated_file"])

            self.assertTrue(output.exists())

            self.assertIn(
                "2024,CHN,NY.GDP.MKTP.CD,18000000000000,USD,A",
                output.read_text(),
            )

            self.assertEqual(
                manifest["quality_metrics"]["validated_row_count"],
                2,
            )

            self.assertEqual(
                manifest["quality_metrics"]["source_null_years"],
                [2023],
            )

            self.assertEqual(
                fake.calls[0][1]["date"],
                "1960:2026",
            )

            self.assertTrue(Path(manifest["raw_file"]).exists())
            self.assertFalse(manifest["historical_vintage_guaranteed"])

            again = fetch.run(
                output_root=Path(temp),
                session=FakeSession(self.sample()),
                now=datetime(2026, 11, 12, tzinfo=timezone.utc),
            )

            self.assertEqual(
                again["source_snapshot_sha256"],
                manifest["source_snapshot_sha256"],
            )

            self.assertEqual(
                len(list(
                    (
                        Path(temp)
                        / "raw"
                        / "world_bank"
                        / "NY.GDP.MKTP.CD"
                        / "CHN"
                    ).glob("*.json")
                )),
                1,
            )

    def test_bad_api_response_does_not_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            fake = FakeSession(self.sample())

            manifest = fetch.run(
                output_root=Path(temp),
                session=fake,
                now=datetime(2026, 11, 11, tzinfo=timezone.utc),
            )

            output = Path(manifest["validated_file"])
            content = output.read_bytes()

            bad = self.sample()
            bad[1][0]["countryiso3code"] = "USA"

            with self.assertRaises(fetch.DataValidationError):
                fetch.run(
                    output_root=Path(temp),
                    session=FakeSession(bad),
                    now=datetime(2026, 11, 12, tzinfo=timezone.utc),
                )

            self.assertEqual(
                output.read_bytes(),
                content,
            )


if __name__ == "__main__":
    unittest.main()
