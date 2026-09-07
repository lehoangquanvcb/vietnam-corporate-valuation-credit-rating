# 8.67 Strict Period / Semantic Parser

- Exact semantic-row scoring before fuzzy matching.
- Flow KPIs use latest four **consecutive** quarterly observations only; FY is fallback and is never mixed with quarters.
- Stock KPIs use latest quarter closing balance.
- Ratio KPIs use latest quarter observation.
- Tidy/long ratio parsing excludes metadata fields such as `level` and `order` from numeric-value selection.
- Adds per-KPI audit columns: `<KPI>_SourceRow`, `<KPI>_Basis`, `<KPI>_Periods`.
- Zero P/E or P/B is treated as missing instead of a valid multiple.
- Debt/EBITDA is produced only when EBITDA is positive and period-compatible.
- One-company refresh prints period/semantic audit so HPG can be verified before full-market refresh.
