
# World Nominal GDP Collector

## Purpose

Fetch the World Bank's `WLD` GDP (current US$) regional aggregate,
validate the annual observations, and publish the same nine-column CSV
schema used by UnifyQ's China, US and Eurozone nominal-GDP collectors.

## Data Source

- Provider: World Bank World Development Indicators (WDI)
- Region: World (`WLD`, WB-2 `1W`)
- Indicator: `NY.GDP.MKTP.CD`
- Unit: Current USD
- Frequency: Annual
- Start Year: 1960
- API Key: Not Required

Official API:

https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.CD?format=json

## System Architecture

World Bank API
    -> Fetch
    -> Raw JSON Storage
    -> Data Validation
    -> Validated CSV
    -> Unified Macro Pipeline

## Installation

Run from the `UnifyQ/macro` directory:

```bash
python3 -m pip install -r 03_Gross_Domestic_Product/GDP/Nominal/Global/requirements.txt
```

## Testing

```bash
python3 -m unittest discover -s 03_Gross_Domestic_Product/GDP/Nominal/Global/tests -v
```

## Execution

```bash
python3 03_Gross_Domestic_Product/GDP/Nominal/Global/fetch.py
```

## Output Files

### Raw JSON

`data/raw/world_bank/NY.GDP.MKTP.CD/WLD/<sha256>.json`

Contains archived World Bank responses.

### Validated CSV

`data/validated/macro/gdp/nominal/global.csv`

### Metadata

`data/metadata/macro/gdp/nominal/global.json`

## CSV Schema

The output follows the same contract as China, US and Eurozone:

- observation_year
- country_iso3
- indicator_id
- value
- unit
- frequency
- source
- obs_status
- retrieved_at

For backward compatibility, `country_iso3` contains `WLD`.

`WLD` is a World Bank aggregate code, not an ISO country code.

## Data Quality Rules

- Verify World Bank aggregate code `1W`.
- Verify region name `World`.
- Verify indicator `NY.GDP.MKTP.CD`.
- Reject malformed observation years.
- Reject duplicate years.
- Reject negative and zero GDP values.
- Reject non-finite GDP values.
- Validate pagination completeness.
- Exclude null observations.
- Exclude explicitly forecast observations.
- Preserve original JSON responses.
- Prevent invalid data from overwriting validated CSV.

## Historical Data Limitations

World Bank GDP data may be revised.

The observation year is not the release date.

The retrieval timestamp is not the original publication date.

Point-in-time historical vintages are not guaranteed.

## Global Economic Share Integration

This data asset provides the world GDP denominator.

Formula:

Global Economic Share =
Country Nominal GDP / World Nominal GDP * 100

The Global Economic Share module should use validated data from:

- China Nominal GDP
- US Nominal GDP
- Eurozone Nominal GDP
- Global Nominal GDP

Global GDP is collected directly from the World Bank.

It is not calculated by adding China, US and Eurozone GDP.

## Downstream Data Assets

- macro.gdp.global_economic_share
- macro.gdp.global_ranking
- macro.ptm.dashboard

## Status

Independent collector implementation completed.

14 offline unit tests passed.

Live World Bank collection remains to be verified.

Dagster integration remains pending.
