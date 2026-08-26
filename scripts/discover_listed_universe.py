from pathlib import Path
import pandas as pd, re
ROOT=Path(__file__).resolve().parents[1]; CFG=ROOT/'config'
try:
    try: from vnstock_data import Listing
    except Exception: from vnstock import Listing
except Exception as e:
    print('Không import được Listing từ vnstock/vnstock_data:',e); raise SystemExit(2)

def norm(s): return str(s).lower().strip()
def first_col(df,cands):
    for c in cands:
        if c in df.columns:return c
    low={str(c).lower():c for c in df.columns}
    for c in cands:
        if c.lower() in low:return low[c.lower()]
    return None

def fetch_listing():
    obj=None
    for make in [lambda:Listing(source='VCI'),lambda:Listing(),lambda:Listing(source='KBS')]:
        try: obj=make(); break
        except Exception:pass
    if obj is None:raise RuntimeError('Không khởi tạo được Listing')
    for method in ['all_symbols','symbols_by_industries','all_symbols_with_industry']:
        try:
            fn=getattr(obj,method); df=fn()
            if df is not None and len(df):return pd.DataFrame(df)
        except Exception:pass
    raise RuntimeError('Không tìm được method listing tương thích. Vui lòng kiểm tra phiên bản vnstock_data.')

def classify(industry,name):
    s=norm(industry)+' '+norm(name)
    if 'ngân hàng' in s or re.search(r'\bbank\b',s):return 'BANK','Ngân hàng','BANK_2026'
    if 'chứng khoán' in s or 'securities' in s or 'brokerage' in s:return 'SECURITIES','Công ty chứng khoán','SECURITIES_2025'
    if 'hàng không' in s or 'airline' in s:return 'CORPORATE','Hàng không','EXCLUDED_SPECIALIZED'
    # Industry holding company cannot be identified reliably from listing alone; analyst can override in master.
    return 'CORPORATE',str(industry) if str(industry) not in ('nan','None','') else 'Chưa phân loại','CORPORATE_2025'

def main():
    df=fetch_listing(); print('Listing columns:',list(df.columns))
    tc=first_col(df,['symbol','ticker','code']); nc=first_col(df,['organ_name','company_name','name','organName']); ec=first_col(df,['exchange','comGroupCode','exchange_name']); ic=first_col(df,['icb_name3','icb_name2','industry_name','industry','sector'])
    if tc is None:raise RuntimeError('Không xác định được cột ticker trong listing')
    rows=[]
    for _,r in df.iterrows():
        t=str(r.get(tc,'')).upper().strip()
        if not t or t in ('NAN','NONE'):continue
        name=str(r.get(nc,t)) if nc else t; ind=str(r.get(ic,'Chưa phân loại')) if ic else 'Chưa phân loại'; exch=str(r.get(ec,'N/A')) if ec else 'N/A'
        et,sector,method=classify(ind,name)
        rows.append({'Ticker':t,'CompanyName':name,'LegalName':name,'EntityType':et,'Sector':sector,'Exchange':exch,'PeerGroup':sector,'Methodology':method,'Active':1})
    new=pd.DataFrame(rows).drop_duplicates('Ticker')
    seed=pd.read_csv(CFG/'company_universe.csv'); seed['Ticker']=seed.Ticker.astype(str).str.upper()
    # Seed/master overrides discovery for classifications already curated.
    merged=pd.concat([new[~new.Ticker.isin(seed.Ticker)],seed],ignore_index=True).drop_duplicates('Ticker',keep='last').sort_values(['EntityType','Sector','Ticker'])
    merged.to_csv(CFG/'company_universe.csv',index=False,encoding='utf-8-sig')
    new.to_csv(CFG/'discovered_universe_raw.csv',index=False,encoding='utf-8-sig')
    # Audit by exchange/entity type. The discovered list is the source of truth for current market coverage.
    audit=merged.groupby(['Exchange','EntityType'],dropna=False).size().reset_index(name='Companies')
    audit.to_csv(CFG/'universe_coverage_audit.csv',index=False,encoding='utf-8-sig')
    print(f'OK - discovered {len(new)} tickers; master now {len(merged)} tickers.')
    print(audit.to_string(index=False))
if __name__=='__main__':
    main()
    try:
        from scripts.industry_classifier import apply_industry_classification
        apply_industry_classification()
    except Exception as e:
        print('CẢNH BÁO: chưa tự phân ngành ICB:',e)
