"""Nhận định theo diễn biến tài chính; không biến mô tả phương pháp thành phân tích."""
import pandas as pd


def enrich_narrative(pack, metric, result):
    from scripts.report_evidence import finite, fmt, vi, label, PCT, MULT
    items=pack['Items'];x=items[metric];typ=pack['Type'];v=x['Value'];mean=x['PeerMean']
    result=dict(result)
    def current(m):return items.get(m,{}).get('Value')
    def annual(m):
        h=items.get(m,{}).get('History',pd.DataFrame())
        return h[h.Value.notna()] if len(h) else h
    def changes(m):
        raw=items.get(m,{}).get('History',pd.DataFrame())
        if len(raw)<2 or not raw.Value.iloc[-2:].notna().all():return None
        a,b=raw.iloc[-2: ].itertuples(index=False)
        if a.Basis!=b.Basis or int(str(b.Period)[:4])-int(str(a.Period)[:4])!=1:return None
        return a,b
    def paired(a,b):
        aa,bb=changes(a),changes(b)
        if aa and bb and aa[1].Period==bb[1].Period:return aa,bb
        return None
    def point(m):
        h=annual(m)
        return h.iloc[-1] if len(h) else None
    def margin_link(m='NetMargin'):
        c=changes(m)
        if not c:return ''
        a,b=c;direction='tăng' if b.Value>a.Value else 'giảm' if b.Value<a.Value else 'không đổi'
        return (f'Biên lợi nhuận năm {b.DisplayPeriod} {direction} '
                f'{vi(abs(b.Value-a.Value)*100,2)} điểm phần trăm, đạt {fmt(m,b.Value)}; '
                +('phần lợi nhuận giữ lại từ doanh thu đã cải thiện.' if b.Value>a.Value else
                  'khả năng chuyển doanh thu thành lợi nhuận suy yếu trong năm cuối.' if b.Value<a.Value else
                  'tăng trưởng lợi nhuận phụ thuộc chủ yếu vào mở rộng doanh thu khi biên không đổi.'))
    # Diễn biến tương quan theo năm, tránh chỉ so với bình quân quý ở biểu đồ dưới.
    h=x['History'];valid=h[h.Value.notna() & h.PeerMean.notna()] if len(h) else h
    if len(valid) and not x.get('HistoryBreaks'):
        b=valid.iloc[-1];rel='cao hơn' if b.Value>b.PeerMean else 'thấp hơn' if b.Value<b.PeerMean else 'bằng'
        text=f'Năm {b.DisplayPeriod}, doanh nghiệp {rel} bình quân peer {fmt(metric,b.PeerMean)}.'
        if len(valid)>1 and not x.get('PeerHistoryBreaks'):
            a=valid.iloc[0]
            if metric in PCT|MULT:
                k=100 if metric in PCT else 1;u='điểm phần trăm' if metric in PCT else 'lần'
                text+=f' Chênh lệch với bình quân từng năm từ {vi((a.Value-a.PeerMean)*k,2)} {u} lên {vi((b.Value-b.PeerMean)*k,2)} {u}.'
            elif min(a.Value,a.PeerMean,b.Value,b.PeerMean)>0:
                text+=f' Quy mô tương đối từ {vi(a.Value/a.PeerMean,2)} lên {vi(b.Value/b.PeerMean,2)} lần bình quân.'
        result['History']+=' '+text

    extra=[]
    if typ=='INSURANCE':
        if metric in {'PB','PE'}:return result
        # Các nhận định bảo hiểm dùng cùng phạm vi và cùng kỳ với bộ bằng chứng.
        pair=x['InsurancePair']
        if x.get('HistoryBreaks'):
            hh=annual(metric)
            if len(hh):result['History']=f'Năm {hh.iloc[-1].DisplayPeriod}, {label(metric)} đạt {fmt(metric,hh.iloc[-1].Value)}.'
        if metric in {'LossRatio','ExpenseRatio','CombinedRatio','GrossWrittenPremium','NetInsurancePremium'}:
            c=paired('LossRatio','ExpenseRatio')
            if c:
                (l0,l1),(e0,e1)=c
                dl,de=(l1.Value-l0.Value)*100,(e1.Value-e0.Value)*100
                extra.append(f'Năm {l1.DisplayPeriod}, bồi thường thay đổi {vi(dl,2)} điểm phần trăm và chi phí khai thác thay đổi {vi(de,2)} điểm phần trăm. '+
                    ('Hai khoản cùng giảm, cải thiện phần thặng dư từ nghiệp vụ bảo hiểm.' if dl<=0 and de<=0 else
                     'Hai khoản cùng tăng, thu hẹp phần phí còn lại sau bồi thường và chi phí.' if dl>=0 and de>=0 else
                     'Hai cấu phần bù trừ nhau; '+('bồi thường' if abs(dl)>abs(de) else 'chi phí khai thác')+' quyết định phần lớn biến động ròng.'))
            cr=current('CombinedRatio')
            if finite(cr):extra.append(f'Tỷ lệ kết hợp quý gần nhất {fmt("CombinedRatio",cr)} '+
                ('để lại khoảng '+vi((1-cr)*100,2)+' đồng trên mỗi 100 đồng phí thuần sau bồi thường và chi phí khai thác.' if cr<1 else
                 'cho thấy bồi thường và chi phí vượt phí thuần '+vi((cr-1)*100,2)+' đồng trên mỗi 100 đồng phí; tăng doanh số chưa đủ để cải thiện kết quả nếu cơ cấu chi phí này kéo dài.'))
        if metric in {'NPAT','UnderwritingProfit','InvestmentIncome','NetMargin','ROE','ROA','Revenue'}:
            u,n=current('UnderwritingProfit'),current('NPAT')
            if finite(u) and finite(n):
                extra.append(f'Lợi nhuận hoạt động bảo hiểm quý gần nhất {fmt("UnderwritingProfit",u)}, trong khi lợi nhuận sau thuế {fmt("NPAT",n)}. '+
                    ('Lãi ròng dương phụ thuộc đóng góp ròng ngoài hoạt động bảo hiểm khi khoản mục bảo hiểm còn âm.' if u<0<n else
                     'Nghiệp vụ bảo hiểm đóng góp lợi nhuận dương, cùng hỗ trợ kết quả ròng.' if u>0 and n>0 else
                     'Kết quả này hạn chế khả năng bổ sung vốn từ lợi nhuận giữ lại.' if n<0 else 'Hai khoản mục cho thấy cơ cấu nguồn tạo lợi nhuận tại kỳ này.'))
            ml=margin_link()
            if ml:extra.append(ml)
            if metric=='InvestmentIncome':
                c=changes(metric)
                if c:extra.append('Nguồn thu đầu tư '+('tăng, bổ sung thu nhập hỗ trợ kết quả chung' if c[1].Value>c[0].Value else 'giảm, thu hẹp phần thu nhập hỗ trợ kết quả chung')+'; mức đóng góp ròng còn phụ thuộc chi phí đầu tư.')
            if metric in {'ROE','ROA'}:
                other='ROA' if metric=='ROE' else 'ROE';other_v=current(other);ea=current('EquityAssets')
                extra=[]
                if finite(v) and finite(other_v):extra.append(f'{metric} quý gần nhất {fmt(metric,v)} đi cùng {other} {fmt(other,other_v)}'+
                    (f' và vốn/tài sản {fmt("EquityAssets",ea)}.' if finite(ea) else '.'))
                c=paired('ROE','ROA')
                if c:
                    de=c[0][1].Value-c[0][0].Value;da=c[1][1].Value-c[1][0].Value
                    extra.append('ROE và ROA cùng cải thiện trong năm cuối, cho thấy hiệu quả tăng trên cả vốn và tài sản.' if de>0 and da>0 else
                                 'ROE tăng trong khi ROA giảm; cải thiện lợi suất vốn chưa đi cùng cải thiện hiệu quả tài sản.' if de>0 and da<0 else
                                 'ROE và ROA cùng giảm trong năm cuối, làm suy yếu khả năng tạo lợi nhuận nội bộ.' if de<0 and da<0 else
                                 'ROE và ROA biến động khác chiều; cần đặt lợi suất vốn cạnh thay đổi cơ cấu tài trợ tài sản.')
                if finite(v) and finite(mean):extra.append(('Hiệu quả sinh lời cao hơn' if v>mean else 'Hiệu quả sinh lời thấp hơn' if v<mean else 'Hiệu quả sinh lời tương đương')+' nhóm so sánh tại quý gần nhất.')
        if metric in {'Equity','EquityAssets','TotalAssets','InsuranceReserves','InsuranceReservesEquity','ReservesPremium','PaidInCapital'}:
            a,b=point('TotalAssets'),point('Equity')
            if a is not None and b is not None and a.Period==b.Period and a.Value>0:
                extra.append(f'Cuối năm {a.DisplayPeriod}, vốn chủ sở hữu tài trợ {vi(b.Value/a.Value*100,2)}% tài sản. '+
                    ((result['Meaning'] or result['Conclusion']) if metric in {'Equity','EquityAssets','TotalAssets'} else ''))
            c=paired('InsuranceReserves','Equity')
            if c and not items.get('InsuranceReserves',{}).get('HistoryBreaks'):
                (r0,r1),(e0,e1)=c
                if e0.Value>0 and e1.Value>0:
                    before,after=r0.Value/e0.Value,r1.Value/e1.Value
                    extra.append(f'Dự phòng nghiệp vụ trên vốn từ {vi(before,2)} lên {vi(after,2)} lần trong năm {e1.DisplayPeriod}; '+
                        ('quy mô nghĩa vụ dự phòng tăng tương đối so với vốn, khiến sai lệch ước tính tổn thất nhạy hơn đối với bộ đệm vốn.' if after>before else
                         'vốn tăng tương đối so với nghĩa vụ dự phòng, tạo dư địa hấp thụ sai lệch ước tính tốt hơn.'))
        if metric in {'Cash','CashAssets','CFO'}:
            cash,cf=current('Cash'),current('CFO')
            if finite(cash) and finite(cf):extra.append(f'Tiền và tương đương tiền cuối quý {fmt("Cash",cash)}, dòng tiền kinh doanh trong quý {fmt("CFO",cf)}; '+
                ('hoạt động kinh doanh tạo thêm nguồn tiền để đáp ứng chi trả.' if cf>0 else 'hoạt động kinh doanh đang sử dụng tiền, làm tăng nhu cầu duy trì dự trữ hoặc thu hồi các khoản đầu tư.'))
            n=point('CFO');profit=point('NPAT')
            if n is not None and profit is not None and n.Period==profit.Period:
                extra.append(f'Năm {n.DisplayPeriod}, tiền kinh doanh {fmt("CFO",n.Value)} so với lợi nhuận {fmt("NPAT",profit.Value)}; '+
                    ('khả năng tạo tiền hỗ trợ kết quả lợi nhuận đã ghi nhận.' if n.Value>=profit.Value and n.Value>0 else 'lợi nhuận và nguồn tiền không tăng tương ứng, nên thanh khoản còn phụ thuộc thời điểm thu phí, chi bồi thường và các khoản phải thu.'))
        if metric in {'InsuranceLiquidity','StressedLiquidAssets','InsuranceContractObligations'}:
            li=current('InsuranceLiquidity')
            if finite(li):extra.append(f'Tài sản thanh khoản sau khấu trừ bằng {fmt("InsuranceLiquidity",li)} nghĩa vụ bảo hiểm; '+
                ('phần dư sau khấu trừ hỗ trợ đáp ứng yêu cầu chi trả bất lợi.' if li>=1 else 'phần thiếu làm tăng nhu cầu huy động tiền hoặc chuyển nhượng tài sản khi chi trả tăng.'))
        if not extra and finite(v):
            # Giữ nhận định chuyên biệt sẵn có; không đưa hướng dẫn phương pháp vào thân bài.
            text=pair.get('AnalysisText','')
            banned=('phương pháp','Bảng ','đo vị trí','cần dữ liệu','chưa đủ','định nghĩa')
            sentences=[s.strip().rstrip('.')+'.' for s in text.split('. ') if s.strip() and not any(b in s for b in banned)]
            extra=sentences[:2]
        if extra:
            result['Meaning']=' '.join(dict.fromkeys(s.strip() for s in extra if s.strip()))
            # Không dùng kết luận chung về dữ liệu hay định nghĩa từ phiên bản cũ.
            result['Conclusion']=''
        if metric in {'PB','PE'}:return result
    elif typ in {'SECURITIES','CORPORATE'}:
        if metric in {'Revenue','NPAT','NetMargin','ROE','ROA','EBITDA','EBITDAMargin','OperatingProfitMargin','GrossMargin'}:
            ml=margin_link(metric if metric in {'EBITDAMargin','OperatingProfitMargin','GrossMargin'} else 'NetMargin')
            if ml:extra.append(ml)
        if typ=='SECURITIES':
            if metric in {'Loans','MarginLoans','MarginLoansEquity','DebtEquity','TotalDebt','Equity','AvailableCapitalRatio'}:
                loans,equity=current('Loans'),current('Equity')
                if finite(loans) and finite(equity) and equity>0:
                    extra.append(f'Các khoản cho vay cuối quý bằng {vi(loans/equity,2)} lần vốn chủ sở hữu; '+
                        ('quy mô cho vay vượt vốn khiến thu hồi khoản vay và khả năng duy trì nguồn tài trợ có ảnh hưởng lớn đến thanh khoản.' if loans>equity else
                         'quy mô cho vay thấp hơn vốn, tạo dư địa tương đối để hấp thụ tổn thất trên khoản mục này.'))
                c=paired('Loans','Equity')
                if c and c[0][0].Value>0 and c[1][0].Value>0:
                    gl=c[0][1].Value/c[0][0].Value-1;ge=c[1][1].Value/c[1][0].Value-1
                    extra.append(f'Trong năm {c[0][1].DisplayPeriod}, cho vay tăng {vi(gl*100,1)}%, vốn tăng {vi(ge*100,1)}%; '+
                        ('tốc độ mở rộng khoản vay làm tăng mức phơi nhiễm trên vốn.' if gl>ge else 'vốn theo kịp tăng trưởng khoản vay, giữ sức chịu đựng tương đối.'))
            if metric=='AvailableCapitalRatio' and finite(v):
                extra.append(f'Tỷ lệ vốn khả dụng đạt {fmt(metric,v)}'+(f', chênh {vi((v-mean)*100,1)} điểm phần trăm so với peer.' if finite(mean) else '.')+' Biến động tỷ lệ này phản ánh dư địa vốn sau khi tính các rủi ro hoạt động; kết luận về ưu thế vốn cần được đặt cạnh quy mô cho vay và danh mục đầu tư.')
        if metric in {'CFO','CFO_Margin','CFO_Debt','FOCF_Debt','FOCFMargin','Capex','CapexRevenue','CashDebt'}:
            cf,cap=point('CFO'),point('Capex')
            if cf is not None and cap is not None and cf.Period==cap.Period:
                residual=cf.Value-abs(cap.Value)
                extra.append(f'Sau chi đầu tư tài sản cố định, tiền còn lại năm {cf.DisplayPeriod} khoảng {fmt("CFO",residual)}; '+
                    ('nguồn tiền này hỗ trợ giảm nợ hoặc bổ sung dự trữ thanh khoản.' if residual>0 else 'thâm hụt cần được bù bằng tiền dự trữ hoặc nguồn tài trợ khác.'))
        if metric in {'DebtEBITDA','NetDebtEBITDA','InterestCoverage','TotalDebt'}:
            c=paired('TotalDebt','EBITDA')
            if c and min(c[0][0].Value,c[1][0].Value,c[1][1].Value)>0:
                gd=c[0][1].Value/c[0][0].Value-1;gp=c[1][1].Value/c[1][0].Value-1
                extra.append(f'Nợ vay năm cuối thay đổi {vi(gd*100,1)}%, EBITDA thay đổi {vi(gp*100,1)}%; '+
                    ('khả năng tạo thu nhập tăng chậm hơn nợ, làm suy yếu mức bao phủ nghĩa vụ vay.' if gd>gp else 'khả năng tạo thu nhập theo kịp nợ, hỗ trợ cải thiện mức bao phủ nghĩa vụ vay.'))
        if extra:result['Meaning']=' '.join(dict.fromkeys([result['Meaning']]+extra)).strip()
    # Với chỉ tiêu có hướng tốt/xấu, nối diễn biến năm với vị thế hiện tại.
    from scripts.report_evidence import HIGHER,LOWER
    c=changes(metric)
    if c and finite(v) and finite(mean) and metric in HIGHER|LOWER:
        delta=c[1].Value-c[0].Value
        favorable=v>mean if metric in HIGHER else v<mean
        improved=delta>0 if metric in HIGHER else delta<0
        if delta and favorable!=improved:
            result['Conclusion']=('Chỉ tiêu vẫn thuận lợi hơn peer tại quý gần nhất, nhưng suy giảm trong năm cuối làm giảm mức độ bền vững của lợi thế này.' if favorable else
                                  'Năm cuối đã cải thiện, song vị thế quý gần nhất vẫn yếu hơn peer; chuyển biến vừa qua chưa đủ để tạo lợi thế tương đối.')
    return result
