import numpy as np, pandas as pd
from scripts.universal_data import get_company,get_snapshot
from scripts.sector_benchmark_engine import industry_snapshot

LABELS={
'Price':'Giá thị trường','TotalAssets':'Tổng tài sản','GrossLoans':'Cho vay khách hàng',
'CustomerDeposits':'Tiền gửi khách hàng','Equity':'Vốn chủ sở hữu','NPAT':'Lợi nhuận sau thuế',
'ROE':'ROE/ROAE','ROA':'ROA/ROAA','NIM':'Biên lãi thuần (NIM)','NPL':'Tỷ lệ nợ xấu (NPL)',
'CAR':'Hệ số an toàn vốn (CAR)','CIR':'Tỷ lệ chi phí/thu nhập (CIR)','LDR':'Cho vay/Tiền gửi (LDR)',
'CASA':'Tiền gửi không kỳ hạn (CASA)','LoanAssets':'Cho vay/Tổng tài sản',
'DepositAssets':'Tiền gửi KH/Tổng tài sản','EquityAssets':'VCSH/Tổng tài sản',
'TangibleEquityAssets':'VCSH hữu hình/Tổng tài sản','NII_OperatingIncome':'Thu nhập lãi thuần/Tổng thu nhập HĐ',
'ProvisionOperatingIncome':'Chi phí dự phòng/Tổng thu nhập HĐ','PB':'P/B','PE':'P/E',
'Revenue':'Doanh thu','GrossMargin':'Biên lợi nhuận gộp','NetMargin':'Biên lợi nhuận ròng',
'EBITDAMargin':'Biên EBITDA','DebtEquity':'Nợ/VCSH','DebtAssets':'Nợ/Tổng tài sản',
'DebtEBITDA':'Nợ vay/EBITDA','CFO_Debt':'CFO/Nợ vay','FOCF_Debt':'FOCF/Nợ vay',
'CFO_Margin':'CFO/Doanh thu','CapexRevenue':'CAPEX/Doanh thu','CurrentRatio':'Hệ số thanh toán hiện hành',
'AvailableCapitalRatio':'Tỷ lệ an toàn vốn khả dụng','MarketShareBrokerage':'Thị phần môi giới',
'ClientAssets':'Tài sản/tiền gửi của khách hàng','MarginLoans':'Dư nợ cho vay ký quỹ',
'MarginLoansEquity':'Cho vay ký quỹ/VCSH','ICGR':'Tỷ lệ tạo vốn nội bộ (ICGR)',
'OperatingProfitMargin':'Biên lợi nhuận hoạt động','EV_EBITDA':'EV/EBITDA',
'AssetEquity':'Tổng tài sản/VCSH','CreditCostProxy':'Chi phí dự phòng/Dư nợ','FundingGapAssets':'Chênh lệch cho vay-tiền gửi/TTS',
'ProfitAssets':'LNST/Tổng tài sản','CashAssets':'Tiền/Tổng tài sản','WorkingCapitalAssets':'Vốn lưu động ròng/Tổng tài sản',
'NetDebtEquity':'Nợ ròng/VCSH','NetDebtEBITDA':'Nợ ròng/EBITDA','EquityAssetsCorp':'VCSH/Tổng tài sản','AssetTurnover':'Doanh thu/Tổng tài sản',
'FOCFMargin':'FOCF/Doanh thu','CashDebt':'Tiền/Nợ vay'
}
PCT=set(['ROE','ROA','NIM','NPL','CAR','CIR','CASA','LoanAssets','DepositAssets','EquityAssets',
'TangibleEquityAssets','NII_OperatingIncome','ProvisionOperatingIncome','GrossMargin','NetMargin',
'EBITDAMargin','DebtAssets','CFO_Debt','FOCF_Debt','CFO_Margin','CapexRevenue','AvailableCapitalRatio',
'MarketShareBrokerage','MarginLoansEquity','ICGR','OperatingProfitMargin','CreditCostProxy','FundingGapAssets','ProfitAssets','CashAssets','WorkingCapitalAssets','EquityAssetsCorp','FOCFMargin','CashDebt'])
MULT=set(['LDR','PB','PE','DebtEquity','DebtEBITDA','CurrentRatio','EV_EBITDA','AssetEquity','NetDebtEquity','NetDebtEBITDA','AssetTurnover'])

BANK_GROUPS={
'Hồ sơ kinh doanh & quy mô':['TotalAssets','GrossLoans','CustomerDeposits','LoanAssets','DepositAssets','AssetEquity'],
'Vốn & khả năng hấp thụ lỗ':['CAR','EquityAssets','TangibleEquityAssets','AssetEquity','ROE','ProfitAssets'],
'Khả năng sinh lợi & hiệu quả':['ROE','ROA','NIM','CIR','NII_OperatingIncome','ProfitAssets'],
'Chất lượng tài sản & chi phí rủi ro':['NPL','CreditCostProxy','ProvisionOperatingIncome','LoanAssets'],
'Nguồn vốn & thanh khoản':['CASA','LDR','DepositAssets','FundingGapAssets'],
'Định giá cổ phiếu':['PB','PE']
}
SEC_GROUPS={
'Hồ sơ kinh doanh & franchise':['Revenue','TotalAssets','Equity','MarketShareBrokerage','ClientAssets','MarginLoans','AssetTurnover'],
'Vốn & đòn bẩy':['AvailableCapitalRatio','DebtEquity','DebtAssets','EquityAssetsCorp','AssetEquity','NetDebtEquity'],
'Khả năng sinh lợi & hiệu quả':['ROE','ROA','NetMargin','OperatingProfitMargin','ICGR','AssetTurnover'],
'Vị thế rủi ro':['MarginLoansEquity','MarketShareBrokerage','DebtEquity','NetDebtEBITDA'],
'Nguồn vốn & thanh khoản':['CurrentRatio','WorkingCapitalAssets','CashAssets','CashDebt','CFO_Debt'],
'Dòng tiền':['CFO_Margin','FOCFMargin','CFO_Debt','FOCF_Debt'],
'Định giá':['PB','PE','EV_EBITDA']
}
CORP_GROUPS={
'Quy mô & hồ sơ kinh doanh':['Revenue','TotalAssets','AssetTurnover','GrossMargin','OperatingProfitMargin','EBITDAMargin'],
'Khả năng sinh lợi':['ROE','ROA','NetMargin','EBITDAMargin','AssetTurnover'],
'Đòn bẩy & khả năng trả nợ':['DebtEquity','DebtAssets','NetDebtEquity','DebtEBITDA','NetDebtEBITDA','CFO_Debt','FOCF_Debt'],
'Dòng tiền & đầu tư':['CFO_Margin','FOCFMargin','CapexRevenue','CFO_Debt','FOCF_Debt'],
'Thanh khoản':['CurrentRatio','WorkingCapitalAssets','CashAssets','CashDebt'],
'Cấu trúc vốn':['EquityAssetsCorp','AssetEquity','NetDebtEquity'],
'Định giá':['PB','PE','EV_EBITDA']
}

def _n(x):
    try:
        v=float(x);return v if np.isfinite(v) else np.nan
    except:return np.nan
def _div(a,b):
    a,b=_n(a),_n(b)
    return a/b if np.isfinite(a) and np.isfinite(b) and b!=0 else np.nan

def enrich_row(r):
    d=dict(r)
    d['LoanAssets']=_div(d.get('GrossLoans'),d.get('TotalAssets'))
    d['DepositAssets']=_div(d.get('CustomerDeposits'),d.get('TotalAssets'))
    d['EquityAssets']=_div(d.get('Equity'),d.get('TotalAssets'))
    d['TangibleEquityAssets']=_div(d.get('TangibleEquity'),d.get('TotalAssets'))
    d['NII_OperatingIncome']=_div(d.get('NetInterestIncome'),d.get('OperatingIncome'))
    d['ProvisionOperatingIncome']=_div(d.get('ProvisionExpense'),d.get('OperatingIncome'))
    d['DebtAssets']=_div(d.get('TotalDebt'),d.get('TotalAssets'))
    d['EBITDAMargin']=_div(d.get('EBITDA'),d.get('Revenue'))
    d['OperatingProfitMargin']=_div(d.get('OperatingProfit'),d.get('Revenue'))
    d['CFO_Margin']=_div(d.get('CFO'),d.get('Revenue'))
    d['CapexRevenue']=_div(abs(_n(d.get('Capex'))),d.get('Revenue'))
    focf=_n(d.get('CFO'))-abs(_n(d.get('Capex'))) if np.isfinite(_n(d.get('CFO'))) and np.isfinite(_n(d.get('Capex'))) else np.nan
    d['FOCF_Debt']=_div(focf,d.get('TotalDebt'))
    d['MarginLoansEquity']=_div(d.get('MarginLoans'),d.get('Equity'))
    d['AssetEquity']=_div(d.get('TotalAssets'),d.get('Equity'))
    d['CreditCostProxy']=_div(abs(_n(d.get('ProvisionExpense'))),d.get('GrossLoans'))
    if np.isfinite(_n(d.get('GrossLoans'))) and np.isfinite(_n(d.get('CustomerDeposits'))) and np.isfinite(_n(d.get('TotalAssets'))) and _n(d.get('TotalAssets'))!=0:
        d['FundingGapAssets']=(_n(d.get('GrossLoans'))-_n(d.get('CustomerDeposits')))/_n(d.get('TotalAssets'))
    else:d['FundingGapAssets']=np.nan
    d['ProfitAssets']=_div(d.get('NPAT'),d.get('TotalAssets'))
    d['CashAssets']=_div(d.get('Cash'),d.get('TotalAssets'))
    if np.isfinite(_n(d.get('CurrentAssets'))) and np.isfinite(_n(d.get('CurrentLiabilities'))) and np.isfinite(_n(d.get('TotalAssets'))) and _n(d.get('TotalAssets'))!=0:
        d['WorkingCapitalAssets']=(_n(d.get('CurrentAssets'))-_n(d.get('CurrentLiabilities')))/_n(d.get('TotalAssets'))
    else:d['WorkingCapitalAssets']=np.nan
    netdebt=_n(d.get('TotalDebt'))-_n(d.get('Cash')) if np.isfinite(_n(d.get('TotalDebt'))) and np.isfinite(_n(d.get('Cash'))) else np.nan
    d['NetDebtEquity']=_div(netdebt,d.get('Equity'))
    d['NetDebtEBITDA']=_div(netdebt,d.get('EBITDA'))
    d['EquityAssetsCorp']=_div(d.get('Equity'),d.get('TotalAssets'))
    d['AssetTurnover']=_div(d.get('Revenue'),d.get('TotalAssets'))
    d['FOCFMargin']=_div(focf,d.get('Revenue'))
    d['CashDebt']=_div(d.get('Cash'),d.get('TotalDebt'))
    return d

def enriched_industry(ticker):
    x=industry_snapshot(ticker)
    if x.empty:return x
    return pd.DataFrame([enrich_row(r) for r in x.to_dict('records')])

def groups_for(ticker):
    et=get_company(ticker).get('EntityType')
    return BANK_GROUPS if et=='BANK' else SEC_GROUPS if et=='SECURITIES' else CORP_GROUPS

def methodology_kpi_table(ticker, include_missing=True):
    s=enrich_row(get_snapshot(ticker)); peers=enriched_industry(ticker); rows=[]
    for group,metrics in groups_for(ticker).items():
        for m in metrics:
            c=_n(s.get(m))
            vals=pd.to_numeric(peers[m],errors='coerce').dropna() if len(peers) and m in peers else pd.Series(dtype=float)
            mean=float(vals.mean()) if len(vals) else np.nan; med=float(vals.median()) if len(vals) else np.nan
            if not include_missing and not np.isfinite(c) and not len(vals):continue
            rows.append({'Nhóm phân tích':group,'Metric':m,'Chỉ tiêu':LABELS.get(m,m),
                         'Doanh nghiệp':c,'TB ngành':mean,'Trung vị':med,'Số DN':int(len(vals)),
                         'Trạng thái dữ liệu':'Có dữ liệu' if np.isfinite(c) else 'N/A – cần bổ sung nguồn'})
    return pd.DataFrame(rows)

def metric_list(ticker, available_only=True):
    t=methodology_kpi_table(ticker,include_missing=True)
    if available_only:t=t[t['Doanh nghiệp'].notna() | t['TB ngành'].notna()]
    return t.Metric.drop_duplicates().tolist()
