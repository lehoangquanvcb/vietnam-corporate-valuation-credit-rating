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


def _candidate_pool(ticker: str, u: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    t = _norm_ticker(ticker)
    z = u[u.Ticker.eq(t)]
    if z.empty:
        return u[u.Ticker.eq(t)].copy(), 'Không xác định'
    r = z.iloc[0]
    et = str(r.get('EntityType','CORPORATE')).upper()
    same_type = u[u.EntityType.astype(str).str.upper().eq(et)].copy()
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
    if pool.empty or t not in set(pool.Ticker):
        return pd.DataFrame()
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
        return out
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
    p = select_dynamic_peers(ticker)
    if p.empty:
        return 'Nhóm tương đồng động (chưa đủ dữ liệu)'
    pool = str(p.iloc[0].get('PeerPool','toàn thị trường'))
    return f'Nhóm tương đồng động: {len(p)} DN từ {pool}'


def build_dynamic_peer_map():
    u = universe(); all_rows=[]; summaries=[]
    if u.empty:
        return pd.DataFrame()
    u=u.copy(); u['Ticker']=u.Ticker.map(_norm_ticker)
    # Load each Bronze snapshot once. This keeps full-market peer construction fast even for 1,000+ tickers.
    snap_cache={'BANK':_snapshot_for_type('BANK'),'SECURITIES':_snapshot_for_type('SECURITIES'),'CORPORATE':_snapshot_for_type('CORPORATE')}
    for i,t in enumerate(u.Ticker.astype(str),1):
        p = select_dynamic_peers(t, _u=u, _snap_cache=snap_cache)
        if len(p):
            all_rows.append(p)
            pool=str(p.iloc[0].get('PeerPool','toàn thị trường'))
            label=f'Nhóm tương đồng động: {len(p)} DN từ {pool}'
            summaries.append({'Ticker':_norm_ticker(t),'DynamicPeerGroup':label,
                              'DynamicPeerCount':len(p),'DynamicPeers':','.join(p.Ticker.astype(str))})
        else:
            summaries.append({'Ticker':_norm_ticker(t),'DynamicPeerGroup':'Nhóm tương đồng động (chưa đủ dữ liệu)',
                              'DynamicPeerCount':0,'DynamicPeers':''})
        if i % 100 == 0:
            print(f'Dynamic peer: {i}/{len(u)}')
    z = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    z.to_csv(DATA/'dynamic_peer_map.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(summaries).to_csv(DATA/'dynamic_peer_summary.csv', index=False, encoding='utf-8-sig')
    print(f'OK - dynamic peer map: {len(z)} relations for {len(u)} companies')
    return z


if __name__ == '__main__':
    build_dynamic_peer_map()
