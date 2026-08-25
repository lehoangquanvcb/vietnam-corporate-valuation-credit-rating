from pathlib import Path
import argparse, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.universal_data import get_company,get_snapshot
from scripts.multisector_rating import securities_rating,corporate_rating
from scripts.multisector_report import generate_docx,generate_pdf
try: from scripts.credit_rating_engine import build_credit_rating
except Exception: build_credit_rating=None
import pandas as pd, numpy as np
from scripts.universal_data import period_date

def bank_rating(t):
    if build_credit_rating is None:return {'ICR':'N/A'}
    s=pd.read_csv(ROOT/'data/bank_snapshot.csv'); s['ROE_Used']=pd.to_numeric(s.ROE,errors='coerce')
    h=pd.read_csv(ROOT/'data/bank_history_long.csv'); h['Date']=h.Period.map(period_date); h['Value']=pd.to_numeric(h.Value,errors='coerce')
    for m in ['GrossLoans','CustomerDeposits','NPAT']:
        rows=[]
        for x,g in h[h.Metric.eq(m)].dropna(subset=['Date','Value']).sort_values(['Ticker','Date']).groupby('Ticker'):
            vals=g.Value.tolist(); back=vals[max(0,len(vals)-5)] if vals else np.nan; cur=vals[-1] if vals else np.nan
            rows.append({'Ticker':x,m+'_Growth':cur/back-1 if pd.notna(back) and back!=0 else np.nan})
        s=s.merge(pd.DataFrame(rows),on='Ticker',how='left')
    r=build_credit_rating(s,t); r['Anchor']=r.get('AnchorRating');r['SACP']=r.get('SACPRating');r['ICR']=r.get('FinalRating');return r

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ticker',required=True);ap.add_argument('--type',choices=['analysis','rating'],default='analysis');ap.add_argument('--out_dir',default='reports');a=ap.parse_args();t=a.ticker.upper();meta=get_company(t);s=get_snapshot(t)
    rr=None
    if a.type=='rating': rr=bank_rating(t) if meta['EntityType']=='BANK' else securities_rating(t,s) if meta['EntityType']=='SECURITIES' else corporate_rating(t,s)
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);stem=f'{t}_{"XHTN" if a.type=="rating" else "Phan_tich_Dinh_gia_MA"}_V8'
    (out/f'{stem}.docx').write_bytes(generate_docx(t,a.type,rr));(out/f'{stem}.pdf').write_bytes(generate_pdf(t,a.type,rr));print(out/f'{stem}.pdf')
if __name__=='__main__':main()
