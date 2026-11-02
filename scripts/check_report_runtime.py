"""Kiểm tra cấu trúc cho toàn danh mục và bằng chứng cho các mã được chọn.

Chạy --all để kiểm tra gói bằng chứng mọi mã; thao tác chỉ đọc số liệu cục bộ.
Không đồng nhất kiểm tra phần mềm với xác nhận dữ liệu hay thẩm định XHTN.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import argparse,json
from scripts.universal_data import universe
from scripts.report_methodology import GROUPS
from scripts.report_evidence import build_pack,narrative,finite


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--tickers',nargs='+')
    parser.add_argument('--output')
    args=parser.parse_args();u=universe()
    invalid=u[~u.EntityType.isin(GROUPS)]
    if len(invalid):raise ValueError('Loại hình chưa có mẫu: '+', '.join(invalid.Ticker))
    selected=args.tickers or (u.Ticker.tolist() if args.all else ['TCB','SSI','FPT','ABI','BVH'])
    rows=[];errors=[]
    for i,t in enumerate(selected):
        try:
            p=build_pack(t);active=0;gaps=0
            if p['Period']:
                end=int(p['Period'][:4])-(p['Period'][-1]!='4')
                expected=[str(y) for y in range(end-4,end+1)]
                for m,x in p['Items'].items():
                    assert x['History'].DisplayPeriod.tolist()==expected,(t,m,'Không phải 5 năm hoàn chỉnh')
                    assert t not in [r['Ticker'] for r in x['Peers']],(t,m,'Peer có chính doanh nghiệp')
                    if finite(x['Value']) or x['History'].Value.notna().any():
                        n=narrative(p,m);assert n['History'] and n['Peers'] and (n['Meaning'] or n['Conclusion']),(t,m)
                        active+=1
                    if not finite(x['Value']):gaps+=1
            rows.append({'Ticker':t,'Type':p['Type'],'Period':p['Period'],'AnnualYears':5,
                         'ActiveMetrics':active,'ExpectedCharts':active*2,'MissingLatestMetrics':gaps,
                         'PeerCandidates':len(p['PeerUniverse'])})
        except Exception as exc:errors.append({'Ticker':t,'Error':str(exc)})
        if (i+1)%10==0:print(f'Checked {i+1}/{len(selected)} tickers',flush=True)
    result={'Build':'V8.132.0-RATING-FIRST-CHARTS','RoutingTickers':len(u),'RoutingByType':u.groupby('EntityType').size().to_dict(),
            'EvidenceTickers':len(rows),'Checks':rows,'Errors':errors,'Result':'PASS' if not errors else 'FAIL',
            'Note':'PASS kiểm tra phần mềm và gói bằng chứng; không xác nhận đủ dữ liệu hay bậc xếp hạng cho mọi mã.'}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:Path(args.output).write_text(text,encoding='utf-8')
    try:print(text)
    except UnicodeEncodeError:print(json.dumps(result,ensure_ascii=True,indent=2))
    return int(bool(errors))


if __name__=='__main__':raise SystemExit(main())
