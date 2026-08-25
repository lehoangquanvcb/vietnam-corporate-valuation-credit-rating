import json
from pathlib import Path
from scripts.fair_value_range import fair_value_range
from scripts.rating_committee_engine import committee_pack

def export_analysis_payload(ticker, out_dir='outputs'):
    p=Path(out_dir); p.mkdir(parents=True,exist_ok=True)
    payload={'fair_value':fair_value_range(ticker),'rating_committee':committee_pack(ticker)}
    fn=p/f'{str(ticker).upper()}_analysis_payload.json'
    fn.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    return str(fn)

if __name__=='__main__':
    import sys
    print(export_analysis_payload(sys.argv[1] if len(sys.argv)>1 else 'VCB'))
