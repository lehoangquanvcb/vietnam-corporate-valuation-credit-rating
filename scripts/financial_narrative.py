"""Nhận định từ chuỗi BCTC năm và so sánh quý; không thay bằng định nghĩa KPI."""
import pandas as pd


def analyse(pack, metric):
    from scripts.report_evidence import finite, fmt, vi, label, PCT, MULT, HIGHER, LOWER
    items=pack['Items']; ticker=pack['Ticker']; x=items[metric]
    def val(m): return items.get(m,{}).get('Value')
    def hist(m):
        h=items.get(m,{}).get('History',pd.DataFrame())
        return h[h.Value.notna()] if len(h) else h
    def last(m):
        h=hist(m);return float(h.iloc[-1].Value) if len(h) else None
    def change(m):
        h=items.get(m,{}).get('History',pd.DataFrame())
        if len(h)<2 or not all(finite(a) for a in h.Value.iloc[-2:]):return None
        a,b=map(float,h.Value.iloc[-2:]);return b/a-1 if a>0 else None
    def same_last(*ms):
        hs=[hist(m) for m in ms]
        return all(len(h) for h in hs) and len({str(h.iloc[-1].Period) for h in hs})==1
    def growth_pair(a,b,yes,no):
        ga,gb=change(a),change(b)
        if ga is None or gb is None or not same_last(a,b):return ''
        year=hist(a).iloc[-1].DisplayPeriod
        return (f'Năm {year}, {label(a).lower()} {"tăng" if ga>=0 else "giảm"} {vi(abs(ga)*100,1)}%, còn {label(b).lower()} {"tăng" if gb>=0 else "giảm"} {vi(abs(gb)*100,1)}%. '
                +(yes if ga>gb else no))
    h=hist(metric); v=x['Value']; mean=x['PeerMean']; history=''; reasoning=[]
    if len(h):
        a,b=h.iloc[0],h.iloc[-1]
        history=f'{label(metric)} năm {b.DisplayPeriod} đạt {fmt(metric,b.Value)}.'
        if len(h)>1:
            direction='tăng' if b.Value>a.Value else 'giảm' if b.Value<a.Value else 'giữ nguyên'
            history=f'Giai đoạn {a.DisplayPeriod}–{b.DisplayPeriod}, {label(metric).lower()} {direction} từ {fmt(metric,a.Value)} đến {fmt(metric,b.Value)}.'
            if metric not in PCT|MULT and a.Value>0 and b.Value>0:
                years=int(str(b.Period)[:4])-int(str(a.Period)[:4])
                if years>0:history+=f' Tốc độ tăng trưởng bình quân đạt {vi(((b.Value/a.Value)**(1/years)-1)*100,1)}%/năm.'
            raw=x['History']
            if len(raw)>1 and all(finite(z) for z in raw.Value.iloc[-2:]):
                c=raw.iloc[-2];d=b.Value-c.Value
                move='tăng' if d>0 else 'giảm' if d<0 else 'không đổi'
                magnitude=vi(abs(d)*100,2)+' điểm phần trăm' if metric in PCT else vi(abs(d),2)+' lần' if metric in MULT else vi(abs(d/c.Value)*100,1)+'%' if c.Value>0 else fmt(metric,abs(d))
                history+=f' Riêng năm {b.DisplayPeriod}, {move} {magnitude} so với năm {c.DisplayPeriod}.' if d else f' Năm {b.DisplayPeriod} không đổi so với năm {c.DisplayPeriod}.'
            peak=h.loc[h.Value.idxmax()]
            if metric in PCT and peak.Period not in (a.Period,b.Period) and peak.Value>b.Value:
                history+=f' Chỉ tiêu đã lùi từ đỉnh {fmt(metric,peak.Value)} năm {peak.DisplayPeriod}.'
    else:history=f'Phân tích {label(metric).lower()} tập trung vào kết quả kỳ gần nhất.'
    peers=''
    if finite(v):
        peers=f'Quý {pack["Period"][-1]}/{pack["Period"][:4]}, {ticker} ghi nhận {fmt(metric,v)}.'
        if finite(mean):
            rel='xấp xỉ' if fmt(metric,v)==fmt(metric,mean) else 'cao hơn' if v>mean else 'thấp hơn'
            gap=vi(abs(v-mean)*100,2)+' điểm phần trăm' if metric in PCT else vi(abs(v-mean),2)+' lần' if metric in MULT else vi(abs(v/mean-1)*100,1)+'%' if mean>0 else fmt(metric,abs(v-mean))
            peers+=f' Kết quả {rel} bình quân peer {fmt(metric,mean)}'+(f', chênh lệch {gap}.' if rel!='xấp xỉ' else '.')
    else:peers='Nhận định dưới đây sử dụng kết quả năm đã công bố.'
    if pack['Type']=='BANK':
        if metric in {'TotalAssets','Equity','EquityAssets','TangibleEquityAssets','AssetEquity'}:
            reasoning.append(growth_pair('TotalAssets','Equity','Tài sản tăng nhanh hơn vốn chủ sở hữu, làm mỏng bộ đệm vốn kế toán tương đối trong năm.','Vốn chủ sở hữu theo kịp quy mô tài sản, củng cố khả năng hấp thụ tổn thất.'))
            if same_last('Equity','TotalAssets') and last('TotalAssets')>0:
                reasoning.append(f'Vốn chủ sở hữu chiếm {vi(last("Equity")/last("TotalAssets")*100,2)}% tổng tài sản cuối năm {hist("Equity").iloc[-1].DisplayPeriod}.')
        if metric in {'GrossLoans','CustomerDeposits','LoanAssets','DepositAssets','LDR','FundingGapAssets','CASA'}:
            reasoning.append(growth_pair('GrossLoans','CustomerDeposits','Tín dụng mở rộng nhanh hơn huy động khách hàng, thu hẹp phần tiền gửi còn dư để tài trợ các tài sản khác.','Huy động khách hàng theo kịp tăng trưởng tín dụng, giảm áp lực tìm nguồn tài trợ bổ sung.'))
            if finite(val('GrossLoans')) and finite(val('CustomerDeposits')):
                gap=val('CustomerDeposits')-val('GrossLoans')
                reasoning.append(f'Tại quý gần nhất, tiền gửi khách hàng {"vượt" if gap>=0 else "thấp hơn"} dư nợ {fmt("CustomerDeposits",abs(gap))}; '+('phần dư huy động này hỗ trợ cân đối nguồn tài trợ tín dụng.' if gap>=0 else 'phần chênh lệch phải được tài trợ bằng vốn chủ sở hữu hoặc các nguồn vốn khác.'))
            if metric=='LoanAssets' and finite(val('NPL')):
                reasoning.append(f'Tỷ lệ nợ xấu hiện là {fmt("NPL",val("NPL"))}; tăng tỷ trọng tín dụng sẽ làm kết quả nhạy hơn với diễn biến chất lượng khoản vay.')
            if metric=='CASA' and finite(val('NIM')):
                reasoning.append(f'CASA hiện ở {fmt("CASA",v)}, nhưng NIM chỉ đạt {fmt("NIM",val("NIM"))}'+(f', so với {fmt("NIM",items["NIM"]["PeerMean"])} của peer.' if finite(items['NIM']['PeerMean']) else '.')+' Nguồn vốn không kỳ hạn chưa đủ để tạo ưu thế về biên lãi nếu NIM vẫn thấp hơn nhóm so sánh.' if finite(items.get('NIM',{}).get('PeerMean')) and val('NIM')<items['NIM']['PeerMean'] else f'NIM hiện đạt {fmt("NIM",val("NIM"))}; cần duy trì nguồn tiền gửi không kỳ hạn để bảo vệ biên thu nhập.')
        if metric in {'NPAT','ROE','ROA','ProfitAssets'}:
            reasoning.append(growth_pair('NPAT','Equity','Lợi nhuận tăng nhanh hơn vốn cuối kỳ, hỗ trợ cải thiện hiệu quả sử dụng vốn.','Lợi nhuận tăng chậm hơn vốn cuối kỳ; tăng trưởng quy mô chưa tạo mức tăng tương ứng về hiệu quả vốn.'))
            if same_last('NIM','CIR'):
                hn,hc=hist('NIM'),hist('CIR')
                if len(hn)>1 and len(hc)>1:
                    n=hn.iloc[-1].Value-hn.iloc[-2].Value;c=hc.iloc[-1].Value-hc.iloc[-2].Value
                    reasoning.append('NIM thu hẹp đồng thời CIR tăng trong năm cuối, tạo sức ép kép lên khả năng sinh lời trước dự phòng.' if n<0 and c>0 else 'Biến động biên lãi và chi phí vận hành cho thấy lợi nhuận phụ thuộc đồng thời vào quy mô tín dụng và hiệu quả hoạt động.')
        if metric in {'NetInterestIncome','NIM','NII_OperatingIncome'}:
            reasoning.append(growth_pair('NetInterestIncome','GrossLoans','Thu nhập lãi thuần tăng nhanh hơn dư nợ cuối kỳ, cho thấy khả năng tạo thu nhập đang theo kịp mở rộng tín dụng.','Thu nhập lãi thuần tăng chậm hơn dư nợ cuối kỳ; phần tăng quy mô chưa chuyển hóa tương ứng thành thu nhập lãi.'))
            hn=hist('NIM')
            if len(hn)>1 and hn.iloc[-1].Value<hn.iloc[-2].Value:
                reasoning.append(f'NIM giảm còn {fmt("NIM",hn.iloc[-1].Value)} năm {hn.iloc[-1].DisplayPeriod}; ngân hàng phải mở rộng tài sản sinh lãi hoặc tăng nguồn thu ngoài lãi để bù phần biên bị thu hẹp.')
            if metric=='NII_OperatingIncome' and finite(v):reasoning.append(f'Thu nhập lãi đóng góp {fmt(metric,v)} thu nhập hoạt động trong quý, nên áp lực NIM có ảnh hưởng trực tiếp đến phần thu nhập này.')
        if metric in {'NPL','LoanLossCoverage','CreditCostProxy','ProvisionOperatingIncome'}:
            if finite(val('NPL')) and finite(val('LoanLossCoverage')):
                reasoning.append(f'Nợ xấu {fmt("NPL",val("NPL"))} đi cùng bao phủ {fmt("LoanLossCoverage",val("LoanLossCoverage"))}. '+('Dự phòng lớn hơn số nợ xấu đã ghi nhận, tạo lớp đệm đối với tổn thất trên nhóm khoản vay này.' if val('LoanLossCoverage')>=1 else 'Dự phòng chưa bao phủ toàn bộ nợ xấu đã ghi nhận, làm khả năng thu hồi tài sản bảo đảm trở nên quan trọng hơn đối với tổn thất ròng.'))
            if same_last('NPL','GrossLoans') and len(hist('NPL'))>=2 and len(hist('GrossLoans'))>=2:
                n,l=hist('NPL'),hist('GrossLoans')
                if list(n.Period.iloc[-2:])==list(l.Period.iloc[-2:]):
                    before=n.iloc[-2].Value*l.iloc[-2].Value;after=n.iloc[-1].Value*l.iloc[-1].Value
                    if before>0:reasoning.append(f'Số nợ xấu ước tính từ tỷ lệ nguồn nhân dư nợ thay đổi {vi((after/before-1)*100,1)}% trong năm cuối; '+('tỷ lệ nợ xấu giảm đi cùng giảm số dư ước tính, cho thấy cải thiện không chỉ đến từ mẫu số tín dụng tăng.' if after<before and n.iloc[-1].Value<n.iloc[-2].Value else 'diễn biến số dư này cần được đặt cạnh tỷ lệ nợ xấu khi đánh giá áp lực tín dụng.'))
        if metric=='CIR':
            if finite(v):reasoning.append(f'Ngân hàng dùng khoảng {vi(v*100,2)} đồng chi phí hoạt động cho mỗi 100 đồng thu nhập trong quý. '+('Tỷ trọng chi phí cao hơn peer làm phần thu nhập còn lại trước dự phòng mỏng hơn tương đối.' if finite(mean) and v>mean else 'Tỷ trọng chi phí thấp hơn peer giúp giữ lại phần thu nhập lớn hơn trước dự phòng.' if finite(mean) and v<mean else 'Hiệu quả chi phí hiện tương đương nhóm so sánh.'))
            if finite(val('NIM')):reasoning.append(f'Với NIM {fmt("NIM",val("NIM"))}, kiểm soát chi phí là một điều kiện để bảo vệ lợi nhuận khi chênh lệch lãi suất chưa mở rộng.')
        if metric=='CAR' and len(h):reasoning.append(f'CAR năm {h.iloc[-1].DisplayPeriod} là {fmt(metric,h.iloc[-1].Value)}; đây là cơ sở đánh giá vị thế vốn tại năm đó, không phải CAR kỳ vọng cho kỳ xếp hạng hiện tại.')
    else:
        if metric in {'Revenue','NPAT','GrossProfit','GrossMargin','NetMargin','EBITDA','EBITDAMargin','OperatingProfit','OperatingProfitMargin','ROE','ROA','ProfitAssets'}:
            reasoning.append(growth_pair('NPAT','Revenue','Lợi nhuận tăng nhanh hơn doanh thu, phản ánh phần tăng quy mô chuyển hóa thành kết quả ròng tốt hơn.','Lợi nhuận chưa theo kịp doanh thu, cho thấy áp lực lên phần lợi nhuận giữ lại từ mỗi đồng doanh thu.'))
        if metric in {'TotalAssets','Equity','TangibleEquity','EquityAssets','EquityAssetsCorp','AssetEquity','ROE'}:
            reasoning.append(growth_pair('TotalAssets','Equity','Tài sản mở rộng nhanh hơn vốn chủ sở hữu; nhu cầu tài trợ ngoài vốn chủ tăng tương đối.','Vốn chủ sở hữu theo kịp tăng tài sản, hỗ trợ khả năng chịu tổn thất.'))
        if metric in {'Loans','MarginLoans','MarginLoansEquity','TradingAssets','FinancialAssets','FVTPL','AFS','HTM','LoansAssets'}:
            reasoning.append(growth_pair(metric,'Equity','Quy mô khoản mục tăng nhanh hơn vốn chủ sở hữu, làm tăng mức rủi ro tài sản trên một đồng vốn.','Vốn chủ sở hữu theo kịp quy mô khoản mục, hỗ trợ năng lực chịu biến động giá hoặc tổn thất tín dụng.'))
        if metric in {'CFO','CFO_Margin','CFO_Debt','NPAT','NetMargin','Capex','FOCF','FOCF_Debt','FOCFMargin'} and same_last('CFO','NPAT'):
            cf,profit=last('CFO'),last('NPAT')
            reasoning.append(f'Năm {hist("CFO").iloc[-1].DisplayPeriod}, dòng tiền kinh doanh đạt {fmt("CFO",cf)}, so với lợi nhuận {fmt("NPAT",profit)}. '+('Dòng tiền vượt lợi nhuận, hỗ trợ khả năng tài trợ hoạt động bằng tiền tạo ra trong năm.' if cf>=profit and cf>0 else 'Lợi nhuận chưa chuyển hóa tương ứng thành tiền, làm tăng nhu cầu tài trợ vốn lưu động.' if profit>0 else 'Kết quả này cho thấy áp lực đồng thời lên lợi nhuận và nguồn tiền hoạt động.'))
        if metric in {'TotalDebt','DebtEquity','DebtAssets','DebtEBITDA','NetDebtEBITDA','NetDebtEquity','CFO_Debt','FOCF_Debt','InterestCoverage','InterestExpense'}:
            reasoning.append(growth_pair('TotalDebt','Equity','Nợ vay tăng nhanh hơn vốn chủ sở hữu, làm tăng sự phụ thuộc vào nguồn tài trợ có nghĩa vụ thanh toán.','Vốn chủ sở hữu tăng ít nhất ngang nợ vay, giúp hạn chế gia tăng đòn bẩy.'))
            if finite(val('InterestCoverage')):reasoning.append(f'Khả năng trang trải lãi vay hiện là {fmt("InterestCoverage",val("InterestCoverage"))}; '+('thu nhập tính trong mô hình chưa đủ bù lãi vay.' if val('InterestCoverage')<1 else 'thu nhập tính trong mô hình vẫn vượt nghĩa vụ lãi vay.'))
        if metric in {'Cash','CashAssets','CashDebt','CurrentRatio','CurrentAssets','CurrentLiabilities','ClientDeposits','AvailableCapitalRatio'}:
            if finite(val('CurrentRatio')):reasoning.append(f'Tài sản ngắn hạn bằng {fmt("CurrentRatio",val("CurrentRatio"))} nợ ngắn hạn; '+('cơ cấu này tạo phần dư tài sản ngắn hạn so với nghĩa vụ ngắn hạn.' if val('CurrentRatio')>=1 else 'nghĩa vụ ngắn hạn vượt tài sản ngắn hạn, tăng áp lực thu tiền và tái cấp vốn.'))
            if finite(val('CFO')):reasoning.append(f'Dòng tiền kinh doanh quý gần nhất {fmt("CFO",val("CFO"))} '+('bổ sung nguồn tiền cho thanh toán.' if val('CFO')>0 else 'làm giảm nguồn tiền sẵn có cho thanh toán.'))
    if metric in {'PB','PE','EV_EBITDA'} and finite(v) and finite(mean):
        if mean>0:
            premium=v/mean-1
            reasoning.append(f'{ticker} đang giao dịch với hệ số {label(metric)} {"cao hơn" if premium>=0 else "thấp hơn"} bình quân peer {vi(abs(premium)*100,1)}%.')
            if metric=='PB' and finite(val('ROE')) and finite(items.get('ROE',{}).get('PeerMean')):
                roe,benchmark=val('ROE'),items['ROE']['PeerMean']
                reasoning.append(f'ROE hiện là {fmt("ROE",roe)}, so với {fmt("ROE",benchmark)} của peer. '+('Mức định giá cao hơn chưa được giải thích bằng ưu thế rõ rệt về ROE ở kỳ này; khả năng duy trì lợi nhuận và chất lượng tài sản là những yếu tố cần làm rõ để bảo vệ phần chênh lệch giá.' if premium>0 and roe<=benchmark+.001 else 'Chênh lệch định giá cần được xem cùng hiệu quả vốn này và mức ổn định lợi nhuận trong chuỗi năm.'))
            elif metric=='PE' and change('NPAT') is not None:
                growth=change('NPAT')
                reasoning.append(f'Lợi nhuận năm cuối {"tăng" if growth>=0 else "giảm"} {vi(abs(growth)*100,1)}%. '+('Hệ số cao hơn peer khiến giá cổ phiếu nhạy hơn với việc tăng trưởng lợi nhuận không đạt kỳ vọng.' if premium>0 else 'Hệ số thấp hơn peer tạo mức giá tương đối thấp hơn trên lợi nhuận đã ghi nhận; mức chiết khấu cần đặt cạnh xu hướng lợi nhuận này.'))
    if not reasoning and metric in {'AssetTurnover','WorkingCapitalAssets','CapexRevenue'}:
        if metric=='AssetTurnover':reasoning.append(growth_pair('Revenue','TotalAssets','Doanh thu tăng nhanh hơn tài sản cuối kỳ, phù hợp với cải thiện mức khai thác tài sản.','Tài sản tăng nhanh hơn doanh thu, cho thấy phần tài sản mở rộng chưa tạo doanh thu tương ứng.'))
        elif metric=='WorkingCapitalAssets' and finite(v):reasoning.append(f'Vốn lưu động ròng chiếm {fmt(metric,v)} tài sản; '+('phần chênh lệch dương tạo bộ đệm tài sản ngắn hạn sau khi trừ nợ ngắn hạn.' if v>=0 else 'phần chênh lệch âm cho thấy tài trợ ngắn hạn đã vượt quy mô tài sản ngắn hạn.'))
        elif metric=='CapexRevenue' and same_last('Capex','CFO'):
            reasoning.append(f'Chi đầu tư năm cuối {fmt("Capex",abs(last("Capex")))} so với tiền kinh doanh {fmt("CFO",last("CFO"))}; '+('hoạt động kinh doanh tạo đủ tiền bù khoản chi đầu tư này.' if last('CFO')>=abs(last('Capex')) else 'chi đầu tư chưa được bù hoàn toàn bằng tiền từ hoạt động kinh doanh.'))
    reasoning=[s for s in reasoning if s]
    good=None
    if finite(v) and finite(mean) and metric in HIGHER|LOWER and fmt(metric,v)!=fmt(metric,mean):good=v>mean if metric in HIGHER else v<mean
    if good is not None:
        outcome={
            'NPL':('Chất lượng tín dụng hiện là điểm hỗ trợ so với peer.','Áp lực nợ xấu cao hơn peer là điểm hạn chế của hồ sơ rủi ro.'),
            'LoanLossCoverage':('Lớp đệm dự phòng là lợi thế tương đối của ngân hàng.','Lớp đệm dự phòng yếu hơn peer làm tăng độ nhạy của lợi nhuận với tổn thất mới.'),
            'NIM':('Biên lãi tạo lợi thế về khả năng sinh lời từ tài sản sinh lãi.','Biên lãi thấp hơn peer là điểm hạn chế của năng lực tạo lợi nhuận.'),
            'CASA':('Nguồn tiền gửi không kỳ hạn tạo lợi thế tài trợ tương đối.','Tỷ trọng tiền gửi không kỳ hạn thấp hơn peer hạn chế lợi thế chi phí vốn.'),
            'CIR':('Hiệu quả vận hành hỗ trợ phần thu nhập dành cho dự phòng và bổ sung vốn.','Hiệu quả chi phí thấp hơn peer làm giảm biên thu nhập trước dự phòng.'),
        }.get(metric,('Vị thế hiện tại thuận lợi hơn peer về '+label(metric).lower()+'.','Vị thế hiện tại bất lợi hơn peer về '+label(metric).lower()+'.'))
        conclusion=outcome[0 if good else 1]
    elif reasoning:conclusion=reasoning[-1];reasoning=reasoning[:-1]
    elif len(h)>1:
        conclusion=f'{ticker} kết thúc giai đoạn với {label(metric).lower()} {"cao hơn" if h.iloc[-1].Value>h.iloc[0].Value else "thấp hơn" if h.iloc[-1].Value<h.iloc[0].Value else "bằng"} năm đầu.'
    else:conclusion=f'{label(metric)} hiện ở {fmt(metric,v)}.' if finite(v) else 'Chưa kết luận về chỉ tiêu này.'
    return {'History':history,'Peers':peers,'Meaning':' '.join(reasoning),'Conclusion':conclusion}


def conclusions(pack):
    """Luận điểm xuyên suốt, tránh diễn giải từng khái niệm trong tóm tắt."""
    metrics=['GrossLoans','Equity','NPAT','NPL','NIM'] if pack['Type']=='BANK' else ['Revenue','NPAT','TotalAssets','CFO','TotalDebt']
    result=[]
    for m in metrics:
        if m in pack['Items']:
            n=analyse(pack,m)
            text=' '.join(s for s in [n['Meaning'],n['Conclusion']] if s)
            if text and text not in result:result.append(text)
    return result
