"""Fixture kiểm tra phương pháp, không phải đánh giá tín nhiệm doanh nghiệp thực."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from scripts.insurance_rating import insurance_rating,anchor_options,MATRIX_1,MATRIX_2,REQUIRED,insurance_scorecard
from scripts.insurance_methodology import RUBRIC_KEYS,industry_score,institution_score,capital_grade,capital_earnings,flexibility,financial_score,GOV_RATINGS
from scripts.insurance_analysis import metric_pair,peer_universe,analysis_pack
from scripts.financial_evidence import at_period,ROOT
from scripts.universal_data import get_snapshot,universe
from scripts.insurance_metrics import extend_records

def assessed_inputs(**changes):
    r=dict(ScopeConfirmed=True,MacroIndustryRisk=1,BusinessRisk=1,CapitalAdequacy=1,
       ModelRepresentativeness='Trung lập',RegulatoryRisk='Thấp',RiskPosition=2,FinancialAdjustment=0,
       AssetQuality='Trên BBB',InvestmentStress=False,ManagementAssessment='Mạnh',FinancialPolicyAssessment='Mạnh',
       GovernanceHarmful=False,LiquidityScore=3,LiquidityNotches=0,OtherAdjustmentsNotches=0,ComparativeNotches=0,
       GroupSupportNotches=0,GovernmentSupportNotches=0,ExternalSupportNotches=0,
       DecisionReason='TEST FIXTURE ONLY',SupportSource='TEST FIXTURE ONLY',
       Evidence={k:{'Assessment':'Trung lập','Reason':'TEST FIXTURE ONLY','Source':'TEST FIXTURE ONLY'} for k in RUBRIC_KEYS})
    r.update(changes);return r

class Methodology(unittest.TestCase):
    def test_default_and_legacy_cannot_manufacture_rating(self):
        for o in [None,dict(ScopeConfirmed=True,MacroIndustryRisk=1,BusinessRisk=1,FinancialRisk=1,GovernanceLiquidityNotches=0)]:
            r=insurance_rating('ABI',o);self.assertEqual(r['ICR'],'N/A');self.assertFalse(r['AssessmentComplete'])
    def test_complete_fixture_is_traceable(self):
        r=insurance_rating('ABI',assessed_inputs());self.assertEqual(r['ICR'],'vnAA+')
        self.assertEqual(r['RatingStatus'],'SIMULATED');self.assertEqual(r['MissingEvidence'],[])
        self.assertEqual(r['AssessmentInputCount'],r['AssessmentInputTotal'])
    def test_no_scope_no_anchor(self):
        self.assertEqual(insurance_rating('ABI',assessed_inputs(ScopeConfirmed=False))['Anchor'],'N/A')
    def test_group_and_reinsurance_outside_scope(self):
        for t in ['BVH','PVI','PRE','VNR']:self.assertEqual(insurance_rating(t,assessed_inputs())['RatingStatus'],'NOT_APPLICABLE')
    def test_each_required_input_and_evidence_gate_icr(self):
        for key in REQUIRED:
            o=assessed_inputs();o.pop(key)
            with self.subTest(key=key):self.assertEqual(insurance_rating('ABI',o)['ICR'],'N/A')
        for field in ['Assessment','Source','Reason']:
            o=assessed_inputs();o['Evidence']['Brand'][field]=''
            self.assertEqual(insurance_rating('ABI',o)['ICR'],'N/A')
    def test_missing_support_preserves_sca(self):
        r=insurance_rating('ABI',assessed_inputs(ExternalSupportNotches=None))
        self.assertEqual((r['Anchor'],r['SCA'],r['ICR']),('vnAA+','vnAA+','N/A'))
    def test_matrix_one_6_or_7_needs_choice(self):
        for macro in [1,2,3]:
            o=assessed_inputs(MacroIndustryRisk=macro,BusinessRisk=6)
            r=insurance_rating('ABI',o);self.assertEqual(r['CombinedRiskCandidates'],(6,7));self.assertEqual(r['Anchor'],'N/A')
            for choice in [6,7]:self.assertEqual(insurance_rating('ABI',dict(o,CombinedRiskSelection=choice))['CombinedRiskScore'],choice)
    def test_anchor_ambiguous_candidates(self):
        o=assessed_inputs(BusinessRisk=2,CapitalAdequacy=3)
        r=insurance_rating('ABI',o);self.assertEqual(anchor_options(r),['vnAA-','vnA+'])
        self.assertEqual(insurance_rating('ABI',dict(o,AnchorSelection='vnAAA'))['Anchor'],'N/A')
        self.assertEqual(insurance_rating('ABI',dict(o,AnchorSelection='vnA+'))['Anchor'],'vnA+')
    def test_all_matrix_two_and_governance_cells_against_source(self):
        f=json.loads((Path(__file__).parent/'insurance_matrix_reference.json').read_text())
        for i,row in enumerate(f['9x12'][2:]):
            for j,text in enumerate(row[2:]):
                value=MATRIX_2[i][j]
                if text=='N/A':self.assertIsNone(value)
                elif 'thấp hơn' in text:self.assertEqual(value,('b-','lower'))
                else:
                    expected=tuple(x.strip().lower().removeprefix('vn') for x in text.split('hoặc'))
                    self.assertEqual(value,expected if len(expected)>1 else expected[0],(i,j))
        for i,row in enumerate(f['17x7'][2:]):self.assertEqual(GOV_RATINGS[i],[v.lower().removeprefix('vn') for v in row[1:]])
    def test_matrix_one_and_governance_sixteen_against_source(self):
        from scripts.insurance_methodology import GOV_MATRIX
        f=json.loads((Path(__file__).parent/'insurance_matrix_reference.json').read_text())
        for i,row in enumerate(f['matrix1'][2:]):
            for j,value in enumerate(row[1:]):self.assertEqual(MATRIX_1[i][j],(6,7) if 'hoặc' in value else int(value[0]))
        for i,row in enumerate(f['governance16'][2:]):
            expected=[v.replace('Rất Mạnh','Rất mạnh').replace('Khá','Khá mạnh') for v in row[1:]]
            self.assertEqual(GOV_MATRIX[i],expected)
    def test_matrix_na_not_missing_input(self):
        r=insurance_rating('ABI',assessed_inputs(CapitalAdequacy=8,FinancialAdjustment=1));self.assertEqual(r['RatingStatus'],'NOT_APPLICABLE')
    def test_regulatory_risk_sets_ten_and_sca_cap(self):
        r=insurance_rating('ABI',assessed_inputs(MacroIndustryRisk=4,BusinessRisk=4,RegulatoryRisk='Đáng kể',OtherAdjustmentsNotches=1,ComparativeNotches=1))
        self.assertEqual(r['FinancialRiskScore'],10);self.assertEqual(r['SCA'],'vnB+')
    def test_governance_harmful_caps_after_positive_adjustments(self):
        r=insurance_rating('ABI',assessed_inputs(GovernanceHarmful=True,ComparativeNotches=1));self.assertEqual(r['SCA'],'vnBB')
    def test_weak_performance_caps_business_at_three(self):
        o=assessed_inputs();o['Evidence']['OperatingPerformance']['Assessment']='Tiêu cực';self.assertEqual(insurance_rating('ABI',o)['BusinessRiskScore'],3)
    def test_adjustments_cannot_exceed_one(self):
        for k in ['OtherAdjustmentsNotches','ComparativeNotches']:
            with self.assertRaises(ValueError):insurance_rating('ABI',assessed_inputs(**{k:2}))
    def test_support_net_not_blind_sum(self):
        r=insurance_rating('ABI',assessed_inputs(GroupSupportNotches=1,GovernmentSupportNotches=1,ExternalSupportNotches=0));self.assertEqual(r['ExternalSupportNotches'],0)
        self.assertEqual(insurance_rating('ABI',assessed_inputs(ExternalSupportNotches=1))['ICR'],'N/A')
    def test_equal_financial_factors_enforce_matrix_eleven(self):
        r=insurance_rating('ABI',assessed_inputs(FinancialAdjustment=2))
        self.assertEqual(r['ICR'],'N/A')
        self.assertTrue(any('Bảng 11' in x for x in r['MissingEvidence']))
    def test_license_exception_needs_explicit_evidence(self):
        with self.assertRaises(ValueError):insurance_rating('ABI',assessed_inputs(OtherAdjustmentsNotches=-2))
        r=insurance_rating('ABI',assessed_inputs(OtherAdjustmentsNotches=-2,LicenseWithdrawal=True,ExceptionSource='TEST ONLY'))
        self.assertEqual(r['SCA'],'vnAA-')
    def test_type_and_range_validation(self):
        for change in [dict(MacroIndustryRisk=True),dict(CapitalAdequacy=9),dict(InvestmentStress=1),dict(AssetQuality='unknown')]:
            with self.assertRaises(ValueError):insurance_rating('ABI',assessed_inputs(**change))
    def test_industry_institution_rules(self):
        self.assertEqual(industry_score(.11,1,1,1,1),1);self.assertEqual(industry_score(.10,3,3,3,3),3)
        self.assertEqual(industry_score(.04,3,3,3,3),3);self.assertEqual(institution_score('Mạnh','Yếu'),3);self.assertEqual(institution_score('Yếu','Yếu',True),6)
    def test_capital_rules_and_boundary(self):
        self.assertEqual(capital_grade(4.1),1);self.assertEqual(capital_grade(.99),8);self.assertIsNone(capital_grade(3.5))
        for a,b in [(5,4),(1,1)]:self.assertEqual(capital_earnings(a,'Tích cực'),b)
        for a,b in [(2,4),(3,4),(4,4)]:self.assertEqual(capital_earnings(a,'Tiêu cực'),b)
    def test_financial_floors_no_auto_band_upgrade(self):
        for quality,floor in [('BBB',3),('BB',7),('B+ trở xuống',8)]:self.assertEqual(financial_score(1,-1,quality,True,'Thấp',False),floor)
        self.assertEqual(financial_score(1,0,'Trên BBB',False,'Thấp',True),8)
    def test_flexibility_rules(self):
        self.assertEqual(flexibility('Tích cực','Trung lập','Trung lập'),1);self.assertEqual(flexibility('Trung lập','Trung lập','Trung lập'),2)
        self.assertEqual(flexibility('Tiêu cực','Trung lập','Trung lập'),3);self.assertEqual(flexibility('Tiêu cực','Tiêu cực','Trung lập'),4)
    def test_scorecard_intermediates(self):
        self.assertTrue(any(r['Cấu phần']=='Bậc sau Bảng 17' for r in insurance_scorecard(insurance_rating('ABI',assessed_inputs()))))

class InsuranceData(unittest.TestCase):
    def test_summary_kpis_use_quarter_and_specialist_direction(self):
        from scripts.methodology_kpi_engine import methodology_kpi_table
        from scripts.insurance_analysis import insurance_summary
        q=methodology_kpi_table('ABI').set_index('Metric')
        self.assertEqual(q.loc['GrossWrittenPremium','Doanh nghiệp'],763469894410)
        a=insurance_summary('AIC');self.assertIsNone(a['Score'])
        self.assertTrue(any('Tỷ lệ kết hợp' in x for x in a['Risks']))
        self.assertFalse(any('Tỷ lệ kết hợp' in x for x in a['Strengths']))
    def test_insurance_reference_value_uses_verified_same_model_peers(self):
        from scripts.multisector_valuation import valuation
        a=valuation('ABI',get_snapshot('ABI'));self.assertEqual(a['Status'],'OK')
        self.assertAlmostEqual(a['FairValue'],a['DerivedBVPS']*a['PeerMultiple'])
        self.assertGreaterEqual(a['PeerPBCount'],5)
        self.assertIsNone(valuation('BVH',get_snapshot('BVH'))['FairValue'])
    def test_peers_separate_legal_models(self):
        self.assertEqual(set(peer_universe('ABI')),{'AIC','BIC','BLI','BMI','MIG','PGI','PTI'})
        self.assertEqual(peer_universe('BVH'),['PVI']);self.assertEqual(peer_universe('PRE'),['VNR'])
    def test_quarter_is_not_ttm(self):
        p=metric_pair('ABI','GrossWrittenPremium');v=p['Peers'].iloc[0].Value
        self.assertEqual(v,763469894410);self.assertNotEqual(v,get_snapshot('ABI')['GrossWrittenPremium']);self.assertEqual(set(p['Peers'].Period),{'2026-Q2'})
    def test_every_metric_has_paired_history_peer(self):
        pack=analysis_pack('ABI');self.assertEqual(len(pack),34)
        for r in pack:
            self.assertEqual(len(r['History']),5);self.assertEqual(len(r['Peers']),8);self.assertTrue(r['HistoryText'] and r['PeerText'] and r['MethodNote'])
    def test_underwriting_reconciles(self):
        for t in ['ABI','AIC','BIC','BLI','BMI','MIG','PGI','PTI']:
            r=at_period(t,'INSURANCE','2026-Q2','QUARTER');ratio=r['CombinedRatio']['Value']
            self.assertAlmostEqual(ratio,r['LossRatio']['Value']+r['ExpenseRatio']['Value'])
            self.assertAlmostEqual((1-ratio)*r['NetInsurancePremium']['Value'],r['UnderwritingProfit']['Value'],delta=1e7)
    def test_zero_borrowing_not_liabilities(self):
        self.assertEqual(at_period('ABI','INSURANCE','2026-Q2','QUARTER')['DebtEquity']['Value'],0)
    def test_missing_regulatory_data_not_invented(self):
        r=at_period('ABI','INSURANCE','2026-Q2','QUARTER')
        for m in ['InsuranceLiquidity','PaidInCapitalRequired','SolvencyRatio']:self.assertIsNone(r[m]['Value'])
    def test_small_group_has_no_mean(self):
        self.assertIsNone(metric_pair('BVH','TotalAssets')['PeerMean']);self.assertEqual(metric_pair('ABI','TotalAssets')['PeerCount'],7)
    def test_group_underwriting_not_applied(self):
        self.assertEqual(at_period('BVH','INSURANCE','2026-Q2','QUARTER')['CombinedRatio']['Status'],'NOT_APPLICABLE')
    def test_manual_liquidity_haircuts(self):
        from scripts.financial_evidence import _record
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'config').mkdir()
            values={'LiquidCash':100,'DepositsIGUnder6M':100,'DepositsOtherUnder6M':100,'GovernmentBondsLiquid':100,'RatedBondsIGLiquid':100,'RatedBondsOtherLiquid':100,'ListedEquitiesLiquid':100,'InsuranceContractObligations':200,'SolvencyMargin':300,'MinimumSolvencyMargin':100}
            pd.DataFrame([dict(Ticker='TEST',Period='2026-Q2',Metric=k,Value=v,Basis='END_PERIOD',Source='fixture',ReviewedBy='fixture',Scope='NONLIFE',Definition='fixture') for k,v in values.items()]).to_csv(root/'config/insurance_metric_inputs.csv',index=False)
            r=extend_records('TEST','2026-Q2','FY',{'NetInsurancePremium':_record('NetInsurancePremium')},root)
            self.assertEqual(r['StressedLiquidAssets']['Value'],599);self.assertEqual(r['InsuranceLiquidity']['Value'],2.995);self.assertEqual(r['SolvencyRatio']['Value'],3)
    def test_alias_normalization(self):
        frame=pd.DataFrame([dict(Ticker='XX1',EntityType='INSURANCE_NONLIFE',Methodology='OTHER',Sector='Khác'),dict(Ticker='XX2',EntityType='CORPORATE',Methodology='CORPORATE',Sector='Môi giới bảo hiểm')])
        with patch('scripts.universal_data.read_csv',return_value=frame):r=universe().set_index('Ticker')
        self.assertEqual(r.loc['XX1','EntityType'],'INSURANCE');self.assertEqual(r.loc['XX2','EntityType'],'CORPORATE')

if __name__=='__main__':unittest.main(verbosity=2)
