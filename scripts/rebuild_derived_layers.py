from __future__ import annotations
from pathlib import Path
import subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
VERSION = '8.74.1'

# Strictly local/repository-derived layers only.
# Network/Vnstock refresh jobs must never be added to this list.
SCRIPTS = [
    ('scripts/coverage_engine.py', True),
    ('scripts/dynamic_peer_engine.py', True),
    ('scripts/sector_benchmark_engine.py', True),
    ('scripts/intelligent_analyst.py', True),
    ('scripts/validate_v8.py', True),
]


def main():
    print(f'V{VERSION} OFFLINE DERIVED-LAYER REBUILD - NO VNSTOCK API CALLS')
    print('Peer crosscheck refresh is intentionally excluded from offline rebuild.')
    for script, fatal in SCRIPTS:
        print('\n>>>', script, flush=True)
        rc = subprocess.call([PYTHON, script], cwd=str(ROOT))
        if rc:
            print(f'ERROR - {script} returned rc={rc}', flush=True)
            if fatal:
                return rc
    print('\nDONE - derived layers rebuilt from local/repository data only.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
