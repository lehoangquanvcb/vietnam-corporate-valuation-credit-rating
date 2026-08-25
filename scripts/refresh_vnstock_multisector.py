from pathlib import Path
import sys, re, json, traceback
from datetime import datetime
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; RAW=DATA/'raw'; CFG=ROOT/'config'
RAW.mkdir(parents=True,exist_ok=True)
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
'TotalAssets':['total assets','bs total assets','assets'],
'Equity':['owners equity','total equity','equity attributable to owners','shareholders equity'],
'TangibleEquity':['tangible equity','net tangible assets'],
'Cash':['cash and cash equivalents','cash'],
'CurrentAssets':['current assets'],
'CurrentLiabilities':['current liabilities'],
'TotalDebt':['total debt','borrowings','interest bearing debt','loans and borrowings','short term borrowings','long term borrowings'],
'Revenue':['revenue','net revenue','sales','operating revenue'],
'GrossProfit':['gross profit'],
'OperatingProfit':['operating profit','ebit','profit from operating activities'],
'NPAT':['net profit after tax','profit after tax','net income','profit attributable to owners'],
'EBITDA':['ebitda'],
'InterestExpense':['interest expense','finance interest expense','borrowing interest expense','interest and similar expense'],
'TaxExpense':['income tax expense','corporate income tax expense'],
'Depreciation':['depreciation and amortisation','depreciation and amortization','depreciation expense'],
'DividendsPaid':['dividends paid','dividend paid'],
'CFO':['cash flow from operating activities','net cash flow from operating activities','net cash generated from operating activities'],
'Capex':['purchase of fixed assets','purchase of property plant equipment','capital expenditure','purchase construction of fixed assets'],
'ROE':['roe','return on equity'],
'ROA':['roa','return on assets'],
'PB':['price to book','p b','pb'],
'PE':['price to earning','p e','pe'],
'EPS':['eps','earning per share'],
'BVPS':['book value per share','bvps'],
'DebtEquity':['debt to equity','debt equity'],
'CurrentRatio':['current ratio'],
'NetMargin':['net profit margin','net margin'],
'GrossMargin':['gross margin'],
'EV_EBITDA':['ev ebitda','enterprise value ebitda'],
'AvailableCapitalRatio':['available capital ratio','capital adequacy ratio'],
'MarginLoans':['margin loans','receivables from margin activities','margin lending'],
'BrokerageRevenue':['brokerage revenue','revenue from brokerage'],
'TradingRevenue':['trading income','gain from financial assets at fvtpl','fvtpl gain'],
'MarginInterestRevenue':['margin lending interest','interest from margin loans','margin interest income'],
'RetainedEarnings':['retained earnings','undistributed profit after tax'],
'CharterCapital':['charter capital','contributed charter capital']
}

def call(opts):
    last=''
    for fn in opts:
        try:
            z=fn()
            if z is not None and len(z): return flat(z), 'OK'
        except Exception as e:last=f'{type(e).__name__}: {e}'
    return pd.DataFrame(), last or 'EMPTY'

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
    hist=[]
    for m,names in MAP.items():
        ratio_metrics={'ROE','ROA','PB','PE','EPS','BVPS','DebtEquity','CurrentRatio','NetMargin','GrossMargin','EV_EBITDA','AvailableCapitalRatio'}
        bs_metrics={'TotalAssets','Equity','TangibleEquity','Cash','CurrentAssets','CurrentLiabilities','TotalDebt','MarginLoans','RetainedEarnings','CharterCapital'}
        cf_metrics={'CFO','Capex','DividendsPaid','Depreciation'}
        source=ratio if m in ratio_metrics else bs if m in bs_metrics else cf if m in cf_metrics else inc
        row[m]=last_numeric(source,names); hist+=hist_rows(source,ticker,m,names)
    # derived metrics only when source data exists
    if pd.isna(row.get('DebtEquity')) and pd.notna(row.get('TotalDebt')) and pd.notna(row.get('Equity')) and row['Equity']!=0: row['DebtEquity']=row['TotalDebt']/row['Equity']
    if pd.isna(row.get('CurrentRatio')) and pd.notna(row.get('CurrentAssets')) and pd.notna(row.get('CurrentLiabilities')) and row['CurrentLiabilities']!=0: row['CurrentRatio']=row['CurrentAssets']/row['CurrentLiabilities']
    if pd.isna(row.get('ROE')) and pd.notna(row.get('NPAT')) and pd.notna(row.get('Equity')) and row['Equity']!=0: row['ROE']=row['NPAT']/row['Equity']
    if pd.isna(row.get('ROA')) and pd.notna(row.get('NPAT')) and pd.notna(row.get('TotalAssets')) and row['TotalAssets']!=0: row['ROA']=row['NPAT']/row['TotalAssets']
    # Derived methodology metrics: calculate only from observed inputs.
    def div(a,b):
        try:
            a=float(a); b=float(b)
            return a/b if np.isfinite(a) and np.isfinite(b) and b!=0 else np.nan
        except:return np.nan
    if pd.isna(row.get('EBITDA')) and pd.notna(row.get('OperatingProfit')) and pd.notna(row.get('Depreciation')):
        row['EBITDA']=row['OperatingProfit']+row['Depreciation']
    row['DebtEBITDA']=div(row.get('TotalDebt'),row.get('EBITDA'))
    row['CFO_Debt']=div(row.get('CFO'),row.get('TotalDebt'))
    if pd.notna(row.get('CFO')) and pd.notna(row.get('Capex')):
        row['FOCF']=row['CFO']-abs(row['Capex'])
        row['FOCF_Debt']=div(row['FOCF'],row.get('TotalDebt'))
    if pd.notna(row.get('FOCF')) and pd.notna(row.get('DividendsPaid')):
        row['DCF']=row['FOCF']-abs(row['DividendsPaid'])
        row['DCF_Debt']=div(row['DCF'],row.get('TotalDebt'))
    if pd.notna(row.get('EBITDA')) and pd.notna(row.get('InterestExpense')):
        row['InterestCoverage']=div(row['EBITDA'],abs(row['InterestExpense']))
    if pd.notna(row.get('EBITDA')) and pd.notna(row.get('InterestExpense')) and pd.notna(row.get('TaxExpense')):
        row['FFO']=row['EBITDA']-abs(row['InterestExpense'])-abs(row['TaxExpense'])
        row['FFO_Debt']=div(row['FFO'],row.get('TotalDebt'))
    row['MarginLoansEquity']=div(row.get('MarginLoans'),row.get('Equity'))
    if pd.isna(row.get('ICGR')):
        row['ICGR']=div(row.get('RetainedEarnings'),row.get('CharterCapital'))
    # Per-metric provenance audit trail
    prov=[]
    for k,v in row.items():
        if k in ('Ticker','RetrievedAt','DataType','SourceMode','ParserLog'):continue
        try: ok=pd.notna(v) and np.isfinite(float(v))
        except: ok=False
        if ok: prov.append({'Ticker':ticker,'Metric':k,'Source':'VNSTOCK_BRONZE_OR_DERIVED','RetrievedAt':row['RetrievedAt']})
    return row,hist,prov

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
    u=pd.read_csv(CFG/'company_universe.csv'); u['Ticker']=u.Ticker.astype(str).str.upper()
    args=[a.upper() for a in sys.argv[1:]]
    if args and args[0] not in ('ALL','BANKS','SECURITIES','CORPORATES'):
        u=u[u.Ticker.isin(args)]
    elif args:
        key=args[0]
        if key=='BANKS':u=u[u.EntityType.eq('BANK')]
        elif key=='SECURITIES':u=u[u.EntityType.eq('SECURITIES')]
        elif key=='CORPORATES':u=u[u.EntityType.eq('CORPORATE')]
    snaps=[]; history=[]; logs=[]; provenance=[]
    for i,r in u.reset_index(drop=True).iterrows():
        t=r.Ticker; typ=r.EntityType; print(f'[{i+1}/{len(u)}] {t} {typ}')
        if typ=='BANK':
            # Bank data remains maintained by the existing dedicated bank refresh pipeline.
            logs.append({'Dataset':f'company:{t}','Status':'SKIP_BANK_DEDICATED','Message':'Use bank refresh engine','RetrievedAt':now()}); continue
        try:
            s,h,pr=fetch(t,typ); s['Price']=price(t); snaps.append(s); history+=h; provenance+=pr
            logs.append({'Dataset':f'company:{t}','Status':'OK','Message':s.get('ParserLog','OK'),'RetrievedAt':now()})
        except Exception as e:
            logs.append({'Dataset':f'company:{t}','Status':'ERROR','Message':f'{type(e).__name__}: {e}','RetrievedAt':now()})
    # append/upsert existing
    old=pd.read_csv(DATA/'company_snapshot.csv') if (DATA/'company_snapshot.csv').exists() else pd.DataFrame()
    new=pd.DataFrame(snaps)
    if len(new):
        if len(old): old=old[~old.Ticker.astype(str).isin(new.Ticker.astype(str))]; new=pd.concat([old,new],ignore_index=True)
        new.to_csv(DATA/'company_snapshot.csv',index=False,encoding='utf-8-sig')
    oldh=pd.read_csv(DATA/'company_history_long.csv') if (DATA/'company_history_long.csv').exists() else pd.DataFrame()
    nh=pd.DataFrame(history)
    if len(nh):
        allh=pd.concat([oldh,nh],ignore_index=True) if len(oldh) else nh
        allh=allh.drop_duplicates(['Ticker','Period','Metric'],keep='last')
        allh.to_csv(DATA/'company_history_long.csv',index=False,encoding='utf-8-sig')
    if provenance:
        pp=DATA/'metric_provenance.csv'
        oldp=pd.read_csv(pp) if pp.exists() else pd.DataFrame()
        zp=pd.concat([oldp,pd.DataFrame(provenance)],ignore_index=True) if len(oldp) else pd.DataFrame(provenance)
        zp=zp.drop_duplicates(['Ticker','Metric'],keep='last')
        zp.to_csv(pp,index=False,encoding='utf-8-sig')
    logp=DATA/'refresh_log_multisector.csv'; oldl=pd.read_csv(logp) if logp.exists() else pd.DataFrame(); pd.concat([oldl,pd.DataFrame(logs)],ignore_index=True).to_csv(logp,index=False,encoding='utf-8-sig')
    print('DONE')
if __name__=='__main__':main()
