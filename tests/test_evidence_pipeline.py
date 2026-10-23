"""Fixtures giả lập chỉ ở temp; kiểm tra tính đúng của phép tính và dữ liệu thực ZIP."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import pandas as pd
from scripts.financial_evidence import normalize_raw,aggregate,at_period,repair_snapshot,same_period_history
from scripts.universal_data import get_snapshot,get_company,peer_snapshot
from scripts.three_methodology_rating import rate_company
from scripts.methodology_kpi_engine import groups_for,methodology_kpi_table
from scripts.multisector_valuation import valuation
from scripts.fair_value_range import fair_value_range

class PeriodContract(unittest.TestCase):
    def frame(self,values,basis='QUARTER',field='IS_NET_REVENUE'):
        return normalize_raw(pd.DataFrame({'period':['2025-Q1','2025-Q2','2025-Q3','2025-Q4'],'id':field,'value':values,'basis':basis}))
    def test_ytd_source_is_differenced_before_summing(self):
        f=self.frame([10,30,60,100],'YTD')
        self.assertEqual(aggregate('Revenue',f,'2025-Q4','TTM')['Value'],100)
        self.assertEqual(aggregate('Revenue',f,'2025-Q2','QUARTER')['Value'],20)
        self.assertEqual(aggregate('Revenue',f,'2025-Q2','YTD')['Value'],30)
    def test_quarters_ytd_and_fy_are_distinct(self):
        f=self.frame([10,20,30,40])
        self.assertEqual(aggregate('Revenue',f,'2025-Q2','QUARTER')['Value'],20)
        self.assertEqual(aggregate('Revenue',f,'2025-Q2','YTD')['Value'],30)
        self.assertEqual(aggregate('Revenue',f,'2025-Q4','FY')['Value'],100)
    def test_no_sum_for_stock_or_ratio(self):
        for m in ['TotalAssets','ROE']:
            self.assertEqual(aggregate(m,self.frame([1,2,3,4]),'2025-Q4','TTM')['Value'],4)
    def test_missing_quarter_is_missing_not_three_quarter_ttm(self):
        f=self.frame([10,None,30,40]);self.assertIsNone(aggregate('Revenue',f,'2025-Q4','TTM')['Value'])
    def test_zero_revenue_is_a_real_observation(self):
        self.assertEqual(aggregate('Revenue',self.frame([0,0,0,0]),'2025-Q4','TTM')['Value'],0)
    def test_same_period_conflicts_are_errors(self):
        f=normalize_raw(pd.DataFrame({'period':['2025-Q1']*2,'id':['BS_TOTAL_ASSETS']*2,'value':[10,20]}))
        self.assertEqual(aggregate('TotalAssets',f,'2025-Q1')['Status'],'ERROR')
    def test_three_source_layouts_agree(self):
        a=normalize_raw(pd.DataFrame({'period':['2025-Q1'],'id':['BS_TOTAL_ASSETS'],'value':[123]}))
        b=normalize_raw(pd.DataFrame({'period':['2025-Q1'],'BS_TOTAL_ASSETS':[123]}))
        c=normalize_raw(pd.DataFrame({'id':['BS_TOTAL_ASSETS'],'2025-Q1':[123]}))
        self.assertEqual([aggregate('TotalAssets',f,'2025-Q1')['Value'] for f in [a,b,c]],[123]*3)
    def test_unknown_flow_basis_is_unreviewed(self):
        self.assertEqual(aggregate('Revenue',self.frame([1,2,3,4],'UNKNOWN'),'2025-Q4','TTM')['Status'],'UNREVIEWED')
    def test_debt_never_matches_doubtful_debt(self):
        with TemporaryDirectory() as td:
            p=Path(td)/'data/raw';p.mkdir(parents=True)
            pd.DataFrame({'period':['2025-Q4'],'BS_TOTAL_ASSETS':[1000], 'BS_EQUITY':[200], 'BS_PROVISION_DOUBTFUL_DEBTS':[-30], 'BS_SHORT_TERM_BORROWINGS':[100]}).to_csv(p/'TEST_balance.csv',index=False)
            s=repair_snapshot('TEST','CORPORATE',{},Path(td))
            self.assertIsNone(s['TotalDebt'])
    def test_denominator_zero_is_not_applicable(self):
        with TemporaryDirectory() as td:
            p=Path(td)/'data/raw';p.mkdir(parents=True)
            pd.DataFrame({'period':['2025-Q4'],'BS_TOTAL_ASSETS':[1000], 'BS_EQUITY':[0], 'BS_SHORT_TERM_BORROWINGS':[100], 'BS_LONG_TERM_BORROWINGS':[0]}).to_csv(p/'TEST_balance.csv',index=False)
            s=repair_snapshot('TEST','CORPORATE',{},Path(td))
            self.assertEqual(s['_MetricEvidence']['DebtEquity']['Status'],'NOT_APPLICABLE')
    def test_cache_invalidation_after_raw_changes(self):
        with TemporaryDirectory() as td:
            p=Path(td)/'data/raw';p.mkdir(parents=True)
            fp=p/'TEST_balance.csv'
            pd.DataFrame({'period':['2025-Q4'],'BS_TOTAL_ASSETS':[100]}).to_csv(fp,index=False)
            self.assertEqual(repair_snapshot('TEST','CORPORATE',{},Path(td))['TotalAssets'],100)
            pd.DataFrame({'period':['2025-Q4'],'BS_TOTAL_ASSETS':[2000]}).to_csv(fp,index=False)
            self.assertEqual(repair_snapshot('TEST','CORPORATE',{},Path(td))['TotalAssets'],2000)

class SuppliedData(unittest.TestCase):
    def test_bank_deposits_recovered(self):
        self.assertEqual(get_snapshot('BID')['CustomerDeposits'],2261489130000000)
        self.assertEqual(get_snapshot('ABB')['CustomerDeposits'],142256010000000)
    def test_corporate_debt_uses_both_borrowing_components(self):
        self.assertEqual(get_snapshot('FPT')['TotalDebt'],16368916886521+2080610610531)
    def test_securities_zero_debt_corrected(self):
        self.assertEqual(get_snapshot('SSI')['TotalDebt'],54038267285887)
        self.assertIsNone(get_snapshot('SSI')['MarginLoans'])
        self.assertGreater(get_snapshot('SSI')['Loans'],0)
    def test_insurance_routes_are_separate(self):
        s=get_snapshot('BVH');self.assertEqual(get_company('BVH')['EntityType'],'INSURANCE')
        self.assertNotIn('EBITDAMargin',[m for ms in groups_for('BVH').values() for m in ms])
        self.assertEqual(s['_MetricEvidence']['EBITDA']['Status'],'NOT_APPLICABLE')
        self.assertEqual(valuation('BVH',s)['Status'],'UNREVIEWED')
    def test_ratings_do_not_fill_unreviewed_inputs(self):
        for t in ['BID','ABB','BVH','FPT','SSI']:
            self.assertEqual(rate_company(t)['ICR'],'N/A',t)
        for t in ['BID','ABB']:self.assertEqual(rate_company(t)['Anchor'],'vnA-')
    def test_explicit_bank_assessment_reaches_same_anchor(self):
        r=rate_company('ABB',{'BusinessProfile':'Phù Hợp','CapitalEarnings':'Phù Hợp','RiskPosition':'Phù Hợp','FundingLiquidity':'Phù Hợp','ExternalSupportNotches':0})
        self.assertEqual(r['ICR'],'vnA-')
    def test_insurance_requires_scope_confirmation(self):
        r=rate_company('ABI',{'MacroIndustryRisk':1,'BusinessRisk':1,'FinancialRisk':1})
        self.assertEqual(r['Anchor'],'N/A');self.assertTrue(any('ScopeConfirmed' in x for x in r['MissingEvidence']))
    def test_five_years_no_stock_sum(self):
        h=same_period_history('FPT','CORPORATE','YTD',5,metrics=['TotalAssets','Revenue'])
        self.assertEqual(h.DisplayPeriod.nunique(),5)
        latest=h[h.DisplayPeriod.eq('6T/2026')].set_index('Metric').Value
        self.assertEqual(latest['TotalAssets'],get_snapshot('FPT')['TotalAssets'])
        raw=pd.read_csv(Path(__file__).resolve().parents[1]/'data/raw/FPT_income.csv')
        self.assertAlmostEqual(latest.Revenue,raw[raw.period.isin(['2026-Q1','2026-Q2'])].IS_NET_REVENUE.sum())
    def test_no_target_in_peer_benchmark(self):
        self.assertNotIn('FPT',peer_snapshot('FPT').Ticker.tolist())
    def test_benchmark_requires_five_observations(self):
        k=methodology_kpi_table('FPT');self.assertTrue(k.loc[k['Số DN'].lt(5),'TB ngành'].isna().all())
    def test_no_market_price_fair_value_fallback(self):
        self.assertIsNone(fair_value_range('BVH')['Base'])
    def test_per_share_values_are_vnd(self):
        for t in ['BID','ABB','BVH','FPT','SSI']:
            s=get_snapshot(t);self.assertGreater(s['BVPS'],1000);self.assertGreater(s['EPS'],100)

if __name__=='__main__':unittest.main(verbosity=2)
