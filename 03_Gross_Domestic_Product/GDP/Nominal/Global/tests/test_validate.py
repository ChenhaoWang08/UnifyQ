
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate import DataValidationError, validate_and_normalize


def row(year, value, *, wb2="1W", name="World", iso3="",
        indicator="NY.GDP.MKTP.CD", status=""):
    return {
        "country": {"id": wb2, "value": name},
        "countryiso3code": iso3,
        "indicator": {"id": indicator},
        "date": str(year), "value": value, "obs_status": status,
    }


class ValidateTests(unittest.TestCase):
    def process(self, rows):
        return validate_and_normalize(
            [[{"page": 1, "pages": 1}, rows]],
            region_code="WLD", indicator_code="NY.GDP.MKTP.CD",
            earliest_year=1960, latest_year=2026,
        )

    def test_valid_and_sorted(self):
        observations, metrics = self.process([
            row(2025, 110_000_000_000_000), row(2024, 105_000_000_000_000, iso3="WLD")
        ])
        self.assertEqual([r.year for r in observations], [2024, 2025])
        self.assertEqual(metrics["validated_row_count"], 2)

    def test_null_and_forecast(self):
        observations, metrics = self.process([
            row(2026, 115, status="F"), row(2025, 110), row(2024, None)
        ])
        self.assertEqual([r.year for r in observations], [2025])
        self.assertEqual(metrics["source_null_years"], [2024])
        self.assertEqual(metrics["skipped_forecast_years"], [2026])

    def test_wrong_wb2(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 110, wb2="XC")])

    def test_wrong_name(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 110, name="Euro area")])

    def test_wrong_iso3(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 110, iso3="USA")])

    def test_wrong_indicator(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 110, indicator="NY.GDP.MKTP.KD")])

    def test_duplicate(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 110), row(2025, 110)])

    def test_invalid_values(self):
        for value in (0, -1, True, "NaN", "inf", "bad"):
            with self.subTest(value=value):
                with self.assertRaises(DataValidationError):
                    self.process([row(2025, value)])

    def test_invalid_year(self):
        with self.assertRaises(DataValidationError):
            self.process([row("2025.0", 110)])

    def test_empty(self):
        with self.assertRaises(DataValidationError):
            self.process([])


if __name__ == "__main__":
    unittest.main()
