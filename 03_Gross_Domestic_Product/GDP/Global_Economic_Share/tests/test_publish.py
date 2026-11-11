
import csv
import hashlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from calculate import run
from test_load import create_inputs
from validate import GESValidationError


class PublishTests(unittest.TestCase):

    NOW = datetime(
        2026, 11, 11, 9, 0,
        tzinfo=timezone.utc,
    )

    def test_end_to_end_derivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_inputs(root)

            manifest = run(
                data_root=root,
                now=self.NOW,
            )

            csv_path = Path(
                manifest["derived_file"]
            )

            self.assertTrue(
                csv_path.exists()
            )

            with csv_path.open(
                newline="",
                encoding="utf-8",
            ) as stream:
                records = list(
                    csv.DictReader(stream)
                )

            self.assertEqual(
                len(records),
                10,
            )

            self.assertEqual(
                manifest["quality_status"],
                "passed",
            )

            self.assertEqual(
                manifest["data_quality"]["common_year_count"],
                2,
            )

            self.assertEqual(
                hashlib.sha256(
                    csv_path.read_bytes()
                ).hexdigest(),
                manifest["derived_csv_sha256"],
            )

            self.assertTrue(
                (
                    root
                    / "metadata/macro/gdp/global_economic_share.json"
                ).exists()
            )

    def test_invalid_input_does_not_overwrite_good_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_inputs(root)

            manifest = run(
                data_root=root,
                now=self.NOW,
            )

            good_csv = Path(
                manifest["derived_file"]
            )

            good_bytes = good_csv.read_bytes()

            source = (
                root / "validated/macro/gdp/nominal/china.csv"
            )

            source.write_text(
                source.read_text().replace(
                    ",USD,", ",CNY,"
                )
            )

            with self.assertRaises(GESValidationError):
                run(
                    data_root=root,
                    now=self.NOW,
                )

            self.assertEqual(
                good_csv.read_bytes(),
                good_bytes,
            )


if __name__ == "__main__":
    unittest.main()
