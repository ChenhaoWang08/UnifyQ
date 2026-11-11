
# China Real GDP Collector

A stand-alone raw-data collector for **China real GDP at constant 2015 US dollars**.

## Source

- Provider: World Bank, World Development Indicators (WDI)
- Economy: China (`CHN`, World Bank two-character `CN`)
- Indicator: `NY.GDP.MKTP.KD` (GDP, constant 2015 US$)
- Reference year: 2015
- Periodicity: annual
- API: `https://api.worldbank.org/v2/country/CHN/indicator/NY.GDP.MKTP.KD?format=json`
- No API key required

## Execute

From the `UnifyQ/macro/` directory:

```bash
python3 -m pip install -r 03_Gross_Domestic_Product/GDP/Real/China/requirements.txt
python3 -m unittest discover -s 03_Gross_Domestic_Product/GDP/Real/China/tests -v
python3 03_Gross_Domestic_Product/GDP/Real/China/fetch.py
```

## Data Flow

World Bank API → Raw JSON snapshot → Strict validation → CSV + metadata.

## Outputs

- Raw snapshots: `data/raw/world_bank/NY.GDP.MKTP.KD/CHN/<sha256>.json`
- Validated CSV: `data/validated/macro/gdp/real/china.csv`
- Metadata manifest: `data/metadata/macro/gdp/real/china.json`

CSV fields (identical to nominal collectors):

`observation_year,country_iso3,indicator_id,value,unit,frequency,source,obs_status,retrieved_at`

CSV `unit` is `constant_2015_USD`, not `USD` at current prices. Metadata includes `base_year=2015`.

## Quality Rules

- Verify `CHN`, World Bank country `CN`, and `NY.GDP.MKTP.KD`.
- Reject invalid years, duplicate years, non-positive and non-finite GDP values.
- Exclude null records and explicitly forecast observations; never impute zero.
- Verify API pagination completeness before publishing.
- Archive raw payloads by SHA-256 and do not replace validated CSV after validation errors.
- Snapshot retrieval time is not the economic observation's initial release time.
- Historical World Bank GDP may be revised; point-in-time vintages are not guaranteed.

## Downstream Uses

- Real GDP comparisons with US / Eurozone / Global
- Real GDP growth calculation
- PTM Macro Dashboard

Do not mix constant-2015 USD real GDP with current USD nominal GDP or interpret the ratio as a meaningful global nominal economic share.

## Status

Collector implemented and offline tests complete. Live World Bank API collection and Dagster integration must be checked separately.
