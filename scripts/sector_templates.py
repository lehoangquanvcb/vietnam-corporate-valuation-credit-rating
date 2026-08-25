from pathlib import Path
import re, unicodedata, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; CFG=ROOT/'config'

TEMPLATES={
'BANK': {'label':'Ngân hàng','metrics':['TotalAssets','ROE','ROA','NIM','NPL','CAR','CASA','LDR','PB'],'valuation':['P/B','Residual Income'],'focus':['Chất lượng tài sản','Vốn','Nguồn vốn & thanh khoản','Khả năng sinh lợi']},
'SECURITIES': {'label':'Công ty chứng khoán','metrics':['Revenue','NPAT','ROE','ROA','AvailableCapitalRatio','DebtEquity','CurrentRatio','PB','PE'],'valuation':['P/B','P/E'],'focus':['Thị phần & franchise','Vốn khả dụng','Đòn bẩy','Thanh khoản','Cơ cấu doanh thu']},
'REAL_ESTATE': {'label':'Bất động sản','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PB','PE'],'valuation':['P/B','P/E','RNAV (khi có dữ liệu dự án)'],'focus':['Quỹ đất & pháp lý','Presales/người mua trả tiền trước','Tồn kho','Nợ ròng/VCSH','Dòng tiền dự án']},
'STEEL_MATERIALS': {'label':'Thép & vật liệu','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['P/E','EV/EBITDA'],'focus':['Sản lượng','Biên lợi nhuận','Giá nguyên liệu','Vòng quay tồn kho','Chu kỳ ngành']},
'POWER_UTILITIES': {'label':'Điện & tiện ích','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['EV/EBITDA','P/E','DCF'],'focus':['Công suất','Sản lượng','Giá bán điện','EBITDA margin','Nợ dự án']},
'OIL_GAS': {'label':'Dầu khí','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['EV/EBITDA','P/E','DCF'],'focus':['Giá dầu/khí','Sản lượng','Backlog','Biên EBITDA','CAPEX']},
'RETAIL': {'label':'Bán lẻ','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['P/E','EV/EBITDA','DCF'],'focus':['SSSG','Doanh thu/cửa hàng','Mở mới/đóng cửa','Biên gộp','Vòng quay tồn kho']},
'TECH': {'label':'Công nghệ','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['P/E','EV/EBITDA','DCF'],'focus':['Tăng trưởng doanh thu','Doanh thu lặp lại','Biên lợi nhuận','Nhân sự kỹ thuật','Thị trường xuất khẩu']},
'LOGISTICS': {'label':'Logistics & cảng','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['EV/EBITDA','P/E','DCF'],'focus':['Sản lượng thông qua','Công suất','Giá dịch vụ','Utilization','CAPEX']},
'CONSUMER': {'label':'Tiêu dùng & thực phẩm','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['P/E','EV/EBITDA','DCF'],'focus':['Sản lượng','Giá bán','Biên gộp','Thương hiệu','Kênh phân phối']},
'CONSTRUCTION_INFRA': {'label':'Xây dựng & hạ tầng','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['P/E','EV/EBITDA','DCF'],'focus':['Backlog','Tiến độ','Phải thu','Dòng tiền','Nợ vay']},
'CHEMICALS': {'label':'Hóa chất','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['P/E','EV/EBITDA','DCF'],'focus':['Giá đầu vào','Giá bán','Công suất','Biên EBITDA','Chu kỳ hàng hóa']},
'INDUSTRIALS': {'label':'Công nghiệp','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['P/E','EV/EBITDA','DCF'],'focus':['Đơn hàng','Công suất','Biên lợi nhuận','CAPEX','Vòng quay vốn']},
'GENERIC_CORPORATE': {'label':'Doanh nghiệp phi tài chính','metrics':['Revenue','NPAT','ROE','ROA','DebtEquity','CurrentRatio','PE','PB'],'valuation':['P/E','EV/EBITDA','P/B'],'focus':['Vị thế kinh doanh','Khả năng sinh lợi','Đòn bẩy','Thanh khoản','Dòng tiền']}
}

def norm(s):
    return unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()

def template_key(entity_type,sector):
    if entity_type=='BANK': return 'BANK'
    if entity_type=='SECURITIES': return 'SECURITIES'
    n=norm(sector)
    rules=[
      ('REAL_ESTATE',['bat dong san','real estate']),
      ('STEEL_MATERIALS',['thep','kim loai','vat lieu','basic resources']),
      ('POWER_UTILITIES',['dien','tien ich','utilities','electric']),
      ('OIL_GAS',['dau khi','oil','gas']),
      ('RETAIL',['ban le','retail']),
      ('TECH',['cong nghe','technology','phan mem']),
      ('LOGISTICS',['logistics','van tai','cang','transportation']),
      ('CONSUMER',['thuc pham','do uong','hang tieu dung','food','beverage','consumer']),
      ('CONSTRUCTION_INFRA',['xay dung','ha tang','construction']),
      ('CHEMICALS',['hoa chat','chemical']),
      ('INDUSTRIALS',['cong nghiep','industrial'])
    ]
    for k,words in rules:
        if any(w in n for w in words): return k
    return 'GENERIC_CORPORATE'

def enrich_universe():
    p=CFG/'company_universe.csv'; u=pd.read_csv(p)
    u['SectorTemplate']=u.apply(lambda r:template_key(str(r.get('EntityType','')),str(r.get('Sector',''))),axis=1)
    u['SectorTemplateLabel']=u.SectorTemplate.map(lambda k:TEMPLATES.get(k,TEMPLATES['GENERIC_CORPORATE'])['label'])
    u.to_csv(p,index=False,encoding='utf-8-sig')
    return u

def get_template(entity_type,sector):
    k=template_key(entity_type,sector); return k,TEMPLATES[k]

if __name__=='__main__':
    u=enrich_universe(); print(u.groupby(['SectorTemplate','SectorTemplateLabel']).size().reset_index(name='Companies').to_string(index=False))
