# V8.70 – Strict Leverage & Cash-flow Fix

V8.70 builds on the exact semantic/period parser in V8.69 and fixes the remaining corporate financial-risk metrics.

- Interest-bearing debt is now forced to `BS_SHORT_TERM_BORROWINGS + BS_LONG_TERM_BORROWINGS` at the latest quarter.
- EBITDA is always derived from `IS_OPERATING_PROFIT` TTM4Q + absolute `CF_DEPRECIATION_AND_AMORTISATION` TTM4Q on the same four-quarter window. Any `financial_health` EBITDA fallback is overwritten and cannot enter leverage ratios.
- Debt/EBITDA uses latest-quarter interest-bearing debt divided by derived TTM4Q EBITDA.
- CFO/Debt uses `CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES` TTM4Q / latest-quarter debt.
- FOCF proxy is CFO + capex cash outflow (`CF_PAYMENTS_FOR_FIXED_ASSETS`, normally negative); FOCF/Debt and Cash/Debt are derived consistently.
- Debt/Equity is recalculated from interest-bearing debt / equity when exact borrowings are available.
- Sanity gates reject impossible Debt/EBITDA (>100x) or dimensionally implausible cash-flow/debt ratios.
- One-company refresh prints leverage and cash-flow audit lines.

Offline regression test on the HPG raw data bundled in V8.69 gives approximately:
- EBITDA TTM4Q: VND 37.755 trillion
- Interest-bearing debt 2026-Q2: VND 98.530 trillion
- Debt/EBITDA: 2.61x
- CFO TTM4Q: VND 28.929 trillion
- CFO/Debt: 29.36%
- FOCF/Debt: 1.70%
- Cash/Debt: 9.93%
