"""Phạm vi so sánh ngành cho báo cáo; tách khỏi peer dùng để định giá/XHTN."""
import pandas as pd
from scripts.universal_data import get_company, universe
from scripts.financial_evidence import at_period, latest_period, comparable_model, insurance_reporting_subtype, _record

# Chỉ tiêu kế toán chung có thể đối chiếu quy mô/tỷ số giữa các loại hình.
# Các chỉ tiêu nghiệp vụ còn lại dùng nhóm so sánh cấu hình trong registry.
SECTOR_METRICS = frozenset({
    'Revenue', 'TotalAssets', 'NPAT', 'ROE', 'ROA', 'NetMargin',
    'Equity', 'EquityAssets', 'PaidInCapital', 'InvestmentIncome',
    'DebtEquity', 'DebtDue24MEquity', 'PB', 'PE',
})
SUBTYPE_LABELS = {'NONLIFE':'Phi nhân thọ', 'LIFE':'Nhân thọ',
                  'REINSURANCE':'Tái bảo hiểm', 'GROUP':'Tập đoàn bảo hiểm'}
POLICY_NOTE = ('Chỉ tiêu tài chính chung đối chiếu toàn bộ nhóm bảo hiểm trong danh mục; '
               'chỉ tiêu nghiệp vụ dùng nhóm so sánh đã cấu hình. BVH và PVI thuộc nhóm Phi nhân thọ. '
               'Số liệu hợp nhất của hai mã được giữ nguyên phạm vi; bình quân mẫu chỉ để tham khảo, không dùng trực tiếp để chấm XHTN hoặc định giá.')


def same_peer_group(target,peer):
    a=str(target.get('InsuranceSubtype','')).strip().upper()
    b=str(peer.get('InsuranceSubtype','')).strip().upper()
    return (target.get('EntityType')==peer.get('EntityType')=='INSURANCE'
            and a in SUBTYPE_LABELS and a==b)


def configured_peer_universe(ticker):
    meta=get_company(ticker)
    companies={r['Ticker']:r for r in universe().to_dict('records')}
    return [t for t in peer_universe(ticker) if same_peer_group(meta,companies[t])]


def peer_universe(ticker, same_model=False):
    """Không cắt top 10, không loại âm thầm mã thiếu số ở quý đang so sánh."""
    ticker=str(ticker).strip().upper();meta=get_company(ticker);u=universe()
    if meta.get('EntityType')!='INSURANCE' or u.empty:return []
    candidates=u[u.EntityType.eq('INSURANCE') & u.Ticker.ne(ticker)].drop_duplicates('Ticker')
    rows=candidates.to_dict('records')
    if same_model:rows=[r for r in rows if comparable_model(meta,r)]
    target=latest_period(ticker,'INSURANCE')
    def order(r):
        e=at_period(r['Ticker'],'INSURANCE',target,'QUARTER').get('TotalAssets',{}) if target else {}
        v=e.get('Value');valid=e.get('Status')=='OK' and pd.notna(v)
        return (0 if valid else 1, -float(v) if valid else 0, r['Ticker'])
    return [r['Ticker'] for r in sorted(rows,key=order)]


def scope_label(metric):
    return 'Toàn nhóm bảo hiểm' if metric in SECTOR_METRICS else 'Nhóm so sánh bảo hiểm đã cấu hình'


def quarter_peers(ticker,metric,target,peers=None):
    ticker=str(ticker).strip().upper()
    # Đọc metadata một lần cho cả nhóm, tránh dựng lại universe cho từng mã.
    companies={r['Ticker']:r for r in universe().to_dict('records')}
    meta=companies.get(ticker,{})
    peers=peer_universe(ticker) if peers is None else peers
    # Danh sách truyền từ bên ngoài vẫn phải loại trùng, loại chính DN và khác ngành.
    candidates=list(dict.fromkeys(str(t).strip().upper() for t in peers))
    candidates=[t for t in candidates if t!=ticker and companies.get(t,{}).get('EntityType')=='INSURANCE']
    rows=[]
    for t in [ticker]+candidates:
        company=companies.get(t,{})
        e=at_period(t,'INSURANCE',target,'QUARTER').get(metric,_record(metric,per=target)) if target else _record(metric)
        subtype=company.get('InsuranceSubtype','')
        reporting_subtype=insurance_reporting_subtype(company)
        rows.append(dict(Ticker=t,Value=e['Value'],Status=e['Status'],Period=target,
                         Basis=e['Basis'],Source=e['Source'],Reason=e['Reason'],
                         InsuranceSubtype=subtype,Model=SUBTYPE_LABELS.get(subtype,'Chưa xác minh'),
                         InsuranceReportingSubtype=reporting_subtype,
                         ReportingScope=company.get('InsuranceScope','Chưa xác minh'),
                         SamePeerGroup=same_peer_group(meta,company),
                         SameModel=comparable_model(meta,company)))
    own=rows[0]
    for r in rows:
        reason=''
        if r['Status']!='OK' or pd.isna(r['Value']):
            reason='Không áp dụng' if r['Status']=='NOT_APPLICABLE' else 'Thiếu số hợp lệ đúng quý'
        elif own['Status']=='NOT_APPLICABLE':reason='Chỉ tiêu không áp dụng cho doanh nghiệp đang phân tích'
        elif r['Basis']!=own['Basis']:reason='Khác cơ sở tính'
        elif r['Ticker']!=ticker and metric not in SECTOR_METRICS and not r['SamePeerGroup']:
            reason='Khác nhóm so sánh đối với chỉ tiêu nghiệp vụ'
        r['Included']=not reason
        r['ExclusionReason']=reason
    return pd.DataFrame(rows)


def included_rows(frame):
    """Một bộ lọc cho số đếm, thống kê, biểu đồ UI và Word."""
    return frame[frame.Included] if len(frame) else frame


def exclusion_text(frame):
    if not len(frame):return ''
    excluded=frame.iloc[1:][~frame.iloc[1:].Included]
    groups=[]
    for reason,rows in excluded.groupby('ExclusionReason',sort=False):
        groups.append(', '.join(rows.Ticker)+': '+reason.lower())
    return ('Không đưa vào so sánh: '+'; '.join(groups)+'.') if groups else ''
