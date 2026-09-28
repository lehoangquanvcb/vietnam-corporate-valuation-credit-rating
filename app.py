from pathlib import Path
import io, json, re
import numpy as np, pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scripts.universal_data import universe,get_company,get_snapshot,entity_history,peer_snapshot,peer_metric_history,industry_snapshot,industry_metric_history,industry_label,period_date,num,coverage
from scripts.multisector_valuation import valuation, latest_market_price
from scripts.securities_public_metrics import latest_capital_ratio
from scripts.multisector_report import generate_docx,generate_pdf
from scripts.sector_templates import get_template
from scripts.sector_kpi_engine import sector_kpi_table
from scripts.intelligent_analyst import analyze as intelligent_analyze
from scripts.valuation_regime import assess as valuation_regime
from scripts.three_methodology_rating import rate_company as rate_three_methodologies
from scripts.fair_value_range import fair_value_range
from scripts.rating_committee_engine import committee_pack
from scripts.valuation_triangulation import triangulate
from scripts.rating_evidence_engine import rating_evidence
try:
    from scripts.coverage_engine import build_coverage_matrix
except Exception:
    build_coverage_matrix=None
try: from scripts.credit_rating_engine import build_credit_rating
except Exception: build_credit_rating=None

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'
BUILD_TAG='V8.116-BASELINE-024914-DATA-CHART-REPAIR'

from scripts.company_profile import load_company_profile, profile_overview_text, profile_source_text

def _override_peer_info(ticker):
    """Read analyst peer override directly at UI boundary so Cloud/local resolve identically."""
    path=ROOT/'config'/'dynamic_peer_overrides.csv'
    try:
        o=pd.read_csv(path)
        if o.empty or not {'TargetTicker','PeerTicker'}.issubset(o.columns): return None, []
        o=o.copy(); o['TargetTicker']=o['TargetTicker'].astype(str).str.upper().str.strip(); o['PeerTicker']=o['PeerTicker'].astype(str).str.upper().str.strip()
        if 'Active' in o.columns: o=o[pd.to_numeric(o['Active'],errors='coerce').fillna(1).eq(1)]
        z=o[o['TargetTicker'].eq(str(ticker).upper().strip())].copy()
        if z.empty:return None, []
        if 'Priority' in z.columns:
            z['_p']=pd.to_numeric(z['Priority'],errors='coerce').fillna(9999); z=z.sort_values(['_p','PeerTicker'])
        peers=[x for x in z.PeerTicker.astype(str).tolist() if x and x!=str(ticker).upper().strip()]
        return 'Nhóm peer chuyên ngành (analyst override)', peers
    except Exception:
        return None, []

def _final_chart_guard(metric, df):
    """Last-mile validity guard: malformed upstream values must never reach Plotly."""
    if df is None or not len(df): return df
    q=df.copy(); m=str(metric)
    for c in ['IndustryMean','IndustryMedian']:
        if c not in q.columns: continue
        v=pd.to_numeric(q[c],errors='coerce')
        if m=='DebtEquity': v=v.where((v>=0)&(v<=10))
        elif m=='CurrentRatio': v=v.where((v>0)&(v<=20))
        elif m=='PE': v=v.where((v>0)&(v<=200))
        elif m=='PB': v=v.where((v>0)&(v<=20))
        elif m in {'ROE','ROA'}: v=v.where((v>=-2)&(v<=2))
        q[c]=v
    keep=[c for c in ['IndustryMean','IndustryMedian'] if c in q.columns]
    return q.dropna(subset=keep,how='all') if keep else q


def _security_raw_latest_value(ticker, metric):
    """Latest actual Securities value from the same raw semantic files used by refresh.
    This is a UI fallback only; it never fabricates observations.
    """
    h=_security_raw_metric_history(ticker,metric)
    if h is not None and len(h):
        v=pd.to_numeric(h['Value'],errors='coerce').dropna()
        if len(v): return float(v.iloc[-1])
    return None

def _snapshot_row(ticker):
    """Flatten one snapshot into a peer-table row without inventing data."""
    try:
        d=get_snapshot(ticker) or {}
    except Exception:
        d={}
    row={'Ticker':str(ticker).upper().strip()}
    if isinstance(d,dict):
        row.update(d)
    # Derive only transparent ratios when source fields are available.
    def _n(k):
        try:
            v=pd.to_numeric(pd.Series([row.get(k)]),errors='coerce').iloc[0]
            return None if pd.isna(v) else float(v)
        except Exception:
            return None
    eq=_n('Equity'); assets=_n('TotalAssets'); npat=_n('NPAT')
    debt=_n('Debt')
    if row.get('ROE') is None and npat is not None and eq not in (None,0):
        row['ROE']=npat/eq
    if row.get('ROA') is None and npat is not None and assets not in (None,0):
        row['ROA']=npat/assets
    if row.get('DebtEquity') is None and debt is not None and eq not in (None,0):
        row['DebtEquity']=debt/eq
    if row.get('CurrentRatio') is None:
        ca=_n('CurrentAssets'); cl=_n('CurrentLiabilities')
        if ca is not None and cl not in (None,0): row['CurrentRatio']=ca/cl
    # V8.116: enrich sparse Securities snapshots from raw semantic files.
    # This fixes blank platform charts without touching the working report/valuation pipeline.
    try:
        if str(get_company(ticker).get('EntityType','')).upper()=='SECURITIES':
            for _m in ['Revenue','NPAT','TotalAssets','Equity','ROE','ROA','DebtEquity','CurrentRatio','PB','PE']:
                if num(row.get(_m)) is None:
                    _v=_security_raw_latest_value(ticker,_m)
                    if _v is not None: row[_m]=_v
            if num(row.get('AvailableCapitalRatio')) is None:
                try:
                    _acr=latest_capital_ratio(str(ticker).upper().strip())
                    if isinstance(_acr,dict):
                        _acr=_acr.get('AvailableCapitalRatio',_acr.get('Ratio',_acr.get('Value')))
                    if num(_acr) is not None: row['AvailableCapitalRatio']=float(num(_acr))
                except Exception:
                    pass
    except Exception:
        pass
    return row

def _securities_peer_frame(ticker, max_peers=10):
    """Build a dynamic Securities peer set when industry_snapshot is empty.
    Priority: analyst override -> closest listed securities firms by size.
    """
    t=str(ticker).upper().strip()
    try:
        q=industry_snapshot(t)
        if q is not None and len(q):
            q=q.copy()
            if 'Ticker' in q.columns:
                q['Ticker']=q['Ticker'].astype(str).str.upper().str.strip()
                if q.Ticker.nunique()>=2:
                    # Preserve upstream peer selection, but rebuild each row through the
                    # enriched snapshot/raw fallback so sparse industry_snapshot columns
                    # cannot blank all charts and KPI tables.
                    _ticks=[t]+[x for x in q['Ticker'].tolist() if x!=t][:max_peers]
                    return pd.DataFrame([_snapshot_row(x) for x in _ticks]).drop_duplicates('Ticker',keep='first')
    except Exception:
        pass

    # Analyst override, if configured.
    try:
        _, override_peers=_override_peer_info(t)
    except Exception:
        override_peers=[]
    peer_tickers=[x for x in override_peers if str(x).upper().strip()!=t]

    # Otherwise build dynamically from all listed/registered securities companies.
    if not peer_tickers:
        try:
            uu=universe().copy()
            uu=uu[uu.EntityType.astype(str).str.upper().eq('SECURITIES')]
            cand=[str(x).upper().strip() for x in uu.Ticker.tolist() if str(x).upper().strip()!=t]
        except Exception:
            cand=[]
        target=_snapshot_row(t)
        target_size=None
        for k in ('TotalAssets','Equity','Revenue','MarketCap'):
            try:
                v=float(target.get(k))
                if np.isfinite(v) and v>0:
                    target_size=(k,v); break
            except Exception:
                pass
        scored=[]
        for x in cand:
            r=_snapshot_row(x)
            score=999.0
            if target_size:
                k,tv=target_size
                try:
                    pv=float(r.get(k))
                    if np.isfinite(pv) and pv>0:
                        score=abs(np.log(pv/tv))
                except Exception:
                    pass
            scored.append((score,x,r))
        scored.sort(key=lambda z:(z[0],z[1]))
        peer_tickers=[x for _,x,_ in scored[:max_peers]]

    rows=[_snapshot_row(t)]+[_snapshot_row(x) for x in peer_tickers[:max_peers]]
    return pd.DataFrame(rows).drop_duplicates('Ticker',keep='first')

def _peer_frame_safe(ticker):
    try:
        et=str(get_company(ticker).get('EntityType','')).upper()
    except Exception:
        et=''
    if et=='SECURITIES':
        return _securities_peer_frame(ticker,10)
    try:
        return industry_snapshot(ticker)
    except Exception:
        return pd.DataFrame()

def _securities_kpi_fallback(ticker, peer_df):
    """Create the same benchmark table from actual target/peer snapshots when
    sector_kpi_table has no usable securities observations.
    """
    if peer_df is None or not len(peer_df) or 'Ticker' not in peer_df.columns:
        return pd.DataFrame()
    t=str(ticker).upper().strip()
    q=peer_df.copy()
    q['Ticker']=q['Ticker'].astype(str).str.upper().str.strip()
    target=q[q.Ticker.eq(t)]
    peers=q[~q.Ticker.eq(t)]
    specs=[
        ('Vốn & đòn bẩy','AvailableCapitalRatio','Tỷ lệ an toàn vốn khả dụng'),
        ('Vốn & đòn bẩy','DebtEquity','Nợ/VCSH'),
        ('Khả năng sinh lợi & hiệu quả','ROE','ROE/ROAE'),
        ('Khả năng sinh lợi & hiệu quả','ROA','ROA/ROAA'),
        ('Nguồn vốn & thanh khoản','CurrentRatio','Hệ số thanh toán hiện hành'),
        ('Định giá','PB','P/B'),
        ('Định giá','PE','P/E'),
    ]
    rows=[]
    for grp,m,label in specs:
        if m not in q.columns: vals=pd.Series(dtype=float)
        else: vals=pd.to_numeric(peers[m],errors='coerce').dropna()
        tv=None
        if len(target) and m in target.columns:
            vv=pd.to_numeric(target[m],errors='coerce').dropna()
            if len(vv): tv=float(vv.iloc[-1])
        mean=float(vals.mean()) if len(vals) else None
        med=float(vals.median()) if len(vals) else None
        rows.append({
            'Metric':m,'Nhóm phân tích':grp,'Chỉ tiêu':label,
            'Doanh nghiệp':tv,'Trung bình ngành':mean,'Trung vị ngành':med,
            'Số DN có dữ liệu':int(len(vals)),
            'Chênh lệch với TB ngành':(tv-mean) if tv is not None and mean is not None else None,
            'Trạng thái dữ liệu':('Có dữ liệu' if tv is not None else 'N/A – cần bổ sung nguồn doanh nghiệp')
        })
    return pd.DataFrame(rows)

def _dynamic_peer_label_ui(ticker, fallback):
    # V8.73.1: analyst override wins at the UI boundary, independent of imported-module cache.
    src, peers=_override_peer_info(ticker)
    if src and peers:
        return f'Nhóm tương đồng động: {len(peers)} DN từ {src}'
    try:
        from scripts.dynamic_peer_engine import dynamic_peer_label
        x=dynamic_peer_label(ticker)
        return x if x else fallback
    except Exception:
        return fallback

def _rating_no_vn(value):
    """Display rating grades without the historical 'vn' prefix."""
    if value is None:
        return value
    s=str(value).strip()
    if re.match(r'(?i)^vn(?=[A-C])',s):
        s=s[2:]
    return s.upper() if re.match(r'(?i)^[A-C]{1,3}(?:[+-])?(?:-[A-C]{1,3})?$',s) else s

# V8.94.1: unique Plotly key per render, including repeated calls from loops.
_plotly_seq = 0
def _plotly_chart_safe(fig, **kwargs):
    global _plotly_seq
    if fig is None:
        return None
    try:
        if hasattr(fig,'data') and len(fig.data)==0:
            return None
    except Exception:
        pass
    _plotly_seq += 1
    # Streamlit 1.5x deprecates use_container_width in favor of width.
    if "use_container_width" in kwargs:
        ucw = kwargs.pop("use_container_width")
        kwargs.setdefault("width", "stretch" if ucw else "content")
    ticker_key = str(globals().get("selected", globals().get("t", ""))).upper().strip() or "NA"
    kwargs["key"] = f"plotly_{ticker_key}_{_plotly_seq}"
    return st.plotly_chart(fig, **kwargs)

st.set_page_config(page_title='Nền tảng Phân tích, Định giá, M&A & XHTN Doanh nghiệp Việt Nam',page_icon='🏢',layout='wide')
st.markdown('''<style>
.block-container{padding-top:4.35rem!important;max-width:1550px}.muted{color:#9CA3AF;font-size:.86rem}
[data-testid="stSidebar"]{min-width:300px;max-width:300px}
h1{font-size:1.95rem!important;line-height:1.35!important;overflow:visible!important}
h2{font-size:1.4rem!important} h3{font-size:1.1rem!important}
.platform-title{
    font-size:1.82rem;font-weight:800;line-height:1.48!important;
    padding:.52rem 0 .20rem 0!important;margin:0 0 .35rem 0!important;
    overflow:visible!important;white-space:normal;word-break:normal;
}
.platform-disclaimer{
    font-size:.86rem;line-height:1.55!important;color:#AEB4BE;
    padding:.08rem 0 .18rem 0!important;margin:0 0 1.00rem 0!important;
    overflow:visible!important;white-space:normal;
}
[data-testid="stMetricValue"]{font-size:1.3rem} div[data-testid="stTabs"] button{white-space:nowrap;font-weight:650}
</style>''',unsafe_allow_html=True)

def vi(x,d=1):
    v=num(x)
    if v is None:return 'N/A'
    return f'{v:,.{d}f}'.replace(',','X').replace('.',',').replace('X','.')
def pct(x):return 'N/A' if num(x) is None else vi(num(x)*100,1)+'%'
def mult(x):return 'N/A' if num(x) is None else vi(x,2)+'x'
def _price_vnd(x):
    v=num(x)
    if v is None:return None
    v=float(v)
    if 0<v<500:v*=1000.0
    while v>1_000_000:v/=1000.0
    return v if 100<=v<=1_000_000 else None
def money(x):
    v=_price_vnd(x)
    return 'N/A' if v is None else vi(v,0)+' đồng/cp'
def bn(x):return 'N/A' if num(x) is None else vi(num(x)/1e9,0)+' tỷ đồng'


def _security_raw_metric_history(ticker, metric):
    """Fallback to Vnstock raw semantic files for Securities trend metrics.
    Returns canonical Period/Value history without API calls.
    """
    t=str(ticker).upper().strip()
    metric_ids={
        'ROE':('ratio',['RT_PRT_ROE']),
        'ROA':('ratio',['RT_PRT_ROA']),
        'DebtEquity':('ratio',['RT_LEV_DE']),
        'CurrentRatio':('ratio',['RT_LQD_CR']),
        'PB':('ratio',['RT_VALUE_PB']),
        'PE':('ratio',['RT_VALUE_PE']),
        'Revenue':('income',['IS_NET_REVENUE','IS_REVENUE','IS_OPERATING_REVENUE']),
        'NPAT':('income',['IS_NET_PROFIT_AFTER_TAX','IS_NET_PROFIT','IS_PROFIT_AFTER_TAX']),
        'TotalAssets':('balance',['BS_TOTAL_ASSETS']),
        'Equity':('balance',['BS_EQUITY','BS_OWNERS_EQUITY','BS_TOTAL_EQUITY']),
    }
    if metric not in metric_ids:
        return pd.DataFrame(columns=['Period','Value'])
    ds,ids=metric_ids[metric]
    candidates=[ROOT/'data'/'raw'/f'{t}_{ds}.csv']
    if ds=='income':
        candidates += [ROOT/'data'/'raw'/f'{t}_income_statement.csv', ROOT/'data'/'raw'/f'{t}_income.csv']
    p=next((x for x in candidates if x.exists()),None)
    if p is None:
        return pd.DataFrame(columns=['Period','Value'])
    try:
        q=pd.read_csv(p)
    except Exception:
        return pd.DataFrame(columns=['Period','Value'])
    if q.empty or not {'period','id','value'}.issubset(q.columns):
        return pd.DataFrame(columns=['Period','Value'])
    q=q[q['id'].astype(str).str.upper().isin([x.upper() for x in ids])].copy()
    q['Value']=pd.to_numeric(q['value'],errors='coerce')
    q=q.dropna(subset=['Value'])
    if q.empty:
        return pd.DataFrame(columns=['Period','Value'])
    def _canon(v):
        ss=str(v).upper().strip().replace('_','-').replace(' ','')
        m=re.fullmatch(r'(20\d{2})-?Q([1-4])',ss)
        return f"{m.group(1)}-Q{m.group(2)}" if m else None
    q['Period']=q['period'].map(_canon)
    q=q.dropna(subset=['Period'])
    if metric in {'ROE','ROA'}:
        q['Value']=q['Value'].map(lambda x: x/100.0 if abs(float(x))>1.5 else float(x))
    def _ord(v):
        m=re.fullmatch(r'(20\d{2})-Q([1-4])',str(v))
        return int(m.group(1))*4+int(m.group(2)) if m else -1
    q['_ord']=q['Period'].map(_ord)
    return q.sort_values('_ord').drop_duplicates('Period',keep='last')[['Period','Value']]

def _security_peer_raw_mean_history(ticker, metric, max_peers=10):
    """Mean peer history from the same raw semantic files used by the target."""
    try:
        pf=_securities_peer_frame(ticker,max_peers)
    except Exception:
        return pd.DataFrame(columns=['Period','IndustryMean'])
    if pf is None or not len(pf) or 'Ticker' not in pf.columns:
        return pd.DataFrame(columns=['Period','IndustryMean'])
    t=str(ticker).upper().strip()
    peer_tickers=[str(x).upper().strip() for x in pf['Ticker'].tolist() if str(x).upper().strip()!=t][:max_peers]
    frames=[]
    for x in peer_tickers:
        h=_security_raw_metric_history(x,metric)
        if len(h):
            h=h.copy(); h['Ticker']=x
            frames.append(h)
    if not frames:
        return pd.DataFrame(columns=['Period','IndustryMean'])
    allh=pd.concat(frames,ignore_index=True)
    return allh.groupby('Period',as_index=False)['Value'].mean().rename(columns={'Value':'IndustryMean'})

def metric_chart(ticker,metric,title,percent=False):
    """Trend chart with Securities raw-history fallback.
    For Securities ratios, use full quarterly raw semantic history so ROE/ROA,
    Debt/Equity and Current Ratio render like Revenue/NPAT trend charts.
    """
    try:
        et=str(get_company(ticker).get('EntityType','')).upper()
    except Exception:
        et=''

    def _norm(v):
        ss=str(v).upper().strip().replace('_','-').replace(' ','')
        m=re.fullmatch(r'(20\d{2})-?Q([1-4])',ss)
        return f"{m.group(1)}-Q{m.group(2)}" if m else str(v).strip()

    def _ord(v):
        m=re.fullmatch(r'(20\d{2})-Q([1-4])',_norm(v))
        return int(m.group(1))*4+int(m.group(2)) if m else -1

    # Target history: normal history first, raw semantic fallback for Securities.
    h=entity_history(ticker)
    z=pd.DataFrame()
    if h is not None and len(h):
        z=h[h.Metric.astype(str).eq(metric)].copy()
        if len(z):
            z['Value']=pd.to_numeric(z.Value,errors='coerce')
            z=z.dropna(subset=['Value'])
            z['Period']=z['Period'].map(_norm)
            z=z[z['Period'].astype(str).str.len()>0]
            z['_ord']=z['Period'].map(_ord)
            z=z.sort_values('_ord').drop_duplicates('Period',keep='last')[['Period','Value','_ord']]
    if et=='SECURITIES' and (z.empty or z['Period'].nunique()<3):
        rz=_security_raw_metric_history(ticker,metric)
        if len(rz):
            rz=rz.copy(); rz['Period']=rz['Period'].map(_norm); rz['_ord']=rz['Period'].map(_ord)
            z=rz.sort_values('_ord').drop_duplicates('Period',keep='last')[['Period','Value','_ord']]

    # Peer history: normal engine first, then raw peer fallback when sparse.
    p=_final_chart_guard(metric,industry_metric_history(ticker,metric))
    pp=pd.DataFrame()
    if p is not None and len(p):
        pp=p.copy()
        if 'Period' in pp.columns:
            pp['Period']=pp['Period'].map(_norm)
        elif 'PeriodDate' in pp.columns:
            pp['Period']=pd.to_datetime(pp['PeriodDate'],errors='coerce').dt.to_period('Q').astype(str).map(_norm)
        pp['IndustryMean']=pd.to_numeric(pp.get('IndustryMean'),errors='coerce')
        pp=pp.dropna(subset=['IndustryMean'])
        pp['_ord']=pp['Period'].map(_ord)
        pp=pp.sort_values('_ord').drop_duplicates('Period',keep='last')[['Period','IndustryMean','_ord']]
    if et=='SECURITIES' and (pp.empty or pp['Period'].nunique()<3):
        rp=_security_peer_raw_mean_history(ticker,metric,10)
        if len(rp):
            rp=rp.copy(); rp['Period']=rp['Period'].map(_norm); rp['_ord']=rp['Period'].map(_ord)
            pp=rp.sort_values('_ord').drop_duplicates('Period',keep='last')[['Period','IndustryMean','_ord']]

    fig=go.Figure()
    if len(z):
        fig.add_trace(go.Scatter(
            x=z['Period'], y=z['Value'],
            mode='lines+markers' if len(z)>=2 else 'markers',
            name=ticker
        ))
    if len(pp):
        fig.add_trace(go.Scatter(
            x=pp['Period'], y=pp['IndustryMean'],
            mode='lines+markers' if len(pp)>=2 else 'markers',
            line=dict(dash='dash'),
            name='Trung bình peer'
        ))

    periods=[]
    for tr in fig.data:
        try: periods.extend([_norm(x) for x in tr.x])
        except Exception: pass
    periods=sorted(set(periods),key=_ord)
    final_title=title if len(periods)>=2 else title.replace('xu hướng DN và trung bình peer','kỳ gần nhất: DN và trung bình peer')

    fig.update_layout(
        title=final_title, height=330,
        legend=dict(orientation='h',y=-.20),
        margin=dict(t=45,b=70),
        xaxis_title='',
        xaxis=dict(type='category',categoryarray=periods,categoryorder='array')
    )
    if percent:
        fig.update_yaxes(tickformat='.1%')
    return fig

def _latest_metric_period(ticker,metric):
    try:
        h=entity_history(ticker)
        z=h[h.Metric.astype(str).eq(metric)].copy()
        z['Date']=z.Period.map(period_date); z=z.dropna(subset=['Date']).sort_values('Date')
        return str(z.iloc[-1].Period) if len(z) else 'kỳ gần nhất'
    except Exception:
        return 'kỳ gần nhất'

def latest_peer_bar_chart(ticker,metric,title,percent=False,max_peers=10):
    """Latest company + peer bar chart with readable financial units."""
    q=_peer_frame_safe(ticker)
    if q is None or not len(q) or 'Ticker' not in q.columns:
        return go.Figure()
    if metric not in q.columns or pd.to_numeric(q.get(metric),errors='coerce').notna().sum()==0:
        try:
            q=pd.DataFrame([_snapshot_row(x) for x in q['Ticker'].astype(str).tolist()])
        except Exception:
            return go.Figure()
    if metric not in q.columns:
        return go.Figure()

    z=q[['Ticker',metric]].copy()
    z['Ticker']=z['Ticker'].astype(str).str.upper().str.strip()
    z[metric]=pd.to_numeric(z[metric],errors='coerce')

    # Same plausibility guards used elsewhere in the platform.
    v=z[metric]
    if metric=='DebtEquity': v=v.where((v>=0)&(v<=10))
    elif metric=='CurrentRatio': v=v.where((v>0)&(v<=20))
    elif metric=='PE': v=v.where((v>0)&(v<=200))
    elif metric=='PB': v=v.where((v>0)&(v<=20))
    elif metric in {'ROE','ROA'}: v=v.where((v>=-2)&(v<=2))
    z[metric]=v
    z=z.dropna(subset=[metric]).drop_duplicates('Ticker',keep='last')

    selected=str(ticker).upper().strip()
    order=[selected]
    try:
        from scripts.dynamic_peer_engine import select_dynamic_peers
        d=select_dynamic_peers(selected)
        if d is not None and len(d) and 'Ticker' in d.columns:
            order += [str(x).upper().strip() for x in d['Ticker'].tolist()
                      if str(x).upper().strip()!=selected][:max_peers]
    except Exception:
        pass
    if len(order)==1:
        order += [x for x in z['Ticker'].tolist() if x!=selected][:max_peers]

    chosen=z.set_index('Ticker').reindex(order[:max_peers+1]).dropna(subset=[metric]).reset_index()
    if chosen.empty:
        return go.Figure()

    # Monetary metrics: scale raw VND into readable report/platform units.
    money_metrics={
        'TotalAssets','GrossLoans','CustomerDeposits','Revenue','NPAT','Equity',
        'Cash','Debt','TotalDebt','ShortTermDebt','LongTermDebt','MarketCap',
        'NetInterestIncome','OperatingIncome','InterestIncome','InterestExpense',
        'LoanLossProvision','BrokerageRevenue','MarginLoans','TradingAssets',
        'FinancialAssets','AvailableCapital'
    }
    vals=chosen[metric].astype(float)
    scale=1.0; unit=''
    if percent:
        plotvals=vals*100.0
        unit='%'
    elif metric in money_metrics:
        mx=float(vals.abs().max()) if len(vals) else 0
        # V8.97 display convention requested by user:
        # < 100 nghìn tỷ đồng => show in tỷ đồng
        # >= 100 nghìn tỷ đồng => show in nghìn tỷ đồng
        if mx>=100e12:
            scale=1e12; unit='nghìn tỷ đồng'
        elif mx>=1e9:
            scale=1e9; unit='tỷ đồng'
        elif mx>=1e6:
            scale=1e6; unit='triệu đồng'
        else:
            unit='đồng'
        plotvals=vals/scale
    else:
        plotvals=vals

    chosen['PlotValue']=plotvals

    # Human-readable bar labels.
    if percent:
        text=[f'{x:.1f}%'.replace('.',',') for x in plotvals]
    else:
        def _fmt(x):
            if abs(x)>=100:return f'{x:,.0f}'
            if abs(x)>=10:return f'{x:,.1f}'
            return f'{x:,.2f}'
        text=[_fmt(x).replace(',','X').replace('.',',').replace('X','.') for x in plotvals]

    fig=go.Figure(go.Bar(
        x=chosen['Ticker'], y=chosen['PlotValue'],
        text=text, textposition='outside',
        cliponaxis=False
    ))
    fig.update_layout(
        title=title,
        yaxis_title=f'Đơn vị: {unit}' if unit else '',
        xaxis_title='',
        margin=dict(l=45,r=20,t=55,b=35),
        height=360
    )
    if percent:
        fig.update_yaxes(ticksuffix='%')
    return fig

def _growth_from_hist(metric):
    try:x=pd.read_csv(DATA/'bank_history_long.csv')
    except:return pd.DataFrame(columns=['Ticker',metric+'_Growth'])
    x=x[x.Metric.astype(str).eq(metric)].copy(); x['Value']=pd.to_numeric(x.Value,errors='coerce'); x['Date']=x.Period.map(period_date); x=x.dropna(subset=['Value','Date']).sort_values(['Ticker','Date'])
    rows=[]
    for t,g in x.groupby('Ticker'):
        vals=g.Value.tolist(); gr=vals[-1]/vals[max(0,len(vals)-5)]-1 if len(vals)>=2 and vals[max(0,len(vals)-5)] else np.nan; rows.append({'Ticker':t,metric+'_Growth':gr})
    return pd.DataFrame(rows)

def bank_rating_result(ticker,overrides=None):
    if build_credit_rating is None:return {'ICR':'N/A','Error':'Bank rating engine unavailable'}
    try:s=pd.read_csv(DATA/'bank_snapshot.csv')
    except:return {'ICR':'N/A','Error':'No bank snapshot'}
    s=s.copy(); s['ROE_Used']=pd.to_numeric(s.get('ROE'),errors='coerce')
    for m in ['GrossLoans','CustomerDeposits','NPAT']:
        g=_growth_from_hist(m); s=s.merge(g,on='Ticker',how='left')
    try:
        r=build_credit_rating(s,ticker,factor_score_overrides=overrides or {})
        r['Anchor']=r.get('AnchorRating',r.get('Anchor'))
        r['SACP']=r.get('SACPRating',r.get('SACP'))
        r['ICR']=r.get('FinalRating',r.get('ICR'))
        return r
    except Exception as e:return {'ICR':'N/A','Error':str(e)}

u=universe()
st.sidebar.markdown('## PHÂN TÍCH DOANH NGHIỆP')
entity_filter=st.sidebar.selectbox('Nhóm doanh nghiệp',['Tất cả','Ngân hàng','Công ty chứng khoán','Doanh nghiệp phi tài chính'])
maptype={'Ngân hàng':'BANK','Công ty chứng khoán':'SECURITIES','Doanh nghiệp phi tài chính':'CORPORATE'}
z=u if entity_filter=='Tất cả' else u[u.EntityType.eq(maptype[entity_filter])]
labels={r.Ticker:f'{r.Ticker} — {r.CompanyName}' for _,r in z.iterrows()}
selected=st.sidebar.selectbox('Mã doanh nghiệp',z.Ticker.tolist(),format_func=lambda x:labels.get(x,x)) if len(z) else None
presentation=st.sidebar.toggle('Chế độ trình bày',value=False)

if not selected: st.error('Không có doanh nghiệp trong bộ lọc.'); st.stop()
meta=get_company(selected); s=get_snapshot(selected); val=valuation(selected,s); peer=_peer_frame_safe(selected)
industry_name=industry_label(selected)
# Resolve the sector template once for the selected company.
# get_template() returns (template_key, template_dict).
sector_template_key, sector_template = get_template(meta.get('EntityType'), meta.get('Sector'))
st.sidebar.markdown('---'); st.sidebar.markdown('## TRẠNG THÁI')

def _clean_text(x, fallback='N/A'):
    if x is None:
        return fallback
    try:
        if pd.isna(x):
            return fallback
    except Exception:
        pass
    t=str(x).strip()
    return fallback if t in ('', 'nan', 'None', '<NA>') else t

_entity_type=_clean_text(meta.get('EntityType'))
_sector=_clean_text(meta.get('Sector'))
_peer_fallback=_clean_text(meta.get('PeerGroup'))
_methodology=_clean_text(meta.get('Methodology'))

# Exchange/stock exchange is intentionally omitted from the UI.
st.sidebar.success(_entity_type)
st.sidebar.caption(
    f"Ngành: {_sector}\n\n"
    f"Nhóm so sánh: {_dynamic_peer_label_ui(selected, _peer_fallback)}\n\n"
    f"Phương pháp: {_methodology}"
)

st.markdown(
    '<div class="platform-title">NỀN TẢNG PHÂN TÍCH, ĐỊNH GIÁ, M&amp;A &amp; XẾP HẠNG TÍN NHIỆM DOANH NGHIỆP VIỆT NAM</div>'
    '<div class="platform-disclaimer">LƯU Ý: SẢN PHẨM CHỈ NHẰM MỤC ĐÍCH NGHIÊN CỨU, KHÔNG DÙNG CHO MỤC ĐÍCH KHUYẾN NGHỊ ĐẦU TƯ VÀ/HOẶC XẾP HẠNG TÍN NHIỆM - TÁC GIẢ: LÊ HOÀNG QUÂN - ĐT: 0384775999</div>',
    unsafe_allow_html=True
)
st.subheader(f"{selected} — {meta.get('CompanyName')}")

# Header KPIs adapt by entity.
if meta['EntityType']=='BANK': kpis=[('Giá thị trường',money(val.get('Price'))),('P/B',mult(s.get('PB'))),('ROE',pct(s.get('ROE'))),('NPL',pct(s.get('NPL'))),('CAR',pct(s.get('CAR'))),('CASA',pct(s.get('CASA')))]
elif meta['EntityType']=='SECURITIES': kpis=[('Giá thị trường',money(val.get('Price'))),('P/B',mult(s.get('PB'))),('P/E',mult(s.get('PE'))),('ROE',pct(s.get('ROE'))),('Nợ/VCSH',mult(s.get('DebtEquity'))),('Vốn khả dụng',pct((latest_capital_ratio(selected) or s.get('AvailableCapitalRatio'))))]
else:kpis=[('Giá thị trường',money(val.get('Price'))),('P/E',mult(s.get('PE'))),('ROE',pct(s.get('ROE'))),('ROA',pct(s.get('ROA'))),('Nợ/EBITDA',mult(s.get('DebtEBITDA'))),('Thanh toán hiện hành',mult(s.get('CurrentRatio')))]
cols=st.columns(6)
for c,(lab,v) in zip(cols,kpis):c.metric(lab,v)

if meta.get('Methodology')=='EXCLUDED_SPECIALIZED': st.warning('Ngành/loại hình này cần phương pháp XHTN chuyên biệt. App vẫn cho phép phân tích tài chính và định giá, nhưng không phát hành kết quả XHTN tự động.')
if meta['EntityType']!='BANK' and not any(num(s.get(k)) is not None for k in ['TotalAssets','Revenue','ROE','Price']): st.info(f'Chưa có đủ dữ liệu tài chính cho {selected}.')

tabs=st.tabs(['HỒ SƠ DOANH NGHIỆP','PHÂN TÍCH, ĐỊNH GIÁ & M&A','BÁO CÁO XẾP HẠNG TÍN NHIỆM','DỮ LIỆU & QUẢN TRỊ'])

def _safe_show(df, wanted, n=None):
    if df is None or not len(df): return pd.DataFrame()
    cols=[c for c in wanted if c in df.columns]
    q=df[cols].copy() if cols else df.copy()
    return q.head(n) if n else q

def _download_report_block(report_type, rating_result=None):
    title='Báo cáo Phân tích – Định giá – M&A' if report_type=='analysis' else 'Báo cáo mô phỏng quá trình Xếp hạng tín nhiệm'
    st.markdown('---')
    st.subheader('Xuất '+title)
    c1,c2=st.columns(2)
    try:
        docx=generate_docx(selected,report_type,rating_result)
        pdf=generate_pdf(selected,report_type,rating_result)
        suffix='Phan_tich_Dinh_gia_MA' if report_type=='analysis' else 'XHTN'
        c1.download_button('Tải báo cáo Word',docx,file_name=f'{selected}_{suffix}.docx',
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',use_container_width=True,
            key=f'docx_{report_type}')
        c2.download_button('Tải báo cáo PDF',pdf,file_name=f'{selected}_{suffix}.pdf',
            mime='application/pdf',use_container_width=True,key=f'pdf_{report_type}')
    except Exception as e:
        st.warning(f'Chưa tạo được báo cáo: {e}')

with tabs[0]:
    st.subheader('Thông tin tổng quan')
    _profile=load_company_profile(selected)
    if _profile:
        st.write(profile_overview_text(selected))
        _src=profile_source_text(selected)
        if _src:
            st.caption('Nguồn hồ sơ: '+_src)
    else:
        st.info('Chưa có hồ sơ doanh nghiệp được xác minh từ nguồn công khai. Không tự suy diễn phần tổng quan từ dữ liệu Vnstock.')

    st.subheader('Hồ sơ doanh nghiệp')
    a,b,c=st.columns(3)
    a.metric('Ngành',meta.get('Sector','N/A'))
    b.metric('Nhóm so sánh',industry_name)
    c.metric('Phương pháp',meta.get('Methodology','N/A'))
    st.write(f"**{meta.get('CompanyName')}** được hệ thống tự phân loại vào **{meta.get('Sector')}**. "
             f"Methodology XHTN: **{meta.get('Methodology')}**.")
    st.caption(f"Nguồn phân ngành: {meta.get('IndustrySource','Master/Legacy')} · Cấp ICB: {meta.get('IndustryLevelUsed','N/A')}")
    try:
        from scripts.dynamic_peer_engine import select_dynamic_peers
        _dp=select_dynamic_peers(selected)
        if len(_dp):
            with st.expander('Nhóm doanh nghiệp tương đồng được hệ thống tự chọn'):
                _show=[c for c in ['PeerRank','Ticker','CompanyName','Sector','SimilarityScore','SimilarityBasis','PeerPool'] if c in _dp.columns]
                _v=_dp[_show].copy()
                if 'SimilarityScore' in _v.columns:_v['SimilarityScore']=(_v['SimilarityScore']*100).round(1).astype(str)+'%'
                st.dataframe(_v,hide_index=True,use_container_width=True)
                st.caption('Peer được tái tính sau mỗi Full Refresh từ toàn bộ universe Vnstock; Master chỉ còn là metadata/fallback.')
    except Exception:
        pass
    st.markdown('### Hồ sơ tài chính & xu hướng')
    if meta['EntityType']=='BANK':
        ml=[('TotalAssets','Tổng tài sản',False),('GrossLoans','Cho vay khách hàng',False),
            ('CustomerDeposits','Tiền gửi khách hàng',False),('ROE','ROE',True),('ROA','ROA',True),
            ('NIM','NIM',True),('NPL','Nợ xấu',True),('CAR','CAR',True),('CASA','CASA',True),('LDR','LDR',True)]
    else:
        ml=[('Revenue','Doanh thu',False),('NPAT','Lợi nhuận sau thuế',False),('ROE','ROE',True),
            ('ROA','ROA',True),('DebtEquity','Nợ/VCSH',False),('CurrentRatio','Thanh toán hiện hành',False)]
    for i in range(0,len(ml),2):
        cc=st.columns(2)
        for j,(m,t,pf) in enumerate(ml[i:i+2]):
            with cc[j]:
                _plotly_chart_safe(metric_chart(selected,m,f'{t} · xu hướng DN và trung bình peer',pf),use_container_width=True)
                _plotly_chart_safe(latest_peer_bar_chart(selected,m,f'{t} · DN và 10 peer tại kỳ gần nhất',pf),use_container_width=True)
    st.markdown('### Bộ chỉ tiêu theo methodology & nhóm tương đồng động')
    st.caption('Benchmark loại chính doanh nghiệp đang phân tích; chỉ hiển thị trung bình/trung vị khi có tối thiểu 5 peer có dữ liệu cho chỉ tiêu đó.')
    skpi,_,_=sector_kpi_table(selected)
    if meta.get('EntityType')=='SECURITIES':
        _peer_obs0=0
        try:
            _peer_obs0=int(pd.to_numeric(skpi.get('Số DN có dữ liệu'),errors='coerce').fillna(0).max()) if len(skpi) else 0
        except Exception:
            _peer_obs0=0
        if _peer_obs0==0:
            skpi=_securities_kpi_fallback(selected,peer)
    if len(skpi):
        wanted=['Nhóm phân tích','Chỉ tiêu','Doanh nghiệp','Trung bình ngành','Trung vị ngành',
                'Số DN có dữ liệu','Chênh lệch với TB ngành','Trạng thái dữ liệu']
        st.dataframe(_safe_show(skpi,wanted),hide_index=True,use_container_width=True)
    else: st.info('Chưa có dữ liệu methodology KPI.')
    if len(peer):
        st.markdown('### Vị trí tương đối trong peer group')
        q=peer.copy(); q['Doanh nghiệp']=q.Ticker.astype(str)
        cols_show=['Doanh nghiệp','ROE','ROA','PB','PE','DebtEquity','CurrentRatio','NPL','CAR','CASA','NIM','CIR','LDR']
        st.dataframe(_safe_show(q,cols_show),hide_index=True,use_container_width=True)

with tabs[1]:
    st.subheader('Phân tích, Định giá & M&A')
    aa=intelligent_analyze(selected)
    c1,c2,c3=st.columns(3)
    c1.metric('Quan điểm định lượng',aa.get('View','N/A')); c2.metric('Điểm tín hiệu',aa.get('Score','N/A')); c3.metric('Mẫu chuyên ngành',aa.get('Template','N/A'))
    st.write(aa.get('Conclusion',''))
    l,r=st.columns(2)
    with l:
        st.markdown('#### Điểm mạnh tương đối')
        for x in aa.get('Strengths',[]): st.write('• '+x)
    with r:
        st.markdown('#### Rủi ro / điểm yếu tương đối')
        for x in aa.get('Risks',[]): st.write('• '+x)

    st.markdown('### Định giá')
    vr=valuation_regime(selected); fv=fair_value_range(selected); vt=triangulate(selected)
    a,b,c,d=st.columns(4)
    a.metric('Giá thị trường',money(val.get('Price'))); b.metric('Giá trị tham chiếu',money(val.get('FairValue')))
    c.metric('Tiềm năng',pct(val.get('Upside'))); d.metric('Chế độ định giá',vr.get('Regime','N/A'))
    q1,q2,q3,q4=st.columns(4)
    fmt=lambda x:'N/A' if x is None else f"{x:,.0f} đồng/cp".replace(',','.')
    q1.metric('Bear',fmt(fv.get('Bear')))
    q2.metric('Base',fmt(fv.get('Base')))
    q3.metric('Bull',fmt(fv.get('Bull')))
    q4.metric('Chiến lược/M&A',fmt(fv.get('StrategicMA')))
    _sa=fv.get('ScenarioAssumptions',{})
    if _sa:
        st.caption(
            "Bear: "+str(_sa.get('Bear',''))+"  |  "
            "Base: "+str(_sa.get('Base',''))+"  |  "
            "Bull: "+str(_sa.get('Bull',''))
        )
    lenses=pd.DataFrame(vt.get('Lenses',[]))
    if len(lenses): st.dataframe(lenses,hide_index=True,use_container_width=True)

    st.markdown('### M&A, quyền kiểm soát, tái cấu trúc & kịch bản stress')
    base=num(val.get('FairValue')) or num(val.get('Price'))
    c1,c2,c3=st.columns(3)
    premium=c1.slider('Thặng dư quyền kiểm soát',0.0,0.60,0.15,0.01)
    synergy=c2.slider('Giá trị cộng hưởng',0.0,0.50,0.08,0.01)
    stake=c3.slider('Tỷ lệ mua',0.01,1.0,0.51,0.01)
    strategic=base*(1+premium+synergy) if base else None
    st.metric('Giá trị chiến lược tham chiếu/cp',money(strategic))
    st.caption('Control premium, synergy và tỷ lệ mua là biến kịch bản theo từng thương vụ; không hard-code giả định của STB cho doanh nghiệp khác.')
    x1,x2=st.columns(2)
    with x1:
        debt_cut=st.slider('Giảm nợ giả định',0,50,10,5)
        equity_raise=st.slider('Tăng vốn giả định',0,50,10,5)
        st.write(f'Kịch bản tái cấu trúc: giảm nợ {debt_cut}% · tăng vốn {equity_raise}%.')
    with x2:
        if meta['EntityType']=='BANK':
            shock=st.slider('Shock NPL (điểm %)',0.0,5.0,1.0,.25)
            st.write(f'NPL hiện tại {pct(s.get("NPL"))}; stress cộng thêm {vi(shock,2)} điểm %.')
        else:
            rev=st.slider('Shock doanh thu',-50,20,-10,5); margin=st.slider('Shock biên lợi nhuận',-10,10,-2,1)
            st.write(f'Doanh thu {rev:+d}% · biên lợi nhuận {margin:+d} điểm %.')
    _download_report_block('analysis')

with tabs[2]:
    st.subheader('Báo cáo Xếp hạng tín nhiệm')
    rr3=rate_three_methodologies(selected)
    r1,r2,r3=st.columns(3)
    r1.metric('Anchor',_rating_no_vn(rr3.get('Anchor','N/A')));r2.metric('SACP / SCA',_rating_no_vn(rr3.get('SACP',rr3.get('SCA','N/A'))));r3.metric('ICR',_rating_no_vn(rr3.get('ICR','N/A')))

    st.markdown('### Phân tích các chỉ số tín dụng trọng yếu')
    _rating_metric_map={
        'BANK':['ROE','ROA','NIM','NPL','CAR','CASA','LDR','CIR'],
        'SECURITIES':['ROE','ROA','AvailableCapitalRatio','DebtEquity','CurrentRatio','PB','PE'],
        'CORPORATE':['Revenue','GrossMargin','EBITDAMargin','ROE','ROA','DebtEquity','DebtEBITDA','CFO_Debt','FOCF_Debt','CurrentRatio','CashDebt']
    }
    _rkpi,_,_=sector_kpi_table(selected)
    if meta.get('EntityType')=='SECURITIES':
        _peer_obs=0
        try:
            _peer_obs=int(pd.to_numeric(_rkpi.get('Số DN có dữ liệu'),errors='coerce').fillna(0).max()) if len(_rkpi) else 0
        except Exception:
            _peer_obs=0
        if _peer_obs==0:
            _rkpi=_securities_kpi_fallback(selected,peer)
    if len(_rkpi):
        _want=set(_rating_metric_map.get(meta.get('EntityType'),[]))
        _show=_rkpi[_rkpi.Metric.astype(str).isin(_want)].copy() if 'Metric' in _rkpi.columns else _rkpi.copy()
        _cols=['Nhóm phân tích','Chỉ tiêu','Doanh nghiệp','Trung bình ngành','Trung vị ngành','Số DN có dữ liệu','Chênh lệch với TB ngành','Trạng thái dữ liệu']
        st.dataframe(_safe_show(_show,_cols),hide_index=True,use_container_width=True)
        # Current-period cross-sectional charts for the most decision-relevant metrics.
        if meta.get('EntityType')=='BANK': _bar_metrics=[('ROE','ROE',True),('NPL','Nợ xấu',True),('CAR','CAR',True),('CASA','CASA',True)]
        elif meta.get('EntityType')=='SECURITIES': _bar_metrics=[('ROE','ROE',True),('DebtEquity','Nợ/VCSH',False),('CurrentRatio','Thanh toán hiện hành',False),('AvailableCapitalRatio','Vốn khả dụng',True)]
        else: _bar_metrics=[('ROE','ROE',True),('DebtEquity','Nợ/VCSH',False),('DebtEBITDA','Nợ/EBITDA',False),('CurrentRatio','Thanh toán hiện hành',False)]
        for _i in range(0,len(_bar_metrics),2):
            _cc=st.columns(2)
            for _j,(_m,_t,_pf) in enumerate(_bar_metrics[_i:_i+2]):
                with _cc[_j]: _plotly_chart_safe(latest_peer_bar_chart(selected,_m,f'{_t} · DN và 10 peer',_pf),use_container_width=True)
    else:
        st.info('Chưa có đủ chỉ tiêu định lượng để phân tích XHTN.')

    if rr3.get('Methodology')=='CORPORATE':
        labels=rr3.get('RiskLabels',{}); _rows=[]
        for k,v in rr3.get('RiskScores',{}).items():
            try: _score=f'{float(v):.1f}/6' if pd.notna(v) else 'N/A'
            except Exception: _score='N/A'
            _rows.append({'Nhóm rủi ro':k,'Điểm':_score,'Mức rủi ro':labels.get(k,'N/A')})
        st.markdown('### Tổng hợp hồ sơ rủi ro')
        st.dataframe(pd.DataFrame(_rows),hide_index=True,use_container_width=True)
        p1,p2,p3=st.columns(3); p1.metric('Peer có dữ liệu',rr3.get('PeerCount',0)); p2.metric('Thanh khoản',rr3.get('Liquidity','N/A')); p3.metric('Đủ dữ liệu để tự động XHTN','CÓ' if rr3.get('DataSufficientForAutoRating') else 'CHƯA')
        if not rr3.get('DataSufficientForAutoRating'):
            st.warning('Chưa đủ dữ liệu doanh nghiệp/peer để phát hành bậc XHTN mô phỏng.')
    elif rr3.get('Methodology') in ('BANK','SECURITIES'):
        st.markdown('### Tổng hợp hồ sơ rủi ro')
        st.dataframe(pd.DataFrame([{'Yếu tố':k,'Đánh giá':v} for k,v in rr3.get('Factors',{}).items()]),hide_index=True,use_container_width=True)

    # V8.75: final component/notch summary, mirroring the user's BANK/SECURITIES sample reports.
    st.markdown('### Tổng kết cấu phần xếp hạng')
    if rr3.get('Methodology') in ('BANK','SECURITIES'):
        _desc_score={'Rất Mạnh':'1/6','Mạnh':'2/6','Phù Hợp':'3/6','Trung Bình':'4/6','Yếu':'5/6','Rất Yếu':'6/6'}
        _desc_notch={'Rất Mạnh':2,'Mạnh':1,'Phù Hợp':0,'Trung Bình':-1,'Yếu':-2,'Rất Yếu':-4}
        _sumrows=[]
        if rr3.get('Methodology')=='SECURITIES':
            _sumrows.append({'Cấu phần':'BICRA tham chiếu','Đánh giá / Điểm':_rating_no_vn(rr3.get('BICRAReference','N/A')),'Nâng/Hạ notch':'—','Kết quả':'Tham chiếu ngành ngân hàng'})
            _sumrows.append({'Cấu phần':'Điều chỉnh Anchor CTCK','Đánh giá / Điểm':'Đặc thù ngành CTCK','Nâng/Hạ notch':f"{int(rr3.get('SectorAnchorAdjustment',-2)):+d}",'Kết quả':_rating_no_vn(rr3.get('Anchor','N/A'))})
        else:
            _sumrows.append({'Cấu phần':'Điểm ban đầu ngành / BICRA','Đánh giá / Điểm':_rating_no_vn(rr3.get('BICRA',rr3.get('Anchor','N/A'))),'Nâng/Hạ notch':'—','Kết quả':_rating_no_vn(rr3.get('Anchor','N/A'))})
        for _k,_v in rr3.get('Factors',{}).items():
            _sumrows.append({'Cấu phần':_k,'Đánh giá / Điểm':f"{_v} ({_desc_score.get(_v,'N/A')})",'Nâng/Hạ notch':f"{_desc_notch.get(_v,0):+d}",'Kết quả':'Điều chỉnh nội sinh'})
        _sumrows.append({'Cấu phần':'Tổng điều chỉnh nội sinh','Đánh giá / Điểm':'—','Nâng/Hạ notch':f"{int(rr3.get('InternalNotches',0)):+d}",'Kết quả':_rating_no_vn(rr3.get('SACP','N/A'))})
        _sumrows.append({'Cấu phần':'Hỗ trợ bên ngoài','Đánh giá / Điểm':'Trung lập' if int(rr3.get('ExternalSupportNotches',0))==0 else 'Có điều chỉnh','Nâng/Hạ notch':f"{int(rr3.get('ExternalSupportNotches',0)):+d}",'Kết quả':_rating_no_vn(rr3.get('ICR','N/A'))})
        _sumrows.append({'Cấu phần':'Kết quả XHTN','Đánh giá / Điểm':rr3.get('Outlook','Ổn định'),'Nâng/Hạ notch':'—','Kết quả':_rating_no_vn(rr3.get('ICR','N/A'))})
        st.dataframe(pd.DataFrame(_sumrows),hide_index=True,use_container_width=True)
    elif rr3.get('Methodology')=='CORPORATE':
        _rs=rr3.get('RiskScores',{}); _rl=rr3.get('RiskLabels',{})
        _sumrows=[]
        for _k,_v in _rs.items():
            try:_pt=f"{float(_v):.1f}/6"
            except Exception:_pt='N/A'
            _sumrows.append({'Cấu phần':_k,'Điểm':_pt,'Mức rủi ro':_rl.get(_k,'N/A'),'Tác động':'Điểm cấu phần'})
        _weighted=rr3.get('WeightedScore')
        try:_weighted_txt=f"{float(_weighted):.2f}/6"
        except Exception:_weighted_txt='N/A'
        def _corp_anchor_band_ui(x):
            try:x=float(x)
            except Exception:return 'N/A'
            if x<=1.155:return f"{x:.2f}/6 → AAA"
            if x<=1.47:return f"{x:.2f}/6 → AA+"
            if x<=1.785:return f"{x:.2f}/6 → AA"
            if x<=2.095:return f"{x:.2f}/6 → AA-"
            if x<=2.405:return f"{x:.2f}/6 → A+"
            if x<=2.72:return f"{x:.2f}/6 → A"
            if x<=3.035:return f"{x:.2f}/6 → A-"
            if x<=3.345:return f"{x:.2f}/6 → BBB+"
            if x<=3.655:return f"{x:.2f}/6 → BBB"
            if x<=3.97:return f"{x:.2f}/6 → BBB-"
            if x<=4.285:return f"{x:.2f}/6 → BB+"
            if x<=4.595:return f"{x:.2f}/6 → BB"
            if x<=4.905:return f"{x:.2f}/6 → BB-"
            if x<=5.22:return f"{x:.2f}/6 → B+"
            if x<=5.535:return f"{x:.2f}/6 → B"
            if x<=5.845:return f"{x:.2f}/6 → B-"
            return f"{x:.2f}/6 → CCC-C"
        def _corp_anchor_rating_ui(x):
            s=_corp_anchor_band_ui(x)
            return s.split('→')[-1].strip() if '→' in s else 'N/A'
        _sumrows += [
            {'Cấu phần':'Điểm rủi ro tổng hợp có trọng số','Điểm':_weighted_txt,'Mức rủi ro':'Điểm cuối trước modifier','Tác động':_corp_anchor_band_ui(_weighted)},
            {'Cấu phần':'Anchor quy đổi từ điểm tổng hợp','Điểm':_corp_anchor_rating_ui(_weighted),'Mức rủi ro':'Quy đổi theo thang 17 bậc','Tác động':'Điểm → Anchor'},
            {'Cấu phần':'Thanh khoản','Điểm':str(rr3.get('LiquidityScore','N/A')),'Mức rủi ro':rr3.get('Liquidity','N/A'),'Tác động':'Modifier/cap nếu trọng yếu; không cộng trực tiếp vào điểm tổng hợp'},
            {'Cấu phần':'Modifier','Điểm':'—','Mức rủi ro':'—','Tác động':f"{int(rr3.get('ModifierNotches',0)):+d} notch"},
            {'Cấu phần':'SCA','Điểm':_rating_no_vn(rr3.get('SCA','N/A')),'Mức rủi ro':'Sau modifier/cap','Tác động':'Anchor + modifier/cap'},
            {'Cấu phần':'Hỗ trợ bên ngoài','Điểm':'—','Mức rủi ro':'—','Tác động':f"{int(rr3.get('ExternalSupportNotches',0)):+d} notch"},
            {'Cấu phần':'Kết quả XHTN','Điểm':_rating_no_vn(rr3.get('ICR','N/A')),'Mức rủi ro':rr3.get('Outlook','N/A'),'Tác động':'SCA + hỗ trợ bên ngoài'},
        ]
        st.dataframe(pd.DataFrame(_sumrows),hide_index=True,use_container_width=True)

    rc=committee_pack(selected)
    st.markdown('### Waterfall trình Hội đồng XHTN')
    st.dataframe(pd.DataFrame(rc.get('Waterfall',[])),hide_index=True,use_container_width=True)
    ev=rating_evidence(selected)
    st.markdown('### Mức độ tin cậy của kết quả')
    e1,e2,e3=st.columns(3); e1.metric('ICR mô phỏng',_rating_no_vn(ev.get('ICR','N/A')));e2.metric('Độ tin cậy XHTN',ev.get('RatingConfidence','N/A'));e3.metric('Độ đầy đủ dữ liệu',f"{ev.get('DataQuality',{}).get('Coverage',0)*100:.0f}%")

    with st.expander('Phương pháp, audit trail & chi tiết máy tính',expanded=False):
        st.write(f"**Phương pháp tự động lựa chọn:** {rr3.get('MethodologyName','N/A')}")
        if rr3.get('Audit'): st.caption(rr3.get('Audit',''))
        if rr3.get('EvidenceMetrics'): st.caption('Chỉ tiêu định lượng sử dụng: '+', '.join(rr3.get('EvidenceMetrics',[])))
        ledger=pd.DataFrame(ev.get('EvidenceLedger',[]))
        if len(ledger): st.dataframe(ledger,hide_index=True,use_container_width=True)
        st.json(rr3)
    st.session_state['rating_result']=rr3
    _download_report_block('rating',rr3)

with tabs[3]:
    st.subheader('Dữ liệu & Quản trị')
    try: cov=pd.read_csv(DATA/'coverage_matrix.csv')
    except Exception: cov=build_coverage_matrix() if build_coverage_matrix else pd.DataFrame()
    if len(cov):
        a,b,c,d=st.columns(4)
        a.metric('Universe trong Master',f'{len(cov):,}'.replace(',', '.'))
        a1=int((cov.Readiness=='PRODUCTION_READY').sum()) if 'Readiness' in cov else 0
        a2=int((cov.Readiness=='PARTIAL').sum()) if 'Readiness' in cov else 0
        a3=int((cov.Readiness=='INSUFFICIENT_DATA').sum()) if 'Readiness' in cov else 0
        b.metric('Sẵn sàng phân tích',f'{a1:,}'.replace(',', '.'));c.metric('Phủ một phần',f'{a2:,}'.replace(',', '.'));d.metric('Thiếu dữ liệu',f'{a3:,}'.replace(',', '.'))
        st.dataframe(cov,hide_index=True,use_container_width=True)
    st.markdown('### Dynamic peer engine')
    try:
        dps=pd.read_csv(DATA/'dynamic_peer_summary.csv')
        if len(dps):
            st.dataframe(dps,hide_index=True,use_container_width=True)
        else: st.info('Chưa có dữ liệu nhóm doanh nghiệp tương đồng.')
    except Exception:
        st.info('Dynamic peer map sẽ được tạo sau RUN_FULL_REFRESH.bat.')
    st.markdown('### Universe & methodology router')
    cols=[c for c in ['Ticker','CompanyName','EntityType','Sector','Exchange','PeerGroup','Methodology'] if c in u.columns]
    st.dataframe(u[cols],hide_index=True,use_container_width=True)
