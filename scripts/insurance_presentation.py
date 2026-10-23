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
    if len(p) and p.iloc[0].Status=='OK' and pd.notna(p.iloc[0].Value):return float(p.iloc[0].Value)
    return None


def has_evidence(pair):
    h=pair['History']
    return own_value(pair) is not None or (len(h)>0 and bool((h.Status.eq('OK')&h.Value.notna()).any()))


def metric_interpretation(pair,subtype):
    m=pair['Metric'];v=own_value(pair);group=subtype in ('GROUP','LIFE')
    notes={
        'GrossWrittenPremium':'Phí gốc thể hiện quy mô khai thác; tăng phí cần đi cùng kiểm soát bồi thường và chi phí. Chưa có mẫu số toàn thị trường nên chưa kết luận về thị phần.',
        'NetInsurancePremium':'Phí thuần phản ánh phần doanh thu bảo hiểm giữ lại theo BCTC. Đọc cùng phí gốc, cơ cấu tái bảo hiểm và biến động dự phòng; chênh lệch giữa hai khoản chưa đủ xác định khẩu vị rủi ro.',
        'Revenue':'Doanh thu cần được đối chiếu với lợi nhuận và biên ròng để phân biệt tăng quy mô với cải thiện hiệu quả. Cơ cấu hoạt động khác nhau làm hạn chế so sánh tuyệt đối.',
        'TotalAssets':'Tài sản lớn tạo quy mô tài chính nhưng không tự chứng minh sức mạnh tín dụng. Khả năng hấp thụ rủi ro còn phụ thuộc vốn, chất lượng tài sản và nghĩa vụ bảo hiểm.',
        'MarketSharePremium':'Thị phần cần tính trên toàn thị trường cùng loại hình, cùng kỳ. Quy mô mẫu cổ phiếu niêm yết không thay thế mẫu số toàn ngành.',
        'LargestProductShare':'Mức tập trung sản phẩm cao làm kết quả nhạy hơn với tổn thất hoặc cạnh tranh trong một nghiệp vụ; cần đọc cùng chất lượng tái bảo hiểm.',
        'NPAT':'Lợi nhuận sau thuế hỗ trợ tích lũy vốn khi được giữ lại. Cần tách đóng góp từ khai thác, đầu tư và các khoản không lặp lại trước khi dự báo khả năng sinh lời.',
        'ROE':'ROE phản ánh lợi nhuận trên vốn chủ sở hữu; cần đối chiếu ROA và tỷ trọng vốn để nhận diện ảnh hưởng của đòn bẩy. Tỷ số nguồn tại quý báo cáo không được coi là tỷ suất riêng ba tháng.',
        'ROA':'ROA phản ánh hiệu quả sử dụng tài sản; khác biệt về quy mô dự phòng và cơ cấu tài sản có thể tạo khoảng cách giữa các công ty. Tỷ số nguồn giữ nguyên cơ sở tính của nhà cung cấp.',
        'NetMargin':'Biên ròng cho biết phần lợi nhuận sau thuế trên doanh thu. Biên tốt chưa đồng nghĩa khai thác bảo hiểm hiệu quả nếu thu nhập đầu tư đóng góp lớn.',
        'LossRatio':'Tỷ lệ bồi thường phải được đọc qua nhiều năm để nhận diện chu kỳ tổn thất; mức thấp tại một quý có thể chịu ảnh hưởng thời điểm ghi nhận hoặc hoàn nhập dự phòng.',
        'ExpenseRatio':'Tỷ lệ chi phí cho thấy mức tiêu hao phí thuần cho khai thác và quản lý theo quy ước BCTC. Cần đọc cùng tỷ lệ bồi thường và tốc độ tăng phí.',
        'CombinedRatio':'Tỷ lệ kết hợp gộp bồi thường và chi phí theo cùng cơ sở thuần. Cần xác nhận tính nhất quán định nghĩa và độ bền qua chuỗi năm trước khi dùng cho thẩm định.',
        'UnderwritingProfit':('Khoản mục hoạt động bảo hiểm ở cấp hợp nhất chịu ảnh hưởng cơ cấu nhân thọ, phi nhân thọ và dự phòng. Không diễn giải số âm của tập đoàn thành lỗ khai thác phi nhân thọ.' if group else 'Lợi nhuận khai thác cần được đọc cùng tỷ lệ kết hợp và biến động dự phòng. Một quý cải thiện chưa chứng minh hiệu quả bền vững.'),
        'InvestmentIncome':'Thu nhập đầu tư hỗ trợ kết quả kinh doanh nhưng đi kèm rủi ro lãi suất, chất lượng tín dụng và biến động thị trường. Không đồng nhất thu nhập đầu tư với lợi nhuận đầu tư ròng.',
        'Equity':'Vốn chủ sở hữu là nguồn hấp thụ tổn thất kế toán. Tăng vốn có thể đến từ lợi nhuận giữ lại hoặc huy động mới; chưa đồng nghĩa đáp ứng vốn pháp định hay biên khả năng thanh toán.',
        'EquityAssets':'Tỷ trọng vốn trên tài sản thể hiện bộ đệm vốn kế toán. Cơ cấu dự phòng và mô hình kinh doanh khác nhau cần được xét trước khi kết luận vốn mạnh/yếu.',
        'PaidInCapital':'Vốn thực góp và thặng dư được tách khỏi tổng vốn chủ sở hữu. Khả năng đáp ứng vốn pháp định cần đối chiếu giấy phép và mức yêu cầu đúng pháp nhân.',
        'PaidInCapitalRequired':'Tỷ số này chỉ đánh giá một khía cạnh vốn pháp định; cần xét dự báo vốn, tăng trưởng kinh doanh và mức tối thiểu đúng giấy phép.',
        'InsuranceReserves':'Dự phòng tăng thể hiện nghĩa vụ bảo hiểm được ghi nhận, không tự chứng minh dự phòng đầy đủ. Cần cấu trúc kỳ hạn và đánh giá chất lượng trích lập.',
        'InsuranceReservesEquity':'Dự phòng so với vốn phản ánh quy mô nghĩa vụ kế toán tương đối với bộ đệm vốn. Không xem dự phòng là nợ vay; sự khác biệt nhân thọ/phi nhân thọ ảnh hưởng lớn đến tỷ số.',
        'ReservesPremium':'Tỷ số dự phòng/phí liên hệ quy mô dự phòng với hoạt động khai thác. Tại quý dùng phí 12 tháng để tránh so sánh số dư với riêng ba tháng; chưa thay thế đánh giá đầy đủ dự phòng.',
        'FXMismatchLiabilities':'Chênh lệch ngoại tệ chưa phòng vệ cần được đọc cùng đồng tiền bồi thường và tài sản đối ứng, không chỉ mức tuyệt đối.',
        'InvestmentLeverage':'Tỷ trọng tài sản đầu tư rủi ro cần được đối chiếu với chất lượng tín dụng, phòng vệ và vốn hấp thụ tổn thất.',
        'LargestSectorShare':'Tập trung danh mục có thể làm tổn thất đồng thời gia tăng; cần phân biệt tập trung ngành, tổ chức phát hành và các ngoại lệ theo phương pháp.',
        'DebtEquity':'Tỷ số chỉ bao gồm nợ vay, không gồm toàn bộ nợ phải trả hay dự phòng bảo hiểm. Nợ vay thấp chưa đủ kết luận thanh khoản an toàn nếu thiếu lịch bồi thường và đáo hạn.',
        'DebtDue24MEquity':'Nợ đáo hạn hai năm cần được đối chiếu với nguồn tiền sẵn có và khả năng tái cấp vốn; không dùng dư nợ tổng cộng thay thế lịch đáo hạn.',
        'InsuranceEBITDAInterest':'Khả năng trả lãi chỉ có ý nghĩa khi EBITDA và lãi vay được đối chiếu cùng kỳ. Không áp dụng công thức nợ/EBITDA của doanh nghiệp phi tài chính.',
        'StressedLiquidAssets':'Giá trị thanh khoản đã khấu trừ phải dựa trên cơ cấu tài sản đủ điều kiện, kỳ hạn và chất lượng tín dụng; tổng tài sản không phải nguồn thanh khoản tương đương.',
        'InsuranceContractObligations':'Nghĩa vụ hợp đồng bảo hiểm là mẫu số riêng của phép đo thanh khoản, không thay bằng toàn bộ nợ phải trả hoặc chỉ số dư dự phòng.',
        'InsuranceLiquidity':'Khả năng thanh khoản cần xét tài sản đủ điều kiện sau khấu trừ so với nghĩa vụ hợp đồng và tình huống căng thẳng.',
        'SolvencyRatio':'Biên khả năng thanh toán cần nguồn công bố đúng kỳ và đúng pháp nhân; tỷ trọng vốn kế toán không thay thế chỉ tiêu này.',
        'PB':'P/B phản ánh mức giá so với giá trị sổ sách tại kỳ nguồn. Chênh lệch định giá cần đọc cùng ROE và cơ cấu hoạt động; không trực tiếp quyết định bậc tín nhiệm.',
        'PE':'P/E phản ánh mức giá so với lợi nhuận theo cơ sở nguồn. Mức thấp không tự chứng minh cổ phiếu rẻ nếu lợi nhuận thiếu bền vững; không dùng để tự chấm XHTN.',
    }
    text=notes[m]
    if m=='CombinedRatio' and v is not None:
        text=('Tại quý so sánh, tỷ lệ '+('dưới' if v<1 else 'trên' if v>1 else 'bằng')+' 100%, '+
              ('cho thấy thặng dư' if v<1 else 'cho thấy thâm hụt' if v>1 else 'ở mức hòa vốn')+' khai thác theo quy ước đang dùng. ')+text
    return text


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
        (good if b.Value>a.Value else risks).append(txt)
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
        (good if better else risks).append(txt)
    if not good:good=['Chưa đủ bằng chứng để kết luận điểm mạnh tài chính; các chỉ tiêu có số được phân tích riêng ở phần nội dung.']
    cov=quantitative_coverage(ticker,pack)
    if 'SolvencyRatio' in cov['Missing']:risks.append('Thiếu biên khả năng thanh toán đúng kỳ; chưa kết luận mức an toàn vốn pháp định.')
    from scripts.financial_evidence import insurance_reporting_subtype
    if insurance_reporting_subtype(get_company(ticker))=='GROUP':risks.append('Số liệu hợp nhất có cơ cấu hoạt động khác nhau; đối chiếu nhóm Phi nhân thọ chỉ có giá trị tham khảo tài chính.')
    return dict(Facts=facts,Strengths=good[:3],Risks=risks[:4])


def pending_assessment_groups(result):
    """Một dòng mỗi nhóm hồ sơ; toàn bộ 43 rubric vẫn giữ trong phiếu nhập."""
    if result.get('RatingBlocker')=='SCOPE':return []
    rows=result.get('SubfactorEvidence',[]);out=[]
    for group in dict.fromkeys(r['Nhóm'] for r in rows):
        items=[r for r in rows if r['Nhóm']==group];done=sum(bool(r['Đủ bằng chứng']) for r in items)
        if done<len(items):out.append({'Nhóm hồ sơ':group,'Có bằng chứng':f'{done}/{len(items)}',
                                      'Cần bổ sung':'; '.join(r['Chỉ tiêu'] for r in items if not r['Đủ bằng chứng'])})
    return out
