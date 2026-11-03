"""Funding assessments and regulatory observations, kept separate from BCTC LDR.

An accounting loans/deposits ratio is a funding-gap indicator, not a regulatory
LDR or a liquidity stress test. A confirmed factor is period-specific and never
turns the remaining automatic factors into a completed assessment.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rows(filename, root=None):
    path = Path(root or ROOT) / 'config' / filename
    return json.loads(path.read_text(encoding='utf-8')).get('Records', []) if path.exists() else []


def _exact(filename, ticker, period, root=None):
    if not re.fullmatch(r'\d{4}-Q[1-4]', str(period)):
        return None
    rows = [r for r in _rows(filename, root) if r.get('Ticker') == str(ticker).upper()
            and r.get('Period') == period]
    if len(rows) > 1:
        raise ValueError(f'Duplicate bank funding record: {ticker} {period}')
    return rows[0] if rows else None


def observations(ticker, period, root=None):
    row = _exact('bank_funding_observations.json', ticker, period, root)
    if not row or row.get('Scope') != 'BANK_ONLY' or not row.get('SourceURL') or not row.get('VerifiedAt'):
        return None
    limits = {'RegulatoryLDR': 2, 'ShortTermFundingForLongLoans': 1,
              'DisclosedCASA': 1, 'QuarterlyCostOfFunds': 1}
    for key, maximum in limits.items():
        v = row.get(key)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))
                              or not math.isfinite(v) or not 0 <= v <= maximum):
            raise ValueError(f'Invalid {key}: {ticker} {period}')
    return dict(row)


def factor_assessment(ticker, period, root=None):
    row = _exact('bank_funding_assessments.json', ticker, period, root)
    grades = {'Mạnh', 'Phù Hợp', 'Trung Bình', 'Yếu'}
    if not row:
        return None
    if (row.get('Funding') not in grades or row.get('Liquidity') not in grades
            or not row.get('Source') or not row.get('Rationale')
            or row.get('SourceType') != 'USER_CONFIRMED_FACTOR'):
        raise ValueError(f'Incomplete funding assessment: {ticker} {period}')
    return dict(row)


def funding_commentary(ticker, period, assessment=None):
    """Financial implications of same-period observations; no peer-basis mixing."""
    row = observations(ticker, period)
    result = []
    def pct(x):
        return f'{x * 100:.1f}'.replace('.', ',') + '%'
    if row and row.get('RegulatoryLDR') is not None:
        text = (f'Tại {period}, LDR riêng lẻ do {ticker} công bố là {pct(row["RegulatoryLDR"])}')
        previous = observations(ticker, f'{int(period[:4])-1}-Q4')
        if previous and previous.get('RegulatoryLDR') is not None:
            a, b = previous['RegulatoryLDR'], row['RegulatoryLDR']
            text += f', {"tăng" if b > a else "giảm" if b < a else "không đổi"} so với {pct(a)} cuối năm trước'
        text += '. '
        short = row.get('ShortTermFundingForLongLoans')
        if short is not None:
            text += f'Vốn ngắn hạn cho vay trung, dài hạn ở {pct(short)}. '
        text += ('Hai tỷ lệ cần được theo dõi cùng tốc độ tăng tín dụng và kỳ hạn huy động. '
                 'Tỷ số cho vay/tiền gửi trên BCTC dùng trong biểu đồ phản ánh khoảng chênh tài trợ; '
                 'không đồng nhất với LDR riêng lẻ công bố và không đủ để kết luận thanh khoản yếu.')
        result.append(text)
    if row and row.get('QuarterlyCostOfFunds') is not None:
        q = int(period[-1]); previous = observations(ticker, period[:6]+str(q-1)) if q>1 else None
        text = f'Chi phí vốn trong quý ở {pct(row["QuarterlyCostOfFunds"])}'
        if previous and previous.get('QuarterlyCostOfFunds') is not None:
            a, b = previous['QuarterlyCostOfFunds'], row['QuarterlyCostOfFunds']
            text += f', so với {pct(a)} quý trước. '
            text += ('Chi phí tăng làm thu hẹp lợi thế tài trợ, dù nguồn tiền gửi không kỳ hạn vẫn hỗ trợ ngân hàng; cần giữ ổn định CASA để bảo vệ biên lãi.' if b>a else 'Diễn biến chi phí vốn hỗ trợ bảo vệ biên lãi; cần giữ ổn định nguồn tiền gửi cốt lõi.')
        else:
            text += '; khả năng giữ chân tiền gửi với chi phí hợp lý là trọng tâm bảo vệ biên lãi.'
        result.append(text)
    if assessment:
        result.append('Kết luận cấu phần: Huy động vốn '+assessment['Funding']+'; Thanh khoản '+assessment['Liquidity']+
                      '. '+assessment['Rationale'])
    return result
