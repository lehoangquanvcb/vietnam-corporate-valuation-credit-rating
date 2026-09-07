# Upgrade 8.66 — Period-aware Vnstock parser

- Fixes vnstock_data 3.2.2 row-wide period schema.
- Stock metrics use latest quarter only.
- Ratio metrics use latest quarter only.
- Flow metrics use TTM from latest 4 quarterly observations when available, otherwise latest FY.
- Never sums FY columns together with quarterly columns.
- Maps observed semantic IDs including IS_NET_REVENUE, IS_GROSS_PROFIT, IS_OPERATING_PROFIT, IS_INTEREST_EXPENSE, RT_VALUE_PE and RT_VALUE_PB.
- One-company refresh remains fast and validates Revenue + TotalAssets + Equity + NPAT before success.
