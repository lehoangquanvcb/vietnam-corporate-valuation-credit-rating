# V8.68 — Strict No-Stale Semantic/Period Gate

- Fixes the key V8.67 failure mode: a failed current refresh could still validate and print an old snapshot.
- Current-run refresh ERROR now stops one-company rebuild immediately and prints the actual exception.
- Revenue/NPAT are accepted only from four consecutive quarters (TTM4Q). No FY, single-quarter, LAST_NUMERIC or financial-health fallback is allowed for core flow KPIs.
- PE/PB no longer accept zero/fallback artefacts.
- Per-metric parsing is isolated so one optional KPI cannot kill the entire ticker.
- Full-fundamental export errors no longer invalidate normalized core parsing.
- Audit fields remain attached to every parsed KPI.

Test HPG first with RUN_REFRESH_ONE_AND_REBUILD.bat. Do not run full market until HPG passes.
