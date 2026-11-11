# Risk Matrix — Quantitative Research System

## Risk Scoring

**Risk Score = Probability × Impact**

Both probability and impact are rated on a scale of 1–5.

- **High Risk:** 15–25
- **Medium Risk:** 8–14
- **Low Risk:** 1–7

| Risk | Probability | Impact | Risk Score |
|---|---|---|---|
| Unreliable free data sources, rate limits, or licensing restrictions | 4 | 5 | 20 |
| Look-ahead bias in historical macroeconomic data | 4 | 5 | 20 |
| Scope creep and excessive module maintenance | 5 | 4 | 20 |
| Backtesting overfitting or failure to account for transaction costs | 4 | 5 | 20 |
| Errors in adjusted stock prices, time zones, or trading calendars | 3 | 5 | 15 |
| SQLite concurrent write conflicts | 4 | 4 | 16 |
| Automated scheduling failures or stale data | 3 | 4 | 12 |
| API key exposure or accidental activation of trading permissions | 3 | 5 | 15 |

## Top Three Technical Risks

### R1 — Data Source Reliability

Establish a data source registry, caching mechanisms, rate limiting, exponential backoff retries, and alternative data providers.

Any data that cannot be retrieved must be marked as `blocked`. Missing data must never be fabricated or replaced with unverified values.

### R2 — Look-Ahead Bias

Store the actual publication timestamps and historical revisions of macroeconomic data.

Backtesting must not use information that was unavailable at the time of the simulated trading decision. Otherwise, the backtesting results are invalid.

### R3 — System Complexity

Limit the initial release to three core MVP features.

All additional feature requests must be placed in the **Later Backlog**.

Multiple AI agents must not bypass data quality validation gates under any circumstances.

## Failure Handling Procedures

**Anomaly Detection → Data Isolation → Error Logging → Repair / Data Source Switching → Historical Backfill → Revalidation → Resume Data Publication**

Any failed data quality check must never be automatically ignored.