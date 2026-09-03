
import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from vnstock_env import load_vnstock_env
load_vnstock_env()

from pathlib import Path
import pandas as pd, re
ROOT=Path(__file__).resolve().parents[1]; CFG=ROOT/'config'

def norm(s): return str(s).lower().strip()
def first_col(df,cands):
    for c in cands:
        if c in df.columns:return c
    low={str(c).lower():c for c in df.columns}
    for c in cands:
        if c.lower() in low:return low[c.lower()]
    return None

def _from_vnstock_data_reference():
    """Primary API for vnstock_data v3/Bronze.

    Current vnstock_data exposes market reference/listing through Reference,
    not a root-level Listing class. Keep this path first so users do NOT need
    the separate legacy `vnstock` package.
    """
    from vnstock_data import Reference
    ref=Reference()
    calls=[
        ('Reference.equity.list', lambda: ref.equity.list()),
        ('Reference.equity.list_by_exchange', lambda: ref.equity.list_by_exchange()),
    ]
    errs=[]
    for label,fn in calls:
        try:
            z=fn(); df=pd.DataFrame(z)
            if len(df):
                print(f'Listing API: {label} | rows={len(df)}')
                return df
            errs.append(f'{label}: EMPTY')
        except Exception as e:
            errs.append(f'{label}: {type(e).__name__}: {e}')
    raise RuntimeError(' ; '.join(errs))

def _from_vnstock_data_listing_legacy():
    # Compatibility only for older vnstock_data builds that exported Listing.
    from vnstock_data import Listing
    obj=None
    for make in [lambda:Listing(source='VCI'),lambda:Listing(),lambda:Listing(source='KBS')]:
        try: obj=make(); break
        except Exception: pass
    if obj is None: raise RuntimeError('Không khởi tạo được vnstock_data.Listing')
    for method in ['all_symbols','symbols_by_exchange','symbols_by_industries','all_symbols_with_industry']:
        try:
            fn=getattr(obj,method); df=pd.DataFrame(fn())
            if len(df):
                print(f'Listing API: vnstock_data.Listing.{method} | rows={len(df)}')
                return df
        except Exception: pass
    raise RuntimeError('Không tìm được method Listing tương thích trong vnstock_data')

def _from_vnstock_legacy():
    # Last-resort compatibility. The package is optional and is NOT required
    # by this platform when vnstock_data is installed.
    from vnstock import Listing
    obj=None
    for make in [lambda:Listing(source='VCI'),lambda:Listing(),lambda:Listing(source='KBS')]:
        try: obj=make(); break
        except Exception: pass
    if obj is None: raise RuntimeError('Không khởi tạo được vnstock.Listing')
    for method in ['all_symbols','symbols_by_exchange','symbols_by_industries','all_symbols_with_industry']:
        try:
            df=pd.DataFrame(getattr(obj,method)())
            if len(df):
                print(f'Listing API: vnstock.Listing.{method} | rows={len(df)}')
                return df
        except Exception: pass
    raise RuntimeError('Không tìm được method Listing tương thích trong vnstock')

def fetch_listing():
    errs=[]
    for label,loader in [
        ('vnstock_data Reference v3', _from_vnstock_data_reference),
        ('vnstock_data Listing legacy', _from_vnstock_data_listing_legacy),
        ('vnstock legacy', _from_vnstock_legacy),
    ]:
        try:
            return loader()
        except Exception as e:
            errs.append(f'{label}: {type(e).__name__}: {e}')
    print('Không lấy được danh sách mã. Chi tiết:')
    for x in errs: print(' -',x)
    print('Gợi ý: chạy RUN_DIAGNOSE_VNSTOCK.bat để kiểm tra đúng Python/venv.')
    raise SystemExit(2)

def classify(industry,name):
    s=norm(industry)+' '+norm(name)
    if 'ngân hàng' in s or 'ngan hang' in s or re.search(r'\bbank\b',s):return 'BANK','Ngân hàng','BANK_2026'
    if 'chứng khoán' in s or 'chung khoan' in s or 'securities' in s or 'brokerage' in s:return 'SECURITIES','Công ty chứng khoán','SECURITIES_2025'
    if 'hàng không' in s or 'hang khong' in s or 'airline' in s:return 'CORPORATE','Hàng không','EXCLUDED_SPECIALIZED'
    return 'CORPORATE',str(industry) if str(industry) not in ('nan','None','') else 'Chưa phân loại','CORPORATE_2025'

def main():
    df=fetch_listing(); print('Listing columns:',list(df.columns))
    CFG.mkdir(parents=True,exist_ok=True)
    df.to_csv(CFG/'vnstock_listing_full.csv',index=False,encoding='utf-8-sig')
    tc=first_col(df,['symbol','ticker','code'])
    nc=first_col(df,['organ_name','company_name','name','organName','organ_short_name'])
    ec=first_col(df,['exchange','comGroupCode','exchange_name','board'])
    ic=first_col(df,['icb_name3','icb_name2','icb_name','industry_name','industry','sector','vi_sector'])
    if tc is None:raise RuntimeError(f'Không xác định được cột ticker trong listing. Columns={list(df.columns)}')
    rows=[]
    for _,r in df.iterrows():
        t=str(r.get(tc,'')).upper().strip()
        if not t or t in ('NAN','NONE'):continue
        name=str(r.get(nc,t)) if nc else t
        ind=str(r.get(ic,'Chưa phân loại')) if ic else 'Chưa phân loại'
        exch=str(r.get(ec,'N/A')) if ec else 'N/A'
        et,sector,method=classify(ind,name)
        rows.append({'Ticker':t,'CompanyName':name,'LegalName':name,'EntityType':et,'Sector':sector,'Exchange':exch,'PeerGroup':sector,'Methodology':method,'Active':1})
    new=pd.DataFrame(rows).drop_duplicates('Ticker')
    seed=pd.read_csv(CFG/'company_universe.csv') if (CFG/'company_universe.csv').exists() else pd.DataFrame()
    if len(seed):
        seed['Ticker']=seed.Ticker.astype(str).str.upper().str.strip()
        override_cols=[c for c in ['CompanyName','LegalName','EntityType','Sector','PeerGroup','Methodology'] if c in seed.columns]
        ov=seed[['Ticker',*override_cols]].drop_duplicates('Ticker',keep='last').set_index('Ticker')
        new=new.set_index('Ticker')
        for c in override_cols:
            common=new.index.intersection(ov.index)
            vals=ov.loc[common,c]
            mask=vals.notna() & vals.astype(str).str.strip().ne('')
            if mask.any(): new.loc[vals.index[mask],c]=vals[mask]
        new=new.reset_index()
    merged=new.copy(); merged['Active']=1
    merged=merged.drop_duplicates('Ticker').sort_values(['EntityType','Sector','Ticker'])
    merged.to_csv(CFG/'company_universe.csv',index=False,encoding='utf-8-sig')
    new.to_csv(CFG/'discovered_universe_raw.csv',index=False,encoding='utf-8-sig')
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
