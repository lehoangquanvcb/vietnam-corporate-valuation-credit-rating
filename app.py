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
from scripts.methodology_data_quality import methodology_readiness
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
st.sidebar.caption(f"Ngành: {meta.get('Sector')}\n\nNhóm so sánh: {meta.get('PeerGroup')}\n\nPhương pháp: {meta.get('Methodology')}")

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

tabs=st.tabs(['TRUNG TÂM PHÂN TÍCH','PHÂN TÍCH GIÁ CỔ PHIẾU','Phủ dữ liệu toàn thị trường','Tổng quan','Hồ sơ doanh nghiệp','Phân tích tài chính','So sánh tương quan','Định giá','M&A / Quyền kiểm soát','Tái cấu trúc','Báo cáo Xếp hạng tín nhiệm','Kịch bản & Stress','Báo cáo & Quản trị'])


with tabs[0]:
    st.subheader('Hai nhiệm vụ cốt lõi')
    a,b=st.columns(2)
    with a:
        st.markdown('### 1. PHÂN TÍCH GIÁ CỔ PHIẾU')
        st.write('Phân tích cơ bản → so sánh ngành → định giá tương đối/nội tại → M&A & control premium → stress test → vùng giá hợp lý.')
        st.info('Đầu ra: Báo cáo Phân tích – Định giá – M&A khoảng 30 trang A4.')
    with b:
        st.markdown('### 2. XẾP HẠNG TÍN NHIỆM')
        st.write('Vĩ mô/ngành → hồ sơ kinh doanh → hồ sơ tài chính → Anchor → notch/điều chỉnh → SACP/SCA → hỗ trợ → ICR → sensitivity.')
        st.info('Đầu ra: Báo cáo Xếp hạng tín nhiệm khoảng 30 trang A4.')
    st.markdown('---')
    st.write(f"**Doanh nghiệp đang phân tích:** {selected} – {meta.get('CompanyName')}")
    st.write(f"**Ngành tự nhận diện:** {meta.get('Sector')} · **Methodology XHTN:** {meta.get('Methodology')}")
    st.caption('Hai nhiệm vụ dùng chung một Data Layer và Industry Benchmark, nhưng giữ riêng phương pháp luận, kết luận và báo cáo đầu ra.')

with tabs[1]:
    vr=valuation_regime(selected)
    st.markdown('#### Chế độ định giá tương đối')
    x1,x2,x3=st.columns(3)
    x1.metric('Trạng thái',vr['Regime'])
    x2.metric('P/E ngành', 'N/A' if vr['IndustryPE'] is None else f"{vr['IndustryPE']:.2f}x")
    x3.metric('P/B ngành', 'N/A' if vr['IndustryPB'] is None else f"{vr['IndustryPB']:.2f}x")
    for n in vr['Notes']: st.write('• '+n)
    fv=fair_value_range(selected)
    st.markdown('#### Vùng giá Bear – Base – Bull và Giá trị chiến lược/M&A')
    c1,c2,c3,c4=st.columns(4)
    fmt=lambda x: 'N/A' if x is None else f"{x:,.0f}".replace(',', '.')
    c1.metric('Bear',fmt(fv.get('Bear')))
    c2.metric('Base',fmt(fv.get('Base')))
    c3.metric('Bull',fmt(fv.get('Bull')))
    c4.metric('Chiến lược/M&A',fmt(fv.get('StrategicMA')))
    st.caption('Giá trị chiến lược/M&A là kịch bản riêng theo từng thương vụ; không dùng giả định riêng của một cổ phiếu cho toàn thị trường.')
    vt=triangulate(selected)
    st.markdown('#### Kiểm tra chéo định giá & độ tin cậy phân tích')
    q1,q2,q3=st.columns(3)
    q1.metric('Độ tin cậy phân tích',vt.get('AnalyticalConfidence','N/A'))
    q2.metric('Độ đầy đủ dữ liệu',f"{vt.get('DataQuality',{}).get('Coverage',0)*100:.0f}%")
    q3.metric('Chế độ định giá',vt.get('Regime','N/A'))
    st.dataframe(pd.DataFrame(vt.get('Lenses',[])),hide_index=True,use_container_width=True)
    if vt.get('DataQuality',{}).get('Missing'):
        st.caption('Dữ liệu cốt lõi còn thiếu: '+', '.join(vt['DataQuality']['Missing']))


    st.subheader('NHIỆM VỤ 1 – PHÂN TÍCH GIÁ CỔ PHIẾU')
    aa=intelligent_analyze(selected)
    c1,c2,c3=st.columns(3)
    c1.metric('Quan điểm định lượng',aa['View']);c2.metric('Điểm tín hiệu',aa['Score']);c3.metric('Mẫu chuyên ngành',aa['Template'])
    st.write(aa['Conclusion'])
    l,r=st.columns(2)
    with l:
        st.markdown('#### Điểm mạnh tương đối')
        for x in aa['Strengths']:st.write('• '+x)
    with r:
        st.markdown('#### Rủi ro / điểm yếu tương đối')
        for x in aa['Risks']:st.write('• '+x)
    st.markdown('#### Nhận định chéo')
    for x in aa['Interpretations']:st.write('• '+x)
    st.markdown('#### Trọng tâm thẩm định chuyên ngành')
    st.write(' • '.join(aa['Focus']))
    st.caption('Engine chỉ diễn giải dữ liệu và benchmark hiện có; không tự tạo dữ liệu còn thiếu và không thay thế judgment của chuyên viên.')
    try:
        cc=pd.read_csv(DATA/'vnstock_peer_crosscheck.csv');rr=cc[cc.Ticker.astype(str).str.upper().eq(selected)]
        if len(rr):
            st.markdown('#### Đối chiếu độc lập với benchmark Vnstock')
            st.dataframe(rr,hide_index=True,use_container_width=True)
    except Exception:pass

with tabs[2]:
    st.subheader('Phủ dữ liệu toàn thị trường')
    try:
        cov=pd.read_csv(DATA/'coverage_matrix.csv')
    except Exception:
        cov=build_coverage_matrix() if build_coverage_matrix else pd.DataFrame()
    if len(cov):
        a,b,c,d=st.columns(4)
        a.metric('Universe trong Master',f'{len(cov):,}'.replace(',', '.'))
        b.metric('Sẵn sàng phân tích',f"{int((cov.Readiness=='PRODUCTION_READY').sum()):,}".replace(',', '.'))
        c.metric('Phủ một phần',f"{int((cov.Readiness=='PARTIAL').sum()):,}".replace(',', '.'))
        d.metric('Thiếu dữ liệu',f"{int((cov.Readiness=='INSUFFICIENT_DATA').sum()):,}".replace(',', '.'))
        st.caption('Universe được phát hiện động từ Vnstock LOCAL. Coverage không đồng nghĩa mọi mã đều đủ dữ liệu để định giá hoặc XHTN.')
        q=cov.groupby(['EntityType','Readiness']).size().reset_index(name='Số doanh nghiệp')
        st.dataframe(q,hide_index=True,use_container_width=True)
        st.dataframe(cov,hide_index=True,use_container_width=True)
    else:
        st.info('Chạy RUN_FULL_MARKET_COVERAGE.bat trên máy LOCAL để phát hiện toàn bộ universe và tạo Coverage Matrix.')

with tabs[3]:
    st.subheader('Tổng quan')
    c1,c2,c3,c4=st.columns(4); c1.metric('Loại hình',meta.get('EntityType'));c2.metric('Ngành',meta.get('Sector'));c3.metric('Sàn',meta.get('Exchange'));c4.metric('Ngành so sánh',industry_name)
    if len(peer):
        st.markdown('### So sánh với trung bình ngành')
        ov,_,_=sector_kpi_table(selected)
        if len(ov):
            ov2=ov[ov['Doanh nghiệp'].notna() | ov['Trung bình ngành'].notna()].copy()
            st.dataframe(ov2[['Nhóm phân tích','Chỉ tiêu','Doanh nghiệp','Trung bình ngành','Trung vị ngành','Số DN có dữ liệu']].head(18),
                         hide_index=True,use_container_width=True)

with tabs[4]:
    st.subheader('Hồ sơ doanh nghiệp')
    st.write(f"**{meta.get('CompanyName')}** được hệ thống tự phân loại vào **{meta.get('Sector')}** từ dữ liệu ngành ICB của Vnstock. Loại hình: **{meta.get('EntityType')}**; benchmark: **{industry_name}**; phương pháp XHTN: **{meta.get('Methodology')}**.")
    st.caption(f"Nguồn phân ngành: {meta.get('IndustrySource','Master/Legacy')} · Cấp ICB sử dụng: {meta.get('IndustryLevelUsed','N/A')}")
    st.write(f"**Mẫu phân tích chuyên ngành:** {sector_template['label']} · **Định giá ưu tiên:** {', '.join(sector_template['valuation'])}")
    st.dataframe(pd.DataFrame([{'Mã':selected,'Tên doanh nghiệp':meta.get('CompanyName'),'Loại hình':meta.get('EntityType'),'Ngành':meta.get('Sector'),'Sàn':meta.get('Exchange'),'Nhóm so sánh':meta.get('PeerGroup'),'Phương pháp XHTN':meta.get('Methodology')}]),hide_index=True,use_container_width=True)

with tabs[5]:
    st.subheader('Phân tích tài chính')
    if meta['EntityType']=='BANK':
        metric_list=[('ROE','ROE',True),('ROA','ROA',True),('NIM','NIM',True),('CIR','CIR',True),('NPL','NPL',True),('CAR','CAR',True),('CASA','CASA',True),('LDR','LDR',True)]
    elif meta['EntityType']=='SECURITIES':
        metric_list=[('ROE','ROE',True),('ROA','ROA',True),('Revenue','Doanh thu',False),('AvailableCapitalRatio','Vốn khả dụng',True),('DebtEquity','Nợ/VCSH',False),('DebtEBITDA','Nợ/EBITDA',False),('CurrentRatio','Thanh khoản hiện hành',False),('MarginLoansEquity','Margin/VCSH',True)]
    else:
        metric_list=[('ROE','ROE',True),('ROA','ROA',True),('Revenue','Doanh thu',False),('NetMargin','Biên LN ròng',True),('DebtEquity','Nợ/VCSH',False),('DebtEBITDA','Nợ/EBITDA',False),('CFO_Debt','CFO/Nợ',True),('FOCF_Debt','FOCF/Nợ',True),('InterestCoverage','EBITDA/Lãi vay',False),('CurrentRatio','Thanh khoản hiện hành',False)]
    for i in range(0,len(metric_list),2):
        cc=st.columns(2)
        for j,item in enumerate(metric_list[i:i+2]):
            m,t,pctflag=item
            with cc[j]:st.plotly_chart(metric_chart(selected,m,f'{t} · so với trung bình ngành',pctflag),use_container_width=True)

with tabs[6]:
    st.subheader('Bộ chỉ tiêu chuyên ngành và trung bình ngành')
    skpi,_,_=sector_kpi_table(selected)
    if len(skpi):
        show=skpi.copy()
        for c in ['Doanh nghiệp','Trung bình ngành','Trung vị ngành','Chênh lệch với TB ngành']:
            if c in show: show[c]=pd.to_numeric(show[c],errors='coerce')
        st.dataframe(show,hide_index=True,use_container_width=True)
    st.caption('Trung bình ngành được tính động từ các doanh nghiệp cùng ngành có dữ liệu; số lượng mẫu được hiển thị riêng cho từng chỉ tiêu.')
    dq=methodology_readiness(selected)
    q1,q2,q3=st.columns(3)
    q1.metric('Độ phủ KPI trọng yếu',f"{dq['Coverage']*100:.0f}%")
    q2.metric('KPI có dữ liệu',f"{dq['Have']}/{dq['Required']}")
    q3.metric('Sẵn sàng methodology',dq['Status'])
    if dq['Missing']:
        st.info('KPI trọng yếu còn thiếu: '+', '.join(dq['Missing'])+'. Hệ thống giữ N/A và ưu tiên bổ sung từ Vnstock/BCTC/manual input có nguồn.')

    st.subheader('So sánh doanh nghiệp với ngành')
    if len(peer):
        q=peer.copy(); q['Doanh nghiệp']=q.Ticker.astype(str)
        cols_show=[c for c in ['Doanh nghiệp','ROE','ROA','PB','PE','DebtEquity','CurrentRatio','NPL','CAR','CASA'] if c in q.columns]
        st.dataframe(q[cols_show],hide_index=True,use_container_width=True)
    else:st.info('Chưa có dữ liệu ngành để so sánh.')

with tabs[7]:
    st.subheader('Định giá')
    a,b,c,d=st.columns(4); a.metric('Giá thị trường',money(val.get('Price')));b.metric('Giá trị tham chiếu',money(val.get('FairValue')));c.metric('Tiềm năng',pct(val.get('Upside')));d.metric('Phương pháp',val.get('PrimaryMethod','N/A'))
    st.caption('V8.0 Foundation chỉ xuất giá trị khi dữ liệu nền đủ điều kiện. Không dùng giả định hard-code để tạo giá trị khi thiếu BCTC/market multiples.')

with tabs[8]:
    st.subheader('M&A / Quyền kiểm soát')
    base=num(val.get('FairValue')) or num(s.get('Price'))
    c1,c2,c3=st.columns(3); premium=c1.slider('Thặng dư quyền kiểm soát',0.0,0.60,0.15,0.01); synergy=c2.slider('Giá trị cộng hưởng (% giá trị độc lập)',0.0,0.50,0.08,0.01); stake=c3.slider('Tỷ lệ mua',0.01,1.0,0.51,0.01)
    strategic=base*(1+premium+synergy) if base else None
    st.metric('Giá trị chiến lược tham chiếu/cp',money(strategic));st.caption('Control premium và synergy là biến kịch bản. Không mặc định đây là giá giao dịch thực tế.')

with tabs[9]:
    st.subheader('Tái cấu trúc')
    if meta['EntityType']=='BANK': st.write('Theo dõi tác động xử lý tài sản, bổ sung vốn, NPL, CAR và BVPS sau tái cấu trúc. Các biến đặc thù chỉ được nhập khi có dữ liệu của chính ngân hàng.')
    else: st.write('Mô phỏng giảm nợ, tăng vốn, bán tài sản, tái cơ cấu danh mục và tác động lên đòn bẩy, thanh khoản và giá trị vốn chủ sở hữu.')
    debt_cut=st.slider('Giảm nợ giả định',0,50,10,5); equity_raise=st.slider('Tăng vốn giả định',0,50,10,5); st.caption(f'Kịch bản: giảm nợ {debt_cut}% và tăng vốn {equity_raise}%.')

with tabs[10]:
    st.subheader('NHIỆM VỤ 2 – XẾP HẠNG TÍN NHIỆM')
    rr3=rate_three_methodologies(selected)
    st.markdown(f"**Phương pháp được tự động lựa chọn:** {rr3.get('MethodologyName','N/A')}")
    st.caption(rr3.get('Audit',''))
    r1,r2,r3=st.columns(3)
    r1.metric('Anchor',rr3.get('Anchor','N/A'))
    r2.metric('SACP / SCA',rr3.get('SACP',rr3.get('SCA','N/A')))
    r3.metric('ICR',rr3.get('ICR','N/A'))
    if rr3.get('Methodology')=='BANK':
        st.write('**BICRA:**',rr3.get('BICRA'),' · **Điều chỉnh nội sinh:**',rr3.get('InternalNotches'),'bậc')
        st.dataframe(pd.DataFrame([{'Yếu tố':k,'Đánh giá':v} for k,v in rr3.get('Factors',{}).items()]),hide_index=True,use_container_width=True)
    elif rr3.get('Methodology')=='SECURITIES':
        st.write('**BICRA tham chiếu:**',rr3.get('BICRAReference'),' → **điều chỉnh Anchor CTCK:** -2 bậc')
        st.dataframe(pd.DataFrame([{'Yếu tố':k,'Đánh giá':v} for k,v in rr3.get('Factors',{}).items()]),hide_index=True,use_container_width=True)
    elif rr3.get('Methodology')=='CORPORATE':
        st.dataframe(pd.DataFrame([{'Nhóm rủi ro':k,'Điểm 1–6':v} for k,v in rr3.get('RiskScores',{}).items()]),hide_index=True,use_container_width=True)
        st.warning('Điểm tự động của doanh nghiệp phi tài chính là sơ bộ khi chưa có đủ KCF định tính/trọng số ngành chính thức; app không dùng BICRA/notch của ngân hàng để thay thế methodology doanh nghiệp.')
    rc=committee_pack(selected)
    st.markdown('#### Waterfall trình Hội đồng XHTN')
    st.dataframe(pd.DataFrame(rc.get('Waterfall',[])),hide_index=True,use_container_width=True)
    with st.expander('Danh mục kiểm tra trước Hội đồng XHTN'):
        for item in rc.get('CommitteeChecklist',[]): st.write('✓ '+item)
    ev=rating_evidence(selected)
    st.markdown('#### Sổ bằng chứng XHTN & mức độ tin cậy')
    e1,e2,e3=st.columns(3)
    e1.metric('ICR mô phỏng',ev.get('ICR','N/A'))
    e2.metric('Độ tin cậy XHTN',ev.get('RatingConfidence','N/A'))
    e3.metric('Độ đầy đủ dữ liệu',f"{ev.get('DataQuality',{}).get('Coverage',0)*100:.0f}%")
    st.dataframe(pd.DataFrame(ev.get('EvidenceLedger',[])),hide_index=True,use_container_width=True)
    st.caption(ev.get('GovernanceRule',''))



    # Single source of truth for XHTN: the 3-methodology router.
    # The detailed methodology result shown above is also the object used by reports.
    rating=rr3
    st.session_state['rating_result']=rating
    with st.expander('Chi tiết kết quả máy tính / audit trail'):
        st.json(rating)

with tabs[11]:
    st.subheader('Kịch bản & Stress')
    if meta['EntityType']=='BANK': shock=st.slider('Shock NPL (điểm %)',0.0,5.0,1.0,.25);st.write(f'NPL hiện tại {pct(s.get("NPL"))}; stress cộng thêm {vi(shock,2)} điểm %.')
    else: rev=st.slider('Shock doanh thu',-50,20,-10,5); margin=st.slider('Shock biên lợi nhuận',-10,10,-2,1);st.write(f'Kịch bản doanh thu {rev:+d}% và biên lợi nhuận {margin:+d} điểm %.')

with tabs[12]:
    st.subheader('Báo cáo & Quản trị')
    st.caption('Bộ báo cáo kế thừa chuẩn trước và mở rộng Data Layer V8.14 được thiết kế ở mức khoảng 30 trang A4, tự co giãn theo dữ liệu thực tế.')
    report_kind=st.radio('Loại báo cáo',['Phân tích, Định giá & M&A','Báo cáo Xếp hạng tín nhiệm'],horizontal=True)
    rr=st.session_state.get('rating_result')
    if report_kind=='Báo cáo Xếp hạng tín nhiệm' and rr is None:
        rr=rate_three_methodologies(selected)
    c1,c2=st.columns(2)
    try:
        rt='rating' if report_kind=='Báo cáo Xếp hạng tín nhiệm' else 'analysis'; docx=generate_docx(selected,rt,rr); pdf=generate_pdf(selected,rt,rr)
        c1.download_button('Tải báo cáo Word',docx,file_name=f'{selected}_{"XHTN" if rt=="rating" else "Phan_tich_Dinh_gia_MA"}.docx',mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',use_container_width=True)
        c2.download_button('Tải báo cáo PDF',pdf,file_name=f'{selected}_{"XHTN" if rt=="rating" else "Phan_tich_Dinh_gia_MA"}.pdf',mime='application/pdf',use_container_width=True)
    except Exception as e:st.warning(f'Chưa tạo được báo cáo: {e}')
    with st.expander('Quản trị dữ liệu & methodology'):
        st.write('Nguồn dữ liệu: Vnstock Bronze chạy LOCAL; Streamlit chỉ đọc CSV đã push lên GitHub.')
        st.write('Corporate sector weights trong V8.0 Foundation là cấu trúc kỹ thuật chờ KCF/benchmark ngành được hiệu chỉnh; app gắn nhãn rõ và không coi đây là methodology chính thức nếu chưa được phê duyệt.')
        st.dataframe(u[['Ticker','CompanyName','EntityType','Sector','Exchange','PeerGroup','Methodology']],hide_index=True,use_container_width=True)
