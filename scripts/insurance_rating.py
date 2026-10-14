"""Saigon Ratings insurance rating adapter (2025 methodology).

Analyst-led: does not manufacture ratings from generic corporate financials.
All risk grades must be documented and reviewed. Reference matrix is sourced from the 2025 non-life methodology; its applicability to other insurers requires analyst validation. Scores follow the two
published matrix steps; ambiguous cells require an explicit committee choice.
"""
from typing import Mapping

MATRIX_1 = [
    [1,2,3,4,5,6],
    [1,2,3,4,5,6],
    [2,2,3,4,5,6],
    [3,3,4,5,6,7],
    [5,5,5,6,6,7],
    [6,7,7,7,7,7],
]
# Rows = combined macro/industry/business (1..7); columns = financial (1..10)
# None = N/A in the source; tuple = alternatives requiring committee selection.
MATRIX_2 = [
    ['aa+','aa','aa-','a+','a','a-','bbb+','bbb-',None,None],
    ['aa','aa-',('aa-','a+'),('a+','a'),'a','a-','bbb','bb+','bb',None],
    ['a+',('a+','a'),('a','a-'),'a-','a-','bbb+','bbb','bb+','bb-','b+'],
    [('a','a-'),'a-','a-','bbb+','bbb+','bbb','bbb-','bb','bb-','b'],
    ['bbb+','bbb+',('bbb+','bbb'),'bbb','bbb','bbb-','bb+','bb','b+','b'],
    ['bbb-','bbb-','bbb-','bb+','bb+','bb+','bb','bb-','b','b'],
    ['bb-','bb-','bb-','bb-','bb-','bb-','b+','b','b',('b-','lower')],
]
SCALE = ['aaa','aa+','aa','aa-','a+','a','a-','bbb+','bbb','bbb-','bb+','bb','bb-','b+','b','b-','ccc','cc','c']

def _grade(x,lo,hi):
    if isinstance(x,bool) or not isinstance(x,int) or not lo <= x <= hi:
        raise ValueError(f'Điểm phải là số nguyên {lo}–{hi}; không suy đoán từ dữ liệu thiếu')
    return x

def _move(x,notches):
    if x not in SCALE: raise ValueError('Bậc xếp hạng không hợp lệ')
    return SCALE[max(0,min(len(SCALE)-1,SCALE.index(x)-notches))]

def insurance_rating(ticker, overrides=None):
    """Compute the insurance rating with explicit analyst inputs.

    Required: MacroIndustryRisk (1..6), BusinessRisk (1..6), FinancialRisk
    (1..10). Optional: AnchorSelection for ambiguous matrix cells, and
    GovernanceLiquidityNotches, OtherAdjustmentsNotches, ComparativeNotches,
    GroupSupportNotches, GovernmentSupportNotches. Missing inputs => N/A.
    """
    o=dict(overrides or {})
    result={'Methodology':'INSURANCE',
            'MethodologyName':'Phương pháp XHTN Công ty Bảo hiểm (tham chiếu Saigon Ratings 2025)',
            'ScopeNote':'Ma trận tham chiếu từ phương pháp bảo hiểm phi nhân thọ 2025; cần xác nhận tính phù hợp khi áp dụng cho loại hình khác', 'Ticker':str(ticker).upper(), 'Anchor':'N/A','SCA':'N/A','SACP':'N/A','ICR':'N/A',
            'ProvisionalAutoScoring':False,'DataSufficientForAutoRating':False,
            'Audit':'Theo ma trận 01 và 02 của phương pháp Saigon Ratings 2025; cần chuyên viên xác nhận các điểm rủi ro.',
            'MissingEvidence':[]}
    required=[('MacroIndustryRisk',1,6),('BusinessRisk',1,6),('FinancialRisk',1,10)]
    for key,lo,hi in required:
        if key not in o:
            result['MissingEvidence'].append(key)
        else:
            _grade(o[key],lo,hi)
    if result['MissingEvidence']: return result
    combined=MATRIX_1[o['MacroIndustryRisk']-1][o['BusinessRisk']-1]
    raw=MATRIX_2[combined-1][o['FinancialRisk']-1]
    result.update({'CombinedRiskScore':combined,'FinancialRiskScore':o['FinancialRisk'], 'AnchorCandidates':raw})
    if raw is None:
        result['MissingEvidence'].append('Ma trận 02 quy định N/A cho tổ hợp điểm này')
        return result
    if isinstance(raw,tuple):
        selected=str(o.get('AnchorSelection','')).lower().replace('vn','')
        if selected not in raw or selected=='lower':
            result['MissingEvidence'].append('AnchorSelection: cần Hội đồng lựa chọn bậc trong ma trận')
            return result
        anchor=selected
    else: anchor=raw
    result['Anchor']='vn'+anchor.upper()
    modifiers=['GovernanceLiquidityNotches','OtherAdjustmentsNotches','ComparativeNotches']
    for key in modifiers:
        if key not in o:
            result['MissingEvidence'].append(key)
    if result['MissingEvidence']: return result
    if any(not isinstance(o[k],int) or isinstance(o[k],bool) or abs(o[k])>6 for k in modifiers):
        raise ValueError('Điều chỉnh phải là số nguyên trong khoảng -6..6; cần chứng cứ')
    sca=_move(anchor,sum(o[k] for k in modifiers))
    result['SCA']=result['SACP']='vn'+sca.upper()
    support=['GroupSupportNotches','GovernmentSupportNotches']
    for key in support:
        if key not in o: result['MissingEvidence'].append(key)
    if result['MissingEvidence']: return result
    if any(not isinstance(o[k],int) or isinstance(o[k],bool) or not 0<=o[k]<=8 for k in support):
        raise ValueError('Hỗ trợ phải là số nguyên từ 0 đến 8 và được thẩm định')
    result['ICR']='vn'+_move(sca,sum(o[k] for k in support)).upper()
    result['DataSufficientForAutoRating']=True
    return result
