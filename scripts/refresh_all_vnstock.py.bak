from __future__ import annotations
from pathlib import Path
from vnstock_env import load_vnstock_env
import subprocess, sys, pandas as pd, json

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / 'config'
PYTHON = sys.executable

def run(cmd, fatal=True):
    print('\n>>>', ' '.join(map(str, cmd)), flush=True)
    rc = subprocess.call([PYTHON, *cmd], cwd=str(ROOT))
    if rc and fatal:
        raise SystemExit(rc)
    return rc

def main():
    sponsor = load_vnstock_env()
    print('Vnstock Sponsor credential:', sponsor['api_key_masked'])
    if not sponsor['api_key_present']:
        print('WARNING - VNSTOCK_API_KEY not found in .env/process environment. vnstock_data may still use a credential previously stored by the official installer.')
    # 1) Discover the current market directly from Vnstock. This intentionally
    # does NOT use a hard-coded ticker list.
    run(['scripts/discover_listed_universe.py'])
    run(['scripts/industry_classifier.py'], fatal=False)

    u = pd.read_csv(CFG/'company_universe.csv')
    u['Ticker'] = u['Ticker'].astype(str).str.upper().str.strip()
    if 'Active' in u.columns:
        u = u[pd.to_numeric(u['Active'], errors='coerce').fillna(1).eq(1)]
    banks = sorted(u.loc[u['EntityType'].astype(str).str.upper().eq('BANK'),'Ticker'].dropna().unique().tolist())
    nonbanks = sorted(u.loc[~u['EntityType'].astype(str).str.upper().eq('BANK'),'Ticker'].dropna().unique().tolist())
    print(f'Universe ACTIVE: {len(u)} | BANK: {len(banks)} | NON-BANK: {len(nonbanks)}')

    # 2) Dedicated bank parser for every discovered bank, not config/banks.json.
    if banks:
        run(['scripts/refresh_vnstock.py','--mode','full','--tickers',','.join(banks)])

    # 3) All securities companies + all non-financial corporates.
    # The multisector script stores the complete raw ratio/BS/IS/CF tables and
    # also exports every numeric field to a normalized long-form Bronze file.
    if nonbanks:
        run(['scripts/refresh_vnstock_multisector.py','ALL'])

    # 4) Rebuild derived layers only after all Bronze files are refreshed.
    for script in [
        'scripts/coverage_engine.py',
        'scripts/dynamic_peer_engine.py',
        'scripts/sector_benchmark_engine.py',
        'scripts/refresh_vnstock_peer_crosscheck.py',
        'scripts/intelligent_analyst.py',
        'scripts/validate_v8.py',
    ]:
        run([script], fatal=(script not in ['scripts/refresh_vnstock_peer_crosscheck.py']))

    print('\nDONE - Vnstock full-market refresh completed.')

if __name__ == '__main__':
    main()
