"""Cập nhật một lần cho toàn thị trường, tiếp tục được sau khi gián đoạn."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.industry_classifier import atomic_csv
from scripts.financial_evidence import _paths, normalize_raw, period_date
import pandas as pd

DATA = ROOT/'data'
STATE = DATA/'market_peer_refresh_state.json'


def required_raw_paths(ticker, entity_type):
    paths = _paths(ticker, entity_type, ROOT)
    # Parser ngân hàng tải balance_q, income_q, ratio_q; không tải cashflow.
    return [p for p in paths if entity_type != 'BANK' or '_cashflow' not in p.name]


def raw_status(ticker, entity_type):
    """Không coi tệp rỗng hoặc snapshot cache là raw đã tải thành công."""
    periods = []
    for path in required_raw_paths(ticker, entity_type):
        if not path.exists() or path.stat().st_size == 0:
            return False, ''
        try:
            raw = normalize_raw(pd.read_csv(path), source=str(path))
            valid = raw.dropna(subset=['Value'])
            if valid.empty:
                return False, ''
            periods.extend(valid.Period.tolist())
        except (OSError, ValueError, KeyError, pd.errors.ParserError):
            return False, ''
    dated = [(period_date(p), p) for p in periods if pd.notna(period_date(p))]
    return bool(dated), max(dated)[1] if dated else ''


def needs_refresh(ticker, entity_type, state, max_age_days, force=False, now=None):
    now = time.time() if now is None else now
    ok, _ = raw_status(ticker, entity_type)
    if force or not ok:
        return True
    # Mốc này là ngày tải thành công, không phải kỳ BCTC hay xác nhận có quý mới.
    record = state.get(ticker, {})
    if record.get('Status') != 'DOWNLOADED':
        return True
    return now - float(record.get('DownloadedAtEpoch', 0)) >= max_age_days*86400


def save_state(state):
    DATA.mkdir(parents=True, exist_ok=True)
    temp = STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(STATE)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Cập nhật phân ngành + dữ liệu peer cho TOÀN BỘ mã, không cần truyền ticker.')
    ap.add_argument('--catalog-only', action='store_true', help='Chỉ cập nhật listing/ICB và chọn peer từ dữ liệu sẵn có')
    ap.add_argument('--offline', action='store_true', help='Chỉ tạo peer map từ dữ liệu local, không gọi Vnstock')
    ap.add_argument('--force', action='store_true', help='Tải lại tài chính mọi mã đang hoạt động')
    ap.add_argument('--max-age-days', type=float, default=7, help='Tải lại khi lần tải thành công đã quá số ngày này')
    ap.add_argument('--ticker-delay', type=float, default=3)
    args = ap.parse_args(argv)
    if args.max_age_days < 0 or args.ticker_delay < 0:
        ap.error('Số ngày và thời gian chờ phải không âm.')
    if not args.offline:
        from scripts.discover_listed_universe import main as discover
        from scripts.industry_classifier import apply_industry_classification
        discover()
        apply_industry_classification()
    from scripts.universal_data import universe
    u = universe().drop_duplicates('Ticker')
    if u.empty:
        raise RuntimeError('Danh mục mã trống; chưa thể xây peer toàn thị trường.')
    try:
        state = json.loads(STATE.read_text(encoding='utf-8'))
    except FileNotFoundError:
        state = {}
    failures = []
    if not args.offline and not args.catalog_only:
        os.environ['VNSTOCK_WORKERS'] = '1'
        targets = [r for r in u.to_dict('records') if needs_refresh(r['Ticker'], r['EntityType'], state, args.max_age_days, args.force)]
        print(f'Cập nhật chung: {len(targets)}/{len(u)} mã cần tải. Có thể chạy lại cùng lệnh để tiếp tục.', flush=True)
        for i, row in enumerate(targets, 1):
            t, et = row['Ticker'], row['EntityType']
            command = (['scripts/refresh_vnstock.py', '--mode', 'fundamentals', '--tickers', t, '--workers', '1']
                       if et == 'BANK' else ['scripts/refresh_vnstock_multisector.py', t, '--workers', '1', '--ticker-delay', str(args.ticker_delay)])
            print(f'[{i}/{len(targets)}] {t}', flush=True)
            started = time.time()
            rc = subprocess.call([sys.executable, *command], cwd=ROOT)
            valid, latest = raw_status(t, et)
            # Có đủ tệp từ lần chạy trước chưa chứng minh API vừa cập nhật thành công.
            updated = all(p.exists() and p.stat().st_mtime >= started-2 for p in required_raw_paths(t, et))
            ok = rc == 0 and valid and updated
            state[t] = {'Status':'DOWNLOADED' if ok else 'FAILED_OR_INCOMPLETE',
                        'LatestObservedPeriod':latest, 'DownloadedAtEpoch':time.time() if ok else 0,
                        'CheckedAt':datetime.now(timezone.utc).isoformat(), 'ProcessCode':rc}
            if not ok:
                failures.append(t)
            save_state(state)
            if i < len(targets):
                time.sleep(args.ticker_delay)
    from scripts.dynamic_peer_engine import build_dynamic_peer_map
    build_dynamic_peer_map()
    active = set(u.Ticker)
    audit = pd.DataFrame([dict(Ticker=t, **row) for t,row in state.items() if t in active])
    if len(audit):
        atomic_csv(audit, DATA/'market_peer_refresh_audit.csv')
    if failures:
        print('CHƯA ĐỦ DỮ LIỆU: '+','.join(failures), flush=True)
        print('Danh sách peer đã tạo cho toàn bộ mã; chạy lại cùng lệnh để thử lại các mã lỗi.', flush=True)
        return 2
    print('Hoàn tất danh mục peer toàn thị trường. Báo cáo tự chọn peer khi đổi mã.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
