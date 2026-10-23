"""Chẩn đoán chỉ đọc, không cần gọi Vnstock hoặc đọc khóa API."""
from pathlib import Path
import ast
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

def main():
    from scripts.insurance_rating import ENGINE_VERSION,insurance_rating,rating_status_text
    from scripts.universal_data import get_snapshot
    from scripts.data_quality_engine import assess_data_quality
    source=(ROOT/'app.py').read_text(encoding='utf-8')
    build=None
    for node in ast.parse(source).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BUILD_TAG' for t in node.targets):
            build=ast.literal_eval(node.value)
    version=(ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()
    from scripts.insurance_analysis import metric_pair, peer_universe
    checks=[]
    for ticker in ['ABI','BVH']:
        s=get_snapshot(ticker);dq=assess_data_quality(ticker);r=insurance_rating(ticker)
        pair=metric_pair(ticker,'TotalAssets')
        checks.append({'Ticker':ticker,'EntityType':s.get('EntityType'),'Period':s.get('SnapshotPeriod'),
                       'SectorPeerCandidates':peer_universe(ticker),'TotalAssetsPeerCount':pair['PeerCount'],
                       'TotalAssetsExcludedPeers':pair['PeerExclusions'],
                       'QuantitativePresent':len(dq['Present']),'QuantitativeTotal':dq['Total'],'ApplicableTotal':dq['ApplicableTotal'],
                       'NotApplicableMetrics':dq['NotApplicable'],'RatingDisplay':rating_status_text(r),
                       'MissingMetrics':dq['Missing'],'RatingStatus':r['RatingStatus'],
                       'DebtEBITDAStatus':s.get('_MetricEvidence',{}).get('DebtEBITDA',{}).get('Status')})
    ok=(version=='8.121.0' and build=='V8.121.0-INSURANCE-PEERS' and ENGINE_VERSION=='8.121.0'
        and all(r['EntityType']=='INSURANCE' and r['DebtEBITDAStatus']=='NOT_APPLICABLE' for r in checks))
    result={'ProjectPath':str(ROOT),'VersionFile':version,'AppBuild':build,'InsuranceEngine':ENGINE_VERSION,
            'Checks':checks,'Result':'PASS' if ok else 'FAIL',
            'Note':'Only checks this local project. Confirm the visible app version separately; missing assessments are not software errors.'}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    try:print(text)
    except UnicodeEncodeError:print(json.dumps(result,ensure_ascii=True,indent=2))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
