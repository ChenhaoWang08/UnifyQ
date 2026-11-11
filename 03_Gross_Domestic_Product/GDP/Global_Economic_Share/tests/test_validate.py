
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from validate import (
    GESValidationError,
    parse_gdp_record,
    validate_share_inputs,
)


class ValidationTests(unittest.TestCase):

    def test_valid_share_inputs(self):
        validate_share_inputs(
            year=2025,
            us=Decimal(35),
            china=Decimal(25),
            eurozone=Decimal(20),
            world=Decimal(120),
        )

    def test_combined_exceeds_world(self):
        with self.assertRaises(GESValidationError):
            validate_share_inputs(
                year=2025,
                us=Decimal(35),
                china=Decimal(25),
                eurozone=Decimal(20),
                world=Decimal(75),
            )

    def test_zero_world(self):
        with self.assertRaises(GESValidationError):
            validate_share_inputs(
                year=2025,
                us=Decimal(1),
                china=Decimal(1),
                eurozone=Decimal(1),
                world=Decimal(0),
            )

    def test_nonfinite_world(self):
        with self.assertRaises(GESValidationError):
            validate_share_inputs(
                year=2025,
                us=Decimal(1),
                china=Decimal(1),
                eurozone=Decimal(1),
                world=Decimal("NaN"),
            )

    def test_invalid_timestamp(self):
        row = {
            "observation_year": "2025",
            "country_iso3": "USA",
            "indicator_id": "NY.GDP.MKTP.CD",
            "value": "123",
            "unit": "USD",
            "frequency": "A",
            "source": "World Bank WDI",
            "obs_status": "",
            "retrieved_at": "not-a-timestamp",
        }

        with self.assertRaises(GESValidationError):
            parse_gdp_record(
                row,
                economy_code="USA",
                latest_year=2026,
            )


if __name__ == "__main__":
    unittest.main()
