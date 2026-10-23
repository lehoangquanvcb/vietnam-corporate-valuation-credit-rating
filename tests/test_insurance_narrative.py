"""Kiểm tra lập luận đổi theo bằng chứng, không suy diễn điểm XHTN."""
import unittest
import pandas as pd
from scripts.insurance_narrative import metric_narrative, enrich_pack, last_change, section_findings, overall_conclusion
from scripts.insurance_analysis import analysis_pack, metric_pair
from scripts.insurance_rating import insurance_rating


def pair(metric, values, current, peers=(.1,.2,.3,.4,.5)):
    h=pd.DataFrame([dict(Period=f'{2021+i}-FY',DisplayPeriod=str(2021+i),Value=v,
                         Status='OK' if v is not None else 'MISSING',Basis='FY') for i,v in enumerate(values)])
    q=pd.DataFrame([dict(Ticker=t,Period='2026-Q2',Value=v,Status='OK' if v is not None else 'MISSING',
                         Included=v is not None,SameModel=True,Basis='QUARTER')
                    for t,v in [('OWN',current)]+[(f'P{i}',v) for i,v in enumerate(peers)]])
    return dict(Metric=metric,Label=metric,History=h,Peers=q,Period='2026-Q2',Basis='FY',HistoryBreaks=[],
                PeerCandidateCount=len(peers),PeerScope='Cùng loại hình')


class Narrative(unittest.TestCase):
    def test_profit_reversal_changes_conclusion(self):
        positive=metric_narrative(pair('NPAT',[100,120],30))
        negative=metric_narrative(pair('NPAT',[100,-20],-5))
        self.assertIn('tạo nguồn bổ sung vốn',positive['ConclusionText'])
        self.assertIn('hao hụt',negative['ConclusionText'])
        self.assertNotIn('tạo nguồn bổ sung vốn',negative['ConclusionText'])

    def test_loss_reduction_is_not_a_positive_profit(self):
        r=metric_narrative(pair('NPAT',[-100,-20],-5))
        self.assertIn('hao hụt',r['ConclusionText'])
        self.assertIn('cải thiện',r['ConclusionText'])

    def test_combined_decomposition_is_arithmetic_not_invented_cause(self):
        pack=[pair('CombinedRatio',[1.1,1.0],.95),pair('LossRatio',[.5,.3],.4),pair('ExpenseRatio',[.6,.7],.55)]
        enrich_pack(pack,'NONLIFE');text=pack[0]['AnalysisText']
        self.assertIn('20,00 điểm phần trăm',text);self.assertIn('10,00 điểm phần trăm',text)
        self.assertIn('Chi phí gia tăng bù trừ',text)
        self.assertNotIn('thiên tai',text)

    def test_inconsistent_components_do_not_attribute_change(self):
        pack=[pair('CombinedRatio',[1.3,1.0],.95),pair('LossRatio',[.5,.3],.4),pair('ExpenseRatio',[.6,.7],.55)]
        enrich_pack(pack,'NONLIFE')
        self.assertIn('chưa khớp',pack[0]['AnalysisText'])
        self.assertNotIn('bù trừ',pack[0]['AnalysisText'])

    def test_negative_claims_does_not_mean_strong_underwriting(self):
        r=metric_narrative(pair('LossRatio',[.4,-.1],-.1))
        self.assertIn('đối chiếu',r['ConclusionText'])
        self.assertNotIn('hỗ trợ biên',r['ConclusionText'])

    def test_combined_break_even_boundary(self):
        for v,word in [(.9,'thặng dư'),(1.,'hòa vốn'),(1.1,'thâm hụt')]:
            r=metric_narrative(pair('CombinedRatio',[.9,1.1],v))
            self.assertIn(word,r['ConclusionText'])

    def test_no_change_across_missing_or_source_break(self):
        for p in [pair('Equity',[100,None,120],130),pair('Equity',[100,120],130)]:
            if len(p['History'])==2:p['HistoryBreaks']=[1]
            self.assertIsNone(last_change(p))
            self.assertNotIn('được củng cố ở năm cuối',metric_narrative(p)['ConclusionText'])

    def test_last_year_growth_and_whole_period_decline_both_visible(self):
        r=metric_narrative(pair('ROE',[.2,.1,.15],.16))
        self.assertIn('giảm từ',r['NarrativeHistory'])
        self.assertIn('Riêng 2023',r['NarrativeHistory'])
        self.assertIn('tăng 5,00 điểm phần trăm',r['NarrativeHistory'])

    def test_no_cross_period_causation(self):
        a=pair('Revenue',[100,120],30);b=pair('NPAT',[10,20],5);b['Period']='2026-Q1'
        r=metric_narrative(a,{'Revenue':a,'NPAT':b})
        self.assertNotIn('Lợi nhuận tăng nhanh',r['AnalysisText'])
        b['Period']='2026-Q2';b['History'].loc[1,'Period']='2024-FY'
        r=metric_narrative(a,{'Revenue':a,'NPAT':b})
        self.assertNotIn('Lợi nhuận tăng nhanh',r['AnalysisText'])

    def test_missing_own_value_is_not_filled_with_peer(self):
        r=metric_narrative(pair('InsuranceLiquidity',[None,None],None))
        self.assertIn('Chưa đủ căn cứ',r['ConclusionText'])
        self.assertNotIn('vùng mạnh',r['AnalysisText'])

    def test_zero_debt_distinct_from_missing(self):
        zero=metric_narrative(pair('DebtEquity',[0,0],0))
        missing=metric_narrative(pair('DebtEquity',[None,None],None))
        self.assertIn('Nợ vay bằng 0',zero['ConclusionText'])
        self.assertNotIn('Nợ vay bằng 0',missing['ConclusionText'])

    def test_liquidity_boundaries_do_not_assign_full_score(self):
        for v,word in [(.99,'yếu'),(1.,'đầy đủ'),(2.2,'đầy đủ'),(2.21,'mạnh')]:
            r=metric_narrative(pair('InsuranceLiquidity',[v,v],v))
            self.assertIn('vùng '+word,r['AnalysisText'])
            self.assertNotIn('AAA',str(r))
            self.assertIn('thời điểm chi trả',r['ConclusionText'])

    def test_small_peer_sample_is_direct_comparison(self):
        r=metric_narrative(pair('ROE',[.1,.2],.15,peers=(.1,.2)))
        self.assertIn('Đối chiếu trực tiếp',r['NarrativePeer'])
        self.assertNotIn('Bình quân',r['NarrativePeer'])

    def test_conflicting_mean_and_median_is_explained(self):
        r=metric_narrative(pair('ROE',[.1,.2],.3,peers=(.1,.1,.1,.2,2.0)))
        self.assertIn('hai vị trí khác nhau',r['NarrativePeer'])

    def test_high_roe_from_leverage_not_automatically_asset_improvement(self):
        pack=[pair('ROE',[.1,.15],.16),pair('ROA',[.05,.04],.04),pair('EquityAssets',[.5,.3],.3)]
        enrich_pack(pack,'NONLIFE')
        self.assertIn('ảnh hưởng đòn bẩy',pack[0]['AnalysisText'])

    def test_gross_investment_revenue_not_called_net_profit(self):
        pack=[pair('NPAT',[10,20],5),pair('UnderwritingProfit',[-10,-5],-2),pair('InvestmentIncome',[20,30],8)]
        enrich_pack(pack,'NONLIFE')
        self.assertIn('các hoạt động khác',pack[0]['AnalysisText'])
        self.assertIn('không phải lợi nhuận đầu tư ròng',pack[0]['AnalysisText'])

    def test_valuation_is_not_credit_strength(self):
        for m in ('PB','PE'):
            r=metric_narrative(pair(m,[1.2,1.1],.9))
            self.assertIn('không phải điểm mạnh hay yếu tín nhiệm',r['ConclusionText'])

    def test_overall_conclusion_balances_profit_against_capital(self):
        pack=[pair('NPAT',[10,20],5),pair('EquityAssets',[.3,.2],.18)]
        self.assertIn('chưa thể kết luận sức chịu tổn thất cải thiện đồng bộ',str(overall_conclusion(pack,'NONLIFE')))
        pack[1]['History'].loc[1,'Value']=.4
        self.assertIn('cùng cải thiện',str(overall_conclusion(pack,'NONLIFE')))

    def test_overall_conclusion_does_not_join_different_years(self):
        pack=[pair('NPAT',[10,20],5),pair('EquityAssets',[.3,.4],.45)]
        pack[1]['History'].loc[:,'Period']=['2022-FY','2023-FY']
        self.assertNotIn('cùng cải thiện',str(overall_conclusion(pack,'NONLIFE')))


class ActualPortfolio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs={t:analysis_pack(t) for t in ('ABI','BVH','PTI')}

    def test_abi_and_pti_produce_different_business_conclusions(self):
        a={p['Metric']:p for p in self.packs['ABI']};t={p['Metric']:p for p in self.packs['PTI']}
        self.assertIn('mở rộng',a['GrossWrittenPremium']['ConclusionText'])
        self.assertIn('thu hẹp',t['GrossWrittenPremium']['ConclusionText'])
        self.assertIn('bù trừ',t['CombinedRatio']['AnalysisText'])

    def test_bvh_scope_and_source_break_preserved(self):
        p={r['Metric']:r for r in self.packs['BVH']}
        self.assertEqual(p['CombinedRatio']['Peers'].iloc[0].Status,'NOT_APPLICABLE')
        self.assertIn('không diễn giải số âm thành lỗ khai thác phi nhân thọ',p['UnderwritingProfit']['AnalysisText'])
        self.assertIn('đứt gãy',p['InsuranceReserves']['NarrativeHistory'])
        self.assertIn('16,1%',p['EquityAssets']['AnalysisText'])
        self.assertEqual(p['TotalAssets']['PeerCount'],11)
        self.assertEqual(p['GrossWrittenPremium']['PeerCount'],9)
        self.assertEqual(insurance_rating('BVH')['RatingBlocker'],'SCOPE')

    def test_latest_recovery_does_not_hide_longer_term_weakness(self):
        from scripts.insurance_presentation import executive_findings
        r=executive_findings('ABI',self.packs['ABI'])
        self.assertIn('chưa trở lại mức đầu chuỗi',str(r['Risks']))
        r=executive_findings('BVH',self.packs['BVH'])
        self.assertIn('Bộ đệm vốn tương đối mỏng hơn',str(r['Risks']))

    def test_every_evidenced_metric_has_reasoning_and_conclusion(self):
        from scripts.insurance_presentation import has_evidence
        for ticker,pack in self.packs.items():
            for p in pack:
                if has_evidence(p):
                    self.assertTrue(p['AnalysisText'],(ticker,p['Metric']))
                    self.assertTrue(p['ConclusionText'],(ticker,p['Metric']))
                    self.assertIn(p['Period'],p['NarrativePeer'])
            text=str(section_findings(pack,'GROUP' if ticker=='BVH' else 'NONLIFE'))
            self.assertNotIn('Phú Hưng',text)
            self.assertIn('không phải bằng chứng doanh nghiệp mất khả năng chi trả',text)
        self.assertFalse(insurance_rating('ABI')['AssessmentComplete'])


if __name__=='__main__':unittest.main()
