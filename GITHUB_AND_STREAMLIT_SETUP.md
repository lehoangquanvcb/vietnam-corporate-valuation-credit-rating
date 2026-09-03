# Tạo repo GitHub mới và app Streamlit mới

## A. GitHub mới

Tên repo khuyến nghị:

`Vietnam_Corporate_Valuation_MA_Credit_Rating_Intelligence`

### Cách nhanh nếu máy đã có GitHub CLI (`gh`)

Double-click:

`CREATE_GITHUB_REPO.bat`

Script sẽ khởi tạo Git local, commit lần đầu, tạo repo GitHub public và push `main`.

### Cách thủ công

1. Trên GitHub → New repository → tạo repo **rỗng** với tên trên. Không thêm README/.gitignore/license từ GitHub.
2. Trong thư mục project chạy `INIT_NEW_GITHUB_REPO.bat`.
3. Sau đó chạy:

```bat
git remote add origin https://github.com/<USERNAME>/Vietnam_Corporate_Valuation_MA_Credit_Rating_Intelligence.git
git push -u origin main
```

## B. Streamlit app mới

Vào `https://share.streamlit.io/` → Create app / Deploy an app.

- Repository: `<USERNAME>/Vietnam_Corporate_Valuation_MA_Credit_Rating_Intelligence`
- Branch: `main`
- Main file path: `app.py`
- Python version: **3.12**
- App URL đề xuất: `vietnam-corporate-valuation-ma-credit-rating`

Không sử dụng repo/app ngân hàng V7.x cũ. Đây là project riêng.

## C. Lần chạy đầu

1. `SETUP_LOCAL_ENV.bat`
2. `RUN_DISCOVER_ALL_LISTED.bat` để thử cập nhật universe toàn thị trường từ listing của phiên bản vnstock đang cài.
3. `RUN_REFRESH_ONE_COMPANY.bat` và nhập `SSI` hoặc `HPG` để kiểm thử data pipeline ngoài ngân hàng.
4. `RUN_FAST.bat` để validate + push GitHub.
5. Streamlit Cloud tự redeploy.

## D. Kiến trúc Bronze

Vnstock chỉ chạy ở PC/local environment. Không cài và không gọi vnstock_data trên Streamlit Cloud. Cloud chỉ đọc CSV đã được commit lên GitHub.

## Vnstock Sponsor Bronze credential

- Chạy `SETUP_VNSTOCK_BRONZE.bat` trên máy local để tạo `.env` và thiết lập `VNSTOCK_API_KEY`.
- Không commit `.env` hoặc API Key lên GitHub.
- Streamlit Cloud chỉ đọc CSV đã push; không cần Sponsor credential.
- Kiểm tra trước bằng `RUN_DIAGNOSE_VNSTOCK.bat`.
