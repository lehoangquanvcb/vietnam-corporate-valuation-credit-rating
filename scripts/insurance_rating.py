"""Mô phỏng phương pháp bảo hiểm phi nhân thọ Saigon Ratings 20.01.2025."""
from scripts.insurance_methodology import capital_earnings, flexibility, financial_score, governance_result, rubric_rows, GOV_LEVELS
ENGINE_VERSION='8.122.0'
INPUT_LABELS={
 'ScopeConfirmed':'Xác nhận phạm vi phi nhân thọ', 'MacroIndustryRisk':'Rủi ro vĩ mô và ngành',
 'BusinessRisk':'Rủi ro kinh doanh','CapitalAdequacy':'An toàn vốn dự phóng (Bảng 12)',
 'ModelRepresentativeness':'Tính đại diện mô hình vốn','RegulatoryRisk':'Rủi ro vốn pháp định',
 'RiskPosition':'Vị thế rủi ro (Bảng 13)', 'FinancialAdjustment':'Điều chỉnh tài chính (Bảng 11)',
 'AssetQuality':'Chất lượng tài sản sau thẩm định','InvestmentStress':'Rủi ro đầu tư gây căng thẳng vốn',
 'ManagementAssessment':'Quản trị và quản lý (Bảng 15)', 'FinancialPolicyAssessment':'Chính sách tài chính (Bảng 15)',
 'GovernanceHarmful':'Quản trị/chính sách gây hại trọng yếu', 'LiquidityScore':'Đánh giá thanh khoản (Bảng 18)',
 'LiquidityNotches':'Điều chỉnh thanh khoản đã thẩm định', 'OtherAdjustmentsNotches':'Điều chỉnh khác',
 'ComparativeNotches':'Điều chỉnh so sánh', 'GroupSupportNotches':'Hỗ trợ tập đoàn',
 'GovernmentSupportNotches':'Hỗ trợ Chính phủ','ExternalSupportNotches':'Hỗ trợ ròng đã loại trùng',
 'CombinedRiskSelection':'Lựa chọn 6/7 tại ma trận 01','AnchorSelection':'Lựa chọn Anchor tại ma trận 02',
 'Evidence':'Bằng chứng từng yếu tố', 'DecisionReason':'Cơ sở các quyết định tổng hợp và điều chỉnh',
 'SupportSource':'Nguồn phương pháp/hồ sơ hỗ trợ bên ngoài',
}
REQUIRED=tuple(k for k in INPUT_LABELS if k not in ['CombinedRiskSelection','AnchorSelection','Evidence'])
MODIFIERS=('GovernanceLiquidityNotches','OtherAdjustmentsNotches','ComparativeNotches')
SUPPORT=('GroupSupportNotches','GovernmentSupportNotches')

MATRIX_1 = [
    [1,2,3,4,5,(6,7)],
    [1,2,3,4,5,(6,7)],
    [2,2,3,4,5,(6,7)],
    [3,3,4,5,6,7],
    [5,5,5,6,6,7],
    [6,7,7,7,7,7],
]
# Rows = combined macro/industry/business (1..7); columns = financial (1..10)
# None = N/A in the source; tuple = alternatives requiring committee selection.
MATRIX_2 = [
    ['aa+','aa','aa-','a+','a','a-','bbb+','bbb-',None,None],
    ['aa','aa-',('aa-','a+'),('a+','a'),'a','a-','bbb','bb+','bb',None],
    ['a+',('a+','a'),('a','a-'),'a-','a-','bbb+','bbb','bb+','bb-','b+'],
    [('a','a-'),'a-','a-','bbb+','bbb+','bbb','bbb-','bb','bb-','b'],
    ['bbb+','bbb+',('bbb+','bbb'),'bbb','bbb','bbb-','bb+','bb','b+','b'],
    ['bbb-','bbb-','bbb-','bb+','bb+','bb+','bb','bb-','b','b'],
    ['bb-','bb-','bb-','bb-','bb-','bb-','b+','b','b',('b-','lower')],
]
SCALE = ['aaa','aa+','aa','aa-','a+','a','a-','bbb+','bbb','bbb-','bb+','bb','bb-','b+','b','b-','ccc','cc','c']

def _grade(x,lo,hi):
    if isinstance(x,bool) or not isinstance(x,int) or not lo <= x <= hi:
        raise ValueError(f'Điểm phải là số nguyên {lo}–{hi}; không suy đoán từ dữ liệu thiếu')
    return x

def _move(x,notches):
    if x not in SCALE: raise ValueError('Bậc xếp hạng không hợp lệ')
    return SCALE[max(0,min(len(SCALE)-1,SCALE.index(x)-notches))]


def anchor_options(result):
    raw=result.get('AnchorCandidates')
    if not isinstance(raw,tuple):return []
    return ['vn'+x.upper() for x in SCALE if x in raw or ('lower' in raw and SCALE.index(x)>SCALE.index('b-'))]

def missing_evidence_labels(result):
    out=[]
    for item in result.get('MissingEvidence',[]):
        key,sep,reason=str(item).partition(':')
        out.append(INPUT_LABELS.get(key,key)+((': '+reason.strip()) if sep else ''))
    return out

def insurance_rating(ticker,overrides=None):
    o=dict(overrides or {});ev=o.get('Evidence',{});rubric=rubric_rows(ev)
    r=dict(Ticker=str(ticker).upper(),Methodology='INSURANCE',EngineVersion=ENGINE_VERSION,
           MethodologyName='Saigon Ratings — Bảo hiểm phi nhân thọ 20.01.2025',
           Anchor='N/A',SCA='N/A',SACP='N/A',ICR='N/A',RatingStatus='UNREVIEWED',
           AssessmentComplete=False,DataSufficientForAutoRating=False,ProvisionalAutoScoring=False,
           MissingEvidence=[],AssessmentInputs=o,SubfactorEvidence=rubric,
           AssessmentInputTotal=len(REQUIRED)+len(rubric),AssessmentInputCount=0,
           CombinedRiskScore=None,CombinedRiskCandidates=None,FinancialRiskScore=None,AnchorCandidates=None)
    from scripts.financial_evidence import SCOPE_NOTE, insurance_reporting_subtype
    r['ScopeNote']=SCOPE_NOTE
    r['Audit']='Ma trận 01, 02, 16, 17 và giới hạn phương pháp 20.01.2025. Các đánh giá định tính, dự báo và quy tắc chưa lượng hóa cần bằng chứng thẩm định; chưa phải xếp hạng được phê duyệt.'
    from scripts.universal_data import get_company
    meta=get_company(ticker)
    r['InsuranceSubtype']=meta.get('InsuranceSubtype')
    r['InsuranceReportingSubtype']=insurance_reporting_subtype(meta)
    r['RatingBlocker']='INPUTS'
    # Ngoài phạm vi không phải 65 đánh giá còn trống. Giữ nguyên dữ liệu phân tích,
    # nhưng không mở phiếu/ma trận phi nhân thọ cho báo cáo tập đoàn hoặc tái BH.
    if r['InsuranceReportingSubtype'] in ['GROUP','LIFE','REINSURANCE']:
        r.update(RatingStatus='NOT_APPLICABLE',RatingBlocker='SCOPE',
                 AssessmentInputTotal=0,AssessmentInputCount=0,SubfactorEvidence=[])
        r['ApplicabilityReason']=(str(meta.get('InsuranceScope'))+'. Phương pháp đang cài đặt áp dụng cho pháp nhân bảo hiểm phi nhân thọ trực tiếp. '
            'Cần phương pháp phù hợp với loại hình hoặc BCTC riêng của pháp nhân thuộc phạm vi để xác định Anchor, SCA và ICR.')
        r['MissingEvidence']=['Phạm vi: '+r['ApplicabilityReason']]
        return r
    absent=r['MissingEvidence']
    for key in REQUIRED:
        v=o.get(key)
        valid=v is not None and v!='' and (key!='ScopeConfirmed' or v is True)
        if valid:r['AssessmentInputCount']+=1
        else:absent.append(key)
    missing_rubric=[x['Chỉ tiêu'] for x in rubric if not x['Đủ bằng chứng']]
    r['AssessmentInputCount']+=len(rubric)-len(missing_rubric)
    if missing_rubric:absent.append('Evidence: '+', '.join(missing_rubric))
    for key,lo,hi in [('MacroIndustryRisk',1,6),('BusinessRisk',1,6),('CapitalAdequacy',1,8),('RiskPosition',1,5),
                      ('FinancialAdjustment',-1,9),('LiquidityScore',1,5),('LiquidityNotches',-8,0),
                      ('OtherAdjustmentsNotches',-18,1),('ComparativeNotches',-1,1),
                      ('GroupSupportNotches',0,18),('GovernmentSupportNotches',0,18),('ExternalSupportNotches',0,18)]:
        if o.get(key) is not None:_grade(o[key],lo,hi)
    if o.get('OtherAdjustmentsNotches',0) is not None and o.get('OtherAdjustmentsNotches',0)<-1:
        if o.get('LicenseWithdrawal') is not True or not str(o.get('ExceptionSource','')).strip():
            raise ValueError('Hạ hơn một bậc chỉ khi thu hồi giấy phép đã có nguồn và quyết định Hội đồng')
    for key in ['InvestmentStress','GovernanceHarmful']:
        if o.get(key) is not None and not isinstance(o[key],bool):raise ValueError(key+': cần đánh giá Có/Không rõ ràng')
    for key,choices in [('ModelRepresentativeness',['Tích cực','Trung lập','Tiêu cực vừa phải','Tiêu cực']),
                        ('RegulatoryRisk',['Thấp','Đáng kể']),('AssetQuality',['Trên BBB','BBB','BB','B+ trở xuống']),
                        ('ManagementAssessment',GOV_LEVELS),('FinancialPolicyAssessment',GOV_LEVELS)]:
        if o.get(key) is not None and o[key] not in choices:raise ValueError('Giá trị không hợp lệ: '+key)
    # Phương pháp gốc chỉ bao phủ pháp nhân phi nhân thọ trực tiếp.
    if o.get('ScopeConfirmed') is not True:return r
    core=['MacroIndustryRisk','BusinessRisk','CapitalAdequacy','ModelRepresentativeness','RegulatoryRisk','FinancialAdjustment','AssetQuality','InvestmentStress','RiskPosition']
    if any(o.get(k) is None for k in core):return r
    business=o['BusinessRisk']
    if ev.get('OperatingPerformance',{}).get('Assessment')=='Tiêu cực':
        business=max(3,business)
        for key in ['MarketPosition','Geography','OtherDiversity']:
            if ev.get(key,{}).get('Assessment')=='Tích cực':absent.append('Evidence: hiệu quả yếu; '+key+' không được mạnh hơn trung lập nếu yếu kéo dài và đáng kể')
    r['BusinessRiskScore']=business
    capital=capital_earnings(o['CapitalAdequacy'],o['ModelRepresentativeness'])
    flex=flexibility(*(ev.get(k,{}).get('Assessment') for k in ['ExternalFunding','FinancialLeverage','InterestService']))
    r['CapitalEarningsScore']=capital;r['FinancialFlexibilityScore']=flex
    if flex is not None and o['RiskPosition']==flex:
        expected={1:-1,2:0,3:1,4:2}[flex]
        if o['FinancialAdjustment']!=expected:
            absent.append('FinancialAdjustment: hai yếu tố cùng mức nên Bảng 11 quy định '+str(expected))
    if o['RiskPosition']==5 and o['FinancialAdjustment']<3 and o['RegulatoryRisk']!='Đáng kể':
        absent.append('FinancialAdjustment: vị thế rủi ro mức 5 đòi hỏi +3 hoặc xấu hơn')
    fin=financial_score(capital,o['FinancialAdjustment'],o['AssetQuality'],False,o['RegulatoryRisk'],o['InvestmentStress'] and o['RiskPosition']==5)
    r['FinancialRiskScore']=fin
    if fin is None:return r
    combined=MATRIX_1[o['MacroIndustryRisk']-1][business-1]
    r['CombinedRiskCandidates']=combined
    if isinstance(combined,tuple):
        r['AssessmentInputTotal']+=1
        if o.get('CombinedRiskSelection') not in combined:
            absent.append('CombinedRiskSelection');return r
        combined=o['CombinedRiskSelection'];r['AssessmentInputCount']+=1
    r['CombinedRiskScore']=combined
    raw=MATRIX_2[combined-1][fin-1];r['AnchorCandidates']=raw
    if raw is None:
        r['RatingStatus']='NOT_APPLICABLE';r['RatingBlocker']='MATRIX'
        r['ApplicabilityReason']='Ma trận 02 không quy định bậc cho tổ hợp điểm đã nhập; cần quyết định xử lý có căn cứ, không ngoại suy.'
        absent.append('Ma trận 02: không quy định bậc cho tổ hợp điểm');return r
    if isinstance(raw,tuple):
        r['AssessmentInputTotal']+=1
        selected=str(o.get('AnchorSelection','')).lower().replace('vn','')
        if 'vn'+selected.upper() not in anchor_options(r):absent.append('AnchorSelection');return r
        r['AssessmentInputCount']+=1;anchor=selected
    else:anchor=raw
    r['Anchor']='vn'+anchor.upper()
    level,sca=governance_result(anchor,o.get('ManagementAssessment'),o.get('FinancialPolicyAssessment'))
    r['GovernanceAssessment']=level
    if sca is None:
        if level:absent.append('Quản trị: Bảng 17 không có hàng cho Anchor này; cần Hội đồng xử lý, không ngoại suy')
        return r
    r['AfterGovernance']='vn'+sca.upper()
    if any(o.get(k) is None for k in ['LiquidityNotches','LiquidityScore','OtherAdjustmentsNotches','ComparativeNotches']):return r
    governance_notch=SCALE.index(anchor)-SCALE.index(sca)
    r['GovernanceLiquidityNotches']=governance_notch+o['LiquidityNotches']
    for key in ['LiquidityNotches','OtherAdjustmentsNotches','ComparativeNotches']:
        r[key]=o[key];sca=_move(sca,o[key])
    caps=[]
    if o['RegulatoryRisk']=='Đáng kể':caps.append(('b+','Rủi ro vốn pháp định đáng kể'))
    if (o.get('ManagementAssessment')=='Yếu' and o.get('FinancialPolicyAssessment')=='Yếu') or o.get('GovernanceHarmful') is True:caps.append(('bb','Giới hạn quản trị/chính sách tài chính'))
    for ceiling,reason in caps:
        if SCALE.index(sca)<SCALE.index(ceiling):sca=ceiling
    r['RatingCaps']=[reason+': vn'+cap.upper() for cap,reason in caps]
    r['SCA']=r['SACP']='vn'+sca.upper();r['InternalNotches']=SCALE.index(anchor)-SCALE.index(sca)
    for key in SUPPORT:r[key]=o.get(key)
    r['ExternalSupportNotches']=o.get('ExternalSupportNotches')
    if any(o.get(k) is None for k in SUPPORT+('ExternalSupportNotches',)):return r
    # Hồ sơ hỗ trợ phải có đánh giá ròng, không tự cộng hai nguồn cùng rủi ro.
    if o['ExternalSupportNotches']>o['GroupSupportNotches']+o['GovernmentSupportNotches']:
        absent.append('ExternalSupportNotches: vượt tổng hỗ trợ từng nguồn; cần đối chiếu');return r
    if absent:return r
    r['ICR']='vn'+_move(sca,o['ExternalSupportNotches']).upper()
    r['RatingStatus']='SIMULATED';r['AssessmentComplete']=True;r['RatingBlocker']=None
    return r

def rating_status_text(result):
    if result.get('RatingBlocker')=='SCOPE':return 'Ngoài phạm vi phương pháp'
    if result.get('RatingBlocker')=='MATRIX':return 'Ma trận không quy định bậc'
    if result.get('RatingStatus')=='SIMULATED':return 'Mô phỏng — chờ phê duyệt'
    return 'Chưa đủ hồ sơ xếp hạng'

def rating_value_text(result,key='ICR'):
    value=result.get(key)
    if value is not None and str(value) not in ('N/A','nan','None'):return str(value).removeprefix('vn')
    if result.get('RatingBlocker')=='SCOPE':return 'Không áp dụng'
    if result.get('RatingBlocker')=='MATRIX':return 'Không có bậc tại ô ma trận'
    return 'Chưa xác định'

def insurance_scorecard(result,include_pending=False):
    if result.get('RatingBlocker')=='SCOPE':
        return [{'Cấu phần':'Phạm vi phương pháp','Kết quả':'Ngoài phạm vi phương pháp','Luận cứ':result['ApplicabilityReason']},
                {'Cấu phần':'Anchor / SCA / ICR','Kết quả':'Không áp dụng','Luận cứ':'Báo cáo tiếp tục phân tích tài chính và peer; không áp ma trận phi nhân thọ lên toàn tập đoàn hoặc loại hình khác.'}]
    o=result.get('AssessmentInputs',{});rows=[]
    def add(label,value):
        missing=value is None or value=='N/A'
        if missing and not include_pending:return
        rows.append({'Cấu phần':label,'Kết quả':'Cần bổ sung đánh giá' if missing else str(value),
                     'Luận cứ':'Chưa có đầu vào hoặc chưa đủ điều kiện tính.' if missing else 'Đầu vào chuyên viên hoặc kết quả ma trận; xem nguồn trong phiếu thẩm định.'})
    for k in ['MacroIndustryRisk','BusinessRisk','CapitalAdequacy','ModelRepresentativeness','RegulatoryRisk','RiskPosition','FinancialAdjustment','AssetQuality']:
        add(INPUT_LABELS[k],o.get(k))
    for k,label in [('BusinessRiskScore','Kinh doanh sau giới hạn'),('CapitalEarningsScore','Vốn và lợi nhuận'),('FinancialFlexibilityScore','Linh hoạt tài chính'),('FinancialRiskScore','Rủi ro tài chính sau giới hạn'),('CombinedRiskCandidates','Các lựa chọn ma trận 01'),('CombinedRiskScore','Điểm kết hợp đã chọn'),('Anchor','Anchor'),('GovernanceAssessment','Đánh giá quản trị tổng hợp'),('AfterGovernance','Bậc sau Bảng 17')]:add(label,result.get(k))
    for k in ['LiquidityScore','LiquidityNotches','OtherAdjustmentsNotches','ComparativeNotches']:add(INPUT_LABELS[k],o.get(k))
    add('SCA — xếp hạng độc lập',result.get('SCA'))
    if result.get('RatingCaps'):add('Giới hạn áp dụng','; '.join(result['RatingCaps']))
    for k in SUPPORT+('ExternalSupportNotches',):add(INPUT_LABELS[k],o.get(k))
    add('ICR — mô phỏng chờ phê duyệt',result.get('ICR'))
    if result.get('RatingStatus')!='SIMULATED':
        reason=result.get('ApplicabilityReason') or (str(result.get('AssessmentInputCount',0))+'/'+str(result.get('AssessmentInputTotal',0))+' đầu vào đã có; chi tiết hồ sơ cần bổ sung được tách khỏi phân tích tài chính.')
        rows.append({'Cấu phần':'Trạng thái hồ sơ XHTN','Kết quả':rating_status_text(result),'Luận cứ':reason})
    return rows
