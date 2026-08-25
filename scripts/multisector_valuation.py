import numpy as np, pandas as pd
from scripts.universal_data import num, peer_snapshot, get_company

def valuation(ticker,s):
    meta=get_company(ticker); typ=meta.get('EntityType'); p=peer_snapshot(ticker)
    price=num(s.get('Price')); eps=num(s.get('EPS')); bvps=num(s.get('BVPS')); roe=num(s.get('ROE'))
    out={'Ticker':ticker,'EntityType':typ,'Price':price}
    if typ=='BANK':
        # Bank-specific valuation is maintained by the proven V7 engine; here provide universal cross-check.
        pb=num(s.get('PB')) or (price/bvps if price and bvps else None)
        peer_pb=pd.to_numeric(p.get('PB',pd.Series(dtype=float)),errors='coerce').median() if len(p) else np.nan
        fair=peer_pb*bvps if bvps and pd.notna(peer_pb) else None
        out.update({'PrimaryMethod':'P/B nhóm so sánh','CurrentMultiple':pb,'PeerMultiple':peer_pb,'FairValue':fair})
    elif typ=='SECURITIES':
        pb=num(s.get('PB')) or (price/bvps if price and bvps else None); pe=num(s.get('PE')) or (price/eps if price and eps else None)
        peer_pb=pd.to_numeric(p.get('PB',pd.Series(dtype=float)),errors='coerce').median() if len(p) else np.nan
        peer_pe=pd.to_numeric(p.get('PE',pd.Series(dtype=float)),errors='coerce').median() if len(p) else np.nan
        vals=[]
        if bvps and pd.notna(peer_pb): vals.append(peer_pb*bvps)
        if eps and pd.notna(peer_pe): vals.append(peer_pe*eps)
        fair=float(np.nanmedian(vals)) if vals else None
        out.update({'PrimaryMethod':'P/B + P/E nhóm CTCK','CurrentMultiple':pb,'PeerMultiple':peer_pb,'FairValue':fair})
    else:
        pe=num(s.get('PE')) or (price/eps if price and eps else None); ev_ebitda=num(s.get('EV_EBITDA'))
        peer_pe=pd.to_numeric(p.get('PE',pd.Series(dtype=float)),errors='coerce').median() if len(p) else np.nan
        peer_ev=pd.to_numeric(p.get('EV_EBITDA',pd.Series(dtype=float)),errors='coerce').median() if len(p) else np.nan
        vals=[]
        if eps and pd.notna(peer_pe): vals.append(peer_pe*eps)
        # EV/EBITDA requires enterprise bridge; do not fabricate if shares/net debt unavailable.
        fair=float(np.nanmedian(vals)) if vals else None
        out.update({'PrimaryMethod':'P/E nhóm ngành + EV/EBITDA cross-check','CurrentMultiple':pe,'PeerMultiple':peer_pe,'PeerEVEBITDA':peer_ev,'FairValue':fair})
    out['Upside']=out['FairValue']/price-1 if out.get('FairValue') and price else None
    return out
