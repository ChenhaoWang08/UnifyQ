# MVP Scope — Quantitative Research System

## Project Objective

To build a quantitative research platform, maintained by a single individual, that establishes a complete, end-to-end workflow—from raw data acquisition, cleaning, and quality validation to macroeconomic analysis, stock backtesting, and the generation of research reports.

## Candidate Features

| Feature | Priority | Status |
|---|---|---|
| Macroeconomic indicator data acquisition, cleaning, and storage | P0 | MVP |
| Historical daily OHLCV stock database and basic backtesting | P0 | MVP |
| Macro Dashboard and Trading Plan reporting | P0 | MVP |
| Analysis of 1,300 stocks, including financial statements, catalysts, and news | P1 | Later |
| Multi-agent autonomous systems, options, and automated trading | P2 | Later |

## MVP Acceptance Criteria

1. At least 15 macroeconomic raw data series must be continuously updated, with source and revision history preserved.
2. Historical daily data for at least 30 stocks must be backfilled for the most recent two-year period.
3. All data must undergo a processing pipeline: Raw → Validated → Curated.
4. The Macro Dashboard must be capable of generating traceable research conclusions based on validated data.
5. At least one reproducible backtest—accounting for transaction costs—must be completed.
6. The MVP shall not execute live market orders.

## Development Principles

Prioritize data accuracy, historical reproducibility, and system recoverability. Do not use the number of indicators, the number of agents, or the complexity of the user interface as metrics for the completion of the MVP.