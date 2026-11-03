"""Bố cục và luận điểm ngân hàng theo báo cáo TCB tham chiếu."""
from scripts.report_evidence import fmt,finite,vi,narrative

CHAPTERS=[
 ('HỒ SƠ KINH DOANH','Hồ sơ Kinh doanh',['TotalAssets','GrossLoans','CustomerDeposits']),
 ('VỐN VÀ LỢI NHUẬN','Vốn và Lợi nhuận',['Equity','CAR','EquityAssets','TangibleEquityAssets','AssetEquity','NPAT','NetInterestIncome','ROE','ROA','NIM','CIR','ProfitAssets','NII_OperatingIncome']),
 ('VỊ THẾ RỦI RO','Vị thế Rủi ro',['NPL','LoanLossCoverage','CreditCostProxy','ProvisionOperatingIncome','LoanAssets']),
 ('HUY ĐỘNG VỐN VÀ THANH KHOẢN','Huy động vốn và Thanh khoản',['CASA','LDR','DepositAssets','FundingGapAssets']),
 ('CHỈ TIÊU THỊ TRƯỜNG','',['PB','PE'])]


def chapter_findings(pack,key):
    items=pack['Items'];ticker=pack['Ticker'];out=[]
    def v(m):return items.get(m,{}).get('Value')
    def mean(m):return items.get(m,{}).get('PeerMean')
    def good(*ms):return all(finite(v(m)) for m in ms)
    def h(m):return items[m]['History'].dropna(subset=['Value'])
    def content(m):
        n=narrative(pack,m);return ' '.join(s for s in [n['Meaning'],n['Conclusion']] if s)
    if key=='Hồ sơ Kinh doanh':
        if good('TotalAssets','GrossLoans','CustomerDeposits'):
            out.append(f'{ticker} có tổng tài sản {fmt("TotalAssets",v("TotalAssets"))}, dư nợ {fmt("GrossLoans",v("GrossLoans"))} và tiền gửi khách hàng {fmt("CustomerDeposits",v("CustomerDeposits"))} tại {pack["Period"]}. Quy mô hoạt động được mở rộng trên cả phía tài sản và nguồn vốn, nhưng tốc độ của hai phía quyết định mức độ cân đối của tăng trưởng.')
        out.append(content('GrossLoans'))
        if good('NII_OperatingIncome','NIM'):
            out.append(f'Thu nhập lãi chiếm {fmt("NII_OperatingIncome",v("NII_OperatingIncome"))} thu nhập hoạt động trong quý. Với NIM {fmt("NIM",v("NIM"))}, năng lực bảo vệ chênh lệch lãi suất tiếp tục là yếu tố chi phối chất lượng tăng trưởng của {ticker}.')
    elif key=='Vốn và Lợi nhuận':
        if good('EquityAssets','AssetEquity') and finite(mean('EquityAssets')):
            out.append(f'Vốn chủ sở hữu bằng {fmt("EquityAssets",v("EquityAssets"))} tổng tài sản, so với bình quân peer {fmt("EquityAssets",mean("EquityAssets"))}. Đòn bẩy tài sản/vốn ở {fmt("AssetEquity",v("AssetEquity"))}. '+('Bộ đệm vốn kế toán dày hơn nhóm so sánh là một điểm hỗ trợ khả năng hấp thụ tổn thất.' if v('EquityAssets')>mean('EquityAssets') else 'Bộ đệm vốn kế toán thấp hơn nhóm so sánh làm tăng yêu cầu bổ sung vốn khi tài sản mở rộng.'))
        if good('ROE','ROA') and finite(mean('ROE')) and finite(mean('ROA')):
            text=f'ROE đạt {fmt("ROE",v("ROE"))} và ROA đạt {fmt("ROA",v("ROA"))}, trong khi peer lần lượt ở {fmt("ROE",mean("ROE"))} và {fmt("ROA",mean("ROA"))}. '
            if v('ROE')<mean('ROE') and v('ROA')>mean('ROA') and good('AssetEquity') and finite(mean('AssetEquity')) and v('AssetEquity')<mean('AssetEquity'):
                text+='ROE thấp hơn đi cùng ROA cao hơn và đòn bẩy thấp hơn; hiệu quả vốn cổ đông chưa phản ánh hết lợi thế tạo lợi nhuận trên tài sản và mức vốn hóa thận trọng hơn.'
            else:text+='Khả năng tích lũy vốn cần được đánh giá cùng tăng trưởng tài sản, thay vì chỉ dựa vào mức lợi nhuận tuyệt đối.'
            out.append(text)
        hn,hc=h('NIM'),h('CIR')
        if len(hn)>=2 and len(hc)>=2:
            n=hn.iloc[-1].Value-hn.iloc[-2].Value;c=hc.iloc[-1].Value-hc.iloc[-2].Value
            out.append(f'Năm {hn.iloc[-1].DisplayPeriod}, NIM ở {fmt("NIM",hn.iloc[-1].Value)}, CIR ở {fmt("CIR",hc.iloc[-1].Value)}. '+('Chi phí hoạt động được tiết giảm tương đối, bù một phần áp lực từ biên lãi thu hẹp.' if n<0 and c<0 else 'Biên lãi giảm đồng thời tỷ trọng chi phí tăng, làm hẹp phần thu nhập còn lại trước dự phòng.' if n<0 and c>0 else 'Diễn biến biên lãi và chi phí vận hành cùng quyết định khả năng giữ lại lợi nhuận để bổ sung vốn.'))
    elif key=='Vị thế Rủi ro':
        hn=h('NPL')
        if len(hn)>1:
            a,b=hn.iloc[0],hn.iloc[-1]
            out.append(f'Tỷ lệ nợ xấu từ {fmt("NPL",a.Value)} năm {a.DisplayPeriod} đến {fmt("NPL",b.Value)} năm {b.DisplayPeriod}. '+((f'NPL quý hiện tại {fmt("NPL",v("NPL"))} vẫn thấp hơn peer {fmt("NPL",mean("NPL"))}, nhưng mức tăng so với đầu chuỗi cho thấy chất lượng tín dụng chưa trở lại nền năm {a.DisplayPeriod}.' if good('NPL') and finite(mean('NPL')) and v('NPL')<mean('NPL') else 'Mức tăng so với đầu chuỗi cho thấy rủi ro tín dụng đã cao hơn nền lịch sử của ngân hàng.') if b.Value>a.Value else 'Mức nợ xấu cuối chuỗi thấp hơn đầu chuỗi là yếu tố hỗ trợ chất lượng tài sản.'))
        out.append(content('NPL'))
        if good('LoanAssets'):
            out.append(f'Cho vay chiếm {fmt("LoanAssets",v("LoanAssets"))} tài sản. Phần tài sản này khiến kết quả và vốn nhạy với tổn thất tín dụng; tăng trưởng dư nợ chỉ hỗ trợ hồ sơ rủi ro khi chất lượng khoản vay và dự phòng cùng được duy trì.')
    elif key=='Huy động vốn và Thanh khoản':
        if good('CASA') and finite(mean('CASA')):
            out.append(f'CASA {fmt("CASA",v("CASA"))} so với peer {fmt("CASA",mean("CASA"))} '+('tạo lợi thế nguồn vốn không kỳ hạn.' if v('CASA')>mean('CASA') else 'cho thấy lợi thế nguồn vốn không kỳ hạn thấp hơn nhóm so sánh.'))
        hc=h('CASA')
        if len(hc)>1:
            a,b=hc.iloc[0],hc.iloc[-1]
            out.append(f'Trong chuỗi năm, CASA từ {fmt("CASA",a.Value)} năm {a.DisplayPeriod} xuống {fmt("CASA",b.Value)} năm {b.DisplayPeriod}. Tỷ trọng nguồn vốn không kỳ hạn giảm làm mức tài trợ bằng tiền gửi có kỳ hạn lớn hơn tương đối.' if b.Value<a.Value else f'CASA tăng từ {fmt("CASA",a.Value)} lên {fmt("CASA",b.Value)} trong chuỗi năm, hỗ trợ cơ cấu chi phí vốn.')
        out.append(content('LDR'))
    return list(dict.fromkeys(s for s in out if s))


def rating_sensitivity(rr):
    """Độ nhạy theo thay đổi cấu phần, không tự đặt ngưỡng hạ bậc tài chính."""
    from scripts.three_methodology_rating import move,label
    if rr.get('ICR') in (None,'N/A',''):return []
    result=[];baseline=rr.get('RawICR',rr['ICR']) if rr.get('DomesticCalibrationApplied') else rr['ICR'];notches=rr.get('FactorNotches',{})
    for key,description in [('Vốn và Lợi nhuận','Vốn và lợi nhuận mất 1 bậc điều chỉnh'),('Vị thế Rủi ro','Vị thế rủi ro mất 1 bậc điều chỉnh'),('Huy động vốn và Thanh khoản','Huy động và thanh khoản mất 1 bậc điều chỉnh')]:
        if key in notches:result.append([description,'−1',label(move(baseline,-1))])
    result.append(['Hai cấu phần cùng mất 1 bậc điều chỉnh','−2',label(move(baseline,-2))])
    return result
