
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

import calculate
from load import load_all
from test_load import create_inputs
from validate import GESValidationError


class CalculationTests(unittest.TestCase):

    def test_percentages_from_real_file_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_inputs(root)

            rows, stats = calculate.calculate_rows(
                load_all(root, 2026),
                calculated_at="2026-11-11T09:00:00Z",
            )

            found = {
                row["series_id"]: row
                for row in rows
                if row["observation_year"] == "2024"
            }

            self.assertEqual(
                found["GES_CHN"]["value"],
                "20.000000",
            )

            self.assertEqual(
                found["GES_USA"]["value"],
                "30.000000",
            )

            self.assertEqual(
                found["GES_EMU"]["value"],
                "15.000000",
            )

            self.assertEqual(
                found["GES_COMBINED"]["value"],
                "65.000000",
            )

            self.assertEqual(
                found["GES_REST"]["value"],
                "35.000000",
            )

            self.assertEqual(len(rows), 10)

            self.assertEqual(
                stats["common_year_count"],
                2,
            )

    def test_partial_years_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            values = {
                "CHN": {
                    2024: "20",
                    2025: "25",
                },
                "USA": {
                    2024: "30",
                    2025: "35",
                },
                "EMU": {
                    2024: "15",
                },
                "WLD": {
                    2024: "100",
                    2025: "120",
                },
            }

            create_inputs(root, values)

            rows, stats = calculate.calculate_rows(
                load_all(root, 2026),
                calculated_at="2026-11-11T09:00:00Z",
            )

            self.assertEqual(len(rows), 5)

            self.assertEqual(
                stats["dropped_years"],
                [2025],
            )

            self.assertEqual(
                stats["missing_by_economy"]["EMU"],
                [2025],
            )

    def test_no_common_years(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            values = {
                "CHN": {2023: "20"},
                "USA": {2024: "30"},
                "EMU": {2025: "15"},
                "WLD": {2022: "100"},
            }

            create_inputs(root, values)

            with self.assertRaises(GESValidationError):
                calculate.calculate_rows(
                    load_all(root, 2026),
                    calculated_at="2026-11-11T09:00:00Z",
                )

    def test_config_matches_contract(self):
        self.assertEqual(
            calculate.load_config()["decimal_places"],
            6,
        )


if __name__ == "__main__":
    unittest.main()
