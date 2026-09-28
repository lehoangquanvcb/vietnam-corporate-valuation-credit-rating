from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILE = ROOT / "data" / "company_profile_master.csv"

def load_company_profile(ticker):
    """Return verified public-source profile row for ticker, or None."""
    t = str(ticker or "").upper().strip()
    if not PROFILE_FILE.exists() or not t:
        return None
    try:
        with PROFILE_FILE.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if str(row.get("Ticker","")).upper().strip() == t:
                    return {k:(v or "").strip() for k,v in row.items()}
    except Exception:
        return None
    return None

def profile_overview_text(ticker, fallback_name=None):
    p = load_company_profile(ticker)
    if not p:
        return ("Chưa có hồ sơ doanh nghiệp được xác minh từ nguồn công khai. "
                "Dữ liệu tài chính và thị trường không được sử dụng để tự suy diễn phần Thông tin tổng quan.")
    name = p.get("CompanyName") or fallback_name or str(ticker).upper()
    parts=[]
    if p.get("Overview"): parts.append(p["Overview"])
    if p.get("CoreBusinesses"): parts.append("Hoạt động cốt lõi: " + p["CoreBusinesses"] + ".")
    if p.get("MarketPosition"): parts.append("Vị thế thị trường: " + p["MarketPosition"] + ".")
    if p.get("Strategy"): parts.append("Định hướng: " + p["Strategy"] + ".")
    return " ".join(parts)

def profile_source_text(ticker):
    p=load_company_profile(ticker)
    if not p: return ""
    bits=[]
    if p.get("SourceName"): bits.append(p["SourceName"])
    if p.get("SourceDate"): bits.append("ngày nguồn: "+p["SourceDate"])
    if p.get("LastUpdated"): bits.append("cập nhật hồ sơ: "+p["LastUpdated"])
    return " | ".join(bits)
