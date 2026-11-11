
# Global Real GDP Collector — UnifyQ

Collect World real GDP directly from the World Bank WDI API and publish it as a validated annual time series. This collector uses **real source data**, not estimates generated locally or hard-coded GDP values.

## Source

- Provider: World Bank World Development Indicators (WDI)
- Area: World (`WLD`, WB-2 `1W`)
- Indicator: `NY.GDP.MKTP.KD` — GDP (constant 2015 US$)
- Unit: constant 2015 US dollars
- Base year: 2015
- Frequency: annual
- Coverage requested: 1960 through the current calendar year (actual available years vary)
- URL: https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.KD?format=json
- API key: none

The World aggregate is **downloaded directly**; do not calculate it by adding US, China, and Euro area GDP. This is a constant-price series and must not be used for nominal GDP economic shares.

## Structure

- `config.json`: fixed indicator and source contract
- `fetch.py`: HTTP requests, retries, pagination, raw storage, CSV, metadata
- `validate.py`: strict World aggregate and series checks
- `tests/`: offline tests using synthetic data; these synthetic values never enter the real published CSV

## Run

Execute from `UnifyQ/macro`:

```bash
python3 -m pip install -r 03_Gross_Domestic_Product/GDP/Real/Global/requirements.txt
python3 -m unittest discover -s 03_Gross_Domestic_Product/GDP/Real/Global/tests -v
python3 03_Gross_Domestic_Product/GDP/Real/Global/fetch.py
```

## Data locations

- Raw source: `data/raw/world_bank/NY.GDP.MKTP.KD/WLD/<sha256>.json`
- Validated CSV: `data/validated/macro/gdp/real/global.csv`
- Manifest: `data/metadata/macro/gdp/real/global.json`

CSV schema (identical to other UnifyQ GDP collectors):

`observation_year,country_iso3,indicator_id,value,unit,frequency,source,obs_status,retrieved_at`

`country_iso3` is populated with `WLD` for backward compatibility; `WLD` is an **aggregate code**, not an ISO country code. The manifest explicitly records this distinction.

## Quality controls

- Requires region `World` (WB-2 `1W`) and indicator `NY.GDP.MKTP.KD`.
- Rejects malformed years, duplicate years, wrong indicator, and nonpositive/nonfinite values.
- Excludes null and explicitly forecast (`F`) observations; does not fill missing years.
- Validates API pagination consistency and total row count.
- Archives raw JSON snapshots by SHA-256.
- Data quality failure does not overwrite the prior validated CSV.

## Limitations

WDI historical data can be revised. `retrieved_at` is retrieval time, not the original economic release time. The data is not guaranteed to be point-in-time accurate for historical trading backtests. The collector is standalone; registering this asset with Dagster is a separate task.
