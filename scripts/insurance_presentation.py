"""Luận điểm và trạng thái chung cho màn hình và báo cáo bảo hiểm.

Nhận xét mô tả bằng chứng, không quy đổi KPI thành điểm định tính/XHTN.
"""
import pandas as pd
from scripts.financial_views import fmt as _fmt
from scripts.methodology_kpi_engine import LABELS
from scripts.universal_data import get_company


def format_metric(metric,value,status='MISSING',compact=False):
    return _fmt(metric,value,status,compact).replace(',','\u0001').replace('.',',').replace('\u0001','.')

fmt=format_metric


def data_gap_explanation(metric,status,reason):
    if status not in ('MISSING','UNREVIEWED'):return str(reason)
    return {
        'MarketSharePremium':'Cần phí gốc của doanh nghiệp và tổng phí toàn thị trường cùng loại hình, cùng kỳ.',
        'LargestProductShare':'Cần cơ cấu phí theo nghiệp vụ/sản phẩm đúng kỳ.',
        'PaidInCapitalRequired':'Cần mức vốn pháp định theo giấy phép của pháp nhân đang phân tích.',
        'FXMismatchLiabilities':'Cần tài sản, nghĩa vụ ngoại tệ và phần đã được phòng vệ.',
        'InvestmentLeverage':'Cần phân loại tài sản đầu tư theo rủi ro, sau phòng vệ.',
        'LargestSectorShare':'Cần cơ cấu danh mục đầu tư theo ngành và tổ chức phát hành.',
        'DebtDue24MEquity':'Cần lịch nợ vay đáo hạn trong 24 tháng.',
        'InsuranceEBITDAInterest':'Cần EBITDA đã đối chiếu và chi phí lãi vay cùng kỳ.',
        'StressedLiquidAssets':'Cần danh mục tiền, tiền gửi, trái phiếu và cổ phiếu; kỳ hạn và chất lượng tín dụng để áp mức khấu trừ.',
        'InsuranceContractObligations':'Cần tổng nghĩa vụ hợp đồng bảo hiểm theo hồ sơ thẩm định.',
        'InsuranceLiquidity':'Cần tài sản thanh khoản sau khấu trừ và tổng nghĩa vụ hợp đồng bảo hiểm.',
        'SolvencyRatio':'Cần biên khả năng thanh toán thực có và biên tối thiểu công bố đúng kỳ, đúng pháp nhân.',
    }.get(metric,str(reason))


def quantitative_coverage(ticker,pack=None):
    from scripts.insurance_analysis import quarter_kpi_table
    if pack is None:
        rows=quarter_kpi_table(ticker).to_dict('records')
        pairs=[(r['Metric'],r['StatusCode']) for r in rows]
    else:
        pairs=[(p['Metric'],p['Peers'].iloc[0].Status if len(p['Peers']) else 'MISSING') for p in pack]
    present=[m for m,s in pairs if s=='OK']
    na=[m for m,s in pairs if s=='NOT_APPLICABLE']
    missing=[m for m,s in pairs if s not in ('OK','NOT_APPLICABLE')]
    total=len(pairs);applicable=total-len(na)
    return dict(Ticker=ticker,EntityType='INSURANCE',Present=present,Missing=missing,NotApplicable=na,
                Total=total,ApplicableTotal=applicable,Coverage=len(present)/applicable if applicable else None,
                Confidence='Độ phủ số liệu, không phải độ tin cậy XHTN',
                Note=f'{len(present)}/{total} chỉ tiêu có số tại quý gần nhất; {len(missing)} cần bổ sung; {len(na)} không áp dụng. '
                     f'Độ phủ tính trên {applicable} chỉ tiêu áp dụng; không đo tiến độ thẩm định.')


def own_value(pair):
    p=pair['Peers']
    if len(p) and p.iloc[0].Status=='OK' and pd.notna(p.iloc[0].Value):
        import math
        v=float(p.iloc[0].Value)
        if math.isfinite(v):return v
    return None


def has_evidence(pair):
    h=pair['History']
    return own_value(pair) is not None or (len(h)>0 and bool((h.Status.eq('OK')&h.Value.notna()).any()))


def metric_interpretation(pair,subtype):
    from scripts.insurance_narrative import metric_narrative
    return metric_narrative(pair,subtype=subtype)['AnalysisText']


def executive_findings(ticker,pack):
    """Luận điểm tự động từ giá trị thực; không gán điểm/mức rủi ro giả."""
    pairs={p['Metric']:p for p in pack};good=[];risks=[];facts=[]
    for m in ['GrossWrittenPremium','NPAT','ROE','EquityAssets']:
        p=pairs[m];v=own_value(p)
        if v is not None:facts.append(f"{p['Label']}: {fmt(m,v,'OK')} ({p['Period']}).")
    for m in ['NPAT','ROE','Equity']:
        p=pairs[m];h=p['History']
        if len(h)<2 or not all(h.tail(2).Status.eq('OK')) or not h.tail(2).Value.notna().all():continue
        a,b=h.iloc[-2],h.iloc[-1]
        if b.Value==a.Value:continue
        txt=f"{p['Label']} {'tăng' if b.Value>a.Value else 'giảm'} từ {fmt(m,a.Value,'OK')} ({a.DisplayPeriod}) lên {fmt(m,b.Value,'OK')} ({b.DisplayPeriod})." if b.Value>a.Value else f"{p['Label']} giảm từ {fmt(m,a.Value,'OK')} ({a.DisplayPeriod}) xuống {fmt(m,b.Value,'OK')} ({b.DisplayPeriod})."
        # Tăng lỗ không được ghi nhận thành điểm mạnh; giảm lỗ chỉ là cải thiện.
        if b.Value<=0:
            txt+=' Mức cuối chuỗi chưa dương, chưa tạo bộ đệm tài chính tích cực.'
        else:
            txt+=(' Nguồn tích lũy từ lợi nhuận được cải thiện nếu được giữ lại.' if m=='NPAT' and b.Value>a.Value else
                  ' Bộ đệm vốn kế toán được mở rộng.' if m=='Equity' and b.Value>a.Value else
                  ' Hiệu quả sử dụng vốn có cải thiện.' if m=='ROE' and b.Value>a.Value else
                  ' Diễn biến này làm giảm mức hỗ trợ đối với hồ sơ tài chính so với năm trước.')
        (good if b.Value>a.Value and b.Value>0 else risks).append(txt)
    # Không để phục hồi năm cuối che khuất suy giảm trong cả chuỗi năm.
    for m in ['NPAT','EquityAssets','CombinedRatio']:
        p=pairs[m];h=p['History']
        if len(h)<3 or p.get('HistoryBreaks'):continue
        a,b=h.iloc[0],h.iloc[-1]
        if a.Status!='OK' or b.Status!='OK' or pd.isna(a.Value) or pd.isna(b.Value):continue
        adverse=b.Value>a.Value if m=='CombinedRatio' else b.Value<a.Value
        if not adverse:continue
        text=f"{p['Label']} từ {fmt(m,a.Value,'OK')} ({a.DisplayPeriod}) về {fmt(m,b.Value,'OK')} ({b.DisplayPeriod}). "
        text+=('Biên khai thác theo quy ước thu hẹp so với đầu chuỗi.' if m=='CombinedRatio' else
               'Bộ đệm vốn tương đối mỏng hơn đầu chuỗi.' if m=='EquityAssets' else
               'Lợi nhuận năm cuối chưa trở lại mức đầu chuỗi.')
        risks.append(text)
    for m in ['ROE','ROA','CombinedRatio']:
        p=pairs[m];v=own_value(p);q=p['Peers']
        if v is None or len(q)<2:continue
        z=q.iloc[1:];z=z[z.Included & z.SameModel]
        if len(z)==1:ref=float(z.iloc[0].Value);name=str(z.iloc[0].Ticker)
        elif len(z)>=5:ref=float(z.Value.mean());name=f'bình quân {len(z)} peer cùng loại hình'
        else:continue
        if abs(v-ref)<1e-9:continue
        better=v<ref if m=='CombinedRatio' else v>ref
        txt=f"{p['Label']} {fmt(m,v,'OK')}, {'thấp' if v<ref else 'cao'} hơn {name} {fmt(m,ref,'OK')} tại {p['Period']}."
        if m=='CombinedRatio' and v>1:
            txt+=' Tỷ lệ vẫn trên 100%, cho thấy thâm hụt khai thác theo quy ước BCTC.'
            risks.append(txt)
        elif m in ('ROE','ROA') and v<0:
            risks.append(txt+' Tỷ suất vẫn âm.')
        else:
            (good if better else risks).append(txt)
    if not good:good=['Chưa đủ bằng chứng để kết luận điểm mạnh tài chính; các chỉ tiêu có số được phân tích riêng ở phần nội dung.']
    cov=quantitative_coverage(ticker,pack)
    if 'SolvencyRatio' in cov['Missing']:risks.append('Thiếu biên khả năng thanh toán đúng kỳ; chưa kết luận mức an toàn vốn pháp định.')
    from scripts.financial_evidence import insurance_reporting_subtype
    if insurance_reporting_subtype(get_company(ticker))=='GROUP':risks.append('Số liệu hợp nhất có cơ cấu hoạt động khác nhau; đối chiếu nhóm Phi nhân thọ chỉ có giá trị tham khảo tài chính.')
    from scripts.insurance_narrative import executive_narrative
    subtype=insurance_reporting_subtype(get_company(ticker))
    # Giữ cảnh báo thiếu biên thanh toán trong bảng tóm tắt, không để bị cắt bởi các KPI.
    critical=[x for x in risks if x.startswith(('Thiếu biên','Số liệu hợp nhất'))]
    urgent=[x for x in risks if 'thâm hụt khai thác' in x]
    other=[x for x in risks if x not in critical and x not in urgent]
    return dict(Facts=facts,Strengths=good[:3],Risks=(urgent+other[:max(0,4-len(critical)-len(urgent))]+critical),
                Narrative=executive_narrative(pack,subtype))



def pending_assessment_groups(result):
    """Một dòng mỗi nhóm hồ sơ; toàn bộ 43 rubric vẫn giữ trong phiếu nhập."""
    if result.get('RatingBlocker')=='SCOPE':return []
    rows=result.get('SubfactorEvidence',[]);out=[]
    for group in dict.fromkeys(r['Nhóm'] for r in rows):
        items=[r for r in rows if r['Nhóm']==group];done=sum(bool(r['Đủ bằng chứng']) for r in items)
        if done<len(items):out.append({'Nhóm hồ sơ':group,'Có bằng chứng':f'{done}/{len(items)}',
                                      'Cần bổ sung':'; '.join(r['Chỉ tiêu'] for r in items if not r['Đủ bằng chứng'])})
    return out
