import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.three_methodology_rating import rate_company
from scripts.rating_committee_engine import committee_pack
from scripts.data_quality_engine import assess_data_quality

def rating_evidence(ticker,overrides=None):
    rr=rate_company(ticker,overrides or {}); rc=committee_pack(ticker,overrides or {})
    dq=assess_data_quality(ticker)
    rows=[]
    for x in rc.get('Waterfall',[]):
        result=x.get('Kết quả')
        judgement = result in ['Rất Mạnh','Mạnh','Phù Hợp','Trung Bình','Yếu','Rất Yếu']
        rows.append({
          'Cấu phần':x.get('Cấu phần'),'Kết quả':result,'Điều chỉnh':x.get('Điều chỉnh'),
          'Loại bằng chứng':'Định lượng + judgment' if judgement else 'Methodology / calculation',
          'Trạng thái kiểm chứng':'Cần chuyên viên xác nhận' if judgement else 'Có thể truy vết',
          'Luận cứ':x.get('Luận cứ')
        })
    # Rating confidence intentionally cannot be "high" on automated qualitative scoring alone.
    if dq['Confidence']=='THẤP': conf='THẤP'
    elif any(r['Trạng thái kiểm chứng']=='Cần chuyên viên xác nhận' for r in rows): conf='TRUNG BÌNH'
    else: conf='KHÁ'
    return {'Ticker':str(ticker).upper(),'Methodology':rr.get('MethodologyName'),'ICR':rr.get('ICR'),
            'EvidenceLedger':rows,'RatingConfidence':conf,'DataQuality':dq,
            'GovernanceRule':'ICR tự động là kết quả mô phỏng. Rating chính thức chỉ hình thành sau analyst validation và quyết định Hội đồng theo quy trình nội bộ.'}
