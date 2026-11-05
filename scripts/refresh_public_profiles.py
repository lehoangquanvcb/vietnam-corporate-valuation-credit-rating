"""Lưu hồ sơ công khai cho toàn bộ danh mục, có thể chạy tiếp sau gián đoạn."""
from pathlib import Path
import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts.public_company_profile import fetch_public_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tickers', nargs='*')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--output', default='docs/public_profile_coverage_v8_141.json')
    args = parser.parse_args()
    with (ROOT/'config/company_universe.csv').open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: (r['EntityType']=='CORPORATE', r['Ticker']))
    tickers = args.tickers or [r['Ticker'] for r in rows]
    if args.limit: tickers = tickers[:args.limit]
    def run(t):
        profile = fetch_public_profile(t)
        time.sleep(.25)
        return {'Ticker':t, 'Available':bool(profile)}
    result = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for row in pool.map(run, tickers):
            result.append(row)
            if len(result) % 50 == 0:
                print(json.dumps({'checked':len(result), 'available':sum(r['Available'] for r in result)}), flush=True)
    target = ROOT / args.output; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({'Checked':len(result), 'Available':sum(r['Available'] for r in result),
        'Missing':[r['Ticker'] for r in result if not r['Available']]}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(target.read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__': main()
