"""Four-component methodology, precision, adjustments and shared exports."""
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
import pandas as pd
import pytest
from docx import Document
from scripts.corporate_methodology import (RISK_KEYS, RISK_TITLES, DEFAULT_WEIGHTS,
    weighted_profile, rating_from_score, validated_weights, apply_adjustments, scorecard)


def test_vic_example_is_sum_of_four_contributions_not_industry_anchor():
    p=weighted_profile(dict(zip(RISK_KEYS,[3,3.1,4.375,3])))
    assert Decimal(p['WeightedScoreExact'])==Decimal('3.51125')
    assert p['InitialRating']=='vnBBB-'
    assert [r['Contribution'] for r in p['WeightedContributions']]==[.6,.93,1.53125,.45]
    assert not {'Anchor','SACP','SCA'} & p.keys()


@pytest.mark.parametrize('i',range(16))
def test_mapping_boundary_uses_unrounded_weighted_total(i):
    boundary=Decimal('1')+i*Decimal('.3125')
    p=weighted_profile(dict.fromkeys(RISK_KEYS,boundary))
    above=weighted_profile(dict.fromkeys(RISK_KEYS,boundary+Decimal('.000000001')))
    assert p['InitialRating']!=above['InitialRating']
    assert p['InitialRating']=='vn'+rating_from_score(boundary).upper()


def test_new_weight_set_changes_calculation_without_changing_scores():
    points=dict(zip(RISK_KEYS,[4,1,2,1]))
    default=weighted_profile(points)
    other=weighted_profile(points,dict(zip(RISK_KEYS,[.1,.4,.4,.1])))
    assert default['WeightedScore']==pytest.approx(1.95)
    assert other['WeightedScore']==pytest.approx(1.7)
    assert points==dict(zip(RISK_KEYS,[4,1,2,1]))
    # The VHM reference gives these four scores and vnAA but no factor weights.
    # We must not change weights or hard-code vnAA to reproduce its conclusion.
    assert default['InitialRating']=='vnA+'


@pytest.mark.parametrize('weights',[
    {'IndustryRisk':1},dict.fromkeys(RISK_KEYS,.3),
    dict(zip(RISK_KEYS,[-.1,.5,.4,.2])),dict(zip(RISK_KEYS,[True,0,0,0])),
    dict(zip(RISK_KEYS,[float('nan'),.3,.35,.15]))])
def test_invalid_weights_are_rejected(weights):
    with pytest.raises(ValueError):validated_weights(weights)


@pytest.mark.parametrize('value',[True,0,6.1,float('inf'),'unknown'])
def test_invalid_factor_does_not_generate_rating(value):
    with pytest.raises(ValueError):weighted_profile({**dict.fromkeys(RISK_KEYS,3),'IndustryRisk':value})


def test_missing_factor_is_visible_and_prevents_total():
    p=weighted_profile(dict(zip(RISK_KEYS,[3,2,None,3])))
    assert p['WeightedScore'] is None and p['InitialRating']=='N/A'
    assert p['MissingRiskGroups']==['FinancialRisk']
    assert p['WeightedContributions'][0]['Contribution']==.6
    assert scorecard(p)[-1]['Kết quả / Căn cứ']=='Chưa đủ căn cứ tổng hợp'


@pytest.mark.parametrize('governance,cap',[(4,'vnBB+'),(5,'vnBB-'),(6,'vnB')])
def test_source_governance_caps(governance,cap):
    r=apply_adjustments('vnAA',governance)
    assert r['ICR']==cap and r['AdjustmentScorecard']


@pytest.mark.parametrize('initial,liquidity,policy,expected',[
    ('vnAA','Phù hợp',None,'vnAA'),('vnAA','Trung Bình',None,'vnAA'),('vnAA','Dưới trung bình',None,'vnAA'),
    ('vnBB+','Dưới trung bình',None,'vnBB+'),('vnBB-','Dưới trung bình',None,'vnBB-'),
    ('vnB+','Dưới trung bình',None,'vnB+'),('vnA','Yếu',None,'vnA'),
    ('vnB','Mạnh',None,'vnB+'),('vnB','Mạnh',True,'vnB+'),('vnB','Mạnh',False,'vnB+'),
    ('vnA','Rất Mạnh',None,'vnAA-')])
def test_liquidity_level_input_uses_uplift_only_rule(initial,liquidity,policy,expected):
    assert apply_adjustments(initial,3,liquidity=liquidity,financial_policy_weak=policy)['ICR']==expected


def test_adjustments_are_separate_from_weighted_total():
    p=weighted_profile(dict.fromkeys(RISK_KEYS,2.5));before=dict(p)
    r={**p,**apply_adjustments(p['InitialRating'],2.5,support=1)}
    assert r['WeightedScore']==2.5 and r['InitialRating']=='vnA'
    assert r['ICR']=='vnA+' and r['AdjustmentScorecard'][0]['Tác động']=='+1 bậc'
    assert p==before
    assert apply_adjustments(p['InitialRating'],2.5)['ICR']==p['InitialRating']


def test_both_entry_points_use_same_weighted_method_with_same_inputs():
    from scripts.report_rating import rate_company as research
    from scripts.three_methodology_rating import rate_company as assessed
    inputs={**dict(zip(RISK_KEYS,[3,1.81,3.5625,3])),
            'Weights':DEFAULT_WEIGHTS,'ModifierNotches':0,'ExternalSupportNotches':0}
    r=research('HPG',inputs);s=assessed('HPG',inputs)
    for key in ['WeightedScoreExact','InitialRating','ICR','WeightedContributions']:
        assert r[key]==s[key]
    for result in [r,s]:assert not {'Anchor','SCA','SACP'} & result.keys()


@pytest.mark.parametrize('ticker',['VIC','HPG','VHM','FPT','VNM'])
def test_real_company_scorecard_is_four_weighted_groups(ticker):
    from scripts.report_rating import rate_company
    r=rate_company(ticker)
    assert r['Methodology']=='CORPORATE' and r['ICR']!='N/A'
    assert r['WeightedScore']==pytest.approx(sum(x['Contribution'] for x in r['WeightedContributions']))
    assert list(r['RiskScores'])==RISK_TITLES
    assert all('Tỷ trọng' in row and 'Điểm đóng góp' in row for row in r['Scorecard'])
    assert not {'Anchor','SCA','SACP'} & r.keys()
    assert 'Anchor' not in str(r['Scorecard'])+r['Audit']
    assert 'cấu hình nghiên cứu' in r['WeightSource']


def test_corporate_word_has_one_weighted_table_no_bank_chain_and_two_charts():
    from scripts.professional_report import generate_docx
    from scripts.report_evidence import build_pack
    from scripts.report_rating import rate_company
    p=build_pack('HPG');p['Sections']=[('Hiệu quả kinh doanh',['Revenue'])]
    r=rate_company('HPG')
    with patch('scripts.professional_report.build_pack',return_value=p):
        doc=Document(BytesIO(generate_docx('HPG','rating',r,{'export_date':'2026-11-06'})))
    assert len(doc.inline_shapes)==2
    tables=[t for t in doc.tables if len(t.columns)==5 and 'Điểm đóng góp' in t.rows[0].cells[-2].text] # five-column scorecard
    assert len(tables)==1
    assert len(tables[0].rows)==9
    text=doc.element.xml
    assert 'Tổng điểm có trọng số' in text and 'Bậc xếp hạng ban đầu' in text
    assert all(label not in text for label in ['Anchor','SACP','SCA'])
