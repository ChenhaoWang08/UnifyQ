
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate import DataValidationError, validate_and_normalize


def row(year, value, *, wb2="1W", name="World", iso3="",
        indicator="NY.GDP.MKTP.KD", status=""):
    return {
        "country": {"id": wb2, "value": name},
        "countryiso3code": iso3,
        "indicator": {"id": indicator, "value": "GDP (constant 2015 US$)"},
        "date": str(year), "value": value, "obs_status": status,
    }


class ValidateTests(unittest.TestCase):
    def check_rows(self, rows):
        return validate_and_normalize(
            [[{"page": 1, "pages": 1}, rows]],
            region_code="WLD", indicator_code="NY.GDP.MKTP.KD",
            earliest_year=1960, latest_year=2026,
        )

    def test_valid_sorted(self):
        data, info = self.check_rows([row(2025, 100), row(2024, 96, iso3="WLD")])
        self.assertEqual([x.year for x in data], [2024, 2025])
        self.assertEqual(info["validated_row_count"], 2)

    def test_null_and_forecast(self):
        data, info = self.check_rows([
            row(2026, 102, status="F"), row(2025, 100), row(2024, None)
        ])
        self.assertEqual([x.year for x in data], [2025])
        self.assertEqual(info["source_null_years"], [2024])
        self.assertEqual(info["skipped_forecast_years"], [2026])

    def test_wrong_wb_code(self):
        with self.assertRaises(DataValidationError):
            self.check_rows([row(2025, 100, wb2="XC")])

    def test_wrong_world_name(self):
        with self.assertRaises(DataValidationError):
            self.check_rows([row(2025, 100, name="Euro area")])

    def test_wrong_iso3(self):
        with self.assertRaises(DataValidationError):
            self.check_rows([row(2025, 100, iso3="USA")])

    def test_wrong_indicator(self):
        with self.assertRaises(DataValidationError):
            self.check_rows([row(2025, 100, indicator="NY.GDP.MKTP.CD")])

    def test_duplicate_year_including_null(self):
        with self.assertRaises(DataValidationError):
            self.check_rows([row(2025, None), row(2025, 100)])

    def test_invalid_gdp_values(self):
        for value in (0, -1, True, "NaN", "Infinity", "bad"):
            with self.subTest(value=value), self.assertRaises(DataValidationError):
                self.check_rows([row(2025, value)])

    def test_invalid_year(self):
        with self.assertRaises(DataValidationError):
            self.check_rows([row("2025.0", 100)])

    def test_out_of_bounds_year(self):
        with self.assertRaises(DataValidationError):
            self.check_rows([row(2050, 100)])

    def test_no_non_null_data(self):
        with self.assertRaises(DataValidationError):
            self.check_rows([row(2025, None)])

    def test_wrong_requested_series(self):
        with self.assertRaises(DataValidationError):
            validate_and_normalize(
                [[{"page": 1}, [row(2025, 100)]]],
                region_code="EMU", indicator_code="NY.GDP.MKTP.KD",
                earliest_year=1960, latest_year=2026,
            )


if __name__ == "__main__":
    unittest.main()
