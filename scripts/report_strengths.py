"""Đưa trọng tâm tài chính vào điểm mạnh/rủi ro, gắn số và chiều biến động."""
from scripts.report_evidence import finite, fmt, label

PRIORITIES = {
    'BANK':['EquityAssets','ROA','NPL','CASA','LoanLossCoverage','NIM','CAR'],
    'SECURITIES':['EquityAssetsCorp','ROA','DebtEquity','CashDebt','NetMargin','CFO_Debt'],
    'CORPORATE':['NetMargin','CFO_Debt','DebtEBITDA','ROA','EquityAssetsCorp','InterestCoverage','CashDebt'],
    'INSURANCE':['CombinedRatio','ROA','EquityAssets','SolvencyRatio','DebtEquity','CashAssets']}
LOWER = {'NPL','CombinedRatio','DebtEquity','DebtEBITDA'}
EFFECTS = {
    'EquityAssets':('Bộ đệm vốn kế toán hỗ trợ hấp thụ tổn thất.','Bộ đệm vốn kế toán cần được củng cố khi tài sản mở rộng.'),
    'EquityAssetsCorp':('Vốn tự có hỗ trợ khả năng chịu biến động kinh doanh.','Mức vốn hóa làm tăng sự phụ thuộc vào nguồn tài trợ bên ngoài.'),
    'ROA':('Hiệu quả tài sản hỗ trợ tích lũy vốn từ lợi nhuận.','Hiệu quả tài sản hạn chế tốc độ tích lũy vốn từ lợi nhuận.'),
    'NPL':('Chất lượng tín dụng tương đối hỗ trợ khả năng giữ lợi nhuận.','Nợ xấu tạo áp lực dự phòng và hấp thụ tổn thất.'),
    'CASA':('Cơ cấu tiền gửi hỗ trợ chi phí huy động.','Lợi thế tiền gửi chi phí thấp còn hạn chế.'),
    'LoanLossCoverage':('Dự phòng tạo nguồn hấp thụ tổn thất tín dụng.','Bộ đệm dự phòng làm lợi nhuận nhạy hơn với tổn thất tín dụng.'),
    'NIM':('Biên lãi hỗ trợ thu nhập trước chi phí và dự phòng.','Biên lãi làm hẹp nguồn thu để bù chi phí và dự phòng.'),
    'CAR':('Vốn an toàn hỗ trợ khả năng hấp thụ rủi ro và mở rộng hoạt động.','Dư địa vốn cần được giữ cùng nhịp tăng tài sản có rủi ro.'),
    'NetMargin':('Khả năng giữ lợi nhuận trên doanh thu là điểm hỗ trợ.','Khả năng giữ lợi nhuận trên doanh thu là điểm cần cải thiện.'),
    'CFO_Debt':('Tiền từ hoạt động hỗ trợ nghĩa vụ nợ.','Nguồn tiền hoạt động hạn chế khả năng tự trang trải nợ.'),
    'DebtEBITDA':('Gánh nợ tương đối với thu nhập hoạt động thấp hơn.','Nghĩa vụ nợ nhạy với sự suy giảm thu nhập hoạt động.'),
    'DebtEquity':('Đòn bẩy nợ vay tương đối thấp hỗ trợ linh hoạt tài chính.','Nhu cầu vay làm tăng sức ép đối với vốn chủ sở hữu.'),
    'CashDebt':('Tiền mặt tạo một phần bộ đệm cho nghĩa vụ vay.','Tiền mặt còn hạn chế so với nghĩa vụ vay.'),
    'InterestCoverage':('Thu nhập tạo mức bao phủ chi phí lãi thuận lợi hơn.','Biên an toàn trả lãi chịu sức ép.'),
    'CombinedRatio':('Hiệu quả khai thác hỗ trợ khả năng giữ lại lợi nhuận.','Hiệu quả khai thác tạo áp lực lên kết quả bảo hiểm.'),
    'SolvencyRatio':('Biên khả năng thanh toán hỗ trợ năng lực nhận rủi ro.','Dư địa khả năng thanh toán cần được củng cố.'),
    'CashAssets':('Tiền mặt hỗ trợ đáp ứng nhu cầu chi trả ngắn hạn.','Bộ đệm tiền mặt cần được đọc cùng nghĩa vụ bồi thường.')}


def summary_findings(pack):
    strengths, risks = [], []
    # Chi đầu tư có thể làm tiền sau đầu tư âm dù chỉ tiêu quý tốt hơn peer.
    # Giữ trọng tâm này trong điểm yếu, không để biến mất vì so sánh tương đối.
    if pack['Type'] == 'CORPORATE':
        cash = pack['Items'].get('CFO',{}).get('History')
        capex = pack['Items'].get('Capex',{}).get('History')
        if cash is not None and capex is not None:
            common = cash[['DisplayPeriod','Value']].merge(capex[['DisplayPeriod','Value']],on='DisplayPeriod',suffixes=('_cash','_capex')).dropna()
            if len(common):
                last = common.iloc[-1]
                after = last.Value_cash - abs(last.Value_capex)
                if after < 0:
                    risks.append(f'Năm {last.DisplayPeriod}, tiền từ hoạt động kinh doanh {fmt("CFO",last.Value_cash)}, trong khi chi đầu tư tài sản cố định {fmt("Capex",abs(last.Value_capex))}. Tiền sau chi đầu tư âm {fmt("CFO",abs(after))}; hoạt động chưa tự trang trải toàn bộ đầu tư, cần sử dụng nguồn tiền khác hoặc huy động thêm. Đây là áp lực tài trợ dù một số tỷ số quý thuận lợi hơn peer.')
    for metric in PRIORITIES[pack['Type']]:
        x = pack['Items'].get(metric, {})
        value, mean = x.get('Value'), x.get('PeerMean')
        history = x.get('History')
        h = history.dropna(subset=['Value']) if history is not None else []
        # Chỉ kết luận vị thế tương đối khi có bình quân cùng kỳ/cơ sở.
        if not finite(value) or not finite(mean): continue
        if fmt(metric,value) == fmt(metric,mean): continue
        good = value < mean if metric in LOWER else value > mean
        if metric not in LOWER and value < 0: good = False
        if metric == 'DebtEBITDA' and value < 0: good = False
        if metric == 'CombinedRatio' and value > 1: good = False
        text = f'{label(metric)}: {fmt(metric,value)} tại {pack["Period"]}, so với bình quân peer {fmt(metric,mean)}. '
        if metric == 'DebtEBITDA' and value < 0:
            text += 'Tỷ số âm không được xem là lợi thế đòn bẩy. '
        text += EFFECTS[metric][0 if good else 1]
        if metric == 'LoanLossCoverage' and value < 1:
            text += ' Tuy nhiên, dự phòng chưa bao phủ toàn bộ nợ xấu đã ghi nhận; mức thu hồi thực còn phụ thuộc tài sản bảo đảm và khả năng trả nợ của khách hàng.'
        if len(h) >= 2:
            # Không nối xu hướng qua thay đổi phạm vi hoặc khoảng trống năm.
            breaks = x.get('HistoryBreaks', [])
            a, b = h.iloc[-2], h.iloc[-1]
            try: adjacent = int(str(b.DisplayPeriod))-int(str(a.DisplayPeriod)) == 1
            except ValueError: adjacent = False
            split = history.index.get_loc(h.index[-1]) in breaks
            if adjacent and not split and a.Value != b.Value:
                direction = 'tăng' if b.Value > a.Value else 'giảm'
                text += f' Năm {b.DisplayPeriod}, chỉ tiêu {direction} từ {fmt(metric,a.Value)} năm {a.DisplayPeriod} lên {fmt(metric,b.Value)}.' if direction == 'tăng' else f' Năm {b.DisplayPeriod}, chỉ tiêu giảm từ {fmt(metric,a.Value)} năm {a.DisplayPeriod} xuống {fmt(metric,b.Value)}.'
                improving = b.Value < a.Value if metric in LOWER else b.Value > a.Value
                if good and not improving: text += ' Vị thế quý hiện tại thuận lợi nhưng xu hướng năm là điểm cần theo dõi.'
                elif not good and improving: text += ' Xu hướng năm có cải thiện, song chưa xóa hạn chế ở kỳ so sánh hiện tại.'
        (strengths if good else risks).append(text)
    return strengths[:3], risks[:3]
