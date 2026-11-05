from datetime import date, datetime, timezone
from io import BytesIO
import csv
import json
from unittest.mock import patch

import pandas as pd
import pytest
from docx import Document
from scripts import public_company_profile as profile
from scripts.report_context import research_sections, issuer_context
from scripts.report_strengths import summary_findings


def test_public_profile_validates_symbol_and_caches_without_copying_whole_source(tmp_path):
    payload = {'SB':'TEST', 'FD':'01/02/2000', 'LD':'03/04/2010', 'EX':'HOSE',
               'SM':'<p>Hoạt động <script>unsafe text</script>'+('dịch vụ '*30)+'</p>',
               'URL':'javascript:bad()', 'AD':'2025-01-01'}
    with patch.object(profile,'urlopen',return_value=BytesIO(json.dumps(payload).encode())) as get:
        row=profile.fetch_public_profile('TEST',cache_dir=tmp_path)
    assert row['Ticker']=='TEST' and row['Established']=='01/02/2000'
    assert row['SourceDate']=='' and row['Website']==''
    assert 'unsafe' not in row['BusinessExcerpt'] and len(row['BusinessExcerpt'].split())<=24
    with patch.object(profile,'urlopen',side_effect=AssertionError('must use cache')):
        assert profile.fetch_public_profile('TEST',cache_dir=tmp_path)==row
    payload['SB']='OTHER'
    with patch.object(profile,'urlopen',return_value=BytesIO(json.dumps(payload).encode())):
        assert profile.fetch_public_profile('TEST',cache_dir=tmp_path,force=True)==row
        assert profile.fetch_public_profile('MISS',cache_dir=tmp_path) is None
    assert not (tmp_path/'MISS.json').exists()


def test_public_profile_timeout_offline_and_past_export(tmp_path):
    with patch.object(profile,'urlopen',side_effect=TimeoutError('source unavailable')) as get:
        assert profile.fetch_public_profile('FAIL',cache_dir=tmp_path) is None
        assert profile.fetch_public_profile('FAIL',cache_dir=tmp_path) is None
        assert get.call_count==1
        assert profile.fetch_public_profile('OFF',cache_dir=tmp_path,allow_network=False) is None
        assert profile.fetch_public_profile('../BAD',cache_dir=tmp_path) is None
        assert profile.fetch_public_profile('PAST',cache_dir=tmp_path,as_of='2020-01-01') is None
        assert get.call_count==1


def test_research_routing_all_registry_tickers_and_source_dates():
    rows=list(csv.DictReader((profile.ROOT/'config/company_universe.csv').open(encoding='utf-8-sig')))
    assert len(rows)>1700
    texts={}
    for r in rows:
        pack={'Ticker':r['Ticker'],'Type':r['EntityType'],'Meta':r}
        sections=research_sections(pack,date(2026,11,5))
        assert len(sections)==2
        assert len(sections[0][1])>=2 and len(sections[1][1])>=3
        for _, blocks in sections:
            assert all(b['Source']['URL'].startswith('https://') and b['Analysis'] for b in blocks)
        texts.setdefault(r['EntityType'],str(sections[1]))
    assert len(set(texts.values()))==4
    assert research_sections(pack,date(2020,1,1))==[]


def test_curated_profile_wins_and_fallback_does_not_invent_business():
    pack={'Ticker':'OCB','Type':'BANK','Meta':{'DisplayName':'OCB'}}
    with patch.object(profile,'fetch_public_profile',side_effect=AssertionError('curated profile wins')):
        paragraphs,source=issuer_context(pack,date(2026,11,5))
    assert len(paragraphs)>=3 and 'ocb.com.vn' in source['URL']
    pack['Ticker']='ZZTEST'
    with patch.object(profile,'fetch_public_profile',return_value=None):
        paragraphs,source=issuer_context(pack,date(2026,11,5))
    assert source is None and any('Chưa lấy được' in p for p in paragraphs)


@pytest.mark.parametrize('ticker',['OCB','SSI','ABI','HPG'])
def test_shared_export_compact_order_two_charts_no_intermediate_table(ticker,monkeypatch):
    from scripts import professional_report as report
    from scripts.report_evidence import build_pack
    pack=build_pack(ticker);metric=next(m for m,x in pack['Items'].items() if x['History'].Value.notna().any())
    pack['Sections']=[('Chỉ tiêu kiểm tra',[metric])]
    monkeypatch.setattr(report,'build_pack',lambda *a:pack)
    monkeypatch.setenv('REPORT_PROFILE_OFFLINE','1')
    doc=Document(BytesIO(report.generate_docx(ticker,'rating',{'ICR':'N/A','Factors':{}}, {'export_date':'2026-11-05'})))
    assert len(doc.inline_shapes)==2
    xml=doc.element.xml
    assert 'w:type="page"' not in xml and 'w:pageBreakBefore' not in xml
    text='\n'.join(p.text for p in doc.paragraphs)
    assert text.index('THÔNG TIN TỔNG QUAN') < text.index('LỊCH SỬ TÀI CHÍNH') < text.index('RỦI RO VĨ MÔ') < text.index('RỦI RO NGÀNH')
    assert 'Các trọng tâm tài chính' not in text
    nodes=list(doc.element.body);positions=[i for i,n in enumerate(nodes) if n.xpath('.//w:drawing')]
    assert len(positions)==2 and not any(n.tag.endswith('}tbl') for n in nodes[positions[0]+1:positions[1]])
    history=next(t for t in doc.tables if t.rows[0].cells[0].text=='Chỉ tiêu' and len(t.columns)==7)
    assert all(not p.paragraph_format.keep_with_next for row in history.rows[1:] for c in row.cells for p in c.paragraphs)
    assert any(rel.reltype.endswith('/hyperlink') for rel in doc.part.rels.values())


def test_summary_does_not_call_negative_cashflow_or_negative_ebitda_strength():
    def item(value, mean):
        return {'Value':value,'PeerMean':mean,'History':pd.DataFrame(columns=['Value','DisplayPeriod'])}
    pack={'Type':'CORPORATE','Period':'2026-Q2','Items':{'CFO_Debt':item(-.1,-.2),'DebtEBITDA':item(-2,3)}}
    strengths,risks=summary_findings(pack)
    assert not strengths and len(risks)==2


def test_annual_investment_cash_deficit_is_retained_in_weaknesses():
    def item(value):
        return {'History':pd.DataFrame([{'DisplayPeriod':'2025','Value':value}])}
    pack={'Type':'CORPORATE','Period':'2026-Q2','Items':{'CFO':item(10e9),'Capex':item(-15e9)}}
    good,bad=summary_findings(pack)
    assert not good and len(bad)==1 and '5,0 tỷ đồng' in bad[0] and 'Năm 2025' in bad[0]
