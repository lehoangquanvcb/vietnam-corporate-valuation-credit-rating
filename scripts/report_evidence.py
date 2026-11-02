"""Bằng chứng và lập luận báo cáo; cùng nguồn chuẩn hóa với giao diện."""
import math
import numpy as np
import pandas as pd
from scripts.universal_data import get_company, peer_tickers
from scripts.financial_evidence import at_period, latest_period, same_period_history, comparable_model
from scripts.methodology_kpi_engine import LABELS, PCT, MULT, BANK_GROUPS, SEC_GROUPS, CORP_GROUPS
from scripts.financial_views import HISTORY_METRICS, BASIS_LABELS

ENGINE_VERSION = '8.131.0'
GROUPS = {'BANK': {
 'Hồ sơ kinh doanh':['TotalAssets','GrossLoans','CustomerDeposits'],
 'Vốn và lợi nhuận':['Equity','CAR','EquityAssets','TangibleEquityAssets','AssetEquity','NPAT','NetInterestIncome','ROE','ROA','NIM','CIR','ProfitAssets','NII_OperatingIncome'],
 'Vị thế rủi ro':['NPL','LoanLossCoverage','CreditCostProxy','ProvisionOperatingIncome','LoanAssets'],
 'Huy động vốn và thanh khoản':['CASA','LDR','DepositAssets','FundingGapAssets'],
 'Chỉ tiêu thị trường':['PB','PE']}, 'SECURITIES': SEC_GROUPS, 'CORPORATE': CORP_GROUPS}
from scripts.report_methodology import GROUPS
EXTRA_LABELS = {'TotalDebt':'Nợ vay', 'CFO':'Dòng tiền từ hoạt động kinh doanh',
    'Capex':'Chi đầu tư tài sản cố định', 'EBITDA':'Lợi nhuận trước lãi vay thuế và khấu hao',
    'CreditCost':'Chi phí tín dụng', 'Group2LoansRatio':'Tỷ lệ nợ nhóm 2',
    'LiquidityCoverageRatio':'Tỷ lệ bao phủ thanh khoản', 'StableFundingRatio':'Tỷ lệ nguồn vốn ổn định',
    'TangibleEquity':'Vốn chủ sở hữu hữu hình', 'IntangibleAssets':'Tài sản vô hình',
    'InterestExpense':'Chi phí lãi vay', 'OperatingProfit':'Lợi nhuận hoạt động',
    'Depreciation':'Khấu hao', 'GrossProfit':'Lợi nhuận gộp', 'Cash':'Tiền và tương đương tiền',
    'CurrentAssets':'Tài sản ngắn hạn', 'CurrentLiabilities':'Nợ ngắn hạn',
    'MinorityEquity':'Lợi ích cổ đông không kiểm soát'}
HIGHER = {'ROE','ROA','NIM','CAR','CASA','LoanLossCoverage','EquityAssets','TangibleEquityAssets',
    'GrossMargin','NetMargin','EBITDAMargin','OperatingProfitMargin','CFO_Margin','FOCFMargin',
    'CFO_Debt','FOCF_Debt','InterestCoverage','CashDebt','EquityAssetsCorp','AvailableCapitalRatio',
    'ProfitAssets','ICGR'}
LOWER = {'NPL','CIR','DebtEquity','DebtAssets','NetDebtEquity','DebtEBITDA','NetDebtEBITDA','AssetEquity'}

def label(metric): return LABELS.get(metric, EXTRA_LABELS.get(metric, metric))
def finite(v):
    try:return math.isfinite(float(v))
    except (TypeError, ValueError):return False
def vi(v, digits=2):
    rounded=round(float(v),digits)
    if rounded==0:rounded=0.0
    return f'{rounded:,.{digits}f}'.replace(',', '_').replace('.', ',').replace('_', '.')
def unit(m): return '%' if m in PCT else 'lần' if m in MULT else 'đồng/cp' if m in {'EPS','BVPS','Price','FairValue'} else 'tỷ đồng'
def scale(m): return 100 if m in PCT else 1 if m in MULT or m in {'EPS','BVPS','Price','FairValue'} else 1e-9
def fmt(m,v,with_unit=True):
    if not finite(v):return '—'
    n=vi(float(v)*scale(m), 2 if m in PCT or m in MULT else 0 if unit(m)=='đồng/cp' else 1)
    return n+(' '+unit(m) if with_unit else '')
def basis_text(v):
    return {'END_PERIOD':'Số dư cuối kỳ','REPORTED_RATIO':'Tỷ số nguồn công bố','QUARTER':'Quý riêng lẻ',
        'YTD':'Lũy kế đầu năm','FY':'Cả năm','TTM':'12 tháng gần nhất','DERIVED_QUARTER':'Tỷ số tính từ quý riêng lẻ',
        'DERIVED_YTD':'Tỷ số tính từ lũy kế','DERIVED_TTM':'Tỷ số tính từ 12 tháng','DERIVED_FY':'Tỷ số tính từ cả năm'}.get(v, v or 'Chưa có cơ sở tính')

def window_ends_at(record_period,target):
    """Dòng tiền lũy kế lưu đầy đủ các quý, không chỉ một nhãn quý cuối."""
    last=str(record_period or '').split('|')[-1]
    if len(last)==4 and last.isdigit():last+='-Q4'
    return last==target

def build_pack(ticker,basis='FY',years=5):
    ticker=str(ticker).upper(); meta=get_company(ticker);typ=meta['EntityType']
    if basis not in BASIS_LABELS:raise ValueError('Cơ sở lịch sử không hợp lệ: '+str(basis))
    if not latest_period(ticker,typ):
        return _empty_pack(ticker,meta,basis,years)
    if typ=='INSURANCE':
        return _insurance_pack(ticker,basis,years)
    years=max(3,min(int(years),5)); target=latest_period(ticker,typ)
    peers=list(dict.fromkeys(t for t in peer_tickers(ticker) if t!=ticker and comparable_model(meta,get_company(t))))
    sections=[];seen=set()
    for title,metrics in GROUPS[typ].items():
        unique=list(dict.fromkeys(m for m in metrics if m not in seen));seen.update(unique)
        if unique:sections.append((title.replace('&','và'),unique))
    extras=[m for m in HISTORY_METRICS[typ] if m not in seen]
    if extras:sections.insert(1,('Kết quả kinh doanh và các số dư bổ sung',extras))
    metrics=list(dict.fromkeys(m for _,ms in sections for m in ms))
    latest=at_period(ticker,typ,target,'QUARTER') if target else {}
    peer_now={t:at_period(t,typ,target,'QUARTER') for t in peers} if target else {}
    history=same_period_history(ticker,typ,basis,years,metrics=metrics)
    peer_history={p:{t:at_period(t,typ,p,basis) for t in peers} for p in history.get('Period',pd.Series(dtype=str)).unique()}
    items={}
    for m in metrics:
        own=latest.get(m,{}); current=own.get('Value') if own.get('Status')=='OK' and window_ends_at(own.get('Period'),target) else None
        rows=[];excluded=[]
        for t in peers:
            r=peer_now.get(t,{}).get(m,{})
            if r.get('Status')=='OK' and window_ends_at(r.get('Period'),target) and finite(r.get('Value')) and (not own.get('Basis') or not finite(current) or r.get('Basis')==own['Basis']):
                rows.append({'Ticker':t,'Value':r['Value'],'Basis':r['Basis']})
            else:excluded.append(t)
        # Không gộp các cơ sở khác nhau khi chính doanh nghiệp chưa có số.
        bases={r['Basis'] for r in rows}
        if len(bases)>1:
            preferred=own.get('Basis') or sorted(bases)[0]
            excluded += [r['Ticker'] for r in rows if r['Basis']!=preferred]
            rows=[r for r in rows if r['Basis']==preferred]
        h=history[history.Metric.eq(m)].copy() if len(history) else pd.DataFrame()
        means=[];counts=[]
        for row in h.itertuples():
            valid=[rr[m]['Value'] for rr in peer_history[row.Period].values() if m in rr and rr[m]['Status']=='OK' and window_ends_at(rr[m]['Period'],row.Period)
                and rr[m]['Basis']==row.Basis and finite(rr[m]['Value'])]
            counts.append(len(valid));means.append(float(np.mean(valid)) if len(valid)>=5 else np.nan)
        if len(h):
            h['Value']=pd.to_numeric(h.Value,errors='coerce').where(h.Status.eq('OK'))
            h['PeerMean']=means;h['PeerCount']=counts
        items[m]={'Metric':m,'Value':current,'Record':own,'Peers':rows,'Excluded':excluded,'PeerCount':len(rows),
            'PeerMean':float(np.mean([r['Value'] for r in rows])) if len(rows)>=5 else None,'History':h}
    return {'Ticker':ticker,'Meta':meta,'Type':typ,'Period':target,'Basis':basis,'Years':years,
            'PeerUniverse':peers,'Sections':sections,'Items':items}

def delta_text(m,a,b):
    if m in PCT:return vi((b-a)*100,2)+' điểm phần trăm'
    if m in MULT:return vi(b-a,2)+' lần'
    if a>0:return vi((b/a-1)*100,1)+'%'
    return fmt(m,b-a)+' (thay đổi tuyệt đối do kỳ gốc không dương)'

def narrative(pack,m):
    from scripts.financial_narrative import analyse
    from scripts.report_insights import enrich_narrative
    return enrich_narrative(pack,m,analyse(pack,m))

def cross_findings(pack):
    metrics={'BANK':['Equity','NPAT','NPL','CASA'],
             'SECURITIES':['Revenue','ROE','Loans','CashDebt'],
             'CORPORATE':['Revenue','NetMargin','CFO','DebtEBITDA'],
             'INSURANCE':['CombinedRatio','NPAT','Equity','InsuranceReserves']}[pack['Type']]
    result=[]
    for m in metrics:
        if m not in pack['Items']:continue
        x=pack['Items'][m]
        if not finite(x['Value']) and not x['History'].Value.notna().any():continue
        n=narrative(pack,m);text=' '.join(z for z in [n['Meaning'],n['Conclusion']] if z)
        if text and text not in result:result.append(text)
    return result


def _insurance_pack(ticker,basis,years):
    """Chuyển bằng chứng bảo hiểm sang giao diện chung, giữ phạm vi so sánh."""
    from scripts.insurance_analysis import analysis_pack,metric_pair
    from scripts.insurance_peers import peer_universe, included_rows
    from scripts.insurance_presentation import own_value
    pairs=analysis_pack(ticker,basis,years);items={}
    present={p['Metric'] for p in pairs}
    peers=peer_universe(ticker)
    for m in dict.fromkeys(m for ms in GROUPS['INSURANCE'].values() for m in ms):
        if m not in present:pairs.append(metric_pair(ticker,m,basis,years,peers))
    for pair in pairs:
        h=pair['History'].copy();ph=pair['PeerHistory']
        h['Value']=pd.to_numeric(h.Value,errors='coerce').where(h.Status.eq('OK'))
        h=h.merge(ph[['Period','PeerMean','PeerCount']],on='Period',how='left',validate='one_to_one')
        # Đồng nhất điều kiện bình quân với ba lĩnh vực còn lại.
        h['PeerMean']=h.PeerMean.where(h.PeerCount.ge(5))
        q=pair['Peers'];rows=included_rows(q.iloc[1:]) if len(q) else q
        own=q.iloc[0].to_dict() if len(q) else {}
        items[pair['Metric']]={'Metric':pair['Metric'],'Value':own_value(pair),'Record':own,
            'Peers':rows[['Ticker','Value','Basis']].to_dict('records') if len(rows) else [],
            'Excluded':q.iloc[1:][~q.iloc[1:].Ticker.isin(rows.Ticker)].Ticker.tolist() if len(q) else [],
            'PeerCount':len(rows),'PeerMean':pair['PeerMean'],'History':h,
            'HistoryBreaks':pair['HistoryBreaks'],'PeerHistoryBreaks':pair['PeerHistoryBreaks'],
            'HistoryWarnings':pair['HistoryWarnings'],'InsurancePair':pair}
    return {'Ticker':ticker,'Meta':get_company(ticker),'Type':'INSURANCE',
            'Period':latest_period(ticker,'INSURANCE'),'Basis':basis,'Years':years,
            'PeerUniverse':peer_universe(ticker),'Sections':list(GROUPS['INSURANCE'].items()),'Items':items}


def _empty_pack(ticker,meta,basis,years):
    """Mã chưa có BCTC vẫn xuất được hồ sơ; không tạo số hoặc kỳ giả."""
    sections=list(GROUPS[meta['EntityType']].items())
    columns=['Metric','Period','DisplayPeriod','Value','Status','Basis','PeerMean','PeerCount']
    items={m:{'Metric':m,'Value':None,'Record':{},'Peers':[],'Excluded':[],
              'PeerCount':0,'PeerMean':None,'History':pd.DataFrame(columns=columns)}
           for _,ms in sections for m in ms}
    return {'Ticker':ticker,'Meta':meta,'Type':meta['EntityType'],'Period':None,'Basis':basis,
            'Years':years,'PeerUniverse':[],'Sections':sections,'Items':items}


def findings(pack):
    strengths=[];risks=[]
    for m,x in pack['Items'].items():
        if m not in HIGHER|LOWER or not finite(x['Value']) or not finite(x['PeerMean']):continue
        if fmt(m,x['Value'])==fmt(m,x['PeerMean']):continue
        good=x['Value']>=x['PeerMean'] if m in HIGHER else x['Value']<=x['PeerMean']
        difference=abs(x['Value']-x['PeerMean'])/max(abs(x['PeerMean']),1e-12)
        negative=m in HIGHER and x['Value']<0
        text=f'{label(m)} {fmt(m,x["Value"])} so với bình quân peer {fmt(m,x["PeerMean"])}.'
        if negative:text+=' Giá trị còn âm nên chưa tạo điểm hỗ trợ tài chính.'
        (strengths if good and not negative else risks).append((difference,text))
    return ([t for _,t in sorted(strengths,reverse=True)[:3]], [t for _,t in sorted(risks,reverse=True)[:3]])
