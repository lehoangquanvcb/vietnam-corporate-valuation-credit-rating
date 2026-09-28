from vnstock_env import load_vnstock_env
load_vnstock_env()

from pathlib import Path
from datetime import datetime, timedelta
import sys, re
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

try:
    from vnstock_data import Market
except Exception:
    Market=None
try:
    from vnstock_data import Quote
except Exception:
    Quote=None

def _flat(df):
    if df is None:return pd.DataFrame()
    x=df.copy()
    if isinstance(x.columns,pd.MultiIndex):
        x.columns=['__'.join(str(v) for v in c if str(v)!='nan') for c in x.columns]
    try:
        if not isinstance(x.index,pd.RangeIndex):x=x.reset_index()
    except Exception:pass
    return x

def _norm(s):
    return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()

def _find_col(df,names):
    nn=[_norm(n) for n in names]
    for c in df.columns:
        if _norm(c) in nn:return c
    for c in df.columns:
        nc=_norm(c)
        if any(n in nc or nc in n for n in nn if len(n)>=4):return c
    return None

def _normalize_price(v):
    try:v=float(v)
    except:return None
    if not np.isfinite(v) or v<=0:return None
    # vnstock market quote can be thousand-VND; model stores VND/share.
    if v<500:v*=1000.0
    while v>1_000_000:v/=1000.0
    return float(v) if 100<=v<=1_000_000 else None

def _extract_latest(df):
    x=_flat(df)
    if x.empty:return None,None
    cc=_find_col(x,['close','close price','closing price'])
    dc=_find_col(x,['time','date','trading date','datetime'])
    if cc is None:return None,None
    x['_close']=pd.to_numeric(x[cc],errors='coerce')
    x['_date']=pd.to_datetime(x[dc],errors='coerce') if dc is not None else pd.NaT
    x=x.dropna(subset=['_close'])
    if x.empty:return None,None
    if x['_date'].notna().any():x=x.sort_values('_date')
    r=x.iloc[-1]
    px=_normalize_price(r['_close'])
    dt=r['_date']
    if pd.isna(dt):dt=pd.Timestamp.now().normalize()
    return px,pd.Timestamp(dt).date().isoformat()

def fetch_latest_market_price(ticker):
    t=str(ticker).upper().strip()
    start=(datetime.now()-timedelta(days=45)).strftime('%Y-%m-%d')
    end=datetime.now().strftime('%Y-%m-%d')
    errors=[]
    if Market is not None:
        try:
            d=Market().equity(t).ohlcv(start=start,end=end)
            px,dt=_extract_latest(d)
            if px is not None:return px,dt,'VNSTOCK_MARKET_OHLCV'
        except Exception as e:errors.append('Market:'+str(e))
    if Quote is not None:
        try:
            q=Quote(source='VCI',symbol=t)
            d=q.history(start=start,end=end,interval='1D')
            px,dt=_extract_latest(d)
            if px is not None:return px,dt,'VNSTOCK_QUOTE_VCI'
        except Exception as e:errors.append('Quote:'+str(e))
    raise RuntimeError(' | '.join(errors) or 'No market-price provider available')

def _upsert_price_history(ticker,price,date,source):
    path=DATA/'price_history.csv'
    old=pd.read_csv(path) if path.exists() else pd.DataFrame()
    row=pd.DataFrame([{'Ticker':ticker,'Date':date,'Close':price,'Source':source}])
    out=pd.concat([old,row],ignore_index=True,sort=False) if len(old) else row
    if 'Ticker' in out.columns:out['Ticker']=out['Ticker'].astype(str).str.upper().str.strip()
    if 'Date' in out.columns:out['Date']=pd.to_datetime(out['Date'],errors='coerce').dt.date.astype(str)
    out=out.drop_duplicates(['Ticker','Date'],keep='last').sort_values(['Ticker','Date'])
    out.to_csv(path,index=False,encoding='utf-8-sig')

def _update_snapshot(ticker,price,date,source):
    path=DATA/'company_snapshot.csv'
    if not path.exists():return
    x=pd.read_csv(path)
    if 'Ticker' not in x.columns:return
    x['Ticker']=x['Ticker'].astype(str).str.upper().str.strip()
    mask=x['Ticker'].eq(ticker)
    if not mask.any():return
    x.loc[mask,'Price']=price
    x.loc[mask,'PriceDate']=date
    x.loc[mask,'PriceSource']=source
    x.to_csv(path,index=False,encoding='utf-8-sig')

def _normalize_history(df,ticker,source):
    x=_flat(df)
    if x.empty:return pd.DataFrame(columns=['Ticker','Date','Close','Source'])
    cc=_find_col(x,['close','close price','closing price'])
    dc=_find_col(x,['time','date','trading date','datetime'])
    if cc is None or dc is None:return pd.DataFrame(columns=['Ticker','Date','Close','Source'])
    out=pd.DataFrame({'Date':pd.to_datetime(x[dc],errors='coerce'),'Close':pd.to_numeric(x[cc],errors='coerce')})
    out=out.dropna(); out['Close']=out['Close'].map(_normalize_price); out=out.dropna(); out=out[out.Close>0]
    out['Ticker']=str(ticker).upper().strip(); out['Source']=source
    return out[['Ticker','Date','Close','Source']].drop_duplicates(['Ticker','Date'],keep='last').sort_values('Date')

def fetch_market_history(ticker,years=3):
    t=str(ticker).upper().strip(); start=(datetime.now()-timedelta(days=366*years)).strftime('%Y-%m-%d'); end=datetime.now().strftime('%Y-%m-%d'); errors=[]
    if Market is not None:
        try:
            d=Market().equity(t).ohlcv(start=start,end=end); h=_normalize_history(d,t,'VNSTOCK_MARKET_OHLCV')
            if len(h)>=20:return h
        except Exception as e:errors.append('Market:'+str(e))
    if Quote is not None:
        try:
            q=Quote(source='VCI',symbol=t); d=q.history(start=start,end=end,interval='1D'); h=_normalize_history(d,t,'VNSTOCK_QUOTE_VCI')
            if len(h)>=20:return h
        except Exception as e:errors.append('Quote:'+str(e))
    return pd.DataFrame(columns=['Ticker','Date','Close','Source'])

def _upsert_history_frame(hist):
    if hist is None or hist.empty:return 0
    path=DATA/'price_history.csv'; old=pd.read_csv(path) if path.exists() else pd.DataFrame(columns=hist.columns)
    out=pd.concat([old,hist],ignore_index=True,sort=False); out['Ticker']=out['Ticker'].astype(str).str.upper().str.strip(); out['Date']=pd.to_datetime(out['Date'],errors='coerce')
    out=out.dropna(subset=['Date','Close']); out['Date']=out['Date'].dt.strftime('%Y-%m-%d'); out=out.drop_duplicates(['Ticker','Date'],keep='last').sort_values(['Ticker','Date'])
    out.to_csv(path,index=False,encoding='utf-8-sig'); return len(hist)

def refresh_market_history(ticker,years=3):
    h=fetch_market_history(ticker,years); n=_upsert_history_frame(h)
    if n: print(f'MARKET HISTORY: {str(ticker).upper()} = {n} rows ({years}Y)')
    return n

def refresh_latest_market_price(ticker):
    t=str(ticker).upper().strip()
    # V8.118: backfill market history, not only the last quote, so relative-price and 1M/3M/6M/12M outlook charts can render.
    try: refresh_market_history(t,3)
    except Exception as e: print('WARNING - market history backfill failed:',e)
    px,dt,source=fetch_latest_market_price(t)
    _upsert_price_history(t,px,dt,source)
    _update_snapshot(t,px,dt,source)
    print(f'LATEST MARKET PRICE: {t} = {px:,.0f} VND/share | {dt} | {source}')
    return px,dt,source

if __name__=='__main__':
    if len(sys.argv)<2:
        print('Usage: python scripts/refresh_latest_market_price.py <TICKER>')
        raise SystemExit(2)
    try:
        refresh_latest_market_price(sys.argv[1])
    except Exception as e:
        print('MARKET PRICE REFRESH FAILED:',e)
        raise SystemExit(3)
