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
    meta=get_company(ticker); typ=meta.get('EntityType'); p=peer_snapshot(ticker)
    price=latest_market_price(ticker,s)
    eps=num(s.get('EPS')); bvps=num(s.get('BVPS')); roe=num(s.get('ROE'))
    out={'Ticker':ticker,'EntityType':typ,'Price':price,'PriceBasis':'LATEST_DAILY_CLOSE_OR_SNAPSHOT'}

    if typ=='BANK':
        pb=num(s.get('PB')) or (price/bvps if price and bvps else None)
        _pb=pd.to_numeric(p.get('PB',pd.Series(dtype=float)),errors='coerce') if len(p) else pd.Series(dtype=float)
        _pb=_pb[(_pb>0)&(_pb<=20)]
        peer_pb=_safe_median(_pb)
        # Derive BVPS transparently when only price/PB are present.
        if bvps is None and price not in (None,0) and pb not in (None,0):
            bvps=price/pb
        fair=peer_pb*bvps if bvps and pd.notna(peer_pb) else None
        out.update({'PrimaryMethod':'P/B nhóm so sánh','CurrentMultiple':pb,'PeerMultiple':peer_pb,
                    'DerivedBVPS':bvps,'FairValue':fair})

    elif typ=='SECURITIES':
        pb=num(s.get('PB')) or (price/bvps if price and bvps else None)
        pe=num(s.get('PE')) or (price/eps if price and eps else None)
        if bvps is None and price not in (None,0) and pb not in (None,0):
            bvps=price/pb
        if eps is None and price not in (None,0) and pe not in (None,0):
            eps=price/pe

        _pb=pd.to_numeric(p.get('PB',pd.Series(dtype=float)),errors='coerce') if len(p) else pd.Series(dtype=float)
        _pe=pd.to_numeric(p.get('PE',pd.Series(dtype=float)),errors='coerce') if len(p) else pd.Series(dtype=float)
        _pb=_pb[(_pb>0)&(_pb<=20)]
        _pe=_pe[(_pe>0)&(_pe<=100)]
        peer_pb=_safe_median(_pb); peer_pe=_safe_median(_pe)

        pb_value=float(peer_pb*bvps) if bvps not in (None,0) and pd.notna(peer_pb) else None
        pe_value=float(peer_pe*eps) if eps not in (None,0) and pd.notna(peer_pe) else None
        vals=[x for x in [pb_value,pe_value] if x is not None and np.isfinite(x) and x>0]
        fair=float(np.median(vals)) if vals else None
        out.update({'PrimaryMethod':'P/B + P/E nhóm CTCK','CurrentMultiple':pb,'CurrentPE':pe,
                    'PeerMultiple':peer_pb,'PeerPE':peer_pe,
                    'DerivedBVPS':bvps,'DerivedEPS':eps,
                    'ImpliedPBValue':pb_value,'ImpliedPEValue':pe_value,'FairValue':fair})

    else:
        pe=num(s.get('PE')) or (price/eps if price and eps else None)
        if eps is None and price not in (None,0) and pe not in (None,0):
            eps=price/pe
        ev_ebitda=num(s.get('EV_EBITDA'))
        _pe=pd.to_numeric(p.get('PE',pd.Series(dtype=float)),errors='coerce') if len(p) else pd.Series(dtype=float)
        _pe=_pe[(_pe>0)&(_pe<=100)]
        peer_pe=_safe_median(_pe)
        _ev=pd.to_numeric(p.get('EV_EBITDA',pd.Series(dtype=float)),errors='coerce') if len(p) else pd.Series(dtype=float)
        _ev=_ev[(_ev>0)&(_ev<=50)]
        peer_ev=_safe_median(_ev)
        fair=float(peer_pe*eps) if eps not in (None,0) and pd.notna(peer_pe) else None
        out.update({'PrimaryMethod':'P/E nhóm ngành + EV/EBITDA cross-check','CurrentMultiple':pe,
                    'PeerMultiple':peer_pe,'PeerEVEBITDA':peer_ev,'DerivedEPS':eps,'FairValue':fair})

    out['Upside']=out['FairValue']/price-1 if out.get('FairValue') and price else None
    return out
