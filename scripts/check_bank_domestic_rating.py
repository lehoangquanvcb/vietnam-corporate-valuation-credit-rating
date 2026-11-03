"""Kiểm tra khung hiệu chỉnh; mức đích không phải kiểm chứng chất lượng tín dụng."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.bank_domestic_rating import load_policy, source_fingerprint
from scripts.report_rating import rate_company
from scripts.three_methodology_rating import label, move


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output')
    args=parser.parse_args();policy=load_policy();rows=[];errors=[]
    for profile in policy['Profiles']:
        for t in profile['Entities']:
            if t=='AGRIBANK':
                rows.append({'Ticker':None,'EntityId':'AGRIBANK','PolicyGrade':profile['Grade'],
                             'ComputedICR':None,'Status':'POLICY_REFERENCE_ONLY','FinancialRatingAvailable':False})
                continue
            try:
                r=rate_company(t)
                if r.get('DomesticCalibrationApplied'):
                    assert r['ICR']==label(move(r['RawICR'],r['DomesticCalibrationNotches']))
                    assert r['SACP']==r['PreCalibrationResult']['SACP']
                    assert r['CARInput']==r['PreCalibrationResult']['CARInput']
                    assert r['AssessmentComplete'] is False
                # Kết quả khác mục tiêu khi thiếu dữ liệu/phiếu riêng là hợp lệ và phải hiện rõ.
                rows.append({'Ticker':t,'PolicyMode':profile['Mode'],'PolicyGrade':profile['Grade'],
                             'SACP':r.get('SACP'),'RawICR':r.get('RawICR',r.get('ICR')),
                             'CalibrationNotches':r.get('DomesticCalibrationNotches',0),
                             'ICR':r.get('ICR'),'Status':r.get('DomesticCalibrationStatus','DISABLED'),
                             'Source':r.get('RatingBasisNote'),'MissingEvidence':r.get('MissingEvidence')})
            except Exception as exc:errors.append({'Ticker':t,'Error':repr(exc)})
    report={'Build':'V8.138.0-BANK-FUNDING-REPORT','Enabled':policy['Enabled'],
            'Fingerprint':source_fingerprint(),'Checks':rows,'Errors':errors,
            'Result':'PASS' if not errors else 'FAIL',
            'Note':'PASS xác nhận tính nhất quán phần mềm. AAA/AA- theo nhóm là hiệu chỉnh của chủ mô hình, không phải ý kiến CRA; Agribank chỉ là tham chiếu.'}
    if args.output:Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=sys.stdout.encoding.lower()!='utf-8',indent=2))
    return int(bool(errors))


if __name__=='__main__':raise SystemExit(main())
