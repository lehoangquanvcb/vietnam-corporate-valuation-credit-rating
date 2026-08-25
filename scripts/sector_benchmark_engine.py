from pathlib import Path
import pandas as pd, numpy as np
from scripts.universal_data import universe,bank_snapshot,generic_snapshot,read_csv,period_date
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'

def industry_tickers(ticker):
    u=universe();t=str(ticker).upper();z=u[u.Ticker.eq(t)]
    if z.empty:return [t]
    r=z.iloc[0];typ=r.EntityType
    if typ=='BANK':return u[u.EntityType.eq('BANK')].Ticker.tolist()
    if typ=='SECURITIES':return u[u.EntityType.eq('SECURITIES')].Ticker.tolist()
    sec=str(r.Sector);return u[(u.EntityType.eq('CORPORATE')) & (u.Sector.astype(str).eq(sec))].Ticker.tolist()

def industry_label(ticker):
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

def build_sector_benchmarks():
    u=universe();rows=[]
    metrics=['ROE','ROA','PB','PE','DebtEquity','CurrentRatio','NPL','CAR','CASA','NIM','LDR','Revenue','NPAT','TotalAssets']
    for t in u.Ticker:
        s=industry_snapshot(t)
        if s.empty:continue
        for m in metrics:
            if m not in s.columns:continue
            v=pd.to_numeric(s[m],errors='coerce').dropna()
            if len(v):rows.append({'Ticker':t,'Sector':u.loc[u.Ticker.eq(t),'Sector'].iloc[0],'Metric':m,'IndustryMean':v.mean(),'IndustryMedian':v.median(),'IndustryCount':len(v)})
    z=pd.DataFrame(rows);z.to_csv(DATA/'industry_benchmarks.csv',index=False,encoding='utf-8-sig');return z
if __name__=='__main__':
    z=build_sector_benchmarks();print(f'OK - {len(z)} industry benchmark rows')
