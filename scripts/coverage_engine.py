from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; CFG=ROOT/'config'

def _read(p):
    try:return pd.read_csv(p)
    except:return pd.DataFrame()

def _present(v):
    try:return pd.notna(v) and str(v).strip() not in ('','nan','None')
    except:return False

def build_coverage_matrix():
    u=_read(CFG/'company_universe.csv')
    if u.empty:return pd.DataFrame()
    u['Ticker']=u.Ticker.astype(str).str.upper().str.strip()
    bank=_read(DATA/'bank_snapshot.csv'); corp=_read(DATA/'company_snapshot.csv')
    price=_read(DATA/'price_history.csv')
    for x in [bank,corp,price]:
        if len(x) and 'Ticker' in x:x['Ticker']=x.Ticker.astype(str).str.upper().str.strip()
    rows=[]
    for _,m in u.iterrows():
        t=m.Ticker; typ=m.get('EntityType','CORPORATE')
        s=bank[bank.Ticker.eq(t)] if typ=='BANK' and len(bank) else corp[corp.Ticker.eq(t)] if len(corp) else pd.DataFrame()
        r=s.iloc[-1].to_dict() if len(s) else {}
        price_ok=(len(price) and 'Ticker' in price and price.Ticker.eq(t).any()) or _present(r.get('Price'))
        bs_fields=['TotalAssets','TotalEquity']
        is_fields=['NPAT'] if typ=='BANK' else ['Revenue','NPAT']
        special=['NPL','CAR','CASA'] if typ=='BANK' else ['AvailableCapitalRatio','DebtEquity'] if typ=='SECURITIES' else ['DebtEquity','CurrentRatio']
        bs_ok=any(_present(r.get(k)) for k in bs_fields); is_ok=any(_present(r.get(k)) for k in is_fields)
        special_n=sum(_present(r.get(k)) for k in special)
        peer=str(m.get('PeerGroup','')).strip() not in ('','nan','Chưa phân loại')
        methodology=str(m.get('Methodology','')) not in ('','nan','EXCLUDED_SPECIALIZED')
        core=sum([price_ok,bs_ok,is_ok,peer]); total=4
        coverage=core/total
        if coverage>=1 and methodology and special_n>=1: readiness='PRODUCTION_READY'
        elif coverage>=.5: readiness='PARTIAL'
        else: readiness='INSUFFICIENT_DATA'
        rows.append({'Ticker':t,'CompanyName':m.get('CompanyName',t),'EntityType':typ,'Sector':m.get('Sector'),'Exchange':m.get('Exchange'),'PeerGroup':m.get('PeerGroup'),'Methodology':m.get('Methodology'),'Price':int(bool(price_ok)),'BalanceSheet':int(bool(bs_ok)),'IncomeStatement':int(bool(is_ok)),'SpecialMetrics':special_n,'PeerMapped':int(bool(peer)),'MethodologyEligible':int(bool(methodology)),'CoveragePct':coverage,'Readiness':readiness})
    z=pd.DataFrame(rows)
    z.to_csv(DATA/'coverage_matrix.csv',index=False,encoding='utf-8-sig')
    summary=z.groupby(['EntityType','Readiness']).size().reset_index(name='Companies')
    summary.to_csv(DATA/'coverage_summary.csv',index=False,encoding='utf-8-sig')
    return z

if __name__=='__main__':
    z=build_coverage_matrix(); print(f'OK - coverage matrix: {len(z)} companies'); print(z.Readiness.value_counts(dropna=False).to_string())
