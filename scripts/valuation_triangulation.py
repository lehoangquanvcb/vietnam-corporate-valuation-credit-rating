import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.universal_data import get_company,get_snapshot,num
from scripts.multisector_valuation import valuation
from scripts.fair_value_range import fair_value_range
from scripts.valuation_regime import assess as regime
from scripts.data_quality_engine import assess_data_quality

def triangulate(ticker,overrides=None):
    o=overrides or {}; meta=get_company(ticker); s=get_snapshot(ticker)
    v=valuation(ticker,s); fv=fair_value_range(ticker,o); rg=regime(ticker); dq=assess_data_quality(ticker)
    current=num(s.get('Price')) or num(s.get('Close'))
    base=num(fv.get('Base'))
    upside=None if current in (None,0) or base is None else base/current-1
    # Explicit lenses; no fabricated target when inherited engine lacks one.
    lenses=[
      {'Lăng kính':'Định giá cơ sở','Giá trị':base,'Trạng thái':'Có dữ liệu' if base is not None else 'Thiếu dữ liệu'},
      {'Lăng kính':'Định giá tương đối ngành','Giá trị':None,'Trạng thái':rg.get('Regime','N/A')},
      {'Lăng kính':'Kịch bản Bear','Giá trị':num(fv.get('Bear')),'Trạng thái':'Stress'},
      {'Lăng kính':'Kịch bản Bull','Giá trị':num(fv.get('Bull')),'Trạng thái':'Upside'},
      {'Lăng kính':'Giá trị chiến lược/M&A','Giá trị':num(fv.get('StrategicMA')),'Trạng thái':'Transaction-specific'}
    ]
    conviction='THẤP'
    if dq['Confidence']=='CAO' and base is not None: conviction='TRUNG BÌNH'
    if dq['Confidence']=='CAO' and base is not None and rg.get('Regime')!='N/A': conviction='KHÁ'
    return {'Ticker':str(ticker).upper(),'Sector':meta.get('Sector'),'CurrentPrice':current,
            'BaseFairValue':base,'UpsideToBase':upside,'Regime':rg.get('Regime'),
            'Lenses':lenses,'AnalyticalConfidence':conviction,'DataQuality':dq,
            'DecisionRule':'Không kết luận chỉ từ một multiple. Giá trị cơ sở phải được kiểm tra chéo với peer, chất lượng ROE/lợi nhuận, stress và M&A nếu có.'}
