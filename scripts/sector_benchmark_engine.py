import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
import pandas as pd, numpy as np
from scripts.universal_data import universe,bank_snapshot,generic_snapshot,read_csv,period_date
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'

def sector_universe_tickers(ticker):
    """Broad industry universe (not the dynamic peer subset)."""
    u=universe();t=str(ticker).upper();z=u[u.Ticker.eq(t)]
    if z.empty:return [t]
    r=z.iloc[0];typ=r.EntityType
    if typ=='BANK':return u[u.EntityType.eq('BANK')].Ticker.tolist()
    if typ=='SECURITIES':return u[u.EntityType.eq('SECURITIES')].Ticker.tolist()
    if 'ICBCode2' in u.columns and pd.notna(r.get('ICBCode2')):
        p=u[(u.EntityType.eq('CORPORATE')) & (u.ICBCode2.astype(str).eq(str(r.get('ICBCode2'))))]
        if len(p)>=6:return p.Ticker.tolist()
    sec=str(r.Sector);return u[(u.EntityType.eq('CORPORATE')) & (u.Sector.astype(str).eq(sec))].Ticker.tolist()

def industry_tickers(ticker):
    """Compatibility name: benchmarks now use a dynamic similarity peer group."""
    try:
        from scripts.dynamic_peer_engine import dynamic_peer_tickers
        p=dynamic_peer_tickers(ticker,include_target=True)
        if len(p)>1:return p
    except Exception:
        pass
    return sector_universe_tickers(ticker)

def industry_label(ticker):
    try:
        from scripts.dynamic_peer_engine import dynamic_peer_label
        return dynamic_peer_label(ticker)
    except Exception:
        u=universe();z=u[u.Ticker.eq(str(ticker).upper())]
        if z.empty:return 'Ngành'
        r=z.iloc[0]
        if r.EntityType=='BANK':return 'Trung bình các ngân hàng niêm yết/ĐKGD'
        if r.EntityType=='SECURITIES':return 'Trung bình ngành công ty chứng khoán niêm yết/ĐKGD'
        return f"Trung bình ngành {r.Sector}"

def industry_snapshot(ticker):
    u=universe();z=u[u.Ticker.eq(str(ticker).upper())]
    if z.empty:return pd.DataFrame()
    typ=z.iloc[0].EntityType;s=bank_snapshot() if typ=='BANK' else generic_snapshot()
    if s.empty:return s
    s=s.copy();s['Ticker']=s.Ticker.astype(str).str.upper();return s[s.Ticker.isin(industry_tickers(ticker))].copy()

def industry_metric_history(ticker,metric):
    u=universe();z=u[u.Ticker.eq(str(ticker).upper())]
    if z.empty:return pd.DataFrame()
    typ=z.iloc[0].EntityType;x=read_csv(DATA/'bank_history_long.csv') if typ=='BANK' else read_csv(DATA/'company_history_long.csv')
    if x.empty:return pd.DataFrame()
    peers=industry_tickers(ticker);x=x[x.Ticker.astype(str).str.upper().isin(peers)&x.Metric.astype(str).eq(str(metric))].copy()
    x['Value']=pd.to_numeric(x.Value,errors='coerce');x=x.dropna(subset=['Value']);x['PeriodDate']=x.Period.map(period_date);x=x.dropna(subset=['PeriodDate'])
    if x.empty:return x
    return x.groupby('PeriodDate',as_index=False).agg(IndustryMean=('Value','mean'),IndustryMedian=('Value','median'),IndustryCount=('Ticker','nunique'))

def build_sector_benchmarks(target_ticker=None):
    u=universe(); rows=[]
    metrics=['ROE','ROA','PB','PE','DebtEquity','CurrentRatio','NPL','CAR','CASA','NIM','LDR','Revenue','NPAT','TotalAssets']
    targets=u.Ticker.tolist()
    if target_ticker:
        tt=str(target_ticker).upper().strip(); targets=[tt] if tt in set(u.Ticker.astype(str).str.upper()) else []
    for t in targets:
        s=industry_snapshot(t)
        if s.empty:continue
        for m in metrics:
            if m not in s.columns:continue
            v=pd.to_numeric(s[m],errors='coerce').replace([float('inf'),float('-inf')],pd.NA).dropna()
            if len(v):rows.append({'Ticker':t,'Sector':u.loc[u.Ticker.eq(t),'Sector'].iloc[0],'Metric':m,'IndustryMean':v.mean(),'IndustryMedian':v.median(),'IndustryCount':len(v),'BenchmarkType':'DYNAMIC_PEER'})
    z=pd.DataFrame(rows); path=DATA/'industry_benchmarks.csv'
    if target_ticker:
        tt=str(target_ticker).upper().strip()
        try: old=pd.read_csv(path); old=old[old.Ticker.astype(str).str.upper().ne(tt)] if 'Ticker' in old.columns else pd.DataFrame()
        except Exception: old=pd.DataFrame()
        z=pd.concat([old,z],ignore_index=True,sort=False)
    z.to_csv(path,index=False,encoding='utf-8-sig');return z

if __name__=='__main__':
    import sys
    target=sys.argv[1] if len(sys.argv)>1 and str(sys.argv[1]).upper() not in {'ALL','--ALL'} else None
    z=build_sector_benchmarks(target);print(f'OK - benchmark updated for {target or "ALL"}')
