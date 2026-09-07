from __future__ import annotations
from pathlib import Path
import argparse, os, subprocess, sys, time
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
# When this file is executed directly as `python scripts/refresh_target_peers.py`,
# Python puts only the scripts directory on sys.path. Add the project root so
# absolute imports such as `from scripts.dynamic_peer_engine ...` work reliably.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA=ROOT/'data'
PYTHON=sys.executable


def _run(args):
    print('>>>',' '.join(map(str,args)),flush=True)
    return subprocess.call([PYTHON,*args],cwd=str(ROOT))


def main():
    ap=argparse.ArgumentParser(description='Refresh only the selected company peer set, Bronze-safe')
    ap.add_argument('ticker')
    ap.add_argument('--delay',type=float,default=float(os.getenv('VNSTOCK_TICKER_DELAY','3.0')))
    ap.add_argument('--retry',type=int,default=3)
    ap.add_argument('--wait',type=int,default=45)
    args=ap.parse_args()
    t=str(args.ticker).upper().strip()
    from scripts.dynamic_peer_engine import select_dynamic_peers
    p=select_dynamic_peers(t)
    if p is None or p.empty or 'Ticker' not in p.columns:
        print(f'ERROR - no peer set resolved for {t}.'); return 2
    peers=[]
    for x in p['Ticker'].astype(str).str.upper().str.strip().tolist():
        if x and x!=t and x not in peers: peers.append(x)
    if not peers:
        print(f'ERROR - peer set empty for {t}.'); return 2
    print('='*66)
    print(f'V8.72.1 TARGET PEER REFRESH | {t}')
    print('Peers:', ', '.join(peers))
    print(f'Bronze safe: worker=1 | delay={args.delay:.1f}s | retry={args.retry}')
    print('='*66)
    os.environ['VNSTOCK_WORKERS']='1'; os.environ['VNSTOCK_TICKER_DELAY']=str(args.delay)
    failed=[]
    for i,x in enumerate(peers,1):
        ok=False
        for attempt in range(1,max(1,args.retry)+1):
            print(f'\n[{i}/{len(peers)}] {x} | attempt {attempt}/{args.retry}')
            rc=_run(['scripts/refresh_vnstock_multisector.py',x,'--workers','1','--ticker-delay',str(args.delay)])
            if rc==0:
                ok=True; break
            if attempt<args.retry:
                w=args.wait*attempt
                print(f'  -> wait {w}s before retry')
                time.sleep(w)
        if not ok: failed.append(x)
    print('\n>>> Rebuild peer map and benchmark for',t)
    _run(['scripts/dynamic_peer_engine.py',t])
    _run(['scripts/sector_benchmark_engine.py',t])
    if failed:
        pd.DataFrame({'Ticker':failed}).to_csv(DATA/f'failed_peers_{t}.csv',index=False,encoding='utf-8-sig')
        print('WARNING - failed peers:', ', '.join(failed))
        print(f'Saved: data/failed_peers_{t}.csv')
    print('DONE - target peer refresh completed.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
