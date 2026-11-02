"""Bảng 2, 8 và ma trận huy động/thanh khoản trong phương pháp NH 2026.

Không suy diễn đánh giá quản trị, hỗ trợ hoặc CAR kỳ vọng từ thứ hạng peer.
"""
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GRADES=['Rất Mạnh','Mạnh','Phù Hợp','Trung Bình','Yếu','Rất Yếu']
FUNDING_GRADES=['Mạnh','Phù Hợp','Trung Bình','Yếu']
FUNDING_MATRIX=((1,0,-1,-2),(0,0,-1,-2),(0,-1,-2,-3),(-1,-2,-3,-3))


def car_grade(value):
    if isinstance(value,bool):return None
    try:v=float(value)
    except (TypeError,ValueError):return None
    if not math.isfinite(v) or v<0 or v>1:return None
    # Biên chung được xếp vào dải cao hơn; >18% mới là Rất Mạnh.
    return 'Rất Mạnh' if v>.18 else 'Mạnh' if v>=.15 else 'Phù Hợp' if v>=.12 else 'Trung Bình' if v>=.09 else 'Yếu' if v>=.08 else 'Rất Yếu'


def saved_assessment(ticker,period):
    selected={}
    # Phiếu nhập riêng có ưu tiên cao hơn kết quả kế thừa từ báo cáo mẫu.
    for name in ['bank_rating_references.json','bank_rating_assessments.json']:
        path=ROOT/'config'/name
        if not path.exists():continue
        payload=json.loads(path.read_text(encoding='utf-8'))
        rows=[r for r in payload.get('assessments',[]) if r.get('Ticker')==ticker and r.get('Period')==period and r.get('Source') and r.get('Rationale')]
        if rows:selected=rows[-1]
    return dict(selected)


def bank_rating(ticker,overrides=None):
    from scripts.three_methodology_rating import NOTCH,move,label,SCALE
    from scripts.financial_evidence import latest_period
    period=latest_period(ticker,'BANK');changes=dict(overrides or {})
    saved=saved_assessment(ticker,period) if changes.get('UseSavedAssessment',True) else {}
    o={**saved,**changes}
    for key in ('BusinessProfile','CapitalEarnings','RiskPosition','FundingLiquidity'):
        if key in changes and key+'Notches' not in changes:o.pop(key+'Notches',None)
    if any(k in changes for k in ('Funding','Liquidity')) and 'FundingLiquidity' not in changes:
        o.pop('FundingLiquidity',None)
    factors={};notches={};missing={};evidence={}
    for key,title in [('BusinessProfile','Hồ sơ Kinh doanh'),('CapitalEarnings','Vốn và Lợi nhuận'),('RiskPosition','Vị thế Rủi ro')]:
        grade=o.get(key)
        if key=='CapitalEarnings' and grade not in GRADES:
            grade=car_grade(o.get('ForecastCAR'))
            adjustment=o.get('CapitalAdjustmentNotches')
            if grade and isinstance(adjustment,int) and not isinstance(adjustment,bool) and -2<=adjustment<=2:
                idx=max(0,min(5,GRADES.index(grade)-adjustment));grade=GRADES[idx]
            elif grade:
                missing['CapitalAdjustmentNotches']='Đánh giá chất lượng vốn và lợi nhuận sau mức CAR kỳ vọng';grade=None
        if grade in GRADES:
            factors[title]=grade
            n=o.get(key+'Notches',NOTCH[grade])
            allowed={'Yếu':{-2,-3},'Rất Yếu':{-4,-5}}.get(grade,{NOTCH[grade]})
            if isinstance(n,bool) or n not in allowed:raise ValueError('Điều chỉnh không phù hợp đánh giá '+key)
            notches[title]=int(n)
        else:missing[key]={'BusinessProfile':'Đánh giá quản trị, tính ổn định và mức đa dạng hoạt động',
                         'CapitalEarnings':'CAR kỳ vọng và đánh giá chất lượng vốn, khả năng tạo lợi nhuận',
                         'RiskPosition':'Đánh giá tăng trưởng, tập trung và chất lượng tín dụng'}[key]
        if o.get('Rationale'):evidence[key]=o['Rationale']
    f,l=o.get('Funding'),o.get('Liquidity')
    title='Huy động vốn và Thanh khoản'
    if f in FUNDING_GRADES and l in FUNDING_GRADES:
        n=FUNDING_MATRIX[FUNDING_GRADES.index(f)][FUNDING_GRADES.index(l)]
        if n==1 and o.get('FundingStrongExceptionConfirmed') is not True:
            missing['FundingStrongExceptionConfirmed']='Mức +1 cần kết luận rõ ưu thế huy động và thanh khoản theo ngoại lệ của ma trận'
        else:factors[title]=f+' / '+l;notches[title]=n
    elif o.get('FundingLiquidity') in GRADES:
        # Tương thích phiếu tổng hợp đã thẩm định; không cho phép +2 ở cấu phần này.
        grade=o['FundingLiquidity'];n=o.get('FundingLiquidityNotches',min(1,NOTCH[grade]))
        allowed={'Yếu':{-2,-3},'Rất Yếu':{-4,-5}}.get(grade,{min(1,NOTCH[grade])})
        if isinstance(n,bool) or n not in allowed:raise ValueError('Điều chỉnh không phù hợp đánh giá FundingLiquidity')
        factors[title]=grade;notches[title]=int(n)
    else:missing['FundingLiquidity']='Đánh giá riêng huy động vốn và thanh khoản để áp dụng ma trận'
    complete=len(notches)==4
    anchor='a-';sacp=move(anchor,sum(notches.values())) if complete else None
    regulatory=o.get('RegulatoryCapitalStatus')
    cap='b-' if regulatory in ('BREACH','SPECIAL_CONTROL') else 'bb+' if regulatory=='AT_RISK' else None
    if cap and sacp and SCALE.index(sacp)<SCALE.index(cap):sacp=cap
    support=o.get('ExternalSupportNotches')
    valid=isinstance(support,int) and not isinstance(support,bool) and 0<=support<=8
    if not valid:missing['ExternalSupportNotches']='Đánh giá khả năng và ý chí hỗ trợ của Chính phủ hoặc chủ sở hữu'
    icr=move(sacp,support) if sacp and valid else None
    return {'Methodology':'BANK','MethodologyName':'Phương pháp XHTN Ngân hàng 2026',
            'Period':period,'Anchor':label(anchor),'BICRA':label(anchor),'Factors':factors,'FactorNotches':notches,
            'InternalNotches':sum(notches.values()) if complete else None,
            'SACP':label(sacp) if sacp else 'N/A','ICR':label(icr) if icr else 'N/A',
            'ExternalSupportNotches':support if valid else None,'Outlook':o.get('Outlook','Chưa xác định'),
            'MissingEvidence':missing,'EvidenceByFactor':evidence,'RegulatoryCap':label(cap) if cap else None,
            'RatingStatus':'SIMULATION' if icr else 'STANDALONE_ONLY' if sacp else 'UNREVIEWED',
            'RatingOrigin':('REFERENCE_REPORT_UPDATED' if any(k!='UseSavedAssessment' for k in changes) else 'REFERENCE_REPORT') if saved.get('SourceType')=='REFERENCE_REPORT' else 'ASSESSMENT',
            'AssessmentSource':saved.get('Source',''),'AssessmentPeriod':saved.get('Period',period),
            'AssessmentRationale':saved.get('Rationale',''),'ReferenceICR':saved.get('ReferenceICR'),
            'DataSufficientForAutoRating':bool(icr),
            'Audit':'Áp dụng bảng CAR kỳ vọng và ma trận huy động/thanh khoản; không thay đánh giá bằng điểm peer.'}
