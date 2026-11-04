V8.140.0-RATING-HEADER
Phát hành: 04/11/2026

1. CÀI ĐẶT
Đây là bản cập nhật giao diện dành cho dự án đã có V8.139.
Giải nén đè nội dung ZIP trực tiếp vào:
E:\Valuation_and_Credit_Rating_Intelligence
app.py phải nằm ngay trong thư mục trên. Không tạo thư mục UPDATE.

2. THAY ĐỔI
- Trong tab BÁO CÁO XẾP HẠNG TÍN NHIỆM, bỏ các ô Giá thị trường và P/B ở đầu trang.
- Thêm ô Mức Xếp hạng tín nhiệm không chỉ định, hiển thị bậc ICR cuối cùng màu xanh lá.
- Dùng cùng kết quả với bảng chấm và báo cáo xuất ra, sau các đánh giá nhập riêng của phiên hiện tại.
- Áp dụng chung cho ngân hàng, chứng khoán, bảo hiểm và doanh nghiệp phi tài chính.
- Các chỉ tiêu tài chính còn lại vẫn hiển thị. Các tab khác giữ phần giá/định giá.
- Nếu chưa xác định được ICR, giữ trạng thái thiếu căn cứ/không áp dụng; không lấy Anchor hoặc SCA thay cho bậc cuối cùng.
- Không thay công thức chấm điểm, dữ liệu CAR hoặc phương pháp V8.139.

3. KIỂM TRA VÀ UP GIT
Chạy từng dòng riêng trong CMD. Chờ xong một lệnh mới nhập lệnh tiếp theo.

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py --tickers MSB TCB SSI ABI HPG
git add -f --pathspec-from-file=GIT_FILES_V8_140.txt
git --no-pager diff --cached --stat
git commit -m "V8.140 show final credit rating in report header"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Kết quả phiên bản mong đợi (không gõ dòng này như một lệnh):
BUILD_TAG='V8.140.0-RATING-HEADER'

Nếu kiểm tra Python báo lỗi hoặc git pull báo CONFLICT, dừng và xử lý trước khi push.
Gói này không tự push GitHub hoặc triển khai Streamlit.

4. KIỂM THỬ
Đã chạy kiểm tra cú pháp Python và 20 tình huống Streamlit AppTest sử dụng chính mã phần đầu trang/điều hướng, với đầu vào xếp hạng kiểm thử.
Đã kiểm tra: bốn nhóm ngành; đổi mã; đánh giá nhập riêng; chuyển cả bốn tab; thiếu ICR; ngoài phạm vi; cùng kết quả ở đầu trang, phần báo cáo và đầu vào xuất file.
Các bậc trong tệp kiểm thử là dữ liệu giả lập để kiểm tra giao diện, không phải kết quả xếp hạng mới của doanh nghiệp.
Không chạy lại toàn bộ bộ kiểm thử tài chính V8.139. Các tệp tính xếp hạng và dữ liệu CAR không đổi.
Chi tiết: docs/header_validation_v8_140.json.
