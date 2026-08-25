from scripts.valuation_triangulation import triangulate
from scripts.rating_evidence_engine import rating_evidence
from scripts.intelligent_analyst import analyze
def decision_pack(ticker):
    return {'Stock':triangulate(ticker),'Credit':rating_evidence(ticker),'Analyst':analyze(ticker)}
