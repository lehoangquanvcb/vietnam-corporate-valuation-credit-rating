"""Cấu trúc báo cáo theo bốn tài liệu phương pháp do người dùng cung cấp.

Định tuyến theo loại hình, không phụ thuộc một mã mẫu. Cấu trúc trình bày
không tự thay đổi đầu vào hay kết quả của các bộ máy chấm điểm.
"""
SOURCES = {
    'BANK': 'Phương pháp XHTN Ngân hàng 2026',
    'SECURITIES': 'Phương pháp XHTN Công ty Chứng khoán 2025',
    'CORPORATE': 'Phương pháp XHTN doanh nghiệp — 17/07/2025',
    'INSURANCE': 'Phương pháp XHTN Công ty Bảo hiểm Phi Nhân thọ 2025',
}
REPORT_TITLE = 'Báo cáo Xếp hạng tín nhiệm không chỉ định'
RESEARCH_NOTE = 'Tài liệu này chỉ phục vụ mục đích nghiên cứu'
from scripts.report_identity import NOTICE
LIMITATION_NOTE = NOTICE

GROUPS = {
 'BANK': {
  'Hồ sơ kinh doanh': ['TotalAssets','GrossLoans','CustomerDeposits'],
  'Vốn và lợi nhuận': ['Equity','CAR','EquityAssets','TangibleEquityAssets','AssetEquity','NPAT','NetInterestIncome','ROE','ROA','NIM','CIR','ProfitAssets','NII_OperatingIncome'],
  'Vị thế rủi ro': ['NPL','LoanLossCoverage','CreditCostProxy','ProvisionOperatingIncome','LoanAssets'],
  'Huy động vốn và thanh khoản': ['CASA','LDR','DepositAssets','FundingGapAssets'],
  'Chỉ tiêu thị trường tham khảo': ['PB','PE'],
 },
 'SECURITIES': {
  'Hồ sơ kinh doanh': ['Revenue','TotalAssets','MarketShareBrokerage','AssetTurnover'],
  'Vốn và lợi nhuận': ['Equity','AvailableCapitalRatio','EquityAssetsCorp','AssetEquity','NPAT','ROE','ROA','NetMargin','OperatingProfitMargin','ICGR'],
  'Vị thế rủi ro': ['Loans','MarginLoans','MarginLoansEquity'],
  'Nguồn vốn và thanh khoản': ['TotalDebt','DebtEquity','DebtAssets','NetDebtEquity','ClientDeposits','CurrentRatio','WorkingCapitalAssets','CashAssets','CashDebt','CFO','CFO_Debt','CFO_Margin','FOCFMargin','FOCF_Debt'],
  'Chỉ tiêu thị trường tham khảo': ['PB','PE'],
 },
 'CORPORATE': {
  'Rủi ro kinh doanh — Quy mô và hiệu quả hoạt động': ['Revenue','TotalAssets','AssetTurnover','GrossMargin','OperatingProfitMargin'],
  'Rủi ro kinh doanh — Khả năng sinh lợi': ['NPAT','EBITDA','EBITDAMargin','NetMargin','ROE','ROA'],
  'Rủi ro tài chính — Dòng tiền và đòn bẩy': ['Equity','TotalDebt','DebtEquity','DebtAssets','NetDebtEquity','DebtEBITDA','NetDebtEBITDA','InterestCoverage','CFO','CFO_Margin','CFO_Debt','Capex','CapexRevenue','FOCFMargin','FOCF_Debt','EquityAssetsCorp','AssetEquity'],
  'Các yếu tố điều chỉnh — Thanh khoản': ['CurrentRatio','WorkingCapitalAssets','CashAssets','CashDebt'],
  'Chỉ tiêu thị trường tham khảo': ['PB','PE','EV_EBITDA'],
 },
 'INSURANCE': {
  'Rủi ro kinh doanh — Vị thế và hiệu quả khai thác': ['GrossWrittenPremium','NetInsurancePremium','Revenue','TotalAssets','MarketSharePremium','LargestProductShare','LossRatio','ExpenseRatio','CombinedRatio','UnderwritingProfit'],
  'Rủi ro tài chính — Nguồn vốn và lợi nhuận': ['Equity','EquityAssets','PaidInCapital','PaidInCapitalRequired','SolvencyRatio','NPAT','ROE','ROA','NetMargin','InvestmentIncome'],
  'Rủi ro tài chính — Vị thế rủi ro': ['InsuranceReserves','InsuranceReservesEquity','ReservesPremium','FXMismatchLiabilities','InvestmentLeverage','LargestSectorShare'],
  'Rủi ro tài chính — Linh hoạt tài chính': ['DebtEquity','DebtDue24MEquity','InsuranceEBITDAInterest'],
  'Rủi ro tài chính — Thanh khoản': ['Cash','CashAssets','CFO','StressedLiquidAssets','InsuranceContractObligations','InsuranceLiquidity'],
  'Chỉ tiêu thị trường tham khảo': ['PB','PE'],
 },
}


def chapter_findings(pack, heading):
    """Luận điểm tài chính theo cấu phần; chỉ lấy kết luận có số doanh nghiệp."""
    from scripts.report_evidence import narrative, finite
    if pack['Type'] == 'BANK':
        from scripts.bank_report_chapters import CHAPTERS, chapter_findings as bank
        key = next((k for title,k,_ in CHAPTERS if title == heading.upper()), '')
        return bank(pack, key) if key else []
    result = []
    for m in GROUPS[pack['Type']].get(heading, []):
        x = pack['Items'][m]
        if not finite(x['Value']) and not x['History'].Value.notna().any():
            continue
        n = narrative(pack, m)
        text = n['Meaning'] or n['Conclusion']
        if text and text not in result:
            result.append(text)
        if len(result) == 2:
            break
    return result


def sensitivity_findings(pack):
    """Điều kiện thay đổi hồ sơ tài chính, gắn với nền số liệu doanh nghiệp."""
    from scripts.report_evidence import finite,fmt
    items=pack['Items']
    def metric(m):
        v=items.get(m,{}).get('Value')
        return fmt(m,v) if finite(v) else None
    if pack['Type']=='SECURITIES':
        debt,margin=metric('DebtEquity'),metric('NetMargin')
        return [
            'Áp lực suy giảm có thể gia tăng nếu khoản cho vay và tài sản đầu tư tiếp tục tăng nhanh hơn vốn, trong khi thị trường giảm làm thu hẹp doanh thu và phát sinh tổn thất. '+
            (f'Nợ vay/vốn hiện {debt}; tăng đòn bẩy từ nền này mà không tạo thêm tiền sẽ làm nhu cầu tái cấp vốn lớn hơn.' if debt else ''),
            (f'Biên lợi nhuận quý gần nhất {margin}. ' if margin else '')+
            'Khả năng cải thiện phụ thuộc việc duy trì hiệu quả qua cả giai đoạn thị trường suy giảm, tăng vốn theo quy mô rủi ro và chuyển lợi nhuận thành nguồn tiền. Đánh giá vốn còn cần tỷ lệ vốn khả dụng và cơ cấu danh mục đã đối chiếu.',
        ]
    leverage,cover,margin=metric('DebtEBITDA'),metric('InterestCoverage'),metric('NetMargin')
    return [
        (f'Nợ/EBITDA hiện {leverage}. ' if leverage else '')+
        'Áp lực hạ đánh giá tài chính sẽ tăng nếu nợ vay mở rộng nhanh hơn EBITDA, dòng tiền kinh doanh suy giảm hoặc đầu tư vượt nguồn tiền nội bộ trong nhiều kỳ. '+
        (f'Khả năng trả lãi đang ở {cover}; biên thu nhập giảm sẽ thu hẹp mức bao phủ này nếu nghĩa vụ lãi không giảm.' if cover else ''),
        (f'Từ nền biên lợi nhuận quý gần nhất {margin}, ' if margin else '')+
        'khả năng cải thiện phụ thuộc tăng trưởng đi cùng duy trì biên, thu tiền từ hoạt động kinh doanh và giảm nhu cầu vay để tài trợ đầu tư. Nợ đến hạn cần có nguồn trả tương ứng để kết quả sinh lời chuyển thành sức mạnh thanh khoản.',
    ]
