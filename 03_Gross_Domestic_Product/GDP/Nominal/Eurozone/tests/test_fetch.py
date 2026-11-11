
import csv
import sys
import tempfile
import unittest

from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

import fetch
from test_validate import row


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append(
            (url, params, timeout)
        )

        return FakeResponse(
            self.responses[len(self.calls) - 1]
        )


def payload(rows, page=1, pages=1, total=None):
    return [
        {
            "page": page,
            "pages": pages,
            "total": (
                len(rows)
                if total is None
                else total
            ),
            "sourceid": "2",
            "lastupdated": "2026-10-08",
        },
        rows,
    ]


class FetchTests(unittest.TestCase):

    NOW = datetime(
        2026, 11, 11,
        tzinfo=timezone.utc,
    )

    def test_offline_end_to_end(self):
        with tempfile.TemporaryDirectory() as root:

            fake = FakeSession([
                payload([
                    row(2025, 18_000_000_000_000),
                    row(2024, 17_000_000_000_000),
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
            ) as stream:
                data = list(csv.DictReader(stream))

            self.assertEqual(
                [x["observation_year"] for x in data],
                ["2024", "2025"],
            )

            self.assertEqual(
                [x["country_iso3"] for x in data],
                ["EMU", "EMU"],
            )

            self.assertEqual(
                result["quality_metrics"]["source_null_years"],
                [2023],
            )

            self.assertTrue(
                Path(result["raw_file"]).exists()
            )

            self.assertTrue(
                (
                    Path(root)
                    / "metadata/macro/gdp/nominal/eurozone.json"
                ).exists()
            )

            self.assertEqual(
                fake.calls[0][1]["source"],
                2,
            )

            self.assertEqual(
                fake.calls[0][1]["date"],
                "1960:2026",
            )

            self.assertIn(
                "/EMU/",
                fake.calls[0][0],
            )

    def test_bad_data_does_not_overwrite_csv(self):
        with tempfile.TemporaryDirectory() as root:

            good = fetch.run(
                output_root=Path(root),
                session=FakeSession([
                    payload([
                        row(2025, 18)
                    ])
                ]),
                now=self.NOW,
            )

            old_bytes = Path(
                good["validated_file"]
            ).read_bytes()

            with self.assertRaises(
                fetch.DataValidationError
            ):
                fetch.run(
                    output_root=Path(root),
                    session=FakeSession([
                        payload([
                            row(
                                2025,
                                18,
                                name="European Union",
                            )
                        ])
                    ]),
                    now=self.NOW,
                )

            self.assertEqual(
                Path(
                    good["validated_file"]
                ).read_bytes(),
                old_bytes,
            )

    def test_two_pages(self):
        with tempfile.TemporaryDirectory() as root:

            fake = FakeSession([
                payload(
                    [row(2024, 17)],
                    page=1,
                    pages=2,
                    total=2,
                ),
                payload(
                    [row(2025, 18)],
                    page=2,
                    pages=2,
                    total=2,
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

            self.assertEqual(
                len(fake.calls),
                2,
            )

    def test_incomplete_pagination(self):
        with tempfile.TemporaryDirectory() as root:

            fake = FakeSession([
                payload(
                    [row(2025, 18)],
                    total=2,
                )
            ])

            with self.assertRaises(
                fetch.DataValidationError
            ):
                fetch.run(
                    output_root=Path(root),
                    session=fake,
                    now=self.NOW,
                )


if __name__ == "__main__":
    unittest.main()
