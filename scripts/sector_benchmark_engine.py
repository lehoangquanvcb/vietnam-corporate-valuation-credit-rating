import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
import pandas as pd, numpy as np
from scripts.universal_data import universe,bank_snapshot,generic_snapshot,read_csv,period_date
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'

MIN_BENCHMARK_PEERS=5


def sector_universe_tickers(ticker):
    """Broad industry universe (fallback only; not the preferred peer subset)."""
    u=universe();t=str(ticker).upper();z=u[u.Ticker.eq(t)]
    if z.empty:return [t]
    r=z.iloc[0];typ=r.EntityType
    if typ=='BANK':return u[u.EntityType.eq('BANK')].Ticker.tolist()
    if typ=='SECURITIES':return u[u.EntityType.eq('SECURITIES')].Ticker.tolist()
    if 'ICBCode2' in u.columns and pd.notna(r.get('ICBCode2')):
        p=u[(u.EntityType.eq('CORPORATE')) & (u.ICBCode2.astype(str).eq(str(r.get('ICBCode2'))))]
        if len(p)>=MIN_BENCHMARK_PEERS+1:return p.Ticker.tolist()
    sec=str(r.Sector);return u[(u.EntityType.eq('CORPORATE')) & (u.Sector.astype(str).eq(sec))].Ticker.tolist()


def industry_tickers(ticker):
    """Target + its selected dynamic peers, retained for UI peer-position tables."""
    try:
        from scripts.dynamic_peer_engine import dynamic_peer_tickers
        p=dynamic_peer_tickers(ticker,include_target=True)
        if len(p)>1:return p
    except Exception:
        pass
    return sector_universe_tickers(ticker)


def benchmark_peer_tickers(ticker):
    """Peer tickers only. The target is NEVER included in benchmark statistics."""
    t=str(ticker).upper().strip()
    return [x for x in industry_tickers(ticker) if str(x).upper().strip()!=t]


def industry_label(ticker):
    try:
        from scripts.dynamic_peer_engine import dynamic_peer_label
        return dynamic_peer_label(ticker)
    except Exception:
        u=universe();z=u[u.Ticker.eq(str(ticker).upper())]
        if z.empty:return 'Nhóm peer'
        r=z.iloc[0]
        if r.EntityType=='BANK':return 'Nhóm peer ngân hàng'
        if r.EntityType=='SECURITIES':return 'Nhóm peer công ty chứng khoán'
        return f"Nhóm peer {r.Sector}"


def _snapshot_all(ticker):
    u=universe();z=u[u.Ticker.eq(str(ticker).upper())]
    if z.empty:return pd.DataFrame()
    typ=z.iloc[0].EntityType;s=bank_snapshot() if typ=='BANK' else generic_snapshot()
    if s.empty:return s
    s=s.copy();s['Ticker']=s.Ticker.astype(str).str.upper();return s


def industry_snapshot(ticker):
    """Target + peers for UI display; benchmark functions filter target separately."""
    s=_snapshot_all(ticker)
    if s.empty:return s
    return s[s.Ticker.isin(industry_tickers(ticker))].copy()


def benchmark_peer_snapshot(ticker):
    s=_snapshot_all(ticker)
    if s.empty:return s
    return s[s.Ticker.isin(benchmark_peer_tickers(ticker))].copy()


def industry_metric_history(ticker,metric):
    """Historical peer benchmark excluding target and suppressing underpowered means."""
    u=universe();z=u[u.Ticker.eq(str(ticker).upper())]
    if z.empty:return pd.DataFrame()
    typ=z.iloc[0].EntityType;x=read_csv(DATA/'bank_history_long.csv') if typ=='BANK' else read_csv(DATA/'company_history_long.csv')
    if x.empty:return pd.DataFrame()
    peers=benchmark_peer_tickers(ticker)
    if not peers:return pd.DataFrame()
    x=x[x.Ticker.astype(str).str.upper().isin(peers)&x.Metric.astype(str).eq(str(metric))].copy()
    x['Value']=pd.to_numeric(x.Value,errors='coerce');x=x.dropna(subset=['Value']);x['PeriodDate']=x.Period.map(period_date);x=x.dropna(subset=['PeriodDate'])
    if x.empty:return x
    z=x.groupby('PeriodDate',as_index=False).agg(IndustryMean=('Value','mean'),IndustryMedian=('Value','median'),IndustryCount=('Ticker','nunique'))
    # A line based on 1-4 peers is visually misleading; do not plot it as "industry average".
    return z[z['IndustryCount'].ge(MIN_BENCHMARK_PEERS)].copy()


def build_sector_benchmarks(target_ticker=None):
    u=universe(); rows=[]
    metrics=['ROE','ROA','PB','PE','DebtEquity','CurrentRatio','NPL','CAR','CASA','NIM','LDR','Revenue','NPAT','TotalAssets']
    targets=u.Ticker.tolist()
    if target_ticker:
        tt=str(target_ticker).upper().strip(); targets=[tt] if tt in set(u.Ticker.astype(str).str.upper()) else []
    for t in targets:
        s=benchmark_peer_snapshot(t)
        if s.empty:continue
        for m in metrics:
            if m not in s.columns:continue
            v=pd.to_numeric(s[m],errors='coerce').replace([float('inf'),float('-inf')],pd.NA).dropna()
            if len(v)>=MIN_BENCHMARK_PEERS:
                rows.append({'Ticker':t,'Sector':u.loc[u.Ticker.eq(t),'Sector'].iloc[0],'Metric':m,
                             'IndustryMean':v.mean(),'IndustryMedian':v.median(),'IndustryCount':len(v),
                             'BenchmarkType':'DYNAMIC_PEER_EX_TARGET'})
            else:
                rows.append({'Ticker':t,'Sector':u.loc[u.Ticker.eq(t),'Sector'].iloc[0],'Metric':m,
                             'IndustryMean':np.nan,'IndustryMedian':np.nan,'IndustryCount':len(v),
                             'BenchmarkType':'INSUFFICIENT_PEER_DATA'})
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
    z=build_sector_benchmarks(target);print(f'OK - benchmark updated for {target or "ALL"}; target excluded; min peers={MIN_BENCHMARK_PEERS}')
