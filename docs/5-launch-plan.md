# Launch Plan — Solo Quantitative Research System

## Launch Objective

Within a recommended six-week development period, build a quantitative research MVP that can operate independently, provides full data traceability, and supports reproducible validation.

## Development Roadmap

| Week | Core Tasks | Acceptance Criteria |
|---|---|---|
| Week 1 | Audit the existing codebase, verify data sources, and define the data schema | Development environment runs successfully, and data contracts are clearly defined |
| Week 2 | Develop the macroeconomic data collection pipeline | 15 raw macroeconomic data series pass data quality validation |
| Week 3 | Develop the historical daily price database | Complete two years of historical data backfilling for 30 stocks |
| Week 4 | Develop the PTM Macro Dashboard | Generate traceable and evidence-based macroeconomic research conclusions |
| Week 5 | Develop a basic backtesting framework and conduct integration testing | Results are reproducible, with no known look-ahead bias |
| Week 6 | Implement automated scheduling, conduct recovery testing, and release the system | Release version v0.1.0 |

## Pre-Launch Checklist

- [ ] Data source licensing terms and usage restrictions have been verified.
- [ ] Data ingestion supports historical backfilling and incremental updates.
- [ ] All data quality validation tests pass.
- [ ] Raw macroeconomic data is stored separately from derived data.
- [ ] The Macro Dashboard displays data anomalies and publication timestamps.
- [ ] Backtesting incorporates transaction costs and point-in-time constraints.
- [ ] Error logs are accessible, and failed tasks can be rerun.
- [ ] The database has been backed up, and restoration procedures have been successfully tested.
- [ ] Automated scheduling operates for seven consecutive days without silent failures.
- [ ] Automated live trading is prohibited in the MVP.

## Post-Launch Roadmap

**Phase 1 — Expand Stock Coverage**

Gradually expand the stock universe to 100, 300, and eventually 1,300 stocks.

**Phase 2 — Complete PTM Macroeconomic Integration**

Progressively integrate all macroeconomic indicators required by the PTM research framework.

**Phase 3 — Expand Fundamental and Market Research**

Incorporate corporate earnings data, market catalysts, and sector and industry research capabilities.

**Phase 4 — Enhance Multi-Agent Workflows**

Improve multi-agent orchestration, task coordination, and automated research workflows.

**Phase 5 — Paper Trading Validation**

Conduct paper trading validation under independent risk management procedures and strict permission controls.

## Final Launch Criteria

The system may only be designated as **MVP Launched** after all core acceptance criteria have been successfully met.