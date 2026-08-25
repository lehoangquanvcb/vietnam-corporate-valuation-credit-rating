from pathlib import Path
import re, unicodedata
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; CFG=ROOT/'config'; DATA=ROOT/'data'

def _norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def _first(df,names):
    low={_norm(c):c for c in df.columns}
    for n in names:
        if _norm(n) in low:return low[_norm(n)]
    for c in df.columns:
        nc=_norm(c)
        if any(_norm(n) in nc or nc in _norm(n) for n in names):return c
    return None

def _reference():
    try:
        from vnstock_data import Reference
        return Reference()
    except Exception:
        return None

def _listing():
    try:
        from vnstock_data import Listing
    except Exception:
        try: from vnstock import Listing
        except Exception:return None
    for make in [lambda:Listing(source='VCI'),lambda:Listing(),lambda:Listing(source='KBS')]:
        try:return make()
        except Exception:pass
    return None

def fetch_industry_map():
    frames=[]
    ref=_reference()
    if ref is not None:
        for call in [lambda:ref.industry.sectors(lang='vi'),lambda:ref.industry.sectors(),lambda:ref.equity.list_by_industry(lang='vi'),lambda:ref.equity.list_by_industry()]:
            try:
                z=pd.DataFrame(call())
                if len(z):frames.append(z)
            except Exception:pass
    lst=_listing()
    if lst is not None:
        for method in ['symbols_by_industries','all_symbols_with_industry']:
            try:
                z=pd.DataFrame(getattr(lst,method)())
                if len(z):frames.append(z)
            except Exception:pass
    if not frames:raise RuntimeError('Không lấy được dữ liệu ngành từ Vnstock Reference/Listing.')
    # choose richest frame with ticker and industry information
    frames=sorted(frames,key=lambda x:(len(x.columns),len(x)),reverse=True)
    for df in frames:
        tc=_first(df,['symbol','ticker','code'])
        if tc is None:continue
        out=[]
        for _,r in df.iterrows():
            t=str(r.get(tc,'')).upper().strip()
            if not t or t in ('NAN','NONE'):continue
            rec={'Ticker':t}
            # Capture ICB levels robustly across vnstock/vnstock_data schema versions.
            for lv in [1,2,3,4]:
                cc=_first(df,[f'icb_code{lv}',f'icb_code_{lv}',f'icb code {lv}',f'icbcode{lv}'])
                nc=_first(df,[f'icb_name{lv}',f'icb_name_{lv}',f'icb name {lv}',f'industry_name{lv}',f'industry{lv}',f'sector_lv{lv}'])
                rec[f'ICBCode{lv}']=r.get(cc) if cc else None
                rec[f'ICBName{lv}']=r.get(nc) if nc else None
            # Common fields seen in Vnstock insights/reference.
            if not rec.get('ICBCode2'):
                c=_first(df,['icb_code2']); rec['ICBCode2']=r.get(c) if c else None
            if not rec.get('ICBName2'):
                c=_first(df,['vi_sector','industry','industry_name','sector']); rec['ICBName2']=r.get(c) if c else None
            out.append(rec)
        z=pd.DataFrame(out).drop_duplicates('Ticker')
        if len(z):
            z.to_csv(CFG/'vnstock_industry_map.csv',index=False,encoding='utf-8-sig')
            return z
    raise RuntimeError('Dữ liệu ngành Vnstock không có cột ticker phù hợp.')

def _entity_and_method(name1,name2,company=''):
    s=' '.join(map(str,[name1,name2,company])); n=_norm(s)
    if 'ngan hang' in n or re.search(r'\bbank\b',n):return 'BANK','BANK_2026'
    if 'chung khoan' in n or 'securities' in n or 'brokerage' in n:return 'SECURITIES','SECURITIES_2025'
    if 'hang khong' in n or 'airline' in n:return 'CORPORATE','EXCLUDED_SPECIALIZED'
    return 'CORPORATE','CORPORATE_2025'

def _best_sector(r):
    # ICB cấp 2 is the default benchmark level: specific enough for economics, broad enough for peer counts.
    for c in ['ICBName2','ICBName3','ICBName1','ICBName4']:
        v=r.get(c)
        if pd.notna(v) and str(v).strip() not in ('','nan','None'):return str(v).strip(),c
    return 'Chưa phân loại','NONE'

def apply_industry_classification(industry_map=None):
    u=pd.read_csv(CFG/'company_universe.csv');u['Ticker']=u.Ticker.astype(str).str.upper().str.strip()
    im=industry_map if industry_map is not None else fetch_industry_map(); im['Ticker']=im.Ticker.astype(str).str.upper().str.strip()
    # Drop stale auto-classification columns before merge.
    for c in ['ICBCode1','ICBName1','ICBCode2','ICBName2','ICBCode3','ICBName3','ICBCode4','ICBName4']:
        if c in u.columns:u=u.drop(columns=[c])
    u=u.merge(im,on='Ticker',how='left')
    sectors=[]; levels=[]; etypes=[]; methods=[]; groups=[]
    for _,r in u.iterrows():
        sec,lv=_best_sector(r); et,method=_entity_and_method(r.get('ICBName1'),sec,r.get('CompanyName'))
        # Banks are intentionally one benchmark universe: all listed/registered-trading banks in the master.
        if et=='BANK': sec='Ngân hàng'; group='20 ngân hàng niêm yết/ĐKGD' if len(u[u.get('EntityType','').astype(str).eq('BANK')])==20 else 'Ngân hàng niêm yết/ĐKGD'
        elif et=='SECURITIES': sec='Công ty chứng khoán'; group='Công ty chứng khoán niêm yết/ĐKGD'
        else: group=sec
        sectors.append(sec);levels.append(lv);etypes.append(et);methods.append(method);groups.append(group)
    u['Sector']=sectors;u['IndustryLevelUsed']=levels;u['EntityType']=etypes;u['Methodology']=methods;u['PeerGroup']=groups;u['IndustrySource']='VNSTOCK_ICB_AUTO'
    u.to_csv(CFG/'company_universe.csv',index=False,encoding='utf-8-sig')
    audit=u.groupby(['EntityType','Sector'],dropna=False).size().reset_index(name='Companies').sort_values(['EntityType','Companies'],ascending=[True,False])
    audit.to_csv(CFG/'industry_classification_audit.csv',index=False,encoding='utf-8-sig')
    print(f'OK - auto-classified {len(u)} companies using Vnstock ICB.');print(audit.head(40).to_string(index=False))
    return u

if __name__=='__main__':apply_industry_classification()
