"""Hỗ trợ chỉ đúng đối tượng, không cộng chồng, không che lấp thiếu dữ liệu/rủi ro."""
from copy import deepcopy
import pytest
from scripts.bank_government_support import government_support, apply_bank_support, ELIGIBLE_BANKS
from scripts.three_methodology_rating import SCALE, move, label
from scripts.report_rating import rate_company


def base(ticker='VCB', sacp='a-', **extra):
    return dict(Methodology='BANK', Ticker=ticker, Period='2026-Q2', SACP=label(sacp),
                SCA=label(sacp), ICR=label(sacp), ExternalSupportNotches=0,
                ExternalSupportAssumed=True, Scorecard=[], **extra)


@pytest.mark.parametrize('ticker', sorted(ELIGIBLE_BANKS))
@pytest.mark.parametrize('sacp', ['aaa','aa','a-','bbb','bb','b-'])
def test_whitelist_limit_and_rating_arithmetic(ticker, sacp):
    r=apply_bank_support(base(ticker,sacp))
    expected=min(6,SCALE.index(sacp))
    assert r['GovernmentSupportNotches']==expected
    assert r['SACP']==label(sacp)
    assert r['ICR']==label(move(sacp,expected))
    assert r['ExternalSupportNotches']==expected


@pytest.mark.parametrize('ticker',['TCB','ABB','OCB','VPB','ACB','MBB','HDB','SSI','UNKNOWN'])
def test_no_government_notch_for_other_banks_even_manual(ticker):
    assert government_support(ticker,'a-','2026-Q2')['Notches']==0
    with pytest.raises(ValueError):government_support(ticker,'a-','2026-Q2',{'GovernmentSupportNotches':1})


@pytest.mark.parametrize('value',[-1,7,True,1.5,'3'])
def test_invalid_notch_is_rejected(value):
    with pytest.raises(ValueError):government_support('VCB','a-','2026-Q2',{'GovernmentSupportNotches':value})


def test_missing_standalone_cannot_become_aaa():
    r=base();r.update(SACP='N/A',SCA='N/A',ICR='N/A',RatingStatus='INSUFFICIENT_DATA')
    out=apply_bank_support(r)
    assert out['GovernmentSupportEligible']
    assert out['GovernmentSupportNotches'] is None
    assert out['ICR']=='N/A' and out['RatingStatus']=='INSUFFICIENT_DATA'


@pytest.mark.parametrize('status',['BREACH','SPECIAL_CONTROL','AT_RISK'])
def test_regulatory_limit_survives_all_support(status):
    r=apply_bank_support(base(sacp='b-',RegulatoryCap='vnB-'),
                         {'RegulatoryCapitalStatus':status,'OtherSupportNotches':4})
    assert r['GovernmentSupportNotches']==r['ExternalSupportNotches']==0
    assert r['ICR']=='vnB-'


def test_default_and_old_or_future_period_do_not_receive_automatic_support():
    assert apply_bank_support(base(),{'DefaultEventConfirmed':True})['GovernmentSupportNotches']==0
    for period in ['2025-Q4','2027-Q1']:
        r=base();r['Period']=period
        assert apply_bank_support(r)['GovernmentSupportAssessment']['Status']=='REVIEW_REQUIRED'


def test_idempotent_and_separate_from_other_support():
    original=base(sacp='bbb');saved=deepcopy(original)
    o={'GovernmentSupportNotches':2,'OtherSupportNotches':1}
    r=apply_bank_support(original,o)
    assert original==saved
    assert r['GovernmentSupportNotches']==2 and r['OtherSupportNotches']==1
    assert r['ICR']=='vnA'
    assert apply_bank_support(r,o)==r
    assert apply_bank_support(r)==r
    assert len([x for x in r['Scorecard'] if x['Cấu phần']=='Hỗ trợ từ Chính phủ'])==1


def test_explicit_old_total_zero_and_separate_other_zero_have_different_meanings():
    old=apply_bank_support(base(),{'ExternalSupportNotches':0})
    new=apply_bank_support(base(),{'OtherSupportNotches':0})
    assert old['ICR']=='vnA-' and old['GovernmentSupportNotches']==0
    assert new['ICR']=='vnAAA' and new['GovernmentSupportNotches']==6


def test_saved_manual_zero_and_regulatory_cap_are_preserved():
    r=base();r['ExternalSupportAssumed']=False
    out=apply_bank_support(r)
    assert out['GovernmentSupportNotches']==0
    assert out['ICR']=='vnA-'
    capped=apply_bank_support(base(sacp='a-',RegulatoryCap='vnB-'))
    assert capped['ICR']=='vnB-'


def test_support_assumption_does_not_contradict_positive_government_notches():
    r=base(Assumptions=['Hỗ trợ bên ngoài: giả định 0 bậc khi chưa có đánh giá riêng.'])
    out=apply_bank_support(r)
    assert out['GovernmentSupportNotches']==6
    assert not any(x.startswith('Hỗ trợ bên ngoài:') for x in out['Assumptions'])


def test_all_bank_routes_display_support_without_creating_agribank_financials():
    from scripts.universal_data import universe
    for ticker in universe().query("EntityType == 'BANK'").Ticker:
        r=rate_company(ticker)
        assert r['GovernmentSupportEligible']==(ticker in ELIGIBLE_BANKS)
        if ticker not in ELIGIBLE_BANKS:assert r['GovernmentSupportNotches']==0
        assert 'Hỗ trợ từ Chính phủ' in [x['Cấu phần'] for x in r['Scorecard']]
        if r['ICR']!='N/A':
            assert r['ExternalSupportNotches']==r['GovernmentSupportNotches']+r['OtherSupportNotches']
            assert r['ICR']==label(move(r['SACP'],r['ExternalSupportNotches']))
    a=rate_company('AGRIBANK')
    assert a['Methodology']=='BANK' and a['GovernmentSupportEligible']
    assert a['GovernmentSupportNotches'] is None and a['ICR']=='N/A'


def test_model_changes_do_not_add_government_support_to_other_industries():
    for ticker in ['SSI','ABI','HPG']:
        r=rate_company(ticker)
        assert 'GovernmentSupportNotches' not in r


def test_withdrawing_support_is_visible_in_sensitivity():
    from scripts.bank_report_chapters import rating_sensitivity
    r=rate_company('VCB')
    rows=rating_sensitivity(r)
    assert rows[-1][2]==r['SACP']


def test_word_includes_separate_support_and_model_assumption():
    from io import BytesIO
    from unittest.mock import patch
    from docx import Document
    from scripts.report_evidence import build_pack
    from scripts.professional_report import generate_docx
    p=build_pack('VCB');p['Sections']=[]
    with patch('scripts.professional_report.build_pack',return_value=p):
        d=Document(BytesIO(generate_docx('VCB','rating',rate_company('VCB'))))
    xml=d.element.xml
    for phrase in ['Hỗ trợ từ Chính phủ','Hỗ trợ cổ đông / khác','tối đa 6','giả định mới của mô hình']:
        assert phrase in xml
    assert 'Bảng 17 của phương pháp' not in xml
    summary=next(t for t in d.tables if any('Cấu phần' in c.text for c in t.rows[0].cells)
                 and any('Hỗ trợ từ Chính phủ' in c.text for row in t.rows for c in row.cells))
    names=[row.cells[0].text for row in summary.rows]
    assert names.index('SACP / SCA')<names.index('Hỗ trợ từ Chính phủ')<names.index('Bậc xếp hạng ước tính')
