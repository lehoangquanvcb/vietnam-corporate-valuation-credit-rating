
import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from vnstock_env import load_vnstock_env
load_vnstock_env()

from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
def refresh():
    from vnstock_data import Insights
    from scripts.universal_data import universe
    ins=Insights();rows=[]
    for t in universe().Ticker:
        try:
            d=pd.DataFrame(ins.equity(str(t)).peer_compare())
            if d.empty:continue
            r=d.iloc[0]
            rows.append({'Ticker':t,'PE':r.get('pe'),'PB':r.get('pb'),'EV_EBITDA':r.get('ev_ebitda'),'ROE':r.get('roe'),'IndustryPE':r.get('industry_pe'),'IndustryPB':r.get('industry_pb'),'IndustryEV_EBITDA':r.get('industry_ev_ebitda'),'IndustryROE':r.get('industry_roe'),'MarketPE':r.get('market_pe'),'MarketPB':r.get('market_pb'),'Beta1Y':r.get('beta_1y')})
        except Exception as e:print('SKIP',t,e)
    z=pd.DataFrame(rows);z.to_csv(DATA/'vnstock_peer_crosscheck.csv',index=False,encoding='utf-8-sig');print('OK',len(z))
if __name__=='__main__':refresh()
