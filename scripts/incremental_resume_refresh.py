from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import argparse, os, subprocess, sys, time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; CFG=ROOT/'config'
PYTHON=sys.executable
VERSION='8.74.1'


def _num(v):
    try:
        x=float(v)
        return x if np.isfinite(x) else np.nan
    except Exception:
        return np.nan


def _parser_version(v):
    try:
        parts=str(v).strip().lstrip(chr(86)+chr(118)).split(chr(46))
        return float(parts[0]+chr(46)+parts[1]) if len(parts) >= 2 else float(parts[0])
    except Exception:
        return 0.0


def _read(path):
    try:return pd.read_csv(path)
    except Exception:return pd.DataFrame()


def _periods(row):
    return str(row.get('Revenue_Periods','')), str(row.get('NPAT_Periods',''))


def _core_quality(row):
    """Classify a non-bank row without weakening the strict CURRENT standard."""
    if row is None:return 'NO_SNAPSHOT'
    rev=_num(row.get('Revenue')); npat=_num(row.get('NPAT'))
    assets=_num(row.get('TotalAssets')); equity=_num(row.get('Equity'))
    rb=str(row.get('Revenue_Basis','')).upper(); nb=str(row.get('NPAT_Basis','')).upper()
    rp,np_= _periods(row)
    expected='2025-Q3'+chr(124)+'2025-Q4'+chr(124)+'2026-Q1'+chr(124)+'2026-Q2'
    if np.isfinite(rev) and rev==0:return 'ZERO_REVENUE'
    core=(np.isfinite(rev) and rev!=0 and np.isfinite(npat) and np.isfinite(assets) and assets>0 and np.isfinite(equity))
    ttm=(rb=='TTM4Q' and nb=='TTM4Q')
    if core and ttm and rp==expected and np_==expected and _parser_version(row.get('ParserVersion'))>=8.70:return 'CURRENT'
    if core and ttm and rp and np_:return 'STALE_VALID'
    return 'INCOMPLETE'


def _latest_company_snapshot():
    """Prefer usable durable data over a newer invalid checkpoint row."""
    parts=[]
    for source_rank,p in enumerate([DATA/'_checkpoint_company_snapshot.csv', DATA/'company_snapshot.csv']):
        x=_read(p)
        if len(x) and 'Ticker' in x.columns:
            x=x.copy(); x['Ticker']=x['Ticker'].astype(str).str.upper().str.strip(); x['_source_rank']=source_rank
            parts.append(x)
    if not parts:return pd.DataFrame()
    x=pd.concat(parts,ignore_index=True,sort=False)
    x['_quality_rank']=x.apply(lambda r:{'CURRENT':4,'STALE_VALID':3,'ZERO_REVENUE':2,'INCOMPLETE':1}.get(_core_quality(r),0),axis=1)
    x['_dt']=pd.to_datetime(x.get('RetrievedAt'),errors='coerce',utc=True) if 'RetrievedAt' in x.columns else pd.NaT
    # Quality first; durable snapshot wins ties; newest row wins within same quality/source.
    x=x.sort_values(['Ticker','_quality_rank','_source_rank','_dt'])
    return x.drop_duplicates('Ticker',keep='last').drop(columns=['_dt','_quality_rank','_source_rank'],errors='ignore')


def _company_valid(row):
    return _core_quality(row)=='CURRENT'


def _bank_valid(row):
    if row is None:return False
    # Require all core bank fields to exist and be finite; the old validator
    # accidentally passed rows when a required column was absent.
    for k in ['TotalAssets','Equity','ROE']:
        if k not in row.index:return False
        v=_num(row.get(k))
        if not np.isfinite(v):return False
    return True


def _raw_count(ticker):
    return sum((DATA/'raw'/f'{ticker}_{k}.csv').exists() for k in ['income','balance','cashflow','ratio'])


def _raw_quality(ticker):
    """Parse existing raw only. No network calls. Used when snapshot is absent/incomplete."""
    if _raw_count(ticker)==0:return 'NO_RAW'
    try:
        import rebuild_multisector_from_raw as offline
        row,_,_,status=offline.build_ticker(ticker)
        if row is None:return 'NO_RAW'
        return status if status in {'CURRENT','STALE_VALID','ZERO_REVENUE'} else 'INCOMPLETE_RAW'
    except Exception:
        return 'INCOMPLETE_RAW'


def _nonbank_state(ticker,row):
    q=_core_quality(row)
    if q in {'CURRENT','STALE_VALID','ZERO_REVENUE'}:return q
    # Snapshot cannot distinguish stale/zero when those rows were never committed.
    # Parse local raw to classify quality without touching the network.
    return _raw_quality(ticker)

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
    ap=argparse.ArgumentParser(description='V8.74.1 incremental/resumable Vnstock Sponsor refresh with raw-aware data-quality states')
    ap.add_argument('--force',action='store_true',help='Refresh all active tickers instead of only missing/incomplete ones')
    ap.add_argument('--retry',type=int,default=3,help='Retry attempts for one failed ticker')
    ap.add_argument('--wait',type=int,default=45,help='Base wait seconds before retry; grows linearly')
    ap.add_argument('--ticker-delay',type=float,default=float(os.getenv('VNSTOCK_TICKER_DELAY','3.0')))
    ap.add_argument('--skip-banks',action='store_true')
    ap.add_argument('--only-failed',action='store_true',help='Retry only data/failed_tickers.csv')
    ap.add_argument('--retry-incomplete',action='store_true',help='Explicitly retry non-current tickers; default run preserves stale/incomplete/no-raw states')
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

    banks=[]; nonbanks=[]; skipped=[]; quality=[]
    for _,r in u.iterrows():
        t=str(r['Ticker']); typ=str(r.get('EntityType','')).upper()
        if typ=='BANK':
            bv=_bank_valid(bm.get(t)); state='BANK_CURRENT' if bv else ('BANK_NO_SNAPSHOT' if bm.get(t) is None else 'BANK_INCOMPLETE')
            quality.append({'Ticker':t,'EntityType':'BANK','DataQualityStatus':state,'RawFiles':0,'UpdatedAt':datetime.now(timezone.utc).isoformat()})
            if args.skip_banks: skipped.append((t,'BANK_SKIP_OPTION'))
            elif args.force or (args.retry_incomplete and not bv) or (bm.get(t) is None): banks.append(t)
            else: skipped.append((t,state))
        else:
            state=_nonbank_state(t,cm.get(t)); quality.append({'Ticker':t,'EntityType':typ or 'NONBANK','DataQualityStatus':state,'RawFiles':_raw_count(t),'UpdatedAt':datetime.now(timezone.utc).isoformat()})
            if args.force or (args.retry_incomplete and state!='CURRENT'):
                nonbanks.append(t)
            else:
                skipped.append((t,state))
    pd.DataFrame(quality).to_csv(DATA/'data_quality_status.csv',index=False,encoding='utf-8-sig')

    print('='*66)
    print('V8.74.1 INCREMENTAL / RESUME REFRESH - VNSTOCK SPONSOR')
    print(f'Universe={len(u)} | preserved/skipped={len(skipped)} | banks to refresh={len(banks)} | non-banks to refresh={len(nonbanks)}')
    qc=pd.DataFrame(quality)['DataQualityStatus'].value_counts(); print('Quality: '+' | '.join(f'{k}={v}' for k,v in qc.items()))
    workers=max(1,min(int(os.getenv('VNSTOCK_WORKERS','2')),2)); print(f'Silver safety: workers={workers} | ticker delay={args.ticker_delay:.1f}s | retry={args.retry} | wait base={args.wait}s')
    print('Default run does NOT re-download CURRENT, STALE_VALID, ZERO_REVENUE, INCOMPLETE or NO_RAW rows.')
    print('Use --retry-incomplete for an explicit retry window, or --force for all active tickers.')
    print('='*66)

    os.environ['VNSTOCK_WORKERS']=str(workers); os.environ['VNSTOCK_TICKER_DELAY']=str(args.ticker_delay)
    status=[]; failed=[]

    # Banks are few. Run only those missing/incomplete, in fundamentals mode first;
    # price history remains intact and can be updated separately when desired.
    if banks:
        rc=_run(['scripts/refresh_vnstock.py','--mode','fundamentals','--tickers',','.join(banks),'--workers',str(workers)])
        if rc:
            print('WARNING - bank incremental refresh returned non-zero; existing bank data were preserved.')

    total=len(nonbanks)
    for i,t in enumerate(nonbanks,1):
        ok=False; last=''
        for attempt in range(1,max(1,args.retry)+1):
            print(f'\n[{i}/{total}] {t} | attempt {attempt}/{max(1,args.retry)}',flush=True)
            rc=_run(['scripts/refresh_vnstock_multisector.py',t,'--workers',str(workers),'--ticker-delay',str(args.ticker_delay)])
            ok=(rc==0 and _validate_ticker(t))
            if ok:
                last='OK_VALIDATED'; break
            if rc==0:
                last='DEFERRED_INCOMPLETE'
                print('  - incomplete snapshot; defer to a later incremental run',flush=True)
                break
            last=f'PROCESS_ERROR rc={rc}'
            if attempt < max(1,args.retry):
                wait=args.wait*attempt
                print(f'  - retry after {wait}s (process/API recovery window)',flush=True)
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
