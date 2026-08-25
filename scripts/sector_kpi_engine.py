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


def canonical_kpi_view(df):
    """Normalize old/new KPI schemas so Streamlit/report code never hard-fails on column drift."""
    if df is None:
        df=pd.DataFrame()
    z=df.copy()
    aliases={
        'Nhóm phân tích':['Nhóm phân tích','Nhóm','Pillar','Trụ cột'],
        'Chỉ tiêu':['Chỉ tiêu','MetricLabel','Tên chỉ tiêu'],
        'Doanh nghiệp':['Doanh nghiệp','Company','Giá trị DN'],
        'Trung bình ngành':['Trung bình ngành','TB ngành','IndustryMean'],
        'Trung vị ngành':['Trung vị ngành','Trung vị','IndustryMedian'],
        'Số DN có dữ liệu':['Số DN có dữ liệu','Số DN','Số doanh nghiệp trong mẫu ngành có dữ liệu','PeerCount'],
        'Chênh lệch với TB ngành':['Chênh lệch với TB ngành','Chênh lệch','GapVsMean'],
        'Trạng thái dữ liệu':['Trạng thái dữ liệu','DataStatus']
    }
    for target,candidates in aliases.items():
        if target not in z.columns:
            src=next((c for c in candidates if c in z.columns),None)
            z[target]=z[src] if src else ('' if target in ['Nhóm phân tích','Chỉ tiêu','Trạng thái dữ liệu'] else np.nan)
    if 'Metric' not in z.columns:
        z['Metric']=z['Chỉ tiêu']
    return z

def safe_kpi_columns(df, requested=None):
    z=canonical_kpi_view(df)
    requested=requested or ['Nhóm phân tích','Chỉ tiêu','Doanh nghiệp','Trung bình ngành','Trung vị ngành','Số DN có dữ liệu']
    return z[[c for c in requested if c in z.columns]]
