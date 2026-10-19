"""Bảng/biểu đồ dùng cùng kỳ và định nghĩa cho Streamlit và Word."""
import numpy as np
import pandas as pd
from scripts.financial_evidence import same_period_history, at_period, metric_evidence, STATUS
from scripts.universal_data import get_company, get_snapshot, peer_snapshot, peer_tickers
from scripts.methodology_kpi_engine import LABELS, PCT, MULT

BASIS_LABELS={'YTD':'Lũy kế cùng kỳ','QUARTER':'Quý riêng lẻ cùng kỳ','FY':'Cả năm','TTM':'12 tháng kết thúc cùng kỳ'}
HISTORY_METRICS={
 'BANK':['TotalAssets','GrossLoans','CustomerDeposits','Equity','NPAT','NetInterestIncome','ROE','ROA','NIM','NPL','LoanLossCoverage','CAR','CASA','LDR'],
 'CORPORATE':['Revenue','NPAT','TotalAssets','Equity','TotalDebt','EBITDA','CFO','Capex','ROE','ROA','GrossMargin','DebtEquity','DebtEBITDA','CurrentRatio'],
 'SECURITIES':['Revenue','NPAT','TotalAssets','Equity','TotalDebt','Loans','ClientDeposits','ROE','ROA','DebtEquity','CurrentRatio','CashAssets'],
 'INSURANCE':['TotalAssets','Equity','InsuranceReserves','GrossWrittenPremium','NetInsurancePremium','Revenue','NPAT','InvestmentIncome','ROE','ROA','PB','PE']}

def fmt(metric,value,status='MISSING',compact=False):
    try:v=float(value)
    except (TypeError,ValueError):return STATUS.get(status,'Thiếu dữ liệu')
    if not np.isfinite(v):return STATUS.get(status,'Thiếu dữ liệu')
    if metric in PCT:return f'{v*100:,.2f}%'
    if metric in MULT:return f'{v:,.2f}x'
    if metric in {'EPS','BVPS','Price','FairValue'}:return f'{v:,.0f}'
    return f'{v/1e9:,.1f}' if compact else f'{v/1e9:,.1f} tỷ đồng'

def history_data(ticker,basis='YTD',years=5,metrics=None):
    typ=get_company(ticker)['EntityType']
    return same_period_history(ticker,typ,basis,years,metrics=metrics or HISTORY_METRICS[typ])

def history_table(ticker,basis='YTD',years=5,metrics=None):
    h=history_data(ticker,basis,years,metrics)
    if h.empty:return pd.DataFrame()
    rows=[]
    for m in h.Metric.drop_duplicates():
        q=h[h.Metric.eq(m)];r={'Chỉ tiêu':LABELS.get(m,m),'Đơn vị':'%' if m in PCT else 'lần' if m in MULT else 'tỷ đồng'}
        r.update({v.DisplayPeriod:fmt(m,v.Value,v.Status,True) for v in q.itertuples()});rows.append(r)
    return pd.DataFrame(rows)

def history_comparison(ticker,metric,basis='YTD',years=5):
    h=history_data(ticker,basis,years,[metric])
    if h.empty:return h
    typ=get_company(ticker)['EntityType']
    from scripts.financial_evidence import comparable_model
    target_meta=get_company(ticker)
    peers=[t for t in peer_tickers(ticker) if t!=ticker and comparable_model(target_meta,get_company(t))]
    h=h.copy(); means=[];counts=[]
    for row in h.itertuples():
        vals=[]
        for t in peers:
            r=at_period(t,typ,row.Period,basis).get(metric)
            if r and r['Status']=='OK' and r['Basis']==row.Basis and r['Value'] is not None:vals.append(r['Value'])
        counts.append(len(vals));means.append(float(np.mean(vals)) if len(vals)>=5 else np.nan)
    h['PeerMean']=means;h['PeerCount']=counts
    return h

def peer_metric_frame(ticker,metric):
    s=get_snapshot(ticker);target=metric_evidence(s,metric);rows=[]
    for row in [s]+peer_snapshot(ticker).to_dict('records'):
        e=metric_evidence(row,metric)
        if e['Status']=='OK' and e['Period']==target['Period'] and e['Basis']==target['Basis']:
            rows.append({'Ticker':row['Ticker'],'Value':e['Value'],'Period':e['Period'],'Basis':e['Basis']})
    return pd.DataFrame(rows,columns=['Ticker','Value','Period','Basis'])

HISTORY_NOTE=('Tiền tệ: tỷ đồng. Số dư lấy cuối kỳ; tỷ số nguồn giữ nguyên tại kỳ báo cáo, không cộng. '
 'ROE/ROA/NIM là tỷ số do nguồn công bố, không tự suy ra tỷ số lũy kế. Nợ/EBITDA và tỷ số trả nợ dùng TTM. '
 'Lũy kế/cả năm/TTM chỉ cộng dòng tiền sau khi đã tách quý và đủ các quý liên tiếp. Ô thiếu được giữ trống trên biểu đồ. '
 'Peer loại chính doanh nghiệp; chỉ tính bình quân khi có ít nhất 5 peer cùng kỳ và cơ sở.')
