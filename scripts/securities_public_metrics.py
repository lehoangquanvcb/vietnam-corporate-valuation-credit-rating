from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'data'/'securities_capital_ratio_master.csv'

def load_capital_ratio_master():
    cols=['Ticker','ReportDate','AsOfDate','AvailableCapitalRatio','SourceURL','SourceDomain','SourceType','AuditStatus','CollectedDate']
    if not MASTER.exists():
        return pd.DataFrame(columns=cols)
    try:
        q=pd.read_csv(MASTER)
    except Exception:
        return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in q.columns:
            q[c]=pd.NA
    rd=pd.to_datetime(q['ReportDate'],errors='coerce')
    ad=pd.to_datetime(q['AsOfDate'],errors='coerce')
    q['AsOfDate']=rd.fillna(ad)
    q['ReportDate']=q['AsOfDate']
    q['Ticker']=q['Ticker'].astype(str).str.upper().str.strip()
    q['AvailableCapitalRatio']=pd.to_numeric(q['AvailableCapitalRatio'],errors='coerce')
    mask=q['AvailableCapitalRatio'].abs()>20
    q.loc[mask,'AvailableCapitalRatio']=q.loc[mask,'AvailableCapitalRatio']/100.0
    q=q.dropna(subset=['Ticker','AsOfDate','AvailableCapitalRatio'])
    q=q[(q['AvailableCapitalRatio']>0)&(q['AvailableCapitalRatio']<=20)]
    return q.sort_values(['Ticker','AsOfDate'])

def latest_capital_ratio_record(ticker):
    q=load_capital_ratio_master()
    if q.empty: return None
    z=q[q['Ticker'].eq(str(ticker).upper().strip())].copy()
    if z.empty: return None
    return z.sort_values('AsOfDate').iloc[-1].to_dict()

def latest_capital_ratio(ticker):
    r=latest_capital_ratio_record(ticker)
    if not r: return None
    try: return float(r.get('AvailableCapitalRatio'))
    except Exception: return None

def capital_ratio_history(ticker):
    q=load_capital_ratio_master()
    if q.empty:
        return pd.DataFrame(columns=['Ticker','AsOfDate','ReportDate','AvailableCapitalRatio'])
    return q[q['Ticker'].eq(str(ticker).upper().strip())].copy().sort_values('AsOfDate').reset_index(drop=True)
