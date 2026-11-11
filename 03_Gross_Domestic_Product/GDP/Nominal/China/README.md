
# China Nominal GDP Collector

**Asset ID:** `macro.gdp.nominal.china`  
**Source:** World Bank WDI  
**Indicator:** `NY.GDP.MKTP.CD`  
**Country:** China (`CHN`)  
**Frequency:** Annual  
**Unit:** Current USD

## Purpose

This module fetches China's annual nominal GDP from the World Bank API.

It stores the original API response, validates historical observations, and publishes standardized data for the UnifyQ Macro Pipeline.

The module does not calculate Global Economic Share directly.

## Data Pipeline

1. Fetch World Bank GDP data.
2. Save the original JSON response.
3. Validate country, indicator, year, and GDP value.
4. Exclude missing and explicitly forecast observations.
5. Publish validated historical GDP data.
6. Generate a metadata manifest.
7. Make validated data available to downstream analytical modules.

## API

Provider: World Bank

Indicator Code: NY.GDP.MKTP.CD

API Endpoint:

https://api.worldbank.org/v2/country/CHN/indicator/NY.GDP.MKTP.CD?format=json&per_page=20000

No API key is required.

## Installation

Run from the UnifyQ repository root:

```bash
python3 -m pip install -r 03_Gross_Domestic_Product/GDP/Nominal/China/requirements.txt
```

## Execution

```bash
python3 03_Gross_Domestic_Product/GDP/Nominal/China/fetch.py
```

## Testing

```bash
python3 -m unittest discover -s 03_Gross_Domestic_Product/GDP/Nominal/China/tests -v
```

## Output Files

### Raw Data

`data/raw/world_bank/NY.GDP.MKTP.CD/CHN/`

Stores the original API responses as JSON files.

### Validated Data

`data/validated/macro/gdp/nominal/china.csv`

Contains validated annual GDP observations.

### Metadata

`data/metadata/macro/gdp/nominal/china.json`

Stores collection details, source information, and quality metrics.

## CSV Schema

- observation_year
- country_iso3
- indicator_id
- value
- unit
- frequency
- source
- obs_status
- retrieved_at

## Data Quality Rules

- Reject incorrect country codes.
- Reject incorrect indicator IDs.
- Reject duplicate valid observations.
- Reject negative, zero, and non-finite GDP values.
- Track missing observations.
- Exclude records explicitly marked as forecasts.
- Preserve original source data.
- Never overwrite validated data when validation fails.

## Historical Data Limitation

World Bank historical GDP data may be revised.

The observation year and retrieval timestamp do not establish when the data was originally published.

Point-in-time historical datasets are required for rigorous trading backtests.

## Future Integration

The validated China GDP series will be consumed by:

- GDP Global Economic Share
- GDP Global Ranking
- GDP Growth Analysis
- PTM Macro Dashboard

Future Dagster integration will use the asset ID:

`macro.gdp.nominal.china`

## Status

Collector implementation completed.

Offline tests passed.

Live API verification and unified Dagster pipeline integration remain pending.
