"""Regression tests for export identity and conditional, method-based scoring."""
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import patch
import re
import pytest
from docx import Document
from scripts.report_identity import export_date, report_filename, report_header, NOTICE
from scripts.report_rating import (rate_company, corporate_anchor, threshold_risk,
    securities_capital, Evidence, _corporate, _financial_institution, _insurance)


def test_export_date_uses_vietnam_and_one_name_without_build():
    when=datetime(2026,11,1,18,0,tzinfo=timezone.utc)
    assert str(export_date(when))=='2026-11-02'
    assert report_filename('tcb','rating',when)=='Báo cáo XHTN không chỉ định TCB 02-11-2026.docx'
    assert report_header('TCB',when)=='TCB - Báo cáo xếp hạng tín nhiệm không chỉ định - ban hành ngày 02/11/2026'
    with pytest.raises(ValueError):report_filename('../TCB')


@pytest.mark.parametrize('i',range(16))
def test_corporate_anchor_exact_boundaries_without_rounding(i):
    from scripts.report_rating import SCALE
    boundary=1+i*.3125
    assert corporate_anchor(boundary)==SCALE[i]
    assert corporate_anchor(boundary+1e-7)==SCALE[i+1]


def test_absolute_cashflow_and_capital_benchmarks():
    assert threshold_risk(-.1,[.5,.35,.25,.15,.10],True)==6
    assert threshold_risk(2,[1.5,2,3,4,5])==3
    assert securities_capital(.9,None,None)==2
    assert securities_capital(2.5,6,2)==4
    assert securities_capital(.5,1.7,2)==6
    assert securities_capital(None,None,None) is None


class Data:
    period='2026-Q2';peers=['AAA','BBB','CCC'];rows=[]
    def __init__(self,values,score=3):
        self.values=values;self.rows=[];self.score=score
        self.records={k:{'Value':v,'Status':'OK','Period':self.period,'Basis':'DERIVED_TTM' if k in {'CFO','FOCF','CFO_Debt','FOCF_Debt'} else 'END_PERIOD'} for k,v in values.items()}
    def value(self,key):return self.values.get(key)
    def peer_score(self,specs):return self.score
    def add(self,metric,value,score=None,rule='',count=None):
        self.rows.append({'Chỉ tiêu':metric,'Giá trị':value,'Điểm':score,'Cách chấm':rule,'Kỳ':self.period})


def test_corporate_deterioration_changes_score_not_ticker_and_negative_ebitda_not_strong():
    good=Data({'TotalDebt':100,'EBITDA':100,'DebtEBITDA':1,'CFO_Debt':.6,'FOCF_Debt':.5,'CFO':60})
    bad=Data({'TotalDebt':100,'EBITDA':-10,'DebtEBITDA':-10,'CFO_Debt':-.1,'FOCF_Debt':-.3,'CFO':-10})
    r1=_corporate('HPG',{},good,{})
    r2=_corporate('HPG',{},bad,{})
    r3=_corporate('ANY',{},good,{})
    assert r1['ICR']==r3['ICR'] and r1['WeightedScore']<r2['WeightedScore']
    assert bad.rows[0]['Điểm']==6
    assert r1['AssessmentComplete'] is False
    assert r1['RatingOrigin']=='AUTO_RESEARCH'
    assert r1['Assumptions']
    assert r1['Outlook']=='Chưa đánh giá'


def test_missing_financial_inputs_never_become_neutral_score():
    r=_corporate('ZZ',{},Data({}),{})
    assert r['ICR']=='N/A' and not r['DataSufficientForAutoRating']


def test_securities_uses_total_liabilities_not_borrowings_and_matrix():
    data=Data({'TotalAssets':400,'Equity':100,'TotalDebt':20,'DebtEquity':.2,'CurrentRatio':2})
    r=_financial_institution('ZZ','SECURITIES',{},data,{})
    assert r['Factors']['Vốn và Lợi nhuận']=='Trung Bình'
    assert r['FactorNotches']['Nguồn vốn và Thanh khoản']==0
    assert data.rows[0]['Giá trị']==3


def test_peer_score_excludes_issuer_stale_and_ties_not_all_best():
    def rec(value,period='2026-Q2'):
        return {m:{'Value':value,'Status':'OK','Period':period,'Basis':'POINT'} for m in ['A','B']}
    rows={'X':rec(5),'P1':rec(5),'P2':rec(5),'P3':rec(5),'P4':rec(100,'2025-Q2')}
    with patch('scripts.report_rating.latest_period',return_value='2026-Q2'),patch('scripts.report_rating.get_company',return_value={'EntityType':'CORPORATE'}),patch('scripts.report_rating.peer_tickers',return_value=list(rows)),patch('scripts.report_rating.comparable_model',return_value=True),patch('scripts.report_rating.at_period',side_effect=lambda t,*a:rows[t]):
        data=Evidence('X','CORPORATE')
        assert data.peer_score([('A',.5,True),('B',.5,True)])==3.5
        assert all(r['Số peer']==3 for r in data.rows)
        assert 'X' not in data.peers


def test_insurance_capital_reference_is_disclosed_not_written_as_source():
    data=Data({'PaidInCapital':1e12,'CombinedRatio':.95})
    before=dict(data.values)
    r=_insurance('ZZ',{},data,{})
    assert data.values==before and 'RequiredCapital' not in data.values
    assert r['CapitalReferenceIsAssumption'] and r['CapitalReferenceAmount']==500e9
    assert r['CapitalEarningsScore']==6  # exact ratio 2: weaker boundary
    assert r['ICR']!='N/A' and not r['AssessmentComplete']
    assert any('không phải vốn pháp định' in x for x in r['Assumptions'])


def test_saved_bank_grade_and_out_of_scope_insurers_preserved():
    tcb=rate_company('TCB',{'UseDomesticCalibration':False})
    assert tcb['ICR']==rate_company('TCB')['ICR'] and tcb['RatingOrigin']=='AUTO_RESEARCH'
    bvh=rate_company('BVH')
    assert bvh['ICR']=='N/A' and bvh['RatingBlocker']=='SCOPE'


@pytest.mark.parametrize('ticker',['TCB','SSI','ABI','HPG'])
def test_every_sector_cover_and_export_metadata(ticker):
    from scripts.report_evidence import build_pack
    from scripts.professional_report import generate_docx
    p=build_pack(ticker);p['Sections']=[]
    with patch('scripts.professional_report.build_pack',return_value=p):
        d=Document(BytesIO(generate_docx(ticker,'rating',mna={'export_date':'2026-11-02'})))
    assert d.tables[0].cell(0,0).text.startswith('Báo cáo Xếp hạng tín nhiệm không chỉ định')
    texts=[x.text for x in d.paragraphs]
    assert 'Tài liệu này chỉ phục vụ mục đích nghiên cứu' not in texts
    assert 'Tác giả: Lê Hoàng Quân, phát hành ngày 02/11/2026' in texts
    assert NOTICE in texts
    assert report_header(ticker,'2026-11-02') in d.sections[0].header.paragraphs[0].text
    for footer in [d.sections[0].footer,d.sections[0].first_page_footer]:
        assert NOTICE in footer.paragraphs[0].text
    assert not re.search(r'V?8[._]1\d\d[._]\d',d.element.xml)
    if ticker=='SSI':assert 'NGÀNH: CHỨNG KHOÁN' in texts
    if ticker!='TCB':
        assert 'Bậc ước tính tự động' in d.element.xml
        assert 'CĂN CỨ ĐỊNH LƯỢNG' in d.element.xml
