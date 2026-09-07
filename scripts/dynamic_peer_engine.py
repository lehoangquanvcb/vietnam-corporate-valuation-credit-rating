from __future__ import annotations
from pathlib import Path
import sys, math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts.universal_data import universe, bank_snapshot, generic_snapshot
DATA = ROOT / 'data'
CFG = ROOT / 'config'

MAX_PEERS = 10
MIN_PEERS = 5
OVERRIDE_FILE = CFG / 'dynamic_peer_overrides.csv'

SIZE_METRICS = {'TotalAssets','Revenue','Equity','Loans','Deposits','MarketCap','ClientAssets','MarginLoans'}

WEIGHTS = {
    'BANK': {
        'TotalAssets': .32, 'ROE': .14, 'NIM': .10, 'NPL': .10, 'CAR': .10,
        'CASA': .08, 'LDR': .07, 'LoanAssets': .05, 'EquityAssets': .04,
    },
    'SECURITIES': {
        'TotalAssets': .26, 'Equity': .15, 'Revenue': .11, 'ROE': .14,
        'DebtEquity': .13, 'CurrentRatio': .07, 'MarginLoansEquity': .09,
        'AssetTurnover': .05,
    },
    'CORPORATE': {
        'TotalAssets': .23, 'Revenue': .20, 'Equity': .10, 'ROE': .11, 'ROA': .08,
        'DebtEquity': .13, 'CurrentRatio': .07, 'AssetTurnover': .05, 'CashAssets': .03,
    },
}


def _norm_ticker(x):
    return str(x).upper().strip()


def _snapshot_for_type(entity_type: str) -> pd.DataFrame:
    s = bank_snapshot() if str(entity_type).upper() == 'BANK' else generic_snapshot()
    if s is None or s.empty or 'Ticker' not in s.columns:
        return pd.DataFrame()
    s = s.copy()
    s['Ticker'] = s['Ticker'].map(_norm_ticker)
    return s.drop_duplicates('Ticker', keep='last')



def _override_pool(ticker: str, u: pd.DataFrame):
    """Optional analyst-maintained peer set.

    Overrides are used before broad ICB/sector matching. They solve cases where the
    provider's ICB hierarchy is too coarse (e.g. HPG classified only as Materials).
    The target itself is appended so similarity can be calculated once peer data exist.
    """
    t=_norm_ticker(ticker)
    try:
        o=pd.read_csv(OVERRIDE_FILE)
    except Exception:
        return pd.DataFrame(), None
    if o.empty or 'TargetTicker' not in o.columns or 'PeerTicker' not in o.columns:
        return pd.DataFrame(), None
    o=o.copy()
    o['TargetTicker']=o['TargetTicker'].map(_norm_ticker)
    o['PeerTicker']=o['PeerTicker'].map(_norm_ticker)
    if 'Active' in o.columns:
        o=o[pd.to_numeric(o['Active'],errors='coerce').fillna(1).eq(1)]
    z=o[o['TargetTicker'].eq(t)].copy()
    if z.empty:return pd.DataFrame(), None
    if 'Priority' in z.columns:
        z['_p']=pd.to_numeric(z['Priority'],errors='coerce').fillna(9999)
        z=z.sort_values(['_p','PeerTicker'])
    wanted=[t]+[x for x in z['PeerTicker'].tolist() if x!=t]
    pool=u[u['Ticker'].isin(wanted)].copy()
    # preserve analyst order instead of alphabetical/provider order
    order={x:i for i,x in enumerate(wanted)}
    pool['_override_order']=pool['Ticker'].map(order).fillna(9999)
    pool=pool.sort_values('_override_order').drop(columns=['_override_order'])
    return pool, 'Nhóm peer chuyên ngành (analyst override)'

def _candidate_pool(ticker: str, u: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    t = _norm_ticker(ticker)
    z = u[u.Ticker.eq(t)]
    if z.empty:
        return u[u.Ticker.eq(t)].copy(), 'Không xác định'
    r = z.iloc[0]
    et = str(r.get('EntityType','CORPORATE')).upper()
    same_type = u[u.EntityType.astype(str).str.upper().eq(et)].copy()
    if et == 'CORPORATE':
        opool, olabel = _override_pool(t, same_type)
        if len(opool) >= 2:
            return opool, olabel
    if et == 'BANK':
        return same_type, 'Ngân hàng niêm yết/ĐKGD'
    if et == 'SECURITIES':
        return same_type, 'Công ty chứng khoán niêm yết/ĐKGD'

    # Corporate: prefer economically coherent ICB level 2; broaden only if too few.
    for col, label in [('ICBCode2','ICB cấp 2'), ('Sector','ngành'), ('ICBCode1','ICB cấp 1')]:
        val = r.get(col)
        if pd.isna(val) or str(val).strip() in ('','nan','None') or col not in same_type.columns:
            continue
        p = same_type[same_type[col].astype(str).eq(str(val))].copy()
        if len(p) >= MIN_PEERS + 1:
            return p, f'{label}: {r.get("Sector", val)}'
    return same_type, 'Doanh nghiệp phi tài chính (mở rộng do ngành ít peer)'


def _pct_rank_distance(series: pd.Series, target_value: float, candidate_value: float, log_scale=False):
    vals = pd.to_numeric(series, errors='coerce').replace([np.inf,-np.inf], np.nan).dropna()
    if len(vals) < 3 or not np.isfinite(target_value) or not np.isfinite(candidate_value):
        return None
    if log_scale:
        vals = np.log1p(np.maximum(vals.astype(float), 0))
        target_value = math.log1p(max(float(target_value),0))
        candidate_value = math.log1p(max(float(candidate_value),0))
    # percentile positions are robust to outliers and scale differences.
    arr = np.sort(vals.to_numpy(dtype=float))
    tr = np.searchsorted(arr, target_value, side='right') / len(arr)
    cr = np.searchsorted(arr, candidate_value, side='right') / len(arr)
    return abs(tr-cr)


def select_dynamic_peers(ticker: str, max_peers: int = MAX_PEERS, _u=None, _snap_cache=None) -> pd.DataFrame:
    t = _norm_ticker(ticker)
    u = (_u.copy() if _u is not None else universe().copy())
    if u.empty:
        return pd.DataFrame()
    u['Ticker'] = u.Ticker.map(_norm_ticker)
    z = u[u.Ticker.eq(t)]
    if z.empty:
        return pd.DataFrame()
    et = str(z.iloc[0].get('EntityType','CORPORATE')).upper()
    pool, pool_label = _candidate_pool(t, u)
    s = (_snap_cache.get(et, pd.DataFrame()) if _snap_cache is not None else _snapshot_for_type(et))
    if s.empty:
        return pd.DataFrame()
    pool = pool.merge(s, on='Ticker', how='inner', suffixes=('','_snap'))
    if pool.empty:
        return pd.DataFrame()
    if t not in set(pool.Ticker):
        # Metadata-only fallback: still expose economically coherent peers, but do not
        # pretend a quantitative similarity score exists. This is useful while a
        # ticker's Bronze snapshot is missing/incomplete.
        base=_candidate_pool(t,u)[0].copy()
        base=base[~base.Ticker.eq(t)].head(max_peers).copy()
        if base.empty:return pd.DataFrame()
        out=pd.DataFrame({'TargetTicker':t,'Ticker':base.Ticker.astype(str).tolist()})
        out['PeerRank']=np.arange(1,len(out)+1);out['SimilarityScore']=np.nan;out['DistanceScore']=np.nan;out['MetricsCoverage']=0.0
        out['PeerPool']=pool_label;out['SimilarityBasis']='Cùng ngành/ICB; chờ dữ liệu tài chính để xếp hạng tương đồng'
        names=u[['Ticker']+[c for c in ['CompanyName','LegalName','Sector','EntityType'] if c in u.columns]].drop_duplicates('Ticker')
        return out.merge(names,on='Ticker',how='left')
    target = pool[pool.Ticker.eq(t)].iloc[-1]
    weights = WEIGHTS.get(et, WEIGHTS['CORPORATE'])
    rows=[]
    for _, r in pool.iterrows():
        ct = _norm_ticker(r.Ticker)
        if ct == t:
            continue
        weighted=0.0; used=0.0; missing=0.0; components=[]
        for m,w in weights.items():
            if m not in pool.columns:
                continue
            tv = pd.to_numeric(pd.Series([target.get(m)]), errors='coerce').iloc[0]
            cv = pd.to_numeric(pd.Series([r.get(m)]), errors='coerce').iloc[0]
            if pd.isna(tv) or pd.isna(cv):
                missing += w
                continue
            d = _pct_rank_distance(pool[m], float(tv), float(cv), log_scale=(m in SIZE_METRICS))
            if d is None:
                continue
            weighted += w*d; used += w
            components.append((m,d,w))
        if used <= 0:
            continue
        # modest penalty for missing comparable dimensions; do not over-penalize sparse Vnstock fields.
        score = weighted/used + 0.18*missing
        sim = max(0.0, 1.0-score)
        main = sorted(components, key=lambda x:x[2]*(1-x[1]), reverse=True)[:3]
        reason = ', '.join([m for m,_,_ in main]) if main else 'các chỉ tiêu hiện có'
        rows.append({'Ticker':ct,'SimilarityScore':sim,'DistanceScore':score,'MetricsCoverage':used,
                     'PeerPool':pool_label,'SimilarityBasis':reason})
    out = pd.DataFrame(rows)
    if out.empty:
        base=_candidate_pool(t,u)[0].copy()
        base=base[~base.Ticker.eq(t)].head(max_peers).copy()
        if base.empty:return out
        out=pd.DataFrame({'TargetTicker':t,'Ticker':base.Ticker.astype(str).tolist()})
        out['PeerRank']=np.arange(1,len(out)+1);out['SimilarityScore']=np.nan;out['DistanceScore']=np.nan;out['MetricsCoverage']=0.0
        out['PeerPool']=pool_label;out['SimilarityBasis']='Cùng ngành/ICB; chờ đủ KPI để tính similarity'
        names=u[['Ticker']+[c for c in ['CompanyName','LegalName','Sector','EntityType'] if c in u.columns]].drop_duplicates('Ticker')
        return out.merge(names,on='Ticker',how='left')
    out = out.sort_values(['DistanceScore','Ticker']).head(max_peers).reset_index(drop=True)
    out.insert(0,'TargetTicker',t)
    out['PeerRank'] = np.arange(1,len(out)+1)
    # attach readable names if available
    names = u[['Ticker'] + [c for c in ['CompanyName','LegalName','Sector','EntityType'] if c in u.columns]].drop_duplicates('Ticker')
    out = out.merge(names, on='Ticker', how='left')
    return out


def dynamic_peer_tickers(ticker: str, include_target=True, max_peers: int=MAX_PEERS):
    t = _norm_ticker(ticker)
    p = select_dynamic_peers(t, max_peers=max_peers)
    peers = p.Ticker.astype(str).tolist() if len(p) else []
    return ([t] if include_target else []) + peers


def dynamic_peer_label(ticker: str):
    # Analyst override is authoritative for the label as well as selection.
    u=universe(); ov,olabel=_override_pool(_norm_ticker(ticker),u)
    if olabel and len(ov)>=2:
        n=max(0,len(ov)-1)
        return f'Nhóm tương đồng động: {n} DN từ {olabel}'
    p = select_dynamic_peers(ticker)
    if p.empty:
        return 'Nhóm tương đồng động (chưa đủ dữ liệu)'
    pool = str(p.iloc[0].get('PeerPool','toàn thị trường'))
    return f'Nhóm tương đồng động: {len(p)} DN từ {pool}'


def build_dynamic_peer_map(target_ticker=None):
    u = universe(); all_rows=[]; summaries=[]
    if u.empty:
        return pd.DataFrame()
    u=u.copy(); u['Ticker']=u.Ticker.map(_norm_ticker)
    targets=u.Ticker.astype(str).tolist()
    if target_ticker:
        tt=_norm_ticker(target_ticker); targets=[tt] if tt in set(targets) else []
    snap_cache={'BANK':_snapshot_for_type('BANK'),'SECURITIES':_snapshot_for_type('SECURITIES'),'CORPORATE':_snapshot_for_type('CORPORATE')}
    for i,t in enumerate(targets,1):
        p = select_dynamic_peers(t, _u=u, _snap_cache=snap_cache)
        if len(p):
            all_rows.append(p)
            pool=str(p.iloc[0].get('PeerPool','toàn thị trường'))
            label=f'Nhóm tương đồng động: {len(p)} DN từ {pool}'
            summaries.append({'Ticker':_norm_ticker(t),'DynamicPeerGroup':label,'DynamicPeerCount':len(p),'DynamicPeers':','.join(p.Ticker.astype(str))})
        else:
            summaries.append({'Ticker':_norm_ticker(t),'DynamicPeerGroup':'Nhóm tương đồng động (chưa đủ dữ liệu)','DynamicPeerCount':0,'DynamicPeers':''})
        if not target_ticker and i % 100 == 0: print(f'Dynamic peer: {i}/{len(targets)}')
    z = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    map_path=DATA/'dynamic_peer_map.csv'; sum_path=DATA/'dynamic_peer_summary.csv'
    if target_ticker:
        tt=_norm_ticker(target_ticker)
        try: old=pd.read_csv(map_path); old=old[old.TargetTicker.astype(str).str.upper().ne(tt)] if 'TargetTicker' in old.columns else pd.DataFrame()
        except Exception: old=pd.DataFrame()
        z=pd.concat([old,z],ignore_index=True,sort=False) if len(old) or len(z) else pd.DataFrame()
        try: olds=pd.read_csv(sum_path); olds=olds[olds.Ticker.astype(str).str.upper().ne(tt)] if 'Ticker' in olds.columns else pd.DataFrame()
        except Exception: olds=pd.DataFrame()
        sums=pd.concat([olds,pd.DataFrame(summaries)],ignore_index=True,sort=False)
    else:
        sums=pd.DataFrame(summaries)
    z.to_csv(map_path,index=False,encoding='utf-8-sig'); sums.to_csv(sum_path,index=False,encoding='utf-8-sig')
    print(f'OK - dynamic peer update: {len(targets)} target(s)')
    return z


if __name__ == '__main__':
    import sys
    target=sys.argv[1] if len(sys.argv)>1 and str(sys.argv[1]).upper() not in {'ALL','--ALL'} else None
    build_dynamic_peer_map(target)
