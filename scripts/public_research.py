from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_FILE = ROOT / "data" / "public_research_master.csv"

def _norm(v):
    return str(v or "").strip()

def load_public_research(ticker=None, entity_type=None, sector=None, kind=None, limit=6):
    """Load curated public research for issuer / macro / industry sections.

    Matching priority:
      1. exact Ticker
      2. exact EntityType + Sector
      3. EntityType only
      4. generic rows
    Runtime never performs web search; it only reads the auditable master CSV.
    """
    if not RESEARCH_FILE.exists():
        return []
    t=_norm(ticker).upper()
    et=_norm(entity_type).upper()
    sec=_norm(sector).lower()
    kd=_norm(kind).upper()

    rows=[]
    try:
        with RESEARCH_FILE.open("r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if kd and _norm(r.get("Kind")).upper()!=kd:
                    continue
                rt=_norm(r.get("Ticker")).upper()
                re=_norm(r.get("EntityType")).upper()
                rs=_norm(r.get("Sector")).lower()

                # Reject rows that are explicitly scoped elsewhere.
                if rt and rt!=t:
                    continue
                if re and re!=et:
                    continue
                if rs and rs!=sec:
                    continue

                score=0
                if rt and rt==t: score+=100
                if re and re==et: score+=20
                if rs and rs==sec: score+=10
                try: score+=int(float(r.get("Priority") or 0))
                except Exception: pass
                rr={k:_norm(v) for k,v in r.items()}
                rr["_score"]=score
                rows.append(rr)
    except Exception:
        return []

    rows.sort(key=lambda x:(x.get("_score",0), x.get("AsOf","")), reverse=True)
    return rows[:max(1,int(limit))]
