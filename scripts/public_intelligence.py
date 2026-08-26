from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'config'/'public_intelligence.csv'

def load_public_intelligence(scope):
    try:
        z=pd.read_csv(PATH)
    except Exception:
        return []
    s=str(scope or '').upper()
    z=z[z.Scope.astype(str).str.upper().isin(['MACRO',s])]
    out=[]
    for _,r in z.iterrows():
        out.append({k:r.get(k,'') for k in ['AsOf','Scope','Key','Title','Narrative','Source','URL']})
    return out

def scope_for_entity(entity_type):
    e=str(entity_type or '').upper()
    return 'BANK' if e=='BANK' else 'SECURITIES' if e=='SECURITIES' else 'CORPORATE'
