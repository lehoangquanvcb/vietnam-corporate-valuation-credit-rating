import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
import json,sys
from scripts.decision_intelligence import decision_pack
ROOT=Path(__file__).resolve().parents[1]
def export(ticker):
    d=ROOT/'outputs';d.mkdir(exist_ok=True)
    p=d/f'{str(ticker).upper()}_decision_intelligence.json'
    p.write_text(json.dumps(decision_pack(ticker),ensure_ascii=False,indent=2),encoding='utf-8')
    print(p);return p
if __name__=='__main__':export(sys.argv[1] if len(sys.argv)>1 else 'VCB')
