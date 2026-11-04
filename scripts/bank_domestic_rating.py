"""Tương thích cấu hình cũ và dấu vân tay nguồn; không còn hiệu chỉnh ICR."""
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
    """Compatibility only: calibration was withdrawn by the user on 03/11/2026."""
    return deepcopy(base)
