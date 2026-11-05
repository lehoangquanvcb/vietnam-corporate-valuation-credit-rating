V8.142.0-CAR-CLEAN-LABELS
Ngày phát hành: 05/11/2026
Áp dụng trên dự án V8.141 đã cập nhật.

THAY ĐỔI
- Biểu đồ CAR trên app và Word/PDF chỉ hiện mã ngân hàng dưới cột.
- Bỏ nhãn TT41, TT14, UNKNOWN, dấu * và ? trên trục mã ngân hàng.
- Bỏ đoạn ghi chú bắt đầu bằng "Nhóm tham chiếu CAR toàn ngành" dưới biểu đồ.
- Thu gọn khoảng cách dưới trục sau khi bỏ dòng nhãn phụ.
- Giữ nguyên giá trị CAR, nhóm so sánh, cách tính bình quân và kết quả xếp hạng.
- Nguồn và cơ sở số liệu vẫn có trong mục "Số CAR và nguồn của từng ngân hàng" và phụ lục nguồn của báo cáo.

CÀI ĐẶT
Giải nén nội dung ZIP trực tiếp vào thư mục project hiện tại, chọn thay thế file:
C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
Không tạo thư mục UPDATE. app.py phải nằm ngay trong thư mục project.

UP GIT (nhập từng lệnh riêng trong CMD)
cd /d C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
findstr /C:"BUILD_TAG=" app.py
git add --pathspec-from-file=GIT_FILES_V8_142.txt
git --no-pager diff --cached --stat
git commit -m "V8.142 simplify CAR chart labels"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Phiên bản cần thấy: V8.142.0-CAR-CLEAN-LABELS
Nếu pull báo CONFLICT, dừng trước khi push để xử lý xung đột.
Sau khi Streamlit nhận bản V8.142, xuất lại Word/PDF. File đã tải trước đó không tự thay đổi.

KIỂM CHỨNG
33 kiểm thử hiện có về biểu đồ và CAR đạt.
Đã kiểm tra nhãn và so sánh giá trị/cột/bình quân trước-sau với OCB, VCB, ABB, MSB.
Chi tiết: docs/car_chart_validation_v8_142.json.
Ảnh mẫu sau sửa: report_examples/V8_142/CAR_OCB_V8_142.png.
