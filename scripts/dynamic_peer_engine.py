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
    'INSURANCE': {'TotalAssets':.4,'Equity':.3,'ROE':.2,'ROA':.1},
    'CORPORATE': {
        'TotalAssets': .23, 'Revenue': .20, 'Equity': .10, 'ROE': .11, 'ROA': .08,
        'DebtEquity': .13, 'CurrentRatio': .07, 'AssetTurnover': .05, 'CashAssets': .03,
    },
}


# V8.123: một danh mục dùng chung, không prepare riêng cho từng doanh nghiệp.
import hashlib
import json
from functools import lru_cache
from threading import RLock
from scripts.industry_classifier import clean, code, atomic_csv
from scripts.financial_evidence import signature, metric_evidence, repair_snapshot

ENGINE_VERSION = '8.123.0'
OUTPUT_COLUMNS = ['TargetTicker','Ticker','PeerRank','SimilarityScore','DistanceScore',
    'MetricsCoverage','PeerPool','SimilarityBasis','DataStatus','IndustryStatus',
    'CompanyName','LegalName','Sector','EntityType']


def _norm_ticker(value):
    return str(value).upper().strip()


def _normalized_universe(frame):
    u = frame.copy()
    if u.empty:
        return u
    u['Ticker'] = u.Ticker.map(_norm_ticker)
    if 'Active' in u:
        u = u[pd.to_numeric(u.Active, errors='coerce').fillna(1).eq(1)].copy()
    u = u.drop_duplicates('Ticker', keep='last')
    u['EntityType'] = u.EntityType.astype(str).str.upper()
    for lv in range(1, 5):
        col = f'ICBCode{lv}'
        u[col] = u[col].map(code) if col in u else ''
    # Nhận diện cache từ parser cũ gán một mã cho cả bốn cấp; không gọi là ICB4.
    collapsed = u.ICBCode1.ne('') & u[[f'ICBCode{i}' for i in (2,3,4)]].eq(u.ICBCode1, axis=0).all(axis=1)
    u['IndustryStatus'] = np.where(collapsed, 'LEGACY_ICB_REFRESH_REQUIRED', 'ICB_OR_SECTOR')
    u.loc[collapsed, [f'ICBCode{i}' for i in range(1,5)]] = ''
    return u


def _overrides():
    from scripts.universal_data import read_csv
    o = read_csv(OVERRIDE_FILE)
    if not {'TargetTicker','PeerTicker'}.issubset(o.columns):
        return pd.DataFrame(columns=['TargetTicker','PeerTicker'])
    o = o.copy()
    for c in ['TargetTicker','PeerTicker']:
        o[c] = o[c].map(_norm_ticker)
    if 'Active' in o:
        o = o[pd.to_numeric(o.Active, errors='coerce').fillna(1).eq(1)]
    o['_priority'] = pd.to_numeric(o['Priority'], errors='coerce').fillna(9999) if 'Priority' in o else 9999
    return o.sort_values(['_priority','PeerTicker']).drop_duplicates(['TargetTicker','PeerTicker'])


def _override_pool(ticker, u, overrides=None):
    o = _overrides() if overrides is None else overrides
    wanted = [ticker] + o.loc[o.TargetTicker.eq(ticker),'PeerTicker'].tolist()
    order = {t: i for i,t in enumerate(dict.fromkeys(wanted))}
    pool = u[u.Ticker.isin(order)].copy()
    if len(pool) < 2:
        return pool.iloc[0:0], None
    return pool.assign(_order=pool.Ticker.map(order)).sort_values('_order').drop(columns='_order'), 'Nhóm peer chuyên ngành (analyst override)'


def _candidate_pool(ticker, u, overrides=None):
    t = _norm_ticker(ticker)
    u = _normalized_universe(u) if 'IndustryStatus' not in u else u
    z = u[u.Ticker.eq(t)]
    if z.empty:
        return z, 'Không tìm thấy mã trong danh mục đang hoạt động'
    r = z.iloc[0]
    same = u[u.EntityType.eq(r.EntityType)]
    if r.EntityType == 'CORPORATE':
        pool, label = _override_pool(t, same, overrides)
        if label:
            return pool, label
    if r.EntityType == 'BANK':
        return same, 'Ngân hàng niêm yết/ĐKGD'
    if r.EntityType == 'SECURITIES':
        return same, 'Công ty chứng khoán niêm yết/ĐKGD'
    if r.EntityType == 'INSURANCE':
        from scripts.financial_evidence import insurance_reporting_subtype, comparable_model
        scope = insurance_reporting_subtype(r)
        return same[same.apply(lambda p: comparable_model(r, p), axis=1)], 'Định giá bảo hiểm cùng phạm vi BCTC ' + scope
    # Ngành nhỏ vẫn giữ; chỉ lùi cấp khi không có bất kỳ peer nào ở cấp chi tiết.
    first = None
    for lv in (4, 3, 2):
        val = code(r.get(f'ICBCode{lv}'))
        if not val:
            continue
        pool = same[same[f'ICBCode{lv}'].eq(val)]
        label = f'ICB cấp {lv}: {clean(r.get(f"ICBName{lv}")) or val} ({val})'
        if first is None:
            first = (pool, label)
        if len(pool) > 1:
            return pool, label
    if first is not None:
        return first  # Không tự ghép toàn thị trường để đủ 5/10 peer.
    sector = clean(r.get('Sector'))
    if sector and sector.lower() not in {'chưa phân loại','unknown','n/a','none','nan'}:
        label = 'Ngành hiện có: ' + sector + ' (chưa có ICB chi tiết)'
        return same[same.Sector.astype(str).eq(sector)], label
    return z, 'Thiếu phân ngành ICB; chưa xác định được peer'


@lru_cache(maxsize=16384)
def _file_digest(sig):
    if not sig[1]:
        return 'MISSING'
    digest = hashlib.sha256()
    with Path(sig[0]).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def peer_source_fingerprint():
    # Hash nội dung dùng lại được sau git clone/đổi Windows -> Cloud.
    # Stat chỉ dùng để tránh đọc lại tệp không đổi trong cùng tiến trình.
    paths = [('config/'+p, CFG/p) for p in ['company_universe.csv','vnstock_industry_map.csv','dynamic_peer_overrides.csv',
        'manual_financial_inputs.csv','raw_period_basis.csv','insurance_entities.csv','insurance_metric_inputs.csv']]
    paths += [('data/'+p, DATA/p) for p in ['company_snapshot.csv','bank_snapshot.csv','bank_history_long.csv','securities_capital_ratio_master.csv']]
    paths += [('data/raw/'+p.name, p) for p in sorted((DATA/'raw').glob('*.csv'))]
    return hashlib.sha256(repr((ENGINE_VERSION, tuple((name,_file_digest(signature(p))) for name,p in paths))).encode()).hexdigest()


class _Catalog:
    def __init__(self, u, snap_cache=None):
        self.u = _normalized_universe(u)
        self.overrides = _overrides()
        self.metadata = self.u.set_index('Ticker').to_dict('index') if len(self.u) else {}
        # Đọc hai bảng tổng hợp một lần cho cả universe, bao gồm INSURANCE.
        frames = list(snap_cache.values()) if snap_cache is not None else [bank_snapshot(), generic_snapshot()]
        self.base = {}
        for frame in frames:
            if frame is not None and len(frame) and 'Ticker' in frame:
                for r in frame.to_dict('records'):
                    self.base[_norm_ticker(r['Ticker'])] = r
        self.evidence = {}
        self.pools = {}
        self.results = {}
        self.lock = RLock()

    def pool(self, t):
        if t not in self.pools:
            self.pools[t] = _candidate_pool(t, self.u, self.overrides)
        return self.pools[t]

    def snapshot(self, t):
        if t not in self.evidence:
            meta = dict(self.metadata.get(t, {}), Ticker=t)
            base = dict(self.base.get(t, {}))
            base.update(meta)
            out = repair_snapshot(t, meta.get('EntityType','CORPORATE'), base, root=ROOT)
            out.update(meta)
            self.evidence[t] = out
        return self.evidence[t]


@lru_cache(maxsize=2)
def _catalog(fingerprint):
    return _Catalog(universe())


def _selection(t, max_peers, catalog):
    key = (t, max_peers)
    if key in catalog.results:
        return catalog.results[key].copy()
    pool, label = catalog.pool(t)
    if pool.empty or max_peers <= 0:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    weights = WEIGHTS.get(str(pool.iloc[0].EntityType), WEIGHTS['CORPORATE'])
    evidence = {ct: catalog.snapshot(ct) for ct in pool.Ticker}
    target = evidence[t]
    # Xếp hạng vector hóa, chỉ so sánh dữ liệu có chứng cứ cùng kỳ/cơ sở tính.
    distances = pd.Series(0., index=pool.Ticker)
    coverage = distances.copy()
    reasons = {ct: [] for ct in pool.Ticker}
    for metric, weight in weights.items():
        te = metric_evidence(target, metric)
        if te['Status'] != 'OK' or not te['Period'] or not te['Basis']:
            continue
        values = {}
        for ct, snap in evidence.items():
            ce = metric_evidence(snap, metric)
            if ce['Status'] == 'OK' and ce['Period'] == te['Period'] and ce['Basis'] == te['Basis']:
                values[ct] = ce['Value']
        values = pd.to_numeric(pd.Series(values), errors='coerce').replace([np.inf,-np.inf], np.nan).dropna()
        if len(values) < 2 or t not in values:
            continue
        ranks = values.rank(method='max', pct=True)
        d = (ranks - ranks[t]).abs()
        distances.loc[d.index] += weight * d
        coverage.loc[d.index] += weight
        for ct in d.index:
            reasons[ct].append(metric)
    rows = []
    for row in pool.to_dict('records'):
        ct = row['Ticker']
        if ct == t:
            continue
        used = float(coverage[ct])
        distance = float(distances[ct]/used + .18*(1-used)) if used > 0 else np.nan
        available = any(metric_evidence(evidence[ct], m)['Status'] == 'OK' for m in weights)
        status = 'COMPARABLE' if used else ('NO_COMMON_PERIOD_OR_METRICS' if available else 'MISSING_VERIFIED_DATA')
        rows.append(dict(row, TargetTicker=t, SimilarityScore=max(0.,1-distance) if used else np.nan,
            DistanceScore=distance, MetricsCoverage=used, PeerPool=label, DataStatus=status,
            SimilarityBasis=', '.join(reasons[ct]) if used else 'Cùng ngành; chưa đủ dữ liệu cùng kỳ để xếp hạng'))
    out = pd.DataFrame(rows)
    if len(out):
        # Giữ peer metadata khi thiếu raw; không tạo score giả, thứ tự hòa theo ticker.
        out = out.sort_values(['DistanceScore','Ticker'], na_position='last').head(max_peers).reset_index(drop=True)
        out['PeerRank'] = np.arange(1, len(out)+1)
    out = out.reindex(columns=OUTPUT_COLUMNS)
    catalog.results[key] = out
    return out.copy()


@lru_cache(maxsize=2)
def _persisted(fingerprint, map_signature, manifest_signature):
    try:
        manifest = json.loads((DATA/'dynamic_peer_manifest.json').read_text(encoding='utf-8'))
        if manifest.get('Fingerprint') != fingerprint or manifest.get('EngineVersion') != ENGINE_VERSION:
            return None
        p = pd.read_csv(DATA/'dynamic_peer_map.csv')
        return {t: g.copy() for t,g in p.groupby('TargetTicker')}
    except (OSError, ValueError, KeyError):
        return None


def select_dynamic_peers(ticker, max_peers=MAX_PEERS, _u=None, _snap_cache=None):
    t = _norm_ticker(ticker)
    max_peers = max(0, int(max_peers))
    if _u is not None or _snap_cache is not None:
        return _selection(t, max_peers, _Catalog(_u if _u is not None else universe(), _snap_cache))
    fingerprint = peer_source_fingerprint()
    saved = _persisted(fingerprint, signature(DATA/'dynamic_peer_map.csv'), signature(DATA/'dynamic_peer_manifest.json'))
    if saved is not None and max_peers <= MAX_PEERS:
        return saved.get(t, pd.DataFrame(columns=OUTPUT_COLUMNS)).head(max_peers).copy()
    catalog = _catalog(fingerprint)
    with catalog.lock:
        return _selection(t, max_peers, catalog)


def _select_dynamic_peers_uncached(ticker, max_peers=MAX_PEERS, _u=None, _snap_cache=None):
    return _selection(_norm_ticker(ticker), max_peers, _Catalog(_u if _u is not None else universe(), _snap_cache))


def dynamic_peer_tickers(ticker, include_target=True, max_peers=MAX_PEERS):
    t = _norm_ticker(ticker)
    return ([t] if include_target else []) + select_dynamic_peers(t, max_peers).Ticker.tolist()


def dynamic_peer_label(ticker):
    p = select_dynamic_peers(ticker)
    if len(p):
        return f'Nhóm tương đồng tự động: {len(p)} DN từ {p.iloc[0].PeerPool}'
    catalog = _catalog(peer_source_fingerprint())
    return catalog.pool(_norm_ticker(ticker))[1]


def peer_catalog_summary():
    catalog = _catalog(peer_source_fingerprint())
    rows = []
    for t in catalog.metadata:
        pool, label = catalog.pool(t)
        rows.append({'Ticker':t, 'EligiblePeerCount':max(0,len(pool)-1), 'PeerPool':label,
                     'IndustryStatus':catalog.metadata[t].get('IndustryStatus','')})
    return pd.DataFrame(rows)


def build_dynamic_peer_map(target_ticker=None):
    fingerprint = peer_source_fingerprint()
    catalog = _catalog(fingerprint)
    targets = [_norm_ticker(target_ticker)] if target_ticker else list(catalog.metadata)
    parts, summaries = [], []
    with catalog.lock:
        for i,t in enumerate(targets,1):
            p = _selection(t, MAX_PEERS, catalog)
            pool, label = catalog.pool(t)
            parts.append(p)
            summaries.append({'Ticker':t, 'DynamicPeerGroup':label, 'EligiblePeerCount':max(0,len(pool)-1),
                'DynamicPeerCount':len(p), 'ComparablePeerCount':int(p.DataStatus.eq('COMPARABLE').sum()),
                'DynamicPeers':','.join(p.Ticker), 'IndustryStatus':catalog.metadata.get(t,{}).get('IndustryStatus','UNKNOWN')})
            if i % 100 == 0:
                print(f'Peer toàn thị trường: {i}/{len(targets)}', flush=True)
    result = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=OUTPUT_COLUMNS)
    summary = pd.DataFrame(summaries)
    manifest_path = DATA/'dynamic_peer_manifest.json'
    # Không để cache một mã được nhận nhầm là cache đã xây cho toàn thị trường.
    if manifest_path.exists():
        manifest_path.unlink()
    if target_ticker:
        for name, field, frame in [('dynamic_peer_map.csv','TargetTicker',result), ('dynamic_peer_summary.csv','Ticker',summary)]:
            try:
                old = pd.read_csv(DATA/name)
                old = old[~old[field].isin(targets)]
            except (OSError, ValueError, KeyError):
                old = pd.DataFrame()
            atomic_csv(pd.concat([old,frame], ignore_index=True), DATA/name)
    else:
        atomic_csv(result, DATA/'dynamic_peer_map.csv')
        atomic_csv(summary, DATA/'dynamic_peer_summary.csv')
        if peer_source_fingerprint() != fingerprint:
            raise RuntimeError('Nguồn thay đổi trong lúc tạo peer map; chạy lại để tạo cache nhất quán.')
        temp = manifest_path.with_suffix('.tmp')
        temp.write_text(json.dumps({'EngineVersion':ENGINE_VERSION,'Fingerprint':fingerprint,'TargetCount':len(targets)}, indent=2), encoding='utf-8')
        temp.replace(manifest_path)
    print(f'OK - đã xử lý {len(targets)} mã; peer thiếu số liệu vẫn có trong danh mục.')
    return result


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv)>1 and sys.argv[1].upper() not in {'ALL','--ALL'} else None
    build_dynamic_peer_map(target)
