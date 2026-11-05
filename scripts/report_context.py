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


def safe_url(value):
    text = str(value or '').strip()
    parsed = urlparse(text)
    return text if parsed.scheme in {'https','http'} and parsed.netloc else ''


def research_sections(pack, when):
    """Chỉ dùng bộ hồ sơ đã tồn tại tại ngày xuất; lọc đúng ngành/mã."""
    catalog = json.loads(CONTEXT_FILE.read_text(encoding='utf-8'))
    if date.fromisoformat(catalog['ResearchedOn']) > when: return []
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
            analysis = row.get('Analysis', '')
            if isinstance(analysis, dict): analysis = analysis.get(kind, analysis.get('DEFAULT', ''))
            blocks.append({'Title':row['Title'], 'Fact':row.get('Fact', source.get('Fact','')),
                           'Analysis':analysis, 'Source':source})
        result.append((heading, blocks))
    return result


def issuer_context(pack, when):
    from scripts.company_profile import load_company_profile
    from scripts.public_company_profile import fetch_public_profile, public_profile_paragraphs
    curated = load_company_profile(pack['Ticker']) or {}
    name = str(pack['Meta'].get('DisplayName') or pack['Meta'].get('CompanyName') or pack['Ticker'])
    # Hồ sơ được biên tập từ trang doanh nghiệp có ưu tiên cao hơn bản tóm tắt KBS.
    curated_date = curated.get('LastUpdated') or curated.get('SourceDate') or ''
    if curated and (not curated_date or curated_date[:10] <= when.isoformat()):
        paragraphs = [curated[k].strip().rstrip('.')+'.' for k in
                      ('Overview','CoreBusinesses','MarketPosition','Strategy') if curated.get(k)]
        if paragraphs:
            return paragraphs, {'Name':curated.get('SourceName','Doanh nghiệp công bố'),
                'URL':safe_url(curated.get('SourceURL')), 'PublishedOn':curated.get('SourceDate',''),
                'AccessedOn':curated.get('LastUpdated','')}
    profile = fetch_public_profile(pack['Ticker'], as_of=when)
    if profile:
        return public_profile_paragraphs(profile, name), {'Name':profile['SourceName'],
            'URL':profile['SourceURL'], 'PublishedOn':profile.get('SourceDate',''),
            'AccessedOn':profile['RetrievedOn']}
    # Chỉ nêu dữ kiện trong danh mục; không dựng mô hình kinh doanh từ tên mã.
    exchange = pack['Meta'].get('Exchange')
    text = name + ' (' + pack['Ticker'] + ')'
    if exchange: text += ', đăng ký giao dịch/niêm yết tại ' + str(exchange)
    return [text+'.', 'Chưa lấy được hồ sơ hoạt động từ nguồn công khai tại lần xuất này.'], None
