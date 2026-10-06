import sys, importlib, traceback, os, inspect, json
from pathlib import Path
import pandas as pd
from vnstock_env import load_vnstock_env

ROOT=Path(__file__).resolve().parents[1]
status=load_vnstock_env()
print('DIAGNOSTIC ENGINE v8.64'); print('Python:',sys.executable); print('Version:',sys.version.replace('\\n',' '))
print('.env:','FOUND' if status['env_file_exists'] else 'NOT FOUND','|',status['env_file'])
print('VNSTOCK_API_KEY:',status['api_key_masked']); print('VNSTOCK_VENV_PATH:',status['venv_path'] or os.getenv('VNSTOCK_VENV_PATH') or 'NOT SET')
print('VNSTOCK_INTERACTIVE:',os.getenv('VNSTOCK_INTERACTIVE',''))
try:
 import vnstock_data
 print(f'vnstock_data: OK | file={vnstock_data.__file__} | version={getattr(vnstock_data,"__version__","N/A")}')
 for name in ['Reference','Fundamental','Market','Quote','Insights','Macro']:print(f'  {name}:','YES' if hasattr(vnstock_data,name) else 'NO')
except Exception as e:
 print('vnstock_data: NOT AVAILABLE',repr(e)); raise SystemExit(2)
print('\nSponsor access smoke test:')
try:
 from vnstock_data import Reference, Fundamental
 d=Reference().equity.list(); print('Sponsor authentication: OK'); print('Reference().equity.list(): OK | rows=',len(d),'| columns=',list(d.columns)[:30])
except Exception:
 traceback.print_exc(); raise SystemExit(3)

ticker=sys.argv[1].strip().upper() if len(sys.argv)>1 else None
if not ticker: raise SystemExit(0)
print(f'\n===== FUNDAMENTAL SCHEMA PROBE: {ticker} =====')
outdir=ROOT/'data'/'diagnostics'/ticker; outdir.mkdir(parents=True,exist_ok=True)
try:eq=Fundamental().equity(ticker)
except Exception:
 traceback.print_exc(); raise SystemExit(4)
print('equity object:',type(eq).__name__)
for method in ['balance_sheet','income_statement','cash_flow','ratio']:
 fn=getattr(eq,method,None)
 print(f'\n--- {method} ---')
 if fn is None: print('METHOD NOT FOUND'); continue
 try: print('signature:',inspect.signature(fn))
 except Exception: pass
 v=getattr(vnstock_data,'__version__','0')
 nums=tuple(int(x) for x in __import__('re').findall(r'\d+',str(v))[:3]) if v else (0,0,0)
 if nums >= (3,2,8):
  attempts=[
   ('time_series',dict(period='quarter',lang='en',format='time_series',drop_empty=True,com_type='Regular')),
   ('long',dict(period='quarter',lang='en',format='long',drop_empty=True,com_type='Regular')),
   ('default',dict(period='quarter',lang='en')),
  ]
 else:
  attempts=[('legacy_quarter_en',dict(period='quarter',lang='en')),('legacy_quarter',dict(period='quarter')),('legacy_default',dict())]
 ok=False
 for tag,kwargs in attempts:
  try:
   df=fn(**kwargs)
   if df is None: print(tag,': None'); continue
   if not isinstance(df,pd.DataFrame): df=pd.DataFrame(df)
   print(f'{tag}: OK shape={df.shape}')
   print('columns:',[str(c) for c in df.columns][:120])
   print(df.head(5).to_string(max_cols=30,index=False))
   df.to_csv(outdir/f'{method}_{tag}.csv',index=False,encoding='utf-8-sig')
   (outdir/f'{method}_{tag}_columns.txt').write_text('\n'.join(map(str,df.columns)),encoding='utf-8')
   ok=True
   # continue to tidy too because it reveals semantic identifiers
  except Exception as e: print(f'{tag}: {type(e).__name__}: {e}')
 if not ok: print('ALL ATTEMPTS FAILED')

print('\n--- financial_health ---')
fh=getattr(eq,'financial_health',None)
if fh is None:
 print('METHOD NOT FOUND')
else:
 for tag,kw in [('regular',dict(scorecard='regular',lang='en',limit=12)),('auto',dict(scorecard='auto',lang='en',limit=12)),('default',dict())]:
  try:
   df=fh(**kw); df=pd.DataFrame(df) if not isinstance(df,pd.DataFrame) else df
   print(f'{tag}: OK shape={df.shape}')
   print('columns:',[str(c) for c in df.columns][:120])
   print(df.head(8).to_string(max_cols=40,index=False))
   df.to_csv(outdir/f'financial_health_{tag}.csv',index=False,encoding='utf-8-sig')
   if len(df): break
  except Exception as e: print(f'{tag}: {type(e).__name__}: {e}')

print('\nDiagnostic files saved to:',outdir)
print('DONE - HPG/schema probe completed.')
