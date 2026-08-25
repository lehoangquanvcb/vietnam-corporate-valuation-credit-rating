import numpy as np
from pathlib import Path
from io import BytesIO
import math, pandas as pd, matplotlib.pyplot as plt
from matplotlib import font_manager
from docx import Document
from docx.shared import Pt, Mm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from scripts.universal_data import get_company,get_snapshot,entity_history,industry_metric_history,industry_label,num
from scripts.multisector_valuation import valuation
from scripts.three_methodology_rating import rate_company
from scripts.rating_committee_engine import committee_pack
from scripts.fair_value_range import fair_value_range
from scripts.valuation_triangulation import triangulate
from scripts.rating_evidence_engine import rating_evidence
from scripts.intelligent_analyst import analyze as intelligent_analyze
from scripts.sector_kpi_engine import sector_kpi_table
from scripts.sector_templates import get_template
from scripts.methodology_kpi_engine import methodology_kpi_table, metric_list, LABELS as METH_LABELS, PCT as METH_PCT, MULT as METH_MULT

ROOT=Path(__file__).resolve().parents[1]

VI_METRIC={
'TotalAssets':'Tổng tài sản','Revenue':'Doanh thu','NPAT':'Lợi nhuận sau thuế','ROE':'ROE','ROA':'ROA',
'NPL':'Tỷ lệ nợ xấu','CAR':'CAR','CASA':'CASA','LDR':'LDR','NIM':'NIM','PB':'P/B','PE':'P/E',
'DebtEquity':'Nợ/VCSH','CurrentRatio':'Hệ số thanh toán hiện hành','AvailableCapitalRatio':'Tỷ lệ vốn khả dụng'
}
PCT={'ROE','ROA','NPL','CAR','CASA','LDR','NIM','AvailableCapitalRatio'}
MULT={'PB','PE','DebtEquity','CurrentRatio'}

def vi(x,d=1):
    v=num(x)
    if v is None:return 'N/A'
    return f'{v:,.{d}f}'.replace(',','X').replace('.',',').replace('X','.')
def pct(x): return 'N/A' if num(x) is None else vi(num(x)*100,1)+'%'
def mult(x): return 'N/A' if num(x) is None else vi(x,2)+'x'
def price(x): return 'N/A' if num(x) is None else vi(num(x)*1000,0)+' đồng/cp'
def metric_fmt(metric,x):
    if metric in PCT:return pct(x)
    if metric in MULT:return mult(x)
    return vi(x,1)

def _font():
    try:return font_manager.findfont('Lato',fallback_to_default=False)
    except:return 'DejaVu Sans'

def _period_date(v):
    s=str(v)
    for q,m,d in [('Q1','03','31'),('Q2','06','30'),('Q3','09','30'),('Q4','12','31')]:
        s=s.replace(q,f'-{m}-{d}')
    return pd.to_datetime(s,errors='coerce')

def chart_metric(ticker,metric,title=None,percent=None):
    h=entity_history(ticker); p=industry_metric_history(ticker,metric)
    fig,ax=plt.subplots(figsize=(8.4,3.15))
    plt.rcParams.update({'font.family':'Lato','font.size':10})
    z=pd.DataFrame()
    if len(h):
        z=h[h.Metric.astype(str).eq(metric)].copy()
        z['Date']=z.Period.map(_period_date); z['Value']=pd.to_numeric(z.Value,errors='coerce')
        z=z.dropna(subset=['Date','Value']).sort_values('Date').drop_duplicates('Date',keep='last')
        if len(z): ax.plot(z.Date,z.Value,marker='o',linewidth=1.8,label=str(ticker).upper())
    if len(p):
        pp=p.copy()
        if 'PeriodDate' in pp: pp=pp.sort_values('PeriodDate')
        ax.plot(pp.PeriodDate,pp.IndustryMean,linestyle='--',linewidth=1.6,label=industry_label(ticker))
    ax.set_title(title or f"{VI_METRIC.get(metric,metric)} - doanh nghiệp và trung bình ngành",fontsize=11)
    ax.grid(alpha=.2); ax.legend(fontsize=8,loc='best')
    if percent is None: percent=metric in PCT
    if percent: ax.yaxis.set_major_formatter(lambda v,pos:(f'{v*100:.1f}%').replace('.',','))
    fig.autofmt_xdate(rotation=0); fig.tight_layout()
    bio=BytesIO(); fig.savefig(bio,dpi=180,bbox_inches='tight'); plt.close(fig); bio.seek(0); return bio

def _set_cell_shading(cell,fill):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),fill); tcPr.append(shd)

def _set_repeat_table_header(row):
    trPr=row._tr.get_or_add_trPr(); tblHeader=OxmlElement('w:tblHeader'); tblHeader.set(qn('w:val'),'true'); trPr.append(tblHeader)

def _set_cell_margins(cell,top=60,start=70,bottom=60,end=70):
    tc=cell._tc; tcPr=tc.get_or_add_tcPr(); tcMar=tcPr.first_child_found_in('w:tcMar')
    if tcMar is None: tcMar=OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for m,v in [('top',top),('start',start),('bottom',bottom),('end',end)]:
        node=tcMar.find(qn('w:'+m))
        if node is None: node=OxmlElement('w:'+m); tcMar.append(node)
        node.set(qn('w:w'),str(v)); node.set(qn('w:type'),'dxa')

def _style_doc(doc):
    sec=doc.sections[0]; sec.page_height=Mm(297); sec.page_width=Mm(210)
    sec.top_margin=Mm(16); sec.bottom_margin=Mm(15); sec.left_margin=Mm(18); sec.right_margin=Mm(16)
    for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3']:
        st=doc.styles[name]; st.font.name='Lato'
        st._element.rPr.rFonts.set(qn('w:ascii'),'Lato'); st._element.rPr.rFonts.set(qn('w:hAnsi'),'Lato'); st._element.rPr.rFonts.set(qn('w:eastAsia'),'Lato')
    n=doc.styles['Normal']; n.font.size=Pt(11); n.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    n.paragraph_format.line_spacing=1.15; n.paragraph_format.space_after=Pt(4)
    doc.styles['Title'].font.size=Pt(20); doc.styles['Title'].font.bold=True
    doc.styles['Heading 1'].font.size=Pt(14); doc.styles['Heading 1'].font.bold=True
    doc.styles['Heading 1'].paragraph_format.space_before=Pt(8); doc.styles['Heading 1'].paragraph_format.space_after=Pt(5)
    doc.styles['Heading 2'].font.size=Pt(12); doc.styles['Heading 2'].font.bold=True
    doc.styles['Heading 2'].paragraph_format.space_before=Pt(6); doc.styles['Heading 2'].paragraph_format.space_after=Pt(4)
    # header/footer
    header=sec.header.paragraphs[0]; header.text='VIETNAM CORPORATE VALUATION & CREDIT RATING INTELLIGENCE'
    header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    for r in header.runs:r.font.name='Lato';r.font.size=Pt(8)
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=footer.add_run('Tài liệu phân tích - sử dụng dữ liệu và giả định tại thời điểm lập báo cáo')
    r.font.name='Lato';r.font.size=Pt(8)

def _add_title(doc,ticker,meta,report_type):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run('BÁO CÁO XẾP HẠNG TÍN NHIỆM' if report_type=='rating' else 'BÁO CÁO PHÂN TÍCH GIÁ CỔ PHIẾU, ĐỊNH GIÁ & M&A')
    r.bold=True;r.font.name='Lato';r.font.size=Pt(20)
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(f"{ticker} - {meta.get('CompanyName')}");r.bold=True;r.font.name='Lato';r.font.size=Pt(16)
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"Ngành: {meta.get('Sector')} | Sàn: {meta.get('Exchange')} | Nhóm so sánh: {meta.get('PeerGroup')}").font.size=Pt(10)
    doc.add_paragraph()
    box=doc.add_table(rows=3,cols=2);box.alignment=WD_TABLE_ALIGNMENT.CENTER;box.style='Table Grid'
    vals=[('Loại hình',meta.get('EntityType')),('Phương pháp',meta.get('Methodology')),('Nguồn benchmark',industry_label(ticker))]
    for i,(a,b) in enumerate(vals):
        box.cell(i,0).text=str(a);box.cell(i,1).text=str(b)
        _set_cell_shading(box.cell(i,0),'E8EEF7')
    doc.add_page_break()

def _add_toc(doc,sections):
    doc.add_heading('MỤC LỤC NỘI DUNG',0)
    for i,(h,_) in enumerate(sections,1):
        p=doc.add_paragraph();p.paragraph_format.space_after=Pt(2)
        p.add_run(f'{i}. {h}')
    doc.add_page_break()

def _add_kpi_table(doc,ticker,limit=10):
    k,_,_=sector_kpi_table(ticker)
    if not len(k):return
    t=doc.add_table(rows=1,cols=5);t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    hdr=['Chỉ tiêu','Doanh nghiệp','TB ngành','Trung vị ngành','Số DN']
    for j,x in enumerate(hdr):
        t.cell(0,j).text=x;_set_cell_shading(t.cell(0,j),'E8EEF7')
    _set_repeat_table_header(t.rows[0])
    for _,r in k.head(limit).iterrows():
        c=t.add_row().cells;m=r['Metric']
        vals=[r['Chỉ tiêu'],metric_fmt(m,r['Doanh nghiệp']),metric_fmt(m,r['Trung bình ngành']),metric_fmt(m,r['Trung vị ngành']),str(int(r['Số DN có dữ liệu']))]
        for j,x in enumerate(vals):c[j].text=str(x)
    for row in t.rows:
        for cell in row.cells:
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER;_set_cell_margins(cell)
            for p in cell.paragraphs:
                for run in p.runs:run.font.name='Lato';run.font.size=Pt(10)

def _analyst_paragraphs(ticker):
    a=intelligent_analyze(ticker)
    pars=[]
    pars.append(a.get('Conclusion',''))
    if a.get('Strengths'): pars.append('Điểm mạnh tương đối: '+' '.join(a['Strengths'][:3]))
    if a.get('Risks'): pars.append('Rủi ro/điểm yếu tương đối: '+' '.join(a['Risks'][:3]))
    if a.get('Interpretations'): pars.append('Nhận định chéo: '+' '.join(a['Interpretations'][:2]))
    return pars

def _stock_sections(ticker,meta,s,val):
    fv=fair_value_range(ticker); _,tmpl=get_template(meta.get('EntityType'),meta.get('Sector'))
    return [
    ('TÓM TẮT ĐIỀU HÀNH',[
        f"{meta.get('CompanyName')} được phân tích theo mẫu chuyên ngành {tmpl['label']}, với benchmark {industry_label(ticker)}.",
        *_analyst_paragraphs(ticker),
        f"Vùng giá mô hình hiện tại: Bear {price(fv.get('Bear'))}; Base {price(fv.get('Base'))}; Bull {price(fv.get('Bull'))}; kịch bản chiến lược/M&A {price(fv.get('StrategicMA'))}. Kịch bản M&A phải được hiệu chỉnh theo từng giao dịch cụ thể."
    ]),
    ('HỒ SƠ DOANH NGHIỆP & NGÀNH',[
        f"Doanh nghiệp thuộc ngành {meta.get('Sector')}. Các trọng tâm chuyên ngành gồm: {', '.join(tmpl['focus'])}.",
        f"Phương pháp định giá ưu tiên theo template: {', '.join(tmpl['valuation'])}. Benchmark được tính từ doanh nghiệp cùng ngành có dữ liệu ở từng chỉ tiêu/kỳ."
    ]),
    ('PHÂN TÍCH KẾT QUẢ KINH DOANH & TĂNG TRƯỞNG',[
        "Đánh giá tăng trưởng cần tách tăng trưởng quy mô khỏi chất lượng tăng trưởng. Doanh thu/tổng tài sản được đặt cạnh trung bình ngành để nhận diện doanh nghiệp đang mở rộng nhanh hơn hay chậm hơn peer.",
        "Kết luận chính thức cần kiểm tra nguồn tăng trưởng, tính lặp lại, cơ cấu doanh thu/tài sản và các khoản mục bất thường."
    ]),
    ('KHẢ NĂNG SINH LỢI & HIỆU QUẢ VỐN',[
        f"ROE hiện tại {pct(s.get('ROE'))}; ROA {pct(s.get('ROA'))}. Các tỷ suất này được so sánh đồng thời với trung bình và trung vị ngành.",
        "ROE cao không tự động đồng nghĩa định giá cao hơn: cần kiểm tra đòn bẩy, chất lượng lợi nhuận, vòng quay vốn và mức độ bền vững."
    ]),
    ('BẢNG CÂN ĐỐI, ĐÒN BẨY & THANH KHOẢN',[
        "Phân tích tập trung vào khả năng hấp thụ tổn thất, cơ cấu nguồn vốn, đòn bẩy và thanh khoản. Chỉ tiêu đặc thù thay đổi theo ngân hàng, CTCK và doanh nghiệp phi tài chính.",
        "Các chỉ tiêu được đọc theo xu hướng thời gian và tương quan peer; không kết luận chỉ từ một kỳ đơn lẻ."
    ]),
    ('SO SÁNH NHÓM TƯƠNG ĐỒNG',[
        f"Nhóm so sánh hiện tại: {industry_label(ticker)}. Mỗi KPI hiển thị số doanh nghiệp thực sự có dữ liệu để tránh tạo cảm giác chính xác giả khi coverage thấp.",
        "Trung vị ngành được dùng như kiểm tra chéo với trung bình ngành trong trường hợp outlier lớn."
    ]),
    ('ĐỊNH GIÁ CƠ SỞ & CHẾ ĐỘ ĐỊNH GIÁ',[
        f"Giá trị tham chiếu của engine: {price(val.get('FairValue'))}; phương pháp chính: {val.get('PrimaryMethod','N/A')}.",
        "Định giá được cross-check với P/E, P/B, EV/EBITDA hoặc phương pháp nội tại phù hợp loại hình. Kết quả phải được đọc cùng ROE, tăng trưởng và rủi ro."
    ]),
    ('BEAR - BASE - BULL',[
        f"Bear {price(fv.get('Bear'))}; Base {price(fv.get('Base'))}; Bull {price(fv.get('Bull'))}.",
        "Bear/Base/Bull là khung độ nhạy, không phải ba mức giá chắc chắn. Analyst có thể override haircut/premium dựa trên stress test và triển vọng ngành."
    ]),
    ('M&A, QUYỀN KIỂM SOÁT & GIÁ TRỊ CHIẾN LƯỢC',[
        f"Kịch bản Strategic/M&A hiện tại {price(fv.get('StrategicMA'))}, dựa trên control premium và synergy scenario của từng case.",
        "Không áp dụng vùng giá hoặc control premium của STB cho các doanh nghiệp khác. Với giao dịch thực tế cần phân tích quy mô lô, quyền kiểm soát, scarcity, synergy, nguồn vốn và điều kiện giao dịch."
    ]),
    ('STRESS TEST, CATALYST & RỦI RO ĐẦU TƯ',[
        "Stress test phải liên kết biến số ngành với doanh thu/lợi nhuận, vốn, thanh khoản và multiple định giá. Catalyst cần có khả năng mở khóa giá trị và mốc thời gian kiểm chứng được.",
        *_analyst_paragraphs(ticker)[1:]
    ]),
    ('KẾT LUẬN PHÂN TÍCH',[
        "Kết luận cuối cùng tổng hợp fundamental, vị trí tương đối so với ngành, định giá cơ sở, vùng Bear/Base/Bull và giá trị chiến lược/M&A.",
        "Kết quả của platform là công cụ hỗ trợ phân tích; quyết định đầu tư cần cập nhật dữ liệu thị trường, thông tin doanh nghiệp và giả định tại thời điểm sử dụng."
    ]),
    ('PHỤ LỤC DỮ LIỆU, PEER & GIẢ ĐỊNH',[
        "Phụ lục ghi nhận KPI, coverage peer, nguồn dữ liệu và các giả định/override. Đây là audit trail để tái lập kết quả."
    ])
    ]

def _rating_sections(ticker,meta,s,rr):
    rc=committee_pack(ticker); method=rr.get('MethodologyName')
    return [
    ('TÓM TẮT XẾP HẠNG',[
        f"Phương pháp được tự động lựa chọn: {method}. Kết quả mô phỏng: Anchor {rr.get('Anchor','N/A')}; SACP/SCA {rr.get('SACP',rr.get('SCA','N/A'))}; ICR {rr.get('ICR','N/A')}.",
        "Kết quả tự động là đầu vào hỗ trợ chuyên viên/Hội đồng, không thay thế phê duyệt XHTN chính thức."
    ]),
    ('PHẠM VI & PHƯƠNG PHÁP LUẬN',[
        rr.get('Audit',''),
        "Platform giữ riêng ba methodology: Ngân hàng, Công ty chứng khoán và Doanh nghiệp phi tài chính; không dùng một scorecard chung cho ba loại hình."
    ]),
    ('RỦI RO VĨ MÔ & NGÀNH',[
        f"Doanh nghiệp hoạt động trong ngành {meta.get('Sector')}. Đánh giá ngành được đặt trong bối cảnh chu kỳ, cạnh tranh, rào cản và khả năng truyền dẫn rủi ro vào hồ sơ tín dụng.",
        "Các yếu tố định tính cần được chuyên viên cập nhật từ hồ sơ doanh nghiệp và nguồn thẩm định."
    ]),
    ('HỒ SƠ KINH DOANH',[
        "Đánh giá vị thế cạnh tranh, quy mô, đa dạng hóa, franchise, mô hình kinh doanh và chất lượng tăng trưởng. Peer benchmark được dùng như bằng chứng định lượng hỗ trợ.",
        "Các KCF chưa có dữ liệu cấu trúc được giữ dưới dạng judgment/override thay vì tự sinh số."
    ]),
    ('HỒ SƠ TÀI CHÍNH',[
        f"ROE {pct(s.get('ROE'))}; ROA {pct(s.get('ROA'))}. Phân tích tài chính được điều chỉnh theo loại hình doanh nghiệp và đặt cạnh peer.",
        "Trọng tâm gồm vốn/đòn bẩy, khả năng sinh lợi, rủi ro tài sản, nguồn vốn, thanh khoản và dòng tiền."
    ]),
    ('ANCHOR, NOTCH/MODIFIER & SACP/SCA',[
        f"Anchor {rr.get('Anchor','N/A')}; SACP/SCA {rr.get('SACP',rr.get('SCA','N/A'))}. Waterfall dưới đây cho phép truy vết từng bước từ điểm khởi đầu đến năng lực tín nhiệm độc lập.",
        "Mọi Analyst Override cần lưu lý do, nguồn dữ liệu và người phê duyệt."
    ]),
    ('HỖ TRỢ BÊN NGOÀI & ICR',[
        f"Hỗ trợ bên ngoài hiện tại {rr.get('ExternalSupportNotches',0)} bậc; ICR {rr.get('ICR','N/A')}.",
        "Chỉ ghi nhận hỗ trợ khi có cơ sở về năng lực và động cơ hỗ trợ theo methodology áp dụng."
    ]),
    ('ĐỘ NHẠY XẾP HẠNG & STRESS TEST',[
        "Độ nhạy cần chỉ ra điều kiện cụ thể có thể nâng/hạ hạng: thay đổi vốn, chất lượng tài sản, đòn bẩy, thanh khoản, lợi nhuận, vị thế kinh doanh hoặc hỗ trợ.",
        "Stress test phải liên kết kịch bản bất lợi với các chỉ tiêu dẫn tới thay đổi notch/modifier hoặc rating cap."
    ]),
    ('EARLY WARNING & GIÁM SÁT SAU XẾP HẠNG',[
        "Thiết lập chỉ báo cảnh báo sớm theo methodology và ngành. Khi chỉ báo vượt ngưỡng, chuyên viên cần đánh giá lại giả định và khả năng thay đổi rating.",
        "Không dùng một ngưỡng chung cho mọi ngành."
    ]),
    ('KẾT LUẬN TRÌNH HỘI ĐỒNG XHTN',[
        f"Kết quả mô phỏng hiện tại: {rr.get('ICR','N/A')}. Hội đồng cần xem xét đầy đủ waterfall, peer, dữ liệu nguồn, override và sensitivity trước khi phê duyệt.",
        "Báo cáo chính thức phải phân biệt rõ kết quả máy tính, nhận định chuyên viên và quyết định Hội đồng."
    ]),
    ('PHỤ LỤC KPI & PEER',["Bảng KPI và benchmark dùng để kiểm tra tính nhất quán của các luận điểm định lượng."]),
    ('PHỤ LỤC WATERFALL & AUDIT TRAIL',["Waterfall ghi lại từng cấu phần, kết quả, điều chỉnh và luận cứ để phục vụ tái kiểm tra."])
    ]

def _add_pars(doc,pars):
    for txt in pars:
        if not txt:continue
        p=doc.add_paragraph(str(txt));p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY

def _add_waterfall(doc,ticker):
    rc=committee_pack(ticker);rows=rc.get('Waterfall',[])
    t=doc.add_table(rows=1,cols=5);t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    hdr=['Bước','Cấu phần','Kết quả','Điều chỉnh','Luận cứ']
    for j,x in enumerate(hdr):t.cell(0,j).text=x;_set_cell_shading(t.cell(0,j),'E8EEF7')
    _set_repeat_table_header(t.rows[0])
    for r in rows:
        c=t.add_row().cells
        for j,k in enumerate(['Bước','Cấu phần','Kết quả','Điều chỉnh','Luận cứ']):c[j].text=str(r.get(k,''))
    for row in t.rows:
        for cell in row.cells:
            _set_cell_margins(cell)
            for p in cell.paragraphs:
                for run in p.runs:run.font.name='Lato';run.font.size=Pt(9)

def _add_fv_table(doc,ticker):
    f=fair_value_range(ticker)
    t=doc.add_table(rows=2,cols=4);t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    hdr=['Bear','Base','Bull','Chiến lược/M&A']; vals=[price(f.get('Bear')),price(f.get('Base')),price(f.get('Bull')),price(f.get('StrategicMA'))]
    for j,x in enumerate(hdr):t.cell(0,j).text=x;_set_cell_shading(t.cell(0,j),'E8EEF7')
    for j,x in enumerate(vals):t.cell(1,j).text=x
    for row in t.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:run.font.name='Lato';run.font.size=Pt(10)


def professional_page_plan(report_type):
    if report_type=='rating':
        return [
        ('TÓM TẮT XẾP HẠNG','Kết quả xếp hạng, triển vọng và luận điểm tín dụng cốt lõi.'),
        ('PHẠM VI XẾP HẠNG & DỮ LIỆU','Phạm vi tổ chức phát hành, BCTC hợp nhất, kỳ dữ liệu và nguồn benchmark.'),
        ('PHƯƠNG PHÁP LUẬN ÁP DỤNG','Tự động route đúng methodology Ngân hàng / CTCK / Doanh nghiệp phi tài chính.'),
        ('RỦI RO VĨ MÔ','Các yếu tố kinh tế vĩ mô có khả năng truyền dẫn vào hồ sơ tín dụng.'),
        ('RỦI RO NGÀNH','Chu kỳ, cấu trúc cạnh tranh, rào cản và mức độ biến động của ngành.'),
        ('HỒ SƠ KINH DOANH','Vị thế cạnh tranh, franchise, quy mô, đa dạng hóa và chất lượng tăng trưởng.'),
        ('QUY MÔ & TĂNG TRƯỞNG','Tăng trưởng tài sản/doanh thu và mức độ bền vững so với peer.'),
        ('KHẢ NĂNG SINH LỢI','ROE, ROA, biên lợi nhuận và chất lượng nguồn thu.'),
        ('CHẤT LƯỢNG TÀI SẢN / RỦI RO TÀI SẢN','NPL hoặc các rủi ro tài sản đặc thù theo loại hình.'),
        ('VỐN & ĐÒN BẨY','Mức độ đầy đủ vốn, đòn bẩy và bộ đệm hấp thụ tổn thất.'),
        ('NGUỒN VỐN','Cơ cấu nguồn vốn, mức độ ổn định, tập trung và chi phí.'),
        ('THANH KHOẢN','Khả năng đáp ứng nghĩa vụ và nguồn thanh khoản dự phòng.'),
        ('DÒNG TIỀN & KHẢ NĂNG TRẢ NỢ','Khả năng chuyển lợi nhuận thành tiền và đáp ứng nghĩa vụ nợ.'),
        ('QUẢN TRỊ & QUẢN LÝ','Chiến lược, quản trị rủi ro, kiểm soát, khẩu vị rủi ro và chính sách tài chính.'),
        ('SO SÁNH NHÓM TƯƠNG ĐỒNG','Vị trí tương đối của doanh nghiệp so với trung bình/trung vị ngành.'),
        ('ANCHOR','Điểm khởi đầu theo đúng methodology áp dụng.'),
        ('ĐIỀU CHỈNH NỘI SINH / MODIFIERS','Từng notch/modifier, luận cứ và tác động.'),
        ('SACP / SCA','Năng lực tín nhiệm độc lập sau các điều chỉnh nội sinh.'),
        ('HỖ TRỢ BÊN NGOÀI','Khả năng và động cơ hỗ trợ từ tập đoàn/chính phủ khi phù hợp.'),
        ('ICR','Kết quả xếp hạng tín nhiệm tổ chức phát hành.'),
        ('ĐỘ NHẠY XẾP HẠNG','Điều kiện định lượng/định tính có thể dẫn tới nâng hoặc hạ hạng.'),
        ('STRESS TEST','Kịch bản bất lợi và tác động tới vốn, thanh khoản, lợi nhuận và rating.'),
        ('EARLY WARNING','Chỉ báo giám sát sau xếp hạng và ngưỡng cần đánh giá lại.'),
        ('KẾT LUẬN TRÌNH HỘI ĐỒNG XHTN','Tóm tắt waterfall, điểm tranh luận và vấn đề cần Hội đồng quyết định.'),
        ('PHỤ LỤC KPI','Bảng KPI chính và benchmark ngành.'),
        ('PHỤ LỤC WATERFALL','Audit trail từ Anchor tới ICR.'),
        ('PHỤ LỤC PEER & COVERAGE','Danh sách peer, trung bình/trung vị và số DN có dữ liệu.'),
        ('GIẢ ĐỊNH, HẠN CHẾ & TUYÊN BỐ SỬ DỤNG','Các giả định, override, giới hạn dữ liệu và điều kiện sử dụng.')
        ]
    return [
        ('TÓM TẮT ĐIỀU HÀNH','Luận điểm đầu tư, vùng giá và rủi ro trọng yếu.'),
        ('HỒ SƠ DOANH NGHIỆP','Loại hình, ngành, sàn, quy mô và vị trí trong peer group.'),
        ('BỐI CẢNH VĨ MÔ','Các biến vĩ mô có ảnh hưởng tới hoạt động và định giá.'),
        ('TRIỂN VỌNG NGÀNH','Chu kỳ, cạnh tranh, quy mô thị trường và động lực tăng trưởng.'),
        ('VỊ THẾ CẠNH TRANH','Franchise, thị phần, lợi thế và hạn chế.'),
        ('MÔ HÌNH KINH DOANH','Cơ cấu nguồn thu/tài sản và mức độ đa dạng.'),
        ('QUY MÔ & TĂNG TRƯỞNG','Tăng trưởng doanh thu/tài sản và chất lượng tăng trưởng.'),
        ('ROE & HIỆU QUẢ VỐN','ROE lịch sử, peer benchmark và nguồn tạo ROE.'),
        ('ROA & HIỆU QUẢ TÀI SẢN','ROA lịch sử và hiệu quả sử dụng tài sản.'),
        ('CHẤT LƯỢNG LỢI NHUẬN','Tính lặp lại, biên lợi nhuận và các khoản bất thường.'),
        ('CHẤT LƯỢNG TÀI SẢN','NPL hoặc rủi ro tài sản đặc thù.'),
        ('VỐN & ĐÒN BẨY','CAR/đòn bẩy và khả năng hấp thụ tổn thất.'),
        ('NGUỒN VỐN & THANH KHOẢN','Cơ cấu nguồn vốn, chi phí vốn và thanh khoản.'),
        ('DÒNG TIỀN','Dòng tiền hoạt động, FCF và khả năng tài trợ tăng trưởng.'),
        ('SO SÁNH PEER','Trung bình, trung vị ngành và vị trí tương đối.'),
        ('ĐỊNH GIÁ TƯƠNG ĐỐI','P/E, P/B, EV/EBITDA và benchmark phù hợp.'),
        ('ĐỊNH GIÁ NỘI TẠI / CƠ SỞ','Giá trị cơ sở và các giả định trọng yếu.'),
        ('BEAR - BASE - BULL','Vùng giá theo các kịch bản thận trọng, cơ sở và tích cực.'),
        ('ĐỘ NHẠY ĐỊNH GIÁ','Độ nhạy với ROE/COE/tăng trưởng hoặc biến số chuyên ngành.'),
        ('M&A - GIÁ TRỊ ĐỘC LẬP','Giá trị trước quyền kiểm soát và cộng hưởng.'),
        ('M&A - QUYỀN KIỂM SOÁT & SCARCITY','Control premium, scarcity và quy mô lô khi có cơ sở.'),
        ('M&A - CỘNG HƯỞNG','Cộng hưởng doanh thu, chi phí, vốn và nguồn vốn.'),
        ('PPA, GOODWILL & TÁI CẤU TRÚC','PPA, goodwill, tăng vốn, giảm nợ và xử lý tài sản.'),
        ('STRESS TEST','Kịch bản bất lợi và tác động tới tài chính/định giá.'),
        ('CATALYST & RỦI RO ĐẦU TƯ','Sự kiện mở khóa giá trị và yếu tố làm suy yếu luận điểm.'),
        ('KẾT LUẬN PHÂN TÍCH','Tổng hợp fundamental, peer, valuation và M&A.'),
        ('PHỤ LỤC KPI, PEER & BIỂU ĐỒ','KPI, benchmark và chuỗi thời gian.'),
        ('GIẢ ĐỊNH, DỮ LIỆU & TUYÊN BỐ SỬ DỤNG','Lineage, coverage, giả định và giới hạn.')
        ]

def _page_narrative(ticker,head,desc,meta,s,val,rr,report_type):
    a=intelligent_analyze(ticker)
    base=[desc]
    if report_type=='rating':
        base.append(f"Phương pháp áp dụng: {rr.get('MethodologyName','N/A')}. Anchor {rr.get('Anchor','N/A')}; SACP/SCA {rr.get('SACP',rr.get('SCA','N/A'))}; ICR {rr.get('ICR','N/A')}.")
        if head in ('SO SÁNH NHÓM TƯƠNG ĐỒNG','PHỤ LỤC PEER & COVERAGE'):
            base.append(f"Benchmark: {industry_label(ticker)}. Kết luận phải đọc cùng số doanh nghiệp có dữ liệu ở từng KPI và từng kỳ.")
        if head in ('ĐIỀU CHỈNH NỘI SINH / MODIFIERS','KẾT LUẬN TRÌNH HỘI ĐỒNG XHTN'):
            base.append("Mọi notch/modifier cần có bằng chứng định lượng, nhận định định tính và audit trail. Analyst Override phải ghi rõ lý do và không được làm mất dấu kết quả máy tính ban đầu.")
        if head in ('ĐỘ NHẠY XẾP HẠNG','STRESS TEST','EARLY WARNING'):
            base.append("Độ nhạy được trình bày theo điều kiện có thể kiểm chứng, liên kết trực tiếp với yếu tố có khả năng làm thay đổi notch, modifier, cap/floor hoặc mức hỗ trợ.")
    else:
        fv=fair_value_range(ticker)
        base.append(f"Giá trị mô hình: Bear {price(fv.get('Bear'))}; Base {price(fv.get('Base'))}; Bull {price(fv.get('Bull'))}; Strategic/M&A {price(fv.get('StrategicMA'))}.")
        if head in ('SO SÁNH PEER','PHỤ LỤC KPI, PEER & BIỂU ĐỒ'):
            base.append(f"Benchmark: {industry_label(ticker)}; sử dụng cả trung bình và trung vị ngành để giảm ảnh hưởng của outlier.")
        if head in ('BEAR - BASE - BULL','ĐỘ NHẠY ĐỊNH GIÁ','STRESS TEST'):
            base.append("Các kịch bản là kiểm tra độ nhạy, không phải dự báo chắc chắn. Các giả định phải được hiệu chỉnh theo chu kỳ ngành, chất lượng doanh nghiệp và dữ liệu mới nhất.")
        if head.startswith('M&A') or head.startswith('PPA'):
            base.append("Giá trị M&A là lớp giá trị riêng của từng giao dịch. Platform không áp dụng vùng giá 80.000-100.000 đồng/cp hoặc control premium của STB cho doanh nghiệp khác.")
    if head in ('TÓM TẮT ĐIỀU HÀNH','KẾT LUẬN PHÂN TÍCH','CATALYST & RỦI RO ĐẦU TƯ','TÓM TẮT XẾP HẠNG'):
        base.extend([x for x in [a.get('Conclusion')] if x])
        base.extend(a.get('Interpretations',[])[:2])
    # Add structured analytical depth so each A4 page is useful, not a filler page.
    if report_type=='rating':
        base.append("Đánh giá tương đối phải chỉ ra doanh nghiệp đang tốt hơn, tương đương hay yếu hơn peer ở những chỉ tiêu nào; đồng thời giải thích liệu chênh lệch đó có đủ bền vững để tác động đến notch/modifier hay không.")
        base.append("Khi dữ liệu định lượng và nhận định định tính mâu thuẫn, báo cáo giữ cả hai lớp thông tin và yêu cầu chuyên viên giải thích nguyên nhân thay vì để engine tự động ưu tiên một phía.")
        base.append("Điểm cần xác minh trước Hội đồng gồm: tính đầy đủ của dữ liệu, các sự kiện sau ngày BCTC, giao dịch với bên liên quan, nghĩa vụ tiềm ẩn, kế hoạch vốn/nguồn vốn và khả năng thay đổi hỗ trợ bên ngoài.")
    else:
        base.append("Phân tích không chỉ so sánh mức hiện tại mà còn xem xu hướng nhiều kỳ, độ lệch so với peer và khả năng mean-reversion. Một mức multiple thấp chỉ được coi là hấp dẫn nếu không phản ánh suy giảm chất lượng tài sản, lợi nhuận hoặc rủi ro cấu trúc.")
        base.append("Giá trị hợp lý được đọc như một vùng thay vì một điểm duy nhất. Khoảng Bear-Base-Bull giúp thể hiện bất định của giả định; Strategic/M&A Value là lớp giá trị riêng khi có quyền kiểm soát, scarcity hoặc synergy có thể chứng minh.")
        base.append("Điểm cần xác minh trước khi sử dụng kết luận gồm: chất lượng BCTC, thay đổi cấu trúc vốn, kế hoạch phát hành, giao dịch cổ đông lớn, sự kiện pháp lý, triển vọng ngành và các thông tin có thể làm thay đổi ROE/COE hoặc multiple mục tiêu.")
    if report_type=='rating':
        ev=rating_evidence(ticker)
        base.append(f"Độ tin cậy XHTN tự động: {ev.get('RatingConfidence')}; độ đầy đủ dữ liệu cốt lõi {ev.get('DataQuality',{}).get('Coverage',0)*100:.0f}%.")
    else:
        vt=triangulate(ticker)
        base.append(f"Độ tin cậy phân tích: {vt.get('AnalyticalConfidence')}; độ đầy đủ dữ liệu cốt lõi {vt.get('DataQuality',{}).get('Coverage',0)*100:.0f}%.")
    base.append("Nhận định cuối cùng phải được đối chiếu với BCTC hợp nhất, thuyết minh, công bố thông tin và các dữ liệu định tính trước khi phát hành chính thức.")
    return base

def _evidence_table(doc,ticker,head,report_type):
    k,_,_=sector_kpi_table(ticker)
    if not len(k):return
    # Pick up to 5 KPIs so each analytical page carries evidence without overcrowding.
    kk=k.head(5)
    t=doc.add_table(rows=1,cols=5);t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    hdr=['Chỉ tiêu','Doanh nghiệp','TB ngành','Trung vị','Số DN']
    for j,x in enumerate(hdr):t.cell(0,j).text=x;_set_cell_shading(t.cell(0,j),'E8EEF7')
    _set_repeat_table_header(t.rows[0])
    for _,r in kk.iterrows():
        c=t.add_row().cells;m=r['Metric']
        vals=[r['Chỉ tiêu'],metric_fmt(m,r['Doanh nghiệp']),metric_fmt(m,r['Trung bình ngành']),metric_fmt(m,r['Trung vị ngành']),str(int(r['Số DN có dữ liệu']))]
        for j,x in enumerate(vals):c[j].text=str(x)
    for row in t.rows:
        for cell in row.cells:
            _set_cell_margins(cell)
            for pp in cell.paragraphs:
                for run in pp.runs:run.font.name='Lato';run.font.size=Pt(9)


def _add_evidence_ledger(doc,ticker):
    ev=rating_evidence(ticker); rows=ev.get('EvidenceLedger',[])
    t=doc.add_table(rows=1,cols=5);t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    hdr=['Cấu phần','Kết quả','Điều chỉnh','Bằng chứng','Kiểm chứng']
    for j,x in enumerate(hdr):t.cell(0,j).text=x;_set_cell_shading(t.cell(0,j),'E8EEF7')
    for r in rows:
        c=t.add_row().cells
        vals=[r.get('Cấu phần'),r.get('Kết quả'),r.get('Điều chỉnh'),r.get('Loại bằng chứng'),r.get('Trạng thái kiểm chứng')]
        for j,x in enumerate(vals):c[j].text=str(x)
    for row in t.rows:
        for cell in row.cells:
            _set_cell_margins(cell)
            for pp in cell.paragraphs:
                for run in pp.runs:run.font.name='Lato';run.font.size=Pt(9)

def _add_triangulation_table(doc,ticker):
    vt=triangulate(ticker);rows=vt.get('Lenses',[])
    t=doc.add_table(rows=1,cols=3);t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    hdr=['Lăng kính','Giá trị','Trạng thái']
    for j,x in enumerate(hdr):t.cell(0,j).text=x;_set_cell_shading(t.cell(0,j),'E8EEF7')
    for r in rows:
        c=t.add_row().cells
        c[0].text=str(r.get('Lăng kính')); c[1].text=price(r.get('Giá trị')); c[2].text=str(r.get('Trạng thái'))
    for row in t.rows:
        for cell in row.cells:
            for pp in cell.paragraphs:
                for run in pp.runs:run.font.name='Lato';run.font.size=Pt(10)


def peer_bar_chart(ticker,metric,title=None,top_n=12):
    from scripts.universal_data import industry_snapshot
    peers=industry_snapshot(ticker)
    if peers is None or not len(peers) or metric not in peers.columns:return None
    z=peers[['Ticker',metric]].copy()
    z[metric]=pd.to_numeric(z[metric],errors='coerce')
    z=z.dropna(subset=[metric]).drop_duplicates('Ticker')
    if not len(z):return None
    selected=str(ticker).upper()
    company=z[z.Ticker.astype(str).str.upper().eq(selected)]
    if len(company):
        cv=float(company.iloc[-1][metric]); z['dist']=(z[metric]-cv).abs()
        chosen=pd.concat([company,z[~z.Ticker.astype(str).str.upper().eq(selected)].sort_values('dist').head(max(0,top_n-1))])
    else:
        chosen=z.sort_values(metric).tail(top_n)
    chosen=chosen.drop_duplicates('Ticker').sort_values(metric)
    mean=float(z[metric].mean())
    fig,ax=plt.subplots(figsize=(8.4,4.2));plt.rcParams.update({'font.family':'Lato','font.size':10})
    ax.barh(chosen.Ticker.astype(str),chosen[metric]);ax.axvline(mean,linestyle='--',linewidth=1.5,label='Trung bình ngành')
    ax.set_title(title or f"{VI_METRIC.get(metric,metric)} - so sánh peer",fontsize=11);ax.grid(axis='x',alpha=.2);ax.legend(fontsize=8)
    if metric in PCT:ax.xaxis.set_major_formatter(lambda v,pos:(f'{v*100:.1f}%').replace('.',','))
    fig.tight_layout();bio=BytesIO();fig.savefig(bio,dpi=180,bbox_inches='tight');plt.close(fig);bio.seek(0);return bio

def peer_scatter_chart(ticker,xmetric,ymetric,title=None):
    from scripts.universal_data import industry_snapshot
    peers=industry_snapshot(ticker)
    if peers is None or not len(peers) or xmetric not in peers.columns or ymetric not in peers.columns:return None
    z=peers[['Ticker',xmetric,ymetric]].copy()
    z[xmetric]=pd.to_numeric(z[xmetric],errors='coerce');z[ymetric]=pd.to_numeric(z[ymetric],errors='coerce')
    z=z.dropna(subset=[xmetric,ymetric]).drop_duplicates('Ticker')
    if len(z)<2:return None
    fig,ax=plt.subplots(figsize=(8.4,4.4));plt.rcParams.update({'font.family':'Lato','font.size':10})
    ax.scatter(z[xmetric],z[ymetric],alpha=.7)
    for _,r in z.iterrows():
        if str(r.Ticker).upper()==str(ticker).upper():
            ax.annotate(str(r.Ticker),(r[xmetric],r[ymetric]),xytext=(5,5),textcoords='offset points',fontweight='bold')
    ax.axvline(z[xmetric].mean(),linestyle='--',linewidth=1);ax.axhline(z[ymetric].mean(),linestyle='--',linewidth=1)
    ax.set_xlabel(VI_METRIC.get(xmetric,xmetric));ax.set_ylabel(VI_METRIC.get(ymetric,ymetric))
    ax.set_title(title or f"{VI_METRIC.get(ymetric,ymetric)} và {VI_METRIC.get(xmetric,xmetric)} - vị trí tương đối",fontsize=11)
    if xmetric in PCT:ax.xaxis.set_major_formatter(lambda v,pos:(f'{v*100:.1f}%').replace('.',','))
    if ymetric in PCT:ax.yaxis.set_major_formatter(lambda v,pos:(f'{v*100:.1f}%').replace('.',','))
    ax.grid(alpha=.2);fig.tight_layout();bio=BytesIO();fig.savefig(bio,dpi=180,bbox_inches='tight');plt.close(fig);bio.seek(0);return bio

def _relative_analysis(ticker,metric):
    k,_,_=sector_kpi_table(ticker)
    if not len(k):return None
    r=k[k.Metric.astype(str).eq(str(metric))]
    if not len(r):return None
    r=r.iloc[-1]
    c=num(r['Doanh nghiệp']);m=num(r['Trung bình ngành']);med=num(r['Trung vị ngành']);n=int(r['Số DN có dữ liệu'])
    if c is None:return None
    label=r['Chỉ tiêu']
    if m in (None,0):return f"{label} của doanh nghiệp là {metric_fmt(metric,c)}; chưa đủ dữ liệu ngành để kết luận tương đối."
    gap=c/m-1;direction='cao hơn' if gap>0 else 'thấp hơn';mag=abs(gap);g=(f"{mag*100:.1f}").replace('.',',')
    txt=f"{label} đạt {metric_fmt(metric,c)}, {direction} trung bình ngành {metric_fmt(metric,m)} khoảng {g}% (mẫu {n} doanh nghiệp có dữ liệu)."
    if med is not None:txt+=f" Trung vị ngành là {metric_fmt(metric,med)}, dùng để kiểm tra ảnh hưởng của outlier."
    if metric=='ROE':txt+=" ROE cần đọc cùng đòn bẩy, chất lượng lợi nhuận và mức định giá P/B/P/E."
    elif metric=='NPL':txt+=" Chênh lệch NPL cần đọc cùng mức bao phủ dự phòng, tài sản bảo đảm và bộ đệm vốn."
    elif metric=='CAR':txt+=" CAR cần đọc cùng tăng trưởng tài sản có rủi ro, kế hoạch vốn và chất lượng tài sản."
    elif metric=='CASA':txt+=" CASA cao hơn peer có thể hỗ trợ chi phí vốn/NIM nhưng cần kiểm tra độ ổn định tiền gửi."
    elif metric=='DebtEquity':txt+=" Đòn bẩy cao hơn peer làm tăng độ nhạy lợi nhuận và khả năng trả nợ."
    return txt

def _page_peer_metrics(head,entity_type):
    if entity_type=='BANK':
        mp={
        'QUY MÔ & TĂNG TRƯỞNG':['TotalAssets','GrossLoans','CustomerDeposits'],
        'ROE & HIỆU QUẢ VỐN':['ROE','NIM','CIR'],
        'ROA & HIỆU QUẢ TÀI SẢN':['ROA','LoanAssets','EquityAssets'],
        'KHẢ NĂNG SINH LỢI':['ROE','ROA','NIM','CIR'],
        'CHẤT LƯỢNG TÀI SẢN':['NPL','ProvisionOperatingIncome','LoanAssets'],
        'CHẤT LƯỢNG TÀI SẢN / RỦI RO TÀI SẢN':['NPL','ProvisionOperatingIncome','LoanAssets'],
        'VỐN & ĐÒN BẨY':['CAR','EquityAssets','ROE'],
        'NGUỒN VỐN & THANH KHOẢN':['CASA','LDR','DepositAssets'],
        'THANH KHOẢN':['LDR','CASA','DepositAssets'],
        'SO SÁNH PEER':['ROE','ROA','NIM','CIR','NPL','CAR','CASA','LDR','PB'],
        'SO SÁNH NHÓM TƯƠNG ĐỒNG':['ROE','ROA','NIM','CIR','NPL','CAR','CASA','LDR','PB']}
    elif entity_type=='SECURITIES':
        mp={
        'QUY MÔ & TĂNG TRƯỞNG':['Revenue','TotalAssets','Equity'],
        'ROE & HIỆU QUẢ VỐN':['ROE','AvailableCapitalRatio','DebtEquity'],
        'ROA & HIỆU QUẢ TÀI SẢN':['ROA','NetMargin'],
        'KHẢ NĂNG SINH LỢI':['ROE','ROA','NetMargin','ICGR'],
        'CHẤT LƯỢNG TÀI SẢN':['MarginLoansEquity','DebtEquity'],
        'CHẤT LƯỢNG TÀI SẢN / RỦI RO TÀI SẢN':['MarginLoansEquity','DebtEquity'],
        'VỐN & ĐÒN BẨY':['AvailableCapitalRatio','DebtEquity','DebtEBITDA'],
        'NGUỒN VỐN & THANH KHOẢN':['CurrentRatio','DebtEquity','CFO_Debt'],
        'THANH KHOẢN':['CurrentRatio','CFO_Debt'],
        'SO SÁNH PEER':['ROE','ROA','AvailableCapitalRatio','DebtEquity','CurrentRatio','PB','PE'],
        'SO SÁNH NHÓM TƯƠNG ĐỒNG':['ROE','ROA','AvailableCapitalRatio','DebtEquity','CurrentRatio','PB','PE']}
    else:
        mp={
        'QUY MÔ & TĂNG TRƯỞNG':['Revenue','TotalAssets','GrossMargin'],
        'ROE & HIỆU QUẢ VỐN':['ROE','DebtEquity','NetMargin'],
        'ROA & HIỆU QUẢ TÀI SẢN':['ROA','EBITDAMargin'],
        'KHẢ NĂNG SINH LỢI':['ROE','ROA','GrossMargin','NetMargin','EBITDAMargin'],
        'CHẤT LƯỢNG TÀI SẢN':['CFO_Debt','FOCF_Debt','DebtEBITDA'],
        'CHẤT LƯỢNG TÀI SẢN / RỦI RO TÀI SẢN':['CFO_Debt','FOCF_Debt','DebtEBITDA'],
        'VỐN & ĐÒN BẨY':['DebtEquity','DebtEBITDA','CFO_Debt','FOCF_Debt'],
        'NGUỒN VỐN & THANH KHOẢN':['CurrentRatio','CFO_Debt','FOCF_Debt'],
        'THANH KHOẢN':['CurrentRatio','CFO_Debt','FOCF_Debt'],
        'SO SÁNH PEER':['ROE','ROA','GrossMargin','NetMargin','DebtEquity','DebtEBITDA','CurrentRatio','PB','PE'],
        'SO SÁNH NHÓM TƯƠNG ĐỒNG':['ROE','ROA','GrossMargin','NetMargin','DebtEquity','DebtEBITDA','CurrentRatio','PB','PE']}
    if head in ('ĐỊNH GIÁ TƯƠNG ĐỐI','ĐỊNH GIÁ CƠ SỞ & CHẾ ĐỘ ĐỊNH GIÁ'):return ['PB','PE','EV_EBITDA']
    return mp.get(head,[])

def _add_peer_section(doc,ticker,head,meta):
    metrics=_page_peer_metrics(head,meta.get('EntityType'))
    for mm in metrics:
        try:
            nar=_relative_analysis(ticker,mm)
            if nar:_add_pars(doc,[nar])
            bio=peer_bar_chart(ticker,mm)
            if bio:doc.add_picture(bio,width=Mm(176))
        except Exception:pass
    if head in ('ROE & HIỆU QUẢ VỐN','KHẢ NĂNG SINH LỢI','SO SÁNH PEER','SO SÁNH NHÓM TƯƠNG ĐỒNG'):
        try:
            bio=peer_scatter_chart(ticker,'ROE','PB')
            if bio:doc.add_picture(bio,width=Mm(176))
        except Exception:pass


def _decision_narrative(ticker,head,meta,snapshot,val,report_type):
    """Four-question analyst narrative: What? Why? Peer? So what?
    Uses only model/public-data fields already available; avoids inventing causes.
    """
    et=meta.get('EntityType')
    lines=[]
    metrics=_page_peer_metrics(head,et)
    # 1) What do the numbers say + peer comparison
    if metrics:
        facts=[]
        for m in metrics[:3]:
            try:
                x=_relative_analysis(ticker,m)
                if x:facts.append(x)
            except Exception:pass
        if facts:
            lines.append("Số liệu nói gì? "+" ".join(facts))
    # 2) Why: disciplined driver framing, not unsupported causal claims
    driver_map={
      'ROE & HIỆU QUẢ VỐN':"Động lực cần kiểm chứng gồm biên lợi nhuận, hiệu suất sử dụng tài sản và đòn bẩy. Báo cáo không quy kết nguyên nhân khi dữ liệu nguồn chưa đủ bằng chứng.",
      'ROA & HIỆU QUẢ TÀI SẢN':"ROA phản ánh khả năng chuyển quy mô tài sản thành lợi nhuận; cần đối chiếu tăng trưởng tài sản, biên lợi nhuận và các khoản thu nhập bất thường.",
      'KHẢ NĂNG SINH LỢI':"Khả năng sinh lợi bền vững cần được kiểm tra qua biên lợi nhuận, cơ cấu thu nhập, chi phí hoạt động và mức sử dụng đòn bẩy.",
      'CHẤT LƯỢNG TÀI SẢN':"Chất lượng tài sản cần được kiểm tra đồng thời qua nợ xấu, dự phòng, tăng trưởng tín dụng/tài sản và mức tập trung rủi ro.",
      'CHẤT LƯỢNG TÀI SẢN / RỦI RO TÀI SẢN':"Chất lượng tài sản cần được kiểm tra đồng thời qua nợ xấu, dự phòng, tăng trưởng tín dụng/tài sản và mức tập trung rủi ro.",
      'VỐN & ĐÒN BẨY':"Bộ đệm vốn phải được đặt cạnh tốc độ tăng trưởng, chất lượng tài sản và khả năng tạo vốn nội bộ; một tỷ lệ vốn cao không tự động đồng nghĩa rủi ro thấp.",
      'NGUỒN VỐN & THANH KHOẢN':"Chất lượng nguồn vốn phụ thuộc chi phí, độ ổn định, mức tập trung và khả năng chuyển đổi tài sản thành thanh khoản trong điều kiện căng thẳng.",
      'THANH KHOẢN':"Thanh khoản cần được đọc theo cả trạng thái hiện tại và sức chịu đựng khi dòng tiền bất lợi; tỷ lệ kế toán đơn lẻ không đủ để kết luận.",
      'ĐỊNH GIÁ TƯƠNG ĐỐI':"Premium/discount định giá chỉ hợp lý khi tương xứng với ROE, tăng trưởng, rủi ro và chất lượng lợi nhuận so với peer.",
      'ĐỊNH GIÁ CƠ SỞ & CHẾ ĐỘ ĐỊNH GIÁ':"Giá trị hợp lý được xem như một vùng thay vì một điểm duy nhất; độ nhạy với ROE, COE, tăng trưởng và multiple giúp lượng hóa rủi ro sai số.",
      'SO SÁNH PEER':"So sánh peer ưu tiên cả trung bình và trung vị để giảm ảnh hưởng của outlier; vị trí tương đối quan trọng hơn một ngưỡng tuyệt đối.",
      'SO SÁNH NHÓM TƯƠNG ĐỒNG':"So sánh peer ưu tiên cả trung bình và trung vị để giảm ảnh hưởng của outlier; vị trí tương đối quan trọng hơn một ngưỡng tuyệt đối."
    }
    if head in driver_map:lines.append("Tại sao cần chú ý? "+driver_map[head])

    # 3/4) Explicit implication for valuation vs credit rating
    if report_type=='analysis':
        implication={
          'ROE & HIỆU QUẢ VỐN':"Tác động đến giá cổ phiếu: ROE cao và bền vững hơn peer có thể biện minh cho P/B premium; ngược lại, ROE thấp nhưng P/B cao làm tăng rủi ro định giá.",
          'ROA & HIỆU QUẢ TÀI SẢN':"Tác động đến giá cổ phiếu: ROA tốt hơn peer hỗ trợ chất lượng lợi nhuận và khả năng duy trì ROE mà không cần tăng mạnh đòn bẩy.",
          'KHẢ NĂNG SINH LỢI':"Tác động đến giá cổ phiếu: chất lượng và độ bền của lợi nhuận quyết định mức multiple có thể duy trì, không chỉ tốc độ tăng EPS ngắn hạn.",
          'CHẤT LƯỢNG TÀI SẢN':"Tác động đến giá cổ phiếu: suy giảm chất lượng tài sản có thể làm tăng chi phí tín dụng, giảm ROE kỳ vọng và kéo giảm multiple hợp lý.",
          'VỐN & ĐÒN BẨY':"Tác động đến giá cổ phiếu: bộ đệm vốn tốt tạo dư địa tăng trưởng/phân phối vốn; thiếu vốn có thể dẫn đến pha loãng hoặc hạn chế tăng trưởng.",
          'NGUỒN VỐN & THANH KHOẢN':"Tác động đến giá cổ phiếu: nguồn vốn ổn định và chi phí thấp hỗ trợ biên lợi nhuận, đồng thời giảm tail risk thanh khoản.",
          'ĐỊNH GIÁ TƯƠNG ĐỐI':"Kết luận định giá phải trả lời premium/discount so với peer có được giải thích bởi ROE, tăng trưởng và rủi ro hay không.",
          'SO SÁNH PEER':"Kết luận đầu tư: ưu tiên doanh nghiệp có tổ hợp ROE/tăng trưởng/chất lượng tài sản tốt hơn peer nhưng valuation chưa phản ánh đầy đủ lợi thế đó.",
          'SO SÁNH NHÓM TƯƠNG ĐỒNG':"Kết luận đầu tư: ưu tiên doanh nghiệp có tổ hợp ROE/tăng trưởng/chất lượng tài sản tốt hơn peer nhưng valuation chưa phản ánh đầy đủ lợi thế đó."
        }
    else:
        implication={
          'ROE & HIỆU QUẢ VỐN':"Tác động đến XHTN: khả năng sinh lợi tốt tạo vốn nội bộ và hấp thụ tổn thất; nhưng lợi nhuận dựa nhiều vào đòn bẩy hoặc thu nhập bất thường có chất lượng thấp hơn.",
          'ROA & HIỆU QUẢ TÀI SẢN':"Tác động đến XHTN: hiệu quả tài sản tốt hỗ trợ khả năng tạo bộ đệm vốn, song phải được kiểm tra tính bền vững.",
          'KHẢ NĂNG SINH LỢI':"Tác động đến XHTN: lợi nhuận bền vững củng cố năng lực hấp thụ tổn thất và trả nợ; biến động lợi nhuận làm giảm độ chắc chắn của hồ sơ tài chính.",
          'CHẤT LƯỢNG TÀI SẢN / RỦI RO TÀI SẢN':"Tác động đến XHTN: chất lượng tài sản suy yếu có thể truyền dẫn sang dự phòng, lợi nhuận, vốn và thanh khoản, do đó là biến số trọng yếu của notch.",
          'VỐN & ĐÒN BẨY':"Tác động đến XHTN: bộ đệm vốn/đòn bẩy quyết định khả năng hấp thụ tổn thất ngoài dự kiến và là đầu vào quan trọng cho đánh giá hồ sơ tài chính.",
          'THANH KHOẢN':"Tác động đến XHTN: thanh khoản yếu có thể tạo áp lực trả nợ ngay cả khi doanh nghiệp còn khả năng sinh lợi; cần xem xét cùng cấu trúc đáo hạn và nguồn dự phòng.",
          'SO SÁNH NHÓM TƯƠNG ĐỒNG':"Tác động đến XHTN: peer comparison là phép kiểm tra tính hợp lý của đánh giá định tính và notch, không thay thế methodology."
        }
    if head in implication:lines.append(implication[head])
    return lines


def _fmt_method_value(metric,v):
    try:v=float(v)
    except:return 'N/A'
    if not np.isfinite(v):return 'N/A'
    if metric in METH_PCT:return f"{v*100:.1f}%".replace('.',',')
    if metric in METH_MULT:return f"{v:.2f}x".replace('.',',')
    if abs(v)>=1e12:return (f"{v/1e12:,.1f} nghìn tỷ").replace(',','X').replace('.',',').replace('X','.')
    if abs(v)>=1e9:return (f"{v/1e9:,.1f} tỷ").replace(',','X').replace('.',',').replace('X','.')
    return (f"{v:,.2f}").replace(',','X').replace('.',',').replace('X','.')

def _add_methodology_kpi_matrix(doc,ticker):
    z=methodology_kpi_table(ticker,include_missing=True)
    if z.empty:return
    doc.add_heading('MA TRẬN CHỈ TIÊU THEO PHƯƠNG PHÁP XHTN',1)
    _add_pars(doc,["Ma trận dưới đây mở rộng phạm vi phân tích theo đúng loại hình doanh nghiệp. Chỉ tiêu chưa có dữ liệu được giữ N/A để chỉ rõ data gap, không tự giả định số liệu."])
    for grp,g in z.groupby('Nhóm phân tích',sort=False):
        doc.add_heading(str(grp),2)
        tb=doc.add_table(rows=1,cols=6);tb.style='Table Grid'
        hdr=['Chỉ tiêu','Doanh nghiệp','TB ngành','Trung vị','Số DN','Dữ liệu']
        for j,x in enumerate(hdr):tb.rows[0].cells[j].text=x
        for _,r in g.iterrows():
            c=tb.add_row().cells;m=r['Metric']
            vals=[r['Chỉ tiêu'],_fmt_method_value(m,r['Doanh nghiệp']),_fmt_method_value(m,r['TB ngành']),
                  _fmt_method_value(m,r['Trung vị']),str(int(r['Số DN'])),r['Trạng thái dữ liệu']]
            for j,x in enumerate(vals):c[j].text=str(x)

def generate_docx(ticker,report_type='analysis',rating_result=None,mna=None):
    ticker=str(ticker).upper();meta=get_company(ticker);s=get_snapshot(ticker);val=valuation(ticker,s)
    rr=rating_result or (rate_company(ticker) if report_type=='rating' else {})
    plan=professional_page_plan(report_type)
    doc=Document();_style_doc(doc);_add_title(doc,ticker,meta,report_type);_add_toc(doc,plan)

    chart_for={
        'QUY MÔ & TĂNG TRƯỞNG':'TotalAssets' if meta.get('EntityType')=='BANK' else 'Revenue',
        'ROE & HIỆU QUẢ VỐN':'ROE','ROA & HIỆU QUẢ TÀI SẢN':'ROA',
        'KHẢ NĂNG SINH LỢI':'ROE',
        'CHẤT LƯỢNG TÀI SẢN':'NPL' if meta.get('EntityType')=='BANK' else 'ROA',
        'CHẤT LƯỢNG TÀI SẢN / RỦI RO TÀI SẢN':'NPL' if meta.get('EntityType')=='BANK' else 'ROA',
        'VỐN & ĐÒN BẨY':'CAR' if meta.get('EntityType')=='BANK' else 'DebtEquity',
        'NGUỒN VỐN & THANH KHOẢN':'CASA' if meta.get('EntityType')=='BANK' else 'CurrentRatio',
        'THANH KHOẢN':'CASA' if meta.get('EntityType')=='BANK' else 'CurrentRatio'
    }

    for i,(head,desc) in enumerate(plan,1):
        if i>1:doc.add_page_break()
        doc.add_heading(f'{i}. {head}',1)
        pars=_page_narrative(ticker,head,desc,meta,s,val,rr,report_type)
        # Analyst layer: What? Why? Peer? So what?
        pars.extend(_decision_narrative(ticker,head,meta,s,val,report_type))
        # Add explicit evidence-led relative-analysis paragraphs.
        for mm in _page_peer_metrics(head,meta.get('EntityType')):
            try:
                x=_relative_analysis(ticker,mm)
                if x:pars.append(x)
            except Exception:pass
        _add_pars(doc,pars)

        if head in chart_for:
            try:doc.add_picture(chart_metric(ticker,chart_for[head]),width=Mm(176))
            except Exception:pass
        if report_type=='analysis' and head=='BEAR - BASE - BULL':
            _add_fv_table(doc,ticker)
        elif report_type=='analysis' and head=='ĐỊNH GIÁ NỘI TẠI / CƠ SỞ':
            _add_triangulation_table(doc,ticker)
        elif report_type=='rating' and head in ('ANCHOR','ĐIỀU CHỈNH NỘI SINH / MODIFIERS','SACP / SCA','ICR','PHỤ LỤC WATERFALL'):
            _add_waterfall(doc,ticker)
        elif report_type=='rating' and head=='KẾT LUẬN TRÌNH HỘI ĐỒNG XHTN':
            _add_evidence_ledger(doc,ticker)
        else:
            _evidence_table(doc,ticker,head,report_type)

        _add_peer_section(doc,ticker,head,meta)

    # Comprehensive methodology KPI appendix
    doc.add_page_break()
    _add_methodology_kpi_matrix(doc,ticker)

    # Dedicated peer appendix
    doc.add_page_break();doc.add_heading('PHỤ LỤC ĐỒ THỊ SO SÁNH PEER CHUYÊN SÂU',1)
    peer_metrics=metric_list(ticker,available_only=True)
    # Keep charts focused on comparable ratios/scale metrics; N/A metrics remain visible in methodology matrix.
    chartable={'TotalAssets','GrossLoans','CustomerDeposits','Equity','Revenue','ROE','ROA','NIM','NPL','CAR','CIR','LDR','CASA',
               'PB','PE','DebtEquity','CurrentRatio','AvailableCapitalRatio','GrossMargin','NetMargin','DebtEBITDA','CFO_Debt'}
    peer_metrics=[m for m in peer_metrics if m in chartable]
    for mm in peer_metrics:
        try:
            doc.add_heading(VI_METRIC.get(mm,mm),2)
            nar=_relative_analysis(ticker,mm)
            if nar:_add_pars(doc,[nar])
            bio=peer_bar_chart(ticker,mm)
            if bio:doc.add_picture(bio,width=Mm(176))
        except Exception:pass

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for pp in cell.paragraphs:
                    for run in pp.runs:
                        run.font.name='Lato'
                        if run.font.size is None:run.font.size=Pt(10)
    bio=BytesIO();doc.save(bio);return bio.getvalue()

def generate_pdf(ticker,report_type='analysis',rating_result=None,mna=None):
    # Single-source-of-truth: build the DOCX first. Local/app callers may convert with LibreOffice.
    # Kept for backward compatibility; uses reportlab fallback only if conversion is unavailable.
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    ticker=str(ticker).upper();meta=get_company(ticker);s=get_snapshot(ticker);val=valuation(ticker,s)
    rr=rating_result or (rate_company(ticker) if report_type=='rating' else {})
    sections=_rating_sections(ticker,meta,s,rr) if report_type=='rating' else _stock_sections(ticker,meta,s,val)
    reg=_font();font='Helvetica';bold='Helvetica-Bold'
    try:
        b=font_manager.findfont(font_manager.FontProperties(family='Lato',weight='bold'),fallback_to_default=False)
        pdfmetrics.registerFont(TTFont('LatoReport',reg));pdfmetrics.registerFont(TTFont('LatoReportB',b));font='LatoReport';bold='LatoReportB'
    except:pass
    bio=BytesIO();pdf=SimpleDocTemplate(bio,pagesize=A4,leftMargin=50,rightMargin=45,topMargin=45,bottomMargin=42)
    body=ParagraphStyle('b',fontName=font,fontSize=11,leading=14,alignment=4,spaceAfter=7)
    h=ParagraphStyle('h',fontName=bold,fontSize=14,leading=17,spaceBefore=8,spaceAfter=6)
    story=[Paragraph('BÁO CÁO XẾP HẠNG TÍN NHIỆM' if report_type=='rating' else 'BÁO CÁO PHÂN TÍCH GIÁ CỔ PHIẾU, ĐỊNH GIÁ & M&A',h),
           Paragraph(f"{ticker} - {meta.get('CompanyName')} | {meta.get('Sector')}",body),PageBreak()]
    for i,(head,pars) in enumerate(sections,1):
        story.append(Paragraph(f'{i}. {head}',h))
        enriched=list(pars)+_decision_narrative(ticker,head,meta,s,val,report_type)
        for x in enriched:story.append(Paragraph(str(x),body))
        if head in ['SO SÁNH NHÓM TƯƠNG ĐỒNG','PHỤ LỤC KPI & PEER']:
            k,_,_=sector_kpi_table(ticker);data=[['Chỉ tiêu','DN','TB ngành','Trung vị','N']]
            for _,r in k.head(10).iterrows():
                m=r['Metric'];data.append([r['Chỉ tiêu'],metric_fmt(m,r['Doanh nghiệp']),metric_fmt(m,r['Trung bình ngành']),metric_fmt(m,r['Trung vị ngành']),str(int(r['Số DN có dữ liệu']))])
            t=Table(data,colWidths=[130,80,90,90,40]);t.setStyle(TableStyle([('FONT',(0,0),(-1,-1),font,9),('FONT',(0,0),(-1,0),bold,9),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8EEF7')),('GRID',(0,0),(-1,-1),.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP')]))
            story.append(t);story.append(Spacer(1,8))
    pdf.build(story);return bio.getvalue()
