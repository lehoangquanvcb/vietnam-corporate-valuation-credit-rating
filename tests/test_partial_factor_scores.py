"""Missing one component must not erase independent assessments or create a grade."""
from unittest.mock import patch

import pytest

from scripts.report_rating import _financial_institution, Evidence


class Inputs:
    period = '2026-Q2'
    peers = ['P1', 'P2', 'P3']

    def __init__(self, values=None, business=3, risk=2):
        self.values = dict(CAR=.13, CASA=.2, LDR=.9)
        self.values.update(values or {})
        self.business, self.risk = business, risk
        self.rows = []

    def value(self, metric):
        return self.values.get(metric)

    def peer_score(self, specs):
        return self.business if specs[0][0] == 'TotalAssets' else self.risk

    def add(self, metric, value, score=None, rule='', count=None):
        self.rows.append({'Metric': metric, 'Chỉ tiêu': metric, 'Giá trị': value,
                          'Điểm': score, 'Cách chấm': rule, 'Kỳ': self.period})


def bank(data, overrides=None, strict=None):
    return _financial_institution('TEST', 'BANK', overrides or {}, data, strict or {})


def test_missing_car_keeps_business_risk_and_funding_but_blocks_total():
    r = bank(Inputs({'CAR': None}))
    assert r['Factors'] == {'Hồ sơ Kinh doanh': 'Phù Hợp', 'Vị thế Rủi ro': 'Mạnh',
                            'Huy động vốn và Thanh khoản': 'Phù Hợp / Phù Hợp'}
    assert r['Funding'] == r['Liquidity'] == 'Phù Hợp'
    assert set(r['MissingEvidence']) == {'CapitalEarnings'}
    assert 'CAR hợp lệ tại 2026-Q2' in r['MissingEvidence']['CapitalEarnings']
    assert r['ICR'] == r['SACP'] == 'N/A'
    assert r['InternalNotches'] is None and not r['DataSufficientForAutoRating']
    capital = next(x for x in r['Scorecard'] if x['Cấu phần'] == 'Vốn và Lợi nhuận')
    assert capital['Tác động'] == '—'
    assert r['ExternalSupportAssumed'] and r['ExternalSupportNotches'] == 0
    assert not r['AssessmentComplete']


def test_missing_first_component_does_not_stop_remaining_calculation():
    r = bank(Inputs(business=None))
    assert set(r['MissingEvidence']) == {'BusinessProfile'}
    assert len(r['FactorNotches']) == 3
    assert r['Factors']['Vốn và Lợi nhuận'] == 'Phù Hợp'
    assert r['Factors']['Vị thế Rủi ro'] == 'Mạnh'
    assert r['ICR'] == 'N/A'


def test_multiple_gaps_are_reported_together_and_known_funding_survives():
    r = bank(Inputs({'CAR': None, 'LDR': None}, business=None))
    assert set(r['MissingEvidence']) == {'BusinessProfile', 'CapitalEarnings', 'Liquidity'}
    assert r['Funding'] == 'Phù Hợp' and r['Liquidity'] is None
    assert 'Huy động vốn và Thanh khoản' not in r['FactorNotches']
    assert r['Factors']['Vị thế Rủi ro'] == 'Mạnh'


def test_explicit_capital_decision_completes_estimate_and_can_be_removed():
    data = Inputs({'CAR': None})
    r = bank(data, {'CapitalEarnings': 'Trung Bình'})
    assert r['ICR'] == 'vnA-' and r['InternalNotches'] == 0
    assert r['RatingStatus'] == 'ESTIMATED' and not r['AssessmentComplete']
    assert bank(data)['ICR'] == 'N/A'


def test_partial_saved_grade_and_explicit_notch_are_retained():
    strict = {'Factors': {'Hồ sơ Kinh doanh': 'Yếu'},
              'FactorNotches': {'Hồ sơ Kinh doanh': -3},
              'ExternalSupportNotches': 2, 'Outlook': 'Tiêu cực'}
    r = bank(Inputs({'CAR': None}), strict=strict)
    assert r['Factors']['Hồ sơ Kinh doanh'] == 'Yếu'
    assert r['FactorNotches']['Hồ sơ Kinh doanh'] == -3
    assert r['ExternalSupportNotches'] == 2 and not r['ExternalSupportAssumed']
    assert r['Outlook'] == 'Tiêu cực'
    changed = bank(Inputs({'CAR': None}), {'BusinessProfile': 'Mạnh'}, strict)
    assert changed['FactorNotches']['Hồ sơ Kinh doanh'] == 1


def test_partial_saved_funding_is_not_replaced_by_automatic_proxy():
    title = 'Huy động vốn và Thanh khoản'
    strict = {'Factors': {title: 'Yếu'}, 'FactorNotches': {title: -3}}
    r = bank(Inputs({'CAR': None, 'LDR': None}), strict=strict)
    assert r['FactorNotches'][title] == -3
    assert set(r['MissingEvidence']) == {'CapitalEarnings'}


def test_saved_regulatory_cap_still_limits_partial_assessment_completion():
    r = bank(Inputs(), strict={'RegulatoryCap': 'vnB-'})
    assert r['SACP'] == 'vnB-' and r['ICR'] == 'vnB-'


@pytest.mark.parametrize('funding,liquidity', [('Mạnh', 'Mạnh'), ('Yếu', 'Yếu')])
def test_funding_matrix_is_not_skipped_when_capital_missing(funding, liquidity):
    r = bank(Inputs({'CAR': None}), {'Funding': funding, 'Liquidity': liquidity})
    assert r['FactorNotches']['Huy động vốn và Thanh khoản'] == (0 if funding == 'Mạnh' else -3)
    assert r['ICR'] == 'N/A'


def test_old_car_is_not_carried_forward_to_complete_a_grade():
    records = {'CAR': {'Status': 'OK', 'Value': .13, 'Period': '2025-Q2'}}
    with patch('scripts.report_rating.latest_period', return_value='2026-Q2'), \
         patch('scripts.report_rating.get_company', return_value={'EntityType': 'BANK'}), \
         patch('scripts.report_rating.peer_tickers', return_value=[]), \
         patch('scripts.report_rating.at_period', return_value=records):
        assert Evidence('TEST', 'BANK').value('CAR') is None


def test_securities_missing_capital_keeps_risk_and_liquidity():
    r = _financial_institution('TEST', 'SECURITIES', {},
                              Inputs({'DebtEquity': .8, 'CurrentRatio': 2}), {})
    assert set(r['MissingEvidence']) == {'CapitalEarnings'}
    assert len(r['FactorNotches']) == 3
    assert r['Anchor'] == 'vnBBB' and r['ICR'] == 'N/A'


def test_word_preserves_partial_components_without_inventing_final_grade():
    from io import BytesIO
    from docx import Document
    from scripts.report_evidence import build_pack
    from scripts.professional_report import generate_docx
    r = bank(Inputs({'CAR': None}))
    p = build_pack('ABB')
    p['Sections'] = []
    with patch('scripts.professional_report.build_pack', return_value=p):
        doc = Document(BytesIO(generate_docx('ABB', 'rating', r)))
    scorecard = next(t for t in doc.tables if t.cell(0, 0).text == 'Cấu phần'
                     and len(t.columns) == 4 and t.cell(0, 1).text == 'Điểm / Đánh giá')
    rows = {row.cells[0].text: [c.text for c in row.cells] for row in scorecard.rows[1:]}
    assert rows['Vị thế Rủi ro'][1] == '2/6 • Mạnh'
    assert rows['Vốn và Lợi nhuận'][2] == '—'
    assert '2026-Q2' in rows['Vốn và Lợi nhuận'][3]
    assert rows['Huy động vốn và Thanh khoản'][1] == 'Phù Hợp / Phù Hợp (giả định)'
    assert rows['Kết quả'][1] == 'Chưa đủ căn cứ tổng hợp'
    assert 'Bậc xếp hạng ước tính' not in rows
