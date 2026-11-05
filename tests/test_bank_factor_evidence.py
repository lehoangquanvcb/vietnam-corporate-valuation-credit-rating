"""Independent evidence scenarios; no fixed desired bank ratings."""
import pandas as pd
import pytest
from scripts.bank_factor_evidence import assess
from scripts.report_rating import Evidence,rate_company

class Context:
    ticker='TEST';period='2026-Q2'
    def __init__(self,changes=None):
        values=dict(TotalAssets=100,GrossLoans=60,CustomerDeposits=65,OperatingIncome=10,NPAT=2,
                    ROA=.02,ROE=.15,CIR=.4,NIM=.04,EquityAssets=.1,TangibleEquityAssets=.1,
                    NII_OperatingIncome=.75,NPL=.02,LoanLossCoverage=1,CreditCostProxy=.01,
                    ProvisionOperatingIncome=.1,Equity=10,CAR=.13)
        values.update(changes or {})
        self.records={m:dict(Value=v,Status='OK' if v is not None else 'MISSING',
                             Period=self.period,Basis='REPORTED_RATIO',Regime='TT41',Scope='CONSOLIDATED')
                      for m,v in values.items()}
        self.rows=[]
    def value(self,m):return self.records.get(m,{}).get('Value')
    def add(self,*args):self.rows.append(args)

@pytest.fixture
def environment(monkeypatch):
    import scripts.bank_factor_evidence as m
    peer=Context()
    monkeypatch.setattr(m,'bank_universe',lambda t:['P'+str(i) for i in range(8)])
    monkeypatch.setattr(m,'at_period',lambda *a,**k:peer.records)
    annual=[]
    for metric,r in peer.records.items():
        for y in range(2021,2026):
            annual.append(dict(Metric=metric,Period=f'{y}-Q4',Status='OK',Value=r['Value'],
                               Regime='TT41',Scope='CONSOLIDATED'))
    history=pd.DataFrame(annual)
    monkeypatch.setattr(m,'same_period_history',lambda *a,**k:history)
    return history

def test_median_is_neutral_and_small_size_alone_does_not_downgrade(environment):
    grades,_=assess(Context())
    assert grades=={'BusinessProfile':3,'CapitalEarnings':3,'RiskPosition':3}
    small=Context(dict(TotalAssets=1,GrossLoans=1,CustomerDeposits=1,OperatingIncome=1))
    assert assess(small)[0]['BusinessProfile']==3

def test_capital_quality_requires_multiple_signals_and_positive_history(environment):
    ctx=Context(dict(ROA=.03,ROE=.2,CIR=.3,NIM=.05,TangibleEquityAssets=.15))
    grades,e=assess(ctx)
    assert grades['CapitalEarnings']==2 and e['CapitalQualityAdjustment']==1
    assert assess(Context(dict(ROA=.03)))[0]['CapitalEarnings']==3
    environment.loc[(environment.Metric=='NPAT')&(environment.Period=='2024-Q4'),'Value']=-1
    assert assess(ctx)[0]['CapitalEarnings']==3

def test_bad_loans_or_capital_consuming_growth_block_strong_risk(environment):
    assert assess(Context(dict(NPL=.01,LoanLossCoverage=2,CreditCostProxy=.005)))[0]['RiskPosition']==2
    assert assess(Context(dict(NPL=.06,LoanLossCoverage=.3)))[0]['RiskPosition']>=5
    environment.loc[(environment.Metric=='GrossLoans')&(environment.Period=='2025-Q4'),'Value']=90
    assert assess(Context(dict(NPL=.01,LoanLossCoverage=2,CreditCostProxy=.005)))[0]['RiskPosition']>=3

def test_missing_car_is_not_zero_or_good_capital(environment):
    assert assess(Context(dict(CAR=None)))[0]['CapitalEarnings'] is None

def test_book_equity_proxy_is_disclosed_when_tangible_equity_is_absent(environment):
    grades,e=assess(Context(dict(TangibleEquityAssets=None,EquityAssets=.15,ROA=.03,ROE=.2,CIR=.3,NIM=.05)))
    assert grades['CapitalEarnings']==2
    assert e['CapitalQualityProxy']=='EquityAssets'
    assert 'chưa điều chỉnh tài sản vô hình' in e['Reasons']['Vốn và Lợi nhuận']

def test_actual_banks_use_multiple_dimensions_and_keep_manual_priority():
    for ticker in ['VCB','TCB','HDB','OCB']:
        rr=rate_company(ticker)
        e=rr['BankFactorEvidence']
        assert len(e['PeerEvidence'])>=10
        assert 'OperatingIncome' in {x['Metric'] for x in e['PeerEvidence']}
        assert e['QualitativePending'] and not rr['AssessmentComplete']
        assert len(e['AnnualEvidence']['CAR'])==5
        assert 'Hiệu chỉnh' not in str(rr['Scorecard'])
    assert rate_company('TCB',{'CapitalEarnings':'Yếu'})['Factors']['Vốn và Lợi nhuận']=='Yếu'


def test_short_profit_rebound_does_not_earn_sustainable_capital_uplift(environment):
    ctx=Context(dict(ROA=.03,ROE=.2,CIR=.3,NIM=.05,TangibleEquityAssets=.15))
    environment.loc[(environment.Metric=='ROA') & environment.Period.isin(['2023-Q4','2024-Q4']),'Value']=.002
    grades,e=assess(ctx)
    assert grades['CapitalEarnings']==3
    assert not e['SustainableEarningsConfirmed']


def test_recovery_with_thin_coverage_cannot_be_strong_risk(environment):
    grades,_=assess(Context(dict(NPL=.005,LoanLossCoverage=.9,CreditCostProxy=.001)))
    assert grades['RiskPosition']>=3


def test_very_strong_car_cannot_be_downgraded_by_positive_earnings(environment):
    grades,_=assess(Context(dict(CAR=.20,ROA=.03,ROE=.2,CIR=.3,NIM=.05,TangibleEquityAssets=.15)))
    assert grades['CapitalEarnings']==1


def test_low_relative_percentile_alone_is_not_a_downgrade(environment):
    grades,_=assess(Context(dict(NPL=.025,LoanLossCoverage=.8,CreditCostProxy=.02)))
    assert grades['RiskPosition']==3
