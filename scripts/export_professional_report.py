import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
import sys, subprocess, shutil
from scripts.multisector_report import generate_docx,generate_pdf

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)

def export(ticker,report_type='analysis'):
    ticker=str(ticker).upper()
    label='XHTN' if report_type=='rating' else 'Phan_tich_Gia_CP_Dinh_gia_MA'
    docx=OUT/f'{ticker}_{label}.docx'
    docx.write_bytes(generate_docx(ticker,report_type))
    pdf=OUT/f'{ticker}_{label}.pdf'
    lo=shutil.which('libreoffice') or shutil.which('soffice')
    if lo:
        subprocess.run([lo,'--headless','--convert-to','pdf','--outdir',str(OUT),str(docx)],check=False,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        generated=OUT/(docx.stem+'.pdf')
        if generated.exists() and generated!=pdf: generated.replace(pdf)
    if not pdf.exists(): pdf.write_bytes(generate_pdf(ticker,report_type))
    print(docx);print(pdf)
    return docx,pdf

if __name__=='__main__':
    t=sys.argv[1] if len(sys.argv)>1 else 'VCB'
    typ=sys.argv[2] if len(sys.argv)>2 else 'analysis'
    export(t,typ)
