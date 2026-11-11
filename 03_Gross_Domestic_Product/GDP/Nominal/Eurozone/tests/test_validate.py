
import sys
import unittest

from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from validate import (
    DataValidationError,
    validate_and_normalize,
)


def row(
    year,
    value,
    *,
    wb2="XC",
    name="Euro area",
    iso3="",
    indicator="NY.GDP.MKTP.CD",
    status="",
):
    return {
        "country": {
            "id": wb2,
            "value": name,
        },
        "countryiso3code": iso3,
        "indicator": {
            "id": indicator,
        },
        "date": str(year),
        "value": value,
        "obs_status": status,
    }


class ValidateTests(unittest.TestCase):

    def process(self, rows):
        return validate_and_normalize(
            [[
                {
                    "page": 1,
                    "pages": 1,
                },
                rows,
            ]],
            region_code="EMU",
            indicator_code="NY.GDP.MKTP.CD",
            earliest_year=1960,
            latest_year=2026,
        )

    def test_aggregate_code_empty_and_emu(self):
        obs, quality = self.process([
            row(
                2025,
                18_000_000_000_000,
                iso3="",
            ),
            row(
                2024,
                17_000_000_000_000,
                iso3="EMU",
            ),
        ])

        self.assertEqual(
            [x.year for x in obs],
            [2024, 2025],
        )

        self.assertEqual(
            quality["validated_row_count"],
            2,
        )

    def test_null_and_forecast(self):
        obs, quality = self.process([
            row(
                2026,
                19,
                status="F",
            ),
            row(
                2025,
                18,
            ),
            row(
                2024,
                None,
            ),
        ])

        self.assertEqual(
            [o.year for o in obs],
            [2025],
        )

        self.assertEqual(
            quality["source_null_years"],
            [2024],
        )

        self.assertEqual(
            quality["skipped_forecast_years"],
            [2026],
        )

    def test_wrong_region_code(self):
        with self.assertRaises(
            DataValidationError
        ):
            self.process([
                row(
                    2025,
                    18,
                    wb2="EU",
                )
            ])

    def test_wrong_aggregate_name(self):
        with self.assertRaises(
            DataValidationError
        ):
            self.process([
                row(
                    2025,
                    18,
                    name="European Union",
                )
            ])

    def test_wrong_iso3(self):
        with self.assertRaises(
            DataValidationError
        ):
            self.process([
                row(
                    2025,
                    18,
                    iso3="USA",
                )
            ])

    def test_wrong_indicator(self):
        with self.assertRaises(
            DataValidationError
        ):
            self.process([
                row(
                    2025,
                    18,
                    indicator="NY.GDP.MKTP.KD",
                )
            ])

    def test_duplicate(self):
        with self.assertRaises(
            DataValidationError
        ):
            self.process([
                row(2025, 18),
                row(2025, 18),
            ])

    def test_invalid_values(self):
        for value in (
            0,
            -5,
            True,
            "NaN",
            "inf",
            "abc",
        ):
            with self.subTest(value=value):
                with self.assertRaises(
                    DataValidationError
                ):
                    self.process([
                        row(2025, value)
                    ])

    def test_invalid_year(self):
        with self.assertRaises(
            DataValidationError
        ):
            self.process([
                row("2025.0", 18)
            ])

    def test_empty_data(self):
        with self.assertRaises(
            DataValidationError
        ):
            self.process([])


if __name__ == "__main__":
    unittest.main()
