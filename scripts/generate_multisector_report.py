from pathlib import Path
import argparse, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.universal_data import get_company,get_snapshot
from scripts.three_methodology_rating import rate_company
from scripts.multisector_report import generate_docx,generate_pdf
try: from scripts.credit_rating_engine import build_credit_rating
except Exception: build_credit_rating=None
import pandas as pd, numpy as np
from scripts.universal_data import period_date

def bank_rating(t):
    return rate_company(t)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ticker',required=True);ap.add_argument('--type',choices=['analysis','rating'],default='analysis');ap.add_argument('--out_dir',default='reports');ap.add_argument('--format',choices=['docx','pdf','both'],default='both');a=ap.parse_args();t=a.ticker.upper();meta=get_company(t);s=get_snapshot(t)
    rr=None
    if a.type=='rating': rr=bank_rating(t) if meta['EntityType']=='BANK' else rate_company(t)
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);stem=f'{t}_{"XHTN" if a.type=="rating" else "Phan_tich_Dinh_gia_MA"}_V8'
    if a.format in ('docx','both'):
        (out/f'{stem}.docx').write_bytes(generate_docx(t,a.type,rr));print(out/f'{stem}.docx')
    if a.format in ('pdf','both'):
        (out/f'{stem}.pdf').write_bytes(generate_pdf(t,a.type,rr));print(out/f'{stem}.pdf')
if __name__=='__main__':main()
