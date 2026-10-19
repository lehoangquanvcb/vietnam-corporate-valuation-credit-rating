from __future__ import annotations
from pathlib import Path
from datetime import datetime
import argparse, sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
DATA=ROOT/'data'; RAW=DATA/'raw'; CFG=ROOT/'config'; FUND_PARTS=DATA/'fundamentals_long'
FUND_PARTS.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
import refresh_vnstock_multisector as parser

PARSER_VERSION='8.74.1'
SOURCE_MODE='VNSTOCK_SPONSOR_RAW_RECOVERY'

def now(): return datetime.now().astimezone().isoformat(timespec='seconds')

def read_raw(t,kind):
    p=RAW/f'{t}_{kind}.csv'
    if not p.exists(): return pd.DataFrame()
    try: return pd.read_csv(p)
    except Exception: return pd.DataFrame()

def semantic_snapshot(source,metric):
    ids=parser.SEMANTIC_IDS[metric]; kind=parser._metric_kind(metric)
    if source is None or source.empty:
        return np.nan,{"row":"","basis":"EMPTY_SOURCE","periods":[]}
    x=parser.flat(source)
    if parser._semantic_col(x) is not None:
        return parser._exact_semantic_snapshot(x,ids,kind,True)
    cols={str(c).strip().upper():c for c in x.columns}
    c=next((cols[str(sid).strip().upper()] for sid in ids if str(sid).strip().upper() in cols),None)
    if c is None:
        return np.nan,{"row":"","basis":"SEMANTIC_ID_NOT_FOUND","periods":[]}
    pc=next((z for z in x.columns if str(z).strip().lower()=="period"),None)
    if pc is None:
        return np.nan,{"row":str(c),"basis":"PERIOD_COLUMN_NOT_FOUND","periods":[]}
    tidy=pd.DataFrame({"period":x[pc],"id":str(c),"value":x[c]})
    return parser._exact_semantic_snapshot(tidy,ids,kind,True)

def snapshot_quality(row):
    """Classify parsed raw data; CURRENT remains strict, stale/zero are preserved explicitly."""
    rev=pd.to_numeric(row.get("Revenue"),errors="coerce")
    npat=pd.to_numeric(row.get("NPAT"),errors="coerce")
    assets=pd.to_numeric(row.get("TotalAssets"),errors="coerce")
    equity=pd.to_numeric(row.get("Equity"),errors="coerce")
    rb=str(row.get("Revenue_Basis","")).upper(); nb=str(row.get("NPAT_Basis","")).upper()
    rp=str(row.get("Revenue_Periods","") or ""); np_=str(row.get("NPAT_Periods","") or "")
    expected="2025-Q3"+chr(124)+"2025-Q4"+chr(124)+"2026-Q1"+chr(124)+"2026-Q2"
    balance_ok=pd.notna(assets) and assets>0 and pd.notna(equity)
    flow_meta=(rb in ("TTM4Q","TTM") and nb in ("TTM4Q","TTM") and bool(rp) and bool(np_))
    if pd.notna(rev) and rev==0 and pd.notna(npat) and balance_ok and flow_meta:
        return "ZERO_REVENUE"
    core=pd.notna(rev) and rev!=0 and pd.notna(npat) and balance_ok
    if core and flow_meta and rp==expected and np_==expected:return "CURRENT"
    if core and flow_meta:return "STALE_VALID"
    return "INCOMPLETE"

def snapshot_usable(row):
    return snapshot_quality(row)=="CURRENT"

def build_ticker(t):
    from scripts.financial_evidence import repair_snapshot, history, normalize_raw
    u=pd.read_csv(CFG/'company_universe.csv');z=u[u.Ticker.astype(str).str.upper().eq(t)]
    typ=str(z.iloc[0].EntityType) if len(z) else 'CORPORATE'
    sources={ds:read_raw(t,ds) for ds in ['ratio','balance','income','cashflow']}
    if all(x.empty for x in sources.values()):return None,[],None,'NO_RAW'
    row=repair_snapshot(t,typ,{'Ticker':t,'RetrievedAt':now(),'DataType':'ACTUAL',
        'SourceMode':SOURCE_MODE,'ParserVersion':PARSER_VERSION,'ParserLog':'RECOVERED_FROM_RAW_V8741_EVIDENCE_8118'})
    h=history(t,typ).to_dict('records');parts=[]
    for ds,df in sources.items():
        if df.empty:continue
        z=normalize_raw(df,f'data/raw/{t}_{ds}.csv');z=z[z.Value.notna()].copy()
        z['Ticker']=t;z['Dataset']=ds;z['DataType']='ACTUAL';z['SourceMode']=SOURCE_MODE
        parts.append(z[['Ticker','Period','Dataset','Field','Value','DataType','SourceMode']])
    long_df=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    row={k:v for k,v in row.items() if not k.startswith('_')}
    return row,h,long_df,snapshot_quality(row)

def main():
    ap=argparse.ArgumentParser(description='V8.74.1 offline multisector rebuild from existing raw files with quality states')
    ap.add_argument('--tickers',default='')
    ap.add_argument('--tickers-file',default='')
    ap.add_argument('--compact',action='store_true')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    u=pd.read_csv(CFG/'company_universe.csv'); u['Ticker']=u.Ticker.astype(str).str.upper().str.strip()
    if 'Active' in u.columns: u=u[pd.to_numeric(u.Active,errors='coerce').fillna(1).eq(1)]
    u=u[~u.EntityType.astype(str).str.upper().eq('BANK')]
    if args.tickers.strip() or args.tickers_file.strip():
        raw_wanted=args.tickers.strip()
        if args.tickers_file.strip():
            file_wanted=Path(args.tickers_file).read_text(encoding='utf-8-sig').replace(chr(10),',').replace(chr(13),',')
            raw_wanted=(raw_wanted+','+file_wanted) if raw_wanted else file_wanted
        wanted={x.strip().upper() for x in raw_wanted.split(',') if x.strip()}
        u=u[u.Ticker.isin(wanted)]
    tickers=u.Ticker.dropna().unique().tolist()
    snaps=[]; manifest=[]; compact=[]; bad=[]; counts={}; history_rows=[]
    for i,t in enumerate(tickers,1):
        row,h,long_df,status=build_ticker(t)
        if row is None:
            counts['NO_RAW']=counts.get('NO_RAW',0)+1
            print(f'[{i}/{len(tickers)}] {t}: NO_RAW'); bad.append(t); continue
        counts[status]=counts.get(status,0)+1
        row['DataQualityStatus']=status
        print(f"[{i}/{len(tickers)}] {t}: {status} | Revenue={row.get('Revenue')} | NPAT={row.get('NPAT')} | Assets={row.get('TotalAssets')} | Equity={row.get('Equity')} | Basis={row.get('Revenue_Basis')}/{row.get('NPAT_Basis')} | Periods={row.get('Revenue_Periods')}")
        if status=='INCOMPLETE':
            bad.append(t); continue
        snaps.append(row)
        history_rows.extend(h)
        if not args.dry_run and long_df is not None and len(long_df):
            fp=FUND_PARTS/f'{t}.csv'; long_df.to_csv(fp,index=False,encoding='utf-8-sig')
            manifest.append({'Ticker':t,'Rows':len(long_df),'Path':str(fp.relative_to(ROOT)).replace(chr(92),'/'),'RetrievedAt':now()})
            if args.compact: compact.append(long_df)
    if args.dry_run:
        print('QUALITY: '+' | '.join(f'{k}={v}' for k,v in counts.items()))
        print(f'DRY RUN DONE | preserved={len(snaps)} | incomplete/no-raw={len(bad)} | total={len(tickers)}')
        if bad: print('INCOMPLETE_FIRST_30='+','.join(bad[:30]))
        return
    snap_path=DATA/"company_snapshot.csv"
    old=pd.read_csv(snap_path) if snap_path.exists() else pd.DataFrame()
    new=pd.DataFrame(snaps)
    if len(new):
        if len(old) and "Ticker" in old.columns:
            old_t=old["Ticker"].astype(str).str.upper()
            new_t=new["Ticker"].astype(str).str.upper()
            old=old[~old_t.isin(set(new_t))]
        merged=pd.concat([old,new],ignore_index=True)
        merged=merged.sort_values("Ticker").drop_duplicates("Ticker",keep="last")
        merged.to_csv(snap_path,index=False,encoding="utf-8-sig")

    if history_rows:
        hp=DATA/'company_history_long.csv'
        old_h=pd.read_csv(hp) if hp.exists() else pd.DataFrame()
        new_h=pd.DataFrame(history_rows)
        if len(old_h):old_h=old_h[~old_h.Ticker.astype(str).str.upper().isin(new_h.Ticker.unique())]
        pd.concat([old_h,new_h],ignore_index=True).to_csv(hp,index=False,encoding='utf-8-sig')

    manifest_path=DATA/"vnstock_company_fundamentals_manifest.csv"
    if manifest:
        old_manifest=pd.read_csv(manifest_path) if manifest_path.exists() else pd.DataFrame()
        new_manifest=pd.DataFrame(manifest)
        if len(old_manifest) and "Ticker" in old_manifest.columns:
            old_mt=old_manifest["Ticker"].astype(str).str.upper()
            new_mt=new_manifest["Ticker"].astype(str).str.upper()
            old_manifest=old_manifest[~old_mt.isin(set(new_mt))]
        merged_manifest=pd.concat([old_manifest,new_manifest],ignore_index=True)
        merged_manifest.sort_values("Ticker").drop_duplicates("Ticker",keep="last").to_csv(manifest_path,index=False,encoding="utf-8-sig")

    if args.compact and compact:
        raise RuntimeError("--compact disabled for safe subset recovery; rebuild compact layer separately after recovery")
    print('QUALITY: '+' | '.join(f'{k}={v}' for k,v in counts.items()))
    print(f'DONE V8.74.1 OFFLINE RECOVERY | preserved={len(snaps)} | incomplete/no-raw={len(bad)} | total={len(tickers)}')
    if bad: print('INCOMPLETE_FIRST_30='+','.join(bad[:30]))

if __name__=='__main__': main()
