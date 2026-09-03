import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.valuation_triangulation import triangulate
from scripts.rating_evidence_engine import rating_evidence
from scripts.intelligent_analyst import analyze
def decision_pack(ticker):
    return {'Stock':triangulate(ticker),'Credit':rating_evidence(ticker),'Analyst':analyze(ticker)}
