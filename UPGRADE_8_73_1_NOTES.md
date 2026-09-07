# V8.73.1 Cloud Runtime Guard Hotfix

Changed files only.

- `app.py`: build fingerprint, runtime peer diagnostics, authoritative analyst-override label, and final Plotly validity guard.
- `scripts/sector_benchmark_engine.py`: analyst override is authoritative before all dynamic/ICB fallback; Debt/Equity validity guard remains 0–10x.
- `scripts/dynamic_peer_engine.py`: analyst override is authoritative for peer labels.
- `scripts/universal_data.py`: V8.73 snapshot/history fallback retained.

No Vnstock refresh is required. Copy files, test local, then commit/push these files.
