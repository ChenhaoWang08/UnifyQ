
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate import DataValidationError, validate_and_normalize


def sample_row(year, value, status=""):
    return {
        "countryiso3code": "CHN",
        "country": {"id": "CN", "value": "China"},
        "indicator": {
            "id": "NY.GDP.MKTP.CD",
            "value": "GDP (current US$)",
        },
        "date": str(year),
        "value": value,
        "obs_status": status,
    }


class QualityGateTests(unittest.TestCase):

    def validate(self, rows):
        return validate_and_normalize(
            [[{"page": 1, "pages": 1}, rows]],
            country_iso3="CHN",
            indicator_code="NY.GDP.MKTP.CD",
            earliest_year=1960,
            latest_year=2026,
        )

    def test_success_and_null_not_imputed(self):
        obs, metrics = self.validate([
            sample_row(2025, 19_000_000_000_000),
            sample_row(2024, None),
            sample_row(2023, 18_000_000_000_000),
        ])

        self.assertEqual(
            [r.year for r in obs],
            [2023, 2025],
        )

        self.assertEqual(
            metrics["source_null_years"],
            [2024],
        )

        self.assertEqual(
            str(obs[-1].value_usd),
            "19000000000000",
        )

    def test_forecast_excluded(self):
        obs, metrics = self.validate([
            sample_row(2026, 20, "F"),
            sample_row(2025, 19),
        ])

        self.assertEqual(
            [r.year for r in obs],
            [2025],
        )

        self.assertEqual(
            metrics["skipped_forecast_years"],
            [2026],
        )

    def test_duplicate_year_rejected(self):
        with self.assertRaises(DataValidationError):
            self.validate([
                sample_row(2025, 19),
                sample_row(2025, 19),
            ])

    def test_wrong_country_rejected(self):
        bad = sample_row(2025, 19)
        bad["countryiso3code"] = "USA"

        with self.assertRaises(DataValidationError):
            self.validate([bad])

    def test_negative_and_nan_rejected(self):
        for value in [-1, "NaN", 0]:
            with self.subTest(value=value):
                with self.assertRaises(DataValidationError):
                    self.validate([
                        sample_row(2025, value)
                    ])

    def test_empty_data_rejected(self):
        with self.assertRaises(DataValidationError):
            self.validate([
                sample_row(2025, None)
            ])


if __name__ == "__main__":
    unittest.main()
