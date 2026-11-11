
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate import DataValidationError, validate_and_normalize


def row(
    year,
    value,
    *,
    country="CHN",
    wb2="CN",
    indicator="NY.GDP.MKTP.KD",
    status="",
):
    return {
        "countryiso3code": country,
        "country": {
            "id": wb2,
            "value": "China",
        },
        "indicator": {
            "id": indicator,
            "value": "GDP (constant 2015 US$)",
        },
        "date": str(year),
        "value": value,
        "obs_status": status,
    }


class ValidateTests(unittest.TestCase):

    def process(self, rows):
        return validate_and_normalize(
            [[{"page": 1, "pages": 1}, rows]],
            country_iso3="CHN",
            indicator_code="NY.GDP.MKTP.KD",
            earliest_year=1960,
            latest_year=2026,
        )

    def test_valid_sorted(self):
        data, q = self.process([
            row(2025, 20),
            row(2024, 19),
        ])
        self.assertEqual(
            [x.year for x in data],
            [2024, 2025],
        )
        self.assertEqual(q["validated_row_count"], 2)

    def test_null_and_forecast(self):
        data, q = self.process([
            row(2024, None),
            row(2025, 20),
            row(2026, 21, status="F"),
        ])
        self.assertEqual(
            [x.year for x in data],
            [2025],
        )
        self.assertEqual(q["source_null_years"], [2024])
        self.assertEqual(q["skipped_forecast_years"], [2026])

    def test_wrong_country(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row(2025, 20, country="USA")
            ])

    def test_wrong_wb_country(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row(2025, 20, wb2="US")
            ])

    def test_wrong_indicator(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row(2025, 20, indicator="NY.GDP.MKTP.CD")
            ])

    def test_duplicate_year(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row(2025, 20),
                row(2025, 20),
            ])

    def test_invalid_value(self):
        for value in (0, -1, True, "NaN", "inf", "bad"):
            with (
                self.subTest(value=value),
                self.assertRaises(DataValidationError),
            ):
                self.process([
                    row(2025, value)
                ])

    def test_invalid_year(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row("2025.0", 20)
            ])

    def test_out_of_range(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row(2050, 20)
            ])

    def test_no_valid_data(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row(2025, None)
            ])


if __name__ == "__main__":
    unittest.main()
