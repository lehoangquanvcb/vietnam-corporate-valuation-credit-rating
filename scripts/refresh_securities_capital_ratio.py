from __future__ import annotations
import argparse, io, re, sys, time
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'securities_capital_ratio_master.csv'

# Official domains only. Extend this dictionary when a new listed broker enters the peer set.
OFFICIAL_DOMAINS={
    'SSI':['ssi.com.vn'],
    'HCM':['hsc.com.vn'],
    'VND':['vndirect.com.vn'],
    'VCI':['vietcap.com.vn'],
    'MBS':['mbs.com.vn'],
    'FTS':['fpts.com.vn'],
    'BSI':['bsc.com.vn'],
    'VDS':['vdsc.com.vn'],
    'TVS':['tvs.vn'],
    'SHS':['shs.com.vn'],
    'VIX':['vixs.vn'],
    'CTS':['vietinbanksecurities.com.vn','vietinbanksecurities.com'],
    'DSC':['dsc.com.vn'],
    'ORS':['ors.com.vn'],
    'AGR':['agriseco.com.vn'],
    'VFS':['vfs.com.vn'],
}


DIRECT_IR_PAGES={
    'VDS':['https://www.vdsc.com.vn/quan-he-co-dong/thong-tin-tai-chinh?groupId=1'],
    'SSI':['https://www.ssi.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin'],
    'HCM':['https://www.hsc.com.vn/vi/bao-cao-tai-chinh'],
    'VND':['https://www.vndirect.com.vn/quan-he-nha-dau-tu/','https://www.vndirect.com.vn/thong-tin-tai-chinh/'],
    'FTS':['https://fpts.com.vn/quan-he-co-dong/'],
    'BSI':['https://www.bsc.com.vn/cong-ty/quan-he-co-dong'],
    'TVS':['https://www.tvs.vn/vi/quan-he-nha-dau-tu'],
    'MBS':['https://www.mbs.com.vn/bao-cao-tai-chinh/'],
    'VCI':['https://www.vietcap.com.vn/quan-he-nha-dau-tu'],
    'SHS':['https://www.shs.com.vn/quan-he-co-dong'],
    'VIX':['https://vixs.vn/quan-he-co-dong'],
    'CTS':['https://vietinbanksecurities.com.vn/quan-he-co-dong'],
    'DSC':['https://www.dsc.com.vn/quan-he-co-dong'],
    'ORS':['https://ors.com.vn/quan-he-co-dong'],
    'AGR':['https://agriseco.com.vn/quan-he-co-dong'],
    'VFS':['https://vfs.com.vn/quan-he-co-dong'],
}

VERIFIED_ATTC_DOCUMENTS={
    'SSI':[
        'https://www.ssi.com.vn/upload/files/IR/20260327_SSI_Bao_cao_ty_le_ATTC_nam_2025_da_kiem_toan.pdf',
    ],
    'MBS':[
        'https://www.mbs.com.vn/files/uploads/2026/07/MBS-FSR-VN-30.06.2026.pdf',
    ],
    'TVS':[
        'https://www.tvs.vn/api/files/TVS_-_31.12.2025_-_Safety_V-260327_122310.738.pdf',
    ],
}

VERIFIED_ATTC_PAGES={
 'SSI':['https://www.ssi.com.vn/quan-he-nha-dau-tu/bao-cao-tai-chinh','https://www.ssi.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin/chi-tiet/cong-bo-bctc-rieng-bctc-hop-nhat-va-bao-cao-ty-le-attc-soat-xet-ban-nien-2026','https://www.ssi.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin/chi-tiet/cong-bo-bctc-rieng-bctc-hop-nhat-va-bao-cao-ty-le-attc-nam-2025-da-kiem-toan'],
 'HCM':['https://www.hsc.com.vn/vi/cbtt-73-2026-bao-cao-tai-chinh-ban-nien-nam-2026-da-soat-xet-va-bao-cao-ty-le-an-toan-tai-chinh-tai-ngay-30-06-2026-da-soat-xet'],
 'MBS':['https://www.mbs.com.vn/bao-cao-tai-chinh/'],
 'TVS':['https://www.tvs.vn/vi/quan-he-nha-dau-tu?tab=financialReport','https://www.tvs.vn/vi/quan-he-nha-dau-tu/bao-cao-ty-le-an-toan-tai-chinh-ban-nien-2026'],
 'FTS':['https://www.fpts.com.vn/quan-he-co-dong/cong-bo-thong-tin/'],
}

FALLBACK_SECURITIES=['SSI','HCM','VND','VCI','MBS','FTS','BSI','TVS','SHS','VIX','CTS','DSC','ORS','AGR','VFS']

HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36'}
RX_RATIO=[
    re.compile(r'(?:tỷ\s*lệ|ty\s*le)\s*(?:an\s*toàn\s*tài\s*chính|an\s*toan\s*tai\s*chinh|vốn\s*khả\s*dụng|von\s*kha\s*dung)[^\d%]{0,500}(\d{2,4}(?:[.,]\d{1,3})?)\s*%',re.I),
    re.compile(r'(\d{2,4}(?:[.,]\d{1,3})?)\s*%[^\n]{0,500}(?:tỷ\s*lệ\s*vốn\s*khả\s*dụng|tỷ\s*lệ\s*an\s*toàn\s*tài\s*chính)',re.I),
    re.compile(r'(?:vốn\s*khả\s*dụng|von\s*kha\s*dung).{0,700}?(\d{3,4}(?:[.,]\d{1,3})?)\s*%',re.I),
]
RX_DATE=[
    re.compile(r'(?:tại\s*(?:thời\s*điểm|ngày)?\s*)?(\d{1,2})[\/\-.](\d{1,2})[\/\-.](20\d{2})',re.I),
    re.compile(r'(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(20\d{2})',re.I),
]

def _clean_text(s):
    return re.sub(r'\s+',' ',str(s or '')).strip()

def _pdf_text(content):
    try:
        from pypdf import PdfReader
        r=PdfReader(io.BytesIO(content))
        return '\n'.join((p.extract_text() or '') for p in r.pages)
    except Exception:
        return ''

def _html_text(content):
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(content,'html.parser').get_text('\n',strip=True)
    except Exception:
        return content.decode('utf-8','ignore')

def _parse_vn_number(x):
    x=str(x or '').strip().replace('\xa0',' ')
    x=re.sub(r'[^\d,.\-]','',x)
    if not x: return None
    if ',' in x and '.' in x:
        if x.rfind(',') > x.rfind('.'):
            x=x.replace('.','').replace(',','.')
        else:
            x=x.replace(',','')
    elif ',' in x:
        x=x.replace(',','.')
    try: return float(x)
    except Exception: return None

def _extract_report_date(txt):
    t=_clean_text(txt)
    pats=[
        r'(?:tại|ngày)\s+ngày\s*(\d{1,2})\s+tháng\s*(\d{1,2})\s+năm\s*(20\d{2})',
        r'(?:tại|ngày)\s*(\d{1,2})\s+tháng\s*(\d{1,2})\s+năm\s*(20\d{2})',
        r'(?:tại\s+ngày|ngày)\s*(\d{1,2})[./-](\d{1,2})[./-](20\d{2})',
        r'(\d{1,2})[./-](\d{1,2})[./-](20\d{2})',
    ]
    for p in pats:
        m=re.search(p,t,re.I)
        if m:
            try: return pd.Timestamp(int(m.group(3)),int(m.group(2)),int(m.group(1)))
            except Exception: pass
    return None

def _extract_ratio_candidates(txt):
    raw=_clean_text(txt)
    low=raw.lower()
    candidates=[]
    anchors=['tỷ lệ vốn khả dụng','ty le von kha dung',
             'tỷ lệ an toàn tài chính','ty le an toan tai chinh']
    for anchor in anchors:
        pos=0
        while True:
            i=low.find(anchor,pos)
            if i<0: break
            chunk=raw[i:i+700]
            for m in re.finditer(r'(\d{2,4}(?:[.,]\d{1,3})?)\s*%',chunk):
                v=_parse_vn_number(m.group(1))
                if v is None or not (100.0 <= v <= 5000.0): continue
                context=chunk[max(0,m.start()-100):m.end()+80].lower()
                penalty=0
                if 'x 100' in context or '× 100' in context: penalty+=10
                if 'tối thiểu' in context or 'toi thieu' in context: penalty+=8
                if 'quy định' in context or 'quy dinh' in context: penalty+=4
                if abs(v-180.0)<1e-9 or abs(v-220.0)<1e-9: penalty+=5
                candidates.append((m.start()+penalty*100,v))
            pos=i+len(anchor)
    return candidates

def _extract(text):
    if not text: return None,None
    d=_extract_report_date(text)
    cands=_extract_ratio_candidates(text)
    if not cands: return d,None
    cands=sorted(cands,key=lambda z:z[0])
    return d,cands[0][1]/100.0

def _same_official_domain(url, domains):
    try:
        host=urlparse(url).netloc.lower()
        return any(host==d.lower() or host.endswith('.'+d.lower()) for d in domains)
    except Exception:
        return False


def _vds_financial_table_rows(years_back=5):
    """Parse VDS official financial-information tables directly.
    Quarterly page provides recent quarters; annual page provides historical FY values.
    Values are read live from VDS, never hardcoded.
    """
    rows=[]
    urls=[
        ('https://www.vdsc.com.vn/quan-he-co-dong/thong-tin-tai-chinh?groupId=1','QUARTER'),
        ('https://www.vdsc.com.vn/quan-he-co-dong/thong-tin-tai-chinh?groupId=2','ANNUAL'),
    ]
    min_year=date.today().year-int(years_back)
    for url,kind in urls:
        try:
            r=requests.get(url,headers=HEADERS,timeout=30)
            r.raise_for_status()
            from bs4 import BeautifulSoup
            soup=BeautifulSoup(r.text,'html.parser')
            for table in soup.find_all('table'):
                txt=_clean_text(table.get_text(' ',strip=True)).lower()
                if 'tỷ lệ an toàn tài chính' not in txt and 'ty le an toan tai chinh' not in txt:
                    continue
                headers=[_clean_text(x.get_text(' ',strip=True)) for x in table.find_all('th')]
                target=None
                for tr in table.find_all('tr'):
                    cells=[_clean_text(x.get_text(' ',strip=True)) for x in tr.find_all(['th','td'])]
                    if cells and ('tỷ lệ an toàn tài chính' in cells[0].lower() or 'ty le an toan tai chinh' in cells[0].lower()):
                        target=cells
                        break
                if not target or len(target)<2: continue
                # Most VDS tables: first header is "Nội dung", followed by periods.
                periods=headers[-(len(target)-1):] if len(headers)>=len(target)-1 else []
                if len(periods)!=len(target)-1:
                    # fallback: derive period labels from complete table text
                    periods=re.findall(r'(?:Quý\s*[1-4]/20\d{2}|Năm\s*20\d{2})',_clean_text(table.get_text(' ',strip=True)),re.I)
                    periods=periods[:len(target)-1]
                for per,val in zip(periods,target[1:]):
                    mval=re.search(r'(\d{2,4}(?:[.,]\d{1,3})?)\s*%',val)
                    if not mval: continue
                    ratio=float(mval.group(1).replace(',','.'))/100.0
                    my=re.search(r'(20\d{2})',per)
                    if not my: continue
                    y=int(my.group(1))
                    if y<min_year: continue
                    if kind=='ANNUAL':
                        d=pd.Timestamp(y,12,31)
                    else:
                        mq=re.search(r'(?:Quý|Q)\s*([1-4])',per,re.I)
                        if not mq: continue
                        q=int(mq.group(1))
                        d=pd.Timestamp(y,3*q,1)+pd.offsets.MonthEnd(0)
                    rows.append({
                        'Ticker':'VDS','ReportDate':d.date().isoformat(),
                        'AvailableCapitalRatio':ratio,'SourceURL':url,
                        'SourceDomain':'vdsc.com.vn','SourceType':'OFFICIAL_CTCK_FINANCIAL_TABLE',
                        'AuditStatus':'SOURCE_DISCLOSURE','CollectedDate':date.today().isoformat()
                    })
        except Exception as e:
            print(f'[WARN] VDS table adapter failed: {url} | {type(e).__name__}')
    # unique date
    uniq={}
    for x in rows: uniq[(x['Ticker'],x['ReportDate'])]=x
    return list(uniq.values())

def _direct_ir_urls(ticker, domains):
    """Crawl official IR landing pages first and return likely ATTC documents/pages."""
    seeds=[]
    for u in (VERIFIED_ATTC_DOCUMENTS.get(ticker,[])+
              VERIFIED_ATTC_PAGES.get(ticker,[])+
              DIRECT_IR_PAGES.get(ticker,[])):
        if u not in seeds: seeds.append(u)
    out=[]
    keywords=('an-toan','an_toan','attc','von-kha-dung','vốn-khả-dụng',
              'ty-le-an-toan','tỷ-lệ-an-toàn','financial-safety','capital-adequacy')
    for seed in seeds:
        try:
            r=requests.get(seed,headers=HEADERS,timeout=25)
            r.raise_for_status()
            html=r.text
            # Keep seed itself because some IR pages contain the ratio directly.
            out.append(seed)
            try:
                from bs4 import BeautifulSoup
                from urllib.parse import urljoin
                soup=BeautifulSoup(html,'html.parser')
                for a in soup.find_all('a',href=True):
                    href=urljoin(seed,a.get('href'))
                    label=_clean_text(a.get_text(' ',strip=True)).lower()
                    blob=(href+' '+label).lower()
                    parent_text=''
                    try: parent_text=_clean_text(a.parent.get_text(' ',strip=True)).lower()
                    except Exception: pass
                    context=(blob+' '+parent_text).lower()
                    attc_label=(('an toàn tài chính' in context) or ('tỷ lệ an toàn' in context) or
                                ('an toan tai chinh' in context) or ('ty le an toan' in context) or
                                ('attc' in context))
                    if _same_official_domain(href,domains) and (
                        any(k in context for k in keywords) or attc_label
                    ):
                        if href not in out: out.append(href)
            except Exception:
                pass
            # Also inspect literal official URLs embedded in scripts/API payloads.
            for hit in re.findall(r'https?://[^"\'<> ]+',html):
                hit=hit.replace('\\\\/','/').replace('&amp;','&')
                blob=hit.lower()
                if _same_official_domain(hit,domains) and any(k in blob for k in keywords):
                    if hit not in out: out.append(hit)
        except Exception as e:
            print(f'[WARN] {ticker} direct IR page failed: {seed} | {type(e).__name__}')
    return out[:100]

def _bing_official_urls(ticker,domain,years):
    """Discover candidate disclosures via public search, then enforce official-domain whitelist."""
    qs=[]
    for y in years:
        qs += [
            f'site:{domain} "{ticker}" "báo cáo tỷ lệ an toàn tài chính" {y}',
            f'site:{domain} "tỷ lệ an toàn tài chính" {y}',
            f'site:{domain} "tỷ lệ vốn khả dụng" {y}',
        ]
    urls=[]
    engines=[
        'https://www.google.com/search?q=',
        'https://www.bing.com/search?q=',
        'https://html.duckduckgo.com/html/?q=',
    ]
    for q in qs:
        for base in engines:
            try:
                html=requests.get(base+quote_plus(q),headers=HEADERS,timeout=15).text
                candidates=[]
                candidates += re.findall(r'https?://[^"\'<> &]+',html)
                candidates += [x.replace('&amp;','&') for x in re.findall(r'href=["\'](https?://[^"\']+)',html,re.I)]
                for hit in candidates:
                    hit=hit.replace('&amp;','&')
                    # unwrap common search redirect parameter
                    m=re.search(r'[?&](?:q|url|uddg)=(https?%3A%2F%2F[^&]+)',hit,re.I)
                    if m:
                        try:
                            from urllib.parse import unquote
                            hit=unquote(m.group(1))
                        except Exception:
                            pass
                    host=urlparse(hit).netloc.lower()
                    if (host==domain.lower() or host.endswith('.'+domain.lower())) and hit not in urls:
                        urls.append(hit)
            except Exception:
                pass
            time.sleep(.10)
    return urls[:80]


def _expand_detail_candidates(url, domains):
    """Follow one official detail page and collect its PDF/attachment links."""
    out=[]
    try:
        r=requests.get(url,headers=HEADERS,timeout=25)
        r.raise_for_status()
        ctype=(r.headers.get('content-type') or '').lower()
        if 'html' not in ctype and not url.lower().endswith(('.htm','.html','/')):
            return out
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        soup=BeautifulSoup(r.text,'html.parser')
        for a in soup.find_all('a',href=True):
            href=urljoin(url,a.get('href'))
            label=_clean_text(a.get_text(' ',strip=True)).lower()
            parent_text=''
            try: parent_text=_clean_text(a.parent.get_text(' ',strip=True)).lower()
            except Exception: pass
            blob=(href+' '+label+' '+parent_text).lower()
            if not _same_official_domain(href,domains):
                continue
            if (href.lower().split('?')[0].endswith('.pdf') or
                'download' in blob or 'attachment' in blob or
                'an toàn tài chính' in blob or 'ty le an toan' in blob or
                'tỷ lệ an toàn' in blob or 'attc' in blob):
                if href not in out: out.append(href)
    except Exception:
        pass
    return out[:30]

def _fetch_extract(url):
    try:
        r=requests.get(url,headers=HEADERS,timeout=35,allow_redirects=True)
        r.raise_for_status()
        ctype=(r.headers.get('content-type') or '').lower()
        final_url=str(getattr(r,'url',url) or url)
        is_pdf=('pdf' in ctype or final_url.lower().split('?')[0].endswith('.pdf')
                or bytes(r.content[:5])==b'%PDF-')
        txt=_pdf_text(r.content) if is_pdf else _html_text(r.content)
        return _extract(txt)
    except Exception:
        return None,None

def _peer_tickers(ticker,max_peers=10):
    """Resolve existing dynamic peers without importing a non-existent module."""
    t=str(ticker).upper().strip()
    out=[]
    # Try project-generated peer files first. We deliberately avoid importing
    # scripts.dynamic_peer_engine because this project build does not expose it.
    candidates=[
        ROOT/'data'/'dynamic_peers.csv',
        ROOT/'data'/'peer_master.csv',
        ROOT/'data'/'dynamic_peer_master.csv',
        ROOT/'data'/'peer_universe.csv',
    ]
    for fp in candidates:
        if not fp.exists(): continue
        try:
            q=pd.read_csv(fp)
            cols={str(c).lower():c for c in q.columns}
            tc=cols.get('ticker') or cols.get('target') or cols.get('targetticker')
            pc=cols.get('peer') or cols.get('peerticker') or cols.get('peer_ticker')
            if tc and pc:
                z=q[q[tc].astype(str).str.upper().str.strip().eq(t)]
                for x in z[pc].tolist():
                    x=str(x).upper().strip()
                    if x and x!=t and x not in out: out.append(x)
            elif 'Ticker' in q.columns:
                for x in q['Ticker'].tolist():
                    x=str(x).upper().strip()
                    if x and x!=t and x in OFFICIAL_DOMAINS and x not in out: out.append(x)
        except Exception:
            pass
        if len(out)>=max_peers: break
    for x in FALLBACK_SECURITIES:
        if x!=t and x not in out: out.append(x)
    return [t]+out[:max_peers]

def collect(ticker,years_back=5,max_peers=10):
    names=_peer_tickers(ticker,max_peers)
    years=list(range(date.today().year-years_back,date.today().year+1))
    rows=[]
    if str(ticker).upper().strip()=='VDS':
        vds_rows=_vds_financial_table_rows(years_back)
        rows.extend(vds_rows)
        print(f'[ADAPTER] VDS official financial tables: {len(vds_rows)} observations')
    old=pd.DataFrame()
    if OUT.exists():
        try: old=pd.read_csv(OUT)
        except Exception: old=pd.DataFrame()
    for t in names:
        domains=OFFICIAL_DOMAINS.get(t,[])
        if not domains:
            print(f'[SKIP] {t}: chưa cấu hình official domain')
            continue
        found=0
        verified_docs=VERIFIED_ATTC_DOCUMENTS.get(t,[])
        if verified_docs:
            print(f'     [ADAPTER] {t}: {len(verified_docs)} verified official ATTC document(s)')
            for _vu in verified_docs:
                _d,_r=_fetch_extract(_vu)
                _ds=_d.date().isoformat() if _d is not None else 'N/A'
                _rs=f'{_r*100:.2f}%' if _r is not None else 'N/A'
                print(f'       [PARSE] date={_ds} | ratio={_rs}')
        candidates=_direct_ir_urls(t,domains)
        # Search engines are fallback only.
        if len(candidates)<2:
            for domain in domains:
                for u in _bing_official_urls(t,domain,years):
                    if u not in candidates: candidates.append(u)
        expanded=list(candidates)
        frontier=list(candidates)
        for _depth in range(2):
            nxt=[]
            for _u in frontier:
                for _x in _expand_detail_candidates(_u,domains):
                    if _x not in expanded:
                        expanded.append(_x); nxt.append(_x)
            frontier=nxt
            if not frontier: break
        candidates=expanded
        for url in candidates:
            if not _same_official_domain(url,domains):
                continue
            d,ratio=_fetch_extract(url)
            if d is None or ratio is None:
                continue
            rows.append({
                'Ticker':t,'ReportDate':d.date().isoformat(),
                'AvailableCapitalRatio':round(float(ratio),6),
                'SourceURL':url,'SourceDomain':urlparse(url).netloc.lower(),
                'SourceType':'OFFICIAL_CTCK_DISCLOSURE',
                'AuditStatus':'SOURCE_DISCLOSURE',
                'CollectedDate':date.today().isoformat()
            })
            found+=1
        print(f'[OK] {t}: {found} observations discovered | candidates={len(candidates)}')
        if found==0 and candidates:
            print(f'     [INFO] official links found but no ratio/date extracted; first={candidates[0]}')
    schema=['Ticker','ReportDate','AvailableCapitalRatio','SourceURL','SourceDomain','SourceType','AuditStatus','CollectedDate']
    new=pd.DataFrame(rows,columns=schema)

    # A previous failed/empty run may have left a zero-column or legacy CSV.
    # Normalize both old and new frames before concatenation so an empty discovery
    # can never raise KeyError: ReportDate.
    if old is None or not isinstance(old,pd.DataFrame):
        old=pd.DataFrame(columns=schema)
    for c in schema:
        if c not in old.columns:
            old[c]=pd.NA
    old=old[schema]

    if new.empty:
        if old.empty:
            OUT.parent.mkdir(parents=True,exist_ok=True)
            pd.DataFrame(columns=schema).to_csv(OUT,index=False,encoding='utf-8-sig')
            print(f'No observations discovered. Empty master initialized safely at {OUT}')
        else:
            print(f'No new observations. Existing master preserved: {OUT} | rows={len(old)}')
        return
    allq=new.copy() if old.empty else pd.concat([old.dropna(how='all'),new],ignore_index=True)

    allq['Ticker']=allq['Ticker'].astype(str).str.upper().str.strip()
    allq['ReportDate']=pd.to_datetime(allq['ReportDate'],errors='coerce')
    allq['AvailableCapitalRatio']=pd.to_numeric(allq['AvailableCapitalRatio'],errors='coerce')
    allq=allq.dropna(subset=['Ticker','ReportDate','AvailableCapitalRatio'])
    allq=allq[(allq['AvailableCapitalRatio']>0.5)&(allq['AvailableCapitalRatio']<=20)]
    # Prefer newest collection for duplicate ticker/report-date observations.
    allq=allq.sort_values(['Ticker','ReportDate','CollectedDate']).drop_duplicates(['Ticker','ReportDate'],keep='last')
    allq['ReportDate']=allq['ReportDate'].dt.date.astype(str)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    allq.to_csv(OUT,index=False,encoding='utf-8-sig')
    print(f'SAVED: {OUT} | rows={len(allq)} | tickers={allq.Ticker.nunique()}')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('ticker',nargs='?',default='VDS')
    ap.add_argument('--years-back',type=int,default=5)
    ap.add_argument('--max-peers',type=int,default=10)
    a=ap.parse_args()
    collect(a.ticker,a.years_back,a.max_peers)
