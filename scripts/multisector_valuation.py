import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np, pandas as pd
from scripts.universal_data import num, peer_snapshot, get_company

DATA=_PROJECT_ROOT/'data'

def _safe_median(series):
    x=pd.to_numeric(series,errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
    return float(x.median()) if len(x) else np.nan

def _normalize_price(x):
    v=num(x)
    if v is None or not np.isfinite(v) or v<=0:
        return None
    v=float(v)
    # Support both thousand-VND quotes (e.g. 11.30) and VND/share (11,300).
    if v < 500:
        v*=1000.0
    while v>1_000_000:
        v/=1000.0
    return v if 100 <= v <= 1_000_000 else None

def latest_market_price(ticker, snapshot=None):
    t=str(ticker).upper().strip()
    p=DATA/'price_history.csv'
    if p.exists():
        try:
            q=pd.read_csv(p)
            q=q[q['Ticker'].astype(str).str.upper().str.strip().eq(t)].copy()
            q['Close']=pd.to_numeric(q['Close'],errors='coerce')
            q['_d']=pd.to_datetime(q['Date'],errors='coerce') if 'Date' in q.columns else pd.NaT
            q=q.dropna(subset=['Close']).sort_values('_d')
            if len(q):
                px=_normalize_price(q.iloc[-1]['Close'])
                if px is not None:return px
        except Exception:pass
    s=snapshot or {}
    return _normalize_price(s.get('Price')) or _normalize_price(s.get('Close'))

def valuation(ticker,s):
    from scripts.financial_evidence import metric_evidence, insurance_reporting_subtype
    meta=get_company(ticker);typ=meta.get('EntityType');p=peer_snapshot(ticker)
    price=latest_market_price(ticker,s);eps=num(s.get('EPS'));bvps=num(s.get('BVPS'))
    target_period=s.get('SnapshotPeriod')
    def median(metric,limit):
        target=metric_evidence(s,metric); vals=[]
        for row in p.to_dict('records') if len(p) else []:
            ev=metric_evidence(row,metric);v=num(ev['Value'])
            if ev['Period']==target['Period'] and ev['Basis']==target['Basis'] and v is not None and 0<v<=limit:vals.append(v)
        return (float(np.median(vals)) if len(vals)>=5 else None),len(vals)
    peer_pb,npb=median('PB',20);peer_pe,npe=median('PE',100)
    out={'Ticker':ticker,'EntityType':typ,'Price':price,'PriceBasis':'LATEST_DAILY_CLOSE_OR_SNAPSHOT',
         'FinancialPeriod':target_period,'DerivedBVPS':bvps,'DerivedEPS':eps,
         'EPSBasis':s.get('EPS_Basis'),'BVPSBasis':s.get('BVPS_Basis'),
         'PeerPBCount':npb,'PeerPECount':npe,'FairValue':None,'Status':'MISSING'}
    if typ=='INSURANCE':
        subtype=insurance_reporting_subtype(meta)
        pbv=peer_pb*bvps if subtype=='NONLIFE' and peer_pb and bvps is not None and bvps>0 else None
        pev=peer_pe*eps if subtype=='NONLIFE' and peer_pe and eps is not None and eps>0 else None
        out.update(PrimaryMethod='P/B peer phi nhân thọ cùng kỳ; P/E đối chiếu',CurrentMultiple=num(s.get('PB')),
                   PeerMultiple=peer_pb,PeerPE=peer_pe,ImpliedPBValue=pbv,ImpliedPEValue=pev,
                   FairValue=pbv,Status='MISSING' if subtype=='NONLIFE' else 'UNREVIEWED',
                   Reason='Giá trị tham chiếu = BVPS × P/B trung vị của ít nhất 5 peer phi nhân thọ cùng kỳ; P/E chỉ đối chiếu. Cần xem chất lượng tài sản, ROE và cơ cấu nghiệp vụ.' if subtype=='NONLIFE' else
                   'Tập đoàn/tái bảo hiểm cần phương pháp định giá phù hợp và mẫu so sánh đủ lớn; không gán bội số phi nhân thọ trực tiếp.')
    elif typ=='BANK':
        fair=peer_pb*bvps if peer_pb and bvps is not None and bvps>0 else None
        out.update(PrimaryMethod='P/B peer cùng kỳ',CurrentMultiple=num(s.get('PB')),PeerMultiple=peer_pb,FairValue=fair)
    elif typ=='SECURITIES':
        pbv=peer_pb*bvps if peer_pb and bvps is not None and bvps>0 else None
        pev=peer_pe*eps if peer_pe and eps is not None and eps>0 else None
        vals=[v for v in [pbv,pev] if v is not None]
        out.update(PrimaryMethod='P/B và P/E peer CTCK cùng kỳ',CurrentMultiple=num(s.get('PB')),CurrentPE=num(s.get('PE')),
                   PeerMultiple=peer_pb,PeerPE=peer_pe,ImpliedPBValue=pbv,ImpliedPEValue=pev,
                   FairValue=float(np.median(vals)) if vals else None)
    else:
        out.update(PrimaryMethod='P/E peer cùng kỳ',CurrentMultiple=num(s.get('PE')),PeerMultiple=peer_pe,
                   FairValue=peer_pe*eps if peer_pe and eps is not None and eps>0 else None)
    if out['FairValue'] is not None:out['Status']='OK'
    out.setdefault('Reason','Tối thiểu 5 peer cùng kỳ/cơ sở và EPS hoặc BVPS dương; không suy ngược từ thị giá khác kỳ')
    out['Upside']=out['FairValue']/price-1 if out['FairValue'] is not None and price else None
    return out
