"""Hồi quy bảng chấm nguồn, cách ly mã/kỳ và bố cục báo cáo tham chiếu."""
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import json
import pytest
from docx import Document
from scripts.rating_reference import parse_bank_reference
from scripts.bank_method_2026 import bank_rating,saved_assessment

ROOT=Path(__file__).resolve().parents[1]


def source_bytes(change=None):
    row=json.loads((ROOT/'config/bank_rating_references.json').read_text())['assessments'][0]
    rows=[list(r) for r in row['SourceScorecard']]
    if change:change(rows)
    d=Document();d.add_paragraph('Ngân hàng Techcombank (TCB) | 2026-Q2')
    t=d.add_table(rows=1,cols=4)
    for c,s in zip(t.rows[0].cells,['Cấu phần','Đánh giá','Nâng/hạ notch','Kết quả']):c.text=s
    for row in rows:
        for c,s in zip(t.add_row().cells,row):c.text=s
    out=BytesIO();d.save(out);return out.getvalue()


def test_parsed_reference_recomputes_aa_plus_from_five_notches():
    row=parse_bank_reference(source_bytes(),'TCB','2026-Q2','fixture.docx')
    assert row['ReferenceICR']==row['ReferenceSACP']=='vnAA+'
    assert row['BusinessProfileNotches']==2
    assert row['ExternalSupportNotches']==0 and row['Outlook']=='Ổn định'
    assert len(row['SourceSHA256'])==64


@pytest.mark.parametrize('ticker,period',[('VCB','2026-Q2'),('TCB','2025-Q4'),('TCB','2026-06')])
def test_wrong_ticker_or_period_is_rejected(ticker,period):
    with pytest.raises(ValueError):parse_bank_reference(source_bytes(),ticker,period,'fixture.docx')


@pytest.mark.parametrize('change',[
    lambda r:r.pop(1),lambda r:r.append(r[1]),
    lambda r:r[-1].__setitem__(3,'AAA'),lambda r:r[-3].__setitem__(2,'+4'),
    lambda r:r[1].__setitem__(2,'+1')])
def test_inconsistent_scorecard_is_rejected(change):
    with pytest.raises(ValueError):parse_bank_reference(source_bytes(change),'TCB','2026-Q2','fixture.docx')


def test_exact_tcb_reference_and_manual_changes_are_not_fixed_rating():
    r=bank_rating('TCB')
    assert r['ICR']=='vnAA+' and r['InternalNotches']==5
    assert r['RatingOrigin']=='REFERENCE_REPORT'
    assert r['AssessmentSource']=='TCB_XHTN(1).docx'
    assert bank_rating('TCB',{'CapitalEarnings':'Phù Hợp'})['ICR']=='vnAA'
    assert bank_rating('TCB',{'UseSavedAssessment':False})['ICR']=='N/A'
    assert bank_rating('TCB',{'Funding':'Mạnh'})['ICR']=='N/A'
    assert bank_rating('VCB')['ICR']=='N/A'
    assert saved_assessment('TCB','2026-Q3')=={}


def test_manual_saved_assessment_has_priority(tmp_path):
    import scripts.bank_method_2026 as mod
    (tmp_path/'config').mkdir()
    reference=json.loads((ROOT/'config/bank_rating_references.json').read_text())
    (tmp_path/'config/bank_rating_references.json').write_text(json.dumps(reference))
    manual=dict(reference['assessments'][0],Source='Manual assessment',SourceType='ASSESSMENT',CapitalEarnings='Phù Hợp',CapitalEarningsNotches=0)
    (tmp_path/'config/bank_rating_assessments.json').write_text(json.dumps({'assessments':[manual]}))
    with patch.object(mod,'ROOT',tmp_path):
        r=bank_rating('TCB');assert r['ICR']=='vnAA' and r['RatingOrigin']=='ASSESSMENT'


@pytest.mark.parametrize('grade,n',[('Yếu',-3),('Rất Yếu',-5)])
def test_legacy_combined_funding_preserves_explicit_negative_notch(grade,n):
    assert bank_rating('TCB',{'FundingLiquidity':grade,'FundingLiquidityNotches':n})['FactorNotches']['Huy động vốn và Thanh khoản']==n


def test_reference_word_has_rating_chapters_notches_annuals_and_source():
    from scripts.report_evidence import build_pack
    from scripts.professional_report import generate_docx
    p=build_pack('TCB');p['Sections']=[('HUY ĐỘNG VỐN VÀ THANH KHOẢN',['CASA'])]
    with patch('scripts.professional_report.build_pack',return_value=p):
        d=Document(BytesIO(generate_docx('TCB','rating')))
    xml=d.element.xml
    for text in ['AA+','Ổn định','TCB_XHTN(1).docx','LUẬN ĐIỂM XẾP HẠNG','ĐỘ NHẠY XẾP HẠNG','TỔNG KẾT CẤU PHẦN XẾP HẠNG','2021','2025','2026-Q2']:
        assert text in xml
    assert '6T/' not in xml and 'Chưa thẩm định' not in xml
    assert not d.element.xpath('.//w:tbl//w:drawing')
    assert len(d.inline_shapes)==2
    scorecard=next(t for t in d.tables if len(t.columns)==4 and t.cell(0,0).text=='Cấu phần')
    assert next(r for r in scorecard.rows if r.cells[0].text=='Tổng điều chỉnh nội sinh').cells[2].text=='+5'


def test_tcb_chapter_reasoning_identifies_strengths_and_deterioration():
    from scripts.report_evidence import build_pack
    from scripts.bank_report_chapters import chapter_findings,rating_sensitivity
    p=build_pack('TCB')
    capital=' '.join(chapter_findings(p,'Vốn và Lợi nhuận'))
    funding=' '.join(chapter_findings(p,'Huy động vốn và Thanh khoản'))
    assert 'ROE thấp hơn đi cùng ROA cao hơn' in capital
    assert 'lợi thế nguồn vốn không kỳ hạn' in funding and 'giảm' in funding
    assert rating_sensitivity(bank_rating('TCB'))[0][2]=='vnAA'
