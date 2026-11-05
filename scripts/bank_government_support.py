"""Hỗ trợ Chính phủ tách khỏi SACP và hỗ trợ cổ đông; chính sách nghiên cứu riêng.

Không phải chuyển đổi thang CRA và không phải bảo lãnh của Chính phủ.
Không lấy bậc ICR đích theo ticker, không cộng vào các cấu phần nội tại.
"""
from copy import deepcopy
import json
from pathlib import Path

ELIGIBLE_BANKS = frozenset({'VCB', 'BID', 'CTG', 'AGRIBANK'})
ROOT = Path(__file__).resolve().parents[1]


def load_policy():
    policy = json.loads((ROOT/'config/bank_government_support.json').read_text(encoding='utf-8'))
    if set(policy['EligibleBanks']) != ELIGIBLE_BANKS:
        raise ValueError('Hỗ trợ Chính phủ chỉ áp dụng VCB, BID, CTG, AGRIBANK')
    _notches(policy['MaximumNotches'], 8)
    return policy


def _notches(value, maximum=8):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError('Notch hỗ trợ phải là số nguyên không âm trong giới hạn chính sách')
    return value


def government_support(ticker, sacp=None, period=None, overrides=None, blocked=False):
    from scripts.three_methodology_rating import SCALE, move, label
    o = overrides or {}; p = load_policy(); ticker = str(ticker).strip().upper()
    eligible = ticker in ELIGIBLE_BANKS
    requested = o.get('GovernmentSupportNotches')
    if requested is not None:
        _notches(requested, p['MaximumNotches'])
        if requested and not eligible:
            raise ValueError('Ngân hàng này không thuộc phạm vi hỗ trợ Chính phủ của mô hình')
    r = {'Eligible': eligible, 'Notches': 0, 'MaximumNotches': p['MaximumNotches'],
         'Ceiling': label(p['SupportCeiling']), 'PolicyId': p['PolicyId'],
         'Level': p['Level'] if eligible else 'Không áp dụng', 'Assumed': eligible,
         'Sources': p['Sources'] if eligible else [], 'ReviewedOn': p['ReviewedOn'],
         'Status': 'NOT_ELIGIBLE', 'Rationale': 'Không thuộc bốn ngân hàng được cộng hỗ trợ Chính phủ.'}
    if not eligible:
        return r
    if blocked:
        r.update(Status='BLOCKED', Rationale='Không tự nâng bậc khi có giới hạn pháp định hoặc sự kiện vỡ nợ; cần đánh giá hỗ trợ riêng.')
        return r
    if o.get('UseGovernmentSupport') is False or 'ExternalSupportNotches' in o:
        r.update(Status='DISABLED', Rationale='Hỗ trợ Chính phủ tắt trong kịch bản hoặc tổng hỗ trợ đã được nhập riêng.')
        return r
    if period and not p['EffectivePeriod'] <= period <= p['ReviewThroughPeriod']:
        r.update(Status='REVIEW_REQUIRED', Rationale='Kỳ ngoài phạm vi chính sách hỗ trợ đã rà soát; không tự chuyển tiếp giả định.')
        return r
    raw = str(sacp).lower().replace('vn', '')
    if raw not in SCALE:
        r.update(Notches=None, Status='PENDING_SACP', Rationale='Thuộc phạm vi hỗ trợ; chưa áp dụng notch khi chưa đủ căn cứ tính SACP.')
        return r
    limit = p['MaximumNotches'] if requested is None else requested
    applied = min(limit, max(0, SCALE.index(raw)-SCALE.index(p['SupportCeiling'])))
    r.update(Notches=applied, Status='APPLIED' if applied else 'AT_CEILING',
             AfterSupport=label(move(raw, applied)), Rationale=p['Rationale'],
             MethodologyDifference=p['MethodologyDifference'])
    return r


def apply_bank_support(result, overrides=None):
    """Một điểm tổng hợp hỗ trợ dùng chung cho báo cáo và UI; gọi lại không cộng lần hai."""
    from scripts.three_methodology_rating import SCALE, move, label
    if result.get('Methodology') != 'BANK':
        return result
    r = deepcopy(result)
    o = dict(r.get('SupportOverrides', {}) if overrides is None else overrides)
    legacy = o.get('ExternalSupportNotches')
    # Tổng hỗ trợ đã thẩm định từ phiên bản cũ không tự cộng chồng với Chính phủ.
    if legacy is None and 'OtherSupportNotches' not in o and 'GovernmentSupportAssessment' not in r:
        if r.get('ExternalSupportNotches') is not None and r.get('ExternalSupportAssumed') is False:
            legacy = r['ExternalSupportNotches']; o['ExternalSupportNotches'] = legacy
    other = _notches(o.get('OtherSupportNotches', legacy if legacy is not None else r.get('OtherSupportNotches', 0)))
    blocked = bool(r.get('RegulatoryCap') or o.get('RegulatoryCapitalStatus') in {'BREACH','SPECIAL_CONTROL','AT_RISK'}
                   or o.get('DefaultEventConfirmed') is True)
    g = government_support(r.get('Ticker'), r.get('SACP'), r.get('Period'), o, blocked)
    r.update(GovernmentSupportAssessment=g, GovernmentSupportEligible=g['Eligible'],
             GovernmentSupportNotches=g['Notches'], OtherSupportNotches=other,
             GovernmentSupportMethod='Chính sách hỗ trợ Chính phủ của mô hình — '+g['PolicyId'],
             SupportOverrides={k:v for k,v in o.items() if k in {'GovernmentSupportNotches','OtherSupportNotches','ExternalSupportNotches','UseGovernmentSupport','DefaultEventConfirmed','RegulatoryCapitalStatus'}})
    assumption = 'Hỗ trợ Chính phủ: '+g['Rationale'] if g['Eligible'] else ''
    assumptions = [x for x in r.get('Assumptions', []) if not str(x).startswith(('Hỗ trợ Chính phủ:', 'Hỗ trợ bên ngoài:'))]
    if not other:
        note = 'Hỗ trợ cổ đông / khác: không cộng bậc khi chưa có đánh giá riêng.'
        if note not in assumptions:
            assumptions.append(note)
    if assumption:
        assumptions.append(assumption)
    r['Assumptions'] = assumptions
    rows = [row for row in r.get('Scorecard', []) if row.get('Cấu phần') not in
            {'Hỗ trợ bên ngoài', 'Hỗ trợ từ Chính phủ', 'Hỗ trợ cổ đông / khác', 'Tổng hỗ trợ bên ngoài'}]
    def row(title, score, impact, reason):
        return {'Cấu phần':title,'Điểm / Đánh giá':score,'Tác động':impact,'Kết quả / Căn cứ':reason}
    support_rows = [row('Hỗ trợ từ Chính phủ',g['Level'],f"+{g['Notches']} bậc" if g['Notches'] is not None else 'Chờ SACP',g['Rationale']),
                    row('Hỗ trợ cổ đông / khác',str(other),f'+{other} bậc','Đánh giá nhập riêng' if other else 'Không cộng khi chưa có đánh giá riêng')]
    raw = str(r.get('SACP')).lower().replace('vn','')
    if raw in SCALE and r.get('ICR') not in (None,'','N/A'):
        gov = g['Notches'] or 0
        # Giữ giới hạn pháp định sau mọi điều chỉnh hỗ trợ.
        available = 0 if blocked else SCALE.index(raw)
        other_applied = min(other, max(0, available-gov))
        total = gov+other_applied
        final = move(raw,total)
        cap = str(r.get('RegulatoryCap')).lower().replace('vn','')
        if cap in SCALE and SCALE.index(final) < SCALE.index(cap):
            final = cap
        # Nếu đầu vào đã ghi nhận một mức xếp hạng thấp hơn do sự kiện đặc biệt,
        # bước hỗ trợ không được xóa kết luận đó.
        previous = str(r.get('ICR')).lower().replace('vn','')
        if blocked and previous in SCALE and SCALE.index(previous) > SCALE.index(final):
            final = previous
        r.update(OtherSupportNotches=other_applied, ExternalSupportNotches=total,
                 ICR=label(final), ExternalSupportAssumed=g['Assumed'] or legacy is None)
        support_rows[1]['Tác động']=f'+{other_applied} bậc'
        if other_applied != other:
            support_rows[1]['Kết quả / Căn cứ']='Mức nhập '+str(other)+'; mức áp dụng bị giới hạn bởi trần hoặc ràng buộc pháp định.'
        for item in rows:
            if item.get('Cấu phần') == 'Bậc xếp hạng ước tính':
                item.update({'Điểm / Đánh giá':r['ICR'], 'Tác động':'SACP + Chính phủ + hỗ trợ khác'})
        if g['Eligible'] and g['Status'] == 'APPLIED':
            r.update(RatingStatus='ESTIMATED', AssessmentComplete=False, ProvisionalAutoScoring=True,
                     RatingBasisNote='Bậc sau hỗ trợ sử dụng giả định Chính phủ công bố trong báo cáo; SACP giữ riêng.')
    idx = next((i for i,x in enumerate(rows) if x.get('Cấu phần') in {'Bậc xếp hạng ước tính','Kết quả'}),len(rows))
    rows[idx:idx] = support_rows
    r['Scorecard'] = rows
    return r
