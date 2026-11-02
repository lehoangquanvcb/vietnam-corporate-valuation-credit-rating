"""Kiểm tra kỳ peer, nguồn thiếu, số 0 và luồng xuất báo cáo thực tế."""
from io import BytesIO
from unittest.mock import patch
import math
import pandas as pd
import pytest
from docx import Document
from docx.oxml.ns import qn
from scripts import report_evidence as evidence


def sample_pack(peer_count=5, stale=None, mismatch=None):
    peers=['P'+str(i) for i in range(peer_count)]
    def record(t,typ,period,basis):
        return {'NPAT':{'Value':0.0 if t=='AAA' else 10.0,'Status':'OK',
            'Basis':'YTD' if t==mismatch else basis,
            'Period':'2025-Q2' if t==stale else period,'Source':'fixture','Reason':''}}
    history=pd.DataFrame([{'Metric':'NPAT','Value':v,'Status':'OK' if v is not None else 'MISSING',
        'Basis':'YTD','Period':str(y)+'-Q2','DisplayPeriod':'6T/'+str(y),'Reason':'','Source':'fixture'}
        for y,v in [(2024,10.),(2025,None),(2026,0.)]])
    with patch.multiple(evidence,get_company=lambda t:{'EntityType':'BANK'},peer_tickers=lambda t:['AAA']+peers+['AAA'],
            latest_period=lambda *a:'2026-Q2',at_period=record,same_period_history=lambda *a,**k:history,
            comparable_model=lambda *a:True,GROUPS={'BANK':{'Hoạt động':['NPAT','NPAT']}},HISTORY_METRICS={'BANK':['NPAT']}):
        return evidence.build_pack('AAA')


def test_peer_excludes_issuer_and_keeps_real_zero():
    p=sample_pack();x=p['Items']['NPAT']
    assert p['PeerUniverse']==['P0','P1','P2','P3','P4']
    assert x['Value']==0.0 and x['PeerCount']==5 and x['PeerMean']==10
    assert math.isnan(x['History'].Value.iloc[1])
    assert '10,0' not in evidence.delta_text('NPAT',0,2e9) # Không chia cho 0.


@pytest.mark.parametrize('kwargs',[{'peer_count':4},{'stale':'P0'},{'mismatch':'P0'}])
def test_mean_requires_five_same_period_and_basis(kwargs):
    x=sample_pack(**kwargs)['Items']['NPAT']
    assert x['PeerCount']==4 and x['PeerMean'] is None


def test_negative_base_does_not_create_misleading_growth():
    assert 'thay đổi tuyệt đối' in evidence.delta_text('NPAT',-1e9,1e9)
    assert 'điểm phần trăm' in evidence.delta_text('NPL',.02,.01)


def test_vcb_quarter_not_ttm_and_no_stale_car():
    from scripts.financial_evidence import at_period
    p=evidence.build_pack('VCB');x=p['Items']['NPAT']
    expected=at_period('VCB','BANK',p['Period'],'QUARTER')['NPAT']['Value']
    assert x['Value']==expected
    assert x['Value']!=at_period('VCB','BANK',p['Period'],'TTM')['NPAT']['Value']
    for row in x['Peers']:
        assert row['Value']==at_period(row['Ticker'],'BANK',p['Period'],'QUARTER')['NPAT']['Value']
    assert p['Items']['CAR']['Value'] is None
    assert p['Items']['CAR']['History'].Value.isna().all() # Không dùng CAR quý 2 làm số cuối năm.
    metrics=[m for _,ms in p['Sections'] for m in ms]
    assert len(metrics)==len(set(metrics))


@pytest.mark.parametrize('ticker',['VCB','SSI','FPT'])
def test_all_sectors_expose_financial_reasoning(ticker):
    p=evidence.build_pack(ticker)
    for m,x in p['Items'].items():
        n=evidence.narrative(p,m)
        assert all(n[k] for k in ['History','Peers','Conclusion'])
        assert isinstance(n['Meaning'],str)
        assert ticker not in [r['Ticker'] for r in x['Peers']]
        assert x['PeerMean'] is None or x['PeerCount']>=5


def test_export_uses_green_layout_vertical_charts_and_passed_rating():
    from scripts.multisector_report import generate_docx
    p=evidence.build_pack('VCB');p['Sections']=[('Chất lượng tài sản',['NPL'])]
    # Rút danh mục để kiểm tra bố cục nhanh; bảng lịch sử vẫn dùng dữ liệu thật.
    rr={'ICR':'N/A','Anchor':'vnA-','Factors':{},'Outlook':'Chưa thẩm định','MissingEvidence':{'BusinessProfile':'Thiếu hồ sơ'}}
    with patch('scripts.professional_report.build_pack',return_value=p):
        doc=Document(BytesIO(generate_docx('VCB','rating',rr)))
    assert len(doc.inline_shapes)==2
    assert all(s.width.mm>170 for s in doc.inline_shapes)
    assert not doc.element.xpath('.//w:tbl//w:drawing')
    xml=doc.element.xml
    assert 'E6F3D8' in xml and '4F9E1E' in xml and 'Lato' in xml
    assert 'vnAA+' not in xml and 'BusinessProfile' not in xml
    assert 'Thu nhập lãi thuần' in xml and 'EBIT = ' not in xml
    assert abs(doc.sections[0].page_width.mm-210)<0.02
    for t in doc.tables:
        # Bảng dữ liệu cần lặp tiêu đề; khối bìa và tóm tắt là bảng bố cục.
        if len(t.rows)>1:
            assert t.rows[0]._tr.find(qn('w:trPr')).find(qn('w:tblHeader')) is not None


def test_insurance_export_uses_shared_renderer():
    from scripts.insurance_report import generate_insurance_docx
    with patch('scripts.professional_report.generate_docx',return_value=b'shared') as render:
        assert generate_insurance_docx('BVH','rating',{'ICR':'N/A'},{'history_basis':'FY'})==b'shared'
        render.assert_called_once_with('BVH','rating',{'ICR':'N/A'},{'history_basis':'FY'})


def test_analysis_export_keeps_valuation_with_missing_values():
    from scripts.professional_report import _valuation
    doc=Document()
    _valuation(doc,evidence.build_pack('VCB'))
    assert any('ĐỊNH GIÁ' in p.text for p in doc.paragraphs)
    assert len(doc.tables)==1


def test_flow_history_mean_accepts_exact_multi_quarter_window():
    p=evidence.build_pack('VCB')
    h=p['Items']['NPAT']['History']
    assert h.PeerMean.notna().all() and h.PeerCount.ge(5).all()
    assert evidence.window_ends_at('2026-Q1|2026-Q2','2026-Q2')
    assert not evidence.window_ends_at('2025-Q1|2025-Q2','2026-Q2')
