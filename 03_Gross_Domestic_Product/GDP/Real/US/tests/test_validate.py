
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate import DataValidationError, validate_and_normalize


def row(year, value, *, iso3="USA", wb2="US", name="United States",
        indicator="NY.GDP.MKTP.KD", status=""):
    return {
        "countryiso3code": iso3,
        "country": {"id": wb2, "value": name},
        "indicator": {"id": indicator, "value": "GDP (constant 2015 US$)"},
        "date": str(year), "value": value, "obs_status": status,
    }


class ValidateTests(unittest.TestCase):
    def process(self, rows):
        return validate_and_normalize(
            [[{"page": 1, "pages": 1}, rows]],
            country_iso3="USA", indicator_code="NY.GDP.MKTP.KD",
            earliest_year=1960, latest_year=2026,
        )

    def test_sorted_and_valid(self):
        rows, meta = self.process([row(2025, 23), row(2024, 22)])
        self.assertEqual([r.year for r in rows], [2024, 2025])
        self.assertEqual(meta["validated_row_count"], 2)

    def test_missing_and_forecast(self):
        data, meta = self.process([
            row(2026, 24, status="F"), row(2025, 23), row(2024, None)
        ])
        self.assertEqual([r.year for r in data], [2025])
        self.assertEqual(meta["source_null_years"], [2024])
        self.assertEqual(meta["skipped_forecast_years"], [2026])

    def test_wrong_iso3(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 23, iso3="CHN")])

    def test_wrong_wb2(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 23, wb2="CN")])

    def test_wrong_country_name(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 23, name="China")])

    def test_wrong_indicator(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 23, indicator="NY.GDP.MKTP.CD")])

    def test_duplicate(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, 23), row(2025, 23)])

    def test_invalid_values(self):
        for val in (0, -1, True, "NaN", "inf", "bad"):
            with self.subTest(val=val), self.assertRaises(DataValidationError):
                self.process([row(2025, val)])

    def test_invalid_year(self):
        with self.assertRaises(DataValidationError):
            self.process([row("2025.0", 23)])

    def test_out_of_range(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2050, 23)])

    def test_no_valid_data(self):
        with self.assertRaises(DataValidationError):
            self.process([row(2025, None)])


if __name__ == "__main__":
    unittest.main()
