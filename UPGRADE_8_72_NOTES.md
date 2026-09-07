# V8.72 — Incremental / Resume Refresh

This is a patch release for V8.71/V8.70 data architecture.

## New
- `RUN_INCREMENTAL_REFRESH.bat`: resumes market download and skips companies that already have a valid V8.70+ strict snapshot.
- `RUN_INCREMENTAL_REFRESH_FAILED.bat`: retries only tickers listed in `data/failed_tickers.csv`.
- `RUN_REBUILD_FROM_RAW.bat`: rebuilds coverage, dynamic peers, benchmarks, analyst and validation **without any Vnstock API calls**.
- `scripts/incremental_resume_refresh.py`: checkpoint-aware planner; reads both durable snapshot and `_checkpoint_company_snapshot.csv` from interrupted runs.
- `scripts/rebuild_derived_layers.py`: offline derived-layer rebuild.

## Bronze API protection
- 1 worker.
- Default 3.0 seconds between ticker API batches.
- Per-ticker validation after refresh.
- Up to 3 retries with 45s/90s retry windows.
- Successful data are retained; one failed ticker does not invalidate completed progress.
- Failure list is persisted in `data/failed_tickers.csv`.

## Recommended workflow now
1. `RUN_INCREMENTAL_REFRESH.bat`
2. If failed tickers remain, wait for the API quota/network to recover and run `RUN_INCREMENTAL_REFRESH_FAILED.bat`.
3. `RUN_REBUILD_FROM_RAW.bat`
4. Check app locally / `git status`.
5. Push data + code to GitHub.

`RUN_FULL_REFRESH.bat` is no longer required for ordinary continuation. Keep it for a deliberate whole-market refresh (e.g. new reporting quarter).
