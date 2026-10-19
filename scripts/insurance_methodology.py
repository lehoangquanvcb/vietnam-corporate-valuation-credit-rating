"""Quy tắc xác định được trong phương pháp phi nhân thọ 20.01.2025.

Không tự lượng hóa kết luận định tính hoặc tự chọn các trường hợp chồng lấn.
"""
QUAL=['Tích cực','Trung lập','Tiêu cực']
RUBRIC={
 'I. Vĩ mô và ngành':[
  ('MacroEvidence','Vĩ mô','Bảng 03: tăng trưởng, lạm phát, tín dụng/nợ xấu, lãi suất/tỷ giá, thị trường trái phiếu và thể chế.'),
  ('IndustryProfitability','Sinh lợi ngành','Bảng 04–05: ROE kỳ vọng >10% / 4–10% / <4%; hoặc ROS và tỷ lệ kết hợp. Mẫu ROE ít nhất 60% số doanh nghiệp.'),
  ('ProductRisk','Rủi ro sản phẩm','Tích cực khi mọi nguồn biến động thấp; tiêu cực khi có nguồn cao; xét hiệu lực tái bảo hiểm.'),
  ('EntryBarriers','Rào cản gia nhập','Bảng 06: pháp lý hoặc hoạt động cao → tích cực; cả hai thấp → tiêu cực.'),
  ('MarketOutlook','Triển vọng thị trường','Bảng 07: tăng trưởng phí thực năm hiện tại và hai năm tiếp theo đều tăng/đều giảm; còn lại trung lập.'),
  ('InstitutionalRisk','Khung thể chế','Bảng 08: pháp lý và hồ sơ quản lý mạnh/trung bình/yếu; cộng 1 điểm rủi ro nếu thiếu chuẩn quản trị/minh bạch.')],
 'II. Rủi ro kinh doanh':[
  ('OperatingPerformance','Hiệu quả kinh doanh','Bảng 09–10: quartile ROE/ROS, kết hợp, bồi thường, dự phòng/phí; năm hiện tại và dự báo hai năm. Lịch sử chỉ là bằng chứng.'),
  ('Brand','Thương hiệu/danh tiếng','Lợi thế ảnh hưởng thường ít nhất nửa tổng phí; khảo sát/đánh giá độc lập, giữ khách hàng, đổi mới sản phẩm.'),
  ('MarketPosition','Vị thế thị trường','Thị phần phí gốc bền vững ≥14% là một ví dụ; không lấy tổng phí của peer niêm yết làm toàn thị trường.'),
  ('Distribution','Kiểm soát phân phối','Khả năng kiểm soát khoảng nửa phí, đa dạng kênh, chi phí duy trì/phát triển và phụ thuộc đối tác.'),
  ('Geography','Đa dạng địa lý','Hiện diện tại thị trường và mức thâm nhập bảo hiểm; hạn chế tập trung địa bàn.'),
  ('OtherDiversity','Đa dạng hóa khác','Một dòng sản phẩm >80% tổng phí → tiêu cực. Hiệu quả yếu kéo dài giới hạn vị thế/đa dạng ở trung lập.')],
 'III. Vốn và rủi ro tài chính':[
  ('CapitalEvidence','An toàn vốn và dự báo','Bảng 12: vốn thực góp/vốn pháp định hiện tại và hai năm tới; nguồn giấy phép và dự báo.'),
  ('ModelEvidence','Tính đại diện mô hình','Tích cực/mức 5–8 cải thiện 1; tiêu cực vừa phải/mức 1–3 giảm 1; tiêu cực/mức 1–2 giảm 2, mức 3 giảm 1.'),
  ('FXRisk','Rủi ro tỷ giá','Lệch ngoại tệ chưa phòng vệ >10% nợ phải trả là trọng yếu.'),
  ('InvestmentRisk','Đòn bẩy đầu tư','Tài sản rủi ro/đầu tư hoặc nghĩa vụ: <20% kéo dài hỗ trợ tích cực; >100% tiêu cực. Xác nhận mẫu số.'),
  ('PortfolioDiversity','Đa dạng danh mục','Tập trung ngành ≤15%, 15–30%, >30%; xét riêng khoảng 50% tài sản nợ Chính phủ.'),
  ('OtherRisk','Rủi ro vốn/lợi nhuận khác','Tái bảo hiểm, lạm phát, lãi suất, bồi thường, hành vi; đánh giá mức độ trọng yếu.'),
  ('ExternalFunding','Tiếp cận nguồn vốn','Nguồn vốn/thanh khoản đa dạng, tín dụng, thị trường vốn, cổ đông, chất lượng nhà tái bảo hiểm.'),
  ('FinancialLeverage','Đòn bẩy tài chính','Nợ vay/VCSH >15% cần xem xét; nợ đáo hạn hai năm >20% VCSH cần cân nhắc hạ đánh giá.'),
  ('InterestService','Khả năng trả lãi','Có xét EBITDA/lãi vay. Không phát sinh lãi vay không tự động chứng minh trung lập; cần thẩm định.')],
 'IV. Thanh khoản':[
  ('MarketConfidence','Niềm tin thị trường','Khả năng thanh khoản bị tác động khi niềm tin suy giảm.'),
  ('CollateralCalls','Bổ sung tài sản bảo đảm','Điều khoản ký quỹ khi tài sản giảm giá hoặc bị hạ hạng.'),
  ('DefaultLiquidity','Thanh khoản khi vi phạm nghĩa vụ','Điều khoản với đối tác/bên cho vay và tác động lan truyền.'),
  ('LiquidityIndicator','Chỉ số thanh khoản','Tài sản thanh khoản sau haircut/nghĩa vụ bảo hiểm: >2,2 mạnh; 1–2,2 đầy đủ; <1 yếu. Bảng 18 cần xét cả bốn yếu tố.')],
 'V. Quản trị và chính sách tài chính':[
  ('StrategyProcess','Quy trình chiến lược','Bảng 14: mục tiêu tài chính/kinh doanh cụ thể, đo lường kết quả.'),
  ('StrategyFit','Chiến lược và năng lực','Sự nhất quán với năng lực tổ chức và điều kiện thị trường.'),
  ('StrategyExecution','Thực thi chiến lược','Chuyển quyết định thành hành động; truy vấn, điều chỉnh, so sánh kết quả.'),
  ('RiskStandards','Tiêu chuẩn quản lý rủi ro','Toàn diện, giám sát, giảm thiểu rủi ro và khẩu vị rủi ro.'),
  ('PerformanceStandards','Tiêu chuẩn thực hiện','Kỷ luật, cam kết, chuẩn mực phù hợp.'),
  ('ManagementPerformance','Hiệu quả quản lý','Sụt giảm ngoài dự kiến về thu nhập/dòng tiền do vận hành.'),
  ('ManagementExpertise','Chuyên môn/kinh nghiệm','Kinh nghiệm, năng lực kiểm soát và thực hiện kế hoạch.'),
  ('ManagementDepth','Chiều sâu quản lý','Phụ thuộc nhân sự chủ chốt và khả năng duy trì hoạt động.'),
  ('BoardEffectiveness','Hiệu quả ban lãnh đạo','Độc lập, giám sát rủi ro và xung đột lợi ích.'),
  ('OwnershipControl','Sở hữu và kiểm soát','Quyền lợi thiểu số, ảnh hưởng của chủ sở hữu kiểm soát.'),
  ('ManagementCulture','Văn hóa quản lý','Cân bằng lợi ích, xử lý bất đồng, thù lao và chấp nhận rủi ro.'),
  ('Compliance','Tuân thủ pháp luật/thuế','Lịch sử vi phạm, quan hệ cơ quan quản lý.'),
  ('Communication','Thông tin liên lạc','Truyền thông nhất quán về vấn đề quan trọng.'),
  ('InternalControls','Kiểm soát nội bộ','Bằng chứng hệ thống kiểm soát nội bộ vận hành hiệu quả.'),
  ('FinancialTransparency','Minh bạch tài chính','BCTC phản ánh bản chất kinh tế và cho phép hiểu nghiệp vụ trọng yếu.'),
  ('FinancialDiscipline','Kỷ luật tài chính','Nợ thực tế và nợ dự phóng, hành động giảm nợ.'),
  ('FinancialPolicy','Khung chính sách tài chính','Lượng hóa, công bố, khả thi và bền vững.'),
  ('CapitalProviderControl','Kiểm soát bên cấp vốn','≥40% vốn thường hoặc kiểm soát đa số quyền biểu quyết ưu đãi theo Bảng 15.')],
}
RUBRIC_KEYS=[key for items in RUBRIC.values() for key,_,_ in items]

def industry_score(roe,product,barriers,outlook,institution):
    if any(x is None for x in [roe,product,barriers,outlook,institution]):return None
    if any(x not in (1,3,6) for x in [product,barriers,outlook]) or institution not in range(1,7):raise ValueError('Điểm ngành ngoài thang phương pháp')
    profit=1 if roe>.10 else 6 if roe<.04 else 3
    return (profit+product+barriers+outlook+institution)/5

def institution_score(legal,record,weak_transparency=False):
    levels=['Mạnh','Trung bình','Yếu']
    if legal not in levels or record not in levels:return None
    return 1+levels.index(legal)+levels.index(record)+int(weak_transparency)

def capital_grade(ratio):
    if ratio is None:return None
    # Ngưỡng đúng bằng điểm biên cần chuyên viên giải quyết cách diễn đạt của nguồn.
    if ratio in [1,1.5,2,2.5,3,3.5,4]:return None
    for grade,threshold in enumerate([4,3.5,3,2.5,2,1.5,1],1):
        if ratio>threshold:return grade
    return 8

def capital_earnings(grade,model):
    if grade not in range(1,9) or model not in ['Tích cực','Trung lập','Tiêu cực vừa phải','Tiêu cực']:return None
    adj=-1 if model=='Tích cực' and grade>=5 else 1 if model=='Tiêu cực vừa phải' and grade<=3 else 2 if model=='Tiêu cực' and grade<=2 else 1 if model=='Tiêu cực' and grade==3 else 0
    return min(8,max(1,grade+adj))

def flexibility(access,leverage,interest):
    a=[access,leverage,interest]
    if any(v not in QUAL for v in a):return None
    neg=a.count('Tiêu cực')
    if neg>=2:return 4
    if neg==1:return 3
    return 1 if access=='Tích cực' else 2

def financial_score(capital,adjustment,asset_quality,diversified,regulatory_risk,investment_stress):
    if regulatory_risk=='Đáng kể':return 10
    if capital not in range(1,9) or adjustment is None or asset_quality not in ['Trên BBB','BBB','BB','B+ trở xuống']:return None
    if not isinstance(adjustment,int) or not -1<=adjustment<=9:raise ValueError('Điều chỉnh rủi ro tài chính không hợp lệ')
    if capital<=3 and adjustment<0:adjustment=0
    score=min(10,max(1,capital+adjustment))
    quality=['Trên BBB','BBB','BB','B+ trở xuống'].index(asset_quality)
    # Chất lượng đã được chuyên viên điều chỉnh theo hạng cụ thể; không tự nhảy nhóm hạng.
    score=max(score,[1,3,7,8][quality])
    if investment_stress:score=max(score,8)
    return score

# Bảng 16: hàng chính sách tài chính, cột quản trị/quản lý.
GOV_LEVELS=['Mạnh','Khá','Trung bình','Yếu']
GOV_MATRIX=[['Rất mạnh','Mạnh','Khá mạnh','Yếu'],['Mạnh','Khá mạnh','Trung bình','Yếu'],
            ['Khá mạnh','Trung bình','Trung bình','Rất yếu'],['Trung bình','Trung bình','Yếu','Rất yếu']]
GOV_COLUMNS=['Rất mạnh','Mạnh','Khá mạnh','Trung bình','Yếu','Rất yếu']
GOV_ANCHORS=['aa+','aa','aa-','a+','a','a-','bbb+','bbb','bbb-','bb+','bb','bb-','b+','b','b-']
GOV_RATINGS=[
 ['aa+','aa+','aa','a+','bbb+','bbb'],['aa','aa','aa-','a+','bbb+','bbb'],
 ['aa-','aa-','a+','a','bbb','bbb'],['a+','a+','a+','a','bbb','bbb-'],
 ['a+','a','a','a-','bbb-','bbb-'],['a','a-','a-','bbb+','bbb-','bbb-'],
 ['a-','bbb+','bbb+','bbb','bb+','bb+'],['bbb+','bbb','bbb','bbb-','bb+','bb+'],
 ['bbb','bbb-','bbb-','bb+','bb','bb'],['bbb-','bb+','bb+','bb','bb','bb-'],
 ['bb+','bb','bb','bb-','b+','b+'],['bb','bb-','bb-','b+','b+','b'],
 ['bb-','b+','b+','b','b-','b-'],['b+','b','b','b-','b-','b-'],
 ['b','b-','b-','b-','b-','b-']]

def governance_result(anchor,management,policy):
    if management not in GOV_LEVELS or policy not in GOV_LEVELS:return None,None
    level=GOV_MATRIX[GOV_LEVELS.index(policy)][GOV_LEVELS.index(management)]
    if anchor not in GOV_ANCHORS:return level,None
    return level,GOV_RATINGS[GOV_ANCHORS.index(anchor)][GOV_COLUMNS.index(level)]

def rubric_rows(evidence=None):
    ev=evidence or {};out=[]
    for group,items in RUBRIC.items():
        for key,label,rule in items:
            v=ev.get(key,{})
            valid=v.get('Assessment') in QUAL and all(str(v.get(k,'')).strip() for k in ['Reason','Source'])
            out.append({'Key':key,'Nhóm':group,'Chỉ tiêu':label,'Hướng dẫn':rule,
                        'Đánh giá':v.get('Assessment','Chưa thẩm định'),'Lập luận':v.get('Reason',''),
                        'Nguồn':v.get('Source',''),'Đủ bằng chứng':valid})
    return out
