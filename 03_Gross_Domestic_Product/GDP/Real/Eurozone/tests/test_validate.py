
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate import DataValidationError, validate_and_normalize


def row(year, value, *, wb2="XC", name="Euro area", iso3="",
        indicator="NY.GDP.MKTP.KD", status=""):
    return {
        "country": {"id": wb2, "value": name},
        "countryiso3code": iso3,
        "indicator": {"id": indicator, "value": "GDP (constant 2015 US$)"},
        "date": str(year),
        "value": value,
        "obs_status": status,
    }


class ValidateTests(unittest.TestCase):
    def process(self, rows):
        return validate_and_normalize(
            [[{"page": 1, "pages": 1}, rows]],
            region_code="EMU", indicator_code="NY.GDP.MKTP.KD",
            earliest_year=1960, latest_year=2026,
        )

    def test_valid_sorted_and_region_codes(self):
        obs, quality = self.process([
            row(2025, 15_000_000_000_000),
            row(2024, 14_000_000_000_000, iso3="EMU"),
        ])
        self.assertEqual([x.year for x in obs], [2024, 2025])
        self.assertEqual(quality["validated_row_count"], 2)

    def test_null_and_forecast(self):
        obs, quality = self.process([
            row(2026, 16, status="F"), row(2025, 15), row(2024, None),
        ])
        self.assertEqual([x.year for x in obs], [2025])
        self.assertEqual(quality["source_null_years"], [2024])
        self.assertEqual(quality["skipped_forecast_years"], [2026])

    def test_wrong_region_code(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 15, wb2="EU")])

    def test_wrong_region_name(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 15, name="European Union")])

    def test_wrong_countryiso3(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 15, iso3="USA")])

    def test_wrong_indicator(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 15, indicator="NY.GDP.MKTP.CD")])

    def test_duplicate_year(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 15), row(2025, 15)])

    def test_invalid_values(self):
        for value in (0, -1, True, "NaN", "inf", "bad"):
            with self.subTest(value=value):
                with self.assertRaises(DataValidationError):
                    self.process([row(2025, value)])

    def test_invalid_year(self):
        with self.assertRaises(DataValidationError):
            self.process([row("2025.0", 15)])

    def test_no_valid_data(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, None)])


if __name__ == "__main__":
    unittest.main()
