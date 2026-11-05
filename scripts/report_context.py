"""Nguồn công khai và nhận định bối cảnh, định tuyến cho mọi loại hình.

Sự kiện nguồn và suy luận tín nhiệm được lưu riêng. Không sửa đầu vào điểm.
Không tải tin lúc mở ứng dụng; hồ sơ doanh nghiệp tải riêng khi xuất file.
"""
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
import json

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_FILE = ROOT / 'data' / 'report_public_context.json'
ISSUER_FILE = ROOT / 'data' / 'report_issuer_research.json'


def _available(row, when):
    """Không đưa nguồn/biên tập tương lai vào bản xuất lùi ngày."""
    for key in ('ResearchedOn', 'PublishedOn', 'AccessedOn'):
        value = str(row.get(key) or '')[:10]
        if value:
            try:
                if date.fromisoformat(value) > when: return False
            except ValueError: return False
    return True


def _research_profile(ticker, when):
    try:
        catalog = json.loads(ISSUER_FILE.read_text(encoding='utf-8'))
        row = catalog.get('Profiles', {}).get(ticker, {})
        if row and _available(catalog, when) and _available(row, when) and all(
                _available(s, when) for s in row.get('Sources', [])):
            return row
    except (OSError, ValueError, TypeError): pass
    return {}


def issuer_name(pack, when):
    researched = _research_profile(pack['Ticker'], when)
    if researched.get('CompanyName'): return researched['CompanyName']
    for key in ('LegalName', 'DisplayName', 'CompanyName'):
        name = str(pack.get('Meta', {}).get(key) or '').strip()
        if name and name.lower() not in {'nan', 'none'} and name != pack['Ticker']: return name
    return pack['Ticker']


def safe_url(value):
    text = str(value or '').strip()
    parsed = urlparse(text)
    return text if parsed.scheme in {'https','http'} and parsed.netloc else ''


def research_sections(pack, when):
    """Chỉ dùng bộ hồ sơ đã tồn tại tại ngày xuất; lọc đúng ngành/mã."""
    catalog = json.loads(CONTEXT_FILE.read_text(encoding='utf-8'))
    if not _available(catalog, when): return []
    sources = catalog['Sources']
    kind = pack['Type']; sector = str(pack['Meta'].get('Sector') or '')
    industry = catalog['Industry'].get(kind, [])
    if kind == 'CORPORATE':
        industry = catalog['CorporateSectors'].get(sector, catalog['CorporateSectors']['DEFAULT'])
    result = []
    for heading, rows in [('RỦI RO VĨ MÔ', catalog['Macro']), ('RỦI RO NGÀNH', industry)]:
        blocks = []
        for row in rows:
            source = sources[row['Source']]
            if not _available(source, when): continue
            analysis = row.get('Analysis', '')
            if isinstance(analysis, dict): analysis = analysis.get(kind, analysis.get('DEFAULT', ''))
            blocks.append({'Title':row['Title'], 'Fact':row.get('Fact', source.get('Fact','')),
                           'Analysis':analysis, 'Source':source,
                           'ResearchedOn':catalog['ResearchedOn']})
        result.append((heading, blocks))
    return result


def issuer_context(pack, when):
    from scripts.company_profile import load_company_profile
    from scripts.public_company_profile import fetch_public_profile, public_profile_paragraphs
    financial = issuer_financial_context(pack)
    researched = _research_profile(pack['Ticker'], when)
    if researched.get('Paragraphs'):
        sources = researched.get('Sources', [])
        source = dict(sources[0], AdditionalSources=sources[1:]) if sources else None
        return researched['Paragraphs'] + financial, source
    curated = load_company_profile(pack['Ticker']) or {}
    name = issuer_name(pack, when)
    # Hồ sơ được biên tập từ trang doanh nghiệp có ưu tiên cao hơn bản tóm tắt KBS.
    curated_date = curated.get('LastUpdated') or curated.get('SourceDate') or ''
    if curated and (not curated_date or curated_date[:10] <= when.isoformat()):
        paragraphs = [curated[k].strip().rstrip('.')+'.' for k in
                      ('Overview','CoreBusinesses','MarketPosition','Strategy') if curated.get(k)]
        if paragraphs:
            return paragraphs + financial, {'Name':curated.get('SourceName','Doanh nghiệp công bố'),
                'URL':safe_url(curated.get('SourceURL')), 'PublishedOn':curated.get('SourceDate',''),
                'AccessedOn':curated.get('LastUpdated','')}
    profile = fetch_public_profile(pack['Ticker'], as_of=when)
    if profile:
        return public_profile_paragraphs(profile, name) + financial, {'Name':profile['SourceName'],
            'URL':profile['SourceURL'], 'PublishedOn':profile.get('SourceDate',''),
            'AccessedOn':profile['RetrievedOn']}
    # Chỉ nêu dữ kiện trong danh mục; không dựng mô hình kinh doanh từ tên mã.
    exchange = pack['Meta'].get('Exchange')
    text = name + ' (' + pack['Ticker'] + ')'
    if exchange and str(exchange).lower() != 'nan': text += ', đăng ký giao dịch/niêm yết tại ' + str(exchange)
    return [text+'.'] + financial + ['Chưa lấy được hồ sơ hoạt động từ nguồn công khai tại lần xuất này.'], None


def issuer_financial_context(pack):
    """Tổng quan riêng theo mã từ BCTC; không trộn dòng quý với số cả năm."""
    from scripts.report_evidence import finite, fmt, vi
    items = pack.get('Items', {})
    kind, ticker = pack.get('Type'), pack['Ticker']
    period = pack.get('Period')
    result = []
    def val(metric): return items.get(metric, {}).get('Value')
    def valid(*metrics): return all(finite(val(m)) for m in metrics)
    if period and valid('TotalAssets', 'Equity') and val('TotalAssets') > 0:
        share = val('Equity') / val('TotalAssets') * 100
        text = (f'Tại kỳ BCTC {period}, tổng tài sản của {ticker} đạt {fmt("TotalAssets", val("TotalAssets"))}, '
                f'vốn chủ sở hữu đạt {fmt("Equity", val("Equity"))}, tương đương {vi(share, 2)}% tổng tài sản. ')
        if kind == 'BANK' and valid('GrossLoans', 'CustomerDeposits') and val('CustomerDeposits') > 0:
            ratio = val('GrossLoans') / val('CustomerDeposits')
            text += (f'Dư nợ cho vay khách hàng bằng {vi(ratio, 2)} lần tiền gửi khách hàng. ' +
                ('Phần dư nợ vượt tiền gửi khách hàng làm tăng nhu cầu sử dụng vốn chủ sở hữu và các nguồn huy động khác; độ ổn định của những nguồn này có ảnh hưởng trực tiếp đến khả năng mở rộng tín dụng.'
                 if ratio > 1 else 'Tiền gửi khách hàng cao hơn dư nợ cho vay, tạo nguồn tài trợ cho các tài sản khác. Mức chênh lệch này hỗ trợ cơ cấu nguồn vốn nhưng chưa phản ánh đầy đủ thanh khoản, do còn phụ thuộc kỳ hạn tiền gửi và khả năng chuyển đổi tài sản thành tiền.'))
        elif kind == 'SECURITIES' and valid('MarginLoans') and val('Equity') > 0:
            text += (f'Cho vay ký quỹ tương đương {vi(val("MarginLoans") / val("Equity"), 2)} lần vốn chủ sở hữu. '
                     'Quy mô dư nợ này gắn khả năng sinh lời với vòng quay giao dịch và giá trị tài sản bảo đảm; khi thị trường giảm sâu, thu hồi nợ có thể chậm hơn nhu cầu hoàn trả vốn vay.')
        elif kind == 'INSURANCE':
            text += 'Vốn chủ sở hữu là nguồn hấp thụ tổn thất khi chi phí bồi thường hoặc dự phòng vượt dự kiến. Chất lượng tài sản đầu tư và tốc độ thu hồi công nợ bảo hiểm quyết định mức độ sẵn có của nguồn lực này khi phát sinh nghĩa vụ chi trả.'
        elif kind == 'CORPORATE' and valid('TotalDebt') and val('Equity') > 0:
            text += (f'Tổng nợ vay bằng {vi(val("TotalDebt") / val("Equity"), 2)} lần vốn chủ sở hữu. '
                     'Khả năng đáp ứng nghĩa vụ nợ phụ thuộc dòng tiền từ hoạt động và tiến độ thu hồi vốn đã đầu tư; quy mô tài sản tự thân không bảo đảm nguồn tiền trả nợ nếu tài sản chủ yếu nằm ở hàng tồn kho, phải thu hoặc dự án dở dang.')
        result.append(text)
    metric = 'TotalAssets' if kind == 'BANK' else 'GrossWrittenPremium' if kind == 'INSURANCE' else 'Revenue'
    history = items.get(metric, {}).get('History')
    if history is not None and len(history) and {'Value', 'DisplayPeriod'} <= set(history.columns):
        rows = history.loc[history.Value.map(finite)]
        if len(rows) >= 2:
            first, last = rows.iloc[0], rows.iloc[-1]
            # Chỉ diễn giải chuỗi năm; không đổi lịch sử cùng kỳ thành doanh thu cả năm.
            if all(str(x).isdigit() and len(str(x)) == 4 for x in rows.DisplayPeriod):
                title = {'TotalAssets':'Tổng tài sản', 'GrossWrittenPremium':'Doanh thu phí bảo hiểm gốc', 'Revenue':'Doanh thu'}[metric]
                text = (f'{title} chuyển từ {fmt(metric, first.Value)} năm {first.DisplayPeriod} lên '
                        f'{fmt(metric, last.Value)} năm {last.DisplayPeriod}. ' if last.Value >= first.Value else
                        f'{title} giảm từ {fmt(metric, first.Value)} năm {first.DisplayPeriod} xuống {fmt(metric, last.Value)} năm {last.DisplayPeriod}. ')
                if kind == 'BANK':
                    text += 'Sự thay đổi quy mô cần được đặt trong tương quan với khả năng bổ sung vốn và tích lũy dự phòng; tài sản tăng nhanh hơn các nguồn lực này sẽ làm giảm dư địa chịu tổn thất.'
                elif kind == 'INSURANCE':
                    text += 'Diễn biến phí phản ánh quy mô khai thác, trong khi hiệu quả tín nhiệm còn phụ thuộc chi phí bồi thường, hoa hồng và chất lượng tái bảo hiểm. Tăng phí chỉ cải thiện khả năng tích lũy vốn khi biên nghiệp vụ được duy trì.'
                else:
                    text += 'Diễn biến doanh thu thể hiện thay đổi quy mô hoạt động; mức đóng góp vào khả năng trả nợ phụ thuộc biên lợi nhuận và lượng tiền thực thu sau nhu cầu vốn lưu động.'
                result.append(text)
    return result
