"""Kiểm tra cấu trúc Word dùng chung bằng cách xuất file thực cho các mã."""
from pathlib import Path
from io import BytesIO
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from docx import Document
from docx.oxml.ns import qn
from scripts.professional_report import generate_docx
from scripts.report_evidence import build_pack


def inspect_document(ticker,data):
    doc=Document(BytesIO(data));paragraphs=[p.text for p in doc.paragraphs]
    joined='\n'.join(paragraphs);nodes=list(doc.element.body)
    positions=[i for i,n in enumerate(nodes) if n.xpath('.//w:drawing')]
    errors=[]
    headings=['THÔNG TIN TỔNG QUAN TỔ CHỨC PHÁT HÀNH','LỊCH SỬ TÀI CHÍNH 5 NĂM GẦN NHẤT','RỦI RO VĨ MÔ','RỦI RO NGÀNH']
    if not all(s in joined for s in headings):errors.append('Thiếu mục tổng quan/lịch sử/rủi ro')
    elif [joined.index(s) for s in headings]!=sorted(joined.index(s) for s in headings):errors.append('Sai thứ tự các mục')
    if 'Các trọng tâm tài chính' in joined:errors.append('Còn mục trọng tâm riêng')
    if doc.element.xpath('.//w:br[@w:type="page"]') or doc.element.xpath('.//w:pageBreakBefore'):
        errors.append('Còn ngắt trang bắt buộc')
    # Một cặp gồm biểu đồ năm và peer quý. Không cho bảng chen giữa.
    intermediate=sum(1 for a,b in zip(positions[::2],positions[1::2]) for n in nodes[a+1:b] if n.tag==qn('w:tbl'))
    if intermediate:errors.append('Còn bảng giữa biểu đồ')
    if not positions:errors.append('Chưa có dữ liệu để kiểm chứng biểu đồ')
    return {'Ticker':ticker,'Charts':len(positions),'IntermediateTables':intermediate,
            'SourceLinks':sum(r.reltype.endswith('/hyperlink') for r in doc.part.rels.values()),'Errors':errors}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tickers',nargs='+',default=['OCB','SSI','ABI','HPG'])
    args=parser.parse_args();checks=[]
    for ticker in args.tickers:
        try:
            pack=build_pack(ticker);row=inspect_document(ticker,generate_docx(ticker,'rating'))
            row.update(EntityType=pack['Type'],Period=pack['Period']);checks.append(row)
        except Exception as e:checks.append({'Ticker':ticker,'Errors':[type(e).__name__+': '+str(e)]})
    ok=not any(r['Errors'] for r in checks)
    print(json.dumps({'Result':'PASS' if ok else 'FAIL','Checks':checks,
        'Note':'Kiểm tra cấu trúc file đã xuất; không xác nhận lại số BCTC hay kết quả thẩm định. Bố cục từng trang cần Word/LibreOffice.'},ensure_ascii=False,indent=2))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
