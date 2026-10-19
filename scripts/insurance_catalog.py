"""Chỉ tiêu bảo hiểm và liên hệ với tài liệu Saigon Ratings ngày 20.01.2025."""
GROUPS = {
 '1. Quy mô và vị thế kinh doanh': ['GrossWrittenPremium','NetInsurancePremium','Revenue','TotalAssets','MarketSharePremium','LargestProductShare'],
 '2. Hiệu quả khai thác và sinh lợi': ['NPAT','ROE','ROA','NetMargin','LossRatio','ExpenseRatio','CombinedRatio','UnderwritingProfit','InvestmentIncome'],
 '3. Vốn và dự phòng': ['Equity','EquityAssets','PaidInCapital','PaidInCapitalRequired','InsuranceReserves','InsuranceReservesEquity','ReservesPremium'],
 '4. Vị thế rủi ro và linh hoạt tài chính': ['FXMismatchLiabilities','InvestmentLeverage','LargestSectorShare','DebtEquity','DebtDue24MEquity','InsuranceEBITDAInterest'],
 '5. Thanh khoản và khả năng thanh toán': ['StressedLiquidAssets','InsuranceContractObligations','InsuranceLiquidity','SolvencyRatio'],
 '6. Định giá tham khảo': ['PB','PE'],
}
LABELS = {
 'MarketSharePremium':'Thị phần phí bảo hiểm gốc', 'LargestProductShare':'Tỷ trọng dòng sản phẩm lớn nhất',
 'UnderwritingProfit':'Lợi nhuận hoạt động bảo hiểm', 'PaidInCapital':'Vốn thực góp và thặng dư',
 'PaidInCapitalRequired':'Vốn thực góp/Vốn pháp định', 'ReservesPremium':'Dự phòng nghiệp vụ/Phí bảo hiểm thuần',
 'FXMismatchLiabilities':'Lệch ngoại tệ chưa phòng vệ/Nợ phải trả',
 'InvestmentLeverage':'Tài sản đầu tư rủi ro/Tổng tài sản đầu tư',
 'LargestSectorShare':'Tỷ trọng ngành lớn nhất trong danh mục đầu tư',
 'DebtDue24MEquity':'Nợ đáo hạn 24 tháng/VCSH', 'InsuranceEBITDAInterest':'EBITDA/Lãi vay đã đối chiếu',
 'StressedLiquidAssets':'Tài sản thanh khoản sau khấu trừ',
 'InsuranceContractObligations':'Tổng nghĩa vụ hợp đồng bảo hiểm',
 'InsuranceLiquidity':'Tỷ số thanh khoản bảo hiểm',
 'SolvencyRatio':'Biên thanh toán/Biên thanh toán tối thiểu',
 'LossRatio':'Tỷ lệ bồi thường thuần', 'ExpenseRatio':'Tỷ lệ chi phí khai thác thuần', 'CombinedRatio':'Tỷ lệ kết hợp',
}
PCT={'MarketSharePremium','LargestProductShare','FXMismatchLiabilities','InvestmentLeverage','LargestSectorShare',
     'LossRatio','ExpenseRatio','CombinedRatio','SolvencyRatio'}
MULT={'PaidInCapitalRequired','ReservesPremium','DebtDue24MEquity','InsuranceEBITDAInterest','InsuranceLiquidity'}
NOTES = {
 'GrossWrittenPremium':'Vị thế thị trường: theo dõi tăng trưởng và thị phần thực. Tổng phí của nhóm cổ phiếu so sánh không đại diện toàn thị trường.',
 'MarketSharePremium':'Mục vị thế thị trường: thị phần bền vững từ 14% là một ví dụ hỗ trợ đánh giá tích cực; cần mẫu số toàn thị trường cùng kỳ.',
 'LargestProductShare':'Mục đa dạng hóa khác: một dòng sản phẩm vượt 80% tổng phí là dấu hiệu tiêu cực.',
 'ROE':'Bảng 04: ROE kỳ vọng >10% / 4–10% / <4%. Dữ liệu lịch sử không thay thế dự báo; yêu cầu so sánh ít nhất 60% số doanh nghiệp ngành.',
 'NetMargin':'Bảng 05: ROS kỳ vọng >12% cùng tỷ lệ kết hợp xấp xỉ ≤100% hỗ trợ tích cực; ROS <5% hoặc tỷ lệ kết hợp khoảng >105% là dấu hiệu tiêu cực.',
 'LossRatio':'Tính từ chi phí bồi thường thuần (kể cả biến động dự phòng bồi thường) / phí bảo hiểm thuần được hưởng. Giữ dấu hoàn nhập.',
 'ExpenseRatio':'Quy ước BCTC: chi phí khai thác thuần = tổng chi phí kinh doanh bảo hiểm − chi phí bồi thường + chi phí quản lý bảo hiểm − thu hoa hồng và thu khác. Không dùng tỷ số nhà cung cấp chưa rõ định nghĩa.',
 'CombinedRatio':'Tỷ lệ bồi thường + tỷ lệ chi phí theo cùng cơ sở thuần. Dưới 100% biểu thị thặng dư khai thác theo quy ước này. Cần chuyên viên đối chiếu định nghĩa trước khi dùng để chấm điểm.',
 'PaidInCapital':'Bảng 12: vốn thực góp gồm vốn điều lệ và thặng dư vốn cổ phần; không đồng nhất với toàn bộ VCSH.',
 'PaidInCapitalRequired':'Bảng 12: các mốc 1; 1,5; 2; 2,5; 3; 3,5; 4 lần. Phải xác nhận vốn pháp định theo giấy phép, hiện tại và dự báo hai năm tới. Không tự chọn mức vốn pháp định.',
 'ReservesPremium':'Hiệu quả kinh doanh có xét dự phòng/phí. Quy ước hiển thị dùng phí thuần TTM khi xem quý để tránh số dư/quý bị phóng đại; bảng lịch sử dùng đúng cơ sở đã ghi.',
 'FXMismatchLiabilities':'Rủi ro tỷ giá: lệch ngoại tệ trọng yếu, chưa phòng vệ >10% tổng nợ phải trả là dấu hiệu tiêu cực.',
 'InvestmentLeverage':'Đòn bẩy đầu tư: tài sản rủi ro cao sau phòng vệ / tổng đầu tư. <20% kéo dài hỗ trợ tích cực; >100% là dấu hiệu tiêu cực theo tài liệu. Cần giữ nhất quán mẫu số.',
 'LargestSectorShare':'Danh mục đa dạng: không ngành nào >15% hỗ trợ tích cực; 15–30% thường trung lập. Xem riêng trường hợp nợ Chính phủ khoảng 50%.',
 'DebtEquity':'Linh hoạt tài chính: chỉ tính nợ vay, không dùng toàn bộ nợ phải trả. >15% cần thẩm định thêm, không tự chấm tiêu cực.',
 'DebtDue24MEquity':'Nợ vay đáo hạn trong hai năm >20% VCSH là dấu hiệu cân nhắc giảm đánh giá; cần lịch trả nợ.',
 'InsuranceEBITDAInterest':'Phương pháp có xét EBITDA/lãi vay. Cần EBITDA đã đối chiếu và lãi vay cùng kỳ; lãi vay bằng 0 là không áp dụng, không tự gán trung lập.',
 'InsuranceLiquidity':'Tài sản thanh khoản sau khấu trừ / tổng nghĩa vụ hợp đồng bảo hiểm: >2,2 mạnh; 1–2,2 đầy đủ; <1 yếu. Đây là chỉ số, chưa phải toàn bộ đánh giá thanh khoản Bảng 18.',
 'StressedLiquidAssets':'Tiền mặt, TPCP khấu trừ 0%; tiền gửi <6 tháng khấu trừ 1%/5%/100% theo hạng; trái phiếu đủ điều kiện 10%/35%/100%; cổ phiếu niêm yết 50%; tài sản khác 100%.',
 'InsuranceContractObligations':'Cần tổng nghĩa vụ hợp đồng bảo hiểm theo hồ sơ thẩm định. Không thay bằng toàn bộ nợ phải trả, phải trả bảo hiểm hay chỉ dự phòng nghiệp vụ.',
 'SolvencyRatio':'Tỷ số biên khả năng thanh toán thực có/biên tối thiểu, theo công bố đúng kỳ; không đồng nhất vốn thực góp/vốn pháp định.',
 'PB':'Chỉ tiêu định giá tham khảo theo tỷ số nguồn tại kỳ báo cáo; không phải yếu tố tự động quyết định XHTN.',
 'PE':'Chỉ tiêu định giá tham khảo theo tỷ số nguồn tại kỳ báo cáo; cần xem chất lượng lợi nhuận và sự khác biệt mô hình.',
}
DEFAULT_NOTE='Phân tích quy mô, biến động và vị thế tương đối; không suy ra điểm tín nhiệm chỉ từ một chỉ tiêu hoặc một quý.'
MANUAL_INPUTS={
 'RequiredCapital','MarketSharePremium','LargestProductShare','FXMismatchLiabilities','InvestmentLeverage','LargestSectorShare',
 'DebtDue24M','InsuranceEBITDA','InsuranceInterestExpense','InsuranceContractObligations',
 'SolvencyMargin','MinimumSolvencyMargin','LiquidCash','DepositsIGUnder6M','DepositsOtherUnder6M',
 'GovernmentBondsLiquid','RatedBondsIGLiquid','RatedBondsOtherLiquid','ListedEquitiesLiquid',
 'LossRatio','ExpenseRatio','CombinedRatio','SolvencyRatio',
}
MANUAL_FLOWS={'InsuranceEBITDA','InsuranceInterestExpense'}
MANUAL_RATIOS={'MarketSharePremium','LargestProductShare','FXMismatchLiabilities','InvestmentLeverage','LargestSectorShare',
               'LossRatio','ExpenseRatio','CombinedRatio','SolvencyRatio'}
FLOW_RATIOS={'LossRatio','ExpenseRatio','CombinedRatio'}
DEFINITION='NET_EARNED_CLAIMS_OPS_ADMIN_OTHER_V1'
