import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.three_methodology_rating import rate_company

def committee_pack(ticker, overrides=None):
    rr=rate_company(ticker,overrides or {})
    method=rr.get('Methodology')
    rows=[]

    if method=='BANK':
        rows.append({'Bước':'1','Cấu phần':'BICRA / Anchor','Kết quả':rr.get('Anchor'),'Điều chỉnh':'—','Luận cứ':'Anchor bắt đầu từ BICRA theo phương pháp ngân hàng.'})
        for k,v in rr.get('Factors',{}).items():
            rows.append({'Bước':'2','Cấu phần':k,'Kết quả':v,'Điều chỉnh':'Theo ma trận notch','Luận cứ':'Đánh giá nội sinh; cần đối chiếu dữ liệu doanh nghiệp, peer và nhận định chuyên viên.'})
        rows.append({'Bước':'3','Cấu phần':'SACP','Kết quả':rr.get('SACP'),'Điều chỉnh':str(rr.get('InternalNotches',0))+' bậc','Luận cứ':'Kết quả độc lập sau các yếu tố nội sinh.'})
        rows.append({'Bước':'4','Cấu phần':'Hỗ trợ bên ngoài','Kết quả':str(rr.get('ExternalSupportNotches',0))+' bậc','Điều chỉnh':str(rr.get('ExternalSupportNotches',0))+' bậc','Luận cứ':'Chính phủ/NHNN hoặc tập đoàn nếu đáp ứng điều kiện.'})
    elif method=='SECURITIES':
        rows.append({'Bước':'1','Cấu phần':'BICRA tham chiếu','Kết quả':rr.get('BICRAReference'),'Điều chỉnh':'—','Luận cứ':'Mốc tham chiếu từ môi trường ngân hàng.'})
        rows.append({'Bước':'2','Cấu phần':'Anchor CTCK','Kết quả':rr.get('Anchor'),'Điều chỉnh':str(rr.get('SectorAnchorAdjustment',-2))+' bậc','Luận cứ':'Điều chỉnh rủi ro tăng thêm của CTCK theo methodology.'})
        for k,v in rr.get('Factors',{}).items():
            rows.append({'Bước':'3','Cấu phần':k,'Kết quả':v,'Điều chỉnh':'Theo ma trận notch','Luận cứ':'Đánh giá nội sinh CTCK; cần đối chiếu peer và dữ liệu rủi ro.'})
        rows.append({'Bước':'4','Cấu phần':'SACP','Kết quả':rr.get('SACP'),'Điều chỉnh':str(rr.get('InternalNotches',0))+' bậc','Luận cứ':'Kết quả độc lập.'})
        rows.append({'Bước':'5','Cấu phần':'Hỗ trợ bên ngoài','Kết quả':str(rr.get('ExternalSupportNotches',0))+' bậc','Điều chỉnh':str(rr.get('ExternalSupportNotches',0))+' bậc','Luận cứ':'Hỗ trợ tập đoàn/Chính phủ nếu có cơ sở.'})
    elif method=='CORPORATE':
        labels=rr.get('RiskLabels',{})
        for k,v in rr.get('RiskScores',{}).items():
            show='N/A' if v is None or str(v)=='nan' else f'{float(v):.1f}/6 · {labels.get(k,"")}'
            rows.append({'Bước':'1','Cấu phần':k,'Kết quả':show,'Điều chỉnh':'Đánh giá theo nhóm rủi ro',
                         'Luận cứ':'Định lượng dựa trên KPI và peer khi có dữ liệu; yếu tố ngành/quản trị cần chuyên viên xác nhận.'})
        rows.append({'Bước':'2','Cấu phần':'Peer benchmark','Kết quả':f"{rr.get('PeerCount',0)} peer",'Điều chỉnh':'Dynamic peer',
                     'Luận cứ':'Nhóm tương đồng động theo ngành, quy mô và hồ sơ tài chính; chỉ tiêu bằng chứng: '+', '.join(rr.get('EvidenceMetrics',[])[:8])})
        rows.append({'Bước':'3','Cấu phần':'Anchor','Kết quả':rr.get('Anchor'),'Điều chỉnh':'Từ hồ sơ rủi ro tổng hợp','Luận cứ':'Không sử dụng BICRA/ngân hàng; không phát hành Anchor nếu dữ liệu định lượng chưa đủ.'})
        rows.append({'Bước':'4','Cấu phần':'Thanh khoản','Kết quả':rr.get('Liquidity','N/A'),'Điều chỉnh':'Yếu tố điều chỉnh/cap','Luận cứ':'Đọc Current Ratio, Cash/Debt, CFO/Debt và FOCF/Debt cùng cấu trúc đáo hạn khi có dữ liệu.'})
        rows.append({'Bước':'5','Cấu phần':'Modifiers','Kết quả':str(rr.get('ModifierNotches',0))+' bậc','Điều chỉnh':str(rr.get('ModifierNotches',0))+' bậc','Luận cứ':'Đa dạng hóa, nghĩa vụ nợ, thanh khoản và các yếu tố điều chỉnh khác.'})
        rows.append({'Bước':'6','Cấu phần':'SCA','Kết quả':rr.get('SCA'),'Điều chỉnh':'Sau modifiers/caps','Luận cứ':'Kết quả độc lập trước hỗ trợ bên ngoài.'})
        rows.append({'Bước':'7','Cấu phần':'Hỗ trợ bên ngoài','Kết quả':str(rr.get('ExternalSupportNotches',0))+' bậc','Điều chỉnh':str(rr.get('ExternalSupportNotches',0))+' bậc','Luận cứ':'Tập đoàn/Chính phủ chỉ khi có bằng chứng về năng lực và động cơ hỗ trợ.'})

    rows.append({'Bước':'Kết luận','Cấu phần':'ICR','Kết quả':rr.get('ICR'),'Điều chỉnh':'—','Luận cứ':'Kết quả cuối cùng trước khi trình/duyệt theo quy trình nội bộ.'})
    return {
        'Ticker':str(ticker).upper(),
        'Methodology':rr.get('MethodologyName'),
        'Rating':rr,
        'Waterfall':rows,
        'CommitteeChecklist':[
            'Kiểm tra đúng methodology và phạm vi áp dụng.',
            'Kiểm tra nguồn dữ liệu, kỳ dữ liệu và BCTC hợp nhất.',
            'Kiểm tra peer group/trung bình ngành và các ngoại lệ.',
            'Kiểm tra từng notch/modifier và bằng chứng hỗ trợ.',
            'Kiểm tra rating cap/floor, hỗ trợ bên ngoài và sensitivity.',
            'Tách rõ kết quả máy tính sơ bộ với quyết định của chuyên viên/Hội đồng.'
        ]
    }
