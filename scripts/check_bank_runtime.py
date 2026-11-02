"""Kiểm tra ngân hàng thực tế và mô phỏng Cloud không có raw; không gọi API."""
from pathlib import Path
from tempfile import TemporaryDirectory
import ast
import json
import math
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

CORE=['TotalAssets','GrossLoans','CustomerDeposits','Equity','NPAT',
      'NetInterestIncome','ROE','ROA','NIM','NPL','PB','PE','CASA']


def check(root=ROOT):
    import pandas as pd
    from scripts.financial_evidence import at_period, latest_period, period_date, repair_snapshot, same_period_history
    root=Path(root)
    build=None
    for node in ast.parse((root/'app.py').read_text(encoding='utf-8-sig')).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BUILD_TAG' for t in node.targets):
            build=ast.literal_eval(node.value)
    result={'AppBuild':build,'Checks':[],'Failures':[]}
    if build!='V8.129.0-REFERENCE-RATING':result['Failures'].append('App build không khớp V8.129.0')
    path=root/'data/bank_history_long.csv'
    if not path.exists():
        result['Failures'].append('Thiếu data/bank_history_long.csv')
        result['Result']='FAIL';return result
    cache=pd.read_csv(path)
    if not {'Ticker','Period','Metric','Value'} <= set(cache):
        result['Failures'].append('Bảng lịch sử thiếu cột Ticker/Period/Metric/Value')
        result['Result']='FAIL';return result
    cache['Ticker']=cache.Ticker.astype(str).str.upper().str.strip()
    cache['Value']=pd.to_numeric(cache.Value,errors='coerce')
    universe=pd.read_csv(root/'config/company_universe.csv')
    banks=sorted(set(universe.loc[universe.EntityType.eq('BANK'),'Ticker'].astype(str)) & set(cache.Ticker))
    if not banks:result['Failures'].append('Không có lịch sử ngân hàng để kiểm tra')
    with TemporaryDirectory(prefix='bank_without_raw_') as td:
        cloud=Path(td);(cloud/'data').mkdir()
        shutil.copyfile(path,cloud/'data/bank_history_long.csv')
        for ticker in banks:
            target=latest_period(ticker,'BANK',cloud)
            if not target:
                result['Failures'].append(ticker+': không xác định được kỳ lịch sử');continue
            q=at_period(ticker,'BANK',target,'QUARTER',cloud)
            rows=cache[cache.Ticker.eq(ticker)&cache.Period.eq(target)&cache.Metric.isin(CORE)]
            compared=0
            for metric,g in rows.groupby('Metric'):
                vals=g.Value.dropna().unique()
                if len(vals)!=1:continue
                # Bảng mặc định chứa quý riêng lẻ. Cơ sở khác được kiểm tra bằng
                # kiểm thử YTD chuyên biệt, không đối chiếu giá trị như quý.
                if metric in {'NPAT','NetInterestIncome'} and 'Basis' in g and not g.Basis.fillna('QUARTER').astype(str).str.upper().isin(['Q','QUARTER']).all():continue
                actual=q[metric]['Value'];compared+=1
                if actual is None or not math.isclose(actual,float(vals[0]),rel_tol=1e-10,abs_tol=1e-10):
                    result['Failures'].append(f'{ticker}/{metric}/{target}: không khớp bảng lịch sử')
            snap=repair_snapshot(ticker,'BANK',root=cloud)
            local=repair_snapshot(ticker,'BANK',root=root)
            hist=same_period_history(ticker,'BANK','FY',5,cloud,CORE)
            result['Checks'].append({
                'Ticker':ticker,'Period':target,'ComparedQuarterMetrics':compared,
                'CoreMetricsWithoutRaw':sum(q[m]['Value'] is not None for m in CORE),
                'CoreMetricTotal':len(CORE),'LocalCoreMetrics':sum(local.get(m) is not None for m in CORE),
                'HistoricalCellsPresent':int(hist.Value.notna().sum()),'HistoricalCellsTotal':len(hist),
                'CAR_AsOf':snap.get('CAR_AsOf'),'NoRawMode':True,
                'MissingWithoutRaw':[m for m in CORE if q[m]['Value'] is None],
            })
            if compared==0:result['Failures'].append(ticker+': chưa đối chiếu được chỉ tiêu nào')
            if ticker=='ABB':
                result['ABB']={m:q[m]['Value'] for m in CORE}
                result['ABB']['NPAT_YTD']=at_period(ticker,'BANK',target,'YTD',cloud)['NPAT']['Value']
                result['ABB']['NPAT_TTM']=snap.get('NPAT')
                result['ABB']['Source']=q['TotalAssets']['Source']
    result['Result']='PASS' if not result['Failures'] else 'FAIL'
    result['Note']='Đối chiếu dữ liệu đã lưu, gồm chế độ không có data/raw. PASS xác nhận luồng đọc; không khẳng định mọi chỉ tiêu đều đủ hoặc app Cloud đã cập nhật.'
    return result


def main():
    try:result=check()
    except Exception as exc:
        result={'Result':'FAIL','Error':f'{type(exc).__name__}: {exc}'}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    try:print(text)
    except UnicodeEncodeError:print(json.dumps(result,ensure_ascii=True,indent=2))
    return 0 if result['Result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
