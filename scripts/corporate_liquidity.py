"""Thanh khoản BCTC thực tế; quy tắc nghiên cứu riêng, không phải A/B dự phóng.

Giữ bốn chỉ tiêu/trọng số của bộ phân tích hiện có; dùng ngưỡng tuyệt đối để
việc thay peer không tự làm thay đổi mức thanh khoản. Không tạo số cho ô thiếu.
"""
import math
from decimal import Decimal

SPECS = [
    ('CurrentRatio', 'Thanh toán hiện hành', .35, (2, 1.5, 1.2, 1, .8)),
    ('CashDebt', 'Tiền và tương đương tiền / Nợ vay', .25, (.5, .3, .2, .1, .05)),
    ('CFO_Debt', 'CFO / Nợ vay', .25, (.4, .25, .15, .05, 0)),
    ('FOCF_Debt', 'Dòng tiền tự do hoạt động / Nợ vay', .15, (.25, .15, .05, 0, -.1)),
]
LEVELS = {'Rất Mạnh': 2, 'Mạnh': 1, 'Phù Hợp': 0, 'Trung Bình': 0, 'Yếu': 0}
POLICY_NOTE = ('Thanh khoản theo BCTC thực tế: số dư cuối kỳ và dòng tiền TTM kết thúc cùng kỳ. '
    'Rất Mạnh: +2 bậc; Mạnh: +1 bậc; Phù Hợp, Trung Bình và Yếu: 0 bậc. '
    'Yếu tố thanh khoản chỉ cộng hoặc giữ nguyên bậc, không trừ bậc và không áp trần hạ bậc do thanh khoản. '
    'Đây là quy tắc nghiên cứu riêng của mô hình, không phải thang đánh giá thanh khoản dự phóng của CRA.')


def finite(value):
    if isinstance(value, bool):return None
    try:value=float(value)
    except (ValueError, TypeError):return None
    return value if math.isfinite(value) else None


def assess(records, period, override=None):
    """Chỉ nhận bản ghi OK, đúng kỳ; tỷ số dòng tiền phải là TTM hoặc FY Q4."""
    def value(metric):
        r=records.get(metric,{})
        p=str(r.get('Period','')).split('|')[-1]
        if len(p)==4:p+='-Q4'
        if not period or p!=period or r.get('Status')!='OK':return None
        if metric in {'CFO_Debt','FOCF_Debt','CFO','FOCF'}:
            b=str(r.get('Basis',''))
            if 'TTM' not in b and not ('FY' in b and period.endswith('Q4')):return None
        return finite(r.get('Value'))

    observations=[];missing=[];values={}
    for metric,title,weight,thresholds in SPECS:
        v=value(metric)
        if metric in {'CurrentRatio','CashDebt'} and v is not None and v<0:v=None
        values[metric]=v
        score=next((i for i,limit in enumerate(thresholds,1) if v>=limit),6) if v is not None else None
        if score is None:missing.append(title)
        r=records.get(metric,{})
        observations.append({'Metric':metric,'Chỉ tiêu':title,'Giá trị':v,'Điểm':score,
            'Tỷ trọng':weight,'Kỳ':r.get('Period',period),'Cơ sở':r.get('Basis',''),
            'Nguồn':r.get('Source',''),'Ngưỡng điểm 1→5':' / '.join(str(x) for x in thresholds)})
    available=[r for r in observations if r['Điểm'] is not None]
    coverage=sum(r['Tỷ trọng'] for r in available)
    ready=(values['CurrentRatio'] is not None and values['CashDebt'] is not None and
           any(values[k] is not None for k in ('CFO_Debt','FOCF_Debt')) and len(available)>=3)
    score=float(sum(Decimal(str(r['Điểm']))*Decimal(str(r['Tỷ trọng'])) for r in available)/
                sum(Decimal(str(r['Tỷ trọng'])) for r in available)) if ready else None
    level='Chưa đủ dữ liệu';notches=0;status='INSUFFICIENT_DATA';origin='ACTUAL_FINANCIALS'
    reasons=[]
    if score is not None:
        level=('Rất Mạnh' if score<1.8 else 'Mạnh' if score<2.6 else 'Phù Hợp' if score<3.4 else 'Trung Bình' if score<4.2 else 'Yếu')
        # Một tỷ số đẹp không bù được mất cân đối vốn lưu động và dòng tiền âm.
        if values['CurrentRatio']<1 and values['CFO_Debt'] is not None and values['CFO_Debt']<0:
            level='Yếu';reasons.append('Thanh toán hiện hành dưới 1 lần và CFO TTM âm: không bù trừ tín hiệu căng thẳng bằng chỉ tiêu khác.')
        if LEVELS[level]>0 and (values['CurrentRatio']<1.2 or values['CFO_Debt'] is None or values['CFO_Debt']<=0 or values['CashDebt']<.2):
            level='Phù Hợp';reasons.append('Chưa đồng thời đạt điều kiện cộng bậc: hiện hành ≥1,2; tiền/nợ ≥0,2; CFO TTM dương.')
        notches=LEVELS[level];status='ASSESSED_ACTUALS'
        if missing:reasons.append('Phân bổ lại tỷ trọng trên chỉ tiêu có số liệu; thiếu '+', '.join(missing)+'.')
    elif value('TotalDebt')==0 and value('Cash') is not None and value('Cash')>=0 and values['CurrentRatio'] is not None and value('CFO') is not None:
        # Không gán tỷ số tiền/nợ = vô cực khi mẫu số bằng 0.
        cr=values['CurrentRatio'];cfo=value('CFO')
        level='Mạnh' if cr>=1.5 and cfo>0 else 'Phù Hợp' if cr>=1 and cfo>=0 else 'Yếu' if cr<1 and cfo<0 else 'Trung Bình'
        notches=LEVELS[level];status='ASSESSED_ACTUALS'
        reasons.append('Không có nợ vay tại kỳ báo cáo: đánh giá bằng thanh toán hiện hành, tiền không âm và CFO TTM; không chia cho nợ bằng 0.')
    else:
        reasons.append('Chưa đủ số liệu đúng kỳ: '+', '.join(missing)+'. Tạm giữ 0 bậc; chưa kết luận mức thanh khoản.')
    if override is not None:
        choices={k.casefold():k for k in LEVELS};choices['dưới trung bình']='Trung Bình'
        level=choices.get(str(override).strip().casefold())
        if level is None:raise ValueError('Mức thanh khoản không hợp lệ')
        notches=LEVELS[level];status='ANALYST_OVERRIDE';origin='ANALYST_OVERRIDE'
        reasons.append('Mức thanh khoản do chuyên viên nhập; thay kết quả tự động, không cộng hai lần.')
    observed='; '.join(r['Chỉ tiêu']+' '+f"{r['Giá trị']:.3f}".replace('.',',')+' lần' for r in available)
    reason=(observed+'. ' if observed else '')+' '.join(reasons)
    return {'Liquidity':level,'LiquidityScore':score,'LiquidityNotches':notches,
        'LiquidityAssessment':{'Status':status,'Origin':origin,'Period':period,'Coverage':coverage,
            'Observations':observations,'MissingMetrics':missing,'Rationale':reason,'PolicyNote':POLICY_NOTE},
        'LiquidityRationale':reason}


def assess_ticker(ticker, override=None):
    from scripts.financial_evidence import latest_period, at_period
    period=latest_period(ticker,'CORPORATE')
    records=at_period(ticker,'CORPORATE',period,'TTM') if period else {}
    return assess(records,period,override)


def display(result):
    level=result.get('Liquidity','Chưa đủ dữ liệu')
    n=result.get('LiquidityNotches')
    suffix=' (tạm giữ bậc)' if result.get('LiquidityAssessment',{}).get('Status')=='INSUFFICIENT_DATA' else ''
    if result.get('InitialRating') in (None,'N/A','') and n is not None:
        suffix=' (chưa áp dụng: thiếu bậc ban đầu)'
    return level+(f' · {n:+d} bậc' if n is not None else '')+suffix
