from pathlib import Path
import pandas as pd
from scripts.universal_data import get_company,get_snapshot,num,universe
from scripts.sector_kpi_engine import sector_kpi_table
from scripts.multisector_valuation import valuation
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
PCT={'ROE','ROA','NPL','CAR','CASA','NIM','LDR','AvailableCapitalRatio'}
LOWER={'NPL','DebtEquity'}; VAL={'PE','PB'}
def fmt(v,m):
    v=num(v)
    if v is None:return 'N/A'
    if m in PCT:return (f'{v*100:.1f}%').replace('.',',')
    if m in VAL:return (f'{v:.2f}x').replace('.',',')
    if abs(v)>=1e12:return (f'{v/1e12:,.1f} nghìn tỷ').replace(',','X').replace('.',',').replace('X','.')
    if abs(v)>=1e9:return (f'{v/1e9:,.1f} tỷ').replace(',','X').replace('.',',').replace('X','.')
    if abs(v)>=1e6:return (f'{v/1e6:,.1f} triệu').replace(',','X').replace('.',',').replace('X','.')
    return f'{v:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
def analyze(ticker):
    meta=get_company(ticker); snap=get_snapshot(ticker); k,key,tmpl=sector_kpi_table(ticker); val=valuation(ticker,snap)
    fs=[];score=0
    for _,r in k.iterrows():
        c=num(r['Doanh nghiệp']);m=num(r['Trung bình ngành'])
        if c is None or m in (None,0):continue
        gap=c/m-1
        if abs(gap)<.05: pts=0
        else:
            good=(gap<0) if r.Metric in LOWER|VAL else (gap>0)
            pts=(2 if abs(gap)>=.25 else 1)*(1 if good else -1)
        score+=pts;fs.append({'Metric':r.Metric,'Label':r['Chỉ tiêu'],'Gap':gap,'Score':pts,'Company':c,'Mean':m,'N':int(r['Số DN có dữ liệu'])})
    pos=sorted([x for x in fs if x['Score']>0],key=lambda x:abs(x['Gap']),reverse=True)[:6]
    neg=sorted([x for x in fs if x['Score']<0],key=lambda x:abs(x['Gap']),reverse=True)[:6]
    def sent(x):
        d='cao hơn' if x['Gap']>0 else 'thấp hơn';g=(f"{abs(x['Gap'])*100:.1f}").replace('.',',')
        return f"{x['Label']} {fmt(x['Company'],x['Metric'])}, {d} trung bình ngành {fmt(x['Mean'],x['Metric'])} khoảng {g}% (mẫu {x['N']} DN)."
    f={x['Metric']:x for x in fs};inter=[]
    if all(x in f for x in ['ROE','DebtEquity']) and f['ROE']['Gap']>0 and f['DebtEquity']['Gap']>0:inter.append('ROE cao hơn ngành đi cùng đòn bẩy cao hơn ngành; không nên áp premium định giá chỉ dựa trên ROE.')
    if all(x in f for x in ['ROE','PB']) and f['ROE']['Gap']>0 and f['PB']['Gap']>0:inter.append('Khả năng sinh lợi cao hơn ngành đã được phản ánh một phần vào P/B cao hơn ngành; cần tránh cộng premium hai lần.')
    if all(x in f for x in ['NPL','CAR']) and f['NPL']['Gap']>0 and f['CAR']['Gap']<0:inter.append('NPL cao hơn ngành đồng thời CAR thấp hơn ngành là tổ hợp bất lợi cần stress test thận trọng.')
    if 'PE' in f and f['PE']['Gap']<-.15:inter.append('P/E discount đáng kể so với ngành chỉ hấp dẫn nếu không xuất phát từ suy giảm lợi nhuận hoặc rủi ro cấu trúc.')
    if 'PB' in f and f['PB']['Gap']<-.15:inter.append('P/B discount tạo dư địa re-rating nếu ROE và chất lượng tài sản cải thiện; discount có thể hợp lý nếu hiệu quả vốn yếu.')
    if not inter:inter=['Chưa có tín hiệu chéo đủ mạnh; kết luận nên dựa trên nhiều nhóm chỉ tiêu thay vì một KPI đơn lẻ.']
    view='TÍCH CỰC' if score>=5 else 'THẬN TRỌNG' if score<=-5 else 'TRUNG LẬP'
    fair=num(val.get('FairValue'));price=num(val.get('Price'));up=(fair/price-1) if fair and price else None
    conc=f'Quan điểm định lượng tổng hợp: {view}. '
    conc+=('Chưa đủ dữ liệu để lượng hóa upside/downside.' if up is None else f"Giá trị tham chiếu của engine chênh khoảng {(f'{up*100:.1f}').replace('.',',')}% so với thị giá; đây là kết quả mô hình, không phải khuyến nghị mua/bán.")
    return {'Ticker':ticker,'CompanyName':meta.get('DisplayName',meta.get('CompanyName')),'Sector':meta.get('Sector'),'Template':tmpl['label'],'Focus':tmpl['focus'],'Score':score,'View':view,'Strengths':[sent(x) for x in pos],'Risks':[sent(x) for x in neg],'Interpretations':inter,'Conclusion':conc}
def export_all():
    rows=[]
    for t in universe().Ticker:
        try:
            a=analyze(t);rows.append({k:a[k] for k in ['Ticker','Sector','Template','Score','View','Conclusion']})
        except Exception as e:rows.append({'Ticker':t,'Error':str(e)})
    z=pd.DataFrame(rows);z.to_csv(DATA/'intelligent_analyst_summary.csv',index=False,encoding='utf-8-sig');return z
if __name__=='__main__':print(export_all().head())
