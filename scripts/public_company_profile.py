"""Hồ sơ công khai theo mã, tải khi xuất báo cáo và lưu đệm; không chấm điểm.

Endpoint KBS được công bố trong vnstock/explorer/kbs/company.py. Chỉ đọc
các trường hồ sơ, không lấy danh sách cá nhân/cổ đông hoặc thay số BCTC.
"""
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
import json
import os
import re
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / 'data' / 'public_profiles'
ENDPOINT = 'https://kbbuddywts.kbsec.com.vn/iis-server/investment/stockinfo/profile/{ticker}?l=1'
MAX_BYTES = 2_000_000
_attempts = {}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}: self.hidden += 1
        if tag in {'br', 'li', 'p', 'div'}: self.parts.append(' ')
    def handle_endtag(self, tag):
        if tag in {'script', 'style'}: self.hidden = max(0, self.hidden - 1)
        if tag in {'li', 'p', 'div'}: self.parts.append(' ')
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


def clean_text(value):
    parser = _Text(); parser.feed(str(value or '')[:200_000])
    return re.sub(r'\s+', ' ', ''.join(parser.parts)).strip(' -•\t\r\n')


def _calendar(value):
    try: return datetime.strptime(str(value), '%d/%m/%Y').strftime('%d/%m/%Y')
    except (TypeError, ValueError): return ''


def _read(ticker, folder, as_of):
    try:
        row = json.loads((folder / (ticker + '.json')).read_text(encoding='utf-8'))
        if row.get('Ticker') != ticker: return None
        if date.fromisoformat(row['RetrievedOn']) > as_of: return None
        return row
    except (OSError, ValueError, KeyError, TypeError): return None


def _write(row, folder):
    # Ghi nguyên tử: hai phiên xuất cùng mã không đọc phải JSON đang ghi dở.
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=folder, delete=False, suffix='.tmp') as f:
        json.dump(row, f, ensure_ascii=False, indent=2); name = f.name
    try: os.replace(name, folder / (row['Ticker'] + '.json'))
    finally:
        if os.path.exists(name): os.unlink(name)


def fetch_public_profile(ticker, *, cache_dir=None, allow_network=True, timeout=5, as_of=None, force=False):
    """Một request có timeout; lỗi nguồn giữ hồ sơ cũ, không treo xuất báo cáo.

    Cache có hạn 30 ngày. Ngày thu thập không được gán thành ngày công bố.
    Bản xuất lùi ngày không dùng hồ sơ thu thập sau ngày xuất.
    """
    ticker = str(ticker or '').strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{2,12}', ticker): return None
    folder = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    today = datetime.now(timezone.utc).date()
    when = date.fromisoformat(str(as_of)) if as_of else today
    old = _read(ticker, folder, when)
    if old and not force and (today-date.fromisoformat(old['RetrievedOn'])).days < 30: return old
    if not allow_network or os.getenv('REPORT_PROFILE_OFFLINE') == '1' or when < today: return old
    key = (str(folder), ticker)
    if not force and time.monotonic() - _attempts.get(key, -1e9) < 600: return old
    _attempts[key] = time.monotonic()
    url = ENDPOINT.format(ticker=ticker)
    try:
        req = Request(url, headers={'Accept':'application/json', 'User-Agent':'ValuationReport/8.141 public-company-profile'})
        with urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES: return old
        data = json.loads(raw)
        if not isinstance(data, dict) or str(data.get('SB', '')).upper() != ticker: return old
        business = clean_text(data.get('SM'))
        founded, listed = _calendar(data.get('FD')), _calendar(data.get('LD'))
        website = str(data.get('URL') or '').strip()
        if urlparse(website).scheme not in {'https','http'}: website = ''
        if not business and not founded and not listed: return old
        # Giữ đoạn trích ngắn, không sao chép toàn bộ hồ sơ hoặc lịch sử của nguồn.
        excerpt = ' '.join(business.split()[:24])
        if len(business.split()) > 24: excerpt += '…'
        row = {'Ticker':ticker, 'Established':founded, 'ListedSince':listed,
               'Exchange':clean_text(data.get('EX')), 'BusinessExcerpt':excerpt,
               'Website':website, 'SourceName':'KBS – hồ sơ doanh nghiệp công khai',
               'SourceURL':url, 'SourceDate':'', 'RetrievedOn':today.isoformat(),
               'LastUpdated':today.isoformat()}
        try: _write(row, folder)
        except OSError: pass  # Filesystem chỉ đọc vẫn xuất được hồ sơ đã tải thành công.
        return row
    except (OSError, ValueError, TypeError, TimeoutError): return old


def public_profile_paragraphs(row, name):
    parts = []
    if row.get('Established'): parts.append('thành lập ngày ' + row['Established'])
    if row.get('ListedSince'):
        parts.append('có ngày bắt đầu giao dịch được nguồn ghi nhận là ' + row['ListedSince'] +
                     (' trên ' + row['Exchange'] if row.get('Exchange') else ''))
    result = [name + ': ' + '; '.join(parts) + '.'] if parts else []
    if row.get('BusinessExcerpt'):
        result.append('Hoạt động theo hồ sơ công khai của KBS (trích): “' + row['BusinessExcerpt'] + '”.')
    if row.get('Website'): result.append('Website doanh nghiệp: ' + row['Website'])
    return result
