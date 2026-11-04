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
EXTRA_FIELDS = ['Scope', 'Regime', 'SourceURL', 'SourcePage', 'VerifiedOn', 'Note',
                'SourceKind', 'InputText', 'ProvidedOn', 'SourceReference', 'ApplyThroughPeriod']


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
        row['SourceKind'] = 'VERIFIED_DISCLOSURE'
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


def user_input_frame(df, ticker, source='data/bank_car_user_inputs.csv'):
    """Giữ số do người dùng cung cấp tách biệt với nguồn đã đối chiếu.

    Kỳ trong tệp là kỳ của số liệu, không phải kỳ báo cáo đang sử dụng.
    Không suy diễn TT41/TT14 hoặc tự chuyển mọi dấu > thành một số ước.
    """
    if df.empty:
        return pd.DataFrame()
    required = {'Ticker', 'Period', 'Value', 'Unit', 'Scope', 'SourceKind',
                'InputText', 'ProvidedOn', 'SourceReference', 'ApplyThroughPeriod'}
    if required - set(df):
        raise ValueError('Nguồn CAR người dùng thiếu cột: ' + ', '.join(sorted(required-set(df))))
    q = df[df.Ticker.fillna('').astype(str).str.strip().str.upper().eq(str(ticker).strip().upper())]
    rows = []
    for item in q.fillna('').to_dict('records'):
        per = str(item['Period']).strip().upper()
        errors = []
        kind = str(item['SourceKind'])
        if not re.fullmatch(r'\d{4}-Q[1-4]', per): errors.append('Kỳ CAR không hợp lệ')
        through = str(item['ApplyThroughPeriod'])
        if not re.fullmatch(r'\d{4}-Q[1-4]', through) or per > through:
            errors.append('Giới hạn kỳ sử dụng không hợp lệ')
        if kind not in {'USER_PROVIDED', 'USER_ESTIMATE'}: errors.append('Loại nguồn không hợp lệ')
        if item['Scope'] not in SCOPES: errors.append('Phạm vi không hợp lệ')
        if not item['InputText'] or not item['SourceReference']: errors.append('Thiếu nội dung/nguồn nhập')
        try: date.fromisoformat(str(item['ProvidedOn']))
        except ValueError: errors.append('Ngày cung cấp không hợp lệ')
        try:
            value = float(item['Value'])
            if item['Unit'] == 'PERCENT': value /= 100
            elif item['Unit'] != 'RATIO': raise ValueError('Đơn vị không hợp lệ')
            if not math.isfinite(value) or not 0 < value < 1: raise ValueError('CAR ngoài phạm vi')
        except (ValueError, TypeError) as exc:
            value = float('nan'); errors.append(str(exc))
        regime = str(item.get('Regime') or 'UNKNOWN').upper()
        if regime not in REGIMES | {'UNKNOWN'}: errors.append('Cơ sở quy định không hợp lệ')
        origin = 'ước tính theo chỉ định người dùng' if kind == 'USER_ESTIMATE' else 'số liệu người dùng cung cấp'
        row = {k: item.get(k, '') for k in EXTRA_FIELDS}
        row.update(Period=per, Field='CAR', Value=value if not errors else float('nan'),
                   Basis='USER_ESTIMATE' if kind == 'USER_ESTIMATE' else 'USER_PROVIDED_RATIO',
                   Source=f"{source} | {origin} | {item['SourceReference']} | {item['InputText']}",
                   Unit='RATIO', Regime=regime, Error='; '.join(errors))
        rows.append(row)
    if not rows:return pd.DataFrame()
    selected = []
    for per, group in pd.DataFrame(rows).groupby('Period', sort=False):
        scope = 'CONSOLIDATED' if group.Scope.eq('CONSOLIDATED').any() else 'BANK_ONLY'
        candidates = group[group.Scope.eq(scope)]
        row = candidates.iloc[0].to_dict()
        if candidates.Error.ne('').any() or any(candidates[c].nunique() > 1 for c in ['Value', 'SourceKind', 'Regime']):
            row.update(Value=float('nan'), Error='Nguồn CAR người dùng lỗi hoặc xung đột')
        selected.append(row)
    return pd.DataFrame(selected)


def car_usage_text(record, target=None):
    """Một nhãn chung cho KPI, bảng điểm và báo cáo xuất file."""
    if record.get('Status') != 'OK' or record.get('Value') is None:
        return ''
    value = f"{record['Value']*100:.2f}".replace('.', ',')
    p = str(record.get('Period', ''))
    y, q = p.split('-Q') if re.fullmatch(r'\d{4}-Q[1-4]', p) else (p, '')
    when = {'1':'31/03/', '2':'30/06/', '3':'30/09/', '4':'31/12/'}.get(q, '')+y
    kind = record.get('SourceKind')
    origin = ('ước tính theo chỉ định người dùng' if kind == 'USER_ESTIMATE' else
              'số liệu người dùng cung cấp' if kind == 'USER_PROVIDED' else
              'đã đối chiếu báo cáo gốc' if kind == 'VERIFIED_DISCLOSURE' else 'số liệu trong nguồn ứng dụng')
    text = f"CAR {value}% tại {when}; {SCOPES.get(record.get('Scope'), 'phạm vi theo nguồn')}; {origin}."
    if kind == 'USER_ESTIMATE': text += ' Đầu vào: '+str(record.get('InputText', ''))+'.'
    if target and p != target:
        text += f' Dùng thay thế để tính điểm tại {target} theo chỉ định; giữ nguyên kỳ số liệu {p}.'
    return text


def comparable_metric(metric, own, peer):
    """CAR không trộn hai chế độ quy định, kể cả một bên chưa xác định chế độ."""
    if metric != 'CAR': return True
    # Nguồn người dùng chưa xác định TT41/TT14 vẫn chấm được, nhưng không gộp peer.
    if 'UNKNOWN' in {str(own.get('Regime', '')), str(peer.get('Regime', ''))}: return False
    regime = str(own.get('Regime', '') or '')
    scope = str(own.get('Scope', '') or '')
    return (regime in REGIMES and regime == str(peer.get('Regime', '') or '')
            and scope in SCOPES and scope == str(peer.get('Scope', '') or ''))


def bank_universe(ticker=None):
    from scripts.universal_data import universe
    u = universe()
    return sorted(set(u.loc[u.EntityType.eq('BANK'), 'Ticker']) - {ticker})


def peer_frame(ticker, target):
    """Hiển thị toàn bộ CAR đúng kỳ; chỉ gộp bình quân cùng phạm vi/chế độ.

    Số người dùng cung cấp vẫn hiện, nhưng không được biến thành số đã xác minh.
    CAR kỳ trước dùng cho chấm điểm không được đưa vào biểu đồ quý hiện tại.
    """
    from scripts.financial_evidence import at_period
    own = at_period(ticker, 'BANK', target, 'QUARTER').get('CAR', {}) if target else {}
    rows = []
    for t in [ticker] + bank_universe(ticker):
        r = at_period(t, 'BANK', target, 'QUARTER').get('CAR', {}) if target else {}
        if r.get('Status') != 'OK' or r.get('Period') != target:
            continue
        value = r.get('Value')
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            continue
        verified = r.get('SourceKind') == 'VERIFIED_DISCLOSURE'
        basis = r.get('Regime', 'UNKNOWN') + ' / ' + SCOPES.get(r.get('Scope'), 'Chưa xác định phạm vi')
        if not verified:
            basis += ' / ' + ('Ước tính' if r.get('SourceKind') == 'USER_ESTIMATE' else 'Người dùng cung cấp')
        rows.append(dict(Ticker=t, Value=value, Period=target, Basis=r.get('Basis'),
                         Regime=r.get('Regime', 'UNKNOWN'), Scope=r.get('Scope', ''),
                         SourceKind=r.get('SourceKind', ''), SourceURL=r.get('SourceURL', ''),
                         BasisLabel=basis, Comparable=verified and comparable_metric('CAR', own, r)))
    return pd.DataFrame(rows, columns=['Ticker','Value','Period','Basis','Regime','Scope',
                                      'SourceKind','SourceURL','BasisLabel','Comparable'])


def peer_note(item):
    rows = item.get('Peers', [])
    groups = sorted(set(r.get('BasisLabel', '') for r in rows if r.get('BasisLabel')))
    if not groups:
        return ''
    unverified=[r['Ticker'] for r in rows if r.get('SourceKind')!='VERIFIED_DISCLOSURE']
    return ('Nhóm tham chiếu CAR toàn ngành, đúng kỳ công bố; TT41/TT14 ghi dưới mã. '
            'Bình quân chỉ gồm CAR đã đối chiếu, cùng phạm vi và cùng TT41/TT14 với doanh nghiệp. '
            'Không dùng số cuối năm trước thay số quý trên biểu đồ.'
            +(' Dấu *: '+', '.join(unverified)+' là số người dùng cung cấp hoặc ước tính, chưa đưa vào bình quân. Dấu ? là chưa xác định chế độ tính.' if unverified else ''))


def history_breaks(history):
    """Không nối đường qua thay đổi phạm vi hoặc chế độ tính CAR."""
    if not {'Regime','Scope'}.issubset(history.columns):return []
    if not history.Regime.isin(REGIMES).any():return []
    return [i for i in range(1,len(history))
            if not comparable_metric('CAR',history.iloc[i-1],history.iloc[i])
            and history.iloc[i-1].get('Status')=='OK' and history.iloc[i].get('Status')=='OK']
