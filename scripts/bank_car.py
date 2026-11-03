"""CAR công bố chính thức: đúng mã/kỳ, đơn vị và phạm vi; không kéo kỳ cũ.

Tệp nguồn được đối chiếu với báo cáo gốc trước khi phát hành. Đây không phải
trình đọc PDF tự động hoặc kết luận ngân hàng chưa công bố khi thiếu một dòng.
"""
import math
import re
from datetime import date
from urllib.parse import urlparse

import pandas as pd

REQUIRED = {'Ticker', 'Period', 'Metric', 'Value', 'Unit', 'Scope', 'Regime',
            'SourceURL', 'SourcePage', 'VerifiedOn'}
SCOPES = {'CONSOLIDATED': 'Hợp nhất', 'BANK_ONLY': 'Riêng lẻ'}
REGIMES = {'TT41', 'TT14'}
EXTRA_FIELDS = ['Scope', 'Regime', 'SourceURL', 'SourcePage', 'VerifiedOn', 'Note']


def disclosure_frame(df, ticker, source='data/bank_car_disclosures.csv'):
    """Chọn CAR tổng vốn/RWA; ưu tiên hợp nhất, chỉ riêng lẻ khi không có HN."""
    if df.empty:
        return pd.DataFrame()
    missing = REQUIRED - set(df)
    if missing:
        raise ValueError('Nguồn CAR thiếu cột: ' + ', '.join(sorted(missing)))
    q = df[df.Ticker.astype(str).str.strip().str.upper().eq(str(ticker).strip().upper())].copy()
    rows = []
    for item in q.fillna('').to_dict('records'):
        per = str(item['Period']).strip().upper()
        if not re.fullmatch(r'\d{4}-Q[1-4]', per):
            raise ValueError(f'{ticker}: kỳ CAR không hợp lệ: {per}')
        scope = str(item['Scope']).strip().upper()
        regime = str(item['Regime']).strip().upper()
        errors = []
        if item['Metric'] != 'CAR': errors.append('Không phải CAR tổng vốn/RWA')
        if scope not in SCOPES: errors.append('Phạm vi CAR không hợp lệ')
        if regime not in REGIMES: errors.append('Chưa xác định cơ sở quy định CAR')
        try:
            value = float(item['Value'])
            if item['Unit'] == 'PERCENT': value /= 100
            elif item['Unit'] != 'RATIO': raise ValueError('Đơn vị phải là PERCENT hoặc RATIO')
            if not math.isfinite(value) or not 0 < value < 1:
                raise ValueError('CAR phải lớn hơn 0 và nhỏ hơn 100%')
        except (ValueError, TypeError) as exc:
            value = float('nan'); errors.append(str(exc))
        url = str(item['SourceURL']).strip()
        if urlparse(url).scheme not in {'https', 'http'} or not urlparse(url).netloc:
            errors.append('Thiếu liên kết báo cáo gốc')
        if not str(item['SourcePage']).strip(): errors.append('Thiếu trang/bảng nguồn')
        try: date.fromisoformat(str(item['VerifiedOn']))
        except ValueError: errors.append('Thiếu ngày đối chiếu nguồn')
        citation = (f"{source} | {SCOPES.get(scope, scope)} | {regime} | "
                    f"trang {item['SourcePage']} | {url}")
        row = {'Period': per, 'Field': 'CAR', 'Value': value if not errors else float('nan'),
               'Basis': 'REPORTED_RATIO', 'Source': citation, 'Unit': 'RATIO',
               'Error': '; '.join(errors)}
        row.update({k: item.get(k, '') for k in EXTRA_FIELDS})
        row.update(Scope=scope, Regime=regime, SourceURL=url)
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    selected = []
    for per, group in pd.DataFrame(rows).groupby('Period', sort=False):
        # Không bỏ qua bản hợp nhất bị lỗi để âm thầm chọn số riêng lẻ.
        preferred = 'CONSOLIDATED' if group.Scope.eq('CONSOLIDATED').any() else 'BANK_ONLY'
        candidates = group[group.Scope.eq(preferred)]
        if candidates.empty: candidates = group
        row = candidates.iloc[0].to_dict()
        if candidates.Error.ne('').any() or candidates.Value.nunique() > 1 or candidates.Regime.nunique() > 1:
            row.update(Value=float('nan'), Error='Nguồn CAR lỗi hoặc xung đột cùng mã/kỳ/phạm vi')
        selected.append(row)
    return pd.DataFrame(selected)


def comparable_metric(metric, own, peer):
    """CAR không trộn hai chế độ quy định, kể cả một bên chưa xác định chế độ."""
    if metric != 'CAR': return True
    return str(own.get('Regime', '') or '') == str(peer.get('Regime', '') or '')
