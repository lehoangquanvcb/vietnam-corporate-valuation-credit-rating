import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
import pandas as pd, numpy as np
from scripts.universal_data import get_company,get_snapshot,num
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
def _read(name):
    p=DATA/name
    try:return pd.read_csv(p)
    except:return pd.DataFrame()
def assess(ticker):
    t=str(ticker).upper(); snap=get_snapshot(t); meta=get_company(t)
    cc=_read('vnstock_peer_crosscheck.csv')
    r=cc[cc.Ticker.astype(str).str.upper().eq(t)].iloc[-1].to_dict() if len(cc) and 'Ticker' in cc and cc.Ticker.astype(str).str.upper().eq(t).any() else {}
    pe=num(r.get('PE',snap.get('PE')));pb=num(r.get('PB',snap.get('PB')))
    ipe=num(r.get('IndustryPE'));ipb=num(r.get('IndustryPB'));mpe=num(r.get('MarketPE'));mpb=num(r.get('MarketPB'))
    scores=[];notes=[]
    for label,x,b in [('P/E',pe,ipe),('P/B',pb,ipb)]:
        if x is not None and b not in (None,0):
            gap=x/b-1
            scores.append(gap)
            state='chiết khấu' if gap<-.1 else 'premium' if gap>.1 else 'xấp xỉ'
            notes.append(f'{label} đang {state} so với ngành khoảng {abs(gap)*100:.1f}%.')
    avg=float(np.mean(scores)) if scores else None
    regime='RẺ TƯƠNG ĐỐI' if avg is not None and avg<-.15 else 'ĐẮT TƯƠNG ĐỐI' if avg is not None and avg>.15 else 'TRUNG TÍNH'
    return {'Ticker':t,'Sector':meta.get('Sector'),'Regime':regime,'PE':pe,'PB':pb,'IndustryPE':ipe,'IndustryPB':ipb,'MarketPE':mpe,'MarketPB':mpb,'Notes':notes,'RelativeGap':avg}
