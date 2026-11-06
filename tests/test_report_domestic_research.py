"""Nguồn đúng thời điểm, tổng quan theo mã và nội dung đúng mô hình hoạt động."""
from datetime import date
import json
from unittest.mock import patch
import pandas as pd
from scripts import report_context as context
from scripts.public_company_profile import public_profile_paragraphs


def test_future_source_is_not_used_even_when_catalog_date_is_old(tmp_path, monkeypatch):
    catalog = json.loads(context.CONTEXT_FILE.read_text(encoding='utf-8'))
    key = catalog['Macro'][0]['Source']
    catalog['Sources'][key]['PublishedOn'] = '2026-12-01'
    path = tmp_path/'research.json'; path.write_text(json.dumps(catalog), encoding='utf-8')
    monkeypatch.setattr(context, 'CONTEXT_FILE', path)
    result = context.research_sections({'Type':'BANK','Meta':{}}, date(2026,11,5))
    assert all(b['Source']['PublishedOn'] != '2026-12-01' for _, blocks in result for b in blocks)


def test_new_abb_profile_is_formal_sourced_and_does_not_replace_rating_inputs():
    pack = {'Ticker':'ABB','Type':'BANK','Meta':{'DisplayName':'ABB'}}
    before = repr(pack)
    with patch('scripts.public_company_profile.fetch_public_profile', side_effect=AssertionError('no fetch')):
        paragraphs, source = context.issuer_context(pack, date(2026,11,5))
    assert 'Ngân hàng' in paragraphs[0] and len(paragraphs) >= 3
    assert source['URL'].startswith('https://') and source['AdditionalSources']
    assert all('KBS (trích)' not in p and '…' not in p for p in paragraphs)
    assert context.issuer_name(pack, date(2026,11,5)) != 'ABB'
    assert not context._research_profile('ABB', date(2026,11,4))
    assert repr(pack) == before


def test_cached_profile_does_not_turn_a_truncated_quote_into_prose():
    row = {'Ticker':'TEST','Established':'01/01/2000','ListedSince':'01/01/2010',
           'Exchange':'HOSE','BusinessExcerpt':'sản xuất hàng tiêu dùng…','Website':'https://example.com'}
    paragraphs = public_profile_paragraphs(row, 'Công ty Kiểm tra')
    assert 'được thành lập' in paragraphs[0] and 'HOSE' in paragraphs[0]
    assert '…' not in str(paragraphs) and 'Website' not in str(paragraphs)


def test_financial_overview_keeps_quarter_balances_separate_from_annual_flows():
    def item(value, history=None):
        return {'Value':value,'History':pd.DataFrame(history or [],columns=['DisplayPeriod','Value'])}
    pack = {'Ticker':'TEST','Type':'CORPORATE','Period':'2026-Q2','Items':{
        'TotalAssets':item(100e9), 'Equity':item(25e9), 'TotalDebt':item(30e9),
        'Revenue':item(7e9,[['2021',40e9],['2025',60e9]])}}
    text = ' '.join(context.issuer_financial_context(pack))
    assert '2026-Q2' in text and '25,00%' in text and '1,20 lần' in text
    assert '40,0 tỷ đồng năm 2021' in text and '60,0 tỷ đồng năm 2025' in text
    assert '7,0 tỷ đồng' not in text
    pack['Items']['Equity']['Value'] = 0
    assert 'inf' not in ' '.join(context.issuer_financial_context(pack))
    pack['Items']['Revenue']['History']['DisplayPeriod']=['6T/2021','6T/2025']
    assert len(context.issuer_financial_context(pack)) == 1


def test_macroeconomic_production_channel_is_specific_to_each_financial_sector():
    texts = []
    for kind in ('BANK','SECURITIES','INSURANCE','CORPORATE'):
        blocks = context.research_sections({'Type':kind,'Meta':{}}, date(2026,11,5))[0][1]
        texts.append(blocks[-1]['Analysis'])
    assert len(set(texts)) == 4
    assert 'ký quỹ' in texts[1] and 'tái bảo hiểm' in texts[2]


def test_domestic_sources_and_broad_financial_sector_do_not_assume_real_estate():
    catalog = json.loads(context.CONTEXT_FILE.read_text(encoding='utf-8'))
    assert all(s['Country']=='VN' for s in catalog['Sources'].values())
    rows = context.research_sections({'Type':'CORPORATE','Meta':{'Sector':'Tài chính'}}, date(2026,11,5))
    text = ' '.join(b['Analysis'] for b in rows[1][1])
    assert 'phân ngành rộng' in text and 'có thể gồm' in text
    assert 'doanh nghiệp bất động sản' not in text


def test_detailed_icb_routes_to_correct_research_sector():
    from scripts.universal_data import get_company
    for ticker, phrase in [('VIC','Khả năng hấp thụ'),('HPG','Chu kỳ giá hàng hóa'),('FPT','Chất lượng hợp đồng')]:
        blocks=context.research_sections({'Type':'CORPORATE','Meta':get_company(ticker)},date(2026,11,6))[1][1]
        assert phrase in blocks[0]['Title']
    old=context.research_sections({'Type':'CORPORATE','Meta':get_company('VIC')},date(2026,11,5))[1][1]
    assert 'Khả năng tạo tiền của danh mục' in old[0]['Title']
