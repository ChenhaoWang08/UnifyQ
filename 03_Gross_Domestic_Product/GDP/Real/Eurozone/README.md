
# Euro area Real GDP Collector

This independent UnifyQ macro asset collects the World Bank's **Euro area GDP (constant 2015 US$)** series, validates it and publishes a compatible nine-column CSV.

## Source

- World Bank World Development Indicators (WDI)
- API economy code: `EMU` (Euro area; World Bank two-character code `XC`)
- Indicator: `NY.GDP.MKTP.KD`
- Frequency: Annual; starts 1960
- Unit: constant 2015 US dollars (not current USD)
- No API key required
- API: `https://api.worldbank.org/v2/country/EMU/indicator/NY.GDP.MKTP.KD?format=json`

The World Bank provides the Euro area aggregate directly. **Do not** build this module by adding up current euro-area member states.

## Installation, test, and execution

Run these commands from `UnifyQ/macro`:

```bash
python3 -m pip install -r 03_Gross_Domestic_Product/GDP/Real/Eurozone/requirements.txt
python3 -m unittest discover -s 03_Gross_Domestic_Product/GDP/Real/Eurozone/tests -v
python3 03_Gross_Domestic_Product/GDP/Real/Eurozone/fetch.py
```

## Files

- Raw JSON snapshots: `data/raw/world_bank/NY.GDP.MKTP.KD/EMU/<sha256>.json`
- Validated CSV: `data/validated/macro/gdp/real/eurozone.csv`
- Metadata: `data/metadata/macro/gdp/real/eurozone.json`

CSV columns (same as China's real GDP collector):

`observation_year,country_iso3,indicator_id,value,unit,frequency,source,obs_status,retrieved_at`

For backward compatibility `country_iso3` contains `EMU`; **EMU is an aggregate code, not an ISO country code**. The metadata records this distinction.

## Quality controls

- Verify Euro area `XC` and indicator `NY.GDP.MKTP.KD`.
- Reject bad years, duplicates, wrong regions, nonpositive or nonfinite numbers.
- Exclude source null values and explicit forecast observations; never fill missing years with zero.
- Check API pagination for completeness.
- Retry transient HTTP errors; archive raw snapshots by SHA-256.
- Validate before overwriting any previously published CSV.

## Historical limitations

WDI historical GDP data may be revised. Retrieval time is **not** the original release timestamp. These data are not guaranteed point-in-time vintages suitable for historical trading simulations without additional controls.

## Downstream

- `macro.gdp.real.eurozone` (this asset)
- Real GDP growth and international comparisons
- PTM Macro Dashboard

Do not use this constant-2015-USD series as the numerator for *nominal* Global Economic Share calculations.

## Status

Independent collector and offline tests implemented. Live API and Dagster integration are separate verification steps.
