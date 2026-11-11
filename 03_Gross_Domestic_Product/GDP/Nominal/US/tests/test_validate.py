
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate import DataValidationError, validate_and_normalize


def row(
    year,
    value,
    *,
    country="USA",
    indicator="NY.GDP.MKTP.CD",
    status="",
):
    return {
        "countryiso3code": country,
        "indicator": {"id": indicator},
        "date": str(year),
        "value": value,
        "obs_status": status,
    }


class ValidateTests(unittest.TestCase):

    def process(self, records):
        return validate_and_normalize(
            [[{"page": 1, "pages": 1}, records]],
            country_iso3="USA",
            indicator_code="NY.GDP.MKTP.CD",
            earliest_year=1960,
            latest_year=2026,
        )

    def test_valid_and_null(self):
        series, metrics = self.process([
            row(2025, 30),
            row(2024, None),
            row(2023, 28),
        ])

        self.assertEqual(
            [s.year for s in series],
            [2023, 2025],
        )

        self.assertEqual(
            metrics["source_null_years"],
            [2024],
        )

    def test_forecast_excluded(self):
        series, metrics = self.process([
            row(2026, 31, status="F"),
            row(2025, 30),
        ])

        self.assertEqual(
            [s.year for s in series],
            [2025],
        )

        self.assertEqual(
            metrics["skipped_forecast_years"],
            [2026],
        )

    def test_wrong_country(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row(2025, 30, country="CHN")
            ])

    def test_wrong_indicator(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row(
                    2025,
                    30,
                    indicator="NY.GDP.MKTP.KD",
                )
            ])

    def test_duplicate_year(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row(2025, 30),
                row(2025, 30),
            ])

    def test_invalid_values(self):
        for v in (0, -1, "NaN", True):
            with self.subTest(value=v):
                with self.assertRaises(DataValidationError):
                    self.process([
                        row(2025, v)
                    ])

    def test_invalid_year(self):
        with self.assertRaises(DataValidationError):
            self.process([
                row("2025.0", 30)
            ])

    def test_empty(self):
        with self.assertRaises(DataValidationError):
            self.process([])


if __name__ == "__main__":
    unittest.main()
