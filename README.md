# UnifyQ
# PTM Quantitative Research System

### A Modular, Data-Driven Quantitative Investment Research Platform

**Project Type:** Individual Software Development Project  
**Role:** Product Manager & Developer  
**Status:** In Development  
**Target Release:** December 2026 (MVP)

---

## 1. Project Overview

PTM Quantitative Research System is a Python-based quantitative investment research platform designed to collect, process, validate, and analyze financial market and macroeconomic data.

The project aims to transform fragmented financial information into a structured research workflow, helping individual investors make more systematic, data-driven decisions.

The system combines macroeconomic research, historical stock market data, financial analysis, and automated data pipelines within a modular architecture.

## 2. Problem Statement

Individual investors often face several challenges:

- Financial information is distributed across multiple websites and data providers.
- Manually collecting and cleaning economic data is time-consuming.
- Inconsistent data formats can lead to inaccurate analysis.
- Historical market research requires reliable, reproducible datasets.
- Professional quantitative research platforms can be expensive and difficult to customize.

This project addresses these problems by creating a centralized, extensible research environment.

## 3. Core Features

### Must Have — MVP (Version 1.0)

**Feature 1: Macroeconomic Data Pipeline**

Automatically collect, clean, validate, and organize macroeconomic indicators, including GDP, CPI, interest rates, unemployment, and manufacturing activity.

Each indicator follows an independent data-processing workflow before entering a unified database.

**Feature 2: Historical Stock Market Database**

Collect and maintain historical daily OHLCV data (Open, High, Low, Close, Volume).

Support historical analysis, financial calculations, and basic quantitative backtesting.

**Feature 3: Macro Dashboard & Research Reports**

Provide a centralized interface for visualizing economic indicators, identifying macroeconomic trends, and generating structured investment research reports.

### Nice to Have — Future Releases

**Feature 4: Large-Scale Equity & Catalyst Analysis**

Expand coverage to approximately 1,300 stocks, including corporate earnings, financial statements, sector analysis, and market catalysts.

**Feature 5: Multi-Agent Automation & Advanced Trading Research**

Integrate AI-powered research agents, advanced risk models, options analysis, and automated research workflows.

These features are deferred to reduce development complexity and prioritize a stable initial release.

## 4. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Data Processing | Pandas, NumPy |
| Data Collection | HTTP APIs, Requests |
| Pipeline Orchestration | Dagster |
| Metadata Database | SQLite |
| Historical Data Storage | Parquet |
| Analytical Queries | DuckDB |
| Desktop Interface | PySide6, pyqtgraph |
| Backend API | FastAPI (when needed) |
| Testing | Pytest |
| Version Control | Git & GitHub |
| Development Environment | VS Code |
| Future AI Workflows | LangGraph |

### Hosting Strategy

The primary research engine is designed to run locally.

For public demonstration, a lightweight, read-only web dashboard is planned using Streamlit Community Cloud.

GitHub will serve as the main platform for source code, documentation, issue tracking, and version management.

The public demo will not provide automated live-trading functionality.

## 5. System Architecture

The platform follows a modular data architecture.

**Data Sources → Independent Collectors → Raw Data Storage → Cleaning & Validation → Unified Data Layer → Quantitative Analysis → Dashboard & Reports**

Each indicator can be updated, tested, and maintained independently.

This design improves data reliability, scalability, and error isolation.

## 6. MVP Development Roadmap

| Phase | Development Goal |
|---|---|
| Week 1 | Review project architecture and define data standards |
| Week 2 | Implement macroeconomic data collection pipelines |
| Week 3 | Build the historical stock market database |
| Week 4 | Develop the macroeconomic dashboard |
| Week 5 | Integrate analytical tools and perform testing |
| Week 6 | Complete quality assurance and release MVP |

The initial release prioritizes reliability over feature quantity.

## 7. Technical Risks

### Primary Risk: Data Availability and Reliability

The system depends on external financial data providers, which may introduce API limitations, missing records, service interruptions, or inconsistent information.

**Mitigation Strategy:**

- Prioritize official and documented data sources.
- Implement caching and retry mechanisms.
- Preserve original data before transformation.
- Validate timestamps, missing values, and duplicate records.
- Provide backup data sources when available.
- Isolate failed data pipelines without interrupting the entire system.

Historical backtesting must also avoid look-ahead bias by respecting the actual release dates of economic information.

## 8. Launch Strategy

**Target Users:** Individual investors, quantitative research beginners, and students interested in financial data analysis.

**Primary Launch Channel:** GitHub, followed by relevant university and quantitative finance communities.

**Value Proposition:**

*A modular quantitative research platform that transforms fragmented financial data into structured, reproducible investment research.*

### Pre-Launch Requirements

- [ ] Complete the three mandatory MVP features.
- [ ] Validate data collection and storage.
- [ ] Test error handling and recovery.
- [ ] Verify dashboard functionality.
- [ ] Run automated tests.
- [ ] Review application security.
- [ ] Prepare project documentation.
- [ ] Deploy and test the demonstration version.
- [ ] Publish the official release.

## 9. Project Documentation

Detailed development and launch planning documents are available in the `docs/` directory.

| Document | Description |
|---|---|
| [MVP Scope](docs/2-mvp-scope.md) | Core features and feature prioritization |
| [Tech Stack](docs/3-tech-stack.md) | Technology choices and deployment |
| [Risk Matrix](docs/4-risk-matrix.md) | Technical constraints and contingency plans |
| [Launch Plan](docs/5-launch-plan.md) | Marketing strategy, QA, and launch operations |

This is an individual project. Team formation documentation is not required.

## 10. Future Development

Future improvements may include:

- Expanding the macroeconomic indicator database.
- Supporting approximately 1,300 equity symbols.
- Integrating corporate financial statements.
- Developing sector and industry research.
- Adding AI-assisted financial analysis.
- Implementing more advanced backtesting and risk management.

## 11. Disclaimer

This project is developed for educational and investment research purposes.

It does not provide personalized financial advice, guarantee investment returns, or execute live trades in its initial release.

---

**Developed as an individual quantitative software engineering project.**