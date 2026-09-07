from __future__ import annotations
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
PYTHON=sys.executable
SCRIPTS=[
    ('scripts/coverage_engine.py',True),
    ('scripts/dynamic_peer_engine.py',True),
    ('scripts/sector_benchmark_engine.py',True),
    ('scripts/refresh_vnstock_peer_crosscheck.py',False),
    ('scripts/intelligent_analyst.py',True),
    ('scripts/validate_v8.py',True),
]

def main():
    print('V8.72 OFFLINE REBUILD - NO VNSTOCK API CALLS')
    for s,fatal in SCRIPTS:
        print('\n>>>',s,flush=True)
        rc=subprocess.call([PYTHON,s],cwd=str(ROOT))
        if rc and fatal:return rc
    print('\nDONE - derived layers rebuilt entirely from local/repository data.')
    return 0
if __name__=='__main__':raise SystemExit(main())
