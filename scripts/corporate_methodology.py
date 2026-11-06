"""Doanh nghiệp phi tài chính: bốn điểm × tỷ trọng → tổng điểm → bậc.

Bảng 01 trong phương pháp 17/07/2025 dùng bước 0,3125. Không có bậc ngành
cố định để cộng/trừ điểm cấu phần. Các điều chỉnh được áp sau phép tổng hợp.
"""
from decimal import Decimal, InvalidOperation
import math

RISK_KEYS = ['IndustryRisk','BusinessRisk','FinancialRisk','GovernanceRisk']
RISK_TITLES = ['Rủi ro Vĩ mô và Ngành','Rủi ro Kinh doanh','Rủi ro Tài chính','Rủi ro Quản trị và Quản lý']
DEFAULT_WEIGHTS = dict(zip(RISK_KEYS,[.20,.30,.35,.15]))
SCALE = ['aaa','aa+','aa','aa-','a+','a','a-','bbb+','bbb','bbb-','bb+','bb','bb-','b+','b','b-','ccc','cc','c']
AUDIT = 'Bốn nhóm rủi ro × tỷ trọng → Tổng điểm không làm tròn trung gian → Bậc xếp hạng ban đầu theo Bảng 01 → Điều chỉnh có căn cứ (nếu có) → Kết quả xếp hạng.'
WEIGHT_NOTE = 'Tỷ trọng 20%/30%/35%/15% là cấu hình nghiên cứu kế thừa; tài liệu phương pháp yêu cầu tỷ trọng theo ngành/KCF, chưa có bộ tỷ trọng ngành được xác nhận trong hồ sơ này.'


def _decimal(value, name):
    if isinstance(value,bool):raise ValueError(name+': không nhận giá trị đúng/sai')
    try:d=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError):raise ValueError(name+': phải là số hữu hạn')
    if not d.is_finite():raise ValueError(name+': phải là số hữu hạn')
    return d


def validated_weights(weights=None):
    w=dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(w)!=set(RISK_KEYS):raise ValueError('Phải có đủ tỷ trọng của bốn nhóm rủi ro')
    values={k:_decimal(w[k],k) for k in RISK_KEYS}
    if any(v<0 for v in values.values()) or abs(sum(values.values())-1)>Decimal('1e-12'):
        raise ValueError('Tỷ trọng phải không âm và tổng bằng 100%')
    return {k:float(v/sum(values.values())) for k,v in values.items()}


def rating_from_score(score):
    value=_decimal(score,'Tổng điểm')
    if not 1<=value<=6:raise ValueError('Điểm rủi ro phải trong khoảng 1–6')
    for i,rating in enumerate(SCALE[:16]):
        if value<=Decimal(1)+i*Decimal('.3125'):return rating
    return 'ccc'  # Bảng nguồn gộp CCC–C; không suy diễn sự kiện vỡ nợ.


def weighted_profile(scores,weights=None):
    w=validated_weights(weights);rows=[];missing=[]
    for key,title in zip(RISK_KEYS,RISK_TITLES):
        raw=scores.get(key);value=None
        if raw is None or (isinstance(raw,float) and math.isnan(raw)):missing.append(key)
        else:
            value=_decimal(raw,key)
            if not 1<=value<=6:raise ValueError(key+': điểm phải trong khoảng 1..6')
        contribution=value*_decimal(w[key],key) if value is not None else None
        rows.append({'Key':key,'Title':title,'Score':float(value) if value is not None else None,
                     'Weight':w[key],'Contribution':float(contribution) if contribution is not None else None})
    total=None if missing else sum(_decimal(r['Score'],r['Key'])*_decimal(r['Weight'],r['Key']) for r in rows)
    if total is not None:total/=sum(_decimal(r['Weight'],r['Key']) for r in rows)
    return {'RatingCalculation':'FOUR_WEIGHTED_RISKS','Weights':w,'WeightedContributions':rows,
            'RiskScores':{r['Title']:r['Score'] for r in rows},'WeightedScore':float(total) if total is not None else None,
            'WeightedScoreExact':str(total) if total is not None else None,
            'InitialRating':'vn'+rating_from_score(total).upper() if total is not None else 'N/A',
            'MissingRiskGroups':missing,'Audit':AUDIT}


def apply_adjustments(initial,governance,modifier=0,support=0,liquidity=None,financial_policy_weak=None):
    """Tách điều chỉnh khỏi tổng điểm; không tự suy thanh khoản từ Current Ratio."""
    for key,v,lo,hi in [('ModifierNotches',modifier,-6,6),('ExternalSupportNotches',support,0,8)]:
        if isinstance(v,bool) or not isinstance(v,int) or not lo<=v<=hi:raise ValueError(key+': số bậc ngoài phạm vi')
    raw=initial.lower().removeprefix('vn');caps=[];rows=[]
    def move(r,n):return SCALE[max(0,min(len(SCALE)-1,SCALE.index(r)-n))]
    current=move(raw,modifier)
    if modifier:rows.append({'Cấu phần':'Điều chỉnh khác','Tác động':f'{modifier:+d} bậc','Kết quả':'vn'+current.upper()})
    if governance>=4:
        ceiling='b' if governance>=6 else 'bb-' if governance>=5 else 'bb+'
        current=max((current,ceiling),key=SCALE.index);caps.append('Quản trị: vn'+ceiling.upper())
        rows.append({'Cấu phần':'Giới hạn quản trị','Tác động':'Trần vn'+ceiling.upper(),'Kết quả':'vn'+current.upper()})
    normalized=str(liquidity or '').strip().casefold()
    if normalized not in {'','rất mạnh','mạnh','phù hợp','trung bình','dưới trung bình','yếu'}:
        raise ValueError('Đánh giá thanh khoản không thuộc phương pháp')
    if normalized=='yếu':
        current=max((current,'b-'),key=SCALE.index);caps.append('Thanh khoản yếu: vnB-')
    elif normalized=='dưới trung bình':
        if SCALE.index(current)<SCALE.index('bb+'):current='bb+'
        elif SCALE.index(current)<=SCALE.index('bb-'):current=move(current,-1)
    elif normalized in {'mạnh','rất mạnh'} and SCALE.index(raw)>=SCALE.index('b+') and financial_policy_weak is False:
        current=move(current,1)
    if governance>=4:
        current=max((current,ceiling),key=SCALE.index)
    if liquidity:rows.append({'Cấu phần':'Thanh khoản','Tác động':liquidity,'Kết quả':'vn'+current.upper()})
    standalone='vn'+current.upper();final='vn'+move(current,support).upper()
    if support:rows.append({'Cấu phần':'Hỗ trợ bên ngoài','Tác động':f'+{support} bậc','Kết quả':final})
    return {'StandaloneRating':standalone,'ICR':final,'InternalNotches':SCALE.index(raw)-SCALE.index(current),
            'ModifierNotches':modifier,'ExternalSupportNotches':support,'RatingCaps':caps,'AdjustmentScorecard':rows}


def scorecard(result):
    rows=[]
    for row in result.get('WeightedContributions',[]):
        score=row['Score'];contribution=row['Contribution']
        rows.append({'Cấu phần':row['Title'],'Điểm / Đánh giá':f'{score:.4f}/6' if score is not None else 'Chưa đủ căn cứ',
            'Tỷ trọng':f"{row['Weight']:.1%}",'Điểm đóng góp':f'{contribution:.6f}' if contribution is not None else '—',
            'Kết quả / Căn cứ':'Điểm cấu phần × tỷ trọng' if contribution is not None else 'Chưa tổng hợp khi thiếu điểm'})
    total=result.get('WeightedScore')
    rows += [
      {'Cấu phần':'Tổng điểm có trọng số','Điểm / Đánh giá':f'{total:.6f}/6' if total is not None else 'Chưa đủ căn cứ','Tỷ trọng':'100%','Điểm đóng góp':f'{total:.6f}' if total is not None else '—','Kết quả / Căn cứ':'Cộng bốn đóng góp; không làm tròn trung gian'},
      {'Cấu phần':'Bậc xếp hạng ban đầu','Điểm / Đánh giá':result.get('InitialRating','N/A'),'Tỷ trọng':'—','Điểm đóng góp':'—','Kết quả / Căn cứ':'Quy đổi tổng điểm theo Bảng 01'},
      {'Cấu phần':'Kết quả xếp hạng','Điểm / Đánh giá':result.get('ICR','N/A'),'Tỷ trọng':'—','Điểm đóng góp':'—','Kết quả / Căn cứ':'Chưa đủ căn cứ tổng hợp' if result.get('ICR') in (None,'N/A','') else 'Sau điều chỉnh có căn cứ' if result.get('AdjustmentScorecard') else 'Bằng bậc ban đầu khi không có điều chỉnh'}]
    return rows


def steps(result):
    total=result.get('WeightedScore')
    rows=[('Tổng điểm bốn nhóm',f'{total:.6f}/6' if total is not None else 'Chưa đủ căn cứ'),
          ('Bậc xếp hạng ban đầu',result.get('InitialRating','N/A'))]
    if result.get('AdjustmentScorecard'):rows.append(('Bậc xếp hạng độc lập',result.get('StandaloneRating','N/A')))
    return rows+[('Kết quả xếp hạng',result.get('ICR','N/A'))]
