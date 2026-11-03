"""Không đánh đồng mức đích hiệu chỉnh, điểm tài chính và ý kiến CRA."""
from copy import deepcopy
from io import BytesIO
import json
from unittest.mock import patch

import pytest
from docx import Document

from scripts.bank_domestic_rating import apply_calibration, load_policy, source_fingerprint, benchmark_for
from scripts.report_rating import rate_company, _base_rate_company
from scripts.three_methodology_rating import SCALE, move, label


@pytest.mark.parametrize('ticker,expected',[
    ('VCB','vnAAA'),('BID','vnAAA'),('CTG','vnAAA'),('TCB','vnAA-'),
    ('VPB','vnAA-'),('ACB','vnAA-'),('ABB','vnA-')])
def test_requested_targets_preserve_financial_inputs_and_explain_notch(ticker,expected):
    r=rate_company(ticker)
    raw=r['PreCalibrationResult']
    assert r['ICR']==expected and r['RatingStatus']=='CALIBRATED_ESTIMATE'
    assert not r['AssessmentComplete']
    for key in ['CARInput','SACP','Factors','FactorNotches','QuantitativeEvidence','ExternalSupportNotches']:
        assert r[key]==raw[key]
    assert label(move(r['RawICR'],r['DomesticCalibrationNotches']))==r['ICR']
    assert 'chủ mô hình' in r['Scorecard'][-1]['Kết quả / Căn cứ'] or 'Mức đích của mô hình' in r['Scorecard'][-1]['Kết quả / Căn cứ']
    assert 'không phải kết luận' in r['RatingBasisNote']


def test_tcb_uses_same_automatic_method_and_old_reference_can_be_reproduced():
    r=rate_company('TCB')
    old=rate_company('TCB',{'UseDomesticCalibration':False})
    auto=_base_rate_company('TCB',{'UseSavedAssessment':False})
    assert old['ICR']==r['LegacyReference']['ICR']=='vnAA+'
    assert r['LegacyReference']['UsedForCurrentRating'] is False
    assert r['RawICR']==auto['ICR'] and r['Factors']==auto['Factors']
    assert r['CARInput']['Value']==.1495
    assert 'UseDomesticCalibration' not in old


@pytest.mark.parametrize('ticker',['OCB','KLB','STB'])
def test_lower_group_keeps_differentiation_and_cannot_exceed_a_minus(ticker):
    r=rate_company(ticker); raw=_base_rate_company(ticker)
    assert r['ICR']==raw['ICR']
    assert SCALE.index(r['ICR'][2:].lower())>=SCALE.index('a-')
    boosted=dict(raw,ICR='vnAA')
    capped=apply_calibration(boosted,ticker)
    assert capped['ICR']=='vnA-' and capped['DomesticCalibrationNotches']<0
    assert boosted['ICR']=='vnAA'


@pytest.mark.parametrize('changes,status',[
    ({'ICR':'N/A','DataSufficientForAutoRating':False,'MissingEvidence':{'CAR':'missing'}},'MISSING_EVIDENCE'),
    ({'RegulatoryCap':'vnB-'},'RISK_LIMIT'),
    ({'DefaultEventConfirmed':True},'RISK_LIMIT'),
    ({'CARInput':{'Value':.04}},'RISK_LIMIT'),
    ({'RegulatoryCapitalStatus':'SPECIAL_CONTROL'},'RISK_LIMIT'),
    ({'AssessmentSource':'manual.json','RatingOrigin':'AUTO_RESEARCH'},'MANUAL_PRIORITY')])
def test_target_never_overrides_missing_data_risk_limits_or_partial_saved_assessment(changes,status):
    base=_base_rate_company('VCB');base.update(changes);before=deepcopy(base)
    r=apply_calibration(base,'VCB')
    assert r['ICR']==base['ICR'] and not r['DomesticCalibrationApplied']
    assert r['DomesticCalibrationStatus']==status and base==before


def test_manual_changes_are_not_erased_by_target_and_can_be_removed():
    manual={'BusinessProfile':'Yếu'}
    r=rate_company('VCB',manual)
    assert r['ICR']==_base_rate_company('VCB',manual)['ICR']
    assert r['Factors']['Hồ sơ Kinh doanh']=='Yếu'
    assert r['DomesticCalibrationStatus']=='MANUAL_PRIORITY'
    assert rate_company('VCB')['ICR']=='vnAAA'


def test_saved_complete_manual_bank_assessment_has_priority(tmp_path,monkeypatch):
    import scripts.bank_method_2026 as bank
    (tmp_path/'config').mkdir()
    row={'Ticker':'VCB','Period':'2026-Q2','Source':'Phiếu riêng','Rationale':'Đánh giá riêng',
         'BusinessProfile':'Phù Hợp','CapitalEarnings':'Phù Hợp','RiskPosition':'Phù Hợp',
         'FundingLiquidity':'Phù Hợp','ExternalSupportNotches':0}
    (tmp_path/'config/bank_rating_assessments.json').write_text(json.dumps({'assessments':[row]}))
    monkeypatch.setattr(bank,'ROOT',tmp_path)
    r=rate_company('VCB')
    assert r['ICR']=='vnA-' and r['DomesticCalibrationStatus']=='MANUAL_PRIORITY'


def test_disabled_policy_returns_legacy_without_mutation():
    base=_base_rate_company('VCB');p=load_policy();p['Enabled']=False
    assert apply_calibration(base,'VCB',policy=p) is base


def test_benchmarks_keep_acb_difference_and_withdrawals_and_agribank_reference_only():
    assert rate_company('ACB')['ICR']=='vnAA-'
    assert benchmark_for('ACB')['Grade']=='AA+'
    assert benchmark_for('ABB')['Status']=='WITHDRAWN'
    assert benchmark_for('OCB')['Status']=='WITHDRAWN'
    p=load_policy();ag=p['UnlistedReferences'][0]
    assert ag['EntityId']=='AGRIBANK' and ag['Grade']=='AAA'
    assert ag['FinancialRatingAvailable'] is False
    from scripts.universal_data import universe
    assert 'AGRIBANK' not in set(universe().Ticker)
    assert rate_company('AGRIBANK')['ICR']=='N/A'


@pytest.mark.parametrize('ticker',['SSI','ABI','HPG','BVH'])
def test_other_sectors_unchanged(ticker):
    assert rate_company(ticker)==_base_rate_company(ticker)


def test_config_and_reference_change_invalidate_download(tmp_path):
    (tmp_path/'config').mkdir()
    before=source_fingerprint(tmp_path)
    path=tmp_path/'config/bank_domestic_calibration.json'
    path.write_text(json.dumps(load_policy()))
    first=source_fingerprint(tmp_path)
    assert first!=before
    p=load_policy();p['Profiles'][0]['Grade']='AA+'
    path.write_text(json.dumps(p));assert source_fingerprint(tmp_path)!=first
    prior=source_fingerprint(tmp_path)
    (tmp_path/'config/bank_domestic_benchmarks.json').write_text('{"References":[]}')
    assert source_fingerprint(tmp_path)!=prior
    p['Profiles'][0]['Grade']='Ba2';path.write_text(json.dumps(p))
    with pytest.raises(ValueError):load_policy(tmp_path)


def test_word_shows_raw_final_and_reference_without_false_support_identity():
    from scripts.report_evidence import build_pack
    from scripts.professional_report import generate_docx
    from scripts.bank_report_chapters import rating_sensitivity
    p=build_pack('ACB');p['Sections']=[]
    r=rate_company('ACB')
    with patch('scripts.professional_report.build_pack',return_value=p):
        d=Document(BytesIO(generate_docx('ACB','rating',r)))
    xml=d.element.xml
    for phrase in ['Bậc hiệu chỉnh trong nước','BBB-','AA-','AA+','Hiệu chỉnh thang trong nước','không phải kết luận','2021','2025']:
        assert phrase in xml
    assert 'ICR bằng SACP khi không cộng' not in xml
    assert 'ICR sau hiệu chỉnh' in xml
    assert rating_sensitivity(r)[0][2]==label(move(r['RawICR'],-1))
