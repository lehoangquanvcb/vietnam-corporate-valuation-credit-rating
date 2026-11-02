"""Điểm vào xuất Word dùng chung; PDF chuyển đổi từ chính kết quả này."""
def generate_docx(ticker, report_type="analysis", rating_result=None, mna=None):
    from scripts.professional_report import generate_docx as render
    return render(ticker, report_type, rating_result, mna)
