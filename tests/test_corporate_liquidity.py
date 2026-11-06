from copy import deepcopy
from unittest.mock import patch
import pytest
from scripts.corporate_liquidity import assess
from scripts.corporate_methodology import apply_adjustments, weighted_profile, RISK_KEYS, scorecard, steps
from scripts.rating_presentation import credit_metrics, credit_header, credit_pack


def records(cr=1.3,cash=.2,cfo=.15,focf=.05):
    values=dict(CurrentRatio=cr,CashDebt=cash,CFO_Debt=cfo,FOCF_Debt=focf)
    return {k:dict(Value=v,Status='OK',Period='2026-Q2',Basis='DERIVED_TTM' if k in {'CFO_Debt','FOCF_Debt'} else 'END_PERIOD',Source='fixture') for k,v in values.items()}


@pytest.mark.parametrize('values,level,n',[
    ((2,.6,.5,.3),'Rất Mạnh',2),((1.5,.3,.3,.2),'Mạnh',1),
    ((1.3,.2,.15,.05),'Phù Hợp',0),((1.05,.21,.21,-.08),'Trung Bình',0),
    ((.7,.01,-.1,-.2),'Yếu',0)])
def test_actual_balances_and_ttm_flows_drive_notches(values,level,n):
    r=assess(records(*values),'2026-Q2')
    assert (r['Liquidity'],r['LiquidityNotches'])==(level,n)
    adjusted=apply_adjustments('vnA-',3,liquidity=level,liquidity_notches=n)
    assert adjusted['ICR']=={2:'vnA+',1:'vnA',0:'vnA-'}[n]


def test_deterioration_moves_rating_without_changing_four_risks():
    p=weighted_profile(dict.fromkeys(RISK_KEYS,3))
    before=deepcopy(p)
    for n in (0,1,2):
        r={**p,**apply_adjustments(p['InitialRating'],3,liquidity_notches=n)}
        assert r['WeightedScore']==3 and r['InitialRating']==before['InitialRating']
    assert p==before


@pytest.mark.parametrize('bad',[None,float('nan'),float('inf'),True,-1])
def test_missing_or_invalid_current_ratio_never_becomes_weak(bad):
    r=assess(records(cr=bad),'2026-Q2')
    assert r['Liquidity']=='Chưa đủ dữ liệu' and r['LiquidityNotches']==0


def test_wrong_period_or_quarter_flow_is_not_ttm():
    data=records();data['CFO_Debt']['Basis']='DERIVED_QUARTER';data['FOCF_Debt']['Period']='2025-Q4'
    r=assess(data,'2026-Q2')
    assert r['LiquidityAssessment']['Status']=='INSUFFICIENT_DATA'
    assert r['LiquidityNotches']==0


def test_three_metrics_renormalize_but_one_ratio_cannot_rate():
    data=records();del data['FOCF_Debt']
    assert assess(data,'2026-Q2')['LiquidityScore']==3
    assert assess({'CurrentRatio':data['CurrentRatio']},'2026-Q2')['LiquidityScore'] is None


def test_no_positive_uplift_with_negative_operating_cashflow():
    r=assess(records(10,3,-.01,2),'2026-Q2')
    assert r['LiquidityNotches']<=0
    weak=assess(records(.9,3,-.01,2),'2026-Q2')
    assert weak['Liquidity']=='Yếu' and weak['LiquidityNotches']==0


def test_zero_debt_is_not_infinite_cash_ratio():
    data=records(1.6,None,None,None)
    for k,v,b in [('TotalDebt',0,'END_PERIOD'),('Cash',20,'END_PERIOD'),('CFO',30,'TTM')]:
        data[k]=dict(Value=v,Status='OK',Period='2026-Q2',Basis=b)
    r=assess(data,'2026-Q2')
    assert r['Liquidity']=='Mạnh' and r['LiquidityScore'] is None and r['LiquidityNotches']==1
    data['CFO']['Value']=-10
    assert assess(data,'2026-Q2')['LiquidityNotches']==0


def test_override_replaces_not_adds_and_rating_caps_survive():
    r=assess(records(.7,.01,-.1,-.2),'2026-Q2','Mạnh')
    adjusted=apply_adjustments('vnAA',4,liquidity=r['Liquidity'],liquidity_notches=r['LiquidityNotches'])
    assert r['LiquidityAssessment']['Origin']=='ANALYST_OVERRIDE'
    assert adjusted['LiquidityAdjustedRating']=='vnAA+' and adjusted['ICR']=='vnBB+'
    assert apply_adjustments('vnAAA',3,liquidity_notches=1)['LiquidityNotches']==0
    capped=apply_adjustments('vnAA+',3,liquidity='Rất Mạnh',liquidity_notches=2)
    assert capped['ICR']=='vnAAA' and capped['LiquidityNotches']==1
    assert capped['LiquidityRequestedNotches']==2


@pytest.mark.parametrize('invalid',[-2,-1,3,True,1.5])
def test_invalid_or_negative_liquidity_notches_rejected(invalid):
    with pytest.raises(ValueError):apply_adjustments('vnA',3,liquidity_notches=invalid)


def test_notches_must_match_assessed_level():
    with pytest.raises(ValueError):
        apply_adjustments('vnA',3,liquidity='Yếu',liquidity_notches=1)


def test_liquidity_row_always_between_initial_and_final_even_if_missing():
    for data in (records(),{}):
        r={**weighted_profile(dict.fromkeys(RISK_KEYS,3)),**assess(data,'2026-Q2')}
        r.update(apply_adjustments(r['InitialRating'],3,liquidity_notches=r['LiquidityNotches']))
        for names in ([x['Cấu phần'] for x in scorecard(r)],[x[0] for x in steps(r)]):
            assert names.index('Bậc xếp hạng ban đầu')<names.index('Yếu tố thanh khoản')<names.index('Kết quả xếp hạng tín nhiệm cuối cùng')
            assert 'Anchor' not in names


def test_rating_filter_removes_market_metrics_without_mutating_analysis():
    from scripts.financial_views import HISTORY_METRICS
    from scripts.report_methodology import GROUPS
    for typ,groups in GROUPS.items():
        pack={'Items':{m:{} for ms in groups.values() for m in ms},'Sections':list(groups.items())}
        clean=credit_pack(pack)
        assert not {'PB','PE','Price','EV_EBITDA'} & clean['Items'].keys()
        assert 'PE' not in credit_metrics(HISTORY_METRICS[typ])
        assert clean is not pack
    assert credit_header([('P/E','4x'),('P/B','1x'),('Giá thị trường','100'),('ROE','10%')])==[('ROE','10%')]


def test_report_uses_same_actual_liquidity_as_strict_engine():
    from scripts.report_rating import rate_company
    from scripts.three_methodology_rating import rate_company as strict
    inputs={**dict.fromkeys(RISK_KEYS,3),'ModifierNotches':0,'ExternalSupportNotches':0}
    a=rate_company('VIC',inputs);b=strict('VIC',inputs)
    for key in ['Liquidity','LiquidityScore','LiquidityNotches','LiquidityAdjustedRating','ICR']:
        assert a[key]==b[key]
    assert a['LiquidityNotches']==0


def test_committee_applies_liquidity_once_before_the_final_row():
    from scripts.rating_committee_engine import committee_pack
    inputs={**dict.fromkeys(RISK_KEYS,3),'ModifierNotches':0,'ExternalSupportNotches':0}
    rows=committee_pack('VIC',inputs)['Waterfall']
    names=[r['Cấu phần'] for r in rows]
    assert names.count('Yếu tố thanh khoản')==1
    assert names[-1]=='Kết quả xếp hạng tín nhiệm cuối cùng'
    assert names.index('Yếu tố thanh khoản')==names.index('Bậc xếp hạng ban đầu')+1


@pytest.mark.parametrize('ticker,method',[('VCB','BANK'),('SSI','SECURITIES'),('ABI','INSURANCE')])
def test_corporate_liquidity_does_not_run_for_financial_institutions(ticker,method):
    from scripts.report_rating import rate_company
    with patch('scripts.corporate_liquidity.assess',side_effect=AssertionError('Corporate liquidity called for financial institution')):
        result=rate_company(ticker)
    assert result['Methodology']==method
    assert result.get('LiquidityAssessment',{}).get('Origin') not in {'ACTUAL_FINANCIALS','ANALYST_OVERRIDE'}
    assert not any(row.get('Cấu phần')=='Yếu tố thanh khoản' for row in result['Scorecard'])
