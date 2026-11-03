"""Read-only check of funding changes on every bank in the local universe."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.universal_data import universe
from scripts.report_rating import rate_company
from scripts.three_methodology_rating import move,label


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args()
    rows=[];errors=[]
    banks=universe();banks=banks[banks.EntityType=='BANK'].Ticker.tolist()
    for ticker in banks:
        try:
            r=rate_company(ticker);n=r.get('FactorNotches',{}).get('Huy động vốn và Thanh khoản')
            if r.get('LiquidityAssumed'):
                assert r['Liquidity']=='Phù Hợp' and not r['AssessmentComplete']
                assert n is None or n<=0
            if r.get('DomesticCalibrationApplied'):
                assert label(move(r['RawICR'],r['DomesticCalibrationNotches']))==r['ICR']
            if ticker=='TCB':
                assert r['Funding']==r['Liquidity']=='Mạnh' and n==1
                assert r['CARInput']['Value']==.1495 and r['FundingObservations']['RegulatoryLDR']==.801
                assert r['SACP']=='vnA' and r['ICR']=='vnAA-'
            rows.append({'Ticker':ticker,'Period':r.get('Period'),'Funding':r.get('Funding'),
                         'Liquidity':r.get('Liquidity'),'LiquidityAssumed':r.get('LiquidityAssumed'),
                         'FundingLiquidityNotches':n,'SACP':r.get('SACP'),'ICR':r.get('ICR'),
                         'Status':r.get('RatingStatus')})
        except Exception as exc:errors.append({'Ticker':ticker,'Error':repr(exc)})
    report={'Build':'V8.138.0-BANK-FUNDING-REPORT','BankCount':len(banks),'Checks':rows,'Errors':errors,
            'Result':'PASS' if not errors else 'FAIL',
            'Note':'PASS xác nhận kiểm tra phần mềm; Mạnh của TCB là đánh giá cấu phần được chủ mô hình xác nhận. Các giả định thanh khoản không phải kết luận thẩm định.'}
    if args.output:Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=sys.stdout.encoding.lower()!='utf-8',indent=2))
    return int(bool(errors))


if __name__=='__main__':raise SystemExit(main())
