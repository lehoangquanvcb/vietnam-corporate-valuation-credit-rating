V8.139.0-BANK-EVIDENCE-CAR
Phát hành: 03/11/2026

1. GIẢI NÉN
Giải nén đè trực tiếp các tệp và thư mục trong ZIP vào:
E:\Valuation_and_Credit_Rating_Intelligence
app.py trong ZIP phải thay đúng app.py ở thư mục này. Không đặt vào thư mục UPDATE.
Đây là gói cập nhật cộng dồn; dùng cùng dữ liệu tài chính hiện có của project.

2. THAY ĐỔI
- Bỏ hoàn toàn bước hiệu chỉnh ICR theo mức đích từng mã.
- Chấm ba cấu phần ngân hàng từ nhiều chỉ tiêu và lịch sử 5 năm, giữ quyền ưu tiên đánh giá nhập riêng đúng kỳ.
- 130/140 điểm CAR cuối năm 2021–2025; 25/28 ngân hàng đủ 5 năm.
- 24 ngân hàng có CAR quý 2/2026: 22 nguồn đã đối chiếu, MBB/MSB dùng đầu vào người dùng có nhãn riêng.
- CAR peer lấy toàn ngành có số đúng kỳ; bình quân chỉ gộp cùng phạm vi và TT41/TT14.
- Giữ báo cáo tông xanh, lịch sử năm, hai biểu đồ trên/dưới, tên tệp ngày xuất và tab xếp hạng mặc định.

Chưa đủ chuỗi năm: NVB 2021–2025, PCB 2021–2023, VBB 2022/2024.
Chưa đủ nguồn quý 2/2026: NVB, PCB, TPB, VBB. Không gán số năm trước thành số quý.
Các quy tắc tự động hóa và giả định được nêu trong docs/BANK_EVIDENCE_CAR_V8_139.md.

3. KIỂM TRA VÀ UP GIT
Chạy từng dòng riêng trong CMD:

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py --tickers VCB TCB HDB OCB ABB SSI ABI HPG
git add -f --pathspec-from-file=GIT_FILES_V8_139.txt
git diff --cached --stat
git commit -m "Remove bank rating calibration and expand CAR history"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Kết quả kiểm tra phiên bản cuối phải là:
BUILD_TAG='V8.139.0-BANK-EVIDENCE-CAR'

Nếu git pull báo xung đột, xử lý xung đột trước khi push; không chạy git reset --hard.
Sau khi push thành công, chờ Streamlit triển khai và kiểm tra phiên bản ở sidebar.
Gói này không tự push GitHub hoặc reboot Streamlit thay bạn.

4. TỆP ĐỐI CHIẾU
data/bank_car_disclosures.csv: CAR đã đối chiếu với URL và trang nguồn.
data/bank_car_user_inputs.csv: số do người dùng cung cấp, giữ riêng với nguồn xác minh.
docs/bank_validation_v8_139.json: kiểm tra đủ 28 ngân hàng và độ phủ CAR.
docs/validation_v8_139.json: kết quả bộ kiểm thử thực thi.
docs/ui_validation_v8_139.json: kiểm tra app trên các mã đại diện.
