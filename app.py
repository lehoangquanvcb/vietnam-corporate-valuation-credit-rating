from pathlib import Path
import io, json
import numpy as np, pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scripts.universal_data import universe,get_company,get_snapshot,entity_history,peer_snapshot,peer_metric_history,industry_snapshot,industry_metric_history,industry_label,period_date,num,coverage
from scripts.multisector_valuation import valuation
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

def _dynamic_peer_label_ui(ticker, fallback):
    try:
        from scripts.dynamic_peer_engine import dynamic_peer_label
        x=dynamic_peer_label(ticker)
        return x if x else fallback
    except Exception:
        return fallback

st.set_page_config(page_title='Nền tảng Phân tích, Định giá, M&A & XHTN Doanh nghiệp Việt Nam',page_icon='🏢',layout='wide')
st.markdown('''<style>
.block-container{padding-top:1rem;max-width:1550px}.muted{color:#9CA3AF;font-size:.86rem}
[data-testid="stSidebar"]{min-width:300px;max-width:300px} h1{font-size:1.95rem!important} h2{font-size:1.4rem!important} h3{font-size:1.1rem!important}
[data-testid="stMetricValue"]{font-size:1.3rem} div[data-testid="stTabs"] button{white-space:nowrap;font-weight:650}
</style>''',unsafe_allow_html=True)

def vi(x,d=1):
    v=num(x)
    if v is None:return 'N/A'
    return f'{v:,.{d}f}'.replace(',','X').replace('.',',').replace('X','.')
def pct(x):return 'N/A' if num(x) is None else vi(num(x)*100,1)+'%'
def mult(x):return 'N/A' if num(x) is None else vi(x,2)+'x'
def money(x):return 'N/A' if num(x) is None else vi(num(x)*1000,0)+' đồng/cp'
def bn(x):return 'N/A' if num(x) is None else vi(num(x)/1e9,0)+' tỷ đồng'

def metric_chart(ticker,metric,title,percent=False):
    h=entity_history(ticker); p=industry_metric_history(ticker,metric); fig=go.Figure()
    if len(h):
        z=h[h.Metric.astype(str).eq(metric)].copy(); z['Date']=z.Period.map(period_date); z['Value']=pd.to_numeric(z.Value,errors='coerce'); z=z.dropna(subset=['Date','Value']).sort_values('Date')
        if len(z):fig.add_trace(go.Scatter(x=z.Date,y=z.Value,mode='markers' if len(z)<3 else 'lines+markers',name=ticker))
    if len(p):fig.add_trace(go.Scatter(x=p.PeriodDate,y=p.IndustryMean,mode='markers' if len(p)<3 else 'lines',line=dict(dash='dash'),name='Trung bình ngành'))
    fig.update_layout(title=title,height=370,legend=dict(orientation='h',y=-.2),margin=dict(t=45,b=70),xaxis_title='')
    if percent:fig.update_yaxes(tickformat='.1%')
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
meta=get_company(selected); s=get_snapshot(selected); val=valuation(selected,s); peer=industry_snapshot(selected)
industry_name=industry_label(selected)
# Resolve the sector template once for the selected company.
# get_template() returns (template_key, template_dict).
sector_template_key, sector_template = get_template(meta.get('EntityType'), meta.get('Sector'))
st.sidebar.markdown('---'); st.sidebar.markdown('## TRẠNG THÁI')
st.sidebar.success(f"{meta.get('EntityType')} · {meta.get('Exchange')}")
st.sidebar.caption(f"Ngành: {meta.get('Sector')}\n\nNhóm so sánh: {_dynamic_peer_label_ui(ticker, meta.get('PeerGroup'))}\n\nPhương pháp: {meta.get('Methodology')}")

st.title('NỀN TẢNG PHÂN TÍCH, ĐỊNH GIÁ, M&A & XẾP HẠNG TÍN NHIỆM DOANH NGHIỆP VIỆT NAM')
st.caption('FULL MARKET DECISION INTELLIGENCE · Ngân hàng + Công ty chứng khoán + Doanh nghiệp phi tài chính · Vnstock Bronze LOCAL → CSV → GitHub → Streamlit')
st.subheader(f"{selected} — {meta.get('CompanyName')}")

# Header KPIs adapt by entity.
if meta['EntityType']=='BANK': kpis=[('Giá thị trường',money(s.get('Price'))),('P/B',mult(s.get('PB'))),('ROE',pct(s.get('ROE'))),('NPL',pct(s.get('NPL'))),('CAR',pct(s.get('CAR'))),('CASA',pct(s.get('CASA')))]
elif meta['EntityType']=='SECURITIES': kpis=[('Giá thị trường',money(s.get('Price'))),('P/B',mult(s.get('PB'))),('P/E',mult(s.get('PE'))),('ROE',pct(s.get('ROE'))),('Nợ/VCSH',mult(s.get('DebtEquity'))),('Vốn khả dụng',pct(s.get('AvailableCapitalRatio')))]
else:kpis=[('Giá thị trường',money(s.get('Price'))),('P/E',mult(s.get('PE'))),('ROE',pct(s.get('ROE'))),('ROA',pct(s.get('ROA'))),('Nợ/EBITDA',mult(s.get('DebtEBITDA'))),('Thanh toán hiện hành',mult(s.get('CurrentRatio')))]
cols=st.columns(6)
for c,(lab,v) in zip(cols,kpis):c.metric(lab,v)

if meta.get('Methodology')=='EXCLUDED_SPECIALIZED': st.warning('Ngành/loại hình này cần phương pháp XHTN chuyên biệt. App vẫn cho phép phân tích tài chính và định giá, nhưng không phát hành kết quả XHTN tự động.')
if meta['EntityType']!='BANK' and not any(num(s.get(k)) is not None for k in ['TotalAssets','Revenue','ROE','Price']): st.info(f'Chưa có BCTC Vnstock LOCAL cho {selected}. Chạy RUN_REFRESH_ONE_COMPANY.bat và nhập {selected}; Streamlit Cloud sẽ đọc CSV sau khi push GitHub.')

tabs=st.tabs(['HỒ SƠ DOANH NGHIỆP','PHÂN TÍCH, ĐỊNH GIÁ & M&A','BÁO CÁO XẾP HẠNG TÍN NHIỆM','DỮ LIỆU & QUẢN TRỊ'])

def _safe_show(df, wanted, n=None):
    if df is None or not len(df): return pd.DataFrame()
    cols=[c for c in wanted if c in df.columns]
    q=df[cols].copy() if cols else df.copy()
    return q.head(n) if n else q

def _download_report_block(report_type, rating_result=None):
    title='Báo cáo Phân tích – Định giá – M&A' if report_type=='analysis' else 'Báo cáo Xếp hạng tín nhiệm'
    st.markdown('---')
    st.subheader('Xuất '+title)
    st.caption('Báo cáo A4 tự dồn trang theo nội dung thực tế; không ép mỗi chương sang một trang mới.')
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
            with cc[j]: st.plotly_chart(metric_chart(selected,m,f'{t} · so với nhóm tương đồng',pf),use_container_width=True)
    st.markdown('### Bộ chỉ tiêu theo methodology & nhóm tương đồng động')
    skpi,_,_=sector_kpi_table(selected)
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
    q1,q2,q3,q4=st.columns(4); fmt=lambda x:'N/A' if x is None else f"{x:,.0f}".replace(',','.')
    q1.metric('Bear',fmt(fv.get('Bear')));q2.metric('Base',fmt(fv.get('Base')));q3.metric('Bull',fmt(fv.get('Bull')));q4.metric('Chiến lược/M&A',fmt(fv.get('StrategicMA')))
    lenses=pd.DataFrame(vt.get('Lenses',[]))
    if len(lenses): st.dataframe(lenses,hide_index=True,use_container_width=True)

    st.markdown('### M&A, quyền kiểm soát, tái cấu trúc & kịch bản stress')
    base=num(val.get('FairValue')) or num(s.get('Price'))
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
    st.markdown(f"**Phương pháp tự động lựa chọn:** {rr3.get('MethodologyName','N/A')}")
    st.caption(rr3.get('Audit',''))
    r1,r2,r3=st.columns(3)
    r1.metric('Anchor',rr3.get('Anchor','N/A'));r2.metric('SACP / SCA',rr3.get('SACP',rr3.get('SCA','N/A')));r3.metric('ICR',rr3.get('ICR','N/A'))
    if rr3.get('Methodology')=='BANK':
        st.write('**BICRA:**',rr3.get('BICRA'),' · **Điều chỉnh nội sinh:**',rr3.get('InternalNotches'),'bậc')
        st.dataframe(pd.DataFrame([{'Yếu tố':k,'Đánh giá':v} for k,v in rr3.get('Factors',{}).items()]),hide_index=True,use_container_width=True)
    elif rr3.get('Methodology')=='SECURITIES':
        st.write('**BICRA tham chiếu:**',rr3.get('BICRAReference'),' → **điều chỉnh Anchor CTCK:** -2 bậc')
        st.dataframe(pd.DataFrame([{'Yếu tố':k,'Đánh giá':v} for k,v in rr3.get('Factors',{}).items()]),hide_index=True,use_container_width=True)
    elif rr3.get('Methodology')=='CORPORATE':
        st.dataframe(pd.DataFrame([{'Nhóm rủi ro':k,'Điểm 1–6':v} for k,v in rr3.get('RiskScores',{}).items()]),hide_index=True,use_container_width=True)
        st.warning('Điểm tự động là sơ bộ khi dữ liệu định tính/KCF chưa đầy đủ; app không dùng methodology ngân hàng thay thế methodology doanh nghiệp.')
    rc=committee_pack(selected)
    st.markdown('### Waterfall trình Hội đồng XHTN')
    st.dataframe(pd.DataFrame(rc.get('Waterfall',[])),hide_index=True,use_container_width=True)
    ev=rating_evidence(selected)
    st.markdown('### Sổ bằng chứng & mức độ tin cậy')
    e1,e2,e3=st.columns(3)
    e1.metric('ICR mô phỏng',ev.get('ICR','N/A'));e2.metric('Độ tin cậy XHTN',ev.get('RatingConfidence','N/A'));e3.metric('Độ đầy đủ dữ liệu',f"{ev.get('DataQuality',{}).get('Coverage',0)*100:.0f}%")
    ledger=pd.DataFrame(ev.get('EvidenceLedger',[]))
    if len(ledger): st.dataframe(ledger,hide_index=True,use_container_width=True)
    st.session_state['rating_result']=rr3
    with st.expander('Chi tiết kết quả máy tính / audit trail'): st.json(rr3)
    _download_report_block('rating',rr3)

with tabs[3]:
    st.subheader('Dữ liệu & Quản trị')
    st.caption('Vnstock Bronze chạy LOCAL → ghi CSV/model outputs → push GitHub → Streamlit Cloud chỉ đọc dữ liệu repository.')
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
        else: st.info('Dynamic peer map sẽ được tạo sau RUN_FULL_REFRESH.bat.')
    except Exception:
        st.info('Dynamic peer map sẽ được tạo sau RUN_FULL_REFRESH.bat.')
    st.markdown('### Universe & methodology router')
    cols=[c for c in ['Ticker','CompanyName','EntityType','Sector','Exchange','PeerGroup','Methodology'] if c in u.columns]
    st.dataframe(u[cols],hide_index=True,use_container_width=True)
