from pathlib import Path
import pandas as pd, numpy as np
from scripts.universal_data import get_company,get_snapshot,num
from scripts.sector_benchmark_engine import industry_snapshot
from scripts.sector_templates import get_template

VI={'Revenue':'Doanh thu','NPAT':'LNST','ROE':'ROE','ROA':'ROA','DebtEquity':'Nợ/VCSH','CurrentRatio':'Thanh toán hiện hành','PE':'P/E','PB':'P/B','TotalAssets':'Tổng tài sản','NIM':'NIM','NPL':'Nợ xấu','CAR':'CAR','CASA':'CASA','LDR':'LDR','AvailableCapitalRatio':'Tỷ lệ vốn khả dụng'}

def sector_kpi_table(ticker):
    m=get_company(ticker); s=get_snapshot(ticker); peers=industry_snapshot(ticker)
    key,t=get_template(m.get('EntityType'),m.get('Sector'))
    rows=[]
    for metric in t['metrics']:
        company=num(s.get(metric))
        vals=pd.to_numeric(peers[metric],errors='coerce').dropna() if len(peers) and metric in peers.columns else pd.Series(dtype=float)
        mean=float(vals.mean()) if len(vals) else None; median=float(vals.median()) if len(vals) else None
        rel=None
        if company is not None and mean not in (None,0): rel=company/mean-1
        rows.append({'Metric':metric,'Chỉ tiêu':VI.get(metric,metric),'Doanh nghiệp':company,'Trung bình ngành':mean,'Trung vị ngành':median,'Số DN có dữ liệu':len(vals),'Chênh lệch với TB ngành':rel})
    return pd.DataFrame(rows),key,t
