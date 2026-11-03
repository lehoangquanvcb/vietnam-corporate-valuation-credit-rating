BẢN CẬP NHẬT V8.133.0 — KẾT QUẢ TỪNG CẤU PHẦN XẾP HẠNG

1. GIẢI NÉN
Giải nén toàn bộ nội dung gói cập nhật trực tiếp vào:
E:\Valuation_and_Credit_Rating_Intelligence
Đồng ý ghi đè. app.py nằm ngay tại thư mục này, không đặt trong UPDATE.
Đây là gói tích lũy cho project hiện có, bao gồm các thay đổi V8.131 và V8.132.

2. NỘI DUNG SỬA
- Mặc định hiển thị kết quả tự động hoặc kết quả từ bảng chấm đã lưu.
- Phiếu nhập tay của cả bốn nhóm ngành chỉ mở khi bật "Nhập hoặc điều chỉnh đánh giá riêng".
- Với ngân hàng và chứng khoán, thiếu một cấu phần không còn làm bộ tính dừng trước những cấu phần khác.
- Bảng điểm giữ lại các cấu phần tính được, ghi rõ chỉ tiêu/kỳ còn thiếu; không gán 0 điểm cho phần thiếu.
- Bảng điểm tự động hiển thị trước phần phân tích chỉ tiêu, đồng thời được chuyển vào báo cáo Word.
- Khi không đủ cấu phần, không tổng hợp SACP/ICR; không dùng CAR quý cũ thay cho quý hiện tại.
- Giữ bảng chấm đã lưu và notch đã nhập; phần hỗ trợ giả định 0 bậc vẫn ghi rõ là giả định.
- Triển vọng chưa được đánh giá không bị tự gán "Ổn định".
- Giữ tab Xếp hạng mặc định, biểu đồ 5 năm, màu xanh lá, tên Word, bìa/header/footer của các bản trước.

Ví dụ ABB trong nguồn dữ liệu hiện có: hồ sơ kinh doanh Phù Hợp; vị thế rủi ro Mạnh;
huy động vốn Trung Bình; thanh khoản Phù Hợp. Đây là tín hiệu tự động theo mô hình đang dùng,
không phải kết luận thẩm định đã phê duyệt. Vốn/lợi nhuận thiếu CAR hợp lệ tại 2026-Q2 nên
chưa tổng hợp bậc cuối cùng. CAR 9,87% tại 2025-Q2 không được mang sang kỳ 2026-Q2.

3. UP GIT
Mở CMD, chạy từng dòng sau khi giải nén:

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
git add -f --pathspec-from-file=GIT_FILES_V8_133.txt
git --no-pager diff --cached --stat
git commit -m "V8.133.0 preserve partial factor scores and clarify automatic assessment"
git pull --rebase origin main
git push origin main
git --no-pager log -1 --oneline
git --no-pager status --short --branch

BUILD_TAG phải là V8.133.0-AUTO-FACTOR-STATUS. Không gõ riêng chuỗi phiên bản như một lệnh.
Nếu đang trong màn hình less/help của Git, nhấn q để quay lại dấu nhắc CMD.

4. KIỂM TRA APP
Sau khi Streamlit nạp commit mới, kiểm tra phiên bản V8.133.0-AUTO-FACTOR-STATUS.
Tải lại trang, chọn ABB, xem bảng "Kết quả từng cấu phần xếp hạng".
Không cần mở phiếu nhập riêng để nhận kết quả tự động.
Nếu có kết luận thẩm định riêng, bật tùy chọn rồi nhập cấu phần tương ứng.
Bỏ chọn tùy chọn sẽ trở về kết quả tự động / bảng chấm đã lưu trên đĩa.
Muốn xuất Word mới, bấm "Chuẩn bị báo cáo Word" rồi tải xuống.

Kiểm tra máy tính tại project (chỉ đọc số liệu):
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py --tickers ABB TCB SSI ABI HPG BVH

Chạy local:
"C:\Users\HP\.venv\Scripts\python.exe" -m streamlit run app.py

PASS của công cụ là kết quả kiểm tra phần mềm, không phải xác nhận đủ dữ liệu hoặc bậc xếp hạng cho mọi mã.
