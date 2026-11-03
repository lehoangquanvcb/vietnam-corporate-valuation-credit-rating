V8.134.0-OFFICIAL-BANK-CAR

SỬA NGUỒN CAR, KHÔNG KẾT LUẬN NGÂN HÀNG CHƯA CÔNG BỐ

Bản này tích hợp số CAR đã đối chiếu vào luồng chung của mọi mã BANK. Hiện bổ sung được 12/28 mã tại 30/6/2026; danh sách chi tiết nằm trong docs/BANK_CAR_DISCLOSURES_V8_134.md. Không tuyên bố đã đủ CAR mọi ngân hàng.

ABB: CAR 12,72%, cấu phần Vốn và lợi nhuận Phù Hợp, bậc tự động A- theo giả định. TCB giữ AA+ từ bảng chấm đã lưu.

CÀI BẢN CẬP NHẬT

Giải nén ZIP, chép app.py, VERSION.txt và các thư mục scripts, data, config, assets, tests, docs trực tiếp vào E:\Valuation_and_Credit_Rating_Intelligence. Đây là bản vá tích lũy, không phải toàn bộ project.

Giữ lại hồ sơ thẩm định và dữ liệu nhập tay của bạn: gói không ghi đè config/bank_rating_assessments.json hoặc config/insurance_metric_inputs.csv.

Trong CMD chạy:

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_bank_car.py --period 2026-Q2
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py --tickers ABB TCB SSI ABI HPG

check_bank_car phải cho Available 12, BankCount 28, Result PARTIAL ở dữ liệu của gói này. Đây là thống kê thiếu nguồn trong app, không phải lỗi thực thi hoặc khẳng định ngân hàng chưa công bố.

UP LÊN GIT

git status --short
git add -f --pathspec-from-file=GIT_FILES_V8_134.txt
git diff --cached --stat
git commit -m "Fix official bank CAR ingestion V8.134.0"
git pull --rebase origin main
git push origin main
git log -1 --oneline
git status

Chỉ tiếp tục push sau khi commit và pull thành công. Nếu Git báo xung đột, dừng ở bước đó và giữ nguyên thông báo để xử lý. Không dùng git reset --hard.

Sau khi Cloud cập nhật, kiểm tra sidebar hiển thị V8.134.0-OFFICIAL-BANK-CAR, mở ABB và xác nhận CAR 12,72%, ICR A-. Nếu đang có đánh giá riêng đã lưu, bậc sẽ ưu tiên hồ sơ đó. Bấm Chuẩn bị báo cáo Word để tạo tệp mới.

Nếu vẫn là bản cũ, vào Manage app > Reboot app. Nhãn phiên bản là thông tin kiểm tra, không phải lệnh CMD.
