"""Lập luận bảo hiểm từ bằng chứng cùng kỳ, dùng chung màn hình và Word.

Tham khảo cách nối luận điểm trong báo cáo PAC do người dùng cung cấp.
Không sao chép sự kiện của PAC, không dùng nhận xét thay phiếu thẩm định.
"""
import math
import pandas as pd
from scripts.insurance_presentation import format_metric as fmt, own_value
from scripts.methodology_kpi_engine import PCT, MULT

ENGINE_VERSION = '8.125.0'


def number(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def value(pairs, metric):
    p = pairs.get(metric)
    return own_value(p) if p else None


def history_rows(pair):
    h = pair.get('History', pd.DataFrame())
    if h.empty:
        return h
    return h[h.Status.eq('OK') & h.Value.map(lambda x: number(x) is not None)]


def last_change(pair):
    """Chỉ hai mốc yêu cầu liền kề; không vượt mốc thiếu/đứt gãy nguồn."""
    h = pair.get('History', pd.DataFrame())
    if len(h) < 2 or len(h)-1 in pair.get('HistoryBreaks', []):
        return None
    a, b = h.iloc[-2], h.iloc[-1]
    if not (a.Status == b.Status == 'OK') or any(number(x) is None for x in (a.Value, b.Value)):
        return None
    # Lịch sử chuẩn có một hàng mỗi năm; kiểm tra thêm khi gọi với bộ dữ liệu khác.
    try:
        if int(str(b.Period)[:4]) - int(str(a.Period)[:4]) != 1:
            return None
    except ValueError:
        return None
    if a.Basis != b.Basis:
        return None
    return a, b


def aligned_changes(pairs, *metrics):
    changes = [last_change(pairs.get(m, {})) for m in metrics]
    if any(c is None for c in changes):
        return None
    if len({(str(c[0].Period), str(c[1].Period)) for c in changes}) != 1:
        return None
    return changes


def decimal(v, digits=2):
    return f'{v:,.{digits}f}'.replace(',', '\x01').replace('.', ',').replace('\x01', '.')


def delta(metric, a, b):
    if metric in PCT:
        return decimal(abs(b-a)*100) + ' điểm phần trăm'
    if metric in MULT:
        return decimal(abs(b-a)) + ' lần'
    if a > 0 and b >= 0:
        return decimal(abs(b/a-1)*100, 1) + '%'
    return fmt(metric, abs(b-a), 'OK')


def trend_sentence(pair):
    """Tóm tắt toàn chuỗi và năm cuối; số từng năm vẫn ở bảng/biểu đồ."""
    m = pair['Metric']; h = pair.get('History', pd.DataFrame()); z = history_rows(pair)
    if z.empty:
        return 'Chưa có lịch sử đủ nguồn để đánh giá tính bền vững của chỉ tiêu.'
    a, b = z.iloc[0], z.iloc[-1]
    label={'EquityAssets':'tỷ trọng vốn chủ sở hữu trên tài sản',
           'InsuranceReservesEquity':'dự phòng nghiệp vụ trên vốn chủ sở hữu',
           'DebtEquity':'nợ vay trên vốn chủ sở hữu'}.get(m,pair['Label'].lower())
    text = f"Giai đoạn {a.DisplayPeriod}–{b.DisplayPeriod}, {label} từ {fmt(m,a.Value,'OK')} lên {fmt(m,b.Value,'OK')}."
    if b.Value < a.Value:
        text = text.replace(' từ ', ' giảm từ ').replace(' lên ', ' xuống ')
    elif b.Value == a.Value:
        text = f"Trong {len(z)} mốc có dữ liệu, đầu và cuối chuỗi {a.DisplayPeriod}–{b.DisplayPeriod} cùng ở mức {fmt(m,b.Value,'OK')}."
    if len(z) == 1:
        text = f"Chỉ có mốc {b.DisplayPeriod}: {fmt(m,b.Value,'OK')}; chưa đủ chuỗi để nhận định xu hướng."
    if pair.get('HistoryBreaks'):
        text = f"Chuỗi {a.DisplayPeriod}–{b.DisplayPeriod} có điểm đứt gãy khả năng so sánh; không diễn giải chênh lệch toàn chuỗi thành tăng trưởng."
    c = last_change(pair)
    if c:
        x,y = c
        if y.Value != x.Value:
            text += f" Riêng {y.DisplayPeriod}, chỉ tiêu {'tăng' if y.Value>x.Value else 'giảm'} {delta(m,x.Value,y.Value)} so với {x.DisplayPeriod}."
        else:
            text += f' Hai năm cuối {x.DisplayPeriod}–{y.DisplayPeriod} không thay đổi.'
    elif len(h)>1:
        text += ' Không tính biến động năm cuối khi mốc liền kề thiếu hoặc không so sánh được.'
    if len(z)<len(h):
        text += f' Có {len(z)}/{len(h)} mốc đủ nguồn; khoảng thiếu được giữ nguyên.'
    return text


def comparable_peers(pair, same_model=False):
    q = pair.get('Peers', pd.DataFrame())
    if len(q)<2:
        return q.iloc[:0]
    z = q.iloc[1:]
    z = z[z.Included & z.Status.eq('OK') & z.Value.map(lambda x:number(x) is not None)]
    if same_model:
        z = z[z.SameModel]
    return z


def peer_sentence(pair):
    """Trung vị giảm ảnh hưởng công ty lớn; luôn nêu bình quân, N và kỳ."""
    v=own_value(pair);m=pair['Metric'];z=comparable_peers(pair);n=len(z)
    if v is None:
        return f"{pair['Period']}: chưa có giá trị hợp lệ của doanh nghiệp để kết luận vị thế tương đối; số peer không thay thế số doanh nghiệp."
    text=f"Tại {pair['Period']}, doanh nghiệp đạt {fmt(m,v,'OK')}. "
    if n>=5:
        med=float(z.Value.median());mean=float(z.Value.mean())
        relation='cao hơn' if v>med else 'thấp hơn' if v<med else 'bằng'
        text+=f"Bình quân {n} peer là {fmt(m,mean,'OK')}, trung vị {fmt(m,med,'OK')}; doanh nghiệp {relation} trung vị"
        if v!=med:text+=' '+delta(m,med,v)
        text+='.'
        if (v-mean)*(v-med)<0:
            text+=' Bình quân và trung vị cho hai vị trí khác nhau; mẫu phân tán nên không dùng riêng bình quân để kết luận.'
    elif n:
        text+='Đối chiếu trực tiếp: '+'; '.join(f'{r.Ticker} {fmt(m,r.Value,"OK")}' for r in z.itertuples())+'.'
    else:
        text+='Chưa có peer cùng kỳ, cùng cơ sở đủ dữ liệu.'
    text+=f" Có {n}/{pair.get('PeerCandidateCount',n)} peer được dùng; {pair.get('PeerScope','cùng kỳ và cơ sở').lower()}."
    if m in ('ROE','ROA','PB','PE'):
        text+=' Giữ cơ sở tỷ số nguồn tại quý báo cáo.'
    return text


def _growth_link(pairs, metric, other, label):
    c=aligned_changes(pairs,metric,other)
    if not c:return ''
    (a,b),(x,y)=c
    if a.Value<=0 or x.Value<=0 or b.Value<0 or y.Value<0:return ''
    g=b.Value/a.Value-1;k=y.Value/x.Value-1
    return (f"Năm {b.DisplayPeriod}, {pairs[metric]['Label'].lower()} thay đổi {decimal(g*100,1)}%, "
            f"trong khi {label} thay đổi {decimal(k*100,1)}%. "
            +('Quy mô tăng nhanh hơn nguồn vốn kế toán, làm tăng yêu cầu bổ sung khả năng hấp thụ tổn thất.'
              if other=='Equity' and g>k and g>0 else
              'Nguồn vốn kế toán tăng nhanh hơn quy mô đang đối chiếu, hỗ trợ bộ đệm tương đối.'
              if other=='Equity' and k>g and k>0 else
              'Lợi nhuận tăng nhanh hơn doanh thu, phù hợp với sự cải thiện biên sinh lời.'
              if other=='NPAT' and k>g and k>0 else
              'Lợi nhuận chưa theo kịp tăng trưởng doanh thu; phần quy mô tăng thêm chưa chuyển hóa tương ứng thành thu nhập ròng.'
              if other=='NPAT' and g>k and g>0 else
              'Hai tốc độ này cần được đọc cùng biên lợi nhuận và biến động cơ cấu kinh doanh.'))


def _profit_link(pairs, subtype):
    u=value(pairs,'UnderwritingProfit');n=value(pairs,'NPAT');i=value(pairs,'InvestmentIncome')
    if u is None:return ''
    text=f"Cùng quý, lợi nhuận hoạt động bảo hiểm là {fmt('UnderwritingProfit',u,'OK')}"
    if n is not None:text+=f", còn lợi nhuận sau thuế là {fmt('NPAT',n,'OK')}"
    text+='.'
    if subtype in ('GROUP','LIFE'):
        text+=' Khoản mục bảo hiểm chịu ảnh hưởng cơ cấu hoạt động và dự phòng ở phạm vi báo cáo; không diễn giải số âm thành lỗ khai thác phi nhân thọ.'
    elif u<0 and n is not None and n>0:
        text+=' Lãi ròng dương chưa đi cùng lãi hoạt động bảo hiểm; khả năng sinh lời còn cần đóng góp ròng từ các hoạt động khác.'
    elif u>0 and n is not None and n>0:
        text+=' Hoạt động bảo hiểm và kết quả ròng cùng dương, hỗ trợ nguồn tạo lợi nhuận từ nghiệp vụ.'
    elif u<0:
        text+=' Hoạt động bảo hiểm đang làm giảm nguồn tích lũy nội bộ và cần được cải thiện để giảm áp lực lên vốn.'
    if i is not None:
        text+=f" Thu nhập đầu tư {fmt('InvestmentIncome',i,'OK')} là khoản thu trước chi phí liên quan, không phải lợi nhuận đầu tư ròng."
    return text


def _combined_link(pairs):
    c=aligned_changes(pairs,'CombinedRatio','LossRatio','ExpenseRatio')
    if not c:return ''
    (a,b),(l0,l1),(e0,e1)=c
    if max(abs(a.Value-l0.Value-e0.Value),abs(b.Value-l1.Value-e1.Value))>1e-6:
        return 'Các cấu phần chưa khớp tổng tỷ lệ kết hợp; cần đối chiếu định nghĩa trước khi quy nguyên nhân.'
    dl=l1.Value-l0.Value;de=e1.Value-e0.Value
    text=(f"Trong {b.DisplayPeriod}, bồi thường {'tăng' if dl>=0 else 'giảm'} {decimal(abs(dl)*100)} điểm phần trăm, "
          f"chi phí {'tăng' if de>=0 else 'giảm'} {decimal(abs(de)*100)} điểm phần trăm so với {a.DisplayPeriod}. ")
    if dl*de<0:
        text+=('Chi phí gia tăng bù trừ một phần lợi ích từ giảm bồi thường.' if de>0 else 'Chi phí giảm bù trừ một phần áp lực từ tăng bồi thường.')
    elif dl<=0 and de<=0:text+='Hai cấu phần cùng hỗ trợ biên khai thác theo quy ước BCTC.'
    else:text+='Hai cấu phần cùng tạo áp lực lên biên khai thác theo quy ước BCTC.'
    return text


def _capital_link(pairs):
    text=_growth_link(pairs,'TotalAssets','Equity','vốn chủ sở hữu')
    c=aligned_changes(pairs,'Equity','NPAT')
    if c:
        (a,b),(_,n)=c
        if n.Value<0 and b.Value<a.Value:
            text+=f" Năm {b.DisplayPeriod} vừa ghi nhận lỗ {fmt('NPAT',n.Value,'OK')} vừa giảm vốn; khả năng tự bổ sung bộ đệm đang chịu sức ép."
        elif n.Value>0 and b.Value<a.Value:
            text+=f" Vốn giảm dù năm {b.DisplayPeriod} vẫn có lãi; cần đối chiếu cổ tức và các biến động vốn khác trước khi xác định nguyên nhân."
    return text.strip()


def metric_narrative(pair, pairs=None, subtype='NONLIFE'):
    pairs=pairs or {pair['Metric']:pair};m=pair['Metric'];v=own_value(pair)
    # Liên kết chỉ sử dụng số doanh nghiệp cùng quý với chỉ tiêu đang xét.
    pairs={k:p for k,p in pairs.items() if p.get('Period')==pair.get('Period')}
    c=last_change(pair);up=c and c[1].Value>c[0].Value;down=c and c[1].Value<c[0].Value
    from scripts.insurance_history import history_peer_sentence
    history=(trend_sentence(pair)+' '+history_peer_sentence(pair)).strip();peer=peer_sentence(pair)
    if v is None:
        return dict(NarrativeHistory=history,NarrativePeer=peer,
                    AnalysisText='Bằng chứng hiện có chỉ hỗ trợ phân tích các mốc lịch sử được nêu; chưa xác định diễn biến hoặc vị thế của doanh nghiệp tại quý gần nhất.',
                    ConclusionText='Chưa đủ căn cứ kết luận cho quý so sánh; cần số liệu đúng kỳ và đúng phạm vi.')
    analysis='';conclusion=''
    if m in ('GrossWrittenPremium','NetInsurancePremium','Revenue'):
        analysis=_growth_link(pairs,m,'Equity','vốn chủ sở hữu') if m!='Revenue' else _growth_link(pairs,m,'NPAT','lợi nhuận sau thuế')
        cr=value(pairs,'CombinedRatio')
        if cr is not None:
            analysis+=f" Tỷ lệ kết hợp cùng quý {fmt('CombinedRatio',cr,'OK')} " + ('cho thấy doanh thu phí đang đi cùng thặng dư khai thác theo quy ước tính.' if cr<1 else 'cho thấy áp lực bồi thường và chi phí cần được xử lý trước khi mở rộng quy mô.')
        if m=='NetInsurancePremium':
            analysis+=' Phí thuần chịu cả tác động của tái bảo hiểm và dự phòng phí; không lấy chênh lệch phí gốc với phí thuần làm tỷ lệ nhượng tái.'
        if not analysis.strip():analysis=f"Quy mô {fmt(m,v,'OK')} là cơ sở đối chiếu năng lực tạo doanh thu tại kỳ này; khả năng chuyển hóa thành vốn phụ thuộc phần lợi nhuận giữ lại."
        conclusion=('Hoạt động đang mở rộng ở năm cuối chuỗi; cần duy trì chất lượng khai thác để tăng trưởng hỗ trợ sức chịu đựng tài chính.' if up else
                    'Năm cuối chuỗi ghi nhận thu hẹp hoạt động; cần theo dõi khả năng phân bổ chi phí cố định và duy trì nguồn thu.' if down else
                    'Quy mô hiện có cần được đánh giá cùng hiệu quả khai thác; chưa có bằng chứng về cải thiện xu hướng năm cuối.')
        if m=='GrossWrittenPremium' and value(pairs,'MarketSharePremium') is None:
            conclusion+=' Chưa có mẫu số toàn thị trường để kết luận tăng hay giảm thị phần.'
    elif m=='TotalAssets':
        analysis=_capital_link(pairs)
        ea=value(pairs,'EquityAssets')
        if ea is not None:analysis+=f" Vốn chủ sở hữu hiện tài trợ {fmt('EquityAssets',ea,'OK')} tổng tài sản; phần còn lại cần được đối chiếu với nghĩa vụ bảo hiểm và các nguồn vốn khác."
        conclusion='Quy mô tài sản tạo năng lực đầu tư nhưng sức chịu lỗ phụ thuộc bộ đệm vốn và chất lượng tài sản; thứ hạng quy mô không quyết định chất lượng tín dụng.'
    elif m=='MarketSharePremium':
        analysis=f"Thị phần {fmt(m,v,'OK')} đo vị trí trên mẫu số toàn thị trường đã khai báo; {'mức giảm năm cuối cho thấy vị trí tương đối thu hẹp' if down else 'mức tăng năm cuối cho thấy vị trí tương đối được mở rộng' if up else 'cần chuỗi liên tục để xác nhận độ bền vị thế'}."
        conclusion='Vị thế thị trường '+('cải thiện theo chuỗi gần nhất' if up else 'chịu áp lực theo chuỗi gần nhất' if down else 'chưa có xu hướng đủ rõ')+'; chất lượng tăng trưởng vẫn phụ thuộc lợi nhuận và mức rủi ro giữ lại.'
    elif m=='LargestProductShare':
        analysis=f"Một dòng sản phẩm chiếm {fmt(m,v,'OK')} phí bảo hiểm; " + ('vượt mốc 80% được phương pháp dùng làm dấu hiệu tập trung tiêu cực.' if v>.8 else 'chưa vượt mốc 80% nêu trong phương pháp, nhưng vẫn cần xét tương quan tổn thất giữa các sản phẩm.')
        conclusion='Rủi ro tập trung sản phẩm là trọng tâm theo dõi.' if v>.8 else 'Chưa xuất hiện dấu hiệu tập trung trên 80% ở chỉ tiêu này; chưa đủ để kết luận danh mục đã đa dạng.'
    elif m in ('NPAT','UnderwritingProfit','InvestmentIncome','NetMargin'):
        analysis=_profit_link(pairs,subtype)
        if m=='NetMargin':analysis+=' Biên ròng phản ánh cả các hoạt động ngoài bảo hiểm, nên cần phân biệt chất lượng lợi nhuận ròng với biên khai thác.'
        if m=='InvestmentIncome':
            analysis+=(' Thu nhập đầu tư năm cuối giảm, làm thu hẹp nguồn thu hỗ trợ nếu các chi phí khác không đổi.' if down else
                       ' Thu nhập đầu tư năm cuối tăng, mở rộng nguồn thu hỗ trợ nhưng chưa chứng minh lợi suất danh mục tăng.' if up else '')
            conclusion='Chất lượng nguồn thu đầu tư còn phụ thuộc mức lặp lại, chi phí vốn và rủi ro đối tác; cần cơ cấu danh mục để đánh giá độ bền.'
        elif m=='UnderwritingProfit' and subtype in ('GROUP','LIFE'):
            conclusion='Cần tách kết quả theo pháp nhân và mảng hoạt động để xác định hiệu quả phi nhân thọ; vẫn phân tích được diễn biến khoản mục hợp nhất.'
        else:
            conclusion=('Kết quả kỳ này đang làm hao hụt nguồn tích lũy nội bộ.' if v<0 else
                        'Kết quả dương tạo nguồn bổ sung vốn nếu được giữ lại.' if v>0 else 'Chưa có phần lợi nhuận để bổ sung vốn ở kỳ này.')
            if down:conclusion+=' Xu hướng năm cuối giảm làm hạn chế mức hỗ trợ so với năm trước.'
            elif up:conclusion+=' Năm cuối có cải thiện; cần duy trì qua các kỳ tiếp theo.'
    elif m in ('ROE','ROA'):
        other='ROA' if m=='ROE' else 'ROE';ov=value(pairs,other);ea=value(pairs,'EquityAssets')
        analysis=f"{m} {fmt(m,v,'OK')}"
        if ov is not None:analysis+=f" đi cùng {other} {fmt(other,ov,'OK')}"
        if ea is not None:analysis+=f" và vốn/tài sản {fmt('EquityAssets',ea,'OK')}"
        analysis+='.'
        cross=aligned_changes(pairs,'ROE','ROA','EquityAssets')
        if cross and cross[0][1].Value>cross[0][0].Value and cross[1][1].Value<=cross[1][0].Value and cross[2][1].Value<cross[2][0].Value:
            analysis+=' ROE tăng trong khi ROA không tăng và tỷ trọng vốn giảm; cải thiện ROE chưa phản ánh cải thiện đồng thời hiệu quả tài sản, cần xét ảnh hưởng đòn bẩy.'
        else:analysis+=' Sự khác biệt về tỷ trọng vốn và dự phòng ảnh hưởng khả năng so sánh tỷ suất giữa các mô hình bảo hiểm.'
        z=comparable_peers(pair,same_model=True)
        if len(z)>=5:
            med=float(z.Value.median())
            analysis+=f" Trong {len(z)} peer cùng phạm vi BCTC, trung vị là {fmt(m,med,'OK')}; mức của doanh nghiệp {'cao hơn' if v>med else 'thấp hơn' if v<med else 'bằng'} mốc này."
        conclusion=('Tỷ suất âm cho thấy khả năng tạo lợi nhuận trên nền vốn/tài sản đang suy yếu.' if v<0 else
                    'Hiệu quả sinh lời năm cuối cải thiện, hỗ trợ tích lũy vốn nếu lợi nhuận được giữ lại.' if up else
                    'Hiệu quả sinh lời năm cuối suy giảm; cần theo dõi khả năng tạo vốn nội bộ.' if down else
                    'Tỷ suất hiện có là bằng chứng về hiệu quả sử dụng vốn/tài sản; cần thêm xu hướng để kết luận mức cải thiện.')
    elif m in ('LossRatio','ExpenseRatio','CombinedRatio'):
        analysis=_combined_link(pairs)
        cr=value(pairs,'CombinedRatio')
        if cr is not None:
            analysis+=f" Tỷ lệ kết hợp tại quý so sánh {fmt('CombinedRatio',cr,'OK')}, "
            analysis+=('còn dư địa '+decimal((1-cr)*100)+' điểm phần trăm trước mốc hòa vốn 100% theo quy ước BCTC.' if cr<1 else
                       'vượt mốc hòa vốn 100% '+decimal((cr-1)*100)+' điểm phần trăm theo quy ước BCTC.' if cr>1 else 'đúng mốc hòa vốn 100% theo quy ước BCTC.')
        if v<0:
            analysis+=' Giá trị âm có thể liên quan hoàn nhập hoặc khoản bù trừ; cần đối chiếu cấu phần, chưa xem đây là hiệu quả bền vững.'
        z=history_rows(pair)
        if m=='CombinedRatio' and len(z)>=2:
            analysis+=f" Trong {len(z)} mốc lịch sử có số, {int((z.Value>1).sum())} mốc vượt 100%."
        conclusion=('Chỉ tiêu âm cần đối chiếu trước khi kết luận hiệu quả.' if v<0 else
                    'Khai thác đang tạo thặng dư theo quy ước đang dùng; độ bền phụ thuộc kiểm soát cả bồi thường và chi phí.' if m=='CombinedRatio' and v<1 else
                    'Khai thác đang chịu thâm hụt theo quy ước đang dùng, tạo áp lực lên nguồn tích lũy vốn.' if m=='CombinedRatio' and v>1 else
                    'Khai thác ở điểm hòa vốn theo quy ước đang dùng, chưa có bộ đệm trước tổn thất tăng thêm.' if m=='CombinedRatio' else
                    'Cấu phần này giảm ở năm cuối, hỗ trợ biên khai thác nhưng không bù được mọi rủi ro từ cấu phần còn lại.' if down else
                    'Cấu phần này tăng ở năm cuối, làm tiêu hao thêm phí thuần và gây áp lực lên biên khai thác.' if up else
                    'Cần đọc chỉ tiêu cùng tỷ lệ kết hợp để đánh giá phần phí còn lại sau bồi thường và chi phí.')
    elif m in ('Equity','EquityAssets','PaidInCapital','PaidInCapitalRequired'):
        analysis=_capital_link(pairs)
        if m=='PaidInCapital':
            analysis+=f" Vốn thực góp và thặng dư là {fmt(m,v,'OK')}; khoản này không bao gồm toàn bộ lợi nhuận giữ lại trong vốn chủ sở hữu."
        if m=='PaidInCapitalRequired':
            analysis+=f" Vốn thực góp bằng {fmt(m,v,'OK')} mức yêu cầu đã khai báo theo giấy phép. "
            analysis+=('Số liệu cho thấy thấp hơn mẫu số vốn yêu cầu.' if v<1 else 'Mức hiện tại cao hơn hoặc bằng mẫu số vốn yêu cầu; chưa bao gồm nhu cầu vốn dự báo hai năm tới.')
        if m=='PaidInCapitalRequired' and v<1:conclusion='Ưu tiên xác minh thiếu hụt vốn và kế hoạch bổ sung; mức xếp hạng cần quyết định thẩm định theo phương pháp.'
        elif v<=0:conclusion='Bộ đệm vốn không dương là tín hiệu rủi ro trọng yếu cần được xác minh ngay ở đúng pháp nhân.'
        elif down:conclusion='Bộ đệm vốn theo chỉ tiêu này giảm ở năm cuối; khả năng hấp thụ tổn thất cần được theo dõi sát.'
        elif up:conclusion='Bộ đệm vốn theo chỉ tiêu này được củng cố ở năm cuối; cần đối chiếu đồng thời mức tăng nghĩa vụ và rủi ro đầu tư.'
        else:conclusion='Mức vốn hiện tại cung cấp bộ đệm kế toán; cần đánh giá nhu cầu vốn theo rủi ro để xác định mức đầy đủ.'
        if value(pairs,'SolvencyRatio') is None:conclusion+=' Chưa có biên khả năng thanh toán để xác nhận mức an toàn vốn theo công bố.'
    elif m in ('InsuranceReserves','InsuranceReservesEquity','ReservesPremium'):
        ratio=value(pairs,'InsuranceReservesEquity')
        analysis=(f"Dự phòng tương đương {fmt('InsuranceReservesEquity',ratio,'OK')} vốn chủ sở hữu ở quý so sánh. " if ratio is not None else '')
        analysis+='Đây là quy mô nghĩa vụ kế toán so với bộ đệm; dự phòng không phải nợ vay.'
        if m=='ReservesPremium':analysis+=' Mẫu số tại quý là phí thuần 12 tháng, nên không diễn giải tỷ lệ này như dự phòng trên phí riêng ba tháng.'
        if pair.get('HistoryBreaks'):analysis+=' Điểm đứt gãy nguồn làm mất khả năng so sánh toàn chuỗi; chỉ nhận xét các đoạn có cơ sở nhất quán.'
        if m=='InsuranceReservesEquity' and up:
            conclusion='Nghĩa vụ dự phòng tăng tương đối so với vốn, làm bộ đệm nhạy hơn với sai lệch ước tính tổn thất.'
        elif m=='InsuranceReservesEquity' and down:
            conclusion='Quy mô dự phòng trên vốn giảm ở năm cuối, giảm độ nhạy kế toán tương đối; chưa chứng minh chất lượng trích lập tốt hơn.'
        else:conclusion='Chưa thể kết luận dự phòng đầy đủ hay thiếu chỉ từ mức tăng/giảm; cần đối chiếu tổn thất, cơ cấu nghiệp vụ và phương pháp trích lập.'
    elif m=='DebtEquity':
        analysis=f"Nợ vay bằng {fmt(m,v,'OK')} vốn chủ sở hữu tại quý so sánh. "
        if abs(v)<1e-12:
            analysis+='Không ghi nhận nợ vay theo chỉ tiêu nguồn, nên chưa có đòn bẩy nợ vay ở thời điểm này; nghĩa vụ bảo hiểm vẫn tồn tại.'
            conclusion='Nợ vay bằng 0 hỗ trợ tính linh hoạt về nghĩa vụ vay; khả năng thanh khoản bảo hiểm cần đánh giá riêng.'
        else:
            analysis+=('Mức này vượt mốc 15% được phương pháp dùng để yêu cầu thẩm định thêm về tính linh hoạt tài chính.' if v>.15 else 'Mức này chưa vượt mốc 15% nêu trong phương pháp; lịch đáo hạn và chi phí vay vẫn quyết định áp lực thực tế.')
            conclusion=('Nợ vay trên vốn tăng ở năm cuối, làm tăng yêu cầu kiểm soát tái cấp vốn.' if up else
                        'Nợ vay trên vốn giảm ở năm cuối, giảm áp lực đòn bẩy tương đối.' if down else 'Cần đối chiếu nợ đến hạn với nguồn tiền sẵn có để kết luận khả năng tái cấp vốn.')
    elif m=='DebtDue24MEquity':
        analysis=f"Nợ đến hạn 24 tháng bằng {fmt(m,v,'OK')} vốn chủ sở hữu; "+('vượt mốc 20% trong phương pháp, cho thấy áp lực tái cấp vốn cần được thẩm định.' if v>.2 else 'chưa vượt mốc 20% trong phương pháp, nhưng phải so với nguồn tiền thực có.')
        conclusion='Ưu tiên kế hoạch nguồn trả nợ và khả năng huy động đã được cam kết, không mặc định hạn mức chưa xác nhận.'
    elif m=='InsuranceEBITDAInterest':
        analysis=f"EBITDA đã đối chiếu bằng {fmt(m,v,'OK')} chi phí lãi vay; "+('thu nhập này chưa đủ trang trải lãi vay trong kỳ.' if v<1 else 'thu nhập này đủ trang trải lãi vay theo phép đo cùng kỳ.')
        conclusion='Khả năng trả lãi cần kiểm tra thêm dòng tiền và nghĩa vụ bảo hiểm; EBITDA không thay nguồn thanh khoản.'
    elif m in ('FXMismatchLiabilities','InvestmentLeverage','LargestSectorShare'):
        threshold={'FXMismatchLiabilities':.1,'InvestmentLeverage':1.,'LargestSectorShare':.3}[m]
        analysis=f"Mức quan sát {fmt(m,v,'OK')} "+('vượt' if v>threshold else 'không vượt')+f" mốc {decimal(threshold*100,0)}% được dùng để rà soát rủi ro trong phương pháp. "
        analysis+=({'FXMismatchLiabilities':'Tổn thất có thể phát sinh nếu đồng tiền của tài sản và nghĩa vụ biến động khác nhau, sau phần đã phòng vệ.',
                    'InvestmentLeverage':'Tổn thất đầu tư có thể truyền sang vốn chủ sở hữu; cần xét chất lượng từng tài sản và hiệu lực phòng vệ.',
                    'LargestSectorShare':'Tập trung ngành làm tăng khả năng tổn thất đồng thời; cần xét thêm tập trung tổ chức phát hành và ngoại lệ nợ Chính phủ.'}[m])
        conclusion='Chỉ tiêu cho thấy một điểm cần thẩm định sâu về vị thế rủi ro.' if v>threshold else 'Chưa vượt mốc rà soát ở chỉ tiêu này; cần đủ các chiều rủi ro trước khi kết luận danh mục an toàn.'
    elif m in ('InsuranceLiquidity','StressedLiquidAssets','InsuranceContractObligations'):
        liq=value(pairs,'InsuranceLiquidity');assets=value(pairs,'StressedLiquidAssets');ob=value(pairs,'InsuranceContractObligations')
        if assets is not None and ob is not None:
            analysis=f"Tài sản sau khấu trừ {fmt('StressedLiquidAssets',assets,'OK')} đối chiếu nghĩa vụ hợp đồng {fmt('InsuranceContractObligations',ob,'OK')}."
        if liq is not None:
            analysis+=f" Tỷ số bao phủ {fmt('InsuranceLiquidity',liq,'OK')} nằm trong vùng "+('mạnh (>2,2 lần)' if liq>2.2 else 'đầy đủ (1–2,2 lần)' if liq>=1 else 'yếu (<1 lần)')+' của phép đo định lượng Bảng 18.'
            conclusion='Nguồn sau khấu trừ '+('đủ' if liq>=1 else 'chưa đủ')+' bao phủ nghĩa vụ đã khai báo; đánh giá thanh khoản tổng thể còn phụ thuộc thời điểm chi trả và khả năng chuyển đổi tài sản.'
        else:
            analysis+=f" Chỉ tiêu hiện có {fmt(m,v,'OK')}, nhưng thiếu tỷ số nguồn/nhu cầu hoàn chỉnh."
            conclusion='Chưa đủ căn cứ khẳng định mức bao phủ thanh khoản khi chưa ghép được nguồn và nghĩa vụ cùng kỳ.'
    elif m=='SolvencyRatio':
        analysis=f"Biên thực có bằng {fmt(m,v,'OK')} biên tối thiểu theo hồ sơ công bố. "
        analysis+=('Mức dưới 100% là dấu hiệu thiếu hụt tại kỳ cần xác minh với pháp nhân.' if v<1 else 'Mức từ 100% trở lên thể hiện biên thực có không thấp hơn biên tối thiểu ở kỳ này.')
        conclusion='Đây là bằng chứng riêng về biên thanh toán; chưa đủ để dự báo khả năng đáp ứng trong các kịch bản tổn thất tương lai.'
    elif m in ('PB','PE'):
        r=value(pairs,'ROE');n=value(pairs,'NPAT')
        analysis=f"{m} hiện {fmt(m,v,'OK')}"
        if r is not None:analysis+=f", đi cùng ROE {fmt('ROE',r,'OK')}"
        analysis+='.'
        if v<=0:analysis+=' Hệ số không dương không phù hợp để suy luận cổ phiếu rẻ từ so sánh bội số.'
        elif n is not None and n<=0:analysis+=' Lợi nhuận quý không dương trong khi bội số theo kỳ nguồn khác; cần đối chiếu cơ sở lợi nhuận trước khi diễn giải.'
        conclusion='Chỉ dùng làm đối chiếu định giá tại kỳ nguồn; chênh lệch bội số không phải điểm mạnh hay yếu tín nhiệm.'
    if not analysis.strip():
        analysis=f"Giá trị {fmt(m,v,'OK')} cần được đặt trong diễn biến và vị trí tương đối đã nêu để đánh giá tác động đến hồ sơ tài chính."
    return dict(NarrativeHistory=history,NarrativePeer=peer,AnalysisText=analysis.strip(),ConclusionText=conclusion)


def enrich_pack(pack, subtype):
    pairs={p['Metric']:p for p in pack}
    for p in pack:
        p.update(metric_narrative(p,pairs,subtype))
    return pack


def section_findings(pack, subtype):
    """Kết luận cấu phần có mạch lập luận thay cho bảng KPI rời rạc."""
    p={r['Metric']:r for r in pack};period=pack[0]['Period'] if pack else 'kỳ chưa xác định'
    def evidence(m):
        r=p.get(m)
        if not r:return ''
        return r.get('NarrativeHistory',trend_sentence(r))+' '+r.get('NarrativePeer',peer_sentence(r))
    def conclusion(m):return p.get(m,{}).get('ConclusionText','')
    def analysis(m):return p.get(m,{}).get('AnalysisText','')
    business=[('Quy mô và khả năng chuyển hóa tăng trưởng',evidence('GrossWrittenPremium')+' '+analysis('Revenue'))]
    business.append(('Kết luận về hồ sơ kinh doanh',conclusion('GrossWrittenPremium')+' Quy mô mẫu niêm yết không xác nhận sức mạnh thương hiệu, mạng lưới hoặc thị phần toàn ngành.'))
    earnings=[('Chất lượng nguồn tạo lợi nhuận',evidence('NPAT')+' '+_profit_link(p,subtype))]
    if value(p,'CombinedRatio') is not None:
        earnings.append(('Bồi thường, chi phí và độ bền biên khai thác',analysis('CombinedRatio')+' '+conclusion('CombinedRatio')))
    else:earnings.append(('Kết luận về khả năng sinh lời',conclusion('NPAT')+' '+conclusion('UnderwritingProfit')))
    capital=[('Khả năng hấp thụ tổn thất và tích lũy vốn',evidence('Equity')+' '+_capital_link(p)),
             ('Kết luận về vốn và dự phòng',conclusion('EquityAssets')+' '+conclusion('InsuranceReservesEquity'))]
    risk=[('Đòn bẩy và khả năng tái cấp vốn',evidence('DebtEquity')+' '+analysis('DebtEquity')),
          ('Kết luận về vị thế rủi ro',conclusion('DebtEquity'))]
    missing=[p[m]['Label'].lower() for m in ('FXMismatchLiabilities','InvestmentLeverage','LargestSectorShare') if m in p and value(p,m) is None]
    if missing:risk[-1]=(risk[-1][0],risk[-1][1]+' Chưa lượng hóa được '+', '.join(missing)+'; do đó chưa kết luận danh mục đầu tư an toàn chỉ từ nợ vay thấp.')
    liq=value(p,'InsuranceLiquidity');sol=value(p,'SolvencyRatio')
    liquidity=[('Nguồn thanh khoản và nghĩa vụ bảo hiểm',
                evidence('InsuranceLiquidity')+' '+analysis('InsuranceLiquidity') if liq is not None else
                f'Tại {period}, chưa có cặp số liệu tài sản thanh khoản sau khấu trừ và nghĩa vụ hợp đồng đủ để xác định tỷ lệ bao phủ. Vốn chủ sở hữu và tổng tài sản có số không thay thế nguồn tiền có thể chi trả khi xảy ra bồi thường.')]
    liquidity.append(('Kết luận về thanh khoản và khả năng thanh toán',
                      (conclusion('InsuranceLiquidity') if liq is not None else 'Chưa đủ căn cứ kết luận thanh khoản mạnh, đầy đủ hay yếu.')+' '+
                      (analysis('SolvencyRatio') if sol is not None else 'Thiếu biên khả năng thanh toán đúng kỳ, nên chưa xác nhận mức an toàn vốn theo công bố. Đây là giới hạn của bằng chứng, không phải bằng chứng doanh nghiệp mất khả năng chi trả.')))
    valuation=[('Ý nghĩa của chênh lệch định giá',evidence('PB')+' '+analysis('PB')),
               ('Kết luận về định giá tham khảo',conclusion('PE'))]
    return dict(zip(['HỒ SƠ KINH DOANH','HIỆU QUẢ KHAI THÁC VÀ KHẢ NĂNG SINH LỢI','VỐN VÀ DỰ PHÒNG NGHIỆP VỤ',
                     'VỊ THẾ RỦI RO VÀ LINH HOẠT TÀI CHÍNH','THANH KHOẢN VÀ KHẢ NĂNG THANH TOÁN','ĐỊNH GIÁ THAM KHẢO'],
                    [business,earnings,capital,risk,liquidity,valuation]))


def executive_narrative(pack, subtype):
    p={r['Metric']:r for r in pack};out=[]
    for m in ('GrossWrittenPremium','NPAT','EquityAssets'):
        if m not in p:continue
        r=p[m]
        if own_value(r) is None:continue
        # Mỗi luận điểm có diễn biến, đối chiếu và hệ quả; chi tiết cấu phần ở thân báo cáo.
        current=f" Tại {r['Period']}, chỉ tiêu đạt {fmt(m,own_value(r),'OK')}."
        out.append(r.get('NarrativeHistory',trend_sentence(r))+current+' '+r.get('ConclusionText',''))
    cr=value(p,'CombinedRatio')
    if cr is not None:
        r=p['CombinedRatio'];out.insert(1,'Tỷ lệ kết hợp: '+r.get('NarrativePeer',peer_sentence(r))+' '+r.get('ConclusionText',''))
    else:
        r=p.get('ROE')
        if r and own_value(r) is not None:out.insert(1,'ROE: '+r.get('NarrativePeer',peer_sentence(r)))
    return out


def sensitivity_narrative(pack, subtype):
    p={r['Metric']:r for r in pack};positive=[];negative=[]
    cr=value(p,'CombinedRatio');eq=value(p,'EquityAssets');debt=value(p,'DebtEquity')
    if cr is not None:
        positive.append(f"Từ nền tỷ lệ kết hợp {fmt('CombinedRatio',cr,'OK')}, duy trì nhiều kỳ dưới 100% và cải thiện cả bồi thường lẫn chi phí sẽ hỗ trợ nguồn tích lũy từ khai thác.")
        negative.append('Tỷ lệ kết hợp vượt 100% kéo dài hoặc chi phí tăng nhanh hơn phí thuần sẽ làm suy yếu hiệu quả nghiệp vụ.')
    else:
        positive.append('Lợi nhuận được duy trì qua nhiều kỳ và có đóng góp được xác nhận từ từng mảng sẽ củng cố chất lượng nguồn tích lũy vốn.')
        negative.append('Lợi nhuận suy giảm, tổn thất đầu tư hoặc tăng nghĩa vụ dự phòng vượt khả năng bổ sung vốn sẽ tạo áp lực lên hồ sơ tài chính.')
    if eq is not None:
        positive.append(f"Vốn tăng tương ứng tài sản, cải thiện bộ đệm vốn/tài sản từ mức {fmt('EquityAssets',eq,'OK')}, đồng thời đáp ứng biên thanh toán sẽ tăng sức chịu tổn thất.")
        negative.append(f"Bộ đệm vốn/tài sản suy giảm tiếp từ {fmt('EquityAssets',eq,'OK')} khi rủi ro không giảm sẽ hạn chế khả năng hấp thụ tổn thất.")
    if debt is not None and debt>0:negative.append(f"Nợ vay/vốn hiện {fmt('DebtEquity',debt,'OK')}; nợ đến hạn tăng mà không có nguồn trả tương ứng làm tăng áp lực tái cấp vốn.")
    return {'Positive':' '.join(positive),'Negative':' '.join(negative),
            'Limit':'Các điều kiện trên là độ nhạy của hồ sơ tài chính, chưa phải cam kết nâng/hạ bậc. Bậc và triển vọng cần phương pháp đúng phạm vi, dự báo và quyết định thẩm định.'}


def overall_conclusion(pack, subtype):
    p={r['Metric']:r for r in pack};period=pack[0]['Period'] if pack else 'kỳ chưa xác định'
    profit=value(p,'NPAT');cr=value(p,'CombinedRatio');equity=value(p,'EquityAssets')
    c=last_change(p.get('NPAT',{}));e=last_change(p.get('EquityAssets',{}))
    text=f'Đến {period}, '
    if profit is not None:
        text+=f"lợi nhuận sau thuế {fmt('NPAT',profit,'OK')} "+('tạo nguồn tích lũy nội bộ nếu được giữ lại.' if profit>0 else 'chưa tạo nguồn tích lũy nội bộ dương.')
    else:text+='chưa có lợi nhuận sau thuế hợp lệ để xác nhận khả năng tích lũy vốn hiện tại.'
    if c:text+=f" Năm cuối chuỗi, lợi nhuận {'tăng' if c[1].Value>c[0].Value else 'giảm' if c[1].Value<c[0].Value else 'không đổi'} so với năm trước."
    if cr is not None:
        text+=f" Tỷ lệ kết hợp {fmt('CombinedRatio',cr,'OK')} cho thấy "+('thặng dư' if cr<1 else 'thâm hụt' if cr>1 else 'hòa vốn')+' khai thác theo quy ước tính.'
    if equity is not None:
        text+=f" Vốn/tài sản tại quý là {fmt('EquityAssets',equity,'OK')}."
    aligned=aligned_changes(p,'NPAT','EquityAssets')
    if aligned and c[1].Value>c[0].Value and e[1].Value<e[0].Value:
        text+=' Sự cải thiện lợi nhuận đi cùng bộ đệm vốn tương đối giảm ở năm cuối; vì vậy chưa thể kết luận sức chịu tổn thất cải thiện đồng bộ.'
    elif aligned and c[1].Value>0 and c[1].Value>c[0].Value and e[1].Value>e[0].Value:
        text+=' Lợi nhuận và tỷ trọng vốn cùng cải thiện ở năm cuối, hỗ trợ hồ sơ tài chính trên hai phương diện tạo thu nhập và bộ đệm kế toán.'
    elif profit is not None and profit<0:
        text+=' Ưu tiên khôi phục nguồn lợi nhuận và bảo vệ vốn trước khi mở rộng rủi ro giữ lại.'
    else:text+=' Cần cân đối khả năng tạo lợi nhuận với tốc độ gia tăng nghĩa vụ và mức rủi ro đầu tư.'
    limits=[]
    if value(p,'InsuranceLiquidity') is None:limits.append('khả năng bao phủ nghĩa vụ bằng tài sản thanh khoản sau khấu trừ')
    if value(p,'SolvencyRatio') is None:limits.append('biên khả năng thanh toán')
    tail=('Điểm chưa khép kín trong kết luận là '+ ' và '.join(limits)+'. Cần bổ sung bằng chứng này trước khi đánh giá đầy đủ khả năng chi trả.' if limits else
          'Đánh giá đầy đủ khả năng chi trả còn cần dự báo, chất lượng tài sản và các điều kiện căng thẳng ngoài số liệu hiện tại.')
    if subtype in ('GROUP','LIFE','REINSURANCE'):
        tail+=' Kết luận tài chính được giữ ở phạm vi số liệu đang phân tích; bậc tín nhiệm cần phương pháp phù hợp với pháp nhân và mô hình hoạt động.'
    return [text,tail]
