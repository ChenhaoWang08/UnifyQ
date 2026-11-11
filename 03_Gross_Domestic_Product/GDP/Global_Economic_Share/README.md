
# Global Economic Share — UnifyQ

## Overview

Global Economic Share (GES) is a derived macroeconomic data asset.

It calculates the share of global nominal GDP represented by:

- United States
- China
- Euro area
- Combined US, China, and Euro area
- Rest of World

The module does not fetch data from the internet.

## Data Source

Provider: World Bank WDI

Indicator: NY.GDP.MKTP.CD

Unit: Current USD

Frequency: Annual

## Input Files

All inputs are loaded from the validated nominal GDP layer:

data/validated/macro/gdp/nominal/china.csv
data/validated/macro/gdp/nominal/us.csv
data/validated/macro/gdp/nominal/eurozone.csv
data/validated/macro/gdp/nominal/global.csv

Each input must also have a valid metadata manifest and
an intact raw source snapshot.

## Calculation

GES = Economy Nominal GDP / World Nominal GDP * 100

Output series:

GES_USA
GES_CHN
GES_EMU
GES_COMBINED
GES_REST

Combined Share = (US + China + Eurozone) / World * 100

Rest Share = 100 - Combined Share

## Pipeline

Validated Nominal GDP
    -> Load
    -> Validate
    -> Calculate
    -> Publish
    -> Derived Data Layer

## Execution

Run from UnifyQ/macro:

```bash
python3 03_Gross_Domestic_Product/GDP/Global_Economic_Share/calculate.py
```

## Tests

```bash
python3 -m unittest discover \
  -s 03_Gross_Domestic_Product/GDP/Global_Economic_Share/tests \
  -v
```

## Output

Derived CSV:

data/derived/macro/gdp/global_economic_share/global_economic_share.csv

Metadata:

data/metadata/macro/gdp/global_economic_share.json

## Derived CSV Schema

observation_year
series_id
value
unit
frequency
source
numerator_gdp_usd
world_gdp_usd
calculated_at

## Quality Controls

- All four source files must exist.
- Source manifests must have quality_status=passed.
- Raw source snapshots must pass SHA-256 checks.
- Only nominal GDP in current USD is accepted.
- Duplicate years are rejected.
- Invalid GDP values are rejected.
- Only common observation years are calculated.
- Combined GDP cannot exceed World GDP.
- Invalid input cannot overwrite previously published data.

## Historical Limitations

World Bank GDP observations may be revised.

The collection timestamp is not the original release timestamp.

Matching source update dates alone does not guarantee
identical historical data vintages.

GES should not be treated as a standalone trading signal.

## Future Integration

Asset ID:

macro.gdp.global_economic_share

Upstream assets:

macro.gdp.nominal.china
macro.gdp.nominal.us
macro.gdp.nominal.eurozone
macro.gdp.nominal.global

Downstream:

PTM Macro Dashboard

The derived CSV and metadata are ready for downstream use.
Dagster asset registration is a separate integration step.
