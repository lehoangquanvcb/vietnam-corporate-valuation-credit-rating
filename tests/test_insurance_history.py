"""Đối chiếu bình quân đúng năm/cơ sở và bố cục biểu đồ theo yêu cầu người dùng."""
import unittest
from unittest.mock import patch
import pandas as pd
from scripts.insurance_analysis import metric_pair,figures
from scripts.insurance_history import historical_peer_benchmark,history_peer_sentence
from scripts.financial_evidence import at_period
from scripts.insurance_peers import peer_universe,period_peers


class HistoricalPeers(unittest.TestCase):
    def test_actual_fy_mean_excludes_company_and_uses_each_year(self):
        p=metric_pair('ABI','TotalAssets');h=p['PeerHistory']
        self.assertEqual(h.Period.tolist(),[f'{y}-Q4' for y in range(2021,2026)])
        peers=peer_universe('ABI')
        for r in h.itertuples():
            values=[at_period(t,'INSURANCE',r.Period,'FY')['TotalAssets']['Value'] for t in peers]
            self.assertEqual(r.PeerCount,11);self.assertNotIn('ABI',r.PeerTickers)
            self.assertAlmostEqual(r.PeerMean,sum(values)/len(values),delta=.01)
        self.assertNotEqual(h.iloc[0].PeerMean,h.iloc[-1].PeerMean)
        self.assertNotEqual(h.iloc[-1].PeerMean,p['PeerMean'])

    def test_period_modes_preserve_target_calendar_and_basis(self):
        for basis in ['QUARTER','YTD','TTM']:
            p=metric_pair('ABI','Revenue',basis,3)
            self.assertEqual(p['PeerHistory'].Period.tolist(),p['History'].Period.tolist())
            last=p['PeerHistory'].iloc[-1]
            frame=period_peers('ABI','Revenue',last.Period,peer_universe('ABI'),basis)
            z=frame.iloc[1:];z=z[z.Included]
            self.assertAlmostEqual(last.PeerMean,z.Value.mean(),delta=.01)

    def test_specialist_scope_keeps_group_ratios_out(self):
        p=metric_pair('ABI','CombinedRatio')
        for r in p['PeerHistory'].itertuples():
            self.assertNotIn('BVH',r.PeerTickers);self.assertNotIn('PVI',r.PeerTickers)
            self.assertNotIn('PRE',r.PeerTickers);self.assertNotIn('VNR',r.PeerTickers)
            self.assertGreater(r.PeerCount,0)

    def test_small_sample_mean_is_visible_with_count(self):
        p=metric_pair('VNR','GrossWrittenPremium')
        self.assertEqual(p['PeerHistory'].PeerCount.tolist(),[1]*5)
        self.assertTrue(p['PeerHistory'].PeerMean.notna().all())
        self.assertIn('1 peer',history_peer_sentence(p))

    def test_missing_year_is_not_zero_or_filled_and_sample_change_breaks_line(self):
        h=pd.DataFrame([dict(Period=f'{y}-Q4',DisplayPeriod=str(y),Basis='FY') for y in [2023,2024,2025]])
        def frame(*args):
            year=args[2][:4]
            rows=[dict(Ticker='OWN',Value=999.,Included=True,Basis='FY')]
            rows += [dict(Ticker='P1',Value=-4.,Included=year!='2024',Basis='FY'),
                     dict(Ticker='P2',Value=8.,Included=year=='2023',Basis='FY')]
            return pd.DataFrame(rows)
        with patch('scripts.insurance_history.universe',return_value=pd.DataFrame()),patch('scripts.insurance_history.period_peers',side_effect=frame):
            result=historical_peer_benchmark('OWN','NPAT',h,'FY',['P1','P2'])
        ph=result['PeerHistory']
        self.assertEqual(ph.PeerCount.tolist(),[2,0,1])
        self.assertEqual(ph.iloc[0].PeerMean,2.)
        self.assertTrue(pd.isna(ph.iloc[1].PeerMean));self.assertEqual(ph.iloc[2].PeerMean,-4.)
        self.assertEqual(result['PeerHistoryBreaks'],[1,2])

    def test_history_plot_has_actual_peer_trace_and_counts(self):
        p=metric_pair('ABI','Equity');history,quarter=figures(p)
        traces=[t for t in history.data if t.name=='Bình quân peer']
        self.assertEqual(len(traces),1)
        self.assertEqual(list(traces[0].customdata),p['PeerHistory'].PeerCount.tolist())
        self.assertEqual(list(traces[0].y),(p['PeerHistory'].PeerMean*1e-9).tolist())
        self.assertTrue(history.layout.showlegend)
        self.assertEqual(quarter.data[0].type,'bar')

    def test_reserve_source_break_is_not_interpreted_as_peer_growth(self):
        p=metric_pair('ABI','InsuranceReserves')
        self.assertIn(1,p['PeerHistoryBreaks'])
        self.assertIn('đứt gãy',history_peer_sentence(p))


if __name__=='__main__':unittest.main()
