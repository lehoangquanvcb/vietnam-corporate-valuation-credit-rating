BẢN CẬP NHẬT V8.130.0 — BÁO CÁO THỐNG NHẤT BỐN LĨNH VỰC

1. GIẢI NÉN
Giải nén nội dung ZIP trực tiếp vào:
E:\Valuation_and_Credit_Rating_Intelligence

app.py, VERSION.txt, scripts, config, data, assets, docs và tests phải nằm trong thư mục project hiện tại. Đồng ý ghi đè các file trong gói. Không đặt trong UPDATE hoặc thêm một thư mục project lồng bên trong.
Đây là gói cập nhật tích lũy cho project hiện có, không phải bộ cài độc lập. Giữ nguyên dữ liệu, môi trường Python và các file nhập đánh giá riêng của bạn.

2. KIỂM TRA
Mở CMD, chạy lần lượt:

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_runtime.py

BUILD_TAG phải là V8.130.0-UNIFIED-REPORTS. Đây là tên phiên bản, không phải lệnh để gõ riêng.
Kiểm tra mặc định chạy TCB, SSI, FPT, ABI, BVH và xác nhận toàn bộ danh mục có mẫu phương pháp. PASS xác nhận kiểm tra phần mềm, không phải xác nhận mọi mã đã đủ hồ sơ để có bậc xếp hạng.

3. ĐƯA LÊN GIT
Chạy từng lệnh trong cùng cửa sổ CMD:

git add -f --pathspec-from-file=GIT_FILES_V8_130.txt
git diff --cached --stat
git commit -m "V8.130.0 unify four-sector credit rating reports"
git pull --rebase origin main
git push origin main
git status

Danh sách GIT_FILES_V8_130.txt chỉ gồm file của bản cập nhật. Các file backup và thư mục không được theo dõi khác không cần thêm vào commit này.
Nếu Git báo xung đột khi rebase, xử lý xung đột trước khi push; không dùng force push.

4. STREAMLIT
Đợi ứng dụng nạp commit mới. Thanh bên phải hiển thị V8.130.0-UNIFIED-REPORTS.
Vào phần báo cáo xếp hạng, tạo lại báo cáo Word rồi tải file mới. File Word cũ đã tải về không tự đổi nội dung.
Nếu chạy local:
"C:\Users\HP\.venv\Scripts\python.exe" -m streamlit run app.py

5. THAY ĐỔI
- Mẫu xanh lá thống nhất cho mọi mã, chọn cấu trúc theo bốn phương pháp.
- Lịch sử và biểu đồ trên dùng năm tài chính hoàn chỉnh, năm gần nhất và bốn năm trước; có bình quân peer từng năm khi đủ số liệu tương thích.
- Biểu đồ dưới so sánh doanh nghiệp và peer tại quý gần nhất; hai biểu đồ xếp dọc.
- Phân tích biến động, vị thế tương đối và tác động tài chính từ các chỉ tiêu liên quan.
- Áp dụng đúng ba cụm từ mới về tên báo cáo và mục đích nghiên cứu.
- Giữ bậc xếp hạng có căn cứ; không gán bậc giả cho hồ sơ thiếu đánh giá.

Không ghi đè file nhập tay insurance_metric_inputs.csv hoặc bank_rating_assessments.json. Gói có các thành phần tích lũy từ V8.119–V8.129 để tránh thiếu module nếu bỏ qua một bản cập nhật.
Chi tiết và phạm vi kiểm chứng: docs\UNIFIED_REPORTS_V8_130.md.
