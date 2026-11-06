"""Xuất dữ liệu tài chính có thể đưa lên Git, không gọi API hay cần khóa.

Chỉ giữ mã dòng semantic dùng bởi engine; giữ kỳ, cơ sở và nguồn gốc.
Chạy tại máy có data/raw để cập nhật gói triển khai sau mỗi lần refresh.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.financial_evidence import MAP, normalize_raw, period, read_csv


def export_ticker(ticker, raw_dir, destination, basis_config=None):
    parts=[]
    basis_config=pd.DataFrame() if basis_config is None else basis_config
    for ds in ('balance','income','cashflow','ratio'):
        path=next((p for p in (raw_dir/f'{ticker}_{ds}.csv',raw_dir/f'{ticker}_{ds}_q.csv') if p.exists()),None)
        if path is None:continue
        basis='QUARTER'
        if {'Ticker','Dataset','Basis'}.issubset(basis_config):
            match=basis_config[basis_config.Ticker.eq(ticker)&basis_config.Dataset.eq(ds)]
            if len(match):basis=str(match.iloc[-1].Basis).upper()
        data=normalize_raw(pd.read_csv(path),f'data/raw/{path.name}',basis)
        fields={sid for dataset,ids in MAP.values() if dataset==ds for sid in ids}
        data=data[data.Field.isin(fields)].copy()
        # Giữ cả dòng lỗi mâu thuẫn; không biến lỗi thành một giá trị tùy ý.
        if data.Error.fillna('').ne('').any():
            raise ValueError(f'{ticker}/{ds}: giá trị mâu thuẫn; cần xử lý nguồn trước khi xuất')
        data=data[data.Value.notna()]
        data['Ticker']=ticker;data['Dataset']=ds
        data['Unit']=data.Unit.fillna('').replace('', 'SOURCE_NATIVE')
        parts.append(data)
    if not parts:return {'Ticker':ticker,'Status':'NO_SOURCE'}
    result=pd.concat(parts,ignore_index=True)
    if result.empty:return {'Ticker':ticker,'Status':'NO_VALID_SEMANTIC_PERIOD'}
    columns=['Ticker','Dataset','Period','Field','Value','Basis','Unit','Source']
    result=result[columns].sort_values(['Dataset','Field','Period']).reset_index(drop=True)
    destination.mkdir(parents=True,exist_ok=True)
    output=destination/f'{ticker}.csv.gz'
    temp=destination/f'{ticker}.tmp.gz'
    result.to_csv(temp,index=False,compression={'method':'gzip','mtime':0})
    temp.replace(output)
    periods=sorted(set(result.Period),key=period)
    return {'Ticker':ticker,'Status':'EXPORTED','Rows':len(result),'FirstPeriod':periods[0],
            'LastPeriod':periods[-1],'Datasets':sorted(result.Dataset.unique()),
            'SHA256':hashlib.sha256(output.read_bytes()).hexdigest()}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw')
    ap.add_argument('--output-dir',type=Path,default=ROOT/'data/financial_evidence')
    ap.add_argument('--tickers',nargs='+')
    args=ap.parse_args()
    universe=read_csv(ROOT/'config/company_universe.csv')
    # Ngân hàng có hợp đồng nguồn riêng; không thay đổi trong bản sửa phi tài chính.
    tickers=args.tickers or universe.loc[universe.EntityType.ne('BANK'),'Ticker'].tolist()
    basis=read_csv(ROOT/'config/raw_period_basis.csv');rows=[]
    for i,t in enumerate(tickers,1):
        try:rows.append(export_ticker(t,args.raw_dir,args.output_dir,basis))
        except Exception as exc:rows.append({'Ticker':t,'Status':'ERROR','Reason':str(exc)})
        if i%100==0:print(f'Đã kiểm tra {i}/{len(tickers)} mã',flush=True)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    manifest={'SchemaVersion':1,'Source':'Dữ liệu semantic đã lưu từ nguồn BCTC; không bổ sung số ước tính',
              'UnitContract':'Giữ đơn vị nguồn: tiền VND, tỷ số thập phân, số lượng cổ phiếu',
              'Tickers':rows}
    (args.output_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(pd.Series([r['Status'] for r in rows]).value_counts().to_json(),flush=True)
    return int(any(r['Status']=='ERROR' for r in rows))


if __name__=='__main__':raise SystemExit(main())
