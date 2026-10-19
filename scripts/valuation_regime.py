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
    from scripts.methodology_kpi_engine import methodology_kpi_table
    table=methodology_kpi_table(t)
    def benchmark(m):
        z=table[table.Metric.eq(m)]
        return num(z.iloc[0]['Trung vị']) if len(z) else None
    pe=num(snap.get('PE'));pb=num(snap.get('PB'))
    ipe=benchmark('PE');ipb=benchmark('PB');mpe=mpb=None
    scores=[];notes=[]
    for label,x,b in [('P/E',pe,ipe),('P/B',pb,ipb)]:
        if x is not None and b not in (None,0):
            gap=x/b-1
            scores.append(gap)
            state='chiết khấu' if gap<-.1 else 'premium' if gap>.1 else 'xấp xỉ'
            notes.append(f'{label} đang {state} so với ngành khoảng {abs(gap)*100:.1f}%.')
    avg=float(np.mean(scores)) if scores else None
    regime='CHƯA ĐỦ DỮ LIỆU' if avg is None else 'RẺ TƯƠNG ĐỐI' if avg is not None and avg<-.15 else 'ĐẮT TƯƠNG ĐỐI' if avg is not None and avg>.15 else 'TRUNG TÍNH'
    return {'Ticker':t,'Sector':meta.get('Sector'),'Regime':regime,'PE':pe,'PB':pb,'IndustryPE':ipe,'IndustryPB':ipb,'MarketPE':mpe,'MarketPB':mpb,'Notes':notes,'RelativeGap':avg}
