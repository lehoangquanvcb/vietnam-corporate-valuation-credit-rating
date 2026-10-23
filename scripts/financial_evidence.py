"""Dữ liệu tài chính dùng chung: mã dòng chính xác, kỳ rõ ràng, không điền số giả.

CSV raw V8.74.1 dùng các quý riêng lẻ. Nguồn lũy kế phải có cột basis=YTD
hoặc cấu hình config/raw_period_basis.csv (Ticker,Dataset,Basis).
Không cộng số dư cuối kỳ hoặc tỷ số; không đọc các cột order/level thành tiền.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STATUS = {'OK': 'Có dữ liệu', 'MISSING': 'Thiếu dữ liệu',
          'NOT_APPLICABLE': 'Không áp dụng', 'ERROR': 'Lỗi dữ liệu/tính toán',
          'UNREVIEWED': 'Chưa thẩm định'}
SCOPE_NOTE = ('Ma trận XHTN được cung cấp tham chiếu phương pháp bảo hiểm phi nhân thọ 2025. '
              'Nhóm INSURANCE bao gồm các mô hình khác nhau; cần xác nhận phạm vi trước khi chấm điểm. '
              'Nợ vay/VCSH và EBITDA/lãi vay được xem xét riêng trong linh hoạt tài chính. Không dùng nợ/EBITDA hoặc thanh khoản hiện hành thay tỷ số bảo hiểm.')
# metric -> dataset, exact semantic identifiers
MAP = {
 'TotalAssets': ('balance', ['BS_TOTAL_ASSETS']),
 'Equity': ('balance', ['BS_EQUITY','BS_OWNERS_EQUITY','BS_TOTAL_EQUITY']),
 'MinorityEquity': ('balance', ['BS_MINORITY_INTEREST']),
 'Cash': ('balance', ['BS_CASH_AND_PRECIOUS_METALS','BS_CASH_AND_CASH_EQUIVALENTS']),
 'CurrentAssets': ('balance', ['BS_SHORT_TERM_ASSETS']),
 'CurrentLiabilities': ('balance', ['BS_SHORT_TERM_LIABILITIES']),
 'TotalLiabilities': ('balance', ['BS_TOTAL_LIABILITIES']),
 'ShortTermBorrowings': ('balance', ['BS_SHORT_TERM_BORROWINGS']),
 'LongTermBorrowings': ('balance', ['BS_LONG_TERM_BORROWINGS']),
 'GrossLoans': ('balance', ['BS_LOANS_TO_CUSTOMERS']),
 'CustomerDeposits': ('balance', ['BS_CUSTOMER_DEPOSITS','BS_DEPOSITS_FROM_CUSTOMERS']),
 'IntangibleAssets': ('balance', ['BS_INTANGIBLE_FIXED_ASSETS']),
 'MarginLoans': ('balance', ['BS_MARGIN_LOANS','BS_MARGIN_LENDING','BS_RECEIVABLES_FROM_MARGIN_LENDING','BS_LOANS_FOR_MARGIN_TRADING','BS_MARGIN_TRADING_LOANS']),
 'Loans': ('balance', ['BS_LOANS']),
 'ClientDeposits': ('balance', ['BS_OFF_CUSTOMER_DEPOSITS']),
 'InsuranceReserves': ('balance', ['BS_INSURANCE_RESERVES']),
 'Revenue': ('income', ['IS_NET_REVENUE','IS_TOTAL_NET_REVENUE_FROM_INSURANCE_BUSINESS','IS_TOTAL_OPERATING_INCOME']),
 'GrossProfit': ('income', ['IS_GROSS_PROFIT']),
 'OperatingProfit': ('income', ['IS_OPERATING_PROFIT','IS_OPERATING_RESULT']),
 'NPAT': ('income', ['IS_NET_PROFIT_AFTER_TAX']),
 'ParentNPAT': ('income', ['IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY']),
 'PBT': ('income', ['IS_PROFIT_BEFORE_TAX']),
 'InterestExpense': ('income', ['IS_INTEREST_EXPENSES']),
 'NetInterestIncome': ('income', ['IS_NET_INTEREST_INCOME']),
 'OperatingIncome': ('income', ['IS_TOTAL_OPERATING_INCOME']),
 'ProvisionExpense': ('income', ['IS_PROVISION_EXPENSES','IS_PROVISION_FOR_CREDIT_LOSSES','IS_CREDIT_LOSS_PROVISION_EXPENSES']),
 'GrossWrittenPremium': ('income', ['IS_GROSS_WRITTEN_PREMIUM']),
 'NetInsurancePremium': ('income', ['IS_NET_INSURANCE_PREMIUM']),
 'RetainedClaims': ('income', ['IS_RETAINED_CLAIMS']),
 'InvestmentIncome': ('income', ['IS_FINANCIAL_INCOME']),
 'CFO': ('cashflow', ['CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES']),
 'Capex': ('cashflow', ['CF_PAYMENTS_FOR_FIXED_ASSETS']),
 'Depreciation': ('cashflow', ['CF_DEPRECIATION_AND_AMORTISATION','CF_DEPRECIATION_AMORTIZATION']),
 'ROE': ('ratio', ['RT_PRT_ROE']), 'ROA': ('ratio', ['RT_PRT_ROA']),
 'PB': ('ratio', ['RT_VALUE_PB']), 'PE': ('ratio', ['RT_VALUE_PE']),
 'EPS': ('ratio', ['RT_VALUE_EPS']), 'BVPS': ('ratio', ['RT_VALUE_BVPS']),
 'OutstandingShares': ('ratio', ['RT_VALUE_OUTSTANDING_SHARES']),
 'EV_EBITDA': ('ratio', ['RT_VALUE_EV_EBITDA']),
 'NIM': ('ratio', ['RT_BANK_NIM']), 'NPL': ('ratio', ['RT_BANK_NPL']),
 'CAR': ('ratio', ['RT_BANK_CAR']), 'CIR': ('ratio', ['RT_BANK_CIR']),
 'LDR': ('ratio', ['RT_BANK_LDR']), 'CASA': ('ratio', ['RT_BANK_CASA']),
 'LoanLossCoverage': ('ratio', ['RT_BANK_NPL_COVERAGE']),
}
from scripts.insurance_metrics import RAW_MAP
MAP.update(RAW_MAP)
FLOWS = {m for m,(ds,_) in MAP.items() if ds in ('income','cashflow')} | {'EBIT','EBITDA','FOCF'}
RATIOS = {m for m,(ds,_) in MAP.items() if ds=='ratio'} - {'OutstandingShares'}
RATIOS |= {'DebtEquity','DebtAssets','EquityAssets','EquityAssetsCorp','AssetEquity',
 'TangibleEquityAssets','LoanAssets','DepositAssets','FundingGapAssets','CreditCostProxy',
 'NII_OperatingIncome','ProvisionOperatingIncome','ProfitAssets','NetMargin','GrossMargin',
 'OperatingProfitMargin','EBITDAMargin','CurrentRatio','WorkingCapitalAssets','CashAssets',
 'NetDebtEquity','NetDebtEBITDA','DebtEBITDA','CFO_Debt','FOCF_Debt','CashDebt','CFO_Margin',
 'FOCFMargin','CapexRevenue','AssetTurnover','MarginLoansEquity','LoansEquity',
 'InsuranceReservesEquity','InterestCoverage','AvailableCapitalRatio'}
INSURANCE_NA = {'EBIT','EBITDA','EBITDAMargin','DebtEBITDA','NetDebtEBITDA','InterestCoverage',
 'EV_EBITDA','CurrentRatio','WorkingCapitalAssets','FOCF','FOCF_Debt','FOCFMargin','CFO_Debt',
 'CashDebt','GrossMargin','OperatingProfitMargin'}
BANK_NA = INSURANCE_NA | {'Revenue','NetMargin','DebtEquity','DebtAssets','TotalDebt',
 'ShortTermBorrowings','LongTermBorrowings','NetDebtEquity','AssetTurnover','CFO_Margin','CapexRevenue'}
SEC_NA = {'EBITDA','EBITDAMargin','DebtEBITDA','NetDebtEBITDA','EV_EBITDA'}

def number(v):
    try:
        n=float(v)
        return n if np.isfinite(n) else None
    except (TypeError,ValueError): return None

def period(v):
    s=str(v).strip().upper()
    m=re.fullmatch(r'(20\d{2})(?:[- ]?Q([1-4]))?',s)
    if not m: return None
    return (int(m[1]),int(m[2]) if m[2] else 4,'Q' if m[2] else 'FY')

def period_date(v):
    p=period(v)
    return pd.Timestamp(p[0],p[1]*3,1)+pd.offsets.MonthEnd(0) if p else pd.NaT

def signature(path):
    p=Path(path)
    return (str(p),p.stat().st_mtime_ns,p.stat().st_size) if p.exists() else (str(p),0,0)

@lru_cache(maxsize=128)
def _csv_cached(sig):
    if not sig[1]: return pd.DataFrame()
    # Metadata ICB là mã định danh, không phải số; giữ số 0 đầu khi đọc lại CSV.
    try: return pd.read_csv(sig[0],dtype={f'ICBCode{lv}':str for lv in range(1,5)})
    except pd.errors.EmptyDataError: return pd.DataFrame()
    except (OSError,ValueError,pd.errors.ParserError) as e:
        x=pd.DataFrame(); x.attrs['error']=f'{type(e).__name__}: {e}'; return x

def read_csv(path): return _csv_cached(signature(path)).copy()

def normalize_raw(df, source='', default_basis='QUARTER'):
    """Chấp nhận long, cột semantic hoặc hàng semantic × kỳ; giữ zero thật."""
    if df.empty: return pd.DataFrame(columns=['Period','Field','Value','Basis','Source','Unit'])
    d=df.copy(); cols={str(c).lower():c for c in d.columns}
    pc=cols.get('period'); ic=next((cols[k] for k in ('id','semantic_id','item') if k in cols),None)
    vc=cols.get('value'); bc=cols.get('basis') or cols.get('period_basis')
    if pc is not None and ic is not None and vc is not None:
        z=pd.DataFrame({'Period':d[pc],'Field':d[ic],'Value':d[vc],
                        'Basis':d[bc] if bc else default_basis,
                        'Unit':d[cols['unit']] if 'unit' in cols else ''})
    elif pc is not None:
        fields=[c for c in d if re.match(r'^(BS|IS|CF|RT)_',str(c))]
        z=d.melt(id_vars=[pc]+([bc] if bc else []),value_vars=fields,var_name='Field',value_name='Value').rename(columns={pc:'Period'})
        z['Basis']=z[bc] if bc else default_basis;z['Unit']=''
    elif ic is not None:
        pcs=[c for c in d if period(c)]
        z=d.melt(id_vars=[ic],value_vars=pcs,var_name='Period',value_name='Value').rename(columns={ic:'Field'})
        z['Basis']=default_basis;z['Unit']=''
    else:
        raise ValueError(f'Không nhận diện cấu trúc raw: {source}')
    z['Field']=z.Field.astype(str).str.strip().str.upper()
    z['Period']=z.Period.astype(str).str.strip().str.upper()
    z['Value']=pd.to_numeric(z.Value,errors='coerce')
    z['Basis']=z.Basis.astype(str).str.upper().replace({'Q':'QUARTER','CUMULATIVE':'YTD'})
    z['Source']=source
    z=z[z.Period.map(period).notna()].copy()
    # Hai giá trị khác nhau cùng semantic/kỳ là xung đột, không chọn tùy tiện.
    conflict=z.groupby(['Period','Field']).Value.transform('nunique').gt(1)
    z.loc[conflict,'Value']=np.nan
    z['Error']=np.where(conflict,'CONFLICTING_SOURCE_VALUES','')
    return z.drop_duplicates(['Period','Field'],keep='last')

def _paths(ticker,typ,root):
    raw=Path(root)/'data/raw'; paths=[]
    for ds in ['balance','income','cashflow','ratio']:
        candidates=[raw/f'{ticker}_{ds}_q.csv',raw/f'{ticker}_{ds}.csv'] if typ=='BANK' else [raw/f'{ticker}_{ds}.csv',raw/f'{ticker}_{ds}_q.csv']
        paths.append(next((p for p in candidates if p.exists()),candidates[0]))
    return paths

def _record(metric,value=None,basis='',per='',source='',reason='',status=None):
    n=number(value)
    return {'Metric':metric,'Value':n,'Status':status or ('OK' if n is not None else 'MISSING'),
            'Basis':basis,'Period':per,'Source':source,'Reason':reason}

def _not_applicable(metric,typ):
    return metric in (BANK_NA if typ=='BANK' else INSURANCE_NA if typ=='INSURANCE' else SEC_NA if typ=='SECURITIES' else set())

@lru_cache(maxsize=128)
def _source_cached(ticker,typ,root,sigs,cache_sig,basis_sig):
    frames={};errors={};cfg=read_csv(Path(root)/'config/raw_period_basis.csv')
    for ds,sig in zip(['balance','income','cashflow','ratio'],sigs):
        raw=_csv_cached(sig)
        default='QUARTER'
        if len(cfg) and {'Ticker','Dataset','Basis'} <= set(cfg):
            q=cfg[cfg.Ticker.astype(str).str.upper().eq(ticker)&cfg.Dataset.eq(ds)]
            if len(q):default=str(q.iloc[-1].Basis).upper()
        try:
            frames[ds]=normalize_raw(raw,str(Path(sig[0]).relative_to(root)),default)
            if raw.attrs.get('error'): errors[ds]=raw.attrs['error']
        except ValueError as e: frames[ds]=pd.DataFrame();errors[ds]=str(e)
    cached=_csv_cached(cache_sig)
    if len(cached) and 'Ticker' in cached:cached=cached[cached.Ticker.astype(str).str.upper().eq(ticker)]
    # Cache chỉ bổ sung các mã ngân hàng không có trong nguồn raw chi tiết.
    # Không tái sử dụng dữ liệu doanh nghiệp bị fuzzy mapping trong bản cũ.
    mapped={}
    for metric,(ds,ids) in MAP.items():
        f=frames[ds]; chunks=[]
        for sid in ids:
            if len(f):
                q=f[f.Field.eq(sid)].copy()
                if len(q):chunks.append(q)
        z=pd.concat(chunks,ignore_index=True).drop_duplicates('Period',keep='first') if chunks else pd.DataFrame()
        if typ=='BANK' and metric in {'CustomerDeposits','OperatingIncome','CAR','ProvisionExpense'} and len(cached):
            q=cached[cached.Metric.eq(metric)].copy()
            if len(q):
                q=q.rename(columns={'Metric':'Field'})
                q['Source']=str(Path(cache_sig[0]).relative_to(root));q['Basis']='QUARTER';q['Unit']='';q['Error']=''
                if len(z):q=q[~q.Period.isin(z.loc[z.Value.notna() & z.Value.ne(0),'Period'])]
                z=pd.concat([q,z],ignore_index=True).drop_duplicates('Period',keep='first')
        mapped[metric]=z
    return mapped,errors

def source_data(ticker,typ,root=ROOT):
    root=Path(root);p=_paths(ticker,typ,root)
    return _source_cached(ticker,typ,str(root),tuple(signature(x) for x in p),
                          signature(root/'data/bank_history_long.csv'),signature(root/'config/raw_period_basis.csv'))

def aggregate(metric, frame, target, basis='TTM'):
    """Tính tại một kỳ; thiếu bất kỳ quý nào thì không cộng thành TTM/YTD/FY."""
    if frame.empty:return _record(metric,per=target,reason='Không có mã dòng chính xác trong dữ liệu nguồn')
    target_p=period(target)
    if not target_p:return _record(metric,status='ERROR',reason='Kỳ không hợp lệ')
    y,q,_=target_p
    z=frame.set_index('Period',drop=False)
    def obs(p):
        return z.loc[p] if p in z.index else None
    if metric not in FLOWS:
        row=obs(target)
        if row is None and q==4:row=obs(str(y))
        if row is None:return _record(metric,per=target,reason='Thiếu dữ liệu đúng kỳ')
        v=number(row.Value);error=str(row.get('Error',''))
        if metric in {'CIR','LoanLossCoverage'} and v is not None:v=abs(v)
        if metric in {'CAR','EPS','BVPS','OutstandingShares'} and v==0:
            return _record(metric,per=target,source=row.Source,reason='Nguồn trả 0 cho chỉ tiêu không đủ cơ sở sử dụng')
        return _record(metric,v,'REPORTED_RATIO' if metric in RATIOS else 'END_PERIOD',target,row.Source+':'+str(row.Field),error,'ERROR' if error else None)
    if basis=='FY': wanted=[f'{y}-Q{i}' for i in range(1,5)]
    elif basis=='YTD':wanted=[f'{y}-Q{i}' for i in range(1,q+1)]
    elif basis=='TTM':wanted=[f'{n//4}-Q{n%4+1}' for n in range(y*4+q-4,y*4+q)]
    else:wanted=[f'{y}-Q{q}']
    # Năm tài chính công bố trực tiếp ưu tiên cho chế độ FY.
    if (basis=='FY' or (basis=='TTM' and q==4)) and obs(str(y)) is not None:
        r=obs(str(y));return _record(metric,r.Value,'FY',str(y),r.Source+':'+str(r.Field))
    vals=[];sources=[]
    for p in wanted:
        r=obs(p)
        if r is None or number(r.Value) is None:
            return _record(metric,basis=basis,per='|'.join(wanted),reason=f'Thiếu quý {p}; không cộng thiếu kỳ',status='ERROR' if r is not None and r.get('Error') else 'MISSING')
        v=float(r.Value);b=str(r.Basis).upper();pp=period(p)
        if b=='YTD' and pp[1]>1:
            prev=obs(f'{pp[0]}-Q{pp[1]-1}')
            if prev is None or number(prev.Value) is None or str(prev.Basis).upper()!='YTD':
                return _record(metric,basis=basis,per=p,reason='Thiếu kỳ lũy kế trước để tách quý')
            v-=float(prev.Value)
        elif b not in {'YTD','QUARTER'}:
            return _record(metric,basis=basis,per=p,status='UNREVIEWED',reason=f'Chưa xác nhận cơ sở nguồn {b}')
        vals.append(v);sources.append(r.Source+':'+str(r.Field))
    return _record(metric,sum(vals),basis,'|'.join(wanted),' + '.join(dict.fromkeys(sources)))

@lru_cache(maxsize=4096)
def _at_period_cached(ticker,typ,target,basis='TTM',root=ROOT,fingerprint=()):
    mapped,errors=source_data(ticker,typ,root)
    records={m:aggregate(m,f,target,basis) for m,f in mapped.items()}
    for m,(ds,_) in MAP.items():
        if ds in errors:records[m]=_record(m,per=target,status='ERROR',reason=errors[ds])
    def calc(m,keys,fn,ratio=False,positive=None):
        rs=[records[k] for k in keys];vs=[r['Value'] for r in rs]
        if any(v is None for v in vs):
            status='ERROR' if any(r['Status']=='ERROR' for r in rs) else 'MISSING'
            records[m]=_record(m,basis=basis,per=target,status=status,reason='Thiếu đầu vào: '+', '.join(k for k,v in zip(keys,vs) if v is None));return
        if ratio and vs[-1]==0:
            records[m]=_record(m,basis=basis,per=target,status='NOT_APPLICABLE',reason='Mẫu số bằng 0');return
        if positive and any(vs[keys.index(k)]<=0 for k in positive):
            records[m]=_record(m,basis=basis,per=target,status='NOT_APPLICABLE',reason='Mẫu số không dương; tỷ số không có ý nghĩa');return
        try:v=fn(*vs)
        except (ArithmeticError,ValueError) as e:
            records[m]=_record(m,status='ERROR',reason=f'{type(e).__name__}: {e}');return
        b=('DERIVED_'+basis) if any(k in FLOWS for k in keys) else 'END_PERIOD'
        records[m]=_record(m,v,b,target,'Công thức: '+'; '.join(keys))
    calc('TotalDebt',['ShortTermBorrowings','LongTermBorrowings'],lambda a,b:a+b)
    calc('TangibleEquity',['Equity','IntangibleAssets'],lambda a,b:a-b)
    calc('ParentEquity',['Equity','MinorityEquity'],lambda a,b:a-b)
    calc('EBIT',['PBT','InterestExpense'],lambda a,b:a+abs(b))
    calc('EBITDA',['EBIT','Depreciation'],lambda a,b:a+abs(b))
    calc('FOCF',['CFO','Capex'],lambda a,b:a-abs(b))
    calc('NetDebt',['TotalDebt','Cash'],lambda a,b:a-b)
    specs={'DebtEquity':('TotalDebt','Equity'),'DebtAssets':('TotalDebt','TotalAssets'),
      'EquityAssets':('Equity','TotalAssets'),'EquityAssetsCorp':('Equity','TotalAssets'),
      'AssetEquity':('TotalAssets','Equity'),'TangibleEquityAssets':('TangibleEquity','TotalAssets'),
      'LoanAssets':('GrossLoans','TotalAssets'),'DepositAssets':('CustomerDeposits','TotalAssets'),
      'NetMargin':('NPAT','Revenue'),'GrossMargin':('GrossProfit','Revenue'),
      'OperatingProfitMargin':('OperatingProfit','Revenue'),'EBITDAMargin':('EBITDA','Revenue'),
      'CurrentRatio':('CurrentAssets','CurrentLiabilities'),'CashAssets':('Cash','TotalAssets'),
      'NetDebtEquity':('NetDebt','Equity'),'CFO_Margin':('CFO','Revenue'),
      'FOCFMargin':('FOCF','Revenue'),'AssetTurnover':('Revenue','TotalAssets'),
      'MarginLoansEquity':('MarginLoans','Equity'),'LoansEquity':('Loans','Equity'),
      'InsuranceReservesEquity':('InsuranceReserves','Equity'),
      'NII_OperatingIncome':('NetInterestIncome','OperatingIncome'),
      'ProfitAssets':('NPAT','TotalAssets'),'CashDebt':('Cash','TotalDebt')}
    for m,keys in specs.items():calc(m,list(keys),lambda a,b:a/b,ratio=True,positive=[keys[1]])
    for m,keys in {'ProvisionOperatingIncome':('ProvisionExpense','OperatingIncome'),
                   'CreditCostProxy':('ProvisionExpense','GrossLoans'),'CapexRevenue':('Capex','Revenue')}.items():
        calc(m,list(keys),lambda a,b:abs(a)/b,ratio=True,positive=[keys[1]])
    calc('FundingGapAssets',['GrossLoans','CustomerDeposits','TotalAssets'],lambda a,b,c:(a-b)/c,ratio=True)
    calc('WorkingCapitalAssets',['CurrentAssets','CurrentLiabilities','TotalAssets'],lambda a,b,c:(a-b)/c,ratio=True)
    # Nợ/EBITDA và các tỷ số trả nợ luôn dùng dòng tiền TTM, dù màn hình chọn quý/YTD.
    if basis!='TTM':
        ttm=at_period(ticker,typ,target,'TTM',root)
        for m in ['DebtEBITDA','NetDebtEBITDA','CFO_Debt','FOCF_Debt','InterestCoverage']:records[m]=ttm[m]
    else:
        for m,keys in {'DebtEBITDA':('TotalDebt','EBITDA'),'NetDebtEBITDA':('NetDebt','EBITDA'),
                       'CFO_Debt':('CFO','TotalDebt'),'FOCF_Debt':('FOCF','TotalDebt')}.items():
            calc(m,list(keys),lambda a,b:a/b,ratio=True,positive=[keys[1]])
        calc('InterestCoverage',['EBIT','InterestExpense'],lambda a,b:a/abs(b),ratio=True)
    # EPS báo cáo được giữ nguyên nếu có; proxy dùng lợi nhuận cổ đông mẹ TTM / cổ phiếu cuối kỳ.
    if records['BVPS']['Value'] is None:
        calc('BVPS',['ParentEquity','OutstandingShares'],lambda a,b:a/b,ratio=True,positive=['OutstandingShares'])
    if records['EPS']['Value'] is None:
        parent=aggregate('ParentNPAT',mapped['ParentNPAT'],target,'TTM')
        sh=records['OutstandingShares']['Value']
        if parent['Value'] is not None and sh is not None and sh>0:
            records['EPS']=_record('EPS',parent['Value']/sh,'PROXY_PARENT_TTM_PER_CURRENT_SHARES',parent['Period'],parent['Source'],
                'Proxy theo cổ phiếu cuối kỳ; không phải EPS cơ bản theo bình quân gia quyền')
    for m in list(records):
        if _not_applicable(m,typ):records[m]=_record(m,per=target,status='NOT_APPLICABLE',reason=f'Không dùng trong phương pháp {typ}')
    if typ=='INSURANCE':
        from scripts.insurance_metrics import extend_records
        records=extend_records(ticker,target,basis,records,root)
    return records

def at_period(ticker,typ,target,basis='TTM',root=ROOT):
    root=Path(root)
    fingerprint=tuple(signature(p) for p in _paths(ticker,typ,root))+ (signature(root/'data/bank_history_long.csv'),signature(root/'config/raw_period_basis.csv'))
    return {m:dict(r) for m,r in _at_period_cached(ticker,typ,target,basis,root,fingerprint+(signature(root/'config/insurance_metric_inputs.csv'),signature(root/'config/insurance_entities.csv'))).items()}


def latest_period(ticker,typ,root=ROOT):
    mapped,_=source_data(ticker,typ,root)
    z=mapped['TotalAssets']
    if z.empty:z=next((f for f in mapped.values() if len(f)),pd.DataFrame())
    ps=[p if period(p)[2]=='Q' else f'{period(p)[0]}-Q4' for p in z.get('Period',[]) if period(p)]
    return max(ps,key=period_date) if ps else None

def repair_snapshot(ticker,typ,base=None,root=ROOT):
    d=dict(base or {});target=latest_period(ticker,typ,root)
    if not target:
        _,errors=source_data(ticker,typ,root)
        status='ERROR' if errors else 'UNREVIEWED'
        reason=str(errors) if errors else 'Không tìm được kỳ raw hợp lệ để xác minh cache'
        d['_DataIssues']=[reason]
        d['_MetricEvidence']={m:_record(m,status=status,reason=reason) for m in set(MAP)|RATIOS|FLOWS}
        for m in d['_MetricEvidence']:d[m]=None
        return d
    records=at_period(ticker,typ,target,'TTM',root)
    # Chỉ CAR được phép hiển thị kỳ công bố cũ; gắn kỳ riêng, không trộn vào benchmark hiện hành.
    if typ=='BANK' and records['CAR']['Value'] is None:
        mapped,_=source_data(ticker,typ,root);f=mapped['CAR']
        for p in sorted(set(f.get('Period',[])),key=period_date,reverse=True):
            if period_date(p)>period_date(target):continue
            r=aggregate('CAR',f,p)
            if r['Value'] is not None and 0<r['Value']<1:
                r['Reason']='Kỳ công bố gần nhất; khác kỳ hiện tại' if p!=target else ''
                records['CAR']=r;break
    for m,r in records.items():
        d[m]=r['Value']; d[m+'_Basis']=r['Basis'];d[m+'_Periods']=r['Period'];d[m+'_SourceRow']=r['Source']
        d[m+'_AsOf']=r['Period'].split('|')[-1] if r['Period'] else target
    d['Ticker']=ticker;d['EntityType']=typ;d['SnapshotPeriod']=target
    d['FlowBasis']='TTM';d['EvidenceVersion']='8.118.0';d['_MetricEvidence']=records
    d['_DataIssues']=[f'{m}: {r["Reason"]}' for m,r in records.items() if r['Status']=='ERROR']
    d['PerShareUnit']='VND/share'
    return d

def insurance_reporting_subtype(meta):
    """Phạm vi BCTC tách khỏi nhóm so sánh do người dùng cấu hình."""
    value=str(meta.get('InsuranceReportingSubtype','')).strip().upper()
    if value in {'LIFE','NONLIFE','REINSURANCE','GROUP'}:return value
    return str(meta.get('InsuranceSubtype','')).strip().upper()


def comparable_model(target,peer):
    if target.get('EntityType')!=peer.get('EntityType'):return False
    if target.get('EntityType')!='INSURANCE':return True
    a=insurance_reporting_subtype(target);b=insurance_reporting_subtype(peer)
    return a in {'LIFE','NONLIFE','REINSURANCE','GROUP'} and a==b


def metric_evidence(snapshot,metric):
    r=snapshot.get('_MetricEvidence',{}).get(metric)
    if r:return dict(r)
    return _record(metric,snapshot.get(metric),str(snapshot.get(metric+'_Basis','')),
                   str(snapshot.get(metric+'_Periods',snapshot.get(metric+'_AsOf',''))),
                   str(snapshot.get(metric+'_SourceRow','')),reason='Cần nguồn chi tiết' if number(snapshot.get(metric)) is None else '')

def history(ticker,typ,root=ROOT,basis='QUARTER'):
    mapped,_=source_data(ticker,typ,root)
    periods=sorted({p for f in mapped.values() for p in f.get('Period',[]) if period(p) and period(p)[2]=='Q'},key=period_date)
    rows=[]
    for p in periods:
        for m,r in at_period(ticker,typ,p,basis,root).items():
            if r['Value'] is not None:
                rows.append(dict(Ticker=ticker,Period=p,Metric=m,Value=r['Value'],Basis=r['Basis'],Source=r['Source'],Status=r['Status']))
    return pd.DataFrame(rows,columns=['Ticker','Period','Metric','Value','Basis','Source','Status'])

def same_period_history(ticker,typ,basis='YTD',years=5,root=ROOT,metrics=None):
    latest=latest_period(ticker,typ,root)
    if not latest:return pd.DataFrame()
    y,q,_=period(latest);years=max(3,min(int(years),5))
    end_year=y if basis!='FY' or q==4 else y-1
    rows=[]
    for year in range(end_year-years+1,end_year+1):
        target=f'{year}-Q{4 if basis=="FY" else q}'
        rr=at_period(ticker,typ,target,basis,root)
        for m in (metrics or rr):
            r=rr.get(m,_record(m,reason='Chưa có ánh xạ nguồn lịch sử'))
            label=f'{year}' if basis=='FY' else f'{year}-Q{q}' if basis=='QUARTER' else f'{q*3}T/{year}' if basis=='YTD' else f'TTM {year}-Q{q}'
            rows.append(dict(Ticker=ticker,Period=target,DisplayPeriod=label,Metric=m,Value=r['Value'],
                Status=r['Status'],Basis=r['Basis'],Source=r['Source'],Reason=r['Reason']))
    return pd.DataFrame(rows)
