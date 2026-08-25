# Cấu trúc V8.10

## Thư mục nghiệp vụ
- `.streamlit/`: cấu hình Streamlit
- `config/`: universe, methodology router, sector config
- `data/`: dữ liệu ACTUAL/model outputs cho Streamlit
- `reports/`: báo cáo xuất ra
- `scripts/`: toàn bộ engine Python
- `tools/legacy_operations/`: BAT cũ được bảo lưu, không còn hiển thị ở root

## File vận hành
- `CONTROL_CENTER.bat`
- `START_LOCAL_APP.bat`
- `SETUP_LOCAL_ENV.bat`
- `RUN_FAST.bat`
- `RUN_REFRESH_ONE_COMPANY.bat`
- `RUN_FULL_REFRESH.bat`
- `RUN_REPORT.bat`

## Nguyên tắc
Streamlit Cloud chỉ đọc dữ liệu/model outputs trong repo.
Vnstock chạy LOCAL.
