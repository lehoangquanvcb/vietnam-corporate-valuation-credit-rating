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
    def notch(key):
        v=rr.get(key)
        return 'Chưa thẩm định' if v is None else str(v)+' bậc'

    if method=='BANK':
        rows.append({'Bước':'1','Cấu phần':'BICRA / Anchor','Kết quả':rr.get('Anchor'),'Điều chỉnh':'—','Luận cứ':'Anchor bắt đầu từ BICRA theo phương pháp ngân hàng.'})
        for k,v in rr.get('Factors',{}).items():
            rows.append({'Bước':'2','Cấu phần':k,'Kết quả':v,'Điều chỉnh':'Theo ma trận notch','Luận cứ':'Đánh giá nội sinh; cần đối chiếu dữ liệu doanh nghiệp, peer và nhận định chuyên viên.'})
        rows.append({'Bước':'3','Cấu phần':'SACP','Kết quả':rr.get('SACP'),'Điều chỉnh':notch('InternalNotches'),'Luận cứ':'Kết quả độc lập sau các yếu tố nội sinh.'})
        rows.append({'Bước':'4','Cấu phần':'Hỗ trợ bên ngoài','Kết quả':notch('ExternalSupportNotches'),'Điều chỉnh':notch('ExternalSupportNotches'),'Luận cứ':'Chính phủ/NHNN hoặc tập đoàn nếu đáp ứng điều kiện.'})
    elif method=='SECURITIES':
        rows.append({'Bước':'1','Cấu phần':'BICRA tham chiếu','Kết quả':rr.get('BICRAReference'),'Điều chỉnh':'—','Luận cứ':'Mốc tham chiếu từ môi trường ngân hàng.'})
        rows.append({'Bước':'2','Cấu phần':'Anchor CTCK','Kết quả':rr.get('Anchor'),'Điều chỉnh':str(rr.get('SectorAnchorAdjustment',-2))+' bậc','Luận cứ':'Điều chỉnh rủi ro tăng thêm của CTCK theo methodology.'})
        for k,v in rr.get('Factors',{}).items():
            rows.append({'Bước':'3','Cấu phần':k,'Kết quả':v,'Điều chỉnh':'Theo ma trận notch','Luận cứ':'Đánh giá nội sinh CTCK; cần đối chiếu peer và dữ liệu rủi ro.'})
        rows.append({'Bước':'4','Cấu phần':'SACP','Kết quả':rr.get('SACP'),'Điều chỉnh':notch('InternalNotches'),'Luận cứ':'Kết quả độc lập.'})
        rows.append({'Bước':'5','Cấu phần':'Hỗ trợ bên ngoài','Kết quả':notch('ExternalSupportNotches'),'Điều chỉnh':notch('ExternalSupportNotches'),'Luận cứ':'Hỗ trợ tập đoàn/Chính phủ nếu có cơ sở.'})
    elif method=='CORPORATE':
        from scripts.corporate_methodology import scorecard
        for i,row in enumerate(scorecard(rr),1):
            rows.append({'Bước':str(i),'Cấu phần':row['Cấu phần'],'Kết quả':row['Điểm / Đánh giá'],
                         'Điều chỉnh':row['Tỷ trọng'],'Điểm đóng góp':row['Điểm đóng góp'],'Luận cứ':row['Kết quả / Căn cứ']})
        for row in rr.get('AdjustmentScorecard',[]):
            rows.append({'Bước':'Điều chỉnh','Cấu phần':row['Cấu phần'],'Kết quả':row['Kết quả'],
                         'Điều chỉnh':row['Tác động'],'Luận cứ':'Áp dụng sau quy đổi tổng điểm bốn nhóm rủi ro.'})

    elif method=='INSURANCE':
        from scripts.insurance_rating import insurance_scorecard
        for i,row in enumerate(insurance_scorecard(rr),1):
            rows.append({**row,'Bước':str(i),'Điều chỉnh':'Không áp dụng' if rr.get('RatingBlocker')=='SCOPE' else 'Theo hồ sơ và ma trận'})

    for row in rows:
        if row.get('Kết quả') is None or str(row.get('Kết quả'))=='N/A':row['Kết quả']='Chưa thẩm định'
    if method not in {'INSURANCE','CORPORATE'}:rows.append({'Bước':'Kết luận','Cấu phần':'ICR','Kết quả':rr.get('ICR'),'Điều chỉnh':'—','Luận cứ':'Kết quả cuối cùng trước khi trình/duyệt theo quy trình nội bộ.'})
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
