"""Regression: withdrawn ticker targets cannot affect calculation or documents."""
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch
import pytest
from docx import Document
from scripts.bank_domestic_rating import apply_calibration,load_policy
from scripts.report_rating import rate_company,_base_rate_company
from scripts.bank_factor_evidence import support_notches

@pytest.mark.parametrize('ticker',['VCB','BID','CTG','TCB','VPB','ACB','ABB','OCB','KLB','STB','SSI','ABI','HPG','BVH'])
def test_no_ticker_target_or_legacy_flag(ticker):
    r=rate_company(ticker)
    base=_base_rate_company(ticker)
    assert r['SACP']==base.get('SACP') if 'SACP' in r else r==base
    assert rate_company(ticker,{'UseDomesticCalibration':True})==r
    assert rate_company(ticker,{'UseDomesticCalibration':False})==r
    assert 'DomesticCalibrationApplied' not in r
    assert not any('hiệu chỉnh' in str(row).lower() for row in r.get('Scorecard',[]))

def test_compatibility_hook_cannot_revive_targets():
    base={'ICR':'vnBBB','SACP':'vnBBB','Factors':{'x':'Phù Hợp'}}
    before=deepcopy(base);p=load_policy();p['Enabled']=True
    assert apply_calibration(base,'VCB',policy=p)==before
    assert base==before and load_policy()['Enabled'] is False

@pytest.mark.parametrize('sca,expected',[('a-',3),('a',2),('a+',1),('aa-',1),('aa',1),('aa+',0),('aaa',0)])
def test_government_support_is_method_table_not_fixed_aaa(sca,expected):
    assert support_notches('VCB',sca)==expected
    assert support_notches('TCB',sca)==0

def test_manual_factor_and_support_override_auto():
    r=rate_company('VCB',{'BusinessProfile':'Yếu','ExternalSupportNotches':0})
    assert r['Factors']['Hồ sơ Kinh doanh']=='Yếu'
    assert r['ExternalSupportNotches']==0
    assert r['GovernmentSupportNotches']==0
    assert r['GovernmentSupportAssessment']['Status']=='DISABLED'
    assert r['ICR']==r['SACP']

def test_word_has_no_calibration_and_sensitivity_recomputes_support():
    from scripts.report_evidence import build_pack
    from scripts.professional_report import generate_docx
    from scripts.bank_report_chapters import rating_sensitivity
    from scripts.three_methodology_rating import move,label
    p=build_pack('VCB');p['Sections']=[];r=rate_company('VCB')
    with patch('scripts.professional_report.build_pack',return_value=p):
        d=Document(BytesIO(generate_docx('VCB','rating',r)))
    assert 'Hiệu chỉnh thang trong nước' not in d.element.xml
    assert 'ICR sau hiệu chỉnh' not in d.element.xml
    from scripts.bank_government_support import apply_bank_support
    sca=label(move(r['SACP'],-1))
    assert rating_sensitivity(r)[0][2]==apply_bank_support(dict(r,SACP=sca))['ICR']
