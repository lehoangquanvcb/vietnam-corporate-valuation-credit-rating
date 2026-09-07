# V8.69 – Exact Semantic ID / Period Parser

- Core corporate KPIs use exact Vnstock semantic IDs, not fuzzy labels.
- Revenue = IS_NET_REVENUE, strict TTM from latest 4 consecutive quarters.
- NPAT = IS_NET_PROFIT_AFTER_TAX, strict TTM from latest 4 consecutive quarters.
- Total assets/equity/cash/liabilities = latest quarter.
- P/E = RT_VALUE_PE and P/B = RT_VALUE_PB, latest quarter.
- ROE/ROA/Debt-Equity/Current Ratio use exact ratio IDs.
- Debt derives from latest-quarter short + long-term borrowings if no total-debt row exists.
- No stale/fuzzy fallback is permitted for exact-semantic core metrics.
- Every core KPI stores SourceRow, Basis, and Periods for audit.
