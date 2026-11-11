
# United States Real GDP Collector

Collect United States Real GDP (constant 2015 US$) from the World Bank WDI API, validate annual observations, retain raw JSON snapshots, and publish a standardized CSV for UnifyQ.

## Source and contract

- Provider: World Bank World Development Indicators (WDI)
- Economy: United States (`USA`, World Bank `US`)
- Indicator: `NY.GDP.MKTP.KD` — GDP (constant 2015 US$)
- Base year: 2015
- Frequency: Annual (`A`)
- Output unit: `constant_2015_USD`
- Coverage requested: 1960 through current calendar year; only available non-null years are published
- API: https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.KD?format=json
- No API key required

## Run from UnifyQ/macro

```bash
python3 -m pip install -r 03_Gross_Domestic_Product/GDP/Real/US/requirements.txt
python3 -m unittest discover -s 03_Gross_Domestic_Product/GDP/Real/US/tests -v
python3 03_Gross_Domestic_Product/GDP/Real/US/fetch.py
```

## Output paths

- Raw JSON: `data/raw/world_bank/NY.GDP.MKTP.KD/USA/<sha256>.json`
- Validated CSV: `data/validated/macro/gdp/real/us.csv`
- Manifest: `data/metadata/macro/gdp/real/us.json`

CSV columns:

`observation_year,country_iso3,indicator_id,value,unit,frequency,source,obs_status,retrieved_at`

## Data checks

- Validate United States codes, real-GDP series, year format and bounds
- Reject duplicate years, zero/negative values, NaN/inf and invalid records
- Skip null and explicitly forecast observations; no missing-year imputation
- Verify World Bank response pagination and total row count
- Retry transient HTTP failures, preserve raw JSON by SHA-256
- Do not overwrite a valid CSV if the new data fails validation

## Historical limitations

GDP data may be revised. `retrieved_at` is collection time, not official GDP release time. World Bank WDI is not guaranteed to supply point-in-time historical vintages. Full pipeline integration with Dagster is a separate task.

## Downstream

Suitable for real GDP growth comparisons and PTM macro research. Do not mix this constant-2015-USD series into nominal GDP global-share calculations.
