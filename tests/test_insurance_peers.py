"""Hồi quy phạm vi so sánh ngành, không mở rộng peer định giá một cách ngầm định."""
import unittest
from unittest.mock import patch
import pandas as pd
from scripts.insurance_analysis import metric_pair, analysis_pack, quarter_kpi_table
from scripts.insurance_peers import peer_universe, configured_peer_universe, quarter_peers, included_rows
from scripts.universal_data import get_snapshot

INSURERS={'ABI','AIC','BIC','BLI','BMI','BVH','MIG','PGI','PRE','PTI','PVI','VNR'}


class InsurancePeers(unittest.TestCase):
    def test_all_insurers_in_sector_comparison_for_every_target(self):
        for ticker in INSURERS:
            self.assertEqual(set(peer_universe(ticker)),INSURERS-{ticker})
            self.assertEqual(len(peer_universe(ticker)),11)

    def test_bvh_quarter_has_twelve_bars_and_mean_excludes_target(self):
        p=metric_pair('BVH','TotalAssets');rows=included_rows(p['Peers'])
        self.assertEqual(set(rows.Ticker),INSURERS)
        self.assertEqual(set(rows.Period),{'2026-Q2'})
        self.assertEqual(p['PeerCount'],11)
        self.assertAlmostEqual(p['PeerMean'],rows[rows.Ticker.ne('BVH')].Value.mean())
        self.assertEqual(p['PeerExclusions'],'')

    def test_specialist_ratios_keep_same_model_and_explain_exclusions(self):
        p=metric_pair('ABI','CombinedRatio');q=p['Peers']
        self.assertEqual(p['PeerCount'],7)
        self.assertTrue(included_rows(q).SameModel.all())
        self.assertEqual(set(q.Ticker),INSURERS)
        self.assertTrue(q.loc[~q.Included,'ExclusionReason'].str.len().gt(0).all())
        self.assertIn('PVI',p['PeerExclusions'])

    def test_bvh_pvi_nonlife_cohort_includes_all_ten_symbols(self):
        nonlife=INSURERS-{'PRE','VNR'}
        from scripts.universal_data import get_company
        for ticker in sorted(nonlife):
            self.assertEqual(get_company(ticker)['InsuranceSubtype'],'NONLIFE')
            self.assertEqual(set(configured_peer_universe(ticker)),nonlife-{ticker})
            for metric in ['GrossWrittenPremium','NetInsurancePremium','UnderwritingProfit','InsuranceReserves']:
                p=metric_pair(ticker,metric);q=included_rows(p['Peers'])
                self.assertEqual(set(q.Ticker),nonlife,(ticker,metric))
                self.assertEqual(p['PeerCount'],9)
                self.assertAlmostEqual(p['PeerMean'],q[q.Ticker.ne(ticker)].Value.mean())
                self.assertIn('9/11',p['PeerText'])
                self.assertIn('PRE',p['PeerExclusions']);self.assertIn('VNR',p['PeerExclusions'])
        for ticker in ['PRE','VNR']:
            p=metric_pair(ticker,'UnderwritingProfit')
            self.assertEqual(set(included_rows(p['Peers']).Ticker),{'PRE','VNR'})

    def test_comparison_reclassification_preserves_reporting_scope(self):
        from scripts.financial_evidence import insurance_reporting_subtype, comparable_model
        from scripts.insurance_rating import insurance_rating
        from scripts.universal_data import get_company
        for ticker in ['BVH','PVI']:
            meta=get_company(ticker);snap=get_snapshot(ticker)
            self.assertEqual(meta['InsuranceSubtype'],'NONLIFE')
            self.assertEqual(snap['InsuranceSubtype'],'NONLIFE')
            self.assertEqual(insurance_reporting_subtype(meta),'GROUP')
            self.assertEqual(insurance_reporting_subtype(snap),'GROUP')
            self.assertFalse(comparable_model(meta,get_company('ABI')))
            self.assertEqual(insurance_rating(ticker)['RatingBlocker'],'SCOPE')
            self.assertEqual(snap['_MetricEvidence']['CombinedRatio']['Status'],'NOT_APPLICABLE')
        q=metric_pair('BVH','UnderwritingProfit')['Peers'].set_index('Ticker')
        self.assertEqual(q.loc['BVH','Model'],'Phi nhân thọ')
        self.assertTrue(q.loc['ABI','SamePeerGroup']);self.assertFalse(q.loc['ABI','SameModel'])
        self.assertTrue(q.loc['ABI','Included'])
        for legacy in ['GROUP','NONLIFE','REINSURANCE','LIFE']:
            self.assertEqual(insurance_reporting_subtype({'InsuranceSubtype':legacy}),legacy)

    def test_kpi_chart_and_narrative_share_counts_and_values(self):
        table=quarter_kpi_table('BVH').set_index('Metric')
        for p in analysis_pack('BVH'):
            self.assertEqual(p['PeerCount'],table.loc[p['Metric'],'Số DN'])
            self.assertEqual(p['PeerCount'],len(included_rows(p['Peers'].iloc[1:])))
            if p['PeerMean'] is not None:self.assertAlmostEqual(p['PeerMean'],table.loc[p['Metric'],'TB ngành'])

    def test_missing_wrong_basis_and_other_sector_are_never_substituted(self):
        def evidence(t,typ,period,basis):
            self.assertEqual(period,'2026-Q2');self.assertEqual(basis,'QUARTER')
            return {'NPAT':dict(Value=None if t=='BMI' else 1,Status='MISSING' if t=='BMI' else 'OK',
                Basis='YTD' if t=='PVI' else 'QUARTER',Source='fixture',Reason='missing fixture')}
        with patch('scripts.insurance_peers.at_period',side_effect=evidence):
            q=quarter_peers('BVH','NPAT','2026-Q2',['BVH','PVI','PVI','BMI','ABI','TCB'])
        self.assertEqual(q.Ticker.tolist(),['BVH','PVI','BMI','ABI'])
        self.assertEqual(included_rows(q).Ticker.tolist(),['BVH','ABI'])
        self.assertEqual(q.set_index('Ticker').loc['PVI','ExclusionReason'],'Khác cơ sở tính')
        self.assertEqual(q.set_index('Ticker').loc['BMI','ExclusionReason'],'Thiếu số hợp lệ đúng quý')

    def test_registry_growth_has_no_top_ten_cutoff_and_missing_is_retained(self):
        rows=[dict(Ticker=f'I{i:02}',EntityType='INSURANCE',InsuranceSubtype='NONLIFE') for i in range(15)]
        def evidence(t,*args):return {'TotalAssets':dict(Value=None if t=='I14' else 100,Status='MISSING' if t=='I14' else 'OK')}
        with patch('scripts.insurance_peers.universe',return_value=pd.DataFrame(rows)), \
             patch('scripts.insurance_peers.get_company',return_value=rows[0]), \
             patch('scripts.insurance_peers.latest_period',return_value='2026-Q2'), \
             patch('scripts.insurance_peers.at_period',side_effect=evidence):
            peers=peer_universe('I00')
        self.assertEqual(len(peers),14);self.assertEqual(peers[-1],'I14')

    def test_valuation_and_qualitative_summary_keep_comparable_peers(self):
        from scripts.universal_data import peer_snapshot
        from scripts.multisector_valuation import valuation
        from scripts.insurance_presentation import executive_findings
        self.assertEqual(set(peer_snapshot('BVH').Ticker),{'PVI'})
        self.assertIsNone(valuation('BVH',get_snapshot('BVH'))['FairValue'])
        findings=executive_findings('BVH',analysis_pack('BVH'))
        self.assertNotIn('bình quân 11',str(findings['Strengths']+findings['Risks']))


if __name__=='__main__':unittest.main()
