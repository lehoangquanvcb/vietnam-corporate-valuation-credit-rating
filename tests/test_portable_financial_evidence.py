"""Hồi quy triển khai Cloud: dữ liệu thực đi cùng Git, không cần raw cục bộ."""
from pathlib import Path
import pandas as pd
import pytest
from scripts.export_financial_evidence import export_ticker
from scripts.financial_evidence import at_period, latest_period, repair_snapshot


def bundle(root, rows, ticker='XYZ'):
    p=root/'data/financial_evidence';p.mkdir(parents=True,exist_ok=True)
    d=pd.DataFrame(rows)
    d['Ticker']=ticker;d['Unit']='VNĐ';d['Source']='fixture audited statements'
    d['Basis']='QUARTER'
    d.to_csv(p/f'{ticker}.csv.gz',index=False)


def sample_rows():
    rows=[dict(Dataset='balance',Period='2026-Q2',Field=k,Value=v) for k,v in
          [('BS_TOTAL_ASSETS',1000),('BS_EQUITY',300),('BS_SHORT_TERM_BORROWINGS',100),('BS_LONG_TERM_BORROWINGS',200)]]
    rows += [dict(Dataset='income',Period=p,Field='IS_NET_REVENUE',Value=v)
             for p,v in [('2025-Q3',10),('2025-Q4',20),('2026-Q1',30),('2026-Q2',40)]]
    return rows


def test_cloud_recovers_stock_ttm_and_both_debt_components(tmp_path):
    bundle(tmp_path,sample_rows())
    assert not (tmp_path/'data/raw').exists()
    assert latest_period('XYZ','CORPORATE',tmp_path)=='2026-Q2'
    s=repair_snapshot('XYZ','CORPORATE',root=tmp_path)
    assert s['TotalAssets']==1000 and s['TotalDebt']==300 and s['Revenue']==100
    assert at_period('XYZ','CORPORATE','2026-Q2','QUARTER',tmp_path)['Revenue']['Value']==40


def test_missing_quarter_is_not_filled_from_latest_or_old_cache(tmp_path):
    rows=[r for r in sample_rows() if r['Period']!='2025-Q4']
    bundle(tmp_path,rows)
    s=repair_snapshot('XYZ','CORPORATE',{'Revenue':9999},tmp_path)
    assert s['Revenue'] is None
    assert s['TotalDebt']==300


def test_raw_priority_is_cell_level_and_raw_conflict_is_not_hidden(tmp_path):
    bundle(tmp_path,sample_rows())
    p=tmp_path/'data/raw';p.mkdir()
    raw=p/'XYZ_balance.csv'
    pd.DataFrame([{'period':'2026-Q2','id':'BS_TOTAL_ASSETS','value':2000}]).to_csv(raw,index=False)
    r=at_period('XYZ','CORPORATE','2026-Q2',root=tmp_path)
    assert r['TotalAssets']['Value']==2000 and r['TotalDebt']['Value']==300
    pd.DataFrame([{'period':'2026-Q2','id':'BS_TOTAL_ASSETS','value':v} for v in [2000,3000]]).to_csv(raw,index=False)
    r=at_period('XYZ','CORPORATE','2026-Q2',root=tmp_path)
    assert r['TotalAssets']['Status']=='ERROR' and r['TotalAssets']['Value'] is None


@pytest.mark.parametrize('damage',['LATEST','WRONG_TICKER','UNNAMED_FIELD'])
def test_invalid_portable_data_cannot_create_rating_inputs(tmp_path,damage):
    rows=sample_rows()
    if damage=='LATEST':rows[0]['Period']='LATEST'
    if damage=='UNNAMED_FIELD':rows[0]['Field']='value'
    bundle(tmp_path,rows,ticker='XYZ')
    if damage=='WRONG_TICKER':
        p=tmp_path/'data/financial_evidence/XYZ.csv.gz';d=pd.read_csv(p);d.loc[0,'Ticker']='OTHER';d.to_csv(p,index=False)
    assert latest_period('XYZ','CORPORATE',tmp_path) is None


def test_bundle_replacement_invalidates_metric_cache(tmp_path):
    bundle(tmp_path,sample_rows())
    assert repair_snapshot('XYZ','CORPORATE',root=tmp_path)['TotalAssets']==1000
    rows=sample_rows();rows[0]['Value']=5000;bundle(tmp_path,rows)
    assert repair_snapshot('XYZ','CORPORATE',root=tmp_path)['TotalAssets']==5000


def test_export_ytd_keeps_basis_and_does_not_export_metadata_as_financials(tmp_path):
    raw=tmp_path/'raw';raw.mkdir()
    pd.DataFrame({'period':['2026-Q1','2026-Q2'],'IS_NET_REVENUE':[10,30],'order':[999,999]}).to_csv(raw/'XYZ_income.csv',index=False)
    cfg=pd.DataFrame([dict(Ticker='XYZ',Dataset='income',Basis='YTD')])
    out=export_ticker('XYZ',raw,tmp_path/'data/financial_evidence',cfg)
    assert out['Rows']==2
    assert at_period('XYZ','CORPORATE','2026-Q2','QUARTER',tmp_path)['Revenue']['Value']==20


def test_vic_cloud_regression_and_nonfinancial_routing():
    from scripts.universal_data import get_company,get_snapshot
    from scripts.report_rating import rate_company
    from scripts.financial_evidence import same_period_history
    from scripts.dynamic_peer_engine import select_dynamic_peers
    assert get_company('VIC')['Sector']=='Bất động sản'
    assert get_company('VIC')['EntityType']=='CORPORATE'
    s=get_snapshot('VIC')
    assert s['TotalAssets']>0 and s['TotalDebt']>0
    assert s['CurrentRatio']>0 and s['ROE'] is not None
    history=same_period_history('VIC','CORPORATE',metrics=['Revenue','TotalAssets'])
    assert history.Value.notna().sum()==10
    peers=select_dynamic_peers('VIC')
    assert peers.Sector.eq('Bất động sản').all()
    r=rate_company('VIC')
    assert r['ICR']!='N/A' and len(r['RiskScores'])==4
    assert not r.get('GovernmentSupportNotches')


@pytest.mark.parametrize('ticker',['ATG','LO5','TCJ','VTJ'])
def test_extreme_corporate_score_does_not_fail_on_float_roundoff(ticker):
    from scripts.report_rating import rate_company
    r=rate_company(ticker)
    assert r['RatingStatus'] in {'ESTIMATED','INSUFFICIENT_DATA'}
    for value in r.get('RiskScores',{}).values():
        if value is not None and pd.notna(value):assert 1 <= value <= 6


def test_universe_cache_refreshes_after_classification_changes(tmp_path,monkeypatch):
    import scripts.universal_data as ud
    monkeypatch.setattr(ud,'CFG',tmp_path)
    p=tmp_path/'company_universe.csv'
    row=dict(Ticker='XYZ',EntityType='CORPORATE',Methodology='CORPORATE_2025',Sector='Chưa phân loại',Active=1)
    pd.DataFrame([row]).to_csv(p,index=False)
    assert ud.universe().iloc[0].Sector=='Chưa phân loại'
    row['Sector']='Bất động sản';pd.DataFrame([row]).to_csv(p,index=False)
    assert ud.universe().iloc[0].Sector=='Bất động sản'
