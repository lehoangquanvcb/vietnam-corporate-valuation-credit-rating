"""Hợp đồng xuất báo cáo chung: kỳ năm/quý, phạm vi peer, nhận định và kiểu chữ."""
from io import BytesIO
from unittest.mock import patch
import pandas as pd
import pytest
from docx import Document
from scripts.report_evidence import build_pack,narrative,finite
from scripts.report_methodology import GROUPS,REPORT_TITLE,RESEARCH_NOTE,LIMITATION_NOTE


@pytest.fixture(scope='module',params=['TCB','SSI','FPT','ABI','BVH'])
def pack(request):return build_pack(request.param)


def test_annual_history_and_quarter_comparison_for_all_four_types(pack):
    from scripts.financial_evidence import at_period
    assert list(dict(pack['Sections']))==list(GROUPS[pack['Type']])
    all_metrics=[m for _,metrics in pack['Sections'] for m in metrics]
    assert len(all_metrics)==len(set(all_metrics))
    assert pack['Ticker'] not in pack['PeerUniverse']
    end=int(pack['Period'][:4])-(pack['Period'][-1]!='4')
    for m,x in pack['Items'].items():
        assert x['History'].DisplayPeriod.tolist()==[str(y) for y in range(end-4,end+1)]
        assert x['History'].Period.str.endswith('-Q4').all()
        assert pack['Ticker'] not in [r['Ticker'] for r in x['Peers']]
        if m=='NPAT':
            assert x['Value']==pytest.approx(at_period(pack['Ticker'],pack['Type'],pack['Period'],'QUARTER')[m]['Value'])
        for r in x['History'].itertuples():
            if pd.notna(r.PeerMean):assert r.PeerCount>=5


def test_every_active_metric_produces_financial_narrative(pack):
    for m,x in pack['Items'].items():
        if not finite(x['Value']) and not x['History'].Value.notna().any():continue
        n=narrative(pack,m)
        assert n['History'] and n['Peers'] and (n['Meaning'] or n['Conclusion'])
        assert '6T/' not in n['History']
        assert not any(b in n['Meaning'] for b in ['Bảng 12','Bảng 18','chỉ tiêu được định nghĩa'])


def test_shared_export_has_exact_requested_text_and_vertical_charts(pack):
    from scripts.professional_report import generate_docx
    from scripts.three_methodology_rating import rate_company
    p=dict(pack);m='NPAT';p['Sections']=[('Kiểm tra lợi nhuận',[m])]
    rr=rate_company(p['Ticker'])
    with patch('scripts.professional_report.build_pack',return_value=p):
        d=Document(BytesIO(generate_docx(p['Ticker'],'rating',rr)))
    xml=d.element.xml
    for text in [REPORT_TITLE,RESEARCH_NOTE,LIMITATION_NOTE]:assert text in xml
    assert 'mô phỏng quá trình' not in xml.lower()
    assert len(d.inline_shapes)==2
    assert not d.element.xpath('.//w:tbl//w:drawing')
    assert '4F9E1E' in xml and 'E6F3D8' in xml
    assert all(s.width.mm>170 for s in d.inline_shapes)
    captions=[p.text for p in d.paragraphs]
    assert captions.index('BCTC 5 năm gần nhất và bình quân peer') < next(i for i,s in enumerate(captions) if s.startswith(pack['Period']+' • '))
    if p['Ticker']!='TCB':assert 'Kết quả xếp hạng AA+' not in xml


def test_insurance_adapter_keeps_history_breaks_and_narrow_metric_scope():
    p=build_pack('BVH')
    for m,x in p['Items'].items():
        original=x['InsurancePair']
        assert x['HistoryBreaks']==original['HistoryBreaks']
        included=original['Peers'].iloc[1:]
        expected=included[included.Included & included.Status.eq('OK')].Ticker.tolist()
        assert [r['Ticker'] for r in x['Peers']]==expected


def test_no_year_growth_across_missing_year_or_source_break():
    from scripts.report_insights import enrich_narrative
    p=build_pack('ABI');x=p['Items']['InsuranceReserves']
    x['HistoryBreaks']=[4]
    n=narrative(p,'InsuranceReserves')
    assert 'Tốc độ tăng trưởng bình quân' not in n['History']
    assert 'dự phòng tăng' not in n['Meaning'].lower()


def test_negative_cashflow_is_not_a_strength_even_when_less_negative_than_peers():
    from scripts.report_evidence import findings
    p={'Items':{'CFO_Debt':{'Value':-.02,'PeerMean':-.5}}}
    strengths,risks=findings(p)
    assert strengths==[] and 'Giá trị còn âm' in risks[0]


def test_all_registered_tickers_have_one_of_four_report_methods():
    from scripts.universal_data import universe
    u=universe()
    assert len(u)>1000
    assert set(u.EntityType)<=set(GROUPS)
    for typ in set(u.EntityType):assert GROUPS[typ]


@pytest.mark.parametrize('typ',list(GROUPS))
def test_no_source_data_does_not_crash_or_invent_years_and_grade(typ):
    from scripts.professional_report import generate_docx
    with patch('scripts.report_evidence.get_company',return_value={'EntityType':typ,'DisplayName':'Không có nguồn'}),patch('scripts.report_evidence.latest_period',return_value=None):
        p=build_pack('ZZTEST')
    assert p['Period'] is None
    assert all(x['History'].empty and x['Value'] is None for x in p['Items'].values())
    with patch('scripts.professional_report.build_pack',return_value=p):
        d=Document(BytesIO(generate_docx('ZZTEST','rating',{'ICR':'N/A'})))
    assert len(d.inline_shapes)==0
    assert '2021–2025' not in d.element.xml and 'AA+' not in d.element.xml
