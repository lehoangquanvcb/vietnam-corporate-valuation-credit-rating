"""Hồi quy CAR: kỳ, phạm vi, ngưỡng chấm, nguồn và làm mới cache."""
import os

import pandas as pd
import pytest

from scripts.bank_car import disclosure_frame, comparable_metric
from scripts.financial_evidence import at_period, same_period_history


def source(**changes):
    row = dict(Ticker='ABB', Period='2026-Q2', Metric='CAR', Value=12.72,
               Unit='PERCENT', Scope='BANK_ONLY', Regime='TT41',
               SourceURL='https://example.org/official-car.pdf', SourcePage=4,
               VerifiedOn='2026-11-03', Note='Fixture')
    return dict(row, **changes)


def seed(root, rows):
    (root/'data/raw').mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(root/'data/bank_car_disclosures.csv', index=False)
    pd.DataFrame([dict(Ticker='ABB', Period='2026-Q2', Metric='TotalAssets', Value=100)]).to_csv(root/'data/bank_history_long.csv', index=False)


def test_exact_ticker_period_and_official_precision_override_feed(tmp_path):
    seed(tmp_path, [source(), source(Ticker='BID', Value=10.01)])
    pd.DataFrame([dict(period='2026-Q2', id='RT_BANK_CAR', value=.13)]).to_csv(tmp_path/'data/raw/ABB_ratio_q.csv', index=False)
    r = at_period('ABB', 'BANK', '2026-Q2', root=tmp_path)['CAR']
    assert r['Value'] == .1272 and r['Status'] == 'OK'
    assert r['Scope'] == 'BANK_ONLY' and r['Regime'] == 'TT41'
    assert r['SourceURL'].endswith('official-car.pdf') and r['VerifiedOn'] == '2026-11-03'
    assert at_period('BID', 'BANK', '2026-Q2', root=tmp_path)['CAR']['Value'] == pytest.approx(.1001)
    assert at_period('ABB', 'BANK', '2026-Q1', root=tmp_path)['CAR']['Value'] is None
    assert at_period('ABB', 'BANK', '2026-Q3', root=tmp_path)['CAR']['Value'] is None
    assert at_period('ABB', 'CORPORATE', '2026-Q2', root=tmp_path)['CAR'].get('SourceURL') is None


def test_consolidated_precedence_is_not_largest_or_last_value():
    frame = disclosure_frame(pd.DataFrame([source(Scope='CONSOLIDATED', Value=11), source(Value=15)]), 'ABB')
    assert frame.iloc[0].Value == .11 and frame.iloc[0].Scope == 'CONSOLIDATED'


@pytest.mark.parametrize('change', [dict(Unit='UNKNOWN'), dict(Value=0), dict(Value=150),
    dict(Metric='Tier1CAR'), dict(Scope='UNKNOWN'), dict(Regime='UNKNOWN'),
    dict(SourceURL=''), dict(SourcePage=''), dict(VerifiedOn='')])
def test_invalid_source_is_not_accepted(change):
    f = disclosure_frame(pd.DataFrame([source(**change)]), 'ABB')
    assert f.iloc[0].Error and pd.isna(f.iloc[0].Value)


def test_conflicting_official_rows_block_fallback(tmp_path):
    seed(tmp_path, [source(Value=11), source(Value=12)])
    pd.DataFrame([dict(period='2026-Q2', id='RT_BANK_CAR', value=.13)]).to_csv(tmp_path/'data/raw/ABB_ratio_q.csv', index=False)
    r = at_period('ABB', 'BANK', '2026-Q2', root=tmp_path)['CAR']
    assert r['Status'] == 'ERROR' and r['Value'] is None


def test_bad_consolidated_row_cannot_silently_use_valid_standalone():
    f = disclosure_frame(pd.DataFrame([source(Scope='CONSOLIDATED', Value=0), source(Value=13)]), 'ABB')
    assert f.iloc[0].Error and pd.isna(f.iloc[0].Value)


def test_source_change_invalidates_caches_and_q2_never_becomes_fy(tmp_path):
    seed(tmp_path, [source()])
    assert at_period('ABB', 'BANK', '2026-Q2', root=tmp_path)['CAR']['Value'] == .1272
    path = tmp_path/'data/bank_car_disclosures.csv'; old = path.stat().st_mtime_ns
    seed(tmp_path, [source(Value=13.72)])
    os.utime(path, ns=(old+1000000, old+1000000))
    assert at_period('ABB', 'BANK', '2026-Q2', root=tmp_path)['CAR']['Value'] == pytest.approx(.1372)
    h = same_period_history('ABB', 'BANK', 'FY', 5, tmp_path, ['CAR'])
    assert h.DisplayPeriod.tolist() == ['2021','2022','2023','2024','2025']
    assert h.Value.isna().all()


def test_missing_and_invalid_registry_and_unrelated_metrics(tmp_path):
    seed(tmp_path, [source()])
    path=tmp_path/'data/bank_car_disclosures.csv'
    path.write_text('wrong,column\na,b\n')
    r=at_period('ABB','BANK','2026-Q2',root=tmp_path)
    assert r['CAR']['Status']=='ERROR' and r['TotalAssets']['Value']==100
    path.unlink()
    assert at_period('ABB','BANK','2026-Q2',root=tmp_path)['CAR']['Status']=='MISSING'


def test_regulatory_basis_keeps_peer_groups_comparable():
    assert comparable_metric('CAR', {'Regime':'TT41'}, {'Regime':'TT41'})
    assert not comparable_metric('CAR', {'Regime':'TT41'}, {'Regime':'TT14'})
    assert not comparable_metric('CAR', {'Regime':'TT41'}, {})
    assert comparable_metric('CAR', {}, {})
    assert comparable_metric('ROE', {'Regime':'TT41'}, {'Regime':'TT14'})


def test_actual_abb_current_car_completes_capital_and_preserves_tcb_reference():
    from scripts.report_rating import rate_company
    from scripts.bank_method_2026 import car_grade
    r = rate_company('ABB')
    assert r['Factors']['Vốn và Lợi nhuận'] == 'Phù Hợp'
    assert r['ICR'] == 'vnA-' and not r['MissingEvidence']
    assert r['RatingOrigin'] == 'AUTO_RESEARCH' and not r['AssessmentComplete']
    assert at_period('TCB','BANK','2026-Q2')['CAR']['Value'] == .1495
    assert car_grade(.1495) != car_grade(.15)
    assert rate_company('TCB')['ICR'] == 'vnAA+'


def test_report_pack_and_ui_peers_use_same_verified_value():
    from scripts.report_evidence import build_pack
    from scripts.financial_views import peer_metric_frame
    p=build_pack('ABB'); item=p['Items']['CAR']
    assert item['Value']==.1272
    ui=peer_metric_frame('ABB','CAR')
    assert ui.loc[ui.Ticker.eq('ABB'),'Value'].iloc[0]==.1272
    assert set(ui.Ticker)-{'ABB'} == {r['Ticker'] for r in item['Peers']}
    assert 'NAB' not in set(ui.Ticker)  # TT14 is not averaged with TT41.


def test_source_update_invalidates_report_download_identity(tmp_path, monkeypatch):
    import scripts.dynamic_peer_engine as engine
    monkeypatch.setattr(engine,'DATA',tmp_path/'data')
    monkeypatch.setattr(engine,'CFG',tmp_path/'config')
    seed(tmp_path,[source()])
    first=engine.peer_source_fingerprint()
    seed(tmp_path,[source(Value=13.72)])
    assert engine.peer_source_fingerprint()!=first
