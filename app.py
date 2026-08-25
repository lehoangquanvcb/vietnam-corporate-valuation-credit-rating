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


def fmt_price(x):
    try:
        if x is None or pd.isna(x): return 'N/A'
        return f'{float(x)*1000:,.0f} đồng/cp'.replace(',', '.')
    except: return 'N/A'

def fmt_mult(x):
    try:
        if x is None or pd.isna(x): return 'N/A'
        return f'{float(x):.2f}x'.replace('.', ',')
    except: return 'N/A'

def fmt_pct(x):
    try:
        if x is None or pd.isna(x): return 'N/A'
        return f'{float(x)*100:.1f}%'.replace('.', ',')
    except: return 'N/A'

tabs=st.tabs([
    'Hồ sơ doanh nghiệp',
    'Phân tích, định giá & M&A',
    'Báo cáo Xếp hạng tín nhiệm',
    'Dữ liệu & Quản trị'
])



# =========================================================
# TAB 1 — HỒ SƠ DOANH NGHIỆP
# Gộp: Trung tâm phân tích + Phủ dữ liệu + Tổng quan + Hồ sơ DN
#      + Phân tích tài chính + So sánh tương quan
# =========================================================
with tabs[0]:
    st.subheader(f'Hồ sơ doanh nghiệp - {selected}')

    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric('Giá thị trường', fmt_price(s.get('Price') or s.get('Close')))
    c2.metric('P/B', fmt_mult(s.get('PB')))
    c3.metric('ROE', fmt_pct(s.get('ROE')))
    c4.metric('NPL', fmt_pct(s.get('NPL')) if meta.get('EntityType')=='BANK' else 'N/A')
    c5.metric('CAR', fmt_pct(s.get('CAR')) if meta.get('EntityType')=='BANK' else 'N/A')
    c6.metric('CASA', fmt_pct(s.get('CASA')) if meta.get('EntityType')=='BANK' else 'N/A')

    st.markdown('### Nhận diện & phạm vi phân tích')
    st.write(f"**{meta.get('CompanyName')}** · Loại hình: **{meta.get('EntityType')}** · Ngành: **{meta.get('Sector')}** · Sàn: **{meta.get('Exchange')}**")
    st.write(f"**Nhóm so sánh:** {industry_name}")
    st.write(f"**Phương pháp XHTN:** {meta.get('Methodology')}")
    st.caption(f"Nguồn phân ngành: {meta.get('IndustrySource','Master/Legacy')} · Cấp ICB: {meta.get('IndustryLevelUsed','N/A')} · Mẫu phân tích chuyên ngành: {sector_template.get('label','N/A')}")

    st.markdown('### Phủ dữ liệu')
    try:
        cov=pd.read_csv(DATA/'coverage_matrix.csv')
        rr=cov[cov.Ticker.astype(str).str.upper().eq(selected)]
        if len(rr):
            st.dataframe(rr,hide_index=True,use_container_width=True)
        else:
            st.info('Chưa có dòng coverage cho doanh nghiệp này.')
    except Exception:
        st.info('Chưa có coverage_matrix.csv. Có thể tạo lại bằng RUN_FULL_REFRESH.bat.')

    st.markdown('### Chỉ tiêu tài chính theo methodology')
    try:
        ov2,_,_=sector_kpi_table(selected)
        # Normalize column names across V8.12/V8.13 to avoid KeyError.
        rename_map={
            'Nhóm phân tích':'Nhóm phân tích',
            'Nhóm phân tích ':'Nhóm phân tích',
            'TB ngành':'Trung bình ngành',
            'Trung vị':'Trung vị ngành',
            'Số DN':'Số DN có dữ liệu'
        }
        ov2=ov2.rename(columns=rename_map)
        wanted=['Nhóm phân tích','Chỉ tiêu','Doanh nghiệp','Trung bình ngành','Trung vị ngành','Số DN có dữ liệu','Trạng thái dữ liệu']
        shown=[c for c in wanted if c in ov2.columns]
        st.dataframe(ov2[shown],hide_index=True,use_container_width=True)
    except Exception as e:
        st.warning(f'Chưa hiển thị được ma trận chỉ tiêu: {e}')

    st.markdown('### So sánh ngành & xu hướng')
    # Keep charts focused; one KPI per chart.
    metrics=['ROE','ROA']
    if meta.get('EntityType')=='BANK':
        metrics += ['NIM','NPL','CAR','CASA','LDR']
    elif meta.get('EntityType')=='SECURITIES':
        metrics += ['AvailableCapitalRatio','DebtEquity','CurrentRatio','PB','PE']
    else:
        metrics += ['DebtEquity','CurrentRatio','PB','PE']
    for mm in metrics:
        try:
            fig=metric_chart(selected,mm)
            if fig is not None:
                st.plotly_chart(fig,use_container_width=True)
        except Exception:
            pass

# =========================================================
# TAB 2 — PHÂN TÍCH, ĐỊNH GIÁ & M&A
# Gộp: Phân tích chuyên viên + Định giá + M&A/Quyền kiểm soát
#      + Tái cấu trúc + Kịch bản & Stress + xuất report phân tích
# =========================================================
with tabs[1]:
    st.subheader('Phân tích, định giá & M&A')

    aa=intelligent_analyze(selected)
    vt=triangulate(selected)
    fv=fair_value_range(selected)

    st.markdown('### Luận điểm phân tích')
    a1,a2,a3=st.columns(3)
    a1.metric('Quan điểm định lượng',aa.get('View','N/A'))
    a2.metric('Độ tin cậy phân tích',vt.get('AnalyticalConfidence','N/A'))
    a3.metric('Độ đầy đủ dữ liệu',f"{vt.get('DataQuality',{}).get('Coverage',0)*100:.0f}%")
    st.write(aa.get('Conclusion',''))
    for x in aa.get('Interpretations',[]): st.write('• '+x)

    st.markdown('### Định giá')
    b1,b2,b3,b4=st.columns(4)
    b1.metric('Bear',fmt_price(fv.get('Bear')))
    b2.metric('Base',fmt_price(fv.get('Base')))
    b3.metric('Bull',fmt_price(fv.get('Bull')))
    b4.metric('Chiến lược/M&A',fmt_price(fv.get('StrategicMA')))
    st.dataframe(pd.DataFrame(vt.get('Lenses',[])),hide_index=True,use_container_width=True)

    st.markdown('### M&A / Quyền kiểm soát / Tái cấu trúc')
    m1,m2,m3=st.columns(3)
    control=m1.slider('Thặng dư quyền kiểm soát',0.0,0.80,float(fv.get('ControlPremium',0.25)),0.05)
    synergy=m2.slider('Hệ số cộng hưởng chiến lược',0.0,0.80,float(fv.get('StrategicSynergy',0.10)),0.05)
    capital=m3.number_input('Vốn bổ sung giả định (tỷ đồng)',min_value=0.0,value=0.0,step=100.0)
    st.caption('Các giả định M&A là theo từng thương vụ; không áp dụng giả định riêng của STB cho doanh nghiệp khác.')

    st.markdown('### Kịch bản & Stress')
    st.write('Bear/Base/Bull được sử dụng như khung độ nhạy. Stress cần hiệu chỉnh theo ngành, chất lượng tài sản, đòn bẩy, thanh khoản và khả năng sinh lợi.')

    st.divider()
    st.markdown('### Xuất báo cáo Phân tích giá cổ phiếu – Định giá – M&A')
    try:
        docx_bytes=generate_docx(selected,'analysis')
        st.download_button('Tải báo cáo Word',docx_bytes,file_name=f'{selected}_Phan_tich_Dinh_gia_MA.docx',
                           mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',use_container_width=True)
        pdf_bytes=generate_pdf(selected,'analysis')
        st.download_button('Tải báo cáo PDF',pdf_bytes,file_name=f'{selected}_Phan_tich_Dinh_gia_MA.pdf',
                           mime='application/pdf',use_container_width=True)
    except Exception as e:
        st.warning(f'Chưa tạo được báo cáo phân tích: {e}')

# =========================================================
# TAB 3 — BÁO CÁO XẾP HẠNG TÍN NHIỆM
# Một tab riêng, không show JSON/code.
# =========================================================
with tabs[2]:
    st.subheader('Báo cáo Xếp hạng tín nhiệm')

    rr3=rate_three_methodologies(selected)
    rc=committee_pack(selected)
    ev=rating_evidence(selected)

    st.markdown(f"**Phương pháp áp dụng:** {rr3.get('MethodologyName','N/A')}")
    st.caption(rr3.get('Audit',''))

    r1,r2,r3,r4=st.columns(4)
    r1.metric('Anchor',rr3.get('Anchor','N/A'))
    r2.metric('SACP / SCA',rr3.get('SACP',rr3.get('SCA','N/A')))
    r3.metric('ICR mô phỏng',rr3.get('ICR','N/A'))
    r4.metric('Độ tin cậy XHTN',ev.get('RatingConfidence','N/A'))

    st.markdown('### Cấu phần đánh giá')
    if rr3.get('Methodology') in ('BANK','SECURITIES'):
        st.dataframe(pd.DataFrame([{'Cấu phần':k,'Đánh giá':v} for k,v in rr3.get('Factors',{}).items()]),
                     hide_index=True,use_container_width=True)
    elif rr3.get('Methodology')=='CORPORATE':
        st.dataframe(pd.DataFrame([{'Nhóm rủi ro':k,'Điểm 1–6':v} for k,v in rr3.get('RiskScores',{}).items()]),
                     hide_index=True,use_container_width=True)
        st.warning('Điểm tự động của doanh nghiệp phi tài chính là sơ bộ khi chưa có đủ KCF/trọng số ngành chính thức.')

    st.markdown('### Waterfall trình Hội đồng XHTN')
    st.dataframe(pd.DataFrame(rc.get('Waterfall',[])),hide_index=True,use_container_width=True)

    st.markdown('### Sổ bằng chứng XHTN')
    st.dataframe(pd.DataFrame(ev.get('EvidenceLedger',[])),hide_index=True,use_container_width=True)
    st.caption(ev.get('GovernanceRule',''))

    st.divider()
    st.markdown('### Xuất báo cáo Xếp hạng tín nhiệm')
    try:
        rating_docx=generate_docx(selected,'rating',rating_result=rr3)
        st.download_button('Tải báo cáo XHTN Word',rating_docx,file_name=f'{selected}_XHTN.docx',
                           mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',use_container_width=True)
        rating_pdf=generate_pdf(selected,'rating',rating_result=rr3)
        st.download_button('Tải báo cáo XHTN PDF',rating_pdf,file_name=f'{selected}_XHTN.pdf',
                           mime='application/pdf',use_container_width=True)
    except Exception as e:
        st.warning(f'Chưa tạo được báo cáo XHTN: {e}')

# =========================================================
# TAB 4 — DỮ LIỆU & QUẢN TRỊ
# Chỉ giữ các phần quản trị thực sự cần.
# =========================================================
with tabs[3]:
    st.subheader('Dữ liệu & Quản trị')

    st.markdown('### Trạng thái dữ liệu')
    try:
        cov=pd.read_csv(DATA/'coverage_matrix.csv')
        st.dataframe(cov,hide_index=True,use_container_width=True)
    except Exception:
        st.info('Chưa có coverage_matrix.csv.')

    st.markdown('### Universe & phân ngành')
    try:
        st.dataframe(U,hide_index=True,use_container_width=True)
    except Exception:
        pass

    st.markdown('### Ghi chú vận hành')
    st.caption('Vnstock chạy LOCAL → CSV/model outputs → GitHub → Streamlit Cloud chỉ đọc dữ liệu. Không chạy Vnstock Sponsor tại runtime trên Cloud.')
