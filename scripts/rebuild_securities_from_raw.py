from pathlib import Path
from datetime import datetime
import re, argparse
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; RAW=DATA/'raw'; CFG=ROOT/'config'; PARTS=DATA/'fundamentals_long'
PARTS.mkdir(parents=True,exist_ok=True)

def _latest_price_from_history(ticker):
    p=DATA/'price_history.csv'
    if not p.exists():
        return np.nan
    try:
        q=pd.read_csv(p)
    except Exception:
        return np.nan
    if q.empty or not {'Ticker','Close'}.issubset(q.columns):
        return np.nan
    q=q[q['Ticker'].astype(str).str.upper().str.strip().eq(str(ticker).upper().strip())].copy()
    if q.empty:
        return np.nan
    q['Close']=pd.to_numeric(q['Close'],errors='coerce')
    q=q.dropna(subset=['Close'])
    if q.empty:
        return np.nan
    if 'Date' in q.columns:
        q['_d']=pd.to_datetime(q['Date'],errors='coerce')
        q=q.sort_values('_d')
    return float(q.iloc[-1]['Close'])

def _existing_snapshot_row(ticker):
    p=DATA/'company_snapshot.csv'
    if not p.exists():
        return {}
    try:
        q=pd.read_csv(p)
    except Exception:
        return {}
    if q.empty or 'Ticker' not in q.columns:
        return {}
    z=q[q['Ticker'].astype(str).str.upper().str.strip().eq(str(ticker).upper().strip())]
    if z.empty:
        return {}
    return z.iloc[-1].to_dict()


def now(): return datetime.now().astimezone().isoformat(timespec='seconds')
def read_csv(p):
    try:return pd.read_csv(p)
    except Exception:return pd.DataFrame()
def period_token(v):
    m=re.fullmatch(r'(20\d{2})-Q([1-4])',str(v).strip().upper().replace('_','-'))
    return (int(m.group(1)),int(m.group(2))) if m else None

def latest_semantic(df, ids):
    if df.empty or not {'id','value'}.issubset(df.columns): return np.nan,None
    z=df[df.id.astype(str).str.upper().isin([x.upper() for x in ids])].copy()
    if z.empty:return np.nan,None
    z['_tok']=z['period'].map(period_token) if 'period' in z else None; z['_v']=pd.to_numeric(z.value,errors='coerce')
    z=z.dropna(subset=['_v']); z=z[z['_tok'].notna()]
    if z.empty:return np.nan,None
    z['_ord']=z['_tok'].map(lambda t:t[0]*4+t[1]); r=z.sort_values('_ord').iloc[-1]
    return float(r['_v']),str(r['period'])

def ttm_semantic(df, ids):
    if df.empty or not {'id','value'}.issubset(df.columns): return np.nan,[]
    z=df[df.id.astype(str).str.upper().isin([x.upper() for x in ids])].copy()
    if z.empty:return np.nan,[]
    z['_tok']=z['period'].map(period_token) if 'period' in z else None; z['_v']=pd.to_numeric(z.value,errors='coerce')
    z=z.dropna(subset=['_v']); z=z[z['_tok'].notna()]; z['_ord']=z['_tok'].map(lambda t:t[0]*4+t[1]); z=z.sort_values('_ord')
    rows=z[['period','_v','_ord']].drop_duplicates('period',keep='last').sort_values('_ord')
    for i in range(len(rows)-4,-1,-1):
        w=rows.iloc[i:i+4]; o=w._ord.astype(int).tolist()
        if len(o)==4 and all(o[j+1]==o[j]+1 for j in range(3)): return float(w._v.sum()),w.period.astype(str).tolist()
    return np.nan,[]

def pct(v):
    if pd.isna(v):return v
    x=float(v); return x/100 if abs(x)>1.5 and abs(x)<=1000 else x

STOCK={
'TotalAssets':('balance',['BS_TOTAL_ASSETS']),'Equity':('balance',['BS_EQUITY','BS_OWNERS_EQUITY','BS_TOTAL_EQUITY']),
'Cash':('balance',['BS_CASH_AND_PRECIOUS_METALS','BS_CASH']),'CurrentAssets':('balance',['BS_SHORT_TERM_ASSETS']),
'CurrentLiabilities':('balance',['BS_SHORT_TERM_LIABILITIES']),'TotalLiabilities':('balance',['BS_TOTAL_LIABILITIES']),
'ROE':('ratio',['RT_PRT_ROE']),'ROA':('ratio',['RT_PRT_ROA']),'PB':('ratio',['RT_VALUE_PB']),'PE':('ratio',['RT_VALUE_PE']),
'DebtEquity':('ratio',['RT_LEV_DE']),'CurrentRatio':('ratio',['RT_LQD_CR']),'NetMargin':('ratio',['RT_PRT_NET_MARGIN']),
'GrossMargin':('ratio',['RT_PRT_GROSS_MARGIN']),'EV_EBITDA':('ratio',['RT_VALUE_EV_EBITDA']),
'MarketCap':('ratio',['RT_VALUE_MARKET_CAP']),'OutstandingShares':('ratio',['RT_VALUE_OUTSTANDING_SHARES']),'AvailableCapitalRatio':('ratio',['RT_BANK_CAR']),
'EquityAssets':('ratio',['RT_LEV_EQUITY_TO_ASSETS']),'LoansEquity':('ratio',['RT_LEV_LOAN_EQUITY'])}
FLOW={'Revenue':('income',['IS_NET_REVENUE','IS_REVENUE']),'NPAT':('income',['IS_NET_PROFIT_AFTER_TAX','IS_PROFIT_AFTER_TAX']),
'CFO':('cashflow',['CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES']),'Depreciation':('cashflow',['CF_DEPRECIATION_AND_AMORTISATION','CF_DEPRECIATION_AMORTIZATION'])}
PERCENT={'ROE','ROA','NetMargin','GrossMargin','AvailableCapitalRatio','EquityAssets'}

def load_raw(t): return {k:read_csv(RAW/f'{t}_{k}.csv') for k in ['ratio','balance','income','cashflow']}
def semantic_long(t,raw):
    out=[]
    for ds,df in raw.items():
        if df.empty or not {'period','id','value'}.issubset(df.columns):continue
        z=df[['period','id','value']].copy(); z['value']=pd.to_numeric(z.value,errors='coerce'); z=z.dropna(subset=['value'])
        z['Ticker']=t; z['Dataset']={'ratio':'ratio','balance':'balance_sheet','income':'income_statement','cashflow':'cash_flow'}[ds]
        z=z.rename(columns={'period':'Period','id':'Field','value':'Value'}); z['DataType']='ACTUAL'; z['SourceMode']='VNSTOCK_BRONZE_RAW_SEMANTIC_RECOVERY'
        out.append(z[['Ticker','Period','Dataset','Field','Value','DataType','SourceMode']])
    return pd.concat(out,ignore_index=True) if out else pd.DataFrame()

def build(t):
    old=_existing_snapshot_row(t)
    raw=load_raw(t)
    if all(x.empty for x in raw.values()):return None,[],None
    row={'Ticker':t,'RetrievedAt':now(),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE_RAW_SEMANTIC_RECOVERY','ParserVersion':'8.96_SECURITIES_LONG_SCHEMA','ParserLog':'RECOVERED_SECURITIES_LONG_SCHEMA'}; hist=[]
    for m,(ds,ids) in STOCK.items():
        v,p=latest_semantic(raw[ds],ids); v=pct(v) if m in PERCENT else v; row[m]=v
        row[f'{m}_SourceRow']='|'.join(ids); row[f'{m}_Basis']='LATEST_Q' if p else 'UNAVAILABLE'; row[f'{m}_Periods']=p or ''

        # Preserve full quarterly history for balance/ratio metrics.
        df=raw[ds]
        if not df.empty and {'period','id','value'}.issubset(df.columns):
            z=df[df.id.astype(str).str.upper().isin([x.upper() for x in ids])].copy()
            z['_v']=pd.to_numeric(z.value,errors='coerce')
            for _,rr in z.dropna(subset=['_v']).iterrows():
                tok=period_token(rr.get('period'))
                if not tok: continue
                per=f"{tok[0]}-Q{tok[1]}"
                vv=float(rr._v)
                if m in PERCENT: vv=pct(vv)
                hist.append({'Ticker':t,'Period':per,'Metric':m,'Value':vv,'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE_RAW_SEMANTIC_RECOVERY'})
    for m,(ds,ids) in FLOW.items():
        v,ps=ttm_semantic(raw[ds],ids); row[m]=v; row[f'{m}_SourceRow']='|'.join(ids); row[f'{m}_Basis']='TTM4Q' if ps else 'TTM4Q_UNAVAILABLE'; row[f'{m}_Periods']='|'.join(ps)
        df=raw[ds]
        if not df.empty and {'period','id','value'}.issubset(df.columns):
            z=df[df.id.astype(str).str.upper().isin([x.upper() for x in ids])].copy(); z['_v']=pd.to_numeric(z.value,errors='coerce')
            for _,rr in z.dropna(subset=['_v']).iterrows():
                tok=period_token(rr.get('period'))
                if tok:
                    per=f"{tok[0]}-Q{tok[1]}"
                    hist.append({'Ticker':t,'Period':per,'Metric':m,'Value':float(rr._v),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE_RAW_SEMANTIC_RECOVERY'})
    st,p1=latest_semantic(raw['balance'],['BS_SHORT_TERM_BORROWINGS']); lt,p2=latest_semantic(raw['balance'],['BS_LONG_TERM_BORROWINGS'])
    row['TotalDebt']=float((0 if pd.isna(st) else st)+(0 if pd.isna(lt) else lt)) if (pd.notna(st) or pd.notna(lt)) else np.nan
    eq,assets,debt,npat=row.get('Equity'),row.get('TotalAssets'),row.get('TotalDebt'),row.get('NPAT')
    if pd.isna(row.get('DebtEquity')) and pd.notna(debt) and pd.notna(eq) and eq!=0:row['DebtEquity']=debt/eq
    if pd.isna(row.get('ROE')) and pd.notna(npat) and pd.notna(eq) and eq!=0:row['ROE']=npat/eq
    if pd.isna(row.get('ROA')) and pd.notna(npat) and pd.notna(assets) and assets!=0:row['ROA']=npat/assets
    # Preserve important non-fundamental fields from the previous snapshot.
    # Raw fundamental rebuild must never erase market data already collected elsewhere.
    for k,v in old.items():
        if k=='Ticker':
            continue
        cur=row.get(k)
        missing=(cur is None) or (isinstance(cur,float) and pd.isna(cur)) or str(cur).strip() in ('','nan','None')
        if missing:
            row[k]=v

    # MARKET PRICE PRIORITY:
    # 1) Latest daily close from price_history.csv.
    # 2) MarketCap / OutstandingShares only as fallback because it is not a current quote.
    px=_latest_price_from_history(t)
    if pd.notna(px):
        _px=float(px)
        # Support both common conventions:
        # 11.30  -> 11,300 VND/share
        # 11,300 -> 11,300 VND/share
        if 0 < _px < 500:
            _px*=1000.0
        while _px>1_000_000:
            _px/=1000.0
        row['Price']=_px
        row['Close']=_px
        row['Price_Basis']='LATEST_DAILY_PRICE_HISTORY'
    else:
        mc=pd.to_numeric(pd.Series([row.get('MarketCap')]),errors='coerce').iloc[0]
        sh=pd.to_numeric(pd.Series([row.get('OutstandingShares')]),errors='coerce').iloc[0]
        if pd.notna(mc) and pd.notna(sh) and sh>0:
            _raw=float(mc/sh)
            # Do NOT blindly multiply by 1,000:
            # some feeds already return VND/share (e.g. 12,150),
            # others return thousand VND/share (e.g. 12.15).
            _px=_raw*1000.0 if 0 < _raw < 500 else _raw
            while _px>1_000_000:
                _px/=1000.0
            row['Price']=_px
            row['Close']=_px
            row['Price_Basis']='MARKETCAP_OUTSTANDING_SHARES_FALLBACK'

    # Transparent per-share derivations needed by relative valuation.
    price=pd.to_numeric(pd.Series([row.get('Price')]),errors='coerce').iloc[0]
    pe=pd.to_numeric(pd.Series([row.get('PE')]),errors='coerce').iloc[0]
    pb=pd.to_numeric(pd.Series([row.get('PB')]),errors='coerce').iloc[0]
    if pd.notna(price) and pd.notna(pe) and pe!=0:
        row['EPS']=float(price/pe)
        row['EPS_Basis']='DERIVED_FROM_PRICE_PE'
    if pd.notna(price) and pd.notna(pb) and pb!=0:
        row['BVPS']=float(price/pb)
        row['BVPS_Basis']='DERIVED_FROM_PRICE_PB'

    row['SnapshotPeriod']=next((row.get(f'{m}_Periods') for m in ['TotalAssets','Equity','ROE'] if row.get(f'{m}_Periods')), '')
    return row,hist,semantic_long(t,raw)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('tickers',nargs='*'); args=ap.parse_args()
    if args.tickers:tickers=[x.upper().strip() for x in args.tickers]
    else:
        u=read_csv(CFG/'company_universe.csv'); u['Ticker']=u.Ticker.astype(str).str.upper().str.strip()
        if 'Active' in u:u=u[pd.to_numeric(u.Active,errors='coerce').fillna(1).eq(1)]
        tickers=u[u.EntityType.astype(str).str.upper().eq('SECURITIES')].Ticker.dropna().unique().tolist()
    snaps=[]; hist=[]; ok=0; miss=0
    for i,t in enumerate(tickers,1):
        row,h,long=build(t)
        if row is None:print(f'[{i}/{len(tickers)}] {t}: NO RAW');miss+=1;continue
        snaps.append(row);hist+=h;ok+=1
        if long is not None and len(long):long.to_csv(PARTS/f'{t}.csv',index=False,encoding='utf-8-sig')
        filled=sum(pd.notna(row.get(k)) for k in ['TotalAssets','Equity','Revenue','NPAT','ROE','ROA','PB','PE','DebtEquity','CurrentRatio'])
        print(f'[{i}/{len(tickers)}] {t}: OK | core={filled}/10')
    if snaps:
        new=pd.DataFrame(snaps); old=read_csv(DATA/'company_snapshot.csv')
        if len(old) and 'Ticker' in old:
            touched=set(new.Ticker.astype(str).str.upper()); old=old[~old.Ticker.astype(str).str.upper().isin(touched)]; new=pd.concat([old,new],ignore_index=True,sort=False)
        new.drop_duplicates('Ticker',keep='last').sort_values('Ticker').to_csv(DATA/'company_snapshot.csv',index=False,encoding='utf-8-sig')
    if hist:
        nh=pd.DataFrame(hist); old=read_csv(DATA/'company_history_long.csv'); ah=pd.concat([old,nh],ignore_index=True,sort=False) if len(old) else nh
        ah.drop_duplicates(['Ticker','Period','Metric'],keep='last').to_csv(DATA/'company_history_long.csv',index=False,encoding='utf-8-sig')
    print(f'DONE | securities={len(tickers)} | rebuilt={ok} | no_raw={miss}')
    if ok==0:print('No raw securities files found. Run Bronze SECURITIES refresh first.')
if __name__=='__main__':main()
