import pandas as pd
import pytest
from pathlib import Path
from scripts.bank_car import bank_universe,peer_frame
from scripts.financial_views import history_comparison
from scripts.report_evidence import build_pack
ROOT=Path(__file__).resolve().parents[1]

def test_checked_annual_registry_has_source_and_no_conflicting_scope():
    df=pd.read_csv(ROOT/'data/bank_car_disclosures.csv')
    q=df[df.Period.str.match(r'202[1-5]-Q4')]
    assert q[['Ticker','Period']].drop_duplicates().shape[0]>=130
    assert not df.duplicated(['Ticker','Period','Scope']).any()
    assert df.SourceURL.str.startswith('https://').all()
    assert df[['Scope','Regime','SourcePage','VerifiedOn']].notna().all().all()
    counts=q.groupby('Ticker').Period.nunique()
    assert (counts==5).sum()>=25

@pytest.mark.parametrize('ticker',['VCB','TCB','HDB','OCB','ABB'])
def test_car_history_full_fiscal_years_and_same_basis_peer_mean(ticker):
    h=history_comparison(ticker,'CAR')
    assert h.DisplayPeriod.tolist()==['2021','2022','2023','2024','2025']
    assert h.Value.notna().all()
    assert h.PeerMean.notna().all()
    assert (h.PeerCount>=5).all()

def test_all_current_banks_displayed_but_estimates_not_averaged():
    q=peer_frame('VCB','2026-Q2')
    assert len(q)>=24
    assert q.Period.eq('2026-Q2').all()
    assert not q[q.SourceKind.ne('VERIFIED_DISCLOSURE')].Comparable.any()
    assert q[q.Comparable].Regime.eq('TT14').all()
    assert q[q.Comparable].Scope.eq('CONSOLIDATED').all()
    p=build_pack('VCB')['Items']['CAR']
    assert set(q.Ticker)-{'VCB'}=={r['Ticker'] for r in p['Peers']}
    assert p['PeerCount']>=23
    assert p['ComparablePeerCount']<p['PeerCount']

def test_regime_change_preserves_points_but_breaks_trend():
    from scripts.bank_car import history_breaks
    from scripts.financial_charts import history_figure
    from scripts.report_evidence import narrative
    p=build_pack('ACB');h=p['Items']['CAR']['History']
    assert history_breaks(h)==[4]
    fig=history_figure(h,'ACB','CAR',100,'%')
    own=[t for t in fig.data if t.name=='ACB']
    assert [len(t.x) for t in own]==[4,1]
    assert 'thay đổi giữa các năm' in narrative(p,'CAR')['History']
    assert history_breaks(p['Items']['TotalAssets']['History'])==[]
