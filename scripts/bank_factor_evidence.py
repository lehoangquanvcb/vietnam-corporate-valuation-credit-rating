"""Đánh giá tự động có điều kiện theo cấu phần của phương pháp ngân hàng.

Ngưỡng định lượng dưới đây là quy tắc triển khai minh bạch, KHÔNG phải bảng
ngưỡng của tác giả phương pháp. Không có mức đích theo ticker; phần định tính
chưa xác nhận được nêu riêng, không suy diễn thành yếu hoặc đã thẩm định.
"""
import math
from statistics import mean, median
from scripts.bank_method_2026 import GRADES, car_grade
from scripts.bank_car import bank_universe
from scripts.financial_evidence import at_period, same_period_history

SUPPORT_TABLE = dict(zip(
 ['aaa','aa+','aa','aa-','a+','a','a-','bbb+','bbb','bbb-','bb+','bb','bb-','b+','b','b-','ccc+','ccc','ccc-','cc'],
 ['aaa','aa+','aa+','aa','aa-','aa-','aa-','a+','a','a-','bbb+','bbb','bbb-','bb+','bb','bb-','b+','b','b-','b-']))
STATE_BANKS = {'VCB','BID','CTG','AGRIBANK'}


def support_notches(ticker, sacp):
    """Bảng 13 gốc, chỉ giữ để đối chiếu; luồng báo cáo dùng bank_government_support."""
    from scripts.three_methodology_rating import SCALE
    target = SUPPORT_TABLE.get(sacp, sacp) if ticker in STATE_BANKS else sacp
    return SCALE.index(sacp) - SCALE.index(target)


def assess(ctx):
    """Bảng 4–5, 6–8 và 11: vị thế/ổn định; vốn+lợi nhuận; tổn thất+khẩu vị."""
    peers = {t:at_period(t,'BANK',ctx.period,'TTM') for t in bank_universe(ctx.ticker)}
    metrics = ['TotalAssets','GrossLoans','CustomerDeposits','OperatingIncome','NPAT',
               'ROA','ROE','CIR','NIM','EquityAssets','TangibleEquityAssets','NII_OperatingIncome',
               'NPL','LoanLossCoverage','CreditCostProxy','ProvisionOperatingIncome','Equity','CAR']
    hist = same_period_history(ctx.ticker,'BANK','FY',5,metrics=metrics)
    annual = {}
    for metric in metrics:
        annual[metric] = {r.Period:float(r.Value) for r in hist[hist.Metric.eq(metric)].itertuples()
                          if r.Status=='OK' and math.isfinite(r.Value)}
    reasons = {};details=[]
    def series(m):return list(annual[m].values())
    def growth(m):
        x=series(m)
        return x[-1]/x[-2]-1 if len(x)>=2 and x[-2]>0 else None
    def percentile(m, higher=True):
        value=ctx.value(m);own=ctx.records.get(m,{})
        if value is None:return None
        vals=[r[m]['Value'] for r in peers.values() if m in r and r[m].get('Status')=='OK'
              and r[m].get('Period')==own.get('Period') and r[m].get('Basis')==own.get('Basis')
              and isinstance(r[m].get('Value'),(float,int)) and math.isfinite(r[m]['Value'])]
        if len(vals)<5:return None
        p=(sum(v<value for v in vals)+.5*sum(v==value for v in vals))/len(vals)
        p=p if higher else 1-p
        ctx.add(m,value,None,'Đối chiếu toàn bộ ngân hàng có số cùng kỳ/cơ sở; trung vị là trung tính',len(vals))
        details.append({'Metric':m,'PercentileStrength':p,'PeerCount':len(vals),'PeerMedian':median(vals)})
        return p
    def weighted(spec):
        points=[(percentile(m,h),w) for m,w,h in spec]
        points=[(p,w) for p,w in points if p is not None]
        return sum(p*w for p,w in points)/sum(w for p,w in points) if len(points)>=2 else None
    # Quy mô được đối chiếu toàn ngành; không chấm thấp ngân hàng chỉ vì peer
    # được chọn đều lớn, và không dùng ROE để thay thế hồ sơ kinh doanh.
    position=weighted([('TotalAssets',.2,True),('GrossLoans',.2,True),
                       ('CustomerDeposits',.3,True),('OperatingIncome',.3,True)])
    incomes=series('OperatingIncome');profits=series('NPAT')
    durable=len(incomes)>=3 and all(v>0 for v in incomes[-3:])
    declines=sum(b<a for a,b in zip(incomes,incomes[1:]))
    business=(2 if position>=.70 and durable else 3) if position is not None else None
    resilient = len(incomes)>=5 and len(profits)>=5 and all(v>0 for v in profits[-5:]) and all(b>=a*.9 for a,b in zip(incomes[-5:],incomes[-4:]))
    if position is not None and position>=.90 and resilient:
        business=1
    if business and ((declines>=2 and (growth('OperatingIncome') or 0)<-.2) or (ctx.value('NPAT') is not None and ctx.value('NPAT')<0)):
        business=max(business,4)
    mix=ctx.value('NII_OperatingIncome')
    if mix is not None:ctx.add('NII_OperatingIncome',mix,None,'Cơ cấu thu nhập; không thay thế phân tích khách hàng/địa bàn/ngành cho vay')
    def pct(v):return ('—' if v is None else f'{v*100:.2f}%'.replace('.',','))
    def money(v):return ('—' if v is None else f'{v/1e9:,.1f}'.replace(',','_').replace('.',',').replace('_','.')+' tỷ đồng')
    reasons['Hồ sơ Kinh doanh']=(f'Tổng tài sản {money(ctx.value("TotalAssets"))}; tiền gửi {money(ctx.value("CustomerDeposits"))}. '
        +(f'Thu nhập hoạt động từ {money(incomes[0])} lên {money(incomes[-1])} trong {len(incomes)} năm, có {declines} năm giảm. ' if incomes else '')
        +('Vị thế thuộc nhóm dẫn đầu, lợi nhuận dương và thu nhập duy trì ổn định qua 5 năm hỗ trợ mức Rất Mạnh có điều kiện.' if business==1 else 'Quy mô và nền thu nhập ổn định hỗ trợ vị thế kinh doanh.' if business==2 else 'Quy mô được xem cùng độ ổn định thu nhập; chưa có căn cứ nâng từ mức nền.' if business==3 else 'Suy giảm thu nhập/lợi nhuận tạo áp lực lên tính ổn định hoạt động.'))
    # Bước 1: giới hạn pháp định được engine chính áp dụng. Bước 2: CAR đầu vào
    # là giả định duy trì khi chưa có forecast. Bước 3: chất lượng vốn/lợi nhuận.
    car=ctx.value('CAR');grade=car_grade(car);base=GRADES.index(grade)+1 if grade else None
    capital_proxy='TangibleEquityAssets' if ctx.value('TangibleEquityAssets') is not None else 'EquityAssets'
    scores={m:percentile(m,h) for m,h in [('ROA',True),('ROE',True),('CIR',False),('NIM',True),(capital_proxy,True)]}
    for m in ['EquityAssets','ProvisionOperatingIncome']:
        if m!=capital_proxy and ctx.value(m) is not None:ctx.add(m,ctx.value(m),None,'Bổ sung đánh giá bộ đệm vốn và khả năng hấp thụ chi phí dự phòng')
    profits_ok=len(profits)>=3 and all(v>0 for v in profits[-3:])
    favorable=sum(p is not None and p>.5 for p in scores.values())
    roa_good=scores['ROA'] is not None and scores['ROA']>=.6
    leverage_good=scores[capital_proxy] is not None and scores[capital_proxy]>=.5
    historical_roa=series('ROA')[-3:]
    sustainable_roa=len(historical_roa)==3 and median(historical_roa)>=.01 and min(historical_roa)>=.005
    # ROE thấp do đòn bẩy thấp không tự phủ nhận khả năng tạo vốn bền vững.
    sound_buffer=(ctx.value(capital_proxy) or 0)>=.10 and (ctx.value('ROA') or 0)>=.01
    car_rows=hist[hist.Metric.eq('CAR') & hist.Status.eq('OK')]
    prior_car=car_rows.iloc[-1].to_dict() if not car_rows.empty else {}
    from scripts.bank_car import comparable_metric
    car_drop=(prior_car and car is not None and comparable_metric('CAR',prior_car,ctx.records.get('CAR',{}))
              and prior_car['Value']-car>.01)
    adj=0
    if base and car>=.09 and favorable>=4 and (roa_good or sound_buffer) and leverage_good and profits_ok and sustainable_roa and not car_drop:
        adj=1
    if base and ctx.value('NPAT') is not None and ctx.value('NPAT')<=0:adj=-1
    capital=max(1 if base==1 else 2 if adj>0 else 1,min(6,base-adj)) if base else None
    reasons['Vốn và Lợi nhuận']=(f'CAR {pct(car)}: mức ban đầu {grade or "chưa có"}; ROA {pct(ctx.value("ROA"))}, '
        f'ROE {pct(ctx.value("ROE"))}, CIR {pct(ctx.value("CIR"))}, '
        +('vốn hữu hình/tài sản ' if capital_proxy=='TangibleEquityAssets' else 'VCSH/tài sản (chưa điều chỉnh tài sản vô hình) ')
        +pct(ctx.value(capital_proxy))+'. '
        +(f'ROA trung vị 3 năm {pct(median(historical_roa))}; ' if len(historical_roa)==3 else 'Thiếu chuỗi ROA 3 năm; ')
        +(f'Khả năng sinh lời bền vững và bộ đệm vốn hỗ trợ tăng {adj} mức đánh giá.' if adj>0 else 'Thua lỗ làm suy yếu khả năng tích lũy vốn.' if adj<0 else 'Chưa có đủ tín hiệu đồng thuận và bền vững để nâng mức từ CAR.'))
    # Không dùng ROA lần thứ hai để chấm rủi ro: tập trung tổn thất, dự phòng,
    # tăng trưởng và biến động chất lượng tài sản qua chu kỳ.
    risk_signal=weighted([('NPL',.45,False),('LoanLossCoverage',.35,True),('CreditCostProxy',.2,False)])
    npl=ctx.value('NPL');coverage=ctx.value('LoanLossCoverage')
    # Phân vị hiện tại chỉ là một nửa bằng chứng; nửa còn lại là lịch sử cùng năm.
    history_scores=[];history_medians={}
    for metric,weight,higher in [('NPL',.45,False),('LoanLossCoverage',.35,True)]:
        own_years=sorted(annual[metric])[-3:]
        if len(own_years)<3:continue
        own_median=median(annual[metric][year] for year in own_years)
        history_medians[metric]=own_median
        peer_medians=[]
        for t in peers:
            ph=same_period_history(t,'BANK','FY',5,metrics=[metric])
            data={row.Period:float(row.Value) for row in ph.itertuples()
                  if row.Metric==metric and row.Status=='OK' and row.Period in own_years and math.isfinite(row.Value)}
            if len(data)==3:peer_medians.append(median(data.values()))
        if len(peer_medians)<5:continue
        point=(sum(v<own_median for v in peer_medians)+.5*sum(v==own_median for v in peer_medians))/len(peer_medians)
        point=point if higher else 1-point
        history_scores.append((point,weight))
        details.append({'Metric':metric,'Window':'MEDIAN_3FY','Periods':own_years,
                        'PercentileStrength':point,'PeerCount':len(peer_medians),'OwnMedian':own_median})
    historical_risk=sum(p*w for p,w in history_scores)/sum(w for p,w in history_scores) if len(history_scores)==2 else None
    blended_risk=(risk_signal+historical_risk)/2 if risk_signal is not None and historical_risk is not None else risk_signal
    # Phân vị thấp chỉ là tín hiệu cảnh báo. Hạ bậc cần thêm dấu hiệu tổn thất,
    # dự phòng hoặc tăng trưởng bất lợi; tránh ép một tỷ lệ cố định ngân hàng vào mức yếu.
    risk=(2 if blended_risk>=.75 else 3) if blended_risk is not None and npl is not None and coverage is not None else None
    if risk==2 and (historical_risk is None or coverage<1):risk=3
    if risk==2 and risk_signal>=.90 and historical_risk>=.85 and npl<=.01 and coverage>=1.5 and history_medians.get('NPL',1)<=.015 and history_medians.get('LoanLossCoverage',0)>=1.5:
        risk=1
    npls=series('NPL');credit_growth=growth('GrossLoans');equity_growth=growth('Equity')
    if risk:
        if blended_risk<.25 and npl>.04:risk=max(risk,4)
        if npl>.03 and coverage<.5:risk=max(risk,4)
        if npl>.05 and coverage<.5:risk=max(risk,5)
        if len(npls)>=2 and npls[-1]-npls[-2]>.01:risk=max(risk,4)
        if credit_growth is not None and equity_growth is not None and credit_growth>.3 and credit_growth-equity_growth>.15:
            risk=max(risk,3)
    reasons['Vị thế Rủi ro']=(f'NPL {pct(npl)}, bao phủ nợ xấu {pct(coverage)}. '
        +(f'Trung vị 3 năm: NPL {pct(history_medians.get("NPL"))}, bao phủ {pct(history_medians.get("LoanLossCoverage"))}. ' if historical_risk is not None else 'Chưa đủ lịch sử so sánh 3 năm để xác nhận mức Mạnh. ')
        +(f'Tăng trưởng dư nợ năm cuối {pct(credit_growth)} so với vốn {pct(equity_growth)}. ' if credit_growth is not None and equity_growth is not None else '')
        +('Nợ xấu thấp và dự phòng cao được duy trì qua chu kỳ, hỗ trợ mức Rất Mạnh có điều kiện.' if risk==1 else 'Tổn thất tín dụng và mức dự phòng hỗ trợ khả năng chống chịu tương đối.' if risk==2 else
          'Cần theo dõi sức ép chuyển nhóm nợ và bổ sung dự phòng.' if risk and risk>=4 else 'Các tín hiệu tổn thất và dự phòng chưa cho thấy ưu thế đủ lớn để nâng bậc.'))
    return {'BusinessProfile':business,'CapitalEarnings':capital,'RiskPosition':risk}, {
        'Reasons':reasons,'PeerEvidence':details,'AnnualEvidence':annual,
        'CapitalStartingGrade':grade,'CapitalQualityAdjustment':adj,
        'SustainableEarningsConfirmed':sustainable_roa and profits_ok,
        'RiskCurrentSignal':risk_signal,'RiskHistoricalSignal':historical_risk,'RiskCombinedSignal':blended_risk,
        'CapitalQualityProxy':capital_proxy,
        'QualitativePending':['Quản trị và chiến lược','Tập trung khách hàng/ngành/địa bàn',
                              'Chất lượng công cụ vốn và cổ tức','Dự phóng CAR 1–2 năm','Rủi ro ngoại bảng'],
        'MethodologySource':'1. Phương pháp XHTN Ngân hàng 2026.docx; bảng 4–8, 11, 17',
        'AutomationPolicy':'Các phân vị/ngưỡng kết hợp là giả định triển khai, không phải ngưỡng do tác giả phương pháp ban hành.'}
