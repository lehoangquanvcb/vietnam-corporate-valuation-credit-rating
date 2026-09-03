from __future__ import annotations
from pathlib import Path
from datetime import datetime
import argparse, re, os
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; RAW=DATA/'raw'; CFG=ROOT/'config'; FUND_PARTS=DATA/'fundamentals_long'
FUND_PARTS.mkdir(parents=True,exist_ok=True)

def now(): return datetime.now().astimezone().isoformat(timespec='seconds')
def norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
def find_col(df,names):
    nn=[norm(n) for n in names]
    for c in df.columns:
        nc=norm(c)
        if nc in nn:return c
    for c in df.columns:
        nc=norm(c)
        if any(n in nc or nc in n for n in nn if len(n)>=4):return c
    return None

def period_cols(df):
    y=find_col(df,['year','fiscal year','fiscalyear']); q=find_col(df,['quarter','q','period'])
    return y,q

def period_value(row,y,q):
    yy=None
    try: yy=int(float(row.get(y))) if y else None
    except: pass
    qq=None; qs=str(row.get(q,'')).upper() if q else ''
    m=re.search(r'([1-4])',qs)
    if m: qq=int(m.group(1))
    if yy and qq:return f'{yy}-Q{qq}'
    if yy:return str(yy)
    return None

def last_numeric(df,names):
    if df is None or df.empty:return np.nan
    c=find_col(df,names)
    if c is None:return np.nan
    x=pd.to_numeric(df[c],errors='coerce').dropna()
    return x.iloc[-1] if len(x) else np.nan

def hist_rows(df,ticker,metric,names):
    if df is None or df.empty:return []
    c=find_col(df,names); y,q=period_cols(df)
    if c is None:return []
    out=[]
    for _,r in df.iterrows():
        v=pd.to_numeric(pd.Series([r.get(c)]),errors='coerce').iloc[0]
        per=period_value(r,y,q)
        if pd.notna(v) and per:
            out.append({'Ticker':ticker,'Period':per,'Metric':metric,'Value':float(v),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE_RAW_RECOVERY'})
    return out

def generic_long(df,ticker,dataset):
    if df is None or df.empty:return pd.DataFrame()
    y,q=period_cols(df); id_cols={c for c in [y,q,find_col(df,['ticker','symbol','code'])] if c}
    rows=[]
    for _,r in df.iterrows():
        per=period_value(r,y,q) or 'LATEST'
        for c in df.columns:
            if c in id_cols: continue
            v=pd.to_numeric(pd.Series([r.get(c)]),errors='coerce').iloc[0]
            if pd.notna(v): rows.append({'Ticker':ticker,'Period':per,'Dataset':dataset,'Field':str(c),'Value':float(v),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE_RAW_RECOVERY'})
    if not rows:return pd.DataFrame()
    return pd.DataFrame(rows).drop_duplicates(['Ticker','Period','Dataset','Field'],keep='last')

MAP={
'TotalAssets':['total assets','bs total assets'], 'Equity':['owners equity','total equity','equity'],
'Cash':['cash and cash equivalents','cash'], 'CurrentAssets':['current assets'], 'CurrentLiabilities':['current liabilities'],
'TotalDebt':['total debt','borrowings','debt'], 'Revenue':['revenue','net revenue','sales'], 'GrossProfit':['gross profit'],
'OperatingProfit':['operating profit','ebit'], 'NPAT':['net profit after tax','profit after tax','net income'],
'EBITDA':['ebitda'], 'CFO':['cash flow from operating activities','net cash flow from operating activities'],
'Capex':['purchase of fixed assets','capital expenditure'], 'ROE':['roe','return on equity'], 'ROA':['roa','return on assets'],
'PB':['price to book','p b','pb'], 'PE':['price to earning','p e','pe'], 'EPS':['eps','earning per share'], 'BVPS':['book value per share','bvps'],
'DebtEquity':['debt to equity','debt equity'], 'CurrentRatio':['current ratio'], 'NetMargin':['net profit margin','net margin'],
'GrossMargin':['gross margin'], 'EV_EBITDA':['ev ebitda','enterprise value ebitda'],
}

def read_raw(t,kind):
    p=RAW/f'{t}_{kind}.csv'
    if not p.exists(): return pd.DataFrame()
    try:return pd.read_csv(p)
    except:return pd.DataFrame()

def build_ticker(t):
    ratio=read_raw(t,'ratio'); bs=read_raw(t,'balance'); inc=read_raw(t,'income'); cf=read_raw(t,'cashflow')
    if all(x.empty for x in [ratio,bs,inc,cf]): return None,[],None
    row={'Ticker':t,'RetrievedAt':now(),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE_RAW_RECOVERY','ParserLog':'RECOVERED_FROM_RAW'}
    hist=[]
    for m,names in MAP.items():
        source=ratio if m in ['ROE','ROA','PB','PE','EPS','BVPS','DebtEquity','CurrentRatio','NetMargin','GrossMargin','EV_EBITDA'] else bs if m in ['TotalAssets','Equity','Cash','CurrentAssets','CurrentLiabilities','TotalDebt'] else cf if m in ['CFO','Capex'] else inc
        row[m]=last_numeric(source,names); hist += hist_rows(source,t,m,names)
    if pd.isna(row.get('DebtEquity')) and pd.notna(row.get('TotalDebt')) and pd.notna(row.get('Equity')) and row['Equity']!=0: row['DebtEquity']=row['TotalDebt']/row['Equity']
    if pd.isna(row.get('CurrentRatio')) and pd.notna(row.get('CurrentAssets')) and pd.notna(row.get('CurrentLiabilities')) and row['CurrentLiabilities']!=0: row['CurrentRatio']=row['CurrentAssets']/row['CurrentLiabilities']
    if pd.isna(row.get('ROE')) and pd.notna(row.get('NPAT')) and pd.notna(row.get('Equity')) and row['Equity']!=0: row['ROE']=row['NPAT']/row['Equity']
    if pd.isna(row.get('ROA')) and pd.notna(row.get('NPAT')) and pd.notna(row.get('TotalAssets')) and row['TotalAssets']!=0: row['ROA']=row['NPAT']/row['TotalAssets']
    if pd.notna(row.get('TotalDebt')) and pd.notna(row.get('EBITDA')) and row['EBITDA']!=0: row['DebtEBITDA']=row['TotalDebt']/row['EBITDA']
    if pd.notna(row.get('CFO')) and pd.notna(row.get('TotalDebt')) and row['TotalDebt']!=0: row['CFO_Debt']=row['CFO']/row['TotalDebt']
    parts=[]
    for ds,df in [('ratio',ratio),('balance_sheet',bs),('income_statement',inc),('cash_flow',cf)]:
        z=generic_long(df,t,ds)
        if len(z):parts.append(z)
    long=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    return row,hist,long

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--compact',action='store_true',help='Also rebuild compact latest-field long file')
    args=ap.parse_args()
    u=pd.read_csv(CFG/'company_universe.csv'); u['Ticker']=u.Ticker.astype(str).str.upper().str.strip()
    if 'Active' in u.columns:u=u[pd.to_numeric(u.Active,errors='coerce').fillna(1).eq(1)]
    u=u[~u.EntityType.astype(str).str.upper().eq('BANK')]
    tickers=u.Ticker.dropna().unique().tolist()
    snaps=[]; hist=[]; manifest=[]; compact=[]
    for i,t in enumerate(tickers,1):
        row,h,long=build_ticker(t)
        if row is None:
            print(f'[{i}/{len(tickers)}] {t}: no raw'); continue
        snaps.append(row); hist += h
        if long is not None and len(long):
            fp=FUND_PARTS/f'{t}.csv'; long.to_csv(fp,index=False,encoding='utf-8-sig')
            manifest.append({'Ticker':t,'Rows':len(long),'Path':str(fp.relative_to(ROOT)).replace('\\','/'),'RetrievedAt':now()})
            if args.compact: compact.append(long.drop_duplicates(['Ticker','Dataset','Field'],keep='last'))
        if i%100==0: print(f'[{i}/{len(tickers)}] recovered')
    old=pd.read_csv(DATA/'company_snapshot.csv') if (DATA/'company_snapshot.csv').exists() else pd.DataFrame()
    new=pd.DataFrame(snaps)
    if len(new):
        if len(old) and 'Ticker' in old.columns: old=old[~old.Ticker.astype(str).isin(new.Ticker.astype(str))]
        pd.concat([old,new],ignore_index=True).sort_values('Ticker').drop_duplicates('Ticker',keep='last').to_csv(DATA/'company_snapshot.csv',index=False,encoding='utf-8-sig')
    oldh=pd.read_csv(DATA/'company_history_long.csv') if (DATA/'company_history_long.csv').exists() else pd.DataFrame()
    nh=pd.DataFrame(hist)
    if len(nh):
        ah=pd.concat([oldh,nh],ignore_index=True) if len(oldh) else nh
        ah.drop_duplicates(['Ticker','Period','Metric'],keep='last').to_csv(DATA/'company_history_long.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(manifest).sort_values('Ticker').to_csv(DATA/'vnstock_company_fundamentals_manifest.csv',index=False,encoding='utf-8-sig')
    if args.compact and compact:
        pd.concat(compact,ignore_index=True).to_csv(DATA/'vnstock_company_fundamentals_long.csv',index=False,encoding='utf-8-sig')
    print(f'DONE recovery | snapshots={len(snaps)} | partitions={len(manifest)}')

if __name__=='__main__': main()
