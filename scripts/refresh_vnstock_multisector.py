
from vnstock_env import load_vnstock_env
load_vnstock_env()

from pathlib import Path
import sys, re, json, traceback, os, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; RAW=DATA/'raw'; CFG=ROOT/'config'; FUND_PARTS=DATA/'fundamentals_long'
RAW.mkdir(parents=True,exist_ok=True)
FUND_PARTS.mkdir(parents=True,exist_ok=True)
try:
    from vnstock_data import Fundamental, Quote
except Exception as e:
    print('Không import được vnstock_data:',e); raise SystemExit(2)

def now(): return datetime.now().astimezone().isoformat(timespec='seconds')
def flat(df):
    if df is None:return pd.DataFrame()
    x=df.copy()
    if isinstance(x.columns,pd.MultiIndex): x.columns=['__'.join(str(v) for v in c if str(v)!='nan') for c in x.columns]
    if isinstance(x.index,pd.MultiIndex) or x.index.name is not None:
        try:x=x.reset_index()
        except:pass
    return x

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

def last_numeric(df,names):
    if df is None or df.empty:return np.nan
    c=find_col(df,names)
    if c is None:return np.nan
    x=pd.to_numeric(df[c],errors='coerce').dropna()
    return x.iloc[-1] if len(x) else np.nan

def period_cols(df):
    y=find_col(df,['year','fiscal year','fiscalyear']); q=find_col(df,['quarter','q','period'])
    return y,q

def period_value(row,y,q):
    yy=None
    try: yy=int(float(row.get(y))) if y else None
    except: pass
    qq=None; qs=str(row.get(q,'')).upper() if q else ''
    m=re.search(r'([1-4])',qs)
    if m:qq=int(m.group(1))
    if yy and qq:return f'{yy}-Q{qq}'
    if yy:return str(yy)
    return None

def hist_rows(df,ticker,metric,names):
    if df is None or df.empty:return []
    c=find_col(df,names); y,q=period_cols(df)
    if c is None:return []
    out=[]
    for _,r in df.iterrows():
        v=pd.to_numeric(pd.Series([r.get(c)]),errors='coerce').iloc[0]
        per=period_value(r,y,q)
        if pd.notna(v) and per: out.append({'Ticker':ticker,'Period':per,'Metric':metric,'Value':float(v),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE'})
    return out

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

def call(opts):
    last=''
    for fn in opts:
        try:
            z=fn()
            if z is not None and len(z): return flat(z), 'OK'
        except Exception as e:last=f'{type(e).__name__}: {e}'
    return pd.DataFrame(), last or 'EMPTY'

def generic_long(df,ticker,dataset):
    """Export every numeric field returned by Vnstock, not only mapped KPIs."""
    if df is None or df.empty:return []
    x=flat(df); y,q=period_cols(x)
    id_cols={c for c in [y,q,find_col(x,['ticker','symbol','code'])] if c}
    out=[]
    for _,r in x.iterrows():
        per=period_value(r,y,q) or 'LATEST'
        for c in x.columns:
            if c in id_cols: continue
            v=pd.to_numeric(pd.Series([r.get(c)]),errors='coerce').iloc[0]
            if pd.notna(v):
                out.append({'Ticker':ticker,'Period':per,'Dataset':dataset,'Field':str(c),'Value':float(v),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE'})
    return out

def fetch(ticker,etype):
    eq=Fundamental().equity(ticker)
    scorecard='banking' if etype=='BANK' else None
    ratio,rs=call([lambda:eq.ratio(period='quarter',lang='en'),lambda:eq.ratio(period='year',lang='en')])
    bs,bs_s=call([lambda:eq.balance_sheet(period='quarter',lang='en'),lambda:eq.balance_sheet(period='year',lang='en')])
    inc,is_s=call([lambda:eq.income_statement(period='quarter',lang='en'),lambda:eq.income_statement(period='year',lang='en')])
    cf,cf_s=call([lambda:eq.cash_flow(period='quarter',lang='en'),lambda:eq.cash_flow(period='year',lang='en')])
    for name,df in [('ratio',ratio),('balance',bs),('income',inc),('cashflow',cf)]:
        if len(df): df.to_csv(RAW/f'{ticker}_{name}.csv',index=False,encoding='utf-8-sig')
    row={'Ticker':ticker,'RetrievedAt':now(),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE','ParserLog':' | '.join([rs,bs_s,is_s,cf_s])}
    hist=[]; allfields=[]
    for ds,df in [('ratio',ratio),('balance_sheet',bs),('income_statement',inc),('cash_flow',cf)]: allfields += generic_long(df,ticker,ds)
    for m,names in MAP.items():
        source=ratio if m in ['ROE','ROA','PB','PE','EPS','BVPS','DebtEquity','CurrentRatio','NetMargin','GrossMargin','EV_EBITDA'] else bs if m in ['TotalAssets','Equity','Cash','CurrentAssets','CurrentLiabilities','TotalDebt'] else cf if m in ['CFO','Capex'] else inc
        row[m]=last_numeric(source,names); hist+=hist_rows(source,ticker,m,names)
    # derived metrics only when source data exists
    if pd.isna(row.get('DebtEquity')) and pd.notna(row.get('TotalDebt')) and pd.notna(row.get('Equity')) and row['Equity']!=0: row['DebtEquity']=row['TotalDebt']/row['Equity']
    if pd.isna(row.get('CurrentRatio')) and pd.notna(row.get('CurrentAssets')) and pd.notna(row.get('CurrentLiabilities')) and row['CurrentLiabilities']!=0: row['CurrentRatio']=row['CurrentAssets']/row['CurrentLiabilities']
    if pd.isna(row.get('ROE')) and pd.notna(row.get('NPAT')) and pd.notna(row.get('Equity')) and row['Equity']!=0: row['ROE']=row['NPAT']/row['Equity']
    if pd.isna(row.get('ROA')) and pd.notna(row.get('NPAT')) and pd.notna(row.get('TotalAssets')) and row['TotalAssets']!=0: row['ROA']=row['NPAT']/row['TotalAssets']
    if pd.notna(row.get('TotalDebt')) and pd.notna(row.get('EBITDA')) and row['EBITDA']!=0: row['DebtEBITDA']=row['TotalDebt']/row['EBITDA']
    if pd.notna(row.get('CFO')) and pd.notna(row.get('TotalDebt')) and row['TotalDebt']!=0: row['CFO_Debt']=row['CFO']/row['TotalDebt']
    return row,hist,allfields

def price(ticker):
    try:
        q=Quote(source='VCI',symbol=ticker)
        d=q.history(start='2025-01-01',end=datetime.now().strftime('%Y-%m-%d'),interval='1D')
        d=flat(d); c=find_col(d,['close']); dt=find_col(d,['time','date','trading date'])
        if c and len(d):
            v=pd.to_numeric(d[c],errors='coerce').dropna()
            return float(v.iloc[-1]) if len(v) else np.nan
    except Exception:return np.nan
    return np.nan

def main():
    ap=argparse.ArgumentParser(description='Vnstock Bronze multisector full-market refresh')
    ap.add_argument('scope',nargs='*',help='ALL / SECURITIES / CORPORATES / ticker list')
    ap.add_argument('--workers',type=int,default=int(os.getenv('VNSTOCK_WORKERS','4')))
    args=ap.parse_args()
    u=pd.read_csv(CFG/'company_universe.csv'); u['Ticker']=u.Ticker.astype(str).str.upper().str.strip()
    if 'Active' in u.columns: u=u[pd.to_numeric(u.Active,errors='coerce').fillna(1).eq(1)]
    scope=[a.upper() for a in args.scope]
    if scope and scope[0] not in ('ALL','BANKS','SECURITIES','CORPORATES'):
        u=u[u.Ticker.isin(scope)]
    elif scope:
        key=scope[0]
        if key=='BANKS':u=u[u.EntityType.eq('BANK')]
        elif key=='SECURITIES':u=u[u.EntityType.eq('SECURITIES')]
        elif key=='CORPORATES':u=u[u.EntityType.eq('CORPORATE')]
    # Banks remain in the dedicated bank parser.
    u=u[~u.EntityType.astype(str).str.upper().eq('BANK')].reset_index(drop=True)
    workers=max(1,min(int(args.workers),6))
    print(f'MULTISECTOR ACTIVE UNIVERSE: {len(u)} | WORKERS: {workers}')
    snaps=[]; history=[]; logs=[]; manifest=[]

    def job(r):
        t=r.Ticker; typ=r.EntityType
        try:
            s,h,a=fetch(t,typ); s['Price']=price(t)
            return t,s,h,a,{'Dataset':f'company:{t}','Status':'OK','Message':s.get('ParserLog','OK'),'RetrievedAt':now()}
        except Exception as e:
            return t,None,[],[],{'Dataset':f'company:{t}','Status':'ERROR','Message':f'{type(e).__name__}: {e}','RetrievedAt':now()}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures={ex.submit(job,r):r.Ticker for _,r in u.iterrows()}
        done=0
        for fut in as_completed(futures):
            done+=1; t,snap,h,a,log=fut.result(); print(f'[{done}/{len(u)}] {t}: {log["Status"]}')
            if snap is not None:
                snaps.append(snap); history += h
                # Memory-safe full-fundamental storage: persist each ticker immediately
                # instead of retaining tens of millions of Python dicts in RAM.
                if a:
                    part = FUND_PARTS / f'{t}.csv'
                    pd.DataFrame(a).drop_duplicates(['Ticker','Period','Dataset','Field'], keep='last').to_csv(part,index=False,encoding='utf-8-sig')
                    manifest.append({'Ticker':t,'Rows':len(a),'Path':str(part.relative_to(ROOT)).replace('\\','/'),'RetrievedAt':now()})
            logs.append(log)
            # Periodic checkpoints protect a long full-market run from losing all
            # normalized outputs if a later ticker fails.
            if done % 50 == 0:
                pd.DataFrame(snaps).to_csv(DATA/'_checkpoint_company_snapshot.csv',index=False,encoding='utf-8-sig')
                pd.DataFrame(history).to_csv(DATA/'_checkpoint_company_history_long.csv',index=False,encoding='utf-8-sig')
                pd.DataFrame(logs).to_csv(DATA/'_checkpoint_refresh_log_multisector.csv',index=False,encoding='utf-8-sig')

    old=pd.read_csv(DATA/'company_snapshot.csv') if (DATA/'company_snapshot.csv').exists() else pd.DataFrame()
    new=pd.DataFrame(snaps)
    if len(new):
        if len(old) and 'Ticker' in old.columns: old=old[~old.Ticker.astype(str).isin(new.Ticker.astype(str))]
        new=pd.concat([old,new],ignore_index=True) if len(old) else new
        new.sort_values('Ticker').drop_duplicates('Ticker',keep='last').to_csv(DATA/'company_snapshot.csv',index=False,encoding='utf-8-sig')

    oldh=pd.read_csv(DATA/'company_history_long.csv') if (DATA/'company_history_long.csv').exists() else pd.DataFrame()
    nh=pd.DataFrame(history)
    if len(nh):
        allh=pd.concat([oldh,nh],ignore_index=True) if len(oldh) else nh
        allh=allh.drop_duplicates(['Ticker','Period','Metric'],keep='last')
        allh.to_csv(DATA/'company_history_long.csv',index=False,encoding='utf-8-sig')

    # Complete numeric fundamental surface from Vnstock is stored as one
    # partition per ticker under data/fundamentals_long/. This preserves ALL
    # numeric fields without building a multi-gigabyte object DataFrame.
    # A small manifest is committed for discovery/audit.
    manp=DATA/'vnstock_company_fundamentals_manifest.csv'
    oldm=pd.read_csv(manp) if manp.exists() else pd.DataFrame()
    nm=pd.DataFrame(manifest)
    if len(nm):
        if len(oldm) and 'Ticker' in oldm.columns:
            touched=set(nm.Ticker.astype(str).str.upper())
            oldm=oldm[~oldm.Ticker.astype(str).str.upper().isin(touched)]
            nm=pd.concat([oldm,nm],ignore_index=True)
        nm.sort_values('Ticker').drop_duplicates('Ticker',keep='last').to_csv(manp,index=False,encoding='utf-8-sig')

    # No monolithic all-field long DataFrame is built here. Complete history
    # is available in the per-ticker partitions; the manifest is the index.

    logp=DATA/'refresh_log_multisector.csv'; oldl=pd.read_csv(logp) if logp.exists() else pd.DataFrame()
    pd.concat([oldl,pd.DataFrame(logs)],ignore_index=True).to_csv(logp,index=False,encoding='utf-8-sig')
    ok=sum(1 for x in logs if x['Status']=='OK'); err=len(logs)-ok
    print(f'DONE | OK={ok} | ERROR={err} | total={len(logs)}')
if __name__=='__main__':main()
