"""Hiệu chỉnh thang trong nước theo cấu hình; tách khỏi điểm tài chính và CRA.

Mức đích là lựa chọn của chủ mô hình, không phải kết quả suy ra từ BCTC.
Không sửa CAR, SACP, notch hỗ trợ, phiếu nhập riêng hoặc xếp hạng CRA.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path

from scripts.three_methodology_rating import SCALE, label

ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = 'bank_domestic_calibration.json'
REFERENCE_FILE = 'bank_domestic_benchmarks.json'


def grade(value):
    value = str(value or '').lower().removeprefix('vn')
    return value if value in SCALE else None


def load_policy(root=None):
    path = Path(root or ROOT) / 'config' / POLICY_FILE
    if not path.exists():
        return {'Enabled': False, 'Profiles': []}
    policy = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(policy.get('Enabled'), bool) or policy.get('Scale') != 'VIETNAM_DOMESTIC':
        raise ValueError('Khung ngân hàng phải khai báo Enabled và thang VIETNAM_DOMESTIC')
    date.fromisoformat(policy['EffectiveDate'])
    seen = set()
    for p in policy['Profiles']:
        if p.get('Mode') not in {'TARGET', 'CEILING'} or not grade(p.get('Grade')) or not p.get('Rationale'):
            raise ValueError('Cấu hình hiệu chỉnh ngân hàng thiếu bậc, chế độ hoặc lý do')
        for entity in p['Entities']:
            if entity in seen:
                raise ValueError('Ngân hàng xuất hiện ở nhiều nhóm hiệu chỉnh: ' + entity)
            seen.add(entity)
    return policy


def source_fingerprint(root=None):
    root = Path(root or ROOT)
    h = hashlib.sha256()
    for name in (POLICY_FILE, REFERENCE_FILE, 'bank_rating_assessments.json', 'bank_rating_references.json',
                 'bank_funding_assessments.json', 'bank_funding_observations.json'):
        path = root / 'config' / name
        h.update(name.encode())
        h.update(path.read_bytes() if path.exists() else b'MISSING')
    return h.hexdigest()


def profile_for(ticker, policy):
    return next((p for p in policy.get('Profiles', []) if ticker in p['Entities']), None)


def benchmark_for(ticker, root=None):
    path = Path(root or ROOT) / 'config' / REFERENCE_FILE
    if not path.exists():
        return None
    rows = json.loads(path.read_text(encoding='utf-8'))['References']
    return next((deepcopy(r) for r in rows if r['Ticker'] == ticker), None)


def policy_rows(policy=None):
    policy = load_policy() if policy is None else policy
    return [{'Ngân hàng': ', '.join(p['Entities']),
             'Cách áp dụng': 'Mức đích hiệu chỉnh' if p['Mode'] == 'TARGET' else 'Trần hiệu chỉnh',
             'Bậc trong nước': label(grade(p['Grade'])), 'Căn cứ': p['Rationale']}
            for p in policy.get('Profiles', [])]


def benchmark_text(reference):
    if not reference:
        return ''
    status = {'PUBLISHED':'mức đã công bố trong nguồn đối chiếu',
              'HISTORICAL_PUBLISHED':'mức công bố lịch sử',
              'USER_REPORTED':'theo bảng tham khảo người dùng cung cấp',
              'HISTORICAL_USER_REPORTED':'mức lịch sử theo bảng người dùng',
              'WITHDRAWN':'đã rút; bậc nêu là mức trước khi rút',
              'DISCONTINUED':'đã ngừng; bậc nêu là mức cuối cùng'}.get(reference['Status'], reference['Status'])
    return ('Tham khảo CRA trong nước: ' + reference['Agency'] + ' ' + reference['Grade']
            + '; ngày tham chiếu ' + reference['ReferenceDate'] + '; ' + status + '. '
            + reference.get('Note', ''))


def apply_calibration(base, ticker, overrides=None, policy=None):
    """Áp một lớp riêng và giữ nguyên toàn bộ bảng điểm gốc để kiểm tra."""
    if base.get('Methodology') != 'BANK':
        return base
    policy = load_policy() if policy is None else policy
    o = dict(overrides or {})
    if not policy.get('Enabled') or o.get('UseDomesticCalibration') is False:
        return base
    r = deepcopy(base)
    r['DomesticBenchmark'] = benchmark_for(ticker)
    p = profile_for(ticker, policy)
    if not p:
        return r
    r['DomesticPolicy'] = {'Id': policy['Id'], 'EffectiveDate': policy['EffectiveDate'],
                           'Source': policy['Source'], 'Profile': deepcopy(p)}
    r['RawICR'] = base.get('ICR', 'N/A')
    r['DomesticCalibrationApplied'] = False
    manual = any(k not in {'UseDomesticCalibration', 'UseSavedAssessment'} for k in o)
    if manual or (base.get('AssessmentSource') and not str(base.get('RatingOrigin', '')).startswith('REFERENCE_REPORT')):
        r['DomesticCalibrationStatus'] = 'MANUAL_PRIORITY'
        return r
    raw = grade(base.get('ICR'))
    if (not raw or base.get('RatingBlocker') or base.get('MissingEvidence')
            or base.get('DataSufficientForAutoRating') is False):
        r['DomesticCalibrationStatus'] = 'MISSING_EVIDENCE'
        return r
    # Không để mức đích che lấp giới hạn vốn, sự kiện vỡ nợ hoặc kiểm soát đặc biệt.
    car = (base.get('CARInput') or {}).get('Value')
    weak_capital = isinstance(car, (int, float)) and not isinstance(car, bool) and car < .08
    if (weak_capital or base.get('RegulatoryCap') or base.get('DefaultEventConfirmed')
            or base.get('RegulatoryCapitalStatus') in {'BREACH', 'SPECIAL_CONTROL', 'AT_RISK'}):
        r['DomesticCalibrationStatus'] = 'RISK_LIMIT'
        return r
    target = grade(p['Grade'])
    final = target if p['Mode'] == 'TARGET' else max((raw, target), key=SCALE.index)
    if p['Mode'] == 'CEILING' and final == raw:
        r['DomesticCalibrationStatus'] = 'WITHIN_CEILING'
        return r
    notch = SCALE.index(raw) - SCALE.index(final)
    r['PreCalibrationResult'] = deepcopy(base)
    r.update(ICR=label(final), RatingOrigin='DOMESTIC_CALIBRATION', RatingStatus='CALIBRATED_ESTIMATE',
             AssessmentComplete=False, ProvisionalAutoScoring=True,
             DomesticCalibrationApplied=True, DomesticCalibrationStatus='APPLIED',
             DomesticCalibrationNotches=notch)
    note = ('Bậc ' + label(final) + ' sau hiệu chỉnh thang trong nước theo khung do Lê Hoàng Quân lựa chọn ngày '
            + date.fromisoformat(policy['EffectiveDate']).strftime('%d/%m/%Y') + '. Bậc trước hiệu chỉnh '
            + label(raw) + '; điều chỉnh ' + f'{notch:+d}' + ' bậc. Đây là mức hiệu chỉnh của mô hình, '
            'không phải kết luận xếp hạng của tổ chức CRA hoặc xác nhận bảo lãnh của Nhà nước.')
    r['RatingBasisNote'] = note
    r['Assumptions'] = list(base.get('Assumptions', [])) + [note, p['Rationale']]
    r['Scorecard'] = deepcopy(base.get('Scorecard', []))
    for row in r['Scorecard']:
        if row.get('Cấu phần') == 'Bậc xếp hạng ước tính':
            row['Cấu phần'] = 'Bậc trước hiệu chỉnh'
    r['Scorecard'].extend([
        {'Cấu phần': 'Hiệu chỉnh thang trong nước', 'Điểm / Đánh giá': p['Name'],
         'Tác động': f'{notch:+d} bậc', 'Kết quả / Căn cứ': p['Rationale']},
        {'Cấu phần': 'ICR sau hiệu chỉnh', 'Điểm / Đánh giá': label(final),
         'Tác động': label(raw) + ' → ' + label(final),
         'Kết quả / Căn cứ': 'Mức đích của mô hình; không đổi SACP hoặc notch hỗ trợ bên ngoài'}])
    r['Audit'] = str(base.get('Audit', '')) + ' ' + note
    return r
