"""Regressions: accounting ratios must not impersonate a liquidity assessment."""
from copy import deepcopy
from io import BytesIO
import json
from unittest.mock import patch

import pytest
from docx import Document
from scripts.bank_funding import observations, factor_assessment, funding_commentary
from scripts.report_rating import _financial_institution, rate_company
from scripts.bank_domestic_rating import source_fingerprint
from scripts.bank_report_chapters import component_scorecard


class Inputs:
    period='2026-Q2'; peers=[]
    def __init__(self, ldr):
        self.rows=[]; self.values={'CAR':.1495,'CASA':.35,'LDR':ldr}
    def value(self, key):return self.values.get(key)
    def peer_score(self, specs):return 3
    def add(self, metric, value, score=None, rule='', count=None):
        self.rows.append({'Metric':metric,'Chỉ tiêu':metric,'Giá trị':value,
                          'Điểm':score,'Cách chấm':rule,'Kỳ':self.period})


@pytest.mark.parametrize('ldr',[.8,1.0,1.2001,1.28,2.5])
def test_accounting_ldr_does_not_assign_weak_liquidity_or_bonus(ldr):
    r=_financial_institution('ANY','BANK',{},Inputs(ldr),{})
    assert r['LiquidityAssumed'] is True
    assert r['Liquidity']=='Phù Hợp'
    assert r['FactorNotches']['Huy động vốn và Thanh khoản']==0
    assert not r.get('FundingAssessment') and not r['AssessmentComplete']
    assert 'giả định' in component_scorecard(r)[-1]['Điểm / Đánh giá']


def test_absent_ratio_does_not_become_zero_or_confirmed_liquidity():
    r=_financial_institution('ANY','BANK',{},Inputs(None),{})
    assert r['ICR']=='N/A' and r['Liquidity'] is None


def test_tcb_partial_assessment_changes_sacp_not_car_or_external_support():
    r=rate_company('TCB')
    assert r['Funding']==r['Liquidity']=='Mạnh'
    assert r['FactorNotches']['Huy động vốn và Thanh khoản']==1
    assert r['SACP']==r['RawICR']=='vnA'
    assert r['DomesticCalibrationNotches']==2 and r['ICR']=='vnAA-'
    assert r['CARInput']['Value']==.1495 and r['ExternalSupportNotches']==0
    assert not r['AssessmentComplete'] and not r['LiquidityAssumed']
    assert r['FundingAssessmentOrigin']=='USER_CONFIRMED_FACTOR'
    assert not r['FundingAssessment']['StressTestIndependentlyVerified']


@pytest.mark.parametrize('ticker,period',[('ABB','2026-Q2'),('TCB','2025-Q4'),('TCB','2026-Q3'),('TCB','2026-06')])
def test_factor_never_crosses_entity_or_period(ticker,period):
    assert factor_assessment(ticker,period) is None


def test_official_regulatory_ratio_keeps_scope_and_exact_period():
    o=observations('TCB','2026-Q2')
    assert o['RegulatoryLDR']==.801 and o['Scope']=='BANK_ONLY'
    assert o['ShortTermFundingForLongLoans']==.278
    assert observations('TCB','2026-Q3') is None
    text=' '.join(funding_commentary('TCB','2026-Q2'))
    assert '80,1%' in text and '76,5%' in text and '4,8%' in text and '4,2%' in text


def test_invalid_source_value_and_duplicate_are_rejected(tmp_path):
    (tmp_path/'config').mkdir()
    path=tmp_path/'config/bank_funding_observations.json'
    row=observations('TCB','2026-Q2'); row['RegulatoryLDR']=80.1
    path.write_text(json.dumps({'Records':[row]}))
    with pytest.raises(ValueError,match='Invalid'):observations('TCB','2026-Q2',tmp_path)
    row['RegulatoryLDR']=.801
    path.write_text(json.dumps({'Records':[row,row]}))
    with pytest.raises(ValueError,match='Duplicate'):observations('TCB','2026-Q2',tmp_path)


def test_individual_manual_decision_takes_priority_and_disables_assumption():
    r=_financial_institution('TCB','BANK',{'Funding':'Mạnh','Liquidity':'Yếu'},Inputs(1.28),{})
    assert r['FactorNotches']['Huy động vốn và Thanh khoản']==-2
    assert not r.get('FundingAssessment') and not r.get('LiquidityAssumed')
    strict={'Factors':{'Huy động vốn và Thanh khoản':'Yếu'},
            'FactorNotches':{'Huy động vốn và Thanh khoản':-3}}
    r=_financial_institution('TCB','BANK',{},Inputs(1.28),strict)
    assert r['FactorNotches']['Huy động vốn và Thanh khoản']==-3


def test_positive_matrix_exception_is_not_inferred_from_strong_words():
    row=factor_assessment('TCB','2026-Q2');row['FundingStrongExceptionConfirmed']=False
    with patch('scripts.bank_funding.factor_assessment',return_value=row):
        r=_financial_institution('TCB','BANK',{},Inputs(1.28),{})
    assert r['FactorNotches']['Huy động vốn và Thanh khoản']==0


def test_both_new_sources_invalidate_export_cache(tmp_path):
    (tmp_path/'config').mkdir(); old=source_fingerprint(tmp_path)
    for name in ['bank_funding_observations.json','bank_funding_assessments.json']:
        (tmp_path/'config'/name).write_text('{}')
        new=source_fingerprint(tmp_path);assert new!=old;old=new


def test_word_and_app_share_factor_result_and_financial_reasoning():
    from scripts.report_evidence import build_pack
    from scripts.professional_report import generate_docx
    p=build_pack('TCB');p['Sections']=[('HUY ĐỘNG VỐN VÀ THANH KHOẢN',['LDR'])]
    r=rate_company('TCB')
    with patch('scripts.professional_report.build_pack',return_value=p):
        d=Document(BytesIO(generate_docx('TCB','rating',r)))
    text=d.element.xml
    assert '80,1%' in text and '27,8%' in text and '4,8%' in text
    assert 'Mạnh / Mạnh' in text and 'Mạnh / Yếu' not in text
    assert 'PHỤ LỤC: CĂN CỨ TÍNH ĐIỂM VÀ GIẢ ĐỊNH' in text
    assert '6T/' not in text and len(d.inline_shapes)==2
    assert not d.element.xpath('.//w:tbl//w:drawing')
    funding=component_scorecard(r,p)[-1]
    table=next(t for t in d.tables if t.cell(0,0).text=='Cấu phần' and len(t.columns)==4)
    actual=next(row for row in table.rows if row.cells[0].text==funding['Cấu phần'])
    assert [c.text for c in actual.cells]==list(funding.values())
