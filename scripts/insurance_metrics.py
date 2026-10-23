"""Chỉ tiêu chuyên ngành có dấu vết nguồn; không suy đoán dữ liệu thuyết minh."""
from pathlib import Path
from scripts.insurance_catalog import MANUAL_INPUTS, MANUAL_FLOWS, MANUAL_RATIOS, FLOW_RATIOS, DEFINITION

RAW_MAP={
 'CharterCapital':('balance',['BS_CHARTER_CAPITAL']),
 'SharePremium':('balance',['BS_SHARE_PREMIUM']),
 'InsuranceClaimsExpense':('income',['IS_TOTAL_INSURANCE_CLAIMS_EXPENSES']),
 'InsuranceOperatingExpense':('income',['IS_TOTAL_DIRECT_INSURANCE_OPERATING_EXPENSES']),
 'InsuranceAdminExpense':('income',['IS_DIRECT_INSURANCE_MANAGEMENT_EXPENSES']),
 'OtherInsuranceIncome':('income',['IS_COMMISSION_ON_REINSURANCE_CEDED_AND_OTHER_INSURANCE_INCOME']),
 'UnderwritingProfit':('income',['IS_PROFIT_FROM_INSURANCE_OPERATING']),
}

def extend_records(ticker,target,basis,records,root):
    from scripts.financial_evidence import _record, read_csv, number, insurance_reporting_subtype
    r=records;provided={}
    def calc(m,keys,fn,den=None,record_basis=None):
        if m in provided:
            r[m]=dict(provided[m]);return
        parts=[r.get(k,_record(k)) for k in keys];vs=[x['Value'] for x in parts]
        if any(v is None for v in vs):
            r[m]=_record(m,per=target,basis=record_basis or basis,
                         status='ERROR' if any(x['Status']=='ERROR' for x in parts) else 'MISSING',
                         reason='Thiếu: '+', '.join(k for k,v in zip(keys,vs) if v is None));return
        if den is not None and vs[keys.index(den)]<=0:
            r[m]=_record(m,per=target,status='NOT_APPLICABLE',reason='Mẫu số không dương');return
        r[m]=_record(m,fn(*vs),record_basis or basis,target,
                     'Công thức '+m+'('+', '.join(keys)+'). Nguồn: '+'; '.join(dict.fromkeys(x['Source'] for x in parts)))
    # Các đầu vào thẩm định phải có kỳ, cơ sở, nguồn, người duyệt và phạm vi.
    f=read_csv(Path(root)/'config/insurance_metric_inputs.csv')
    accepted={}
    if not f.empty:
        required={'Ticker','Period','Metric','Value','Basis','Source','ReviewedBy','Scope','Definition'}
        if not required <= set(f):
            for m in MANUAL_INPUTS:r[m]=_record(m,per=target,status='ERROR',reason='Tệp đầu vào bảo hiểm thiếu cột bắt buộc')
        else:
            q=f[f.Ticker.astype(str).str.upper().eq(ticker)&f.Period.astype(str).eq(target)]
            for m in MANUAL_INPUTS:
                z=q[q.Metric.eq(m)].copy()
                expected=basis if m in MANUAL_FLOWS|FLOW_RATIOS else 'END_PERIOD'
                z=z[z.Basis.eq(expected)]
                if z.empty:continue
                if len(z)!=1:
                    r[m]=_record(m,per=target,status='ERROR',reason='Trùng bản ghi đầu vào cùng kỳ/cơ sở');continue
                row=z.iloc[0];v=number(row.Value)
                valid=all(str(row[k]).strip() not in ('','nan','None') for k in ['Source','ReviewedBy','Scope','Definition'])
                if v is None or not valid:
                    r[m]=_record(m,per=target,status='UNREVIEWED',reason='Thiếu giá trị, nguồn, người duyệt, định nghĩa hoặc phạm vi');continue
                if m in FLOW_RATIOS and str(row.Definition)!=DEFINITION:
                    r[m]=_record(m,per=target,status='UNREVIEWED',reason='Khác định nghĩa tỷ lệ khai thác của bộ so sánh');continue
                r[m]=_record(m,v,('DERIVED_'+basis) if m in FLOW_RATIOS else expected,target,str(row.Source)+' | '+str(row.ReviewedBy)+' | '+str(row.Scope)+' | '+str(row.Definition))
                accepted[m]=r[m]
    provided={m:dict(r[m]) for m in MANUAL_INPUTS if m in r}
    for m in MANUAL_INPUTS:
        if m not in r:r[m]=_record(m,per=target,reason='Cần công bố/thuyết minh đúng kỳ đã thẩm định; nhập tại config/insurance_metric_inputs.csv')
    calc('PaidInCapital',['CharterCapital','SharePremium'],lambda a,b:a+b,record_basis='END_PERIOD')
    calc('PaidInCapitalRequired',['PaidInCapital','RequiredCapital'],lambda a,b:a/b,den='RequiredCapital',record_basis='END_PERIOD')
    calc('LossRatio',['InsuranceClaimsExpense','NetInsurancePremium'],lambda a,b:-a/b,den='NetInsurancePremium',record_basis='DERIVED_'+basis)
    calc('ExpenseRatio',['InsuranceOperatingExpense','InsuranceClaimsExpense','InsuranceAdminExpense','OtherInsuranceIncome','NetInsurancePremium'],
         lambda a,b,c,d,e:(-a+b-c-d)/e,den='NetInsurancePremium',record_basis='DERIVED_'+basis)
    calc('CombinedRatio',['LossRatio','ExpenseRatio'],lambda a,b:a+b,record_basis='DERIVED_'+basis)
    for m in FLOW_RATIOS:
        r[m]['Reason']='Quy ước BCTC thuần; cần đối chiếu trước khi chấm điểm. '+r[m].get('Reason','')
        r[m]['Definition']=DEFINITION
    calc('DebtDue24MEquity',['DebtDue24M','Equity'],lambda a,b:a/b,den='Equity',record_basis='END_PERIOD')
    calc('InsuranceEBITDAInterest',['InsuranceEBITDA','InsuranceInterestExpense'],lambda a,b:a/abs(b),den='InsuranceInterestExpense',record_basis='DERIVED_'+basis)
    liquid=['LiquidCash','DepositsIGUnder6M','DepositsOtherUnder6M','GovernmentBondsLiquid','RatedBondsIGLiquid','RatedBondsOtherLiquid','ListedEquitiesLiquid']
    calc('StressedLiquidAssets',liquid,lambda *v:sum(a*w for a,w in zip(v,[1,.99,.95,1,.9,.65,.5])),record_basis='END_PERIOD')
    calc('InsuranceLiquidity',['StressedLiquidAssets','InsuranceContractObligations'],lambda a,b:a/b,den='InsuranceContractObligations',record_basis='END_PERIOD')
    calc('SolvencyRatio',['SolvencyMargin','MinimumSolvencyMargin'],lambda a,b:a/b,den='MinimumSolvencyMargin',record_basis='END_PERIOD')
    # So sánh số dư/phí quý dùng TTM được ghi rõ, không đổi nhãn thành tỷ số quý.
    premium=r['NetInsurancePremium']
    if basis=='QUARTER':
        from scripts.financial_evidence import source_data, aggregate
        mapped,_=source_data(ticker,'INSURANCE',root)
        premium=aggregate('NetInsurancePremium',mapped['NetInsurancePremium'],target,'TTM')
    r['ReservesPremiumDenominator']=premium
    calc('ReservesPremium',['InsuranceReserves','ReservesPremiumDenominator'],lambda a,b:a/b,den='ReservesPremiumDenominator',record_basis='END_PERIOD / '+('TTM' if basis=='QUARTER' else basis))
    # Phạm vi phi nhân thọ không tự áp cho BCTC hợp nhất hỗn hợp nhân thọ/đầu tư.
    entities=read_csv(Path(root)/'config/insurance_entities.csv')
    z=entities[entities.Ticker.eq(ticker)] if 'Ticker' in entities else entities.iloc[:0]
    if len(z) and insurance_reporting_subtype(z.iloc[0])=='GROUP':
        for m in FLOW_RATIOS|{'PaidInCapitalRequired','ReservesPremium'}:
            r[m]=_record(m,per=target,status='NOT_APPLICABLE',reason='BCTC tập đoàn: cần tách pháp nhân phi nhân thọ và cơ sở phù hợp trước khi tính tỷ số chuyên ngành')
    return r
