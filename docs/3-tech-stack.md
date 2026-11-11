# Tech Stack — Quantitative Research System

## Technology Selection

| Domain | Technology |
|---|---|
| Primary Language | Python |
| Data Acquisition | HTTPX / Requests / Official APIs |
| Pipeline Orchestration | Dagster |
| Data Processing | Pandas, NumPy, PyArrow |
| Metadata & Task State | SQLite |
| Historical Market Data Storage | Parquet |
| Historical Data Querying | DuckDB |
| Frontend | PySide6 + pyqtgraph |
| Internal API | FastAPI (as needed) |
| Multi-Agent Workflow | LangGraph (not in the MVP critical path) |
| Testing | Pytest |
| Version Control | Git |
| Deployment | Local machine (no cloud server dependency for now) |

## Data Architecture

```text
Data Providers
      ↓
Individual Collectors
      ↓
Raw Storage
      ↓
Cleaning & Validation
      ↓
Unified Data Layer
      ↓
Macro Analytics / Backtesting
      ↓
Dashboard / Trading Plan
```

## Engineering Requirements

- Each indicator must have its own dedicated collection and validation task, while sharing a unified scheduling mechanism and data interface.
- Avoid creating individual scrapers for each stock; reuse market data collectors instead.
- Retain raw data, observation dates, announcement dates, and revision versions.
- Use SQLite for state and metadata; use Parquet for large-scale historical market data.
- All tasks must be re-runnable; failed tasks must not overwrite valid, existing data.
- Centralized management for API keys, configurations, logs, and testing.
- During the MVP phase, prioritize reusing existing code; avoid unnecessary architectural rewrites.