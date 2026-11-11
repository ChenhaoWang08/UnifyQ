
# Euro area Nominal GDP Collector (EMU)

**Asset:** `macro.gdp.nominal.eurozone`

**Provider:** World Bank, World Development Indicators (WDI)

**Series:** `NY.GDP.MKTP.CD`

**Geography:** Euro area aggregate (`EMU`, WB-2 `XC`)

**Frequency:** Annual (`A`)

**Unit:** Current USD

## Purpose

Fetch the annual Euro area nominal GDP aggregate
published by the World Bank.

Store raw snapshots, validate all observations,
and publish the same nine-column CSV contract
used by UnifyQ's China and US GDP collectors.

This asset does not recompute eurozone GDP
by summing member economies.

The World Bank aggregate is the data source.

## Data Source

Provider: World Bank WDI

Indicator: NY.GDP.MKTP.CD

Regional Aggregate: EMU

Internal World Bank Code: XC

API:

https://api.worldbank.org/v2/country/EMU/indicator/NY.GDP.MKTP.CD?format=json

No API key required.

## Installation

Run from UnifyQ/macro:

```bash
python3 -m pip install -r 03_Gross_Domestic_Product/GDP/Nominal/Eurozone/requirements.txt
```

## Tests

```bash
python3 -m unittest discover -s 03_Gross_Domestic_Product/GDP/Nominal/Eurozone/tests -v
```

## Execution

```bash
python3 03_Gross_Domestic_Product/GDP/Nominal/Eurozone/fetch.py
```

## Data Pipeline

1. Request World Bank API data.
2. Handle transient errors with retry and backoff.
3. Retrieve all API pages.
4. Verify pagination completeness.
5. Save the original JSON response.
6. Validate all GDP observations.
7. Reject invalid or duplicate data.
8. Publish validated annual GDP to CSV.
9. Generate metadata and quality metrics.

## Output Files

### Raw Data

data/raw/world_bank/NY.GDP.MKTP.CD/EMU/

### Validated Data

data/validated/macro/gdp/nominal/eurozone.csv

### Metadata

data/metadata/macro/gdp/nominal/eurozone.json

## CSV Schema

observation_year,
country_iso3,
indicator_id,
value,
unit,
frequency,
source,
obs_status,
retrieved_at

The CSV schema is identical to the China and US
nominal GDP collectors.

The country_iso3 field contains EMU for compatibility.

EMU is a regional aggregate code, not an ISO country code.

## Quality Rules

- Verify Euro area aggregate code XC.
- Verify aggregate name Euro area.
- Verify GDP indicator ID.
- Reject malformed years.
- Reject duplicate observations.
- Reject zero or negative GDP.
- Reject non-finite GDP values.
- Track missing observations.
- Exclude explicitly forecast observations.
- Validate API pagination completeness.
- Preserve raw JSON on validation failure.
- Never publish invalid GDP data.

## Historical Data Limitations

World Bank GDP observations may be revised.

The observation year is not the original release date.

The retrieval timestamp is not the release timestamp.

Point-in-time historical vintages are not guaranteed.

## Future Integration

The validated Eurozone GDP series can be used by:

- GDP Global Economic Share
- GDP International Comparisons
- PTM Macro Dashboard

Asset ID:

macro.gdp.nominal.eurozone

## Important Note

Eurozone GDP must not be added to individual
member-country GDP totals when calculating world GDP.

This would double-count economic activity.

## Status

Independent collector implementation completed.

Offline unit tests passed.

Live World Bank collection and Dagster integration
remain pending.
