"""Read-only check of automatic report scores and all-sector routing."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.universal_data import universe
from scripts.report_rating import rate_company
from scripts.report_identity import report_filename


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tickers',nargs='+')
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--output')
    args=parser.parse_args();u=universe();rows=[];errors=[]
    allowed={'BANK','SECURITIES','INSURANCE','CORPORATE'}
    assert set(u.EntityType)<=allowed,'Có loại hình chưa được định tuyến'
    selected=args.tickers or (u.Ticker.tolist() if args.all else ['TCB','SSI','ABI','HPG','FPT','BVH'])
    for i,t in enumerate(selected):
        try:
            r=rate_company(t);has_grade=r.get('ICR') not in (None,'','N/A')
            if r.get('RatingOrigin')=='AUTO_RESEARCH' and has_grade:
                assert r.get('Scorecard') and r.get('Assumptions')
                assert r.get('AssessmentComplete') is False
                assert r.get('Anchor') not in (None,'N/A') and r.get('SCA') not in (None,'N/A')
            assert not r.get('DomesticCalibrationApplied'),'Không được hiệu chỉnh theo mức đích'
            if r.get('RatingBlocker')=='SCOPE':assert not has_grade
            if r.get('RatingStatus')=='INSUFFICIENT_DATA':
                assert not has_grade and not r.get('DataSufficientForAutoRating')
                assert r.get('MissingEvidence')
            rows.append({'Ticker':t,'Methodology':r.get('Methodology'),'Status':r.get('RatingStatus'),
                'Origin':r.get('RatingOrigin'),'Anchor':r.get('Anchor'),'SCA':r.get('SCA',r.get('SACP')),
                'ICR':r.get('ICR'),
                'ConditionalAssumptions':len(r.get('Assumptions',[])),
                'FileName':report_filename(t),'MissingEvidence':r.get('MissingEvidence')})
        except Exception as exc:errors.append({'Ticker':t,'Error':repr(exc)})
        if (i+1)%10==0:print(f'Checked {i+1}/{len(selected)}',flush=True)
    result={'Build':'V8.140.0-RATING-HEADER','RoutingTickers':len(u),'CheckedTickers':len(rows),
        'ByStatus':dict(Counter(r['Status'] for r in rows)),'Checks':rows,'Errors':errors,
        'Result':'PASS' if not errors else 'FAIL',
        'Note':'PASS xác nhận kiểm tra phần mềm. Bậc tự động có giả định, không phải thẩm định hoàn chỉnh; không tạo bậc khi thiếu dữ liệu cốt lõi hoặc ngoài phạm vi phương pháp.'}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:Path(args.output).write_text(text,encoding='utf-8')
    try:print(text)
    except UnicodeEncodeError:print(json.dumps(result,ensure_ascii=True,indent=2))
    return int(bool(errors))


if __name__=='__main__':raise SystemExit(main())
