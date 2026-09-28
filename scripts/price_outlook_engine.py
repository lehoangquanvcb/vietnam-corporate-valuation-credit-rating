from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

def _prices(ticker):
    fp=DATA/'price_history.csv'
    if not fp.exists(): return pd.DataFrame(columns=['Date','Close'])
    q=pd.read_csv(fp)
    if not {'Ticker','Date','Close'}.issubset(q.columns): return pd.DataFrame(columns=['Date','Close'])
    q=q[q.Ticker.astype(str).str.upper().eq(str(ticker).upper())][['Date','Close']].copy()
    q['Date']=pd.to_datetime(q.Date,errors='coerce'); q['Close']=pd.to_numeric(q.Close,errors='coerce')
    return q.dropna().query('Close>0').sort_values('Date').drop_duplicates('Date',keep='last')

def outlook(ticker, fair_values=None):
    """Scenario-aware 1/3/6/12M price outlook. Estimates, not deterministic forecasts.
    Short horizons weight observed momentum/volatility; longer horizons progressively
    converge toward the current fundamental Base valuation. Returns no forecast when
    there is insufficient market history.
    """
    q=_prices(ticker)
    if len(q)<20: return {'Ticker':str(ticker).upper(),'Status':'INSUFFICIENT_PRICE_HISTORY','Rows':[]}
    px=float(q.Close.iloc[-1]); r=np.log(q.Close).diff().dropna().tail(252)
    vol=float(r.std()*np.sqrt(252)) if len(r)>=20 else None
    def mom(days):
        if len(q)<=days: return 0.0
        return float(q.Close.iloc[-1]/q.Close.iloc[-days-1]-1)
    m20,m60=mom(20),mom(60)
    base=(fair_values or {}).get('Base'); bear=(fair_values or {}).get('Bear'); bull=(fair_values or {}).get('Bull')
    try: base=float(base) if base and float(base)>0 else px
    except: base=px
    rows=[]
    for months,days,wfund in [(1,21,.10),(3,63,.25),(6,126,.50),(12,252,.75)]:
        years=days/252
        momentum=np.clip(.65*m20+.35*m60,-.35,.35)
        market_target=px*(1+momentum*min(1.0,days/63))
        central=(1-wfund)*market_target+wfund*base
        sigma=(vol or .35)*np.sqrt(years)
        lo=central*np.exp(-1.0*sigma); hi=central*np.exp(1.0*sigma)
        if bear:
            try: lo=min(lo,(1-wfund)*px+wfund*float(bear))
            except: pass
        if bull:
            try: hi=max(hi,(1-wfund)*px+wfund*float(bull))
            except: pass
        conf='THẤP' if months<=3 or len(q)<126 else ('TRUNG BÌNH' if len(q)<252 else 'KHÁ')
        rows.append({'Horizon':f'{months}M','Months':months,'Central':central,'Bear':lo,'Bull':hi,'ExpectedReturn':central/px-1,'Confidence':conf})
    return {'Ticker':str(ticker).upper(),'Status':'OK','CurrentPrice':px,'AsOf':q.Date.iloc[-1],'AnnualizedVolatility':vol,'Rows':rows}
