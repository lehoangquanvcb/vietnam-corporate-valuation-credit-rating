"""Báo cáo bảo hiểm: từng chỉ tiêu có lịch sử, peer quý và nhận xét cùng UI."""
from io import BytesIO
import re
import numpy as np
import pandas as pd
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from scripts.insurance_analysis import analysis_pack, peer_universe
from scripts.insurance_rating import insurance_rating, insurance_scorecard
from scripts.insurance_methodology import rubric_rows
from scripts.financial_views import fmt, BASIS_LABELS
from scripts.methodology_kpi_engine import PCT,MULT
from scripts.universal_data import get_company

def pair_image(pair):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    m=pair['Metric'];scale=100 if m in PCT else 1 if m in MULT else 1e-9
    unit='%' if m in PCT else 'lần' if m in MULT else 'tỷ đồng'
    fig,axes=plt.subplots(1,2,figsize=(7,1.55),dpi=170)
    h,p=pair['History'],pair['Peers']
    a,b=axes
    if len(h) and h.Value.notna().any():
        a.plot(range(len(h)),pd.to_numeric(h.Value,errors='coerce')*scale,'o-',color='#166b55',lw=1.6,markersize=3)
        a.set_xticks(range(len(h)),h.DisplayPeriod,fontsize=6)
    else:a.text(.5,.5,'Chưa có chuỗi được xác minh',ha='center',va='center',transform=a.transAxes,fontsize=8);a.set_xticks([]);a.set_yticks([])
    if len(p):
        z=p[p.Status.eq('OK')&p.Value.notna()&p.Basis.eq(p.iloc[0].Basis)]
    else:z=p
    if len(z):
        b.bar(z.Ticker,z.Value*scale,color=['#166b55' if t==p.iloc[0].Ticker else '#8da6b9' for t in z.Ticker])
        b.tick_params(axis='x',labelsize=6)
    else:b.text(.5,.5,'Chưa có số cùng kỳ và cơ sở',ha='center',va='center',transform=b.transAxes,fontsize=8);b.set_xticks([]);b.set_yticks([])
    for ax,title in [(a,'Chuỗi năm gần nhất'),(b,'Peer quý '+str(pair['Period']))]:
        ax.set_title(title,loc='left',fontsize=8,fontweight='bold');ax.set_ylabel(unit,fontsize=6)
        ax.tick_params(axis='y',labelsize=6);ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15)
    fig.tight_layout(pad=.6,w_pad=1.8)
    stream=BytesIO();fig.savefig(stream,format='png');plt.close(fig);stream.seek(0);return stream

def generate_insurance_docx(ticker,report_type='analysis',rating_result=None,options=None):
    from scripts.evidence_report import _table
    from scripts.multisector_valuation import valuation
    from scripts.fair_value_range import fair_value_range
    options=options or {};basis=options.get('history_basis','FY');years=int(options.get('history_years',5))
    meta=get_company(ticker);pack=analysis_pack(ticker,basis,years);rr=rating_result or insurance_rating(ticker)
    doc=Document();sec=doc.sections[0];sec.page_width=Mm(210);sec.page_height=Mm(297)
    sec.top_margin=sec.bottom_margin=Mm(14);sec.left_margin=sec.right_margin=Mm(16)
    for name in ['Normal','Title','Subtitle','Heading 1','Heading 2']:
        style=doc.styles[name];style.font.name='DejaVu Sans';style.font.color.rgb=RGBColor(0,0,0)
        style.paragraph_format.space_after=Pt(4);style.paragraph_format.line_spacing=1.03
    doc.styles['Normal'].font.size=Pt(9)
    doc.styles['Title'].font.size=Pt(20);doc.styles['Heading 1'].font.size=Pt(12);doc.styles['Heading 2'].font.size=Pt(10)
    def para(txt,size=None):
        p=doc.add_paragraph(str(txt));p.paragraph_format.widow_control=True
        if size:
            for run in p.runs:run.font.size=Pt(size)
        return p
    doc.add_paragraph('Phân tích bảo hiểm và mô phỏng tín nhiệm' if report_type=='rating' else 'Phân tích tài chính và định giá bảo hiểm','Title')
    doc.add_paragraph(ticker+' '+str(meta.get('DisplayName',ticker)),'Subtitle')
    para('Tác giả Lê Hoàng Quân. Phiên bản V8.119.0. Kỳ tài chính '+str(pack[0]['Period'])+'.')
    para('Báo cáo đối chiếu từng chỉ tiêu qua '+str(years)+' năm và giữa doanh nghiệp với peer ở quý gần nhất. Mục đích là đánh giá xu hướng, hiệu quả, khả năng hấp thụ rủi ro và các bằng chứng cần thiết cho thẩm định.')
    para('Phạm vi: '+str(meta.get('InsuranceScope','Chưa xác nhận loại hình'))+'. Phương pháp tham chiếu: Phương pháp XHTN Công ty Bảo hiểm Phi Nhân thọ Saigon Ratings, cập nhật 20.01.2025.')
    para('Bậc mô phỏng hiện tại: Anchor '+rr.get('Anchor','N/A')+'; SCA '+rr.get('SCA','N/A')+'; ICR '+rr.get('ICR','N/A')+'. '+('Đã nhập đủ bằng chứng, chờ phê duyệt.' if rr.get('AssessmentComplete') else 'Chưa đủ đầu vào hoặc ngoài phạm vi phương pháp; không tự gán điểm từ dữ liệu thiếu.'))
    para('Đây là tài liệu nghiên cứu và mô phỏng, không phải kết quả xếp hạng đã được phê duyệt hoặc khuyến nghị đầu tư.')
    doc.add_heading('Cơ sở đọc số liệu',1)
    para('Lịch sử: '+BASIS_LABELS[basis]+'. Quý so sánh là quý gần nhất có BCTC của doanh nghiệp; dòng thu nhập/chi phí lấy quý riêng lẻ, số dư lấy cuối quý. ROE/ROA/PB/PE giữ cơ sở tỷ số nguồn, không coi là tỷ suất quý hay cộng tỷ số. Dự phòng/phí tại quý dùng phí TTM và ghi rõ.')
    para('Peer cùng mô hình: '+(', '.join(peer_universe(ticker)) or 'chưa có')+'. Loại chính doanh nghiệp; không thay quý thiếu bằng quý khác. Chỉ công bố bình quân/trung vị khi có ít nhất 5 peer cùng cơ sở. Mẫu niêm yết hiện có chưa chứng minh bao phủ ít nhất 60% số doanh nghiệp toàn ngành theo phương pháp.')
    para('Tỷ lệ khai thác được tính theo quy ước BCTC thuần nêu tại từng chỉ tiêu; cần chuyên viên kiểm tra tính tương thích trước khi chấm điểm. Dữ liệu thuyết minh chưa có được giữ thiếu, kể cả vốn pháp định, nghĩa vụ bảo hiểm và tài sản đủ điều kiện thanh khoản.')
    doc.add_heading('Danh mục phân tích',1)
    for g in dict.fromkeys(p['Group'] for p in pack):para(re.sub(r'^\d+\. ','',g))
    if report_type=='analysis':
        from scripts.universal_data import get_snapshot
        v=valuation(ticker,get_snapshot(ticker));fv=fair_value_range(ticker)
        doc.add_heading('Định giá tham khảo',1)
        para(str(v.get('PrimaryMethod',''))+'. '+str(v.get('Reason','')))
        _table(doc,['Kịch bản','Giá trị đồng mỗi cổ phiếu'],[[k,fmt('FairValue',fv.get(k),v.get('Status'))] for k in ['Bear','Base','Bull','StrategicMA']],[80,98])
    for i,pair in enumerate(pack):
        if i%2==0:doc.add_page_break()
        m=pair['Metric'];h=pair['History'];p=pair['Peers']
        doc.add_heading(str(i+1)+' '+pair['Label'].replace('/',' trên '),1)
        para(re.sub(r'^\d+\. ','',pair['Group']),8)
        doc.add_picture(pair_image(pair),width=Mm(176))
        # Hai bảng số nhỏ đi cùng hai biểu đồ, không để người đọc ước lượng số.
        if len(h):
            _table(doc,['Lịch sử']+h.DisplayPeriod.tolist(),[[ticker]+[fmt(m,r.Value,r.Status,True) if r.Status=='OK' else '—' for r in h.itertuples()]],[25]+[153/len(h)]*len(h))
        if len(p):
            _table(doc,['Quý '+str(pair['Period'])]+p.Ticker.tolist(),[['Giá trị']+[fmt(m,r.Value,r.Status,True) if r.Status=='OK' else '—' for r in p.itertuples()]],[25]+[153/len(p)]*len(p))
        para(pair['HistoryText'],8.5);para(pair['PeerText'],8.5);para(pair['MethodNote'],8)
    doc.add_page_break();doc.add_heading('Thẩm định các yếu tố định tính và dự báo',1)
    para('Các yếu tố phi tài chính được đánh giá bằng bằng chứng hiện tại, lịch sử và dự báo hai năm. Không tạo biểu đồ số cho dữ liệu định tính chưa có. Mỗi yếu tố dưới đây cần lập luận và nguồn, kể cả khi kết luận trung lập.')
    rows=rr.get('SubfactorEvidence',rubric_rows())
    for group in dict.fromkeys(r['Nhóm'] for r in rows):
        doc.add_heading(re.sub(r'^[IVX]+\. ','',group),2)
        for row in [x for x in rows if x['Nhóm']==group]:
            p=para(row['Chỉ tiêu']+'  '+row['Đánh giá'],9)
            p.paragraph_format.keep_with_next=True
            para(row['Hướng dẫn'],8.5)
            if row['Lập luận'] or row['Nguồn']:para('Lập luận: '+row['Lập luận']+'. Nguồn: '+row['Nguồn'],8.5)
    doc.add_heading('Tổng hợp ma trận và quyết định',1)
    _table(doc,['Cấu phần','Kết quả'],[[r['Cấu phần'],r['Kết quả']] for r in insurance_scorecard(rr)],[102,76])
    para('Đầu vào có bằng chứng: '+str(rr.get('AssessmentInputCount',0))+'/'+str(rr.get('AssessmentInputTotal',0))+'.')
    for key in ['DecisionReason','SupportSource']:
        val=rr.get('AssessmentInputs',{}).get(key)
        if val:para(val)
    doc.add_heading('Nguồn và khả năng kiểm tra',1)
    para('Số liệu tài chính lấy từ các tệp data/raw/{Mã}_balance.csv, _income.csv và _ratio.csv trong project; nhận diện bằng mã semantic, không đọc cột thứ tự/cấp độ thành số tài chính. Dòng quý lũy kế chỉ tách được khi đủ quý trước. Đầu vào bổ sung phải có kỳ, cơ sở, nguồn, phạm vi và người duyệt trong config/insurance_metric_inputs.csv.')
    para('Phân loại peer được lưu cùng nguồn trong config/insurance_entities.csv. BCTC BVH/PVI là tập đoàn; PRE/VNR là tái bảo hiểm, không tự áp ma trận phi nhân thọ. So sánh hai tập đoàn chỉ là đối chiếu quy mô và tài chính; cơ cấu hoạt động vẫn khác nhau.')
    para('Tài liệu phương pháp gốc: 4. Phương pháp XHTN Công ty Bảo hiểm Phi Nhân thọ 2025(1).docx, ngày 20.01.2025. Tham chiếu Bảng 01–02, 04–18 và các mục vốn, linh hoạt tài chính, thanh khoản, điều chỉnh và hỗ trợ bên ngoài. Quy tắc chưa định lượng không được thay bằng điểm mặc định.')
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT;footer.add_run(ticker+'   V8.119.0   ')
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
    for scope in [doc.element,doc.styles.element]:
        for el in list(scope.iter(qn('w:pBdr'))):el.getparent().remove(el)
        for el in scope.iter(qn('w:color')):
            el.attrib.pop(qn('w:themeColor'),None)
    out=BytesIO();doc.save(out);return out.getvalue()
