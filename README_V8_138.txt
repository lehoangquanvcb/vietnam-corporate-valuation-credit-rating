BẢN CẬP NHẬT V8.138.0-BANK-FUNDING-REPORT

Giải nén TOÀN BỘ nội dung ZIP trực tiếp vào:
E:\Valuation_and_Credit_Rating_Intelligence
Chọn thay thế tệp trùng tên. app.py phải nằm ngay trong thư mục project, KHÔNG để trong thư mục UPDATE.

Đã sửa:
- Bỏ suy luận thanh khoản Yếu chỉ từ cho vay/tiền gửi BCTC > 1,2 lần cho mọi ngân hàng.
- TCB kỳ 2026-Q2: Huy động Mạnh / Thanh khoản Mạnh theo đánh giá được người dùng xác nhận, +1 bậc; SACP A; ICR AA- theo khung hiệu chỉnh đã chọn (+2 bậc).
- Đối chiếu riêng LDR công bố TCB 80,1%, vốn ngắn hạn cho vay trung dài hạn 27,8%; phân tích chi phí vốn tăng từ 4,2% lên 4,8%.
- App và Word dùng cùng bố cục bốn cấu phần, lập luận tài chính, bảng điểm gọn và phụ lục kỹ thuật. Giữ biểu đồ năm 5 năm với line peer và biểu đồ quý đặt dưới.
- Khi chưa có đánh giá thanh khoản riêng, kết quả ước tính ghi rõ giả định trung tính. Không coi giả định là kết luận thẩm định. Phiếu nhập riêng luôn ưu tiên.

MỞ CMD VÀ CHẠY TỪNG DÒNG, chỉ chuyển bước khi dòng trước thành công:

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_bank_funding.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py --tickers TCB VCB ABB OCB STB SSI ABI HPG

git add -f --pathspec-from-file=GIT_FILES_V8_138.txt
git --no-pager diff --cached --stat
git commit -m "Fix bank funding analysis and report format V8.138.0"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Dòng kiểm tra phải hiện: BUILD_TAG='V8.138.0-BANK-FUNDING-REPORT'
Không gõ nối hai lệnh. Nếu rebase báo xung đột, dừng và gửi nguyên thông báo.

Trên Streamlit Cloud, chờ cập nhật hoặc Manage app > Reboot app. Kiểm tra sidebar đúng phiên bản, chọn TCB rồi Chuẩn bị báo cáo Word để tạo file mới.

Chi tiết căn cứ: docs/BANK_FUNDING_V8_138.md.
Các kiểm tra PASS là kiểm tra phần mềm, không xác nhận độc lập mức tín nhiệm. Gói đã được kiểm tra trong môi trường thử nghiệm, chưa tự push GitHub hoặc triển khai Streamlit Cloud của bạn.
