"""Hồi quy lỗi Cloud thiếu data/raw; dữ liệu giả chỉ nằm trong thư mục tạm."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import pandas as pd
from scripts.financial_evidence import at_period, repair_snapshot, same_period_history


class BankHistoryFallback(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'data/raw').mkdir(parents=True)

    def history(self, rows):
        pd.DataFrame(rows).to_csv(self.root/'data/bank_history_long.csv',index=False)

    def row(self, metric, value, period='2026-Q2', **extra):
        return dict(Ticker='ABB',Period=period,Metric=metric,Value=value,**extra)

    def records(self, target='2026-Q2', basis='QUARTER', typ='BANK'):
        return at_period('ABB',typ,target,basis,self.root)

    def raw(self, rows, dataset='balance'):
        pd.DataFrame(rows).to_csv(self.root/f'data/raw/ABB_{dataset}_q.csv',index=False)

    def test_cloud_core_metrics_recovered_with_provenance(self):
        values={'TotalAssets':260e12,'GrossLoans':133e12,'CustomerDeposits':142e12,
                'Equity':22e12,'NPAT':1.2e12,'NetInterestIncome':1.7e12,
                'ROE':.21,'ROA':.016,'NIM':.026,'NPL':.012,'PB':1.24,'PE':6.0,'CASA':.09}
        self.history([self.row(m,v) for m,v in values.items()]);rs=self.records()
        for m,v in values.items():
            self.assertEqual(rs[m]['Value'],v,m)
            self.assertEqual(rs[m]['Status'],'OK',m)
            self.assertIn('bank_history_long.csv:'+m,rs[m]['Source'])

    def test_quarter_ytd_ttm_distinct_and_stock_ratio_not_summed(self):
        ps=['2025-Q3','2025-Q4','2026-Q1','2026-Q2']
        rows=[self.row('NPAT',v,p) for p,v in zip(ps,[2,3,5,7])]
        rows += [self.row(m,v,p) for p in ps for m,v in [('TotalAssets',100),('ROE',.1)]]
        self.history(rows)
        for b,want in [('QUARTER',7),('YTD',12),('TTM',17)]:
            r=self.records(basis=b)
            self.assertEqual(r['NPAT']['Value'],want)
            self.assertEqual(r['TotalAssets']['Value'],100)
            self.assertEqual(r['ROE']['Value'],.1)

    def test_explicit_ytd_cache_is_differenced(self):
        self.history([self.row('NPAT',10,'2026-Q1',Basis='YTD'),self.row('NPAT',30,Basis='YTD')])
        self.assertEqual(self.records()['NPAT']['Value'],20)
        self.assertEqual(self.records(basis='YTD')['NPAT']['Value'],30)

    def test_missing_flow_quarter_remains_missing(self):
        self.history([self.row('NPAT',7)])
        self.assertIsNone(self.records(basis='YTD')['NPAT']['Value'])
        self.assertIsNone(self.records(basis='TTM')['NPAT']['Value'])

    def test_raw_priority_and_real_zero(self):
        self.history([self.row('TotalAssets',999),self.row('GrossLoans',88),self.row('NPAT',99)])
        self.raw([dict(period='2026-Q2',id='BS_TOTAL_ASSETS',value=100),
                  dict(period='2026-Q2',id='BS_LOANS_TO_CUSTOMERS',value=0)])
        self.raw([dict(period='2026-Q2',id='IS_NET_PROFIT_AFTER_TAX',value=0)],'income')
        r=self.records()
        self.assertEqual(r['TotalAssets']['Value'],100)
        self.assertEqual(r['GrossLoans']['Value'],0)
        self.assertEqual(r['NPAT']['Value'],0)
        self.assertIn('data/raw/ABB_balance_q.csv',r['TotalAssets']['Source'])

    def test_raw_gaps_use_only_the_corresponding_cache_period(self):
        self.history([self.row('TotalAssets',90,'2025-Q2'),self.row('TotalAssets',100)])
        self.raw([dict(period='2026-Q2',id='BS_TOTAL_ASSETS',value=101)])
        self.assertEqual(self.records('2025-Q2')['TotalAssets']['Value'],90)
        self.assertEqual(self.records()['TotalAssets']['Value'],101)
        self.assertIsNone(self.records('2025-Q1')['TotalAssets']['Value'])

    def test_raw_conflict_is_not_hidden_by_cache(self):
        self.history([self.row('TotalAssets',100)])
        self.raw([dict(period='2026-Q2',id='BS_TOTAL_ASSETS',value=v) for v in [1,2]])
        r=self.records()['TotalAssets']
        self.assertEqual(r['Status'],'ERROR');self.assertIsNone(r['Value'])

    def test_conflicting_cache_values_are_errors(self):
        self.history([self.row('TotalAssets',v) for v in [100,200]])
        r=self.records()['TotalAssets']
        self.assertEqual(r['Status'],'ERROR');self.assertIsNone(r['Value'])

    def test_exact_metric_and_ticker_no_npl_coverage_collision(self):
        self.history([self.row('NPL',.01),self.row('LoanLossCoverage',1.2),
                      dict(Ticker='BID',Period='2026-Q2',Metric='NPL',Value=.5)])
        r=self.records();self.assertEqual(r['NPL']['Value'],.01)
        self.assertEqual(r['LoanLossCoverage']['Value'],1.2)

    def test_negative_profit_and_zero_are_preserved(self):
        self.history([self.row('NPAT',-5),self.row('NPL',0)])
        self.assertEqual(self.records()['NPAT']['Value'],-5)
        self.assertEqual(self.records()['NPL']['Value'],0)

    def test_cache_only_applies_to_banks_and_trusted_units(self):
        self.history([self.row('TotalAssets',100),self.row('EPS',2.9),self.row('BVPS',14.1)])
        for typ in ['CORPORATE','SECURITIES','INSURANCE']:
            self.assertIsNone(self.records(typ=typ)['TotalAssets']['Value'],typ)
        self.assertIsNone(self.records()['EPS']['Value'])
        self.assertIsNone(self.records()['BVPS']['Value'])

    def test_sparse_car_retains_its_date_not_current_benchmark(self):
        self.history([self.row('TotalAssets',100),self.row('CAR',.0987,'2025-Q2')])
        r=repair_snapshot('ABB','BANK',root=self.root)
        self.assertEqual(r['CAR'],.0987);self.assertEqual(r['CAR_AsOf'],'2025-Q2')
        self.assertIsNone(self.records()['CAR']['Value'])

    def test_five_year_history_does_not_fill_missing_year(self):
        self.history([self.row('TotalAssets',v,f'{y}-Q2') for y,v in [(2022,1),(2024,3),(2025,4),(2026,5)]])
        h=same_period_history('ABB','BANK','YTD',5,self.root,['TotalAssets'])
        self.assertEqual(len(h),5);self.assertEqual(h.Value.notna().sum(),4)
        self.assertTrue(h.loc[h.DisplayPeriod.eq('6T/2023'),'Value'].isna().all())

    def test_updated_history_invalidates_cache(self):
        self.history([self.row('TotalAssets',100)])
        self.assertEqual(self.records()['TotalAssets']['Value'],100)
        self.history([self.row('TotalAssets',2000)])
        self.assertEqual(self.records()['TotalAssets']['Value'],2000)


if __name__=='__main__':unittest.main(verbosity=2)
