from io import BytesIO
from unittest.mock import patch
import pandas as pd
import pytest
from docx import Document
from scripts.report_evidence import build_pack,narrative
from scripts.bank_method_2026 import bank_rating,car_grade,FUNDING_GRADES,FUNDING_MATRIX


@pytest.mark.parametrize('ticker',['VCB','SSI','FPT'])
def test_five_completed_financial_years_and_quarter_peer(ticker):
    from scripts.financial_evidence import at_period
    from scripts.universal_data import get_company
    p=build_pack(ticker);typ=get_company(ticker)['EntityType']
    year=int(p['Period'][:4])-(p['Period'][-1]!='4')
    for m,x in p['Items'].items():
        assert list(x['History'].DisplayPeriod)==[str(y) for y in range(year-4,year+1)]
        for r in x['History'].itertuples():
            assert r.Period.endswith('-Q4')
        if m=='NPAT':
            assert x['Value']==at_period(ticker,typ,p['Period'],'QUARTER')[m]['Value']
            for r in x['History'].itertuples():
                expected=at_period(ticker,typ,r.Period,'FY')[m]['Value']
                if pd.notna(r.Value):assert r.Value==expected


def test_export_cannot_reintroduce_ytd_from_stale_options():
    from scripts.professional_report import generate_docx
    pack=build_pack('VCB');pack['Sections']=[]
    with patch('scripts.professional_report.build_pack',return_value=pack) as build:
        doc=Document(BytesIO(generate_docx('VCB','rating',mna={'history_basis':'YTD','history_years':3})))
        build.assert_called_once_with('VCB','FY',5)
    assert 'LỊCH SỬ TÀI CHÍNH 5 NĂM' in doc.element.xml
    assert '6T/2026' not in doc.element.xml
    assert 'Phạm vi định lượng' not in doc.element.xml
    assert 'Số peer có số' not in doc.element.xml


def test_insurance_export_uses_five_annual_years():
    from scripts.insurance_analysis import metric_pair
    p=metric_pair('BVH','NPAT')
    assert list(p['History'].DisplayPeriod)==['2021','2022','2023','2024','2025']
    assert p['Period']=='2026-Q2'


def test_vcb_narrative_connects_growth_funding_profitability_and_risk():
    p=build_pack('VCB')
    checks={'GrossLoans':'Tín dụng mở rộng nhanh hơn huy động',
            'Equity':'Tài sản tăng nhanh hơn vốn',
            'NPAT':'NIM thu hẹp đồng thời CIR tăng',
            'NPL':'cải thiện không chỉ đến từ mẫu số tín dụng tăng'}
    for metric,expected in checks.items():
        n=narrative(p,metric);text=' '.join(n.values())
        assert expected in text
        assert '6T/' not in text and 'điểm cần theo dõi trong đánh giá tài chính' not in text
    assert '24,43' in narrative(p,'ROE')['History']


@pytest.mark.parametrize('car,grade',[(.1801,'Rất Mạnh'),(.18,'Mạnh'),(.15,'Mạnh'),(.12,'Phù Hợp'),(.09,'Trung Bình'),(.08,'Yếu'),(.079,'Rất Yếu'),(None,None),(float('nan'),None),(12,None)])
def test_car_table_uses_expected_car_decimal(car,grade):
    assert car_grade(car)==grade


def assessment():
    return {'BusinessProfile':'Phù Hợp','CapitalEarnings':'Phù Hợp','RiskPosition':'Phù Hợp',
            'Funding':'Phù Hợp','Liquidity':'Phù Hợp','ExternalSupportNotches':0}


@pytest.mark.parametrize('i,j',[(i,j) for i in range(4) for j in range(4)])
def test_funding_liquidity_matrix(i,j):
    o=assessment();o.update(Funding=FUNDING_GRADES[i],Liquidity=FUNDING_GRADES[j],FundingStrongExceptionConfirmed=True)
    r=bank_rating('VCB',o)
    assert r['FactorNotches']['Huy động vốn và Thanh khoản']==FUNDING_MATRIX[i][j]
    assert r['ICR']!='N/A'


def test_no_implicit_support_or_peer_grades():
    r=bank_rating('VCB')
    assert r['ICR']==r['SACP']=='N/A'
    assert 'CapitalEarnings' in r['MissingEvidence']
    o=assessment();o.pop('ExternalSupportNotches')
    r=bank_rating('VCB',o)
    assert r['SACP']=='vnA-' and r['ICR']=='N/A'
    assert r['RatingStatus']=='STANDALONE_ONLY'


def test_car_forecast_requires_final_capital_adjustment():
    o=assessment();o.pop('CapitalEarnings');o['ForecastCAR']=.12
    assert bank_rating('VCB',o)['SACP']=='N/A'
    o['CapitalAdjustmentNotches']=0
    assert bank_rating('VCB',o)['SACP']=='vnA-'
    o['RegulatoryCapitalStatus']='BREACH'
    assert bank_rating('VCB',o)['SACP']=='vnB-'


def test_persisted_assessment_cannot_leak_to_a_new_period(tmp_path):
    import json
    import scripts.bank_method_2026 as mod
    (tmp_path/'config').mkdir()
    row=dict(assessment(),Ticker='VCB',Period='2025-Q4',Source='User assessment',Rationale='Fixture, not a live rating')
    (tmp_path/'config/bank_rating_assessments.json').write_text(json.dumps({'assessments':[row]}))
    with patch.object(mod,'ROOT',tmp_path):
        assert mod.saved_assessment('VCB','2026-Q2')=={}
        assert mod.saved_assessment('VCB','2025-Q4')['BusinessProfile']=='Phù Hợp'


def test_ui_quarter_peer_uses_quarter_income_not_ttm():
    from scripts.financial_views import peer_metric_frame
    from scripts.financial_evidence import at_period
    q=peer_metric_frame('VCB','NPAT')
    assert len(q)>5
    for r in q.itertuples():
        assert r.Value==at_period(r.Ticker,'BANK',r.Period,'QUARTER')['NPAT']['Value']
        assert r.Basis=='QUARTER'


def test_vcb_annual_profit_is_four_raw_quarters_and_stocks_are_year_end():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    raw=pd.read_csv(root/'data/bank_history_long.csv')
    raw=raw[raw.Ticker.eq('VCB') & raw.Metric.eq('NPAT')]
    p=build_pack('VCB')
    for r in p['Items']['NPAT']['History'].itertuples():
        year=str(r.DisplayPeriod)
        q=raw[raw.Period.isin([year+'-Q'+str(i) for i in range(1,5)])]
        assert q.Period.nunique()==4
        assert r.Value==pytest.approx(q.Value.sum())
    cache=pd.read_csv(root/'data/bank_history_long.csv')
    for r in p['Items']['TotalAssets']['History'].itertuples():
        q=cache[cache.Ticker.eq('VCB') & cache.Period.eq(r.Period) & cache.Metric.eq('TotalAssets')]
        assert len(q)==1
        assert r.Value==pytest.approx(q.Value.iloc[0])
