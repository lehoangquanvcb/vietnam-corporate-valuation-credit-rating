"""Mẫu Word xanh theo báo cáo tham chiếu; bằng chứng cùng nguồn với giao diện."""
from io import BytesIO
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker as mticker
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from scripts.universal_data import get_company, get_snapshot
from scripts.report_rating import rate_company
from scripts.report_identity import export_date, report_header, NOTICE
from scripts.financial_views import HISTORY_METRICS, BASIS_LABELS
from scripts.report_evidence import (build_pack, narrative, cross_findings, findings, fmt, finite,
    unit, scale, vi, label, basis_text, ENGINE_VERSION)
from scripts.report_methodology import REPORT_TITLE, RESEARCH_NOTE, LIMITATION_NOTE, SOURCES, chapter_findings

GREEN='4F9E1E'; DARK='2F6F12'; PALE='E6F3D8'; GRAY='56624F'
TYPE_LABELS={'BANK':'Ngân hàng','SECURITIES':'Chứng khoán','CORPORATE':'Doanh nghiệp phi tài chính','INSURANCE':'Bảo hiểm phi nhân thọ'}
FACTOR_LABELS={'CapitalAdjustmentNotches':'Điều chỉnh chất lượng vốn và lợi nhuận','FundingStrongExceptionConfirmed':'Điều kiện tăng bậc huy động và thanh khoản','BusinessProfile':'Hồ sơ kinh doanh','CapitalEarnings':'Vốn và lợi nhuận',
 'RiskPosition':'Vị thế rủi ro','FundingLiquidity':'Nguồn vốn và thanh khoản',
 'InternalNotches':'Điều chỉnh nội tại','ModifierNotches':'Điều chỉnh bổ sung',
 'ExternalSupportNotches':'Hỗ trợ bên ngoài','CombinedRiskScore':'Điểm rủi ro tổng hợp',
 'FinancialRiskScore':'Điểm rủi ro tài chính','WeightedScore':'Điểm có trọng số',
 'BusinessRisk':'Rủi ro kinh doanh','FinancialRisk':'Rủi ro tài chính','Liquidity':'Thanh khoản',
 'ManagementGovernance':'Quản trị và điều hành','ComparableRatingAnalysis':'So sánh xếp hạng'}
for _f in (Path(__file__).resolve().parents[1]/'assets/fonts').glob('Lato-*.ttf'):
    font_manager.fontManager.addfont(str(_f))

def _font(run,size=10.5,bold=False,color='000000'):
    run.font.name='Lato';run.font.size=Pt(size);run.bold=bold;run.font.color.rgb=RGBColor.from_string(color)
    fonts=run._element.get_or_add_rPr().get_or_add_rFonts()
    for key in ('ascii','hAnsi','eastAsia','cs'):fonts.set(qn('w:'+key),'Lato')

def _shade(cell,fill):
    sh=OxmlElement('w:shd');sh.set(qn('w:fill'),fill);cell._tc.get_or_add_tcPr().append(sh)

def _para(doc,text,size=10.5,bold=False,keep=False,color='000000',lead=None):
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    pf=p.paragraph_format;pf.space_after=Pt(6);pf.line_spacing=1.08
    pf.keep_with_next=keep;pf.widow_control=True;pf.keep_together=True
    if lead:_font(p.add_run(lead+' '),size,True,color)
    _font(p.add_run(str(text)),size,bold,color)
    return p

def _band(doc,text,level=1):
    p=doc.add_paragraph(style='Heading '+str(level));p.paragraph_format.keep_with_next=True
    p.paragraph_format.space_before=Pt(8);p.paragraph_format.space_after=Pt(8)
    _font(p.add_run(text),12 if level==1 else 11,True,'FFFFFF' if level==1 else DARK)
    if level==1:
        sh=OxmlElement('w:shd');sh.set(qn('w:fill'),GREEN);p._p.get_or_add_pPr().append(sh)
        p.paragraph_format.left_indent=Mm(2);p.paragraph_format.right_indent=Mm(2)
    return p

def _table(doc,headers,rows,widths,font_size=9):
    t=doc.add_table(rows=1,cols=len(headers));t.autofit=False;t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for c,w in zip(t.columns,widths):c.width=Mm(w)
    for c,h in zip(t.rows[0].cells,headers):c.text=str(h)
    for row in rows:
        for c,v in zip(t.add_row().cells,row):c.text=re.sub(r'\bvn(?=[A-C])','',str(v))
    for i,row in enumerate(t.rows):
        pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
        if i==0:pr.append(OxmlElement('w:tblHeader'))
        for j,(c,w) in enumerate(zip(row.cells,widths)):
            c.width=Mm(w);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tc=c._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');b.append(e)
            tc.append(b);_shade(c,PALE if i==0 else 'F6F9F2' if i%2==0 else 'FFFFFF')
            mar=OxmlElement('w:tcMar')
            for edge,n in [('top',65),('bottom',65),('left',80),('right',80)]:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),str(n));e.set(qn('w:type'),'dxa');mar.append(e)
            tc.append(mar)
            for p in c.paragraphs:
                p.paragraph_format.space_after=Pt(1);p.paragraph_format.line_spacing=1.05
                if len(t.rows)<=4:p.paragraph_format.keep_with_next=i<len(t.rows)-1
                p.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 or headers[j] in {'Kết quả / Căn cứ','ĐIỂM HẠN CHẾ VÀ RỦI RO','Căn cứ'} else WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:_font(r,font_size,i==0)
    return t

def _style(doc,ticker,when=None,report_type="rating"):
    sec=doc.sections[0];sec.page_width=Mm(210);sec.page_height=Mm(297)
    sec.left_margin=Mm(17);sec.right_margin=Mm(17);sec.top_margin=Mm(17);sec.bottom_margin=Mm(21)
    sec.header_distance=Mm(8);sec.footer_distance=Mm(8);sec.different_first_page_header_footer=True
    for name,size in [('Normal',10.5),('Title',26),('Subtitle',17),('Heading 1',12),('Heading 2',11)]:
        style=doc.styles[name];style.font.name='Lato';style.font.size=Pt(size);style.font.color.rgb=RGBColor(0,0,0)
        style.paragraph_format.space_after=Pt(6)
    header=sec.header.paragraphs[0]
    header.paragraph_format.space_after=Pt(0)
    _font(header.add_run(report_header(ticker,when,report_type)),8,False,GRAY)
    for footer in (sec.footer,sec.first_page_footer):
        p=footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1
        _font(p.add_run(NOTICE),7.5,False,GRAY)
        p=footer.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_after=Pt(0)
        _font(p.add_run('Trang '),7.5,False,GRAY)
        field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');p._p.append(field)
    for el in list(doc.styles.element.iter(qn('w:pBdr'))):el.getparent().remove(el)
    for name in ('Title','Subtitle','Heading 1','Heading 2'):
        for el in doc.styles[name].element.iter(qn('w:color')):
            for attr in ('themeColor','themeTint','themeShade'):el.attrib.pop(qn('w:'+attr),None)

def _show_rating(v):
    return 'Chưa xác định' if v is None or str(v) in ('N/A','nan','None','') else re.sub(r'^vn(?=[A-C])','',str(v))

def _embed_fonts(doc):
    """Nhúng Lato theo OOXML để Word/PDF không phụ thuộc phông cài trên máy."""
    from uuid import uuid5, NAMESPACE_URL
    from lxml import etree
    from docx.opc.part import Part
    from docx.opc.packuri import PackURI
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    part=doc.part.part_related_by(RT.FONT_TABLE);root=etree.fromstring(part.blob)
    node=next((f for f in root if f.get(qn('w:name'))=='Lato'),None)
    if node is None:
        node=OxmlElement('w:font');node.set(qn('w:name'),'Lato');root.append(node)
        family=OxmlElement('w:family');family.set(qn('w:val'),'swiss');node.append(family)
    for style,tag in [('Regular','embedRegular'),('Bold','embedBold'),('Italic','embedItalic'),('BoldItalic','embedBoldItalic')]:
        path=Path(__file__).resolve().parents[1]/'assets/fonts'/('Lato-'+style+'.ttf')
        if not path.exists():continue
        key=uuid5(NAMESPACE_URL,'valuation/Lato/'+style);data=bytearray(path.read_bytes());mask=key.bytes[::-1]
        for i in range(32):data[i]^=mask[i%16]
        font=Part(PackURI('/word/fonts/Lato-'+style+'.odttf'),'application/vnd.openxmlformats-officedocument.obfuscatedFont',bytes(data),doc.part.package)
        rel=part.relate_to(font,RT.FONT);embed=OxmlElement('w:'+tag)
        embed.set(qn('r:id'),rel);embed.set(qn('w:fontKey'),'{'+str(key).upper()+'}');node.append(embed)
    part._blob=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
    setting=OxmlElement('w:embedTrueTypeFonts');doc.settings.element.append(setting)

def _cover(doc,pack,report_type,when=None):
    name=pack['Meta'].get('DisplayName') or pack['Meta'].get('CompanyName') or pack['Ticker']
    doc.add_paragraph().paragraph_format.space_after=Mm(18)
    t=doc.add_table(rows=1,cols=1);t.autofit=False;t.columns[0].width=Mm(176)
    c=t.cell(0,0);c.width=Mm(176);_shade(c,GREEN)
    mar=OxmlElement('w:tcMar')
    for edge,value in [('top',360),('bottom',360),('left',240),('right',240)]:
        e=OxmlElement('w:'+edge);e.set(qn('w:w'),str(value));e.set(qn('w:type'),'dxa');mar.append(e)
    c._tc.get_or_add_tcPr().append(mar)
    title=REPORT_TITLE if report_type=='rating' else 'BÁO CÁO PHÂN TÍCH ĐỊNH GIÁ VÀ M&A'
    q=c.paragraphs[0];q.style='Title';q.paragraph_format.space_after=Pt(14)
    _font(q.add_run(title),24,True,'FFFFFF')
    q=c.add_paragraph();_font(q.add_run(str(name)+' ('+pack['Ticker']+')'),18,True,'FFFFFF')
    _para(doc,'NGÀNH: '+TYPE_LABELS[pack['Type']].upper(),11,True).paragraph_format.space_before=Pt(8)
    _para(doc,'QUỐC GIA: VIỆT NAM',11,True)
    doc.add_paragraph().paragraph_format.space_after=Mm(12)
    first=next((x['History'] for x in pack['Items'].values() if len(x['History'])),None)
    years='–'.join([str(first.DisplayPeriod.iloc[0]),str(first.DisplayPeriod.iloc[-1])]) if first is not None else '5 năm gần nhất'
    for text in ['Kỳ so sánh peer: '+str(pack['Period']),'Lịch sử BCTC năm: '+years,
                 'Tác giả: Lê Hoàng Quân, phát hành ngày '+export_date(when).strftime('%d/%m/%Y')]:_para(doc,text,10,color=GRAY)
    _para(doc,LIMITATION_NOTE,9,color=GRAY)
    doc.add_page_break()


def _normalize_page_breaks(doc):
    """Gắn ngắt trang vào tiêu đề kế tiếp, không tạo trang trắng khi vừa đầy trang."""
    from docx.text.paragraph import Paragraph
    for node in list(doc.element.body):
        if node.tag!=qn('w:p'):continue
        p=Paragraph(node,doc);nxt=node.getnext()
        if not p.text.strip() and any(b.get(qn('w:type'))=='page' for b in node.findall('.//'+qn('w:br'))):
            if nxt is not None and nxt.tag==qn('w:p'):
                Paragraph(nxt,doc).paragraph_format.page_break_before=True
                node.getparent().remove(node)

def _cell_para(cell,text,size=10,bold=False,color='000000'):
    p=cell.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after=Pt(6);p.paragraph_format.line_spacing=1.05
    _font(p.add_run(text),size,bold,color);return p

def _summary(doc,pack,rr,report_type):
    _band(doc,str(pack['Meta'].get('DisplayName',pack['Ticker'])).upper()+' ('+pack['Ticker']+')')
    if report_type=='rating':
        t=doc.add_table(rows=1,cols=2);t.autofit=False
        for col,w in zip(t.columns,[57,119]):col.width=Mm(w)
        left,right=t.rows[0].cells
        for cell,w in zip([left,right],[57,119]):
            cell.width=Mm(w);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.TOP
            for p0 in cell.paragraphs:p0.paragraph_format.space_after=Pt(5)
            mar=OxmlElement('w:tcMar')
            for edge,n in [('top',130),('bottom',100),('left',150),('right',150)]:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),str(n));e.set(qn('w:type'),'dxa');mar.append(e)
            cell._tc.get_or_add_tcPr().append(mar)
        _shade(left,PALE);_font(left.paragraphs[0].add_run('KẾT QUẢ XẾP HẠNG'),11,True)
        _font(right.paragraphs[0].add_run('LUẬN ĐIỂM XẾP HẠNG'),11,True)
        rating='Ngoài phạm vi phương pháp' if rr.get('RatingBlocker')=='SCOPE' else _show_rating(rr.get('ICR'))
        _cell_para(left,rating,26 if rr.get('ICR') not in (None,'N/A','') else 14,True,DARK)
        for title,value in [('Triển vọng',rr.get('Outlook')),('Anchor',rr.get('Anchor')),('SACP / SCA',rr.get('SACP',rr.get('SCA'))),('Hỗ trợ bên ngoài',str(rr['ExternalSupportNotches'])+' bậc' if rr.get('ExternalSupportNotches') is not None else None)]:
            if value:_cell_para(left,title+': '+_show_rating(value),10)
        _cell_para(left,'Kỳ tài chính: '+str(pack['Period']),9)
        _cell_para(left,'BCTC 5 năm và peer quý gần nhất',9)
        if rr.get('RatingOrigin')=='AUTO_RESEARCH':
            _cell_para(left,'Bậc ước tính tự động',9,True,DARK)
            _cell_para(left,'Theo các giả định công bố cuối báo cáo',9,False,GRAY)
        if rr.get('DomesticCalibrationApplied'):
            _cell_para(left,'Bậc hiệu chỉnh trong nước',9,True,DARK)
            _cell_para(left,'Trước hiệu chỉnh: '+_show_rating(rr['RawICR']),9)
            _cell_para(left,'Hiệu chỉnh: '+f"{rr['DomesticCalibrationNotches']:+d}"+' bậc',9)
        if str(rr.get('RatingOrigin','')).startswith('REFERENCE_REPORT'):
            _cell_para(left,'Kế thừa bảng chấm trong báo cáo tham chiếu',9,False,GRAY)
        if rr.get('ICR') not in (None,'N/A',''):
            text=('Bậc hiệu chỉnh trong nước ' if rr.get('DomesticCalibrationApplied') else 'Bậc xếp hạng ước tính ' if rr.get('RatingOrigin')=='AUTO_RESEARCH' else 'Kết quả xếp hạng ')+rating+'; Anchor '+_show_rating(rr.get('Anchor'))+'.'
            if rr.get('InternalNotches') is not None:text+=' Điều chỉnh nội tại '+str(rr['InternalNotches'])+' bậc.'
            if rr.get('ExternalSupportNotches') is not None:text+=' Hỗ trợ bên ngoài '+str(rr['ExternalSupportNotches'])+' bậc.'
            if rr.get('DomesticCalibrationApplied'):
                text+=' Từ bậc '+_show_rating(rr['RawICR'])+', hiệu chỉnh theo nhóm '+f"{rr['DomesticCalibrationNotches']:+d}"+' bậc. Mức đích của chủ mô hình được tách khỏi năng lực tín dụng độc lập và mức CRA công bố.'
            _cell_para(right,text,10)
        if pack['Type']=='BANK':
            from scripts.bank_report_chapters import chapter_findings
            texts=[chapter_findings(pack,k,rr) for k in ['Vốn và Lợi nhuận','Vị thế Rủi ro','Huy động vốn và Thanh khoản']]
            for rows in texts:
                if rows:_cell_para(right,rows[0],10)
        else:
            for text in cross_findings(pack)[:3]:_cell_para(right,text,10)
        if str(rr.get('RatingOrigin','')).startswith('REFERENCE_REPORT'):
            _para(doc,'Nguồn bảng chấm: '+re.sub(r'[_ |–-]*V?8[._]\d+(?:[._]\d+)?(?:-[A-Z-]+)?','',rr.get('AssessmentSource',''))+'; kỳ '+rr.get('AssessmentPeriod','')+'. Bậc được tính lại từ các đánh giá trong nguồn, không phải kết luận thẩm định mới.',8.5,color=GRAY)
        if rr.get('DomesticCalibrationApplied'):
            _para(doc,rr['RatingBasisNote'],8.5,color=GRAY)
        if rr.get('DomesticBenchmark'):
            from scripts.bank_domestic_rating import benchmark_text
            _para(doc,benchmark_text(rr['DomesticBenchmark']),8.5,color=GRAY)
    else:
        _band(doc,'LUẬN ĐIỂM PHÂN TÍCH',2)
        for text in cross_findings(pack)[:3]:_para(doc,text,10)
    _band(doc,'NHỮNG NHÂN TỐ CHÍNH DẪN ĐẾN KẾT QUẢ XẾP HẠNG' if report_type=='rating' else 'ĐIỂM MẠNH VÀ RỦI RO')
    good,bad=findings(pack)
    _table(doc,['ĐIỂM MẠNH','ĐIỂM HẠN CHẾ VÀ RỦI RO'],[
        ['\n'.join(good) or 'Chưa có kết luận so sánh.','\n'.join(bad) or 'Chưa có kết luận so sánh.']], [88,88],9.5)
    if pack['Type']=='BANK':
        from scripts.bank_report_chapters import chapter_findings
        rows=chapter_findings(pack,'Huy động vốn và Thanh khoản',rr)
        if len(rows)>1:_para(doc,rows[1],10)
    doc.add_page_break()

def _context(doc,pack):
    from scripts.company_profile import load_company_profile,profile_source_text
    from scripts.public_research import load_public_research
    _band(doc,'THÔNG TIN TỔNG QUAN TỔ CHỨC PHÁT HÀNH')
    profile=load_company_profile(pack['Ticker']) or {}
    text=' '.join(str(profile.get(k) or '').strip().rstrip('.')+'.' for k in ['Overview','CoreBusinesses','Strategy'] if profile.get(k))
    _para(doc,text or (str(pack['Meta'].get('DisplayName',pack['Ticker']))+' thuộc nhóm '+TYPE_LABELS[pack['Type']]+'. Hồ sơ hoạt động chi tiết chưa có trong dữ liệu lưu sẵn.'))
    if profile:_para(doc,profile_source_text(pack['Ticker']),8.5,color=GRAY)
    for title,kind in [('RỦI RO VĨ MÔ','MACRO'),('RỦI RO NGÀNH','INDUSTRY')]:
        rows=load_public_research(ticker=pack['Ticker'],entity_type=pack['Type'],sector=pack['Meta'].get('Sector'),kind=kind,limit=1)
        if rows:
            _band(doc,title)
            row=rows[0];_para(doc,row.get('Narrative',''),10)
            _para(doc,'Nguồn hồ sơ lưu sẵn: '+str(row.get('Source') or 'chưa ghi tên')+' • Ngày nguồn '+str(row.get('AsOf') or 'chưa ghi ngày')+'.',8.5,color=GRAY)
    # Khi chưa có hồ sơ vĩ mô/ngành, không thay bằng định nghĩa phương pháp.

def _overview(doc,pack):
    _band(doc,'LỊCH SỬ TÀI CHÍNH 5 NĂM GẦN NHẤT')
    first=next((x['History'] for x in pack['Items'].values() if len(x['History'])),None)
    if first is None:_para(doc,'Chưa có dữ liệu lịch sử với kỳ xác định.');return
    cols=list(first.DisplayPeriod);rows=[]
    for m in HISTORY_METRICS[pack['Type']]:
        h=pack['Items'][m]['History'];rows.append([label(m),unit(m)]+[fmt(m,v,False) for v in h.Value])
    table=_table(doc,['Chỉ tiêu','Đơn vị']+cols,rows,[42,16]+[118/len(cols)]*len(cols),8)
    # The compact five-year overview fits on one page. Move it as a block
    # instead of leaving its last row alone on the next page.
    for row in table.rows[:-1]:
        for cell in row.cells:
            for p in cell.paragraphs:p.paragraph_format.keep_with_next=True
    _para(doc,'BCTC năm: số dư tại cuối năm, kết quả kinh doanh và dòng tiền cả năm; tỷ số công bố tại cuối năm. Đơn vị tiền tệ: tỷ đồng.',9,color=GRAY)
    _band(doc,'Các trọng tâm tài chính',2)
    for text in cross_findings(pack)[:2]:_para(doc,text,10)

def _chart(pack,m,kind):
    x=pack['Items'][m];h=x['History'];sc=scale(m)
    font='Lato' if any(f.name=='Lato' for f in font_manager.fontManager.ttflist) else 'DejaVu Sans'
    with plt.rc_context({'font.family':font,'font.size':9}):
        fig,ax=plt.subplots(figsize=(6.9,1.7 if kind=='history' else 1.55),dpi=170)
        if kind=='history':
            if len(h):
                _plot_segments(ax,h.Value*sc,x.get('HistoryBreaks',[]),'#2F6F12','o-',pack['Ticker'])
                if h.PeerMean.notna().any():_plot_segments(ax,h.PeerMean*sc,x.get('PeerHistoryBreaks',[]),'#BA7A22','s--','Bình quân peer cùng kỳ')
                ax.set_xticks(range(len(h)),h.DisplayPeriod,fontsize=9)
                ax.legend(loc='lower left',bbox_to_anchor=(0,1),ncol=2,fontsize=8,frameon=False)
            if not len(h) or not h.Value.notna().any():ax.text(.5,.45,'Chưa có chuỗi doanh nghiệp',ha='center',transform=ax.transAxes)
        else:
            rows=([{'Ticker':pack['Ticker'],'Value':x['Value']}] if finite(x['Value']) else [])+x['Peers']
            if rows:
                ax.bar([r['Ticker'] for r in rows],[r['Value']*sc for r in rows],color=['#4F9E1E' if r['Ticker']==pack['Ticker'] else '#B2BEA8' for r in rows],width=.65)
                if finite(x['PeerMean']):
                    ax.axhline(x['PeerMean']*sc,color='#BA7A22',ls='--',lw=1,label='Bình quân peer')
                    ax.legend(loc='lower left',bbox_to_anchor=(0,1),fontsize=8,frameon=False)
                ax.tick_params(axis='x',labelsize=7 if len(rows)>20 else 9,rotation=45 if len(rows)>14 else 0)
            else:
                ax.text(.5,.5,'Chưa có số cùng kỳ và cơ sở',ha='center',transform=ax.transAxes)
                ax.set_xticks([]);ax.set_yticks([]);ax.axis('off')
        ax.set_ylabel(unit(m),fontsize=8);ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,pos:vi(v,2 if unit(m)=='lần' else 1)))
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
        ax.tick_params(axis='y',labelsize=8);fig.tight_layout(pad=.5)
        out=BytesIO();fig.savefig(out,format='png');plt.close(fig);out.seek(0);return out

def _plot_segments(ax,values,breaks,color,style,label):
    """Ngắt đường trước điểm đổi phạm vi mà vẫn hiển thị đủ giá trị từng năm."""
    stops=[0]+sorted(set(i for i in breaks if 0<i<len(values)))+[len(values)]
    for index,(a,b) in enumerate(zip(stops,stops[1:])):
        ax.plot(range(a,b),values.iloc[a:b],style,lw=1.5,markersize=3,color=color,label=label if index==0 else None)

def _picture(doc,bio,keep=False):
    p=doc.add_paragraph();p.paragraph_format.space_after=Pt(3);p.paragraph_format.keep_with_next=keep;p.add_run().add_picture(bio,width=Mm(176))

def _metric_page(doc,pack,group,m):
    x=pack['Items'][m];h=x['History'];n=narrative(pack,m)
    _band(doc,label(m),2)
    if m=='CAR' and pack['Type']=='BANK':
        from scripts.bank_car import car_usage_text
        text=car_usage_text(pack.get('CARInput',{}),pack.get('Period'))
        if text:_para(doc,text,9,color=GRAY,keep=True)
    _para(doc,n['History'],10,lead='Diễn biến doanh nghiệp',keep=True)
    _para(doc,'BCTC 5 năm gần nhất và bình quân peer',9,True,keep=True,color=DARK);_picture(doc,_chart(pack,m,'history'),keep=True)
    if len(h):
        rows=[[pack['Ticker']]+[fmt(m,v,False) for v in h.Value],['Bình quân peer']+[fmt(m,v,False) for v in h.PeerMean]]
        _table(doc,[unit(m)]+list(h.DisplayPeriod),rows,[31]+[145/len(h)]*len(h),8)
    _para(doc,n['Peers'],10,lead='So sánh quý gần nhất',keep=True)
    _para(doc,str(pack['Period'] or 'Chưa xác định kỳ')+' • '+basis_text(x['Record'].get('Basis'))+' | '+label(m),9,True,keep=True,color=DARK)
    if m!='CAR' or finite(x['Value']) or x['Peers']:
        _picture(doc,_chart(pack,m,'quarter'),keep=True)
    _para(doc,(n['Meaning']+' '+n['Conclusion']).strip(),10,lead='Đánh giá')

def _readable(text):
    from scripts.methodology_kpi_engine import LABELS
    from scripts.report_evidence import EXTRA_LABELS
    text=str(text).replace('_metrics',' — chỉ tiêu cần bổ sung')
    for key,val in sorted({**LABELS,**EXTRA_LABELS,**FACTOR_LABELS}.items(),key=lambda kv:-len(kv[0])):text=re.sub(r'\b'+re.escape(key)+r'\b',val,text)
    return text

def _sources(doc,pack,rr=None):
    doc.add_page_break();_band(doc,'NGUỒN VÀ PHẠM VI BÁO CÁO')
    _para(doc,'BCTC và tỷ số tài chính lưu trong ứng dụng; lịch sử sử dụng 5 năm tài chính đã kết thúc gần nhất. So sánh peer dùng số dư cuối quý, dòng thu nhập quý riêng lẻ và tỷ số công bố tại quý gần nhất. Tỷ số trả nợ dùng dòng tiền 12 tháng kết thúc tại kỳ so sánh.',10)
    _para(doc,'Nhóm peer: '+', '.join(pack['PeerUniverse'])+'. Bình quân loại chính doanh nghiệp, dùng các công ty có cùng kỳ và cơ sở tính; chỉ trình bày khi có ít nhất 5 peer. Thành phần có số có thể thay đổi theo năm và chỉ tiêu.',10)
    _para(doc,'Phương pháp áp dụng: '+SOURCES[pack['Type']]+'.',10)
    rr=rr or {}
    if rr.get('DomesticPolicy'):
        _para(doc,'Khung hiệu chỉnh: '+rr['DomesticPolicy']['Source']+'. SACP và bảng điểm tài chính gốc được lưu riêng; mức đích không thay thế đánh giá tín dụng độc lập.',9)
    if rr.get('DomesticBenchmark'):
        from scripts.bank_domestic_rating import benchmark_text
        _para(doc,benchmark_text(rr['DomesticBenchmark']),9)
        _para(doc,'Nguồn tham khảo CRA: '+rr['DomesticBenchmark']['URL'],8,color=GRAY).alignment=WD_ALIGN_PARAGRAPH.LEFT
    if pack['Type']=='BANK':
        from scripts.bank_funding import observations
        funding=observations(pack['Ticker'],pack['Period'])
        if funding:
            _para(doc,'Nguồn huy động và thanh khoản: '+funding['Source']+'; kỳ '+funding['Period']+'. '+funding['BasisNote'],9,color=GRAY)
            _para(doc,funding['SourceURL'],9,color=GRAY).alignment=WD_ALIGN_PARAGRAPH.LEFT
        if rr.get('FundingAssessment'):
            _para(doc,'Nguồn đánh giá cấu phần huy động và thanh khoản: '+rr['FundingAssessment']['Source']+'. Chỉ áp dụng cho kỳ '+rr['FundingAssessment']['Period']+'.',9,color=GRAY)
        from scripts.bank_car import car_usage_text
        from scripts.financial_evidence import at_period
        car=pack.get('CARInput',{})
        records=[car]
        history=pack['Items'].get('CAR',{}).get('History')
        if history is not None:
            for p in history.get('Period',[]):
                if p!=car.get('Period'):
                    records.append(at_period(pack['Ticker'],'BANK',p,'FY').get('CAR',{}))
        for source in records:
            text=car_usage_text(source,pack.get('Period') if source is car else None)
            if not text:continue
            _para(doc,text,9,color=GRAY,keep=bool(source.get('SourceURL')))
            if source.get('SourceURL'):
                _para(doc,'Nguồn công bố, trang '+str(source.get('SourcePage',''))+'; '+str(source.get('Regime',''))+'.',9,color=GRAY,keep=True)
                _para(doc,source['SourceURL'],9,color=GRAY).alignment=WD_ALIGN_PARAGRAPH.LEFT
            elif source.get('SourceReference'):
                _para(doc,str(source['SourceReference'])+'; ngày cung cấp '+str(source.get('ProvidedOn',''))+'.',9,color=GRAY)
            if source.get('Note'):_para(doc,source['Note'],9,color=GRAY)
    if pack['Type']=='INSURANCE' and pack['Meta'].get('InsuranceScope'):
        _para(doc,'Phạm vi BCTC: '+str(pack['Meta']['InsuranceScope'])+'. Phân nhóm peer không thay đổi phạm vi pháp nhân của số liệu.',9,color=GRAY)
    missing=[label(m) for m,x in pack['Items'].items() if not finite(x['Value'])]
    if missing:
        note=('Biểu đồ so sánh quý giữ đúng kỳ; CAR dùng thay thế cho bảng điểm, nếu có, được nêu riêng ở trên.'
              if pack['Type']=='BANK' else 'Không thay bằng số 0 hay số kỳ cũ.')
        _para(doc,'Các chỉ tiêu chưa có giá trị quý hiện tại: '+', '.join(missing)+'. '+note,9,color=GRAY)
    for m,x in pack['Items'].items():
        for warning in x.get('HistoryWarnings',[]):_para(doc,label(m)+': '+warning,9,color=GRAY)
    _para(doc,NOTICE,9,color=GRAY)

def _scorecard(doc,pack,rr):
    from scripts.bank_report_chapters import rating_sensitivity
    _band(doc,'QUẢN TRỊ, ĐIỀU HÀNH VÀ CÁC ĐIỀU CHỈNH KHÁC')
    evidence=[r for r in rr.get('SubfactorEvidence',[]) if r.get('Đủ bằng chứng')]
    if evidence:
        for row in evidence:
            _para(doc,str(row.get('Lập luận',''))+' Nguồn: '+str(row.get('Nguồn','')),10,lead=str(row.get('Chỉ tiêu','')))
    else:
        governance=rr.get('Factors',{}).get('Quản trị và điều hành') or rr.get('AssessmentInputs',{}).get('ManagementAssessment')
        _para(doc,'Đánh giá quản trị: '+str(governance)+'.' if governance else 'Chưa có kết luận quản trị và điều hành được xác nhận trong hồ sơ hiện tại.',9,color=GRAY)
    _band(doc,'YẾU TỐ BÊN NGOÀI')
    support=rr.get('ExternalSupportNotches')
    if rr.get('DomesticCalibrationApplied'):
        _para(doc,'Hỗ trợ bên ngoài trong bảng điểm gốc: '+str(support)+' bậc; bậc trước hiệu chỉnh '+_show_rating(rr['RawICR'])+'. Hiệu chỉnh thang trong nước '+f"{rr['DomesticCalibrationNotches']:+d}"+' bậc đưa kết quả về '+_show_rating(rr['ICR'])+'. Phần hiệu chỉnh này không được ghi nhận là hỗ trợ Nhà nước hoặc chủ sở hữu.')
    elif support is not None:
        _para(doc,('Trong kịch bản tự động, hỗ trợ bên ngoài đóng góp ' if rr.get('RatingOrigin')=='AUTO_RESEARCH' else 'Hỗ trợ bên ngoài đóng góp ')+str(support)+' bậc. '+('ICR bằng SACP khi không cộng điều chỉnh hỗ trợ.' if support==0 else 'Điều chỉnh này đưa kết quả từ '+_show_rating(rr.get('SACP'))+' lên '+_show_rating(rr.get('ICR'))+'.'))
    else:_para(doc,'Chưa xác định điều chỉnh hỗ trợ bên ngoài cho kỳ xếp hạng này.')
    _band(doc,'ĐỘ NHẠY XẾP HẠNG')
    if pack['Type']=='BANK':
        _para(doc,'Áp lực hạ bậc có thể xuất hiện nếu bộ đệm vốn suy giảm, nợ xấu tăng vượt khả năng bù đắp của dự phòng và lợi nhuận, hoặc nguồn vốn mất ổn định khi tín dụng tiếp tục mở rộng. Khả năng cải thiện phụ thuộc việc duy trì vốn, hiệu quả sinh lời và chất lượng tài sản qua nhiều kỳ.')
    if pack['Type']=='INSURANCE' and pack.get('Period'):
        from scripts.insurance_narrative import sensitivity_narrative
        from scripts.financial_evidence import insurance_reporting_subtype
        sensitivity=sensitivity_narrative([x['InsurancePair'] for x in pack['Items'].values()],insurance_reporting_subtype(pack['Meta']))
        for key in ['Positive','Negative']:
            if sensitivity.get(key):_para(doc,sensitivity[key])
    elif pack['Type'] in {'SECURITIES','CORPORATE'}:
        from scripts.report_methodology import sensitivity_findings
        for text in sensitivity_findings(pack):_para(doc,text)
    rows=rating_sensitivity(rr) if pack['Type']=='BANK' else []
    if rows:
        _table(doc,['Kịch bản thay đổi đánh giá','Thay đổi bậc','Bậc trước hiệu chỉnh' if rr.get('DomesticCalibrationApplied') else 'ICR mô phỏng'],[[a,b,_show_rating(c)] for a,b,c in rows],[110,29,37],9)
        _para(doc,('Độ nhạy được tính trên bậc gốc trước hiệu chỉnh. Mức đích theo nhóm không tự thay đổi trong các kịch bản này; cần xem xét lại khung khi hồ sơ rủi ro thay đổi. ' if rr.get('DomesticCalibrationApplied') else '')+'Các kịch bản giữ nguyên cấu phần khác và hỗ trợ bên ngoài; thể hiện độ nhạy của phép tính, không phải dự báo thay đổi xếp hạng.',8.5,color=GRAY)
    _band(doc,'TỔNG KẾT CẤU PHẦN XẾP HẠNG')
    if rr.get('Scorecard'):
        headers=['Cấu phần','Điểm / Đánh giá','Tác động','Kết quả / Căn cứ']
        rows=rr['Scorecard']
        if pack['Type']=='BANK':
            from scripts.bank_report_chapters import component_scorecard
            components=component_scorecard(rr,pack)
            names={r['Cấu phần'] for r in components}
            rows=([r for r in rows if r['Cấu phần']=='Anchor']+components+
                  [r for r in rows if r['Cấu phần'] not in names|{'Anchor'}])
        _table(doc,headers,[[row.get(h,'') for h in headers] for row in rows],[43,36,23,74],9)
        if rr.get('QuantitativeEvidence'):
            if pack['Type']=='BANK':
                doc.add_page_break()
                _band(doc,'PHỤ LỤC: CĂN CỨ TÍNH ĐIỂM VÀ GIẢ ĐỊNH')
            else:
                _band(doc,'CĂN CỨ ĐỊNH LƯỢNG CỦA BẢNG ĐIỂM',2)
            rows=[]
            for e in rr['QuantitativeEvidence']:
                value=e.get('Giá trị')
                displayed=(vi(value,3)+' lần' if e.get('Metric') in ('LiabilitiesEquity','EBITDAInterest') else fmt(e.get('Metric',''),value)) if finite(value) else '—'
                period=str(e.get('Kỳ',''));period=('TTM đến '+period.split('|')[-1]) if '|' in period else period
                rows.append([e['Chỉ tiêu'],displayed,vi(e['Điểm'],3) if finite(e.get('Điểm')) else '—',period,e['Cách chấm']])
            _table(doc,['Chỉ tiêu','Giá trị','Điểm','Kỳ','Căn cứ'],rows,[38,27,16,35,60],8)
        if rr.get('Assumptions'):
            _band(doc,'GIẢ ĐỊNH SỬ DỤNG CHO BẬC ƯỚC TÍNH',2)
            _para(doc,rr.get('RatingBasisNote',''),9,bold=True,color=DARK)
            for i,text in enumerate(rr['Assumptions'],1):_para(doc,str(i)+'. '+text,9)
    elif pack['Type']=='INSURANCE':
        from scripts.insurance_rating import INPUT_LABELS
        score_fields={'CombinedRiskScore':'Rủi ro kinh doanh tổng hợp','CapitalEarningsScore':'Nguồn vốn và lợi nhuận',
                      'FinancialRiskScore':'Rủi ro tài chính','FinancialFlexibilityScore':'Linh hoạt tài chính'}
        rows=[[title,vi(rr[k],1) if finite(rr.get(k)) else 'Chưa xác định'] for k,title in score_fields.items()]
        rows += [[INPUT_LABELS.get(k,k),str(v)] for k,v in rr.get('AssessmentInputs',{}).items()
                 if k in {'RiskPosition','LiquidityScore','ManagementAssessment','FinancialPolicyAssessment','OtherAdjustmentsNotches','ComparativeNotches','ExternalSupportNotches'} and v is not None]
        rows += [['Anchor',_show_rating(rr.get('Anchor'))],['SCA',_show_rating(rr.get('SCA'))],
                 ['Xếp hạng TCPH',_show_rating(rr.get('ICR'))],['Triển vọng',_show_rating(rr.get('Outlook'))]]
        _table(doc,['Cấu phần','Kết quả'],rows,[100,76],10)
        if rr.get('ApplicabilityReason'):_para(doc,rr['ApplicabilityReason'],9,color=GRAY)
    elif rr.get('FactorNotches'):
        rows=[['Điểm ban đầu ngành / BICRA',_show_rating(rr.get('Anchor')),'—','Điểm khởi đầu']]
        for title,grade in rr.get('Factors',{}).items():
            n=rr['FactorNotches'].get(title)
            rows.append([title,grade,f'{n:+d}' if n is not None else '—','Điều chỉnh nội sinh'])
        n=rr.get('InternalNotches');support=rr.get('ExternalSupportNotches')
        rows += [['Tổng điều chỉnh nội sinh','—',f'{n:+d}' if n is not None else '—',_show_rating(rr.get('SACP'))],
                 ['Hỗ trợ bên ngoài','Trung lập' if support==0 else 'Điều chỉnh' if support is not None else 'Chưa xác định',f'{support:+d}' if support is not None else '—',_show_rating(rr.get('ICR'))],
                 ['Kết quả xếp hạng',_show_rating(rr.get('Outlook')),'—',_show_rating(rr.get('ICR'))]]
        _table(doc,['Cấu phần','Đánh giá','Nâng/hạ bậc','Kết quả'],rows,[62,43,27,44],9.5)
    else:
        rows=[['Anchor',_show_rating(rr.get('Anchor'))]]+[[str(k),str(v)] for k,v in rr.get('Factors',{}).items()]
        if pack['Type']=='SECURITIES':
            for title in ['Hồ sơ Kinh doanh','Vốn và Lợi nhuận','Vị thế Rủi ro','Nguồn vốn và Thanh khoản']:
                if title not in rr.get('Factors',{}):rows.append([title,'Chưa xác định'])
        rows += [[_readable(k),vi(v,2)+'/6' if finite(v) else 'Chưa xác định'] for k,v in rr.get('RiskScores',{}).items()]
        rows += [['SACP / SCA',_show_rating(rr.get('SACP',rr.get('SCA')))],['ICR',_show_rating(rr.get('ICR'))]]
        _table(doc,['Cấu phần','Kết quả'],rows,[100,76],10)
    if str(rr.get('RatingOrigin','')).startswith('REFERENCE_REPORT'):
        _para(doc,'Bảng chấm kế thừa từ '+re.sub(r'[_ |–-]*V?8[._]\d+(?:[._]\d+)?(?:-[A-Z-]+)?','',rr.get('AssessmentSource',''))+' cho '+rr.get('AssessmentPeriod','')+'.',8.5,color=GRAY)
    if rr.get('MissingEvidence'):
        if pack['Type']=='INSURANCE':
            from scripts.insurance_presentation import pending_assessment_groups
            names=[r['Nhóm hồ sơ'] for r in pending_assessment_groups(rr)]
        else:names=list(dict.fromkeys(_readable(k) for k in rr['MissingEvidence'] if not k.endswith('_metrics')))
        if names:_para(doc,'Cấu phần chưa có kết luận: '+'; '.join(names)+'.',9,color=GRAY)

def _valuation(doc,pack):
    from scripts.multisector_valuation import valuation
    from scripts.fair_value_range import fair_value_range
    v=valuation(pack['Ticker'],get_snapshot(pack['Ticker']));fv=fair_value_range(pack['Ticker'])
    doc.add_page_break();_band(doc,'ĐỊNH GIÁ VÀ KỊCH BẢN M&A')
    _para(doc,'Phương pháp chính: '+str(v.get('PrimaryMethod') or 'Chưa xác định')+'. '+str(v.get('Reason') or ''))
    _table(doc,['Kịch bản','Giá trị tham chiếu đồng/cp'],[[n,fmt('FairValue',fv.get(k))] for k,n in [('Bear','Thận trọng'),('Base','Cơ sở'),('Bull','Tích cực'),('StrategicMA','M&A chiến lược')]],[90,86],10)
    for k,t in fv.get('ScenarioAssumptions',{}).items():_para(doc,str(t),10,lead={'Bear':'Thận trọng','Base':'Cơ sở','Bull':'Tích cực','StrategicMA':'M&A chiến lược'}.get(k,k)+'.')
    _para(doc,'Các giá trị M&A và cộng hưởng là giả định kịch bản. Ô thiếu không được thay bằng thị giá; cần đủ đầu vào và xác nhận cơ sở định giá trước khi sử dụng kết quả.')

def generate_docx(ticker,report_type='analysis',rating_result=None,mna=None):
    ticker=str(ticker).upper()
    pack=build_pack(ticker,'FY',5)
    rr=rating_result if rating_result is not None else rate_company(ticker)
    when=export_date((mna or {}).get('export_date'))
    doc=Document();_style(doc,ticker,when,report_type);_cover(doc,pack,report_type,when);_summary(doc,pack,rr,report_type);_context(doc,pack);_overview(doc,pack)
    doc.core_properties.author='Lê Hoàng Quân'
    doc.core_properties.title=REPORT_TITLE+' - '+ticker
    doc.core_properties.subject='Phát hành ngày '+when.strftime('%d/%m/%Y')
    for group,metrics in pack['Sections']:
        active=[m for m in metrics if finite(pack['Items'][m]['Value']) or (len(pack['Items'][m]['History']) and pack['Items'][m]['History'].Value.notna().any())]
        if not active:continue
        _band(doc,group.upper())
        if pack['Type']=='BANK':
            from scripts.bank_report_chapters import CHAPTERS,chapter_findings
            key=next((k for title,k,_ in CHAPTERS if title==group.upper()),'')
            if key:
                if key in rr.get('Factors',{}):
                    n=rr.get('FactorNotches',{}).get(key)
                    _para(doc,'Đánh giá cấu phần: '+rr['Factors'][key]+(f' | Điều chỉnh {n:+d} bậc.' if n is not None else '.'),10,True,keep=True,color=DARK)
                for text in chapter_findings(pack,key,rr):_para(doc,text,10)
        else:
            from scripts.report_methodology import chapter_findings as method_findings
            for text in method_findings(pack,group):_para(doc,text,10)
        for m in active:_metric_page(doc,pack,group,m)
    doc.add_page_break()
    if report_type=='rating':_scorecard(doc,pack,rr)
    else:_valuation(doc,pack)
    _sources(doc,pack,rr)
    _normalize_page_breaks(doc)
    _embed_fonts(doc)
    out=BytesIO();doc.save(out);return out.getvalue()
