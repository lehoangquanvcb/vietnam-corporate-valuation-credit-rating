import pandas as pd, numpy as np
from scripts.methodology_kpi_engine import methodology_kpi_table
from scripts.universal_data import get_company

PRIORITY={
'BANK':['CAR','NPL','LLR','NIM','CIR','CASA','LDR','ROE','ROA'],
'SECURITIES':['AvailableCapitalRatio','DebtEquity','DebtEBITDA','ROE','ROA','CurrentRatio','MarginLoansEquity','MarketShareBrokerage','ICGR'],
'CORPORATE':['DebtEBITDA','FFO_Debt','CFO_Debt','FOCF_Debt','InterestCoverage','ROE','ROA','CurrentRatio','NetMargin']
}
def methodology_readiness(ticker):
    typ=get_company(ticker).get('EntityType','CORPORATE')
    z=methodology_kpi_table(ticker,include_missing=True)
    req=PRIORITY.get(typ,[])
    q=z[z.Metric.isin(req)].drop_duplicates('Metric')
    have=q['Doanh nghiệp'].notna().sum()
    total=len(req); coverage=have/total if total else 0
    missing=[m for m in req if m not in set(q.loc[q['Doanh nghiệp'].notna(),'Metric'])]
    if coverage>=.80: status='TỐT'
    elif coverage>=.55: status='TRUNG BÌNH'
    else: status='THIẾU DỮ LIỆU'
    return {'EntityType':typ,'Coverage':coverage,'Have':int(have),'Required':int(total),'Missing':missing,'Status':status}
