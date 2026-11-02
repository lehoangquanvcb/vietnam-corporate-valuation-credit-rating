"""Kế thừa bảng chấm trong báo cáo mô phỏng đã có, không cố định bậc theo ticker."""
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import argparse
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

FACTOR_KEYS={'Hồ sơ Kinh doanh':'BusinessProfile','Vốn và Lợi nhuận':'CapitalEarnings',
             'Vị thế Rủi ro':'RiskPosition','Huy động vốn và Thanh khoản':'FundingLiquidity'}


def parse_bank_reference(content,ticker,period,source_name):
    from docx import Document
    from scripts.three_methodology_rating import NOTCH,move,label
    ticker=str(ticker).strip().upper()
    if not re.fullmatch(r'\d{4}-Q[1-4]',period):raise ValueError('Kỳ phải có dạng YYYY-Qn')
    doc=Document(BytesIO(content))
    text='\n'.join([p.text for p in doc.paragraphs]+[c.text for t in doc.tables for row in t.rows for c in row.cells])
    if not re.search(r'\('+re.escape(ticker)+r'\)',text):raise ValueError('Mã doanh nghiệp không khớp báo cáo')
    if 'ngân hàng' not in text.casefold():raise ValueError('Báo cáo không thuộc phương pháp ngân hàng')
    periods=Counter(re.findall(r'\b20\d{2}-Q[1-4]\b',text))
    if periods and periods.most_common(1)[0][0]!=period:raise ValueError('Kỳ khai báo không khớp kỳ tài chính chính trong báo cáo')
    candidates=[t for t in doc.tables if len(t.columns)==4 and 'Cấu phần' in t.rows[0].cells[0].text and any(k in t.rows[0].cells[2].text.casefold() for k in ['notch','nâng/hạ bậc'])]
    if len(candidates)!=1:raise ValueError('Cần đúng một bảng tổng kết cấu phần có cột nâng/hạ notch')
    rows=[[c.text.strip() for c in r.cells] for r in candidates[0].rows[1:]]
    parsed={};anchor=None;support=None;reported_sacp=None;reported_icr=None;reported_total=None;outlook=None
    seen=set()
    for row in rows:
        name,grade,notch,result=row;key=next((v for k,v in FACTOR_KEYS.items() if k.casefold()==name.casefold()),None)
        if key:
            if key in seen:raise ValueError('Cấu phần bị lặp: '+name)
            seen.add(key);g=re.sub(r'\s*\([^)]*\)\s*$','',grade).strip()
            g=next((v for v in NOTCH if v.casefold()==g.casefold()),None)
            if g is None or not re.fullmatch(r'[+-]?\d+',notch):raise ValueError('Đánh giá hoặc notch không hợp lệ: '+name)
            n=int(notch);allowed={'Yếu':{-2,-3},'Rất Yếu':{-4,-5}}.get(g,{NOTCH[g]})
            if key=='FundingLiquidity':allowed={min(1,v) for v in allowed}
            if n not in allowed:raise ValueError('Notch không khớp đánh giá: '+name)
            parsed[key]=g;parsed[key+'Notches']=n
        elif 'BICRA' in name or name=='Bậc neo':anchor=grade
        elif name=='Tổng điều chỉnh nội sinh':reported_total=int(notch);reported_sacp=result
        elif name=='Hỗ trợ bên ngoài':support=int(notch)
        elif name.casefold()=='kết quả xếp hạng':reported_icr=result;outlook=grade
    if set(FACTOR_KEYS.values())!=seen or anchor is None or support is None or reported_total is None:
        raise ValueError('Bảng nguồn thiếu cấu phần, bậc neo hoặc hỗ trợ')
    if label(anchor)!='vnA-' or not 0<=support<=8:raise ValueError('Bậc neo/hỗ trợ không phù hợp phương pháp hiện hành')
    total=sum(parsed[k+'Notches'] for k in FACTOR_KEYS.values())
    sacp=label(move(anchor,total));icr=label(move(sacp,support))
    if total!=reported_total or sacp!=label(reported_sacp) or icr!=label(reported_icr):
        raise ValueError('Tổng notch hoặc bậc tính lại không khớp bảng nguồn')
    return {'Ticker':ticker,'Period':period,**parsed,'ExternalSupportNotches':support,'Outlook':outlook,
            'Source':source_name,'SourceType':'REFERENCE_REPORT','SourceSHA256':sha256(content).hexdigest(),
            'SourceScorecard':rows,'ReferenceSACP':sacp,'ReferenceICR':icr,
            'Rationale':'Kế thừa các đánh giá và số bậc trong bảng tổng kết của báo cáo mô phỏng do người dùng cung cấp; tính lại từ bậc neo, không phải kết luận thẩm định mới.',
            'ImportedAt':datetime.now(timezone.utc).isoformat()}


def main():
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--ticker',required=True)
    p.add_argument('--period',required=True);p.add_argument('--output',default=str(ROOT/'config/bank_rating_references.json'))
    a=p.parse_args();source=Path(a.file)
    row=parse_bank_reference(source.read_bytes(),a.ticker,a.period,source.name)
    dest=Path(a.output);payload=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else {'methodology':'BANK_2026','assessments':[]}
    payload['assessments']=[r for r in payload['assessments'] if (r.get('Ticker'),r.get('Period'))!=(row['Ticker'],row['Period'])]+[row]
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:row[k] for k in ['Ticker','Period','ReferenceSACP','ReferenceICR','Source','SourceType']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
