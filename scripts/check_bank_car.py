"""Kiểm kê CAR đã cập nhật vào ứng dụng; không suy ra tình trạng công bố."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts.financial_evidence import at_period, rating_car_record
from scripts.universal_data import universe


def audit(period='2026-Q2'):
    u = universe()
    rows = []
    for ticker in sorted(u.loc[u.EntityType.eq('BANK'), 'Ticker'].unique()):
        current = at_period(ticker, 'BANK', period, 'QUARTER').get('CAR', {})
        r = rating_car_record(ticker, period)
        ok = r.get('Status') == 'OK' and r.get('Value') is not None
        kind = r.get('SourceKind') or 'AVAILABLE_FEED'
        status = ('FALLBACK_2025_' if r.get('FallbackUsed') else '')+kind if ok else 'SOURCE_ERROR' if r.get('Status')=='ERROR' else 'NOT_YET_INGESTED'
        rows.append({'Ticker': ticker, 'Period': period, 'SourcePeriod': r.get('Period'),
                     'CARPercent': round(r['Value'] * 100, 6) if ok else None,
                     'Status': status, 'SourceKind': kind if ok else None,
                     'CurrentPeriodAvailable': current.get('Status')=='OK' and current.get('Value') is not None,
                     'FallbackUsed': bool(r.get('FallbackUsed')), 'InputText':r.get('InputText'),
                     'Scope': r.get('Scope'), 'Regime': r.get('Regime'),
                     'SourceURL': r.get('SourceURL'), 'SourcePage': r.get('SourcePage'),
                     'SourceReference':r.get('SourceReference'),
                     'Note': r.get('Note', r.get('Reason', ''))})
    missing = [r['Ticker'] for r in rows if r['CARPercent'] is None]
    return {'Build': 'V8.137.0-DOMESTIC-BANK-RATING', 'Period': period, 'BankCount': len(rows),
            'VerifiedDisclosures': sum(r['Status'] == 'VERIFIED_DISCLOSURE' for r in rows),
            'CurrentPeriodAvailable':sum(r['CurrentPeriodAvailable'] for r in rows),
            'Fallback2025':sum(r['FallbackUsed'] for r in rows),
            'UserInputsUsed':sum(r['SourceKind'] in {'USER_PROVIDED','USER_ESTIMATE'} for r in rows),
            'Available': len(rows) - len(missing), 'PendingIngestion': missing,
            'Result': 'COMPLETE' if not missing else 'PARTIAL', 'Checks': rows,
            'Note': 'Available là CAR dùng được để tính điểm, gồm số cuối 2025 theo chỉ định cho kỳ 2026-Q2. CurrentPeriodAvailable chỉ đếm đúng kỳ. PARTIAL không phải kết luận ngân hàng chưa công bố CAR. SourceKind phân biệt nguồn đối chiếu, người dùng và ước tính.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--period', default='2026-Q2')
    parser.add_argument('--output')
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    result = audit(args.period)
    if args.output: Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 2 if args.require_complete and result['PendingIngestion'] else int(any(r['Status'] == 'SOURCE_ERROR' for r in result['Checks']))


if __name__ == '__main__': raise SystemExit(main())
