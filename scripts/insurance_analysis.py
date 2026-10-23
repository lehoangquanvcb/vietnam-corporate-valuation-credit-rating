"""Một gói bằng chứng cho mỗi chỉ tiêu, dùng chung giao diện và Word."""
import numpy as np
import pandas as pd
from scripts.insurance_catalog import GROUPS, NOTES, DEFAULT_NOTE
from scripts.financial_evidence import latest_period, same_period_history, insurance_reporting_subtype
from scripts.universal_data import get_company
from scripts.insurance_peers import peer_universe, configured_peer_universe, quarter_peers, included_rows, scope_label, exclusion_text, POLICY_NOTE, SUBTYPE_LABELS
from scripts.financial_views import BASIS_LABELS
from scripts.insurance_presentation import format_metric as fmt
from scripts.methodology_kpi_engine import LABELS, PCT, MULT

BASIS_TEXT={'QUARTER':'quý riêng lẻ','FY':'cả năm','YTD':'lũy kế','TTM':'12 tháng','END_PERIOD':'cuối kỳ','REPORTED_RATIO':'tỷ số nguồn','DERIVED_QUARTER':'tỷ số tính từ quý riêng lẻ','DERIVED_FY':'tỷ số cả năm','DERIVED_YTD':'tỷ số lũy kế','DERIVED_TTM':'tỷ số 12 tháng','END_PERIOD / TTM':'số dư cuối quý trên phí 12 tháng'}

def _change(metric,a,b):
    delta=b-a
    if metric in PCT:text=f'{delta*100:+.2f} điểm phần trăm'
    elif metric in MULT:text=f'{delta:+.2f} lần'
    elif a<=0:text=f'{delta/1e9:+,.1f} tỷ đồng (nền không dương)'
    else:text=f'{delta/a*100:+.1f}%'
    return text.replace(',','\u0001').replace('.',',').replace('\u0001','.')

def metric_pair(ticker,metric,basis='FY',years=5,peers=None):
    target=latest_period(ticker,'INSURANCE')
    peers=peer_universe(ticker) if peers is None else peers
    h=same_period_history(ticker,'INSURANCE',basis,years,metrics=[metric])
    p=quarter_peers(ticker,metric,target,peers) if target else pd.DataFrame()
    hs=[];breaks=[]
    # Kiểm tra khả năng so sánh của chuỗi dự phòng; giữ nguyên giá trị nguồn.
    # Đây là cờ kiểm tra dữ liệu, không phải ngưỡng rủi ro tín nhiệm.
    if metric in ('InsuranceReserves','InsuranceReservesEquity','ReservesPremium'):
        for i in range(1,len(h)):
            c,d=h.iloc[i-1],h.iloc[i]
            if c.Status=='OK' and d.Status=='OK' and c.Value>0 and d.Value>0 and max(c.Value,d.Value)/min(c.Value,d.Value)>100:
                breaks.append(i)
    warnings=[f"Giá trị nguồn thay đổi hơn 100 lần giữa {h.iloc[i-1].DisplayPeriod} và {h.iloc[i].DisplayPeriod}; cần đối chiếu BCTC và phạm vi ghi nhận. Giữ nguyên số nguồn, không tính tăng trưởng qua điểm này." for i in breaks]
    valid=h[h.Status.eq('OK')&h.Value.notna()] if len(h) else h
    if len(valid):
        a,b=valid.iloc[0],valid.iloc[-1]
        hs.append(f"Chuỗi {BASIS_LABELS[basis].lower()}: có {len(valid)}/{len(h)} mốc. {a.DisplayPeriod}: {fmt(metric,a.Value,'OK')}; {b.DisplayPeriod}: {fmt(metric,b.Value,'OK')}.")
        if len(valid)>1:
            if not breaks:hs.append(f"Đầu–cuối chuỗi thay đổi {_change(metric,a.Value,b.Value)}.")
            else:hs.append('Chưa tính thay đổi toàn chuỗi do có điểm cần đối chiếu nguồn.')
            changes=[]
            for i in range(1,len(h)):
                c,d=h.iloc[i-1],h.iloc[i]
                if i not in breaks and c.Status=='OK' and d.Status=='OK' and pd.notna(c.Value) and pd.notna(d.Value):
                    changes.append(f"{d.DisplayPeriod}: {_change(metric,c.Value,d.Value)}")
            if changes:hs.append('Biến động từng năm so với năm liền trước: '+'; '.join(changes)+'.')
            if len(h)>=2 and not (h.iloc[-1].Status=='OK' and h.iloc[-2].Status=='OK'):
                hs.append('Thiếu mốc liền kề nên không tính tăng trưởng năm gần nhất.')
        if valid.iloc[-1].Period!=h.iloc[-1].Period:hs.append('Mốc cuối yêu cầu còn thiếu; số gần nhất nêu trên không thay thế mốc đó.')
    else:hs.append('Chưa có chuỗi lịch sử đủ nguồn cho chỉ tiêu này; các năm thiếu được giữ trống, không nội suy.')
    ps=[];mean=median=None;n=0;rank=None
    if len(p):
        own=p.iloc[0];others=p.iloc[1:]
        matched=included_rows(others)
        n=len(matched)
        ps.append(f"{target}: {ticker} {fmt(metric,own.Value,own.Status)} ({BASIS_TEXT.get(own.Basis,own.Basis) or 'chưa xác định'}).")
        if own.Status=='OK' and 0<n<5:
            ps.append('Đối chiếu trực tiếp: '+'; '.join(f"{row.Ticker} {fmt(metric,row.Value,'OK')}; chênh lệch của {ticker} {_change(metric,row.Value,own.Value)}" for row in matched.itertuples())+'.')
        if n>=5:
            mean=float(matched.Value.mean());median=float(matched.Value.median())
            ps.append(f"Bình quân {n} peer cùng kỳ/cơ sở {fmt(metric,mean,'OK')}; trung vị {fmt(metric,median,'OK')}.")
            if own.Status=='OK':ps.append(f"Chênh lệch với bình quân: {_change(metric,mean,own.Value)}.")
        elif n==0:ps.append('Chưa có peer đủ số liệu cùng kỳ và cơ sở để đối chiếu.')
        ps.append(f'Có {n}/{len(others)} peer được dùng; phạm vi: {scope_label(metric).lower()}.')
        if own.Status!='OK':ps.append(str(own.Reason))
    else:ps.append('Chưa tìm được quý tài chính có dữ liệu để so sánh.')
    label={'ROE':'Tỷ suất sinh lời trên vốn chủ sở hữu','ROA':'Tỷ suất sinh lời trên tổng tài sản'}.get(metric,LABELS.get(metric,metric))
    result=dict(Metric=metric,Label=label,History=h,Peers=p,
                HistoryText=' '.join(hs),PeerText=' '.join(ps),MethodNote=NOTES.get(metric,DEFAULT_NOTE),
                PeerMean=mean,PeerMedian=median,PeerCount=n,Period=target,Basis=basis,
                PeerCandidateCount=max(len(p)-1,0),PeerScope=scope_label(metric),
                PeerExclusions=exclusion_text(p),
                HistoryBreaks=breaks,HistoryWarnings=warnings)
    from scripts.insurance_narrative import metric_narrative
    from scripts.insurance_history import historical_peer_benchmark
    result.update(historical_peer_benchmark(ticker,metric,h,basis,peers))
    result.update(metric_narrative(result,subtype=insurance_reporting_subtype(get_company(ticker))))
    return result

def analysis_pack(ticker,basis='FY',years=5):
    peers=peer_universe(ticker);rows=[]
    for group,metrics in GROUPS.items():
        for metric in metrics:
            r=metric_pair(ticker,metric,basis,years,peers);r['Group']=group;rows.append(r)
    from scripts.insurance_narrative import enrich_pack
    return enrich_pack(rows,insurance_reporting_subtype(get_company(ticker)))

def quarter_kpi_table(ticker,include_missing=True):
    from scripts.financial_evidence import STATUS
    rows=[];peers=peer_universe(ticker);target=latest_period(ticker,'INSURANCE')
    for group,metrics in GROUPS.items():
        for m in metrics:
            p=quarter_peers(ticker,m,target,peers);e=p.iloc[0]
            z=included_rows(p.iloc[1:]);vals=z.Value
            if not include_missing and e.Status!='OK' and vals.empty:continue
            rows.append({'Nhóm phân tích':group,'Metric':m,'Chỉ tiêu':LABELS.get(m,m),'Doanh nghiệp':e.Value,
                         'TB ngành':vals.mean() if len(vals)>=5 else np.nan,'Trung vị':vals.median() if len(vals)>=5 else np.nan,
                         'Số DN':len(vals),'Số ứng viên':len(p)-1,'Phạm vi peer':scope_label(m),'Trạng thái dữ liệu':STATUS[e.Status],'StatusCode':e.Status,
                         'Kỳ dữ liệu':target,'Cơ sở':BASIS_TEXT.get(e.Basis,e.Basis),'Nguồn / Công thức':e.Source,
                         'Giải thích':e.Reason,'Trạng thái peer':(f'{len(vals)}/{len(p)-1} peer hợp lệ; '+scope_label(m)+'. '+exclusion_text(p))})
    return pd.DataFrame(rows)

def insurance_summary(ticker):
    from scripts.insurance_presentation import executive_findings,quantitative_coverage
    meta=get_company(ticker);pack=analysis_pack(ticker);findings=executive_findings(ticker,pack)
    cov=quantitative_coverage(ticker,pack)
    return {'Ticker':ticker,'CompanyName':meta.get('DisplayName'),'Sector':'Bảo hiểm','Template':'Bảo hiểm theo phương pháp 2025',
            'Focus':list(GROUPS),'Score':None,'View':'ĐỐI CHIẾU CHUYÊN NGÀNH',
            'Strengths':findings['Strengths'],'Risks':findings['Risks'],'Interpretations':findings['Narrative'],
            'Conclusion':' '.join(findings['Narrative'])+' '+cov['Note']}


def figures(pair):
    """Hai biểu đồ có cùng đơn vị; giữ khoảng trống tại mốc thiếu."""
    import plotly.graph_objects as go
    m=pair['Metric'];scale=100 if m in PCT else 1 if m in MULT else 1e-9
    unit='%' if m in PCT else 'lần' if m in MULT else 'tỷ đồng'
    h=pair['History'];p=pair['Peers'];ph=pair.get('PeerHistory',pd.DataFrame())
    a=go.Figure();b=go.Figure()
    if len(h):
        cuts=[0]+pair.get('HistoryBreaks',[])+[len(h)]
        for start,stop in zip(cuts,cuts[1:]):
            z=h.iloc[start:stop]
            a.add_scatter(x=z.DisplayPeriod,y=pd.to_numeric(z.Value,errors='coerce').where(z.Status.eq('OK'))*scale,mode='lines+markers',connectgaps=False,name='Doanh nghiệp',legendgroup='company',showlegend=start==0,line_color='#166b55')
    if len(ph):
        cuts=[0]+pair.get('PeerHistoryBreaks',[])+[len(ph)]
        for start,stop in zip(cuts,cuts[1:]):
            z=ph.iloc[start:stop]
            a.add_scatter(x=z.DisplayPeriod,y=z.PeerMean*scale,customdata=z.PeerCount,
                          mode='lines+markers',connectgaps=False,name='Bình quân peer',legendgroup='peers',showlegend=start==0,
                          line=dict(color='#C07820',dash='dash'),hovertemplate='%{x}: %{y:.2f}<br>N = %{customdata}<extra>Bình quân peer</extra>')
    if len(p):
        z=included_rows(p)
        if len(z):b.add_bar(x=z.Ticker,y=z.Value*scale,marker_color=['#166b55' if t==p.iloc[0].Ticker else '#8da6b9' for t in z.Ticker])
    for fig,title in [(a,'Chuỗi năm gần nhất'),(b,f"Doanh nghiệp và {pair['PeerCount']} peer · {pair['Period']}")]:
        fig.update_layout(title=title,height=310,margin=dict(t=50,l=60,r=15,b=65),yaxis_title=unit,showlegend=fig is a,
                          legend=dict(orientation='h',y=-.18,x=0))
    return a,b

def render_analysis(ticker,basis='FY',years=5,key='insurance'):
    import streamlit as st
    st.subheader('Phân tích bảo hiểm theo từng chỉ tiêu')
    meta=get_company(ticker)
    st.caption('Nguồn phương pháp: Saigon Ratings, 20.01.2025. '+str(meta.get('InsuranceScope','Chưa xác nhận loại hình'))+
               '. Lịch sử dùng cơ sở đã chọn; so sánh ngang dùng đúng quý gần nhất của doanh nghiệp. Dòng tiền quý riêng lẻ, số dư cuối quý; ROE/ROA/PB/PE giữ cơ sở tỷ số nguồn.')
    peers=peer_universe(ticker)
    st.caption(f'Nhóm so sánh ngành: {len(peers)+1} doanh nghiệp, gồm {ticker} và {len(peers)} peer: '+(', '.join(peers) or 'chưa có')+'.')
    configured=configured_peer_universe(ticker)
    st.caption('Nhóm so sánh nghiệp vụ: '+SUBTYPE_LABELS.get(meta.get('InsuranceSubtype'),'Chưa xác minh')+
               f'; {len(configured)} peer: '+(', '.join(configured) or 'chưa có')+'. Số peer thực dùng phụ thuộc dữ liệu đúng quý và cơ sở tính.')
    st.caption(POLICY_NOTE)
    with st.expander('Danh sách bảo hiểm và độ phủ dữ liệu quý gần nhất',expanded=False):
        audit=quarter_peers(ticker,'TotalAssets',latest_period(ticker,'INSURANCE'),peers)
        st.dataframe(pd.DataFrame([{'Mã':r.Ticker,'Nhóm so sánh':r.Model,'Phạm vi số liệu':r.ReportingScope,'Quý so sánh':r.Period,
            'Tổng tài sản':fmt('TotalAssets',r.Value,r.Status),
            'Đưa vào biểu đồ tài sản':'Có' if r.Included else 'Không','Lý do':r.ExclusionReason} for r in audit.itertuples()]),hide_index=True,use_container_width=True)
    from scripts.insurance_presentation import has_evidence,quantitative_coverage,executive_findings
    pack=analysis_pack(ticker,basis,years);coverage=quantitative_coverage(ticker,pack)
    st.caption(coverage['Note'])
    findings=executive_findings(ticker,pack)
    a,b=st.columns(2)
    with a:
        st.markdown('**Điểm mạnh từ số liệu**')
        for text in findings['Strengths']:st.write(text)
    with b:
        st.markdown('**Điểm hạn chế / rủi ro**')
        for text in findings['Risks']:st.write(text)
    from scripts.insurance_narrative import section_findings,overall_conclusion
    conclusions=section_findings(pack,insurance_reporting_subtype(meta))
    st.markdown('**Kết luận tổng hợp**')
    for text in overall_conclusion(pack,insurance_reporting_subtype(meta)):st.write(text)
    st.markdown('**Luận điểm phân tích**')
    for text in findings['Narrative']:st.write(text)
    from scripts.insurance_report import SECTIONS
    for heading,metrics in SECTIONS:
        with st.expander('Nhận định tổng hợp · '+heading,expanded=False):
            for title,text in conclusions[heading]:
                st.markdown('**'+title+'**');st.write(text)
    for pair in pack:
        if not has_evidence(pair):continue
        with st.expander(pair['Group']+' · '+pair['Label'],expanded=False):
            f1,f2=figures(pair)
            st.plotly_chart(f1,use_container_width=True,key=key+'hist_'+pair['Metric'])
            st.write(pair['NarrativeHistory'])
            st.caption(pair['PeerHistoryNote'])
            st.plotly_chart(f2,use_container_width=True,key=key+'peer_'+pair['Metric'])
            st.write(pair['NarrativePeer']);st.write(pair['AnalysisText'])
            st.markdown('**Kết luận:** '+pair['ConclusionText']);st.caption(pair['MethodNote'])
            if pair['PeerExclusions']:st.caption(pair['PeerExclusions'])
            for warning in pair.get('HistoryWarnings',[]):st.warning(warning)
            h=pair['History'];p=pair['Peers'];m=pair['Metric']
            if len(h):
                ph=pair['PeerHistory'].set_index('Period')
                st.dataframe(pd.DataFrame([{'Kỳ':r.DisplayPeriod,'Giá trị':fmt(m,r.Value,r.Status),'Bình quân peer':fmt(m,ph.loc[r.Period,'PeerMean'],'OK'),
                    'Số peer':int(ph.loc[r.Period,'PeerCount']),'Cơ sở':BASIS_TEXT.get(r.Basis,r.Basis),'Nguồn':r.Source,'Lưu ý':r.Reason} for r in h.itertuples()]),hide_index=True,use_container_width=True)
            with st.expander('Nguồn và thành phần peer từng năm',expanded=False):
                st.dataframe(pair['PeerHistoryEvidence'],hide_index=True,use_container_width=True)
            if len(p):
                st.dataframe(pd.DataFrame([{'Mã':r.Ticker,'Nhóm so sánh':r.Model,'Phạm vi số liệu':r.ReportingScope,'Kỳ':r.Period,'Giá trị':fmt(m,r.Value,r.Status),'Đưa vào so sánh':'Có' if r.Included else 'Không','Lý do loại':r.ExclusionReason,'Cơ sở':BASIS_TEXT.get(r.Basis,r.Basis),'Nguồn':r.Source,'Lưu ý':r.Reason} for r in p.itertuples()]),hide_index=True,use_container_width=True)
    with st.expander('Dữ liệu cần bổ sung và chỉ tiêu không áp dụng',expanded=False):
        from scripts.insurance_presentation import data_gap_explanation
        table=quarter_kpi_table(ticker)
        table['Giải thích']=[data_gap_explanation(r['Metric'],r['StatusCode'],r['Giải thích']) for r in table.to_dict('records')]
        st.dataframe(table[~table.StatusCode.eq('OK')][['Chỉ tiêu','Trạng thái dữ liệu','Kỳ dữ liệu','Giải thích']],hide_index=True,use_container_width=True)
