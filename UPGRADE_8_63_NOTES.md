# 8.63 – Vnstock Schema Probe & Parser Hard Gate
- `diagnose_vnstock.py <TICKER>` now actually probes the ticker's balance sheet, income statement, cash flow and ratios and saves raw diagnostic CSVs under `data/diagnostics/<TICKER>/`.
- Multisector parser now supports both wide/time_series and tidy/long Vnstock fundamental payloads by resolving metric aliases in either columns or row labels/semantic fields.
- `refresh_one_company.py` no longer prints success for a non-bank company unless Revenue, TotalAssets, Equity and NPAT were parsed.
- If the hard gate fails, the script exits non-zero and tells the user to run the ticker schema probe.
