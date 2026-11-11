
# US Nominal GDP Collector

## Overview

This module collects the United States' annual nominal GDP
from the World Bank World Development Indicators API.

It is part of the UnifyQ quantitative macroeconomic research system.

## Data Source

- Provider: World Bank WDI
- Country: United States
- Country Code: USA
- Indicator: NY.GDP.MKTP.CD
- Indicator Name: GDP (current US$)
- Frequency: Annual
- Unit: USD
- Start Year: 1960
- API Key: Not Required

## Objective

Fetch historical US nominal GDP, validate observations,
and publish standardized data for downstream analysis.

## Data Processing

1. Request annual GDP observations from the World Bank API.
2. Handle API failures with retry and backoff.
3. Fetch all available response pages.
4. Store the original JSON response.
5. Validate country, indicator, year and GDP values.
6. Reject duplicate or invalid observations.
7. Exclude null and explicitly forecast values.
8. Publish validated observations to CSV.
9. Save metadata and data-quality information.

## Output

### Validated CSV

data/validated/macro/gdp/nominal/us.csv

### Raw JSON

data/raw/world_bank/NY.GDP.MKTP.CD/USA/

### Metadata

data/metadata/macro/gdp/nominal/us.json

## CSV Schema

observation_year
country_iso3
indicator_id
value
unit
frequency
source
obs_status
retrieved_at

The CSV schema is identical to the China nominal GDP collector.

## Installation

From the macro directory:

python3 -m pip install -r 03_Gross_Domestic_Product/GDP/Nominal/US/requirements.txt

## Execution

From the macro directory:

python3 03_Gross_Domestic_Product/GDP/Nominal/US/fetch.py

## Testing

From the macro directory:

python3 -m unittest discover -s 03_Gross_Domestic_Product/GDP/Nominal/US/tests -v

## Data Quality

The module rejects:

- Invalid country codes
- Unexpected indicator IDs
- Duplicate valid observations
- Invalid observation years
- Zero or negative GDP values
- Non-finite GDP values
- Malformed API responses

Raw responses are archived before validation.
Invalid data cannot overwrite the existing validated CSV.

## Historical Limitations

World Bank GDP observations may be revised.

The observation year is not the original publication date.
The retrieval timestamp is the collection date, not the release date.

Point-in-time historical vintages are not guaranteed.

## Future Integration

The validated US nominal GDP data will be consumed by:

- Global Economic Share
- Global GDP Ranking
- GDP Growth Analysis
- PTM Macro Dashboard

Asset ID:

macro.gdp.nominal.us

## Project Status

Independent collector implementation completed.
Offline tests verified.
Live API collection and Dagster integration remain pending.
