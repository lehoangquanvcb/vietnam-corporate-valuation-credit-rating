"""Xuất và kiểm tra báo cáo Word thực tế của đúng project đang chạy."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import argparse
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))


def check(ticker='VCB',output=None):
    from docx import Document
    from scripts.report_evidence import build_pack,finite
    from scripts.multisector_report import generate_docx
    from scripts.three_methodology_rating import rate_company
    rr=rate_company(ticker)
    pack=build_pack(ticker);data=generate_docx(ticker,'rating');doc=Document(BytesIO(data))
    chart_metrics=sum(finite(x['Value']) or (len(x['History'])>0 and x['History'].Value.notna().any()) for x in pack['Items'].values())
    failures=[];xml=doc.element.xml
    if (ROOT/'VERSION.txt').read_text().strip()!='8.129.0':failures.append('VERSION.txt chưa phải 8.129.0')
    if len(doc.inline_shapes)!=2*chart_metrics:failures.append('Số biểu đồ không khớp danh mục có bằng chứng')
    if not all(s.width.mm>170 for s in doc.inline_shapes):failures.append('Biểu đồ chưa đủ chiều rộng')
    if doc.element.xpath('.//w:tbl//w:drawing'):failures.append('Còn biểu đồ nằm trong bảng ghép ngang')
    if not all(s in xml for s in ['4F9E1E','E6F3D8','Lato']):failures.append('Chưa nhận đúng mẫu xanh Lato')
    year=int(pack['Period'][:4])-(pack['Period'][-1]!='4')
    expected=[str(y) for y in range(year-4,year+1)]
    if any(list(x['History'].DisplayPeriod)!=expected for x in pack['Items'].values()):failures.append('Chuỗi lịch sử chưa đúng 5 năm tài chính')
    with ZipFile(BytesIO(data)) as z:
        fonts=[n for n in z.namelist() if n.startswith('word/fonts/')]
    if len(fonts)!=4:failures.append('Chưa nhúng đủ các phông Lato')
    histories={m:{'OwnCells':int(x['History'].Value.notna().sum()),'PeerMeanCells':int(x['History'].PeerMean.notna().sum())}
        for m,x in pack['Items'].items() if len(x['History'])}
    if output:
        out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    return {'ProjectPath':str(ROOT),'Ticker':ticker,'Period':pack['Period'],'ReportEngine':'8.129.0',
        'HistoryBasis':pack['Basis'],'AnnualYears':expected,'PeerBasis':'QUARTER',
        'Rating':{k:rr.get(k) for k in ['Anchor','InternalNotches','SACP','ExternalSupportNotches','ICR','Outlook','RatingOrigin','AssessmentSource','AssessmentPeriod']},
        'CurrentMetricsPresent':sum(finite(x['Value']) for x in pack['Items'].values()),'CurrentMetricsTotal':len(pack['Items']),
        'MissingMetrics':[m for m,x in pack['Items'].items() if not finite(x['Value'])],
        'Peers':pack['PeerUniverse'],'ChartCount':len(doc.inline_shapes),'EmbeddedFonts':len(fonts),'History':histories,
        'Failures':failures,'Result':'PASS' if not failures else 'FAIL',
        'Note':'Đã thực sự xuất Word và kiểm tra cấu trúc. Không xác nhận app Cloud đã triển khai hoặc mọi chỉ tiêu đều đủ; bố cục cần kiểm tra trực quan khi đổi dữ liệu.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ticker',default='VCB');parser.add_argument('--output');args=parser.parse_args()
    try:result=check(args.ticker.upper(),args.output)
    except Exception as exc:result={'Result':'FAIL','Error':f'{type(exc).__name__}: {exc}'}
    try:print(json.dumps(result,ensure_ascii=False,indent=2))
    except UnicodeEncodeError:print(json.dumps(result,ensure_ascii=True,indent=2))
    return 0 if result['Result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
