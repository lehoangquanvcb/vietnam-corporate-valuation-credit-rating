from pathlib import Path
import json, re
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; CFG=ROOT/'config'

def read_csv(path):
    try:return pd.read_csv(path)
    except Exception:return pd.DataFrame()

def universe():
    x=read_csv(CFG/'company_universe.csv')
    if len(x):
        x['Ticker']=x['Ticker'].astype(str).str.upper().str.strip()
        x=x[x.get('Active',1).fillna(1).astype(int).eq(1)]
    return x

def bank_snapshot(): return read_csv(DATA/'bank_snapshot.csv')
def generic_snapshot():
    x=read_csv(DATA/'company_snapshot.csv')
    m=read_csv(CFG/'manual_financial_inputs.csv')
    if len(x) and len(m) and 'Ticker' in x and 'Ticker' in m:
        x=x.copy(); m=m.copy()
        x['Ticker']=x['Ticker'].astype(str).str.upper(); m['Ticker']=m['Ticker'].astype(str).str.upper()
        m=m.drop_duplicates('Ticker',keep='last')
        meta_cols={'Ticker','AsOfDate','Source','DataType','Note'}
        value_cols=[c for c in m.columns if c not in meta_cols]
        x=x.merge(m,on='Ticker',how='left',suffixes=('','_Manual'))
        for c in value_cols:
            cm=c+'_Manual'
            if cm in x.columns:
                if c not in x.columns:x[c]=np.nan
                live=pd.to_numeric(x[c],errors='coerce')
                manual=pd.to_numeric(x[cm],errors='coerce')
                x[c]=live.where(live.notna(),manual)
        return x
    return x

def price_history(): return read_csv(DATA/'price_history.csv')
def generic_history(): return read_csv(DATA/'company_history_long.csv')

def get_company(ticker):
    u=universe(); t=str(ticker).upper().strip()
    z=u[u.Ticker.eq(t)]
    if z.empty:
        return {'Ticker':t,'CompanyName':t,'EntityType':'CORPORATE','Sector':'Chưa phân loại','Exchange':'N/A','PeerGroup':'Chưa phân loại','Methodology':'CORPORATE_2025','Active':1}
    return z.iloc[0].to_dict()

def get_snapshot(ticker):
    meta=get_company(ticker); t=meta['Ticker']
    if meta['EntityType']=='BANK':
        s=bank_snapshot(); z=s[s.get('Ticker',pd.Series(dtype=str)).astype(str).str.upper().eq(t)] if len(s) else pd.DataFrame()
    else:
        s=generic_snapshot(); z=s[s.get('Ticker',pd.Series(dtype=str)).astype(str).str.upper().eq(t)] if len(s) else pd.DataFrame()
    out=dict(meta)
    if len(z): out.update(z.iloc[-1].to_dict())
    return out

def entity_history(ticker):
    meta=get_company(ticker); t=meta['Ticker']
    if meta['EntityType']=='BANK': x=read_csv(DATA/'bank_history_long.csv')
    else: x=generic_history()
    if x.empty:return x
    return x[x.Ticker.astype(str).str.upper().eq(t)].copy()

def industry_tickers(ticker):
    from scripts.sector_benchmark_engine import industry_tickers as _it
    return _it(ticker)

def industry_snapshot(ticker):
    from scripts.sector_benchmark_engine import industry_snapshot as _is
    return _is(ticker)

def industry_metric_history(ticker,metric):
    from scripts.sector_benchmark_engine import industry_metric_history as _ih
    return _ih(ticker,metric)

def industry_label(ticker):
    from scripts.sector_benchmark_engine import industry_label as _il
    return _il(ticker)

def peer_tickers(ticker):
    m=get_company(ticker); u=universe()
    p=u[u.PeerGroup.astype(str).eq(str(m.get('PeerGroup')))].Ticker.astype(str).tolist()
    return p or [ticker]

def peer_snapshot(ticker):
    meta=get_company(ticker); peers=peer_tickers(ticker)
    s=bank_snapshot() if meta['EntityType']=='BANK' else generic_snapshot()
    if s.empty:return s
    s=s.copy(); s['Ticker']=s['Ticker'].astype(str).str.upper()
    return s[s.Ticker.isin(peers)].copy()

def peer_metric_history(ticker,metric):
    meta=get_company(ticker); peers=peer_tickers(ticker)
    x=read_csv(DATA/'bank_history_long.csv') if meta['EntityType']=='BANK' else generic_history()
    if x.empty:return pd.DataFrame()
    x=x[x.Ticker.astype(str).str.upper().isin(peers) & x.Metric.astype(str).eq(str(metric))].copy()
    x['Value']=pd.to_numeric(x.Value,errors='coerce'); x=x.dropna(subset=['Value'])
    if x.empty:return x
    x['PeriodDate']=x['Period'].map(period_date); x=x.dropna(subset=['PeriodDate'])
    return x.groupby('PeriodDate',as_index=False).agg(PeerMean=('Value','mean'),PeerMedian=('Value','median'),PeerCount=('Ticker','nunique'))

def period_date(v):
    s=str(v).upper(); y=re.search(r'(20\d{2})',s); q=re.search(r'Q\s*([1-4])',s)
    if not y:return pd.NaT
    yy=int(y.group(1)); mm=(int(q.group(1))-1)*3+1 if q else 1
    return pd.Timestamp(yy,mm,1)

def num(x):
    try:
        v=float(x); return v if np.isfinite(v) else None
    except:return None

def coverage(snapshot,fields):
    if not fields:return 0
    return sum(num(snapshot.get(k)) is not None for k in fields)/len(fields)
