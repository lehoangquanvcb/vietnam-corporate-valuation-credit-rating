# Upgrade 8.64 — Vnstock 3.2.2 compatibility + hard verification

- Detects installed vnstock_data version.
- For <=3.2.7 (including user's Bronze 3.2.2), uses legacy-compatible Fundamental calls and avoids v3.2.8-only format/drop_empty/com_type arguments.
- Uses Fundamental.financial_health() as a normalized scorecard fallback for regular/securities companies (available since vnstock_data 3.1.0).
- Supports wide, legacy and long/tidy-like payloads; unnamed index is materialized for row-label parsing.
- Normalizes common percentage ratios.
- `RUN_REFRESH_ONE_AND_REBUILD.bat` prints VERSION 8.64.
- `refresh_one_company.py` prints hard parsing gate and actual parsed Revenue/TotalAssets/Equity/NPAT values.
- `diagnose_vnstock.py HPG` now probes both raw reports and `financial_health`, saves CSVs under data/diagnostics/HPG/.

Important: local refresh does not update Streamlit Cloud until updated data CSVs are committed and pushed to GitHub.
