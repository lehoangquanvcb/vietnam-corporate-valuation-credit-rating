from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import argparse, os, subprocess, sys, time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; CFG=ROOT/'config'
PYTHON=sys.executable
VERSION='8.72'


def _num(v):
    try:
        x=float(v)
        return x if np.isfinite(x) else np.nan
    except Exception:
        return np.nan


def _parser_version(v):
    try:return float(str(v).strip())
    except Exception:return 0.0


def _read(path):
    try:return pd.read_csv(path)
    except Exception:return pd.DataFrame()


def _latest_company_snapshot():
    """Combine durable snapshot + valid checkpoint from an interrupted run."""
    parts=[]
    for p in [DATA/'company_snapshot.csv', DATA/'_checkpoint_company_snapshot.csv']:
        x=_read(p)
        if len(x) and 'Ticker' in x.columns:
            x=x.copy(); x['Ticker']=x['Ticker'].astype(str).str.upper().str.strip()
            parts.append(x)
    if not parts:return pd.DataFrame()
    x=pd.concat(parts,ignore_index=True,sort=False)
    # Prefer the newest retrieved row, otherwise later concatenated row.
    if 'RetrievedAt' in x.columns:
        x['_dt']=pd.to_datetime(x['RetrievedAt'],errors='coerce',utc=True)
        x=x.sort_values(['Ticker','_dt'])
    return x.drop_duplicates('Ticker',keep='last').drop(columns=['_dt'],errors='ignore')


def _company_valid(row):
    if row is None:return False
    if _parser_version(row.get('ParserVersion')) < 8.70:return False
    for k in ['Revenue','NPAT','TotalAssets','Equity']:
        v=_num(row.get(k))
        if not np.isfinite(v) or v<=0:return False
    # Flow provenance is mandatory after the strict period-aware parser.
    if str(row.get('Revenue_Basis','')).upper()!='TTM4Q':return False
    if str(row.get('NPAT_Basis','')).upper()!='TTM4Q':return False
    return True


def _bank_valid(row):
    if row is None:return False
    # Bank engine is separate and does not share ParserVersion. Require core actuals.
    for k in ['TotalAssets','Equity','ROE']:
        if k in row.index:
            v=_num(row.get(k))
            if not np.isfinite(v):return False
    return True


def _row_map(df):
    if df is None or not len(df) or 'Ticker' not in df.columns:return {}
    q=df.copy(); q['Ticker']=q['Ticker'].astype(str).str.upper().str.strip()
    return {str(r.Ticker):r for _,r in q.drop_duplicates('Ticker',keep='last').iterrows()}


def _run(args):
    print('>>>',' '.join(map(str,args)),flush=True)
    return subprocess.call([PYTHON,*args],cwd=str(ROOT))


def _validate_ticker(ticker):
    x=_latest_company_snapshot(); m=_row_map(x)
    return _company_valid(m.get(ticker))


def _write_state(rows, failed):
    pd.DataFrame(rows).to_csv(DATA/'incremental_refresh_status.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame({'Ticker':sorted(set(failed))}).to_csv(DATA/'failed_tickers.csv',index=False,encoding='utf-8-sig')


def main():
    ap=argparse.ArgumentParser(description='V8.72 incremental/resumable Vnstock Bronze refresh')
    ap.add_argument('--force',action='store_true',help='Refresh all active tickers instead of only missing/incomplete ones')
    ap.add_argument('--retry',type=int,default=3,help='Retry attempts for one failed ticker')
    ap.add_argument('--wait',type=int,default=45,help='Base wait seconds before retry; grows linearly')
    ap.add_argument('--ticker-delay',type=float,default=float(os.getenv('VNSTOCK_TICKER_DELAY','3.0')))
    ap.add_argument('--skip-banks',action='store_true')
    ap.add_argument('--only-failed',action='store_true',help='Retry only data/failed_tickers.csv')
    args=ap.parse_args()

    u=_read(CFG/'company_universe.csv')
    if not len(u) or 'Ticker' not in u.columns:
        print('ERROR - config/company_universe.csv missing/empty.'); return 2
    u=u.copy(); u['Ticker']=u['Ticker'].astype(str).str.upper().str.strip()
    if 'Active' in u.columns:u=u[pd.to_numeric(u['Active'],errors='coerce').fillna(1).eq(1)]

    if args.only_failed:
        f=_read(DATA/'failed_tickers.csv')
        wanted=set(f['Ticker'].astype(str).str.upper().str.strip()) if len(f) and 'Ticker' in f.columns else set()
        u=u[u['Ticker'].isin(wanted)]

    cs=_latest_company_snapshot(); cm=_row_map(cs)
    bs=_read(DATA/'bank_snapshot.csv'); bm=_row_map(bs)

    banks=[]; nonbanks=[]; skipped=[]
    for _,r in u.iterrows():
        t=str(r['Ticker']); typ=str(r.get('EntityType','')).upper()
        if typ=='BANK':
            if args.skip_banks: skipped.append((t,'BANK_SKIP_OPTION'))
            elif args.force or not _bank_valid(bm.get(t)): banks.append(t)
            else: skipped.append((t,'BANK_ALREADY_COMPLETE'))
        else:
            if args.force or not _company_valid(cm.get(t)): nonbanks.append(t)
            else: skipped.append((t,'COMPANY_ALREADY_COMPLETE'))

    print('='*66)
    print('V8.72 INCREMENTAL / RESUME REFRESH')
    print(f'Universe={len(u)} | already complete={len(skipped)} | banks to refresh={len(banks)} | non-banks to refresh={len(nonbanks)}')
    print(f'Bronze safety: workers=1 | ticker delay={args.ticker_delay:.1f}s | retry={args.retry} | wait base={args.wait}s')
    print('Existing completed tickers are NOT re-downloaded.')
    print('='*66)

    os.environ['VNSTOCK_WORKERS']='1'; os.environ['VNSTOCK_TICKER_DELAY']=str(args.ticker_delay)
    status=[]; failed=[]

    # Banks are few. Run only those missing/incomplete, in fundamentals mode first;
    # price history remains intact and can be updated separately when desired.
    if banks:
        rc=_run(['scripts/refresh_vnstock.py','--mode','fundamentals','--tickers',','.join(banks),'--workers','1'])
        if rc:
            print('WARNING - bank incremental refresh returned non-zero; existing bank data were preserved.')

    total=len(nonbanks)
    for i,t in enumerate(nonbanks,1):
        ok=False; last=''
        for attempt in range(1,max(1,args.retry)+1):
            print(f'\n[{i}/{total}] {t} | attempt {attempt}/{max(1,args.retry)}',flush=True)
            rc=_run(['scripts/refresh_vnstock_multisector.py',t,'--workers','1','--ticker-delay',str(args.ticker_delay)])
            ok=(rc==0 and _validate_ticker(t))
            if ok:
                last='OK_VALIDATED'; break
            last=f'FAILED_OR_INCOMPLETE rc={rc}'
            if attempt < max(1,args.retry):
                wait=args.wait*attempt
                print(f'  -> retry after {wait}s (Bronze/API recovery window)',flush=True)
                time.sleep(wait)
        status.append({'Ticker':t,'Status':'OK' if ok else 'FAILED','Message':last,'UpdatedAt':datetime.now(timezone.utc).isoformat()})
        if not ok: failed.append(t)
        _write_state(status,failed)

    _write_state(status,failed)
    print('\nINCREMENTAL DOWNLOAD COMPLETE')
    print(f'Non-bank OK={sum(r["Status"]=="OK" for r in status)} | FAILED={len(failed)}')
    if failed:
        print('Failed tickers saved to data/failed_tickers.csv')
        print('Re-run later: RUN_INCREMENTAL_REFRESH_FAILED.bat')
    print('Next offline step: RUN_REBUILD_FROM_RAW.bat')
    return 0 if not failed else 0  # keep successful progress; failures are resumable

if __name__=='__main__':
    raise SystemExit(main())
