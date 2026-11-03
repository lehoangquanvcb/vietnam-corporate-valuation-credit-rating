"""Chỉ định CAR người dùng: thứ tự nguồn, kỳ gốc, ước tính và bảng điểm."""
import os
from unittest.mock import patch

import pandas as pd
import pytest

from scripts.bank_car import user_input_frame, car_usage_text
from scripts.financial_evidence import at_period, rating_car_record, same_period_history, repair_snapshot
from tests.test_bank_car_disclosures import source, seed


def supplied(**changes):
    row=dict(Ticker='ABB',Period='2026-Q2',Value=12.5,Unit='PERCENT',Scope='CONSOLIDATED',
             Regime='UNKNOWN',SourceKind='USER_ESTIMATE',InputText='> 12,00%',
             ProvidedOn='2026-11-03',SourceReference='Bảng người dùng',ApplyThroughPeriod='2026-Q2')
    return dict(row,**changes)


def inputs(root, rows):
    (root/'data').mkdir(exist_ok=True,parents=True)
    pd.DataFrame(rows).to_csv(root/'data/bank_car_user_inputs.csv',index=False)


def test_official_current_wins_even_over_consolidated_user_estimate(tmp_path):
    seed(tmp_path,[source()]);inputs(tmp_path,[supplied()])
    r=rating_car_record('ABB','2026-Q2',tmp_path)
    assert r['Value']==.1272 and r['Scope']=='BANK_ONLY'
    assert r['SourceKind']=='VERIFIED_DISCLOSURE' and not r['FallbackUsed']


def test_user_current_wins_over_2025_and_has_no_fake_verified_source(tmp_path):
    seed(tmp_path,[source(Period='2025-Q4',Value=11)])
    inputs(tmp_path,[supplied()])
    r=rating_car_record('ABB','2026-Q2',tmp_path)
    assert r['Value']==.125 and r['Basis']=='USER_ESTIMATE' and r['InputText']=='> 12,00%'
    assert r['Period']=='2026-Q2' and r['SourceKind']=='USER_ESTIMATE'
    assert not r.get('SourceURL') and not r.get('VerifiedOn')
    assert 'ước tính' in car_usage_text(r,'2026-Q2')


def test_previous_year_for_score_only_and_never_carried_to_future(tmp_path):
    seed(tmp_path,[])
    # Tệp registry rỗng có đủ schema.
    pd.DataFrame(columns=list(source())).to_csv(tmp_path/'data/bank_car_disclosures.csv',index=False)
    inputs(tmp_path,[supplied(Period='2025-Q4',Value=16,SourceKind='USER_PROVIDED',InputText='16,00%')])
    assert at_period('ABB','BANK','2026-Q2',root=tmp_path)['CAR']['Value'] is None
    r=rating_car_record('ABB','2026-Q2',tmp_path)
    assert r['Value']==.16 and r['Period']=='2025-Q4' and r['FallbackUsed']
    assert r['UsePeriod']=='2026-Q2' and '31/12/2025' in car_usage_text(r,'2026-Q2')
    assert rating_car_record('ABB','2026-Q3',tmp_path)['Value'] is None
    assert rating_car_record('ABB','2025-Q3',tmp_path)['Value'] is None
    h=same_period_history('ABB','BANK','FY',5,tmp_path,['CAR'])
    assert h.Value.notna().sum()==1 and h.iloc[-1].Value==.16 and h.iloc[-1].DisplayPeriod=='2025'
    s=repair_snapshot('ABB','BANK',root=tmp_path)
    assert s['CAR']==.16 and s['CAR_AsOf']=='2025-Q4' and s['SnapshotPeriod']=='2026-Q2'


def test_source_conflict_is_not_hidden_by_user_or_older_data(tmp_path):
    seed(tmp_path,[source(Value=11),source(Value=12)])
    inputs(tmp_path,[supplied(),supplied(Period='2025-Q4')])
    assert rating_car_record('ABB','2026-Q2',tmp_path)['Status']=='ERROR'
    assert repair_snapshot('ABB','BANK',root=tmp_path)['CAR'] is None


@pytest.mark.parametrize('changes',[dict(Unit='UNKNOWN'),dict(Value=0),dict(Value=150),
    dict(SourceKind='VERIFIED_DISCLOSURE'),dict(Period='2026-Q7'),dict(ProvidedOn=''),
    dict(SourceReference=''),dict(ApplyThroughPeriod='2025-Q4')])
def test_bad_user_input_rejected(changes):
    r=user_input_frame(pd.DataFrame([supplied(**changes)]),'ABB').iloc[0]
    assert r.Error and pd.isna(r.Value)


def test_user_change_invalidates_evidence_and_peer_download_cache(tmp_path,monkeypatch):
    import scripts.dynamic_peer_engine as engine
    seed(tmp_path,[source(Ticker='BID')]);inputs(tmp_path,[supplied()])
    monkeypatch.setattr(engine,'DATA',tmp_path/'data');monkeypatch.setattr(engine,'CFG',tmp_path/'config')
    before=engine.peer_source_fingerprint()
    assert rating_car_record('ABB','2026-Q2',tmp_path)['Value']==.125
    path=tmp_path/'data/bank_car_user_inputs.csv';old=path.stat().st_mtime_ns
    inputs(tmp_path,[supplied(Value=12.6)])
    os.utime(path,ns=(old+1000000,old+1000000))
    assert rating_car_record('ABB','2026-Q2',tmp_path)['Value']==.126
    assert before!=engine.peer_source_fingerprint()


def test_actual_priority_fallback_and_scores_all_supplied_listed_codes():
    from scripts.report_rating import rate_company
    expected={'ABB':(.1272,'2026-Q2'),'TCB':(.1495,'2026-Q2'),'SSB':(.1206,'2026-Q2'),
              'BAB':(.0895,'2026-Q2'),'STB':(.0989,'2026-Q2'),'EIB':(.126,'2026-Q2'),
              'MSB':(.1228,'2026-Q2'),'VCB':(.125,'2026-Q2'),'HDB':(.16,'2025-Q4'),
              'VIB':(.122,'2025-Q4'),'MBB':(.115,'2025-Q4')}
    for t,(v,p) in expected.items():
        car=rating_car_record(t,'2026-Q2')
        assert car['Value']==pytest.approx(v) and car['Period']==p,t
        rr=rate_company(t)
        assert rr['ICR'] not in ('N/A','',None), (t,rr.get('MissingEvidence'))
        if rr.get('RatingOrigin')=='AUTO_RESEARCH':
            e=next(e for e in rr['QuantitativeEvidence'] if e['Metric']=='CAR')
            assert e['Kỳ']==p and e['Giá trị']==pytest.approx(v)
            assert rr['AssessmentComplete'] is False
    assert at_period('TCB','BANK','2025-Q4')['CAR']['Value']==.1461
    assert rate_company('TCB')['ICR']=='vnAA+'


def test_pack_and_peer_chart_do_not_relabel_2025_as_current():
    from scripts.report_evidence import build_pack
    from scripts.financial_views import peer_metric_frame
    pack=build_pack('HDB')
    assert pack['CARInput']['Value']==.16
    assert pack['Items']['CAR']['Value'] is None
    assert 'HDB' not in set(peer_metric_frame('HDB','CAR').Ticker)
    pack=build_pack('VCB')
    assert pack['Items']['CAR']['Value']==.125
    assert pack['Items']['CAR']['Record']['SourceKind']=='USER_ESTIMATE'
    assert peer_metric_frame('VCB','CAR').Ticker.tolist()==['VCB']


def test_car_narrative_keeps_estimate_and_fallback_explicit():
    from scripts.report_evidence import build_pack, narrative
    estimated=narrative(build_pack('VCB'),'CAR')
    assert 'ước tính' in estimated['Peers'] and 'ghi nhận' not in estimated['Peers']
    assert '12,50' in estimated['Meaning'] and 'giả định' in estimated['Meaning']
    older=narrative(build_pack('HDB'),'CAR')
    assert '31/12/2025' in older['Peers'] and 'Dùng thay thế' in older['Peers']
    assert '16,00' in older['Meaning'] and 'giả định' in older['Meaning']
