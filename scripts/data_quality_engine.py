import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.universal_data import get_company,get_snapshot,num

CORE = {
'BANK':['TotalAssets','ROE','ROA','NPL','CAR','CASA','NIM','PB','PE'],
'SECURITIES':['Revenue','ROE','ROA','AvailableCapitalRatio','DebtEquity','CurrentRatio','PB','PE'],
'CORPORATE':['Revenue','ROE','ROA','DebtEquity','CurrentRatio','PB','PE']
}

def assess_data_quality(ticker):
    meta=get_company(ticker); s=get_snapshot(ticker)
    typ=str(meta.get('EntityType','CORPORATE'))
    fields=CORE.get(typ,CORE['CORPORATE'])
    present=[x for x in fields if num(s.get(x)) is not None]
    missing=[x for x in fields if x not in present]
    coverage=len(present)/len(fields) if fields else 0
    if coverage>=.85: level='CAO'
    elif coverage>=.65: level='TRUNG BÌNH'
    else: level='THẤP'
    return {'Ticker':str(ticker).upper(),'EntityType':typ,'Coverage':coverage,
            'Present':present,'Missing':missing,'Confidence':level,
            'Note':'Confidence phản ánh độ đầy đủ dữ liệu định lượng cốt lõi, không phải mức độ chắc chắn của khuyến nghị/xếp hạng.'}
