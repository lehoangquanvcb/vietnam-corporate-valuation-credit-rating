import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
import pandas as pd, numpy as np
from scripts.universal_data import get_company,get_snapshot,num
from scripts.sector_benchmark_engine import industry_snapshot
from scripts.sector_templates import get_template
from scripts.methodology_kpi_engine import methodology_kpi_table

VI={'Revenue':'Doanh thu','NPAT':'LNST','ROE':'ROE','ROA':'ROA','DebtEquity':'Nợ/VCSH','CurrentRatio':'Thanh toán hiện hành','PE':'P/E','PB':'P/B','TotalAssets':'Tổng tài sản','NIM':'NIM','NPL':'Nợ xấu','CAR':'CAR','CASA':'CASA','LDR':'LDR','AvailableCapitalRatio':'Tỷ lệ vốn khả dụng'}

def sector_kpi_table(ticker):
    m=get_company(ticker)
    key,t=get_template(m.get('EntityType'),m.get('Sector'))
    z=methodology_kpi_table(ticker,include_missing=True).copy()
    z=z.rename(columns={'TB ngành':'Trung bình ngành','Trung vị':'Trung vị ngành','Số DN':'Số DN có dữ liệu'})
    z['Chênh lệch với TB ngành']=np.where(
        pd.to_numeric(z['Doanh nghiệp'],errors='coerce').notna() &
        pd.to_numeric(z['Trung bình ngành'],errors='coerce').notna() &
        pd.to_numeric(z['Trung bình ngành'],errors='coerce').ne(0),
        pd.to_numeric(z['Doanh nghiệp'],errors='coerce')/pd.to_numeric(z['Trung bình ngành'],errors='coerce')-1,
        np.nan)
    return z,key,t
