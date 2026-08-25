from scripts.fair_value_range import fair_value_range
from scripts.rating_committee_engine import committee_pack
from scripts.universal_data import get_company,get_snapshot,num
from scripts.multisector_valuation import valuation
from scripts.intelligent_analyst import analyze
try:
    from scripts.multisector_rating import rate_company
except Exception:
    rate_company=None

def run(ticker):
    meta=get_company(ticker); snap=get_snapshot(ticker)
    stock=analyze(ticker); val=valuation(ticker,snap)
    rating={}
    if rate_company:
        try: rating=rate_company(ticker)
        except Exception as e: rating={'Error':str(e)}
    return {'Meta':meta,'StockAnalysis':stock,'Valuation':val,'FairValueRange':fair_value_range(ticker),'CreditRating':rating,'RatingCommittee':committee_pack(ticker)}
