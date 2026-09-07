# V8.72.2 Peer Refresh Import Hotfix

## Fixed
- `RUN_REFRESH_PEERS.bat` previously failed with `ModuleNotFoundError: No module named 'scripts'`.
- Root cause: `refresh_target_peers.py` is executed directly from the `scripts` folder, so the project root was not on `sys.path`.
- The script now inserts the project root into `sys.path` before importing `scripts.dynamic_peer_engine`.

## Unchanged
- Keeps V8.72.1 targeted peer refresh logic.
- Keeps HPG steel/materials peer override.
- Keeps minimum 5 valid peer observations before showing peer benchmark.
- Keeps Bronze-safe one-worker refresh.

## After copying
Run:

    RUN_REFRESH_PEERS.bat

Enter:

    HPG

The process should now resolve the peer set and start refreshing peer tickers instead of stopping at import.
