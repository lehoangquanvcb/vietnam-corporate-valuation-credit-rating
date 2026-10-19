"""Một gói bằng chứng cho mỗi chỉ tiêu, dùng chung giao diện và Word."""
import numpy as np
import pandas as pd
from scripts.insurance_catalog import GROUPS, NOTES, DEFAULT_NOTE
from scripts.financial_evidence import at_period, latest_period, same_period_history, comparable_model, _record
from scripts.universal_data import get_company, universe
from scripts.financial_views import fmt, BASIS_LABELS
from scripts.methodology_kpi_engine import LABELS, PCT, MULT

BASIS_TEXT={'QUARTER':'quý riêng lẻ','FY':'cả năm','YTD':'lũy kế','TTM':'12 tháng','END_PERIOD':'cuối kỳ','REPORTED_RATIO':'tỷ số nguồn','DERIVED_QUARTER':'tỷ số tính từ quý riêng lẻ','DERIVED_FY':'tỷ số cả năm','DERIVED_YTD':'tỷ số lũy kế','DERIVED_TTM':'tỷ số 12 tháng','END_PERIOD / TTM':'số dư cuối quý trên phí 12 tháng'}

def peer_universe(ticker):
    meta=get_company(ticker);u=universe()
    peers=[r for r in u.to_dict('records') if r['Ticker']!=ticker and comparable_model(meta,r)]
    # Tối đa 10 peer cùng mô hình; xếp theo quy mô tài sản ở chính quý so sánh.
    target=latest_period(ticker,'INSURANCE')
    def size(r):
        if not target:return 0
        v=at_period(r['Ticker'],'INSURANCE',target,'QUARTER').get('TotalAssets',{}).get('Value')
        return v if v is not None else -1
    return [r['Ticker'] for r in sorted(peers,key=size,reverse=True)[:10]]

def quarter_peers(ticker,metric,target,peers):
    rows=[]
    for t in [ticker]+peers:
        e=at_period(t,'INSURANCE',target,'QUARTER').get(metric,_record(metric,per=target))
        rows.append(dict(Ticker=t,Value=e['Value'],Status=e['Status'],Period=target,
                         Basis=e['Basis'],Source=e['Source'],Reason=e['Reason']))
    return pd.DataFrame(rows)

def _change(metric,a,b):
    delta=b-a
    if metric in PCT:return f'{delta*100:+.2f} điểm phần trăm'
    if metric in MULT:return f'{delta:+.2f} lần'
    if a<=0:return f'chênh lệch {delta/1e9:+,.1f} tỷ đồng; không tính tăng trưởng từ nền không dương'
    return f'{delta/a*100:+.1f}%'

def metric_pair(ticker,metric,basis='FY',years=5,peers=None):
    target=latest_period(ticker,'INSURANCE')
    peers=peer_universe(ticker) if peers is None else peers
    h=same_period_history(ticker,'INSURANCE',basis,years,metrics=[metric])
    p=quarter_peers(ticker,metric,target,peers) if target else pd.DataFrame()
    hs=[]
    valid=h[h.Status.eq('OK')&h.Value.notna()] if len(h) else h
    if len(valid):
        a,b=valid.iloc[0],valid.iloc[-1]
        hs.append(f"Chuỗi {BASIS_LABELS[basis].lower()}: có {len(valid)}/{len(h)} mốc. {a.DisplayPeriod}: {fmt(metric,a.Value,'OK')}; {b.DisplayPeriod}: {fmt(metric,b.Value,'OK')}.")
        if len(valid)>1:
            hs.append(f"Đầu–cuối chuỗi thay đổi {_change(metric,a.Value,b.Value)}.")
            if len(h)>=2 and h.iloc[-1].Status=='OK' and h.iloc[-2].Status=='OK':
                c,d=h.iloc[-2],h.iloc[-1]
                hs.append(f"Năm gần nhất so với năm liền trước: {_change(metric,c.Value,d.Value)}.")
            else:hs.append('Thiếu mốc liền kề nên không tính tăng trưởng năm gần nhất.')
        if valid.iloc[-1].Period!=h.iloc[-1].Period:hs.append('Mốc cuối yêu cầu còn thiếu; số gần nhất nêu trên không thay thế mốc đó.')
    else:hs.append('Chưa có chuỗi lịch sử đủ nguồn cho chỉ tiêu này; các năm thiếu được giữ trống, không nội suy.')
    ps=[];mean=median=None;n=0;rank=None
    if len(p):
        own=p.iloc[0];others=p.iloc[1:]
        matched=others[others.Status.eq('OK')&others.Value.notna()&others.Basis.eq(own.Basis)]
        n=len(matched)
        ps.append(f"Quý so sánh {target}: {ticker} {fmt(metric,own.Value,own.Status)}. Có {n}/{len(peers)} peer đủ dữ liệu cùng cơ sở ({BASIS_TEXT.get(own.Basis,own.Basis) or 'chưa xác định'}).")
        if own.Status=='OK' and n:
            same=np.isclose(matched.Value,own.Value,rtol=1e-9,atol=1e-12);lower=int(((matched.Value<own.Value)&~same).sum());equal=int(same.sum())
            ps.append(f"Giá trị cao hơn {lower}, bằng {equal}, thấp hơn {n-lower-equal} peer; đây là vị trí số học, chưa phải kết luận chất lượng tín dụng.")
        if n>=5:
            mean=float(matched.Value.mean());median=float(matched.Value.median())
            ps.append(f"Bình quân peer {fmt(metric,mean,'OK')}; trung vị {fmt(metric,median,'OK')}.")
            if own.Status=='OK':ps.append(f"Chênh lệch với bình quân: {_change(metric,mean,own.Value)}.")
        else:ps.append('Mẫu dưới 5 peer: chỉ trình bày từng công ty, không suy ra bình quân đại diện.')
        if own.Status!='OK':ps.append(str(own.Reason))
    else:ps.append('Chưa tìm được quý tài chính có dữ liệu để so sánh.')
    label={'ROE':'Tỷ suất sinh lời trên vốn chủ sở hữu','ROA':'Tỷ suất sinh lời trên tổng tài sản'}.get(metric,LABELS.get(metric,metric))
    return dict(Metric=metric,Label=label,History=h,Peers=p,
                HistoryText=' '.join(hs),PeerText=' '.join(ps),MethodNote=NOTES.get(metric,DEFAULT_NOTE),
                PeerMean=mean,PeerMedian=median,PeerCount=n,Period=target,Basis=basis)

def analysis_pack(ticker,basis='FY',years=5):
    peers=peer_universe(ticker);rows=[]
    for group,metrics in GROUPS.items():
        for metric in metrics:
            r=metric_pair(ticker,metric,basis,years,peers);r['Group']=group;rows.append(r)
    return rows

def quarter_kpi_table(ticker,include_missing=True):
    from scripts.financial_evidence import STATUS
    rows=[];peers=peer_universe(ticker);target=latest_period(ticker,'INSURANCE')
    for group,metrics in GROUPS.items():
        for m in metrics:
            p=quarter_peers(ticker,m,target,peers);e=p.iloc[0]
            z=p.iloc[1:];vals=z.loc[z.Status.eq('OK')&z.Value.notna()&z.Basis.eq(e.Basis),'Value']
            if not include_missing and e.Status!='OK' and vals.empty:continue
            rows.append({'Nhóm phân tích':group,'Metric':m,'Chỉ tiêu':LABELS.get(m,m),'Doanh nghiệp':e.Value,
                         'TB ngành':vals.mean() if len(vals)>=5 else np.nan,'Trung vị':vals.median() if len(vals)>=5 else np.nan,
                         'Số DN':len(vals),'Trạng thái dữ liệu':STATUS[e.Status],'StatusCode':e.Status,
                         'Kỳ dữ liệu':target,'Cơ sở':BASIS_TEXT.get(e.Basis,e.Basis),'Nguồn / Công thức':e.Source,
                         'Giải thích':e.Reason,'Trạng thái peer':'Đủ ≥5 peer cùng kỳ/cơ sở' if len(vals)>=5 else 'Mẫu nhỏ, không có bình quân đại diện'})
    return pd.DataFrame(rows)

def insurance_summary(ticker):
    meta=get_company(ticker);table=quarter_kpi_table(ticker);pos=[];risks=[]
    for m in ['ROE','ROA','NetMargin','CombinedRatio','LossRatio']:
        row=table[table.Metric.eq(m)].iloc[0];own=row['Doanh nghiệp'];mean=row['TB ngành']
        if pd.isna(own) or pd.isna(mean):continue
        gap=own-mean
        if abs(gap)<1e-6:continue
        lower_good=m in ['CombinedRatio','LossRatio']
        text=f"{LABELS.get(m,m)} {fmt(m,own,'OK')}, {'cao' if gap>0 else 'thấp'} hơn bình quân peer {abs(gap)*100:.2f} điểm phần trăm tại {row['Kỳ dữ liệu']} (N={row['Số DN']})."
        (pos if (gap<0 if lower_good else gap>0) else risks).append(text)
    return {'Ticker':ticker,'CompanyName':meta.get('DisplayName'),'Sector':'Bảo hiểm','Template':'Bảo hiểm theo phương pháp 2025',
            'Focus':list(GROUPS),'Score':None,'View':'ĐỐI CHIẾU CHUYÊN NGÀNH','Strengths':pos,'Risks':risks,
            'Interpretations':['Hiệu quả khai thác phải xem cùng vốn, thanh khoản, chất lượng tài sản và dự báo.'],
            'Conclusion':f"Có {table['Doanh nghiệp'].notna().sum()}/34 chỉ tiêu có số tại quý so sánh. Tỷ lệ bồi thường/kết hợp thấp hơn chỉ là tín hiệu hiệu quả theo quy ước BCTC; không cộng các KPI thành điểm XHTN hoặc mặc định quy mô lớn là tín hiệu tốt."}

def figures(pair):
    """Hai biểu đồ có cùng đơn vị; giữ khoảng trống tại mốc thiếu."""
    import plotly.graph_objects as go
    m=pair['Metric'];scale=100 if m in PCT else 1 if m in MULT else 1e-9
    unit='%' if m in PCT else 'lần' if m in MULT else 'tỷ đồng'
    h=pair['History'];p=pair['Peers']
    a=go.Figure();b=go.Figure()
    if len(h):a.add_scatter(x=h.DisplayPeriod,y=pd.to_numeric(h.Value,errors='coerce')*scale,mode='lines+markers',connectgaps=False,name='Doanh nghiệp',line_color='#166b55')
    if len(p):
        z=p[p.Status.eq('OK')&p.Value.notna()&p.Basis.eq(p.iloc[0].Basis)]
        if len(z):b.add_bar(x=z.Ticker,y=z.Value*scale,marker_color=['#166b55' if t==p.iloc[0].Ticker else '#8da6b9' for t in z.Ticker])
    for fig,title in [(a,'Chuỗi năm gần nhất'),(b,'Doanh nghiệp và peer · '+str(pair['Period']))]:
        fig.update_layout(title=title,height=265,margin=dict(t=45,l=45,r=10,b=45),yaxis_title=unit,showlegend=False)
    return a,b

def render_analysis(ticker,basis='FY',years=5,key='insurance'):
    import streamlit as st
    st.subheader('Phân tích bảo hiểm theo từng chỉ tiêu')
    meta=get_company(ticker)
    st.caption('Nguồn phương pháp: Saigon Ratings, 20.01.2025. '+str(meta.get('InsuranceScope','Chưa xác nhận loại hình'))+
               '. Lịch sử dùng cơ sở đã chọn; so sánh ngang dùng đúng quý gần nhất của doanh nghiệp. Dòng tiền quý riêng lẻ, số dư cuối quý; ROE/ROA/PB/PE giữ cơ sở tỷ số nguồn.')
    st.caption('Peer: '+(', '.join(peer_universe(ticker)) or 'chưa có công ty cùng mô hình')+'. Mẫu cổ phiếu hiện có không mặc nhiên đạt yêu cầu 60% toàn ngành của phương pháp.')
    for pair in analysis_pack(ticker,basis,years):
        with st.expander(pair['Group']+' · '+pair['Label'],expanded=False):
            a,b=st.columns(2)
            f1,f2=figures(pair)
            with a:st.plotly_chart(f1,use_container_width=True,key=key+'hist_'+pair['Metric'])
            with b:st.plotly_chart(f2,use_container_width=True,key=key+'peer_'+pair['Metric'])
            st.write(pair['HistoryText']);st.write(pair['PeerText']);st.caption(pair['MethodNote'])
            h=pair['History'];p=pair['Peers'];m=pair['Metric']
            if len(h):
                st.dataframe(pd.DataFrame([{'Kỳ':r.DisplayPeriod,'Giá trị':fmt(m,r.Value,r.Status),'Cơ sở':BASIS_TEXT.get(r.Basis,r.Basis),'Nguồn':r.Source,'Lưu ý':r.Reason} for r in h.itertuples()]),hide_index=True,use_container_width=True)
            if len(p):
                st.dataframe(pd.DataFrame([{'Mã':r.Ticker,'Kỳ':r.Period,'Giá trị':fmt(m,r.Value,r.Status),'Cơ sở':BASIS_TEXT.get(r.Basis,r.Basis),'Nguồn':r.Source,'Lưu ý':r.Reason} for r in p.itertuples()]),hide_index=True,use_container_width=True)
