"""Automatic, explicitly conditional research scores for the four report routes.

The strict assessment engines remain available: an estimate must never be saved
as a reviewed assessment. Method tables and report-policy assumptions are kept
separate in Scorecard, QuantitativeEvidence and Assumptions.
"""
import math
from scripts.universal_data import get_company, peer_tickers
from scripts.financial_evidence import at_period, latest_period, comparable_model, insurance_reporting_subtype
from scripts.three_methodology_rating import rate_company as assessed_rating, SCALE, NOTCH, move, label
from scripts.bank_method_2026 import GRADES, FUNDING_GRADES, FUNDING_MATRIX, car_grade
from scripts.methodology_kpi_engine import LABELS
from scripts.bank_car import comparable_metric

RISK_KEYS = ['IndustryRisk', 'BusinessRisk', 'FinancialRisk', 'GovernanceRisk']
RISK_TITLES = ['Rủi ro Vĩ mô và Ngành', 'Rủi ro Kinh doanh', 'Rủi ro Tài chính', 'Rủi ro Quản trị và Quản lý']
DEFAULT_WEIGHTS = dict(zip(RISK_KEYS, [.20, .30, .35, .15]))


def number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def corporate_anchor(score):
    """Table 01: exact 0.3125 steps, no intermediate rounding."""
    score = number(score)
    if score is None or not 1 <= score <= 6:
        raise ValueError('Điểm rủi ro phải trong khoảng 1–6')
    for i, rating in enumerate(SCALE[:16]):
        if score <= 1 + i * .3125:
            return rating
    return 'ccc'  # CCC–C is one source band; no default event is inferred.


def threshold_risk(value, thresholds, higher_better=False):
    value = number(value)
    if value is None:
        return None
    for i, boundary in enumerate(thresholds, 1):
        if (value >= boundary if higher_better else value < boundary):
            return i
    return 6


def _clamp_grade(score):
    return max(1, min(6, int(math.floor(score + .5))))


def _cap(rating, ceiling):
    return max((rating, ceiling), key=SCALE.index)


def _notch(o, key, assumptions, lo=-6, hi=8):
    n = o.get(key)
    if n is None:
        assumptions.append({'ModifierNotches': 'Điều chỉnh bổ sung',
                            'ExternalSupportNotches': 'Hỗ trợ bên ngoài',
                            'LiquidityNotches': 'Điều chỉnh thanh khoản',
                            'OtherAdjustmentsNotches': 'Điều chỉnh khác',
                            'ComparativeNotches': 'Điều chỉnh so sánh'}.get(key, key) +
                           ': giả định 0 bậc khi chưa có đánh giá riêng; không phải kết luận đã thẩm định.')
        return 0
    if isinstance(n, bool) or not isinstance(n, int) or not lo <= n <= hi:
        raise ValueError(key + ': notch nằm ngoài phạm vi cho phép')
    return n


def _row(title, score, impact='—', result=''):
    return {'Cấu phần': title, 'Điểm / Đánh giá': str(score), 'Tác động': str(impact), 'Kết quả / Căn cứ': str(result)}


class Evidence:
    def __init__(self, ticker, typ):
        self.ticker, self.typ = ticker, typ
        self.period = latest_period(ticker, typ)
        self.meta = get_company(ticker)
        self.records = at_period(ticker, typ, self.period, 'TTM') if self.period else {}
        if typ=='BANK' and self.period:
            from scripts.financial_evidence import rating_car_record
            self.records['CAR']=rating_car_record(ticker,self.period)
        self.peers = list(dict.fromkeys(t for t in peer_tickers(ticker)
                                       if t != ticker and comparable_model(self.meta, get_company(t)))) if self.period else []
        self.peer_records = {}
        self.rows = []

    def value(self, metric):
        if metric == 'EBITDAInterest':
            ebitda, interest = self.value('EBITDA'), self.value('InterestExpense')
            return ebitda/abs(interest) if ebitda is not None and interest is not None and interest != 0 else None
        r = self.records.get(metric, {})
        # Ngoại lệ CAR cuối 2025 chỉ được bộ chọn nguồn chung phê chuẩn cho Q2/2026.
        allowed_car=(metric=='CAR' and self.typ=='BANK' and r.get('FallbackUsed') is True
                     and r.get('UsePeriod')==self.period=='2026-Q2' and r.get('Period')=='2025-Q4')
        if r.get('Status') != 'OK' or (not str(r.get('Period', '')).split('|')[-1] == self.period and not allowed_car):
            return None
        return number(r.get('Value'))

    def add(self, metric, value, score=None, rule='', count=None):
        r = self.records.get(metric, {})
        if metric == 'EBITDAInterest':
            r = self.records.get('EBITDA', {})
        names={'EBITDAInterest':'EBITDA / Chi phí lãi vay','LiabilitiesEquity':'Nợ phải trả / Vốn chủ sở hữu','PaidInCapital':'Vốn thực góp'}
        self.rows.append({'Metric':metric, 'Chỉ tiêu': names.get(metric,LABELS.get(metric, metric)), 'Giá trị': value,
                          'Điểm': score, 'Cách chấm': rule, 'Kỳ': r.get('Period', self.period),
                          'Cơ sở': r.get('Basis', ''), 'Số peer': count, 'Nguồn': r.get('Source', '')})

    def peer_score(self, specs):
        total = weight = 0.0
        count = 0
        for metric, w, higher in specs:
            value = self.value(metric)
            own = self.records.get(metric, {})
            if value is None:
                continue
            values = []
            for t in self.peers:
                if t not in self.peer_records:
                    self.peer_records[t] = at_period(t, self.typ, self.period, 'TTM')
                r = self.peer_records[t].get(metric, {})
                v = number(r.get('Value'))
                if (v is not None and r.get('Status') == 'OK' and r.get('Period') == own.get('Period')
                        and r.get('Basis') == own.get('Basis') and comparable_metric(metric,own,r)):
                    values.append(v)
            if len(values) < 3:
                continue
            # Midrank prevents identical peers from all receiving the best grade.
            percentile = (sum(v < value for v in values) + .5 * sum(v == value for v in values)) / len(values)
            score = 6 - 5 * (percentile if higher else 1 - percentile)
            total += w * score
            weight += w
            count += 1
            self.add(metric, value, score, 'Điểm tương đối 1–6; phân vị trong peer cùng kỳ/cơ sở (quy tắc tự động)', len(values))
        return (total / weight if count >= 2 and weight >= .4 else None)


def _base(ticker, typ, ctx, strict):
    return {**strict, 'Ticker': ticker, 'Methodology': typ, 'Period': ctx.period,
            'RatingStatus': 'ESTIMATED', 'RatingOrigin': 'AUTO_RESEARCH',
            'AssessmentComplete': False, 'ProvisionalAutoScoring': True,
            'DataSufficientForAutoRating': True, 'MissingEvidence': {},
            'RatingBlocker': None, 'Assumptions': [], 'QuantitativeEvidence': ctx.rows,
            'PeerCount': len(ctx.peers), 'Scorecard': [],
            'Outlook': 'Chưa đánh giá',
            'RatingBasisNote': 'Bậc ước tính tự động theo số liệu và các giả định công bố; chưa phải kết quả thẩm định.',
            'Audit': 'Bảng phương pháp gốc quyết định Anchor/notch; quy tắc định lượng thay thế và giả định được công bố riêng.'}


def _missing(r, text, missing=None):
    r.update(ICR='N/A', SCA='N/A', SACP='N/A', RatingStatus='INSUFFICIENT_DATA',
             DataSufficientForAutoRating=False, RatingBlocker='INPUTS',
             MissingEvidence=missing or {'FinancialInputs': text},
             RatingBasisNote='Các cấu phần có đủ đầu vào vẫn được tính riêng; chưa đủ căn cứ tổng hợp bậc xếp hạng.')
    r['Scorecard'].append(_row('Kết quả', 'Chưa đủ căn cứ tổng hợp', '—', text))
    return r


def _finish(r, anchor, sca, support, outlook=None):
    r.update(Anchor=label(anchor), SCA=label(sca), SACP=label(sca), ICR=label(move(sca, support)),
             InternalNotches=SCALE.index(anchor)-SCALE.index(sca), ExternalSupportNotches=support)
    if outlook and outlook not in ('Chưa thẩm định', 'Chưa xác định'):
        r['Outlook'] = outlook
    r['Scorecard'].extend([
        _row('Anchor', label(anchor), 'Điểm khởi đầu'),
        _row('SACP / SCA', label(sca), f"{r['InternalNotches']:+d} bậc", 'Sau điều chỉnh nội tại và giới hạn'),
        _row('Hỗ trợ bên ngoài', support, f'{support:+d} bậc', 'Đánh giá nhập riêng hoặc giả định 0 bậc'),
        _row('Bậc xếp hạng ước tính', r['ICR'], 'SCA + hỗ trợ', 'Triển vọng: '+r['Outlook'])])
    r['EvidenceMetrics'] = list(dict.fromkeys(x['Chỉ tiêu'] for x in r['QuantitativeEvidence']))
    return r


def _corporate(ticker, o, ctx, strict):
    r = _base(ticker, 'CORPORATE', ctx, strict)
    a = r['Assumptions']
    business = number(o.get('BusinessRisk'))
    if business is None:
        business = ctx.peer_score([('Revenue', .18, True), ('TotalAssets', .12, True),
            ('AssetTurnover', .18, True), ('GrossMargin', .18, True), ('EBITDAMargin', .20, True), ('ROA', .14, True)])
        a.append('Điểm kinh doanh tự động dùng quy mô, hiệu quả và sinh lợi tương đối với peer; chưa thay thế đánh giá thương hiệu, đa dạng hóa và vị thế cạnh tranh định tính.')
    financial = number(o.get('FinancialRisk'))
    debt, ebitda, cfo = ctx.value('TotalDebt'), ctx.value('EBITDA'), ctx.value('CFO')
    benchmarks = [
        ('DebtEBITDA', .40, [1.5, 2, 3, 4, 5], False),
        ('FFO_Debt', .20, [.60, .45, .30, .20, .12], True),
        ('EBITDAInterest', .10, [13, 9, 6, 3, 2], True),
        ('CFO_Debt', .15, [.50, .35, .25, .15, .10], True),
        ('FOCF_Debt', .15, [.40, .25, .15, .10, .05], True)]
    scores = []
    if financial is None:
        for metric, weight, limits, higher in benchmarks:
            v = ctx.value(metric)
            if metric == 'DebtEBITDA' and debt is not None and debt > 0 and ebitda is not None and ebitda <= 0:
                grade = 6
                ctx.add(metric, None, grade, 'EBITDA không dương và có nợ vay: rủi ro 6; không coi tỷ số âm là tốt')
            else:
                grade = threshold_risk(v, limits, higher)
                if grade is not None:
                    ctx.add(metric, v, grade, 'Ngưỡng tuyệt đối Phụ lục 2; tại biên chọn mức rủi ro cao hơn với Nợ/EBITDA')
            if grade is not None:
                scores.append((grade, weight))
        if len(scores) >= 2:
            financial = max(1.0,min(6.0,sum(s*w for s,w in scores) / sum(w for _,w in scores)))
        elif debt == 0 and cfo is not None:
            financial = 2.0 if cfo >= 0 else 4.0
            a.append('Không có nợ vay: điểm tài chính quy ước 2 nếu CFO không âm, 4 nếu CFO âm; đây là quy tắc tự động riêng, không phải một ngưỡng trong phương pháp.')
        a.append('Trọng số nội bộ điểm tài chính: Nợ/EBITDA 40%, FFO/Nợ 20%, EBITDA/lãi vay 10%, CFO/Nợ 15%, FOCF/Nợ 15%; phân bổ lại trên chỉ tiêu thực có. Đây là cấu hình mô hình, không phải trọng số công bố trong phương pháp.')
    industry, governance = number(o.get('IndustryRisk')), number(o.get('GovernanceRisk'))
    if industry is None:
        industry = 3.0
        a.append('Rủi ro vĩ mô/ngành: giả định trung tính 3/6; chưa có báo cáo đánh giá ngành riêng.')
    if governance is None:
        governance = 3.0
        a.append('Quản trị/quản lý: giả định 3/6, không phải xác nhận chất lượng quản trị của doanh nghiệp.')
    w = dict(o.get('Weights') or DEFAULT_WEIGHTS)
    if set(w) != set(RISK_KEYS) or any(number(x) is None or x < 0 for x in w.values()) or abs(sum(w.values())-1) > 1e-8:
        raise ValueError('Trọng số bốn cấu phần phải không âm và tổng bằng 1')
    a.append('Trọng số bốn cấu phần ngành/kinh doanh/tài chính/quản trị lần lượt '+
             '/'.join(f'{w[k]:.0%}' for k in RISK_KEYS)+': cấu hình kế thừa của ứng dụng, chưa phải trọng số ngành KCF được xác nhận.')
    a.append('Sử dụng dữ liệu thực tế đến kỳ báo cáo; chưa có dự báo hai năm nên không lập giả số cho trọng số dự phóng của phương pháp.')
    if business is None or financial is None:
        return _missing(r, 'Cần ít nhất hai chỉ tiêu kinh doanh cùng kỳ với ≥3 peer và hai chỉ tiêu trả nợ/dòng tiền, hoặc dữ liệu xác nhận không có nợ vay.')
    values = [industry, business, financial, governance]
    if any(not 1 <= v <= 6 for v in values):
        raise ValueError('Điểm cấu phần phải thuộc thang 1–6')
    weighted = sum(v*w[k] for k,v in zip(RISK_KEYS, values))
    anchor = corporate_anchor(weighted)
    modifier = _notch(o, 'ModifierNotches', a)
    sca = move(anchor, modifier)
    caps = []
    if governance >= 4:
        ceiling = 'b' if governance >= 6 else 'bb-' if governance >= 5 else 'bb+'
        sca = _cap(sca, ceiling);caps.append('Quản trị: '+label(ceiling))
    # Forward-looking liquidity cannot be inferred from current ratio alone.
    liquidity = o.get('LiquidityAssessment')
    if liquidity == 'Yếu':
        sca = _cap(sca, 'b-');caps.append('Thanh khoản yếu: vnB-')
    elif liquidity == 'Dưới trung bình':
        if SCALE.index(sca) < SCALE.index('bb+'):
            sca = 'bb+'
        elif SCALE.index(sca) <= SCALE.index('bb-'):
            sca = move(sca, -1)
    elif liquidity in ('Mạnh','Rất Mạnh') and SCALE.index(anchor) >= SCALE.index('b+') and o.get('FinancialPolicyWeak') is False:
        sca = move(sca, 1)
    elif liquidity is None:
        a.append('Thanh khoản: chưa có dự báo nguồn/sử dụng tiền và điều khoản nợ; giả định 0 bậc, không tự tăng bậc từ Current Ratio.')
    support = _notch(o, 'ExternalSupportNotches', a, 0, 8)
    from scripts.three_methodology_rating import _risk_label
    r.update(RiskScores=dict(zip(RISK_TITLES,values)), RiskLabels={k:_risk_label(v) for k,v in zip(RISK_TITLES,values)},
             Weights=w, WeightedScore=weighted, ModifierNotches=modifier, RatingCaps=caps,
             Liquidity=liquidity or 'Chưa có đánh giá dự phóng', LiquidityScore=None)
    for key,title,v in zip(RISK_KEYS,RISK_TITLES,values):
        r['Scorecard'].append(_row(title, f'{v:.3f}/6', f'{w[key]:.0%}', f'Đóng góp {v*w[key]:.4f}'))
    r['Scorecard'].append(_row('Điểm có trọng số', f'{weighted:.4f}/6', 'Bảng 01', label(anchor)))
    r['Scorecard'].append(_row('Điều chỉnh / giới hạn', modifier, f'{modifier:+d} bậc', '; '.join(caps) or 'Không áp giới hạn bổ sung trong kịch bản'))
    return _finish(r, anchor, sca, support, o.get('Outlook'))


def securities_capital(leverage=None, capital_ratio=None, debt_ebitda=None):
    """Source capital benchmarks; conservative worst available benchmark."""
    grades = []
    if number(leverage) is not None and leverage >= 0:
        grades.append(2 if leverage < 1 else 3 if leverage < 2.5 else 4 if leverage < 4 else 5 if leverage < 5 else 6)
    if number(capital_ratio) is not None:
        grades.append(2 if capital_ratio > 5.5 else 3 if capital_ratio >= 4 else 4 if capital_ratio >= 2.5 else 5 if capital_ratio >= 1.8 else 6)
    if number(debt_ebitda) is not None:
        grades.append(3 if 0 <= debt_ebitda < 3 else 4 if debt_ebitda < 4 and debt_ebitda >= 0 else 5 if 4 <= debt_ebitda < 6 else 6)
    return max(grades) if grades else None


def _financial_institution(ticker, typ, o, ctx, strict):
    r = _base(ticker, typ, ctx, strict);a = r['Assumptions']
    anchor = 'a-' if typ == 'BANK' else move('a-', -2)
    factors, notches = {}, {}
    missing = {}
    r.update(Anchor=label(anchor), Factors=factors, FactorNotches=notches,
             InternalNotches=None, BICRAReference=label('a-'),
             SectorAnchorAdjustment=-2 if typ=='SECURITIES' else 0)
    business = ctx.peer_score([('TotalAssets', .4, True), ('Revenue', .3, True), ('ROE', .3, True)])
    keys = [('BusinessProfile','Hồ sơ Kinh doanh'),('CapitalEarnings','Vốn và Lợi nhuận'),('RiskPosition','Vị thế Rủi ro')]
    auto = {'BusinessProfile': _clamp_grade(business) if business is not None else None}
    if typ == 'SECURITIES':
        assets, equity = ctx.value('TotalAssets'), ctx.value('Equity')
        leverage = (assets-equity)/equity if assets is not None and equity is not None and equity > 0 else None
        capital = ctx.value('AvailableCapitalRatio')
        auto['CapitalEarnings'] = securities_capital(leverage, capital, ctx.value('DebtEBITDA'))
        if equity is not None and equity <= 0:
            auto['CapitalEarnings'] = 6
        ctx.add('LiabilitiesEquity', leverage, auto['CapitalEarnings'], 'Tổng nợ phải trả/VCSH = (Tổng tài sản−VCSH)/VCSH; không dùng riêng nợ vay')
        if capital is not None:
            ctx.add('AvailableCapitalRatio', capital, None, 'Ngưỡng vốn khả dụng trong phương pháp chứng khoán')
        risk = ctx.peer_score([('DebtEquity', .5, False),('ROA', .25, True),('CurrentRatio', .25, True)])
        a.append('Vốn/lợi nhuận lấy mức yếu nhất trong các benchmark có số: tổng nợ phải trả/VCSH, vốn khả dụng, Nợ/EBITDA. Cách gộp thận trọng là quy tắc tự động; phần thiếu không được coi là đạt ngưỡng.')
        if capital is None:
            a.append('Chưa có tỷ lệ vốn khả dụng cùng kỳ: chưa xác nhận mức tuân thủ vốn pháp định.')
    else:
        car = ctx.value('CAR')
        grade = car_grade(car)
        auto['CapitalEarnings'] = GRADES.index(grade)+1 if grade else None
        if car is not None:
            from scripts.bank_car import car_usage_text
            car_record=getattr(ctx,'records',{}).get('CAR',{})
            r['CARInput']=car_record
            usage=car_usage_text(car_record,ctx.period)
            ctx.add('CAR', car, auto['CapitalEarnings'], 'Bảng CAR ngân hàng; '+(usage or 'giả định giữ nguyên CAR đầu vào'))
            if car_record.get('FallbackUsed') or car_record.get('SourceKind') in {'USER_PROVIDED','USER_ESTIMATE'}:
                a.append(usage)
        risk = ctx.peer_score([('NPL', .5, False), ('LoanLossCoverage', .3, True), ('ROA', .2, True)])
        a.append('Vốn/lợi nhuận: giả định CAR đầu vào được chọn duy trì, điều chỉnh chất lượng vốn 0 bậc; không tạo CAR dự báo. Kỳ và loại nguồn được nêu trong căn cứ chấm điểm.')
    auto['RiskPosition'] = _clamp_grade(risk) if risk is not None else None
    for key,title in keys:
        grade = o.get(key)
        origin = 'Đánh giá nhập riêng'
        # Retain partial saved/manual decisions, including a forecast-CAR decision
        # already resolved by the strict bank engine. Never replace these with a proxy.
        inherited = (strict.get('Factors') or {}).get(title)
        inherited_notch = (strict.get('FactorNotches') or {}).get(title)
        if grade not in NOTCH and inherited in NOTCH and inherited_notch is not None:
            grade = inherited
            origin = 'Bảng chấm đã lưu / đánh giá nhập riêng'
        if grade not in NOTCH:
            score = auto[key]
            if score is None:
                reason = ('Thiếu CAR hợp lệ tại '+ctx.period+'; cần CAR cùng kỳ hoặc kết luận vốn/lợi nhuận có căn cứ.'
                          if typ=='BANK' and key=='CapitalEarnings' else
                          'Thiếu đầu vào định lượng cùng kỳ cho '+title+'; cần bổ sung số liệu hoặc đánh giá riêng.')
                missing[key] = reason
                r['Scorecard'].append(_row(title, 'Thiếu đầu vào', '—', reason))
                continue
            grade = GRADES[score-1]
            origin = 'Tín hiệu định lượng tự động'
        n = o.get(key+'Notches', inherited_notch if origin.startswith('Bảng chấm') else NOTCH[grade])
        allowed = {'Yếu':{-2,-3},'Rất Yếu':{-4,-5}}.get(grade,{NOTCH[grade]})
        if isinstance(n,bool) or n not in allowed:
            raise ValueError('Notch không phù hợp mức đánh giá '+key)
        factors[title] = grade;notches[title] = n
        r['Scorecard'].append(_row(title, f'{GRADES.index(grade)+1}/6 • {grade}', f'{n:+d} bậc', origin))
    a.append('Hồ sơ kinh doanh/vị thế rủi ro tự động dùng các chỉ tiêu tương đối với peer; các nhận định quản trị, tập trung và đa dạng hóa chưa được xác nhận riêng.')
    title = 'Huy động vốn và Thanh khoản' if typ == 'BANK' else 'Nguồn vốn và Thanh khoản'
    n = None
    if o.get('FundingLiquidity') in NOTCH:
        grade = o['FundingLiquidity'];n = o.get('FundingLiquidityNotches',min(1,NOTCH[grade]))
        allowed = {'Yếu':{-2,-3},'Rất Yếu':{-4,-5}}.get(grade,{min(1,NOTCH[grade])})
        if isinstance(n,bool) or n not in allowed:
            raise ValueError('Notch nguồn vốn/thanh khoản không phù hợp')
        funding_reason = 'Đánh giá tổng hợp nhập riêng'
    elif title in (strict.get('FactorNotches') or {}):
        grade = strict['Factors'][title]
        n = strict['FactorNotches'][title]
        funding_reason = 'Bảng chấm đã lưu / đánh giá nhập riêng'
    else:
        if typ == 'SECURITIES':
            debt_eq, current = ctx.value('DebtEquity'), ctx.value('CurrentRatio')
            f = 'Phù Hợp' if debt_eq is not None and debt_eq < 2.5 else 'Trung Bình' if debt_eq is not None and debt_eq < 4 else 'Yếu' if debt_eq is not None else None
            l = 'Mạnh' if current is not None and current >= 2 else 'Phù Hợp' if current is not None and current >= 1.2 else 'Trung Bình' if current is not None and current >= 1 else 'Yếu' if current is not None else None
            a.append('Nguồn vốn/thanh khoản: quy tắc thay thế dùng Nợ vay/VCSH (<2,5; <4) và thanh toán hiện hành (≥2; ≥1,2; ≥1); sau đó áp ma trận notch. Đây không phải đánh giá kỳ hạn nguồn vốn đầy đủ.')
            funding_inputs = [('DebtEquity', debt_eq), ('CurrentRatio', current)]
        else:
            casa, ldr = ctx.value('CASA'), ctx.value('LDR')
            f = 'Mạnh' if casa is not None and casa >= .3 else 'Phù Hợp' if casa is not None and casa >= .15 else 'Trung Bình' if casa is not None else None
            l = 'Phù Hợp' if ldr is not None and ldr <= 1 else 'Trung Bình' if ldr is not None and ldr <= 1.2 else 'Yếu' if ldr is not None else None
            a.append('Nguồn vốn/thanh khoản: tín hiệu thay thế từ CASA và LDR, không tự cộng ngoại lệ +1; chưa thay thế đánh giá nguồn vốn bán buôn và dòng tiền stress.')
            funding_inputs = [('CASA', casa), ('LDR', ldr)]
        f, l = o.get('Funding',f), o.get('Liquidity',l)
        r.update(Funding=f if f in FUNDING_GRADES else None, Liquidity=l if l in FUNDING_GRADES else None)
        for key, value in funding_inputs:
            if value is not None:
                ctx.add(key, value, None, 'Tín hiệu thay thế huy động/thanh khoản; notch theo ma trận, không cộng điểm riêng')
        for key, value, metric in [('Funding', f, funding_inputs[0][0]), ('Liquidity', l, funding_inputs[1][0])]:
            if value not in FUNDING_GRADES:
                missing[key] = 'Thiếu '+metric+' hợp lệ tại '+ctx.period+' hoặc đánh giá riêng về '+('huy động vốn.' if key=='Funding' else 'thanh khoản.')
        if f in FUNDING_GRADES and l in FUNDING_GRADES:
            n = FUNDING_MATRIX[FUNDING_GRADES.index(f)][FUNDING_GRADES.index(l)]
            if n > 0 and o.get('FundingStrongExceptionConfirmed') is not True:
                n = 0;a.append('Không cộng ngoại lệ nguồn vốn mạnh khi chưa có bằng chứng xác nhận điều kiện ngoại lệ.')
        grade = (f if f in FUNDING_GRADES else 'Thiếu đầu vào huy động')+' / '+(l if l in FUNDING_GRADES else 'Thiếu đầu vào thanh khoản')
        funding_reason = 'Huy động / Thanh khoản; áp ma trận từ đánh giá nhập riêng và/hoặc tín hiệu định lượng tự động'
    if n is not None:
        factors[title]=grade;notches[title]=n
    r['Scorecard'].append(_row(title, grade, f'{n:+d} bậc' if n is not None else '—', funding_reason))
    support_inputs = dict(o)
    if support_inputs.get('ExternalSupportNotches') is None and strict.get('ExternalSupportNotches') is not None:
        support_inputs['ExternalSupportNotches'] = strict['ExternalSupportNotches']
    support = _notch(support_inputs, 'ExternalSupportNotches', a, 0, 8)
    r['ExternalSupportNotches'] = support
    r['ExternalSupportAssumed'] = support_inputs.get('ExternalSupportNotches') is None
    outlook = o.get('Outlook') or strict.get('Outlook')
    if outlook not in (None, '', 'Chưa xác định', 'Chưa thẩm định'):
        r['Outlook'] = outlook
    if missing:
        r['Scorecard'].extend([
            _row('Anchor', label(anchor), 'Điểm khởi đầu'),
            _row('Hỗ trợ bên ngoài', support, f'{support:+d} bậc', 'Giả định 0 bậc; chưa thẩm định' if r['ExternalSupportAssumed'] else 'Bảng chấm đã lưu / đánh giá nhập riêng')])
        r['EvidenceMetrics'] = list(dict.fromkeys(x['Chỉ tiêu'] for x in r['QuantitativeEvidence']))
        return _missing(r, ' '.join(missing.values()), missing)
    sca = move(anchor,sum(notches.values()))
    if typ == 'SECURITIES' and SCALE.index(sca)>SCALE.index('b-') and o.get('DefaultEventConfirmed') is not True:
        sca='b-'
        r['Scorecard'].append(_row('Sàn của phương pháp', 'vnB-', 'Giới hạn', 'Không áp sàn khi đã xác nhận sự kiện vỡ nợ'))
    regulatory = o.get('RegulatoryCapitalStatus')
    if regulatory in ('BREACH','SPECIAL_CONTROL'):
        sca = _cap(sca,'b-')
    elif regulatory == 'AT_RISK':
        sca = _cap(sca,'bb+')
    inherited_cap = strict.get('RegulatoryCap')
    for ceiling in SCALE:
        if inherited_cap == label(ceiling):
            sca = _cap(sca, ceiling)
            break
    return _finish(r,anchor,sca,support,outlook)


def _insurance(ticker,o,ctx,strict):
    from scripts.insurance_rating import MATRIX_1, MATRIX_2
    from scripts.insurance_methodology import capital_grade, capital_earnings, governance_result
    r=_base(ticker,'INSURANCE',ctx,strict);a=r['Assumptions']
    business=number(o.get('BusinessRisk'))
    if business is None:
        score=ctx.peer_score([('NetInsurancePremium',.25,True),('ROE',.30,True),('ROA',.15,True),('CombinedRatio',.30,False)])
        if score is None:return _missing(r,'Thiếu chỉ tiêu kinh doanh/peer phi nhân thọ cùng kỳ.')
        business=_clamp_grade(score)
        combined=ctx.value('CombinedRatio')
        if combined is not None and combined>1:business=max(3,business)
        a.append('Điểm kinh doanh 1–6 ước tính từ quy mô phí, ROE, ROA và tỷ lệ kết hợp so với peer phi nhân thọ; chưa thay thế đánh giá thị phần toàn thị trường, thương hiệu và phân phối.')
    macro=o.get('MacroIndustryRisk')
    if macro is None:
        macro=3;a.append('Rủi ro vĩ mô/ngành: giả định trung tính 3/6 khi chưa có đánh giá riêng.')
    capital=o.get('CapitalAdequacy');paid=ctx.value('PaidInCapital');required=ctx.value('RequiredCapital')
    if capital is None:
        if paid is None or paid<=0:return _missing(r,'Chưa có vốn thực góp hợp lệ để chấm an toàn vốn.')
        reference=required
        if reference is None or reference<=0:
            reference=number(o.get('ResearchCapitalReference',500e9))
            if reference is None or reference<=0:raise ValueError('Mức vốn tham chiếu nghiên cứu phải dương')
            a.append(f'An toàn vốn dùng mẫu số kịch bản {reference/1e9:,.0f} tỷ đồng; đây không phải vốn pháp định đã xác minh cho giấy phép của doanh nghiệp. Giữ nguyên vốn thực góp hiện tại, không lập giả dự báo hai năm.')
        ratio=paid/reference;capital=capital_grade(ratio)
        if capital is None:
            # Source intervals overlap at exact boundaries: choose the weaker band explicitly.
            capital=next((i for i,b in enumerate([4,3.5,3,2.5,2,1.5,1],1) if ratio>b),8)
            a.append('Tại điểm biên của Bảng 12, kịch bản chọn mức rủi ro cao hơn do cách diễn đạt nguồn chồng lấn.')
        ctx.add('PaidInCapital',paid,capital,f'Bảng 12: vốn thực góp / mẫu số {reference/1e9:,.0f} tỷ = {ratio:.3f} lần')
        r['CapitalReferenceAmount']=reference;r['CapitalReferenceIsAssumption']=required is None
    model=o.get('ModelRepresentativeness') or 'Trung lập'
    if not o.get('ModelRepresentativeness'):a.append('Tính đại diện mô hình vốn: giả định trung lập, không điều chỉnh điểm vốn.')
    capscore=capital_earnings(capital,model)
    adjustment=o.get('FinancialAdjustment')
    if adjustment is None:
        adjustment=0;a.append('Vị thế rủi ro và linh hoạt tài chính: giả định tổng điều chỉnh 0 điểm; chưa xác nhận chất lượng danh mục đầu tư và khả năng tiếp cận vốn.')
    fin=max(1,min(10,capscore+(0 if capscore<=3 and adjustment<0 else adjustment)))
    quality=o.get('AssetQuality')
    if quality in ('BBB','BB','B+ trở xuống'):fin=max(fin,{'BBB':3,'BB':7,'B+ trở xuống':8}[quality])
    if o.get('RegulatoryRisk')=='Đáng kể':fin=10
    if o.get('InvestmentStress') and o.get('RiskPosition')==5:fin=max(8,fin)
    if quality is None:a.append('Chưa có xếp hạng chất lượng tài sản: kịch bản chưa áp giới hạn chất lượng danh mục; không coi đây là danh mục đạt trên BBB.')
    combined=MATRIX_1[int(macro)-1][int(business)-1]
    if isinstance(combined,tuple):
        if o.get('CombinedRiskSelection') is not None and o['CombinedRiskSelection'] not in combined:
            raise ValueError('Lựa chọn ma trận 01 không thuộc ô tương ứng')
        combined=o.get('CombinedRiskSelection') or max(combined)
        a.append('Ô ma trận 01 có hai lựa chọn: mặc định lấy điểm rủi ro cao hơn nếu chưa có lựa chọn riêng.')
    raw=MATRIX_2[combined-1][fin-1]
    r.update(CombinedRiskScore=combined,CapitalEarningsScore=capscore,FinancialRiskScore=fin,BusinessRiskScore=business)
    for title,v,rule in [('Rủi ro ngành',macro,'Giả định/đánh giá 1–6'),('Rủi ro kinh doanh',business,'Điểm 1–6'),
        ('Rủi ro tổng hợp',combined,'Ma trận 01'),('An toàn vốn',capital,'Bảng 12'),('Vốn và lợi nhuận',capscore,'Sau tính đại diện mô hình'),
        ('Rủi ro tài chính',fin,'Điều chỉnh tài chính và giới hạn')]:r['Scorecard'].append(_row(title,v,'Điểm',rule))
    if raw is None:return _missing(r,'Ma trận 02 không quy định bậc cho tổ hợp này; không ngoại suy.')
    if isinstance(raw,tuple):
        selected=str(o.get('AnchorSelection','')).lower().replace('vn','')
        options=[x for x in raw if x in SCALE]
        if selected and selected not in options and not ('lower' in raw and selected in SCALE and SCALE.index(selected)>SCALE.index('b-')):
            raise ValueError('Lựa chọn Anchor không thuộc ô ma trận 02')
        if 'lower' in raw and not selected:
            return _missing(r,'Ô ma trận B-/thấp hơn cần đánh giá riêng về khả năng vỡ nợ.')
        anchor=selected if selected else max(options,key=SCALE.index)
        a.append('Ô ma trận 02 có hai bậc: chọn bậc thấp hơn nếu chưa có lựa chọn riêng.')
    else:anchor=raw
    management=o.get('ManagementAssessment') or 'Trung bình';policy=o.get('FinancialPolicyAssessment') or 'Trung bình'
    if not o.get('ManagementAssessment') or not o.get('FinancialPolicyAssessment'):
        a.append('Quản trị/chính sách tài chính: giả định Trung bình cho phần chưa được đánh giá; áp đúng ma trận 16–17, không mặc định tác động 0 bậc.')
    level,sca=governance_result(anchor,management,policy)
    if sca is None:return _missing(r,'Bảng 17 không có hàng tương ứng với Anchor.')
    r['Scorecard'].append(_row('Quản trị / chính sách tài chính',level,f'{SCALE.index(anchor)-SCALE.index(sca):+d} bậc','Bảng 16–17: '+label(sca)))
    for key in ['LiquidityNotches','OtherAdjustmentsNotches','ComparativeNotches']:
        n=_notch(o,key,a,-8 if key=='LiquidityNotches' else -1,0 if key=='LiquidityNotches' else 1)
        sca=move(sca,n);r['Scorecard'].append(_row({'LiquidityNotches':'Thanh khoản','OtherAdjustmentsNotches':'Điều chỉnh khác','ComparativeNotches':'So sánh xếp hạng'}[key],n,f'{n:+d} bậc'))
    if o.get('RegulatoryRisk')=='Đáng kể':sca=_cap(sca,'b+')
    if (management=='Yếu' and policy=='Yếu') or o.get('GovernanceHarmful') is True:sca=_cap(sca,'bb')
    support=_notch(o,'ExternalSupportNotches',a,0,18)
    return _finish(r,anchor,sca,support,o.get('Outlook'))


def rate_company(ticker, overrides=None):
    ticker=str(ticker).strip().upper();o={k:v for k,v in dict(overrides or {}).items() if v is not None}
    strict=assessed_rating(ticker,o)
    typ=strict.get('Methodology')
    # Confirmed/saved bank and insurance assessments always take precedence.
    if typ in ('BANK','INSURANCE') and strict.get('ICR') not in (None,'','N/A'):
        return strict
    if typ=='EXCLUDED_SPECIALIZED' or strict.get('RatingBlocker') in ('SCOPE','MATRIX'):
        return strict
    ctx=Evidence(ticker,typ)
    if not ctx.period:
        return _missing(_base(ticker,typ,ctx,strict),'Không có kỳ BCTC hợp lệ; không tự gán điểm hoặc bậc.')
    if typ=='CORPORATE':return _corporate(ticker,o,ctx,strict)
    if typ in ('BANK','SECURITIES'):return _financial_institution(ticker,typ,o,ctx,strict)
    if typ=='INSURANCE':return _insurance(ticker,o,ctx,strict)
    return strict
