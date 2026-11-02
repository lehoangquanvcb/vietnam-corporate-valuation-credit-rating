"""One export date for the document, download name and Streamlit cache."""
from datetime import date, datetime, timedelta, timezone
import re

VIETNAM = timezone(timedelta(hours=7))
NOTICE = ('Tài liệu này chỉ phục vụ mục đích nghiên cứu không có giá trị thay thế '
          'Báo cáo xếp hạng tín nhiệm thông thường')


def export_date(value=None):
    if value is None:
        return datetime.now(VIETNAM).date()
    if isinstance(value, datetime):
        return value.astimezone(VIETNAM).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def report_filename(ticker, report_type='rating', when=None, extension='docx'):
    ticker = str(ticker).strip().upper()
    if not re.fullmatch(r'[A-Z0-9._-]+', ticker):
        raise ValueError('Mã doanh nghiệp không hợp lệ')
    if extension not in {'docx', 'pdf'}:
        raise ValueError('Định dạng báo cáo không hợp lệ')
    prefix = 'Báo cáo XHTN không chỉ định' if report_type == 'rating' else 'Báo cáo phân tích định giá và M&A'
    return f'{prefix} {ticker} {export_date(when):%d-%m-%Y}.{extension}'


def report_header(ticker, when=None, report_type='rating'):
    title = ('Báo cáo xếp hạng tín nhiệm không chỉ định' if report_type == 'rating'
             else 'Báo cáo phân tích định giá và M&A')
    return f'{ticker} - {title} - ban hành ngày {export_date(when):%d/%m/%Y}'
