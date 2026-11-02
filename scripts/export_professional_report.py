import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
import sys, subprocess, shutil
from scripts.multisector_report import generate_docx,generate_pdf
from scripts.report_identity import export_date, report_filename

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)

def export(ticker,report_type='analysis'):
    ticker=str(ticker).upper()
    when=export_date()
    docx=OUT/report_filename(ticker,report_type,when)
    docx.write_bytes(generate_docx(ticker,report_type,mna={'export_date':when}))
    pdf=OUT/report_filename(ticker,report_type,when,'pdf')
    pdf.write_bytes(generate_pdf(ticker,report_type,mna={'export_date':when}))
    print(docx);print(pdf)
    return docx,pdf

if __name__=='__main__':
    t=sys.argv[1] if len(sys.argv)>1 else 'VCB'
    typ=sys.argv[2] if len(sys.argv)>2 else 'analysis'
    export(t,typ)
