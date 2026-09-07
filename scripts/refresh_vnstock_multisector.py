
from vnstock_env import load_vnstock_env
load_vnstock_env()

from pathlib import Path
import sys, re, json, traceback, os, argparse, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import numpy as np, pandas as pd

PLATFORM_REFRESH_VERSION='8.72.1'

def _version_tuple(v):
    try: return tuple(int(x) for x in re.findall(r'\d+', str(v))[:3])
    except Exception: return (0,0,0)

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; RAW=DATA/'raw'; CFG=ROOT/'config'; FUND_PARTS=DATA/'fundamentals_long'
RAW.mkdir(parents=True,exist_ok=True)
FUND_PARTS.mkdir(parents=True,exist_ok=True)
try:
    import vnstock_data
    from vnstock_data import Fundamental
    VNSTOCK_DATA_VERSION=getattr(vnstock_data,'__version__','0')
    try:
        from vnstock_data import Market
    except Exception:
        Market=None
    try:
        from vnstock_data import Quote
    except Exception:
        Quote=None
except Exception as e:
    print('Không import được vnstock_data:',e); raise SystemExit(2)

def now(): return datetime.now().astimezone().isoformat(timespec='seconds')
def flat(df):
    if df is None:return pd.DataFrame()
    x=df.copy()
    if isinstance(x.columns,pd.MultiIndex): x.columns=['__'.join(str(v) for v in c if str(v)!='nan') for c in x.columns]
    if isinstance(x.index,pd.MultiIndex) or x.index.name is not None or not isinstance(x.index,pd.RangeIndex):
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

def _alias_match(value, names):
    nv=norm(value); nn=[norm(n) for n in names]
    if not nv:return False
    return nv in nn or any((n in nv or nv in n) for n in nn if len(n)>=4)

def _name_score(value, names):
    """Prefer exact semantic/account IDs over fuzzy textual matches."""
    nv=norm(value)
    if not nv:return -1
    nn=[norm(n) for n in names]
    if nv in nn:return 1000
    # compact form lets IS_NET_REVENUE exactly match aliases despite punctuation
    cv=re.sub(r'[^a-z0-9]','',nv)
    for n in nn:
        if cv == re.sub(r'[^a-z0-9]','',n):return 950
    best=-1
    for n in nn:
        if len(n)<4:continue
        if n in nv or nv in n:
            # Reward token coverage but keep this well below exact semantic IDs.
            score=500 + min(len(n),len(nv))
            if score>best:best=score
    return best


def _period_token(c):
    """Return (year, quarter, kind) for a period label."""
    s=str(c).strip().upper().replace('_','-')
    m=re.fullmatch(r'(20\d{2})-Q([1-4])',s)
    if m:return (int(m.group(1)),int(m.group(2)),'Q')
    m=re.fullmatch(r'(20\d{2})',s)
    if m:return (int(m.group(1)),0,'FY')
    return None

def _period_columns(df, kind=None):
    out=[]
    for c in df.columns:
        tok=_period_token(c)
        if tok and (kind is None or tok[2]==kind): out.append((c,tok))
    return sorted(out,key=lambda x:(x[1][0],x[1][1]))

def _metric_row(df,names):
    """Return best semantic/account row, not the first fuzzy match."""
    x=flat(df)
    if x.empty:return None
    label_hints=('id','item','semantic','metric','indicator','name','code','field','account')
    label_cols=[c for c in x.columns if any(h==norm(c) or h in norm(c) for h in label_hints)]
    label_cols += [c for c in x.columns if c not in label_cols and (x[c].dtype=='object' or str(x[c].dtype).startswith('string')) and _period_token(c) is None]
    best_score=-1; best_row=None
    for _,r in x.iterrows():
        row_score=-1
        for c in label_cols:
            try: row_score=max(row_score,_name_score(r.get(c,''),names))
            except Exception:pass
        if row_score>best_score:
            best_score=row_score; best_row=r
    return best_row if best_score>=500 else None

def _row_period_value(row,col):
    try:return float(pd.to_numeric(pd.Series([row.get(col)]),errors='coerce').iloc[0])
    except Exception:return np.nan

def _quarter_is_consecutive(a,b):
    ya,qa,_=a; yb,qb,_=b
    return (yb*4+qb)==(ya*4+qa+1)

def _latest_four_consecutive(qvals):
    """Return latest 4 consecutive quarterly values or [] if unavailable."""
    if len(qvals)<4:return []
    qvals=sorted(qvals,key=lambda x:(x[0][0],x[0][1]))
    for i in range(len(qvals)-4,-1,-1):
        w=qvals[i:i+4]
        if all(_quarter_is_consecutive(w[j][0],w[j+1][0]) for j in range(3)):
            return w
    return []

def _snapshot_from_rowwide(df,names,metric_kind='stock',return_meta=False):
    """Period-aware extractor for vnstock_data 3.2.2 wide financial tables."""
    x=flat(df); r=_metric_row(x,names)
    if r is None:return (np.nan,{}) if return_meta else np.nan
    # identify the semantic row for audit
    row_id=''
    for c in ['id','item','semantic_id','metric','code','name']:
        cc=next((z for z in x.columns if norm(z)==norm(c)),None)
        if cc is not None and str(r.get(cc,'')).lower()!='nan':
            row_id=str(r.get(cc)); break
    qcols=_period_columns(x,'Q'); fycols=_period_columns(x,'FY')
    if metric_kind=='flow':
        qvals=[]
        for c,tok in qcols:
            v=_row_period_value(r,c)
            if pd.notna(v):qvals.append((tok,v,c))
        w=_latest_four_consecutive([(tok,v) for tok,v,c in qvals])
        if w:
            val=float(sum(v for _,v in w))
            meta={'row':row_id,'basis':'TTM4Q','periods':[f'{t[0]}-Q{t[1]}' for t,v in w]}
            return (val,meta) if return_meta else val
        # STRICT 8.68: a flow KPI is valid only when four consecutive quarters exist.
        # Never silently substitute FY or a single quarter into a TTM field.
        return (np.nan,{'row':row_id,'basis':'TTM4Q_UNAVAILABLE','periods':[]}) if return_meta else np.nan
    for c,tok in reversed(qcols):
        v=_row_period_value(r,c)
        if pd.notna(v):
            meta={'row':row_id,'basis':'LATEST_Q','periods':[f'{tok[0]}-Q{tok[1]}']}
            return (v,meta) if return_meta else v
    for c,tok in reversed(fycols):
        v=_row_period_value(r,c)
        if pd.notna(v):
            meta={'row':row_id,'basis':'LATEST_FY','periods':[str(tok[0])]}
            return (v,meta) if return_meta else v
    return (np.nan,{}) if return_meta else np.nan

def _long_period_col(x):
    # Prefer a column whose VALUES look like 2026-Q2 / 2025.
    for c in x.columns:
        vals=x[c].astype(str).str.strip()
        if vals.str.match(r'^20\d{2}(?:-Q[1-4])?$').mean()>=0.25:return c
    return find_col(x,['period','fiscal period','date','year quarter'])

def _long_value_col(x,label_cols,period_col):
    # Explicit value/amount field first. Never use metadata level/order as the value.
    bad={'level','order','unit','id','item','semantic','metric','indicator','name','code','field','account'}
    explicit=[c for c in x.columns if norm(c) in ('value','amount','val','numeric value','data value')]
    for c in explicit:
        if pd.to_numeric(x[c],errors='coerce').notna().any():return c
    candidates=[]
    for c in x.columns:
        if c in label_cols or c==period_col or norm(c) in bad:continue
        vals=pd.to_numeric(x[c],errors='coerce')
        if vals.notna().any():candidates.append((int(vals.notna().sum()),c))
    return sorted(candidates,reverse=True)[0][1] if candidates else None

def _snapshot_from_long(df,names,metric_kind='stock',return_meta=False):
    x=flat(df)
    if x.empty:return (np.nan,{}) if return_meta else np.nan
    label_hints=('semantic','item','metric','indicator','name','code','field','account','id')
    label_cols=[c for c in x.columns if any(h==norm(c) or h in norm(c) for h in label_hints)]
    label_cols += [c for c in x.columns if c not in label_cols and (x[c].dtype=='object' or str(x[c].dtype).startswith('string'))]
    scores=[]
    for idx,r in x.iterrows():
        sc=max([_name_score(r.get(c,''),names) for c in label_cols] or [-1])
        if sc>=500:scores.append((idx,sc))
    if not scores:return (np.nan,{}) if return_meta else np.nan
    best=max(sc for _,sc in scores)
    z=x.loc[[idx for idx,sc in scores if sc==best]].copy()
    pc=_long_period_col(z); vc=_long_value_col(z,label_cols,pc)
    if vc is None:return (np.nan,{}) if return_meta else np.nan
    z['_V']=pd.to_numeric(z[vc],errors='coerce')
    if pc is not None:z['_TOK']=z[pc].map(_period_token)
    else:z['_TOK']=None
    z=z.dropna(subset=['_V'])
    if z.empty:return (np.nan,{}) if return_meta else np.nan
    # semantic id for audit
    rid=''
    for c in label_cols:
        sv=str(z.iloc[0].get(c,''))
        if _name_score(sv,names)>=best:rid=sv;break
    if pc is not None:
        q=[]; fy=[]
        for _,r in z.iterrows():
            tok=r['_TOK']; v=float(r['_V'])
            if tok is None:continue
            (q if tok[2]=='Q' else fy).append((tok,v))
        q=sorted(q,key=lambda t:(t[0][0],t[0][1])); fy=sorted(fy,key=lambda t:t[0][0])
        if metric_kind=='flow':
            w=_latest_four_consecutive(q)
            if w:
                val=float(sum(v for _,v in w)); meta={'row':rid,'basis':'TTM4Q','periods':[f'{t[0]}-Q{t[1]}' for t,v in w]}
                return (val,meta) if return_meta else val
            return (np.nan,{'row':rid,'basis':'TTM4Q_UNAVAILABLE','periods':[]}) if return_meta else np.nan
        else:
            if q:
                tok,v=q[-1]; meta={'row':rid,'basis':'LATEST_Q','periods':[f'{tok[0]}-Q{tok[1]}']}
                return (v,meta) if return_meta else v
            if fy:
                tok,v=fy[-1]; meta={'row':rid,'basis':'LATEST_FY','periods':[str(tok[0])]}
                return (v,meta) if return_meta else v
    # STRICT 8.68: no unperioded numeric fallback.
    return (np.nan,{'row':rid,'basis':'NO_VALID_PERIOD','periods':[]}) if return_meta else np.nan

def metric_snapshot(df,names,metric_kind='stock',return_meta=False):
    """Deterministic extractor: row-wide -> tidy/long -> column-wide fallback."""
    if df is None or df.empty:return (np.nan,{}) if return_meta else np.nan
    x=flat(df)
    if _period_columns(x):
        v,meta=_snapshot_from_rowwide(x,names,metric_kind,True)
        if pd.notna(v):return (v,meta) if return_meta else v
    v,meta=_snapshot_from_long(x,names,metric_kind,True)
    if pd.notna(v):return (v,meta) if return_meta else v
    # legacy column-wide schema (periods as rows; KPI as columns)
    c=find_col(x,names)
    if c is not None:
        y,q=period_cols(x); z=x.copy()
        if y:
            z['_Y']=pd.to_numeric(z[y],errors='coerce')
            z['_Q']=z[q].astype(str).str.extract(r'([1-4])',expand=False).pipe(pd.to_numeric,errors='coerce').fillna(0) if q else 0
            z=z.sort_values(['_Y','_Q'])
        vals=pd.to_numeric(z[c],errors='coerce')
        if metric_kind=='flow':
            if y and q:
                z['_V']=vals; qs=z.dropna(subset=['_V']); qs=qs[qs['_Q'].between(1,4)]
                if len(qs)>=4:
                    # Require the four selected observations to be consecutive.
                    toks=[]
                    for _,rr in qs.iloc[-4:].iterrows(): toks.append((int(rr['_Y']),int(rr['_Q']),'Q'))
                    if all(_quarter_is_consecutive(toks[j],toks[j+1]) for j in range(3)):
                        val=float(qs['_V'].iloc[-4:].sum()); meta={'row':str(c),'basis':'TTM4Q_COLUMN','periods':[f'{a}-Q{b}' for a,b,_ in toks]}
                        return (val,meta) if return_meta else val
            return (np.nan,{'row':str(c),'basis':'TTM4Q_UNAVAILABLE','periods':[]}) if return_meta else np.nan
        vals=vals.dropna()
        if len(vals):
            val=float(vals.iloc[-1]); meta={'row':str(c),'basis':'LATEST_COLUMN','periods':[]}
            return (val,meta) if return_meta else val
    return (np.nan,{}) if return_meta else np.nan

def _latest_numeric_from_long(df,names):
    return metric_snapshot(df,names,'stock')

def last_numeric(df,names):
    # Backward-compatible default: balance/ratio-like latest observation.
    return metric_snapshot(df,names,'stock')

PERCENT_METRICS={'ROE','ROA','NetMargin','GrossMargin','CFO_Debt','FOCF_Debt','CashDebt'}

def normalize_metric_value(metric, value):
    try:v=float(value)
    except Exception:return value
    if metric in PERCENT_METRICS and abs(v)>1.5 and abs(v)<=1000:
        return v/100.0
    return v

def _extract_all_mapped(df):
    out={}
    for m,names in MAP.items():
        try:
            v=metric_snapshot(df,names,'stock')
            if pd.notna(v): out[m]=normalize_metric_value(m,v)
        except Exception: pass
    return out

def call_financial_health(eq, etype):
    fn=getattr(eq,'financial_health',None)
    if fn is None:return pd.DataFrame(),'financial_health:METHOD_NOT_FOUND'
    ct='securities' if str(etype).upper()=='SECURITIES' else 'regular'
    attempts=[
        ('scorecard_type',dict(scorecard=ct,lang='en',limit=12)),
        ('scorecard_auto',dict(scorecard='auto',lang='en',limit=12)),
        ('com_type',dict(com_type=ct,lang='en',limit=12)),
        ('lang_limit',dict(lang='en',limit=12)),
        ('default',dict()),
    ]
    last=''
    for tag,kw in attempts:
        try:
            d=fn(**kw)
            if d is None: continue
            if not isinstance(d,pd.DataFrame): d=pd.DataFrame(d)
            d=flat(d)
            if len(d):return d,f'financial_health:{tag}:OK shape={d.shape}'
        except Exception as e:last=f'{tag}:{type(e).__name__}:{e}'
    return pd.DataFrame(), 'financial_health:FAILED '+last

def hist_rows_any(df,ticker,metric,names):
    if df is None or df.empty:return []
    x=flat(df)
    # Vnstock 3.2.2 row-wide semantic/account schema: one metric per row,
    # periods across columns. Preserve every actual period separately.
    if _period_columns(x):
        r=_metric_row(x,names)
        if r is not None:
            out=[]
            for c,tok in _period_columns(x):
                v=_row_period_value(r,c)
                if pd.notna(v):
                    yy,qq,kind=tok; per=f'{yy}-Q{qq}' if kind=='Q' else str(yy)
                    out.append({'Ticker':ticker,'Period':per,'Metric':metric,'Value':float(normalize_metric_value(metric,v)),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE'})
            if out:return out
    # conventional column-wide time series
    rows=hist_rows(x,ticker,metric,names)
    if rows:return rows
    # tidy/long fallback
    label_hints=('semantic','item','metric','indicator','name','code','field','account','id','index')
    label_cols=[c for c in x.columns if any(h in norm(c) for h in label_hints)]
    label_cols += [c for c in x.columns if c not in label_cols and (x[c].dtype=='object' or str(x[c].dtype).startswith('string'))]
    mask=pd.Series(False,index=x.index)
    for c in label_cols:
        try:mask |= x[c].astype(str).map(lambda z:_alias_match(z,names))
        except Exception:pass
    z=x[mask].copy()
    if z.empty:return []
    value_cols=[c for c in z.columns if 'value' in norm(c) or 'amount' in norm(c)]
    period_candidates=[c for c in z.columns if any(h in norm(c) for h in ('period','date','year','quarter'))]
    out=[]
    for _,r in z.iterrows():
        per=None
        for pc in period_candidates:
            sv=str(r.get(pc,''))
            if sv and sv.lower()!='nan': per=sv; break
        for vc in value_cols:
            v=pd.to_numeric(pd.Series([r.get(vc)]),errors='coerce').iloc[0]
            if pd.notna(v):
                out.append({'Ticker':ticker,'Period':per or 'LATEST','Metric':metric,'Value':float(normalize_metric_value(metric,v)),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE'})
                break
    return out

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

FLOW_METRICS={'Revenue','GrossProfit','OperatingProfit','InterestExpense','NPAT','EBITDA','Depreciation','CFO','Capex'}
RATIO_METRICS={'ROE','ROA','PB','PE','EPS','BVPS','DebtEquity','CurrentRatio','NetMargin','GrossMargin','EV_EBITDA','InterestCoverage'}
STOCK_METRICS={'TotalAssets','Equity','Cash','CurrentAssets','CurrentLiabilities','TotalDebt','TotalLiabilities'}

def _metric_kind(metric):
    if metric in FLOW_METRICS:return 'flow'
    if metric in RATIO_METRICS:return 'ratio'
    return 'stock'

MAP={
'TotalAssets':['total assets','bs total assets','assets total'],
'Equity':['owners equity','owner equity','total equity','equity','bs owners equity','bs total equity'],
'Cash':['cash and cash equivalents','cash','bs cash and precious metals','bs cash and cash equivalents'],
'CurrentAssets':['current assets','bs current assets'],
'CurrentLiabilities':['current liabilities','bs current liabilities'],
'TotalDebt':['total debt','total borrowings','borrowings','interest bearing debt','debt'],
'TotalLiabilities':['total liabilities','bs total liabilities'],
'Revenue':['revenue','net revenue','sales','is net revenue','is revenue','IS_NET_REVENUE'],
'GrossProfit':['gross profit','is gross profit','IS_GROSS_PROFIT'],
'OperatingProfit':['operating profit','operating income','ebit','is operating profit','IS_OPERATING_PROFIT'],
'InterestExpense':['interest expense','finance costs','borrowing costs','is interest expense','cf interest expense','IS_INTEREST_EXPENSE'],
'NPAT':['net profit after tax','profit after tax','net income','is net profit after tax','is profit after tax','IS_NET_PROFIT_AFTER_TAX','IS_PROFIT_AFTER_TAX','IS_NET_INCOME'],
'EBITDA':['ebitda'],
'Depreciation':['depreciation and amortisation','depreciation and amortization','cf depreciation and amortisation','cf depreciation and amortization'],
'CFO':['cash flow from operating activities','net cash flow from operating activities','net cash from operating activities','cf net cash flow from operating activities'],
'Capex':['purchase of fixed assets','capital expenditure','purchase of property plant equipment','cf purchase of fixed assets'],
'ROE':['roe','return on equity'], 'ROA':['roa','return on assets'],
'PB':['price to book','price book','p b','pb','RT_VALUE_PB'], 'PE':['price to earning','price earning','p e','pe','RT_VALUE_PE'],
'EPS':['eps','earning per share'], 'BVPS':['book value per share','bvps'],
'DebtEquity':['debt to equity','debt equity'], 'CurrentRatio':['current ratio'],
'NetMargin':['net profit margin','net margin'], 'GrossMargin':['gross margin','gross profit margin'],
'EV_EBITDA':['ev ebitda','enterprise value ebitda'],
'InterestCoverage':['interest coverage','ebit interest expense','interest coverage ratio'],
}

# V8.69: exact semantic-ID map for vnstock_data 3.2.2/legacy tables.
# Do not infer core financial metrics from fuzzy labels when a stable semantic ID exists.
SEMANTIC_IDS={
    'TotalAssets':['BS_TOTAL_ASSETS'],
    'Equity':['BS_OWNERS_EQUITY'],
    'Cash':['BS_CASH_AND_PRECIOUS_METALS'],
    'CurrentAssets':['BS_SHORT_TERM_ASSETS'],
    'CurrentLiabilities':['BS_SHORT_TERM_LIABILITIES'],
    'TotalLiabilities':['BS_TOTAL_LIABILITIES'],
    'Revenue':['IS_NET_REVENUE'],
    'GrossProfit':['IS_GROSS_PROFIT'],
    'OperatingProfit':['IS_OPERATING_PROFIT'],
    'InterestExpense':['IS_INTEREST_EXPENSES'],
    'NPAT':['IS_NET_PROFIT_AFTER_TAX'],
    'Depreciation':['CF_DEPRECIATION_AND_AMORTISATION','CF_DEPRECIATION_AMORTIZATION'],
    'CFO':['CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES'],
    'Capex':['CF_PAYMENTS_FOR_FIXED_ASSETS'],
    'ROE':['RT_PRT_ROE'],
    'ROA':['RT_PRT_ROA'],
    'PB':['RT_VALUE_PB'],
    'PE':['RT_VALUE_PE'],
    'DebtEquity':['RT_LEV_DE'],
    'CurrentRatio':['RT_LQD_CR'],
    'NetMargin':['RT_PRT_NET_MARGIN'],
    'GrossMargin':['RT_PRT_GROSS_MARGIN'],
    'EV_EBITDA':['RT_VALUE_EV_EBITDA'],
}

# V8.70: components used for deterministic leverage/cash-flow derivations.
BORROWING_SEMANTIC_IDS={
    'ShortTermBorrowings':['BS_SHORT_TERM_BORROWINGS'],
    'LongTermBorrowings':['BS_LONG_TERM_BORROWINGS'],
}

def _semantic_col(x):
    """Find the semantic/account identifier column, preferring `id`."""
    for wanted in ('id','semantic_id','item','code'):
        for c in x.columns:
            if norm(c)==wanted:return c
    return None

def _exact_semantic_snapshot(df, semantic_ids, metric_kind='stock', return_meta=False):
    """Extract one metric by exact Vnstock semantic ID and explicit periods.

    Supports both vnstock_data 3.2.2 long tables (period/id/value rows) and
    financial_health row-wide tables (id + 2025-Q4/2026-Q1/... columns).
    No fuzzy fallback is used here.
    """
    if df is None or df.empty:return (np.nan,{}) if return_meta else np.nan
    x=flat(df)
    ids={str(v).strip().upper() for v in semantic_ids}
    idc=_semantic_col(x)
    if idc is None:return (np.nan,{}) if return_meta else np.nan
    z=x[x[idc].astype(str).str.strip().str.upper().isin(ids)].copy()
    if z.empty:return (np.nan,{}) if return_meta else np.nan
    # Respect semantic ID preference order if more than one alias is present.
    chosen=None
    for sid in semantic_ids:
        q=z[z[idc].astype(str).str.strip().str.upper().eq(str(sid).upper())]
        if len(q): chosen=(str(sid).upper(),q.copy()); break
    if chosen is None:return (np.nan,{}) if return_meta else np.nan
    sid,z=chosen

    # Row-wide: one semantic row and period labels across columns.
    pcols=_period_columns(z)
    if pcols:
        r=z.iloc[0]
        qvals=[]; fyvals=[]
        for c,tok in pcols:
            v=_row_period_value(r,c)
            if pd.isna(v):continue
            if tok[2]=='Q':qvals.append((tok,float(v)))
            else:fyvals.append((tok,float(v)))
        qvals=sorted(qvals,key=lambda a:(a[0][0],a[0][1])); fyvals=sorted(fyvals,key=lambda a:a[0][0])
        if metric_kind=='flow':
            w=_latest_four_consecutive(qvals)
            if w:
                val=float(sum(v for _,v in w)); meta={'row':sid,'basis':'TTM4Q','periods':[f'{t[0]}-Q{t[1]}' for t,v in w]}
                return (val,meta) if return_meta else val
            return (np.nan,{'row':sid,'basis':'TTM4Q_UNAVAILABLE','periods':[]}) if return_meta else np.nan
        if qvals:
            tok,val=qvals[-1]; meta={'row':sid,'basis':'LATEST_Q','periods':[f'{tok[0]}-Q{tok[1]}']}
            return (val,meta) if return_meta else val
        if fyvals:
            tok,val=fyvals[-1]; meta={'row':sid,'basis':'LATEST_FY','periods':[str(tok[0])]}
            return (val,meta) if return_meta else val
        return (np.nan,{'row':sid,'basis':'NO_VALID_PERIOD','periods':[]}) if return_meta else np.nan

    # Long/tidy: explicit period and value columns.
    pc=next((c for c in z.columns if norm(c)=='period'),None) or _long_period_col(z)
    vc=next((c for c in z.columns if norm(c) in ('value','amount')),None)
    if vc is None:vc=_long_value_col(z,[idc],pc)
    if pc is None or vc is None:return (np.nan,{'row':sid,'basis':'NO_PERIOD_OR_VALUE','periods':[]}) if return_meta else np.nan
    vals=[]
    for _,r in z.iterrows():
        tok=_period_token(r.get(pc)); v=pd.to_numeric(pd.Series([r.get(vc)]),errors='coerce').iloc[0]
        if tok is not None and pd.notna(v): vals.append((tok,float(v)))
    qvals=sorted([a for a in vals if a[0][2]=='Q'],key=lambda a:(a[0][0],a[0][1]))
    fyvals=sorted([a for a in vals if a[0][2]=='FY'],key=lambda a:a[0][0])
    if metric_kind=='flow':
        w=_latest_four_consecutive(qvals)
        if w:
            val=float(sum(v for _,v in w)); meta={'row':sid,'basis':'TTM4Q','periods':[f'{t[0]}-Q{t[1]}' for t,v in w]}
            return (val,meta) if return_meta else val
        return (np.nan,{'row':sid,'basis':'TTM4Q_UNAVAILABLE','periods':[]}) if return_meta else np.nan
    if qvals:
        tok,val=qvals[-1]; meta={'row':sid,'basis':'LATEST_Q','periods':[f'{tok[0]}-Q{tok[1]}']}
        return (val,meta) if return_meta else val
    if fyvals:
        tok,val=fyvals[-1]; meta={'row':sid,'basis':'LATEST_FY','periods':[str(tok[0])]}
        return (val,meta) if return_meta else val
    return (np.nan,{'row':sid,'basis':'NO_VALID_PERIOD','periods':[]}) if return_meta else np.nan

def _exact_semantic_history(df,ticker,metric,semantic_ids):
    """History rows for an exact semantic ID; used by charts and peer trends."""
    if df is None or df.empty:return []
    x=flat(df); idc=_semantic_col(x)
    if idc is None:return []
    ids={str(v).upper() for v in semantic_ids}
    z=x[x[idc].astype(str).str.strip().str.upper().isin(ids)].copy()
    if z.empty:return []
    # choose preferred ID only
    for sid in semantic_ids:
        zz=z[z[idc].astype(str).str.strip().str.upper().eq(str(sid).upper())]
        if len(zz): z=zz;break
    out=[]
    if _period_columns(z):
        r=z.iloc[0]
        for c,tok in _period_columns(z):
            v=_row_period_value(r,c)
            if pd.notna(v):
                per=f'{tok[0]}-Q{tok[1]}' if tok[2]=='Q' else str(tok[0])
                out.append({'Ticker':ticker,'Period':per,'Metric':metric,'Value':float(normalize_metric_value(metric,v)),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE'})
        return out
    pc=next((c for c in z.columns if norm(c)=='period'),None) or _long_period_col(z)
    vc=next((c for c in z.columns if norm(c) in ('value','amount')),None)
    if pc is None or vc is None:return []
    for _,r in z.iterrows():
        tok=_period_token(r.get(pc)); v=pd.to_numeric(pd.Series([r.get(vc)]),errors='coerce').iloc[0]
        if tok is not None and pd.notna(v):
            per=f'{tok[0]}-Q{tok[1]}' if tok[2]=='Q' else str(tok[0])
            out.append({'Ticker':ticker,'Period':per,'Metric':metric,'Value':float(normalize_metric_value(metric,v)),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE'})
    return out

def _metric_exact_then_fallback(source, health, metric, names):
    """Exact semantic first; health is a second exact source; fuzzy only for unmapped metrics."""
    kind=_metric_kind(metric)
    if metric in SEMANTIC_IDS:
        v,meta=_exact_semantic_snapshot(source,SEMANTIC_IDS[metric],kind,True)
        if pd.isna(v) and health is not None and len(health):
            v,meta=_exact_semantic_snapshot(health,SEMANTIC_IDS[metric],kind,True)
        return v,meta
    return metric_snapshot(source,names,kind,True)

def call(opts):
    last=''
    for fn in opts:
        try:
            z=fn()
            if z is not None and len(z): return flat(z), 'OK'
        except Exception as e:last=f'{type(e).__name__}: {e}'
    return pd.DataFrame(), last or 'EMPTY'

def _com_type(etype):
    e=str(etype).upper()
    return 'securities' if e=='SECURITIES' else 'regular'

def call_report(eq, method, period, etype):
    """Version-aware report loader.
    vnstock_data <=3.2.7 uses the pre-VAS schema and does not support
    format/drop_empty/com_type. From 3.2.8 the VAS semantic-ID schema is used.
    """
    fn=getattr(eq,method)
    ct=_com_type(etype)
    v=_version_tuple(VNSTOCK_DATA_VERSION)
    if v >= (3,2,8):
        opts=[
            lambda: fn(period=period, lang='en', format='time_series', drop_empty=True, com_type=ct.capitalize()),
            lambda: fn(period=period, lang='en', format='wide', drop_empty=True, com_type=ct.capitalize()),
            lambda: fn(period=period, lang='en', format='long', drop_empty=True, com_type=ct.capitalize()),
            lambda: fn(period=period, lang='en'),
        ]
    else:
        # Bronze on the user's machine is 3.2.2: use legacy-compatible calls.
        opts=[
            lambda: fn(period=period, lang='en'),
            lambda: fn(period=period),
            lambda: fn(lang='en'),
            lambda: fn(),
        ]
    return call(opts)

def sum_last(df, groups):
    vals=[]
    for names in groups:
        v=metric_snapshot(df,names,'stock')
        if pd.notna(v): vals.append(float(v))
    return sum(vals) if vals else np.nan

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
    health,hs=call_financial_health(eq,etype)
    ratio,rs=call_report(eq,'ratio','quarter',etype)
    if ratio.empty: ratio,rs=call_report(eq,'ratio','year',etype)
    bs,bs_s=call_report(eq,'balance_sheet','quarter',etype)
    if bs.empty: bs,bs_s=call_report(eq,'balance_sheet','year',etype)
    inc,is_s=call_report(eq,'income_statement','quarter',etype)
    if inc.empty: inc,is_s=call_report(eq,'income_statement','year',etype)
    cf,cf_s=call_report(eq,'cash_flow','quarter',etype)
    if cf.empty: cf,cf_s=call_report(eq,'cash_flow','year',etype)
    for name,df in [('ratio',ratio),('balance',bs),('income',inc),('cashflow',cf)]:
        if len(df): df.to_csv(RAW/f'{ticker}_{name}.csv',index=False,encoding='utf-8-sig')
    row={'Ticker':ticker,'RetrievedAt':now(),'DataType':'ACTUAL','SourceMode':'VNSTOCK_BRONZE','ParserVersion':PLATFORM_REFRESH_VERSION,'VnstockDataVersion':VNSTOCK_DATA_VERSION,'ParserLog':' | '.join([hs,rs,bs_s,is_s,cf_s])}
    hist=[]; allfields=[]
    for ds,df in [('ratio',ratio),('balance_sheet',bs),('income_statement',inc),('cash_flow',cf)]:
        try: allfields += generic_long(df,ticker,ds)
        except Exception as e: row_export_error=f'{ds}:{type(e).__name__}:{e}'
    health_map=_extract_all_mapped(health) if len(health) else {}
    parse_errors=[]
    for m,names in MAP.items():
        source=ratio if m in ['ROE','ROA','PB','PE','EPS','BVPS','DebtEquity','CurrentRatio','NetMargin','GrossMargin','EV_EBITDA','InterestCoverage'] else bs if m in ['TotalAssets','Equity','Cash','CurrentAssets','CurrentLiabilities','TotalDebt','TotalLiabilities'] else cf if m in ['CFO','Capex','Depreciation'] else inc
        try:
            v,selmeta=_metric_exact_then_fallback(source,health,m,names)
        except Exception as e:
            v,selmeta=np.nan,{'row':'','basis':'PARSER_ERROR','periods':[]}
            parse_errors.append(f'{m}:{type(e).__name__}:{e}')
        # Only non-semantic auxiliary metrics may use the broad financial_health map.
        # Core KPIs must retain exact semantic ID + period provenance.
        if pd.isna(v) and m not in SEMANTIC_IDS and m in health_map:
            v=health_map[m]; selmeta={'row':'financial_health','basis':'HEALTH_FALLBACK','periods':[]}
        row[m]=normalize_metric_value(m,v) if pd.notna(v) else np.nan
        if selmeta:
            row[f'{m}_SourceRow']=selmeta.get('row','')
            row[f'{m}_Basis']=selmeta.get('basis','')
            row[f'{m}_Periods']='|'.join(selmeta.get('periods',[]) or [])
        if m in SEMANTIC_IDS:
            mh=_exact_semantic_history(source,ticker,m,SEMANTIC_IDS[m])
            if not mh and len(health): mh=_exact_semantic_history(health,ticker,m,SEMANTIC_IDS[m])
            hist+=mh
        else:
            hist+=hist_rows_any(source,ticker,m,names)
            if not any(x.get('Metric')==m for x in hist) and len(health): hist+=hist_rows_any(health,ticker,m,names)
    if parse_errors: row['ParserLog']=row.get('ParserLog','')+' | METRIC_ERRORS='+';'.join(parse_errors)
    row['SnapshotPeriod']='LATEST_QUARTER'
    row['FlowBasis']='TTM_LAST_4_CONSECUTIVE_QUARTERS_STRICT'
    # V8.70 deterministic derived metrics. Never accept dimensionally-invalid
    # financial_health fallbacks for EBITDA / debt service ratios.
    # Interest-bearing debt = latest-quarter short-term + long-term borrowings.
    _dparts=[]; _dmeta=[]
    for _label,_sids in BORROWING_SEMANTIC_IDS.items():
        _v,_m=_exact_semantic_snapshot(bs,_sids,'stock',True)
        if pd.isna(_v) and len(health):
            _v,_m=_exact_semantic_snapshot(health,_sids,'stock',True)
        if pd.notna(_v):
            _dparts.append(float(_v)); _dmeta.append(_m)
    if len(_dparts)==2:
        row['TotalDebt']=float(sum(_dparts))
        row['TotalDebt_SourceRow']='BS_SHORT_TERM_BORROWINGS+BS_LONG_TERM_BORROWINGS'
        row['TotalDebt_Basis']='DERIVED_LATEST_Q'
        row['TotalDebt_Periods']='|'.join(sorted(set(p for mm in _dmeta for p in mm.get('periods',[]))))
    else:
        # Do not use fuzzy "debt" or health scorecard fields as interest-bearing debt.
        row['TotalDebt']=np.nan
        row['TotalDebt_SourceRow']=''
        row['TotalDebt_Basis']='BORROWINGS_UNAVAILABLE'
        row['TotalDebt_Periods']=''

    # EBITDA = Operating Profit (EBIT proxy) TTM + D&A TTM. Both must carry TTM4Q provenance.
    op=float(row['OperatingProfit']) if pd.notna(row.get('OperatingProfit')) else np.nan
    da=float(row['Depreciation']) if pd.notna(row.get('Depreciation')) else np.nan
    op_basis=str(row.get('OperatingProfit_Basis',''))
    da_basis=str(row.get('Depreciation_Basis',''))
    op_periods=str(row.get('OperatingProfit_Periods',''))
    da_periods=str(row.get('Depreciation_Periods',''))
    if pd.notna(op) and pd.notna(da) and op_basis=='TTM4Q' and da_basis=='TTM4Q' and op_periods and op_periods==da_periods:
        ebitda=op + abs(da)
        if ebitda>0:
            row['EBITDA']=float(ebitda)
            row['EBITDA_SourceRow']='IS_OPERATING_PROFIT+CF_DEPRECIATION_AND_AMORTISATION'
            row['EBITDA_Basis']='DERIVED_TTM4Q'
            row['EBITDA_Periods']=op_periods
        else:
            row['EBITDA']=np.nan
            row['EBITDA_SourceRow']=''
            row['EBITDA_Basis']='INVALID_DERIVED_EBITDA'
            row['EBITDA_Periods']=''
    else:
        # Explicitly overwrite any financial_health fallback value.
        row['EBITDA']=np.nan
        row['EBITDA_SourceRow']=''
        row['EBITDA_Basis']='TTM_COMPONENTS_UNAVAILABLE'
        row['EBITDA_Periods']=''

    # Interest coverage = EBIT TTM / absolute interest expense TTM, only on matching TTM windows.
    ie=float(row['InterestExpense']) if pd.notna(row.get('InterestExpense')) else np.nan
    ie_basis=str(row.get('InterestExpense_Basis',''))
    ie_periods=str(row.get('InterestExpense_Periods',''))
    if pd.notna(op) and pd.notna(ie) and ie!=0 and op_basis=='TTM4Q' and ie_basis=='TTM4Q' and op_periods==ie_periods:
        row['InterestCoverage']=op/abs(ie)
        row['InterestCoverage_SourceRow']='IS_OPERATING_PROFIT/IS_INTEREST_EXPENSES'
        row['InterestCoverage_Basis']='DERIVED_TTM4Q'
        row['InterestCoverage_Periods']=op_periods

    # Valuation multiples: zero is not a valid parsed P/E or P/B observation.
    for _m in ['PE','PB']:
        if pd.notna(row.get(_m)) and float(row[_m])==0:
            row[_m]=np.nan

    # Core derived ratios with strict unit/basis checks.
    debt=float(row['TotalDebt']) if pd.notna(row.get('TotalDebt')) else np.nan
    equity=float(row['Equity']) if pd.notna(row.get('Equity')) else np.nan
    assets=float(row['TotalAssets']) if pd.notna(row.get('TotalAssets')) else np.nan
    npat=float(row['NPAT']) if pd.notna(row.get('NPAT')) else np.nan
    cfo=float(row['CFO']) if pd.notna(row.get('CFO')) else np.nan
    capex=float(row['Capex']) if pd.notna(row.get('Capex')) else np.nan
    cash=float(row['Cash']) if pd.notna(row.get('Cash')) else np.nan

    # Prefer statement-consistent debt/equity over provider ratio when exact borrowings are available.
    if pd.notna(debt) and pd.notna(equity) and equity!=0:
        row['DebtEquity']=debt/equity
        row['DebtEquity_SourceRow']='TotalDebt/BS_OWNERS_EQUITY'
        row['DebtEquity_Basis']='DERIVED_LATEST_Q'
        row['DebtEquity_Periods']=row.get('TotalDebt_Periods','')
    if pd.isna(row.get('CurrentRatio')) and pd.notna(row.get('CurrentAssets')) and pd.notna(row.get('CurrentLiabilities')) and row['CurrentLiabilities']!=0:
        row['CurrentRatio']=row['CurrentAssets']/row['CurrentLiabilities']
    if pd.isna(row.get('ROE')) and pd.notna(npat) and pd.notna(equity) and equity!=0:
        row['ROE']=npat/equity
    if pd.isna(row.get('ROA')) and pd.notna(npat) and pd.notna(assets) and assets!=0:
        row['ROA']=npat/assets

    if pd.notna(debt) and pd.notna(row.get('EBITDA')) and float(row['EBITDA'])>0:
        row['DebtEBITDA']=debt/float(row['EBITDA'])
        row['DebtEBITDA_SourceRow']='TotalDebt/EBITDA'
        row['DebtEBITDA_Basis']='LATEST_Q_DEBT_OVER_TTM4Q_EBITDA'
        row['DebtEBITDA_Periods']=f"{row.get('TotalDebt_Periods','')} / {row.get('EBITDA_Periods','')}"
    else:
        row['DebtEBITDA']=np.nan

    # CFO/Debt only if CFO is strict TTM4Q and debt is latest quarter.
    if pd.notna(cfo) and pd.notna(debt) and debt!=0 and str(row.get('CFO_Basis',''))=='TTM4Q':
        row['CFO_Debt']=cfo/debt
        row['CFO_Debt_SourceRow']='CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES/TotalDebt'
        row['CFO_Debt_Basis']='TTM4Q_CFO_OVER_LATEST_Q_DEBT'
        row['CFO_Debt_Periods']=row.get('CFO_Periods','')
    else:
        row['CFO_Debt']=np.nan

    # Free operating cash flow proxy = CFO + capex cash outflow (capex row is negative in VAS cash flow).
    if pd.notna(cfo) and pd.notna(capex) and str(row.get('CFO_Basis',''))=='TTM4Q' and str(row.get('Capex_Basis',''))=='TTM4Q' and str(row.get('CFO_Periods',''))==str(row.get('Capex_Periods','')):
        focf=cfo + capex
        row['FOCF']=focf
        row['FOCF_SourceRow']='CFO+CF_PAYMENTS_FOR_FIXED_ASSETS'
        row['FOCF_Basis']='DERIVED_TTM4Q'
        row['FOCF_Periods']=row.get('CFO_Periods','')
        row['FOCF_Debt']=focf/debt if pd.notna(debt) and debt!=0 else np.nan
    else:
        row['FOCF']=np.nan; row['FOCF_Debt']=np.nan
    row['CashDebt']=cash/debt if pd.notna(cash) and pd.notna(debt) and debt!=0 else np.nan

    # Sanity gates: prevent impossible leverage from entering peer/rating engines.
    if pd.notna(row.get('DebtEBITDA')) and not (0 <= float(row['DebtEBITDA']) <= 100):
        row['ParserLog']=row.get('ParserLog','')+f" | SANITY_FAIL DebtEBITDA={row['DebtEBITDA']}"
        row['DebtEBITDA']=np.nan
    for _m in ['CFO_Debt','FOCF_Debt','CashDebt']:
        if pd.notna(row.get(_m)) and abs(float(row[_m]))>10:
            row['ParserLog']=row.get('ParserLog','')+f" | SANITY_FAIL {_m}={row[_m]}"
            row[_m]=np.nan
    return row,hist,allfields

def price(ticker):
    try:
        if Market is not None:
            d=Market().equity(ticker).ohlcv(start='2025-01-01',end=datetime.now().strftime('%Y-%m-%d'))
            d=flat(d); c=find_col(d,['close']);
            if c and len(d):
                v=pd.to_numeric(d[c],errors='coerce').dropna()
                if len(v): return float(v.iloc[-1])
    except Exception:
        pass
    try:
        if Quote is not None:
            q=Quote(source='VCI',symbol=ticker)
            d=q.history(start='2025-01-01',end=datetime.now().strftime('%Y-%m-%d'),interval='1D')
            d=flat(d); c=find_col(d,['close'])
            if c and len(d):
                v=pd.to_numeric(d[c],errors='coerce').dropna()
                if len(v): return float(v.iloc[-1])
    except Exception:
        pass
    return np.nan

def main():
    ap=argparse.ArgumentParser(description='Vnstock Bronze multisector full-market refresh')
    ap.add_argument('scope',nargs='*',help='ALL / SECURITIES / CORPORATES / ticker list')
    ap.add_argument('--workers',type=int,default=int(os.getenv('VNSTOCK_WORKERS','1')))
    ap.add_argument('--ticker-delay',type=float,default=float(os.getenv('VNSTOCK_TICKER_DELAY','2.5')),help='Seconds between ticker API batches; Bronze-safe default 2.5s')
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
    workers=max(1,min(int(args.workers),2))
    ticker_delay=max(0.0,float(args.ticker_delay))
    print(f'REFRESH ENGINE v{PLATFORM_REFRESH_VERSION} | vnstock_data={VNSTOCK_DATA_VERSION}')
    print(f'MULTISECTOR ACTIVE UNIVERSE: {len(u)} | WORKERS: {workers} | TICKER_DELAY: {ticker_delay:.1f}s')
    snaps=[]; history=[]; logs=[]; manifest=[]

    def job(r):
        t=r.Ticker; typ=r.EntityType
        if ticker_delay: time.sleep(ticker_delay)
        try:
            s,h,a=fetch(t,typ); s['Price']=price(t)
            return t,s,h,a,{'Dataset':f'company:{t}','Status':'OK','Message':s.get('ParserLog','OK'),'RetrievedAt':now()}
        except Exception as e:
            msg=f'{type(e).__name__}: {e}'
            print(f'ERROR DETAIL {t}: {msg}')
            traceback.print_exc()
            return t,None,[],[],{'Dataset':f'company:{t}','Status':'ERROR','Message':msg,'RetrievedAt':now()}

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
