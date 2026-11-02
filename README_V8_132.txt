BẢN CẬP NHẬT V8.132.0 — TAB XẾP HẠNG MẶC ĐỊNH VÀ BIỂU ĐỒ TÀI CHÍNH

1. GIẢI NÉN
Giải nén toàn bộ nội dung gói cập nhật trực tiếp vào:
E:\Valuation_and_Credit_Rating_Intelligence
Đồng ý ghi đè. app.py nằm ngay trong thư mục này, không đặt trong UPDATE.
Đây là gói cập nhật tích lũy cho project hiện có, đã bao gồm các thay đổi V8.131.

2. NỘI DUNG SỬA
- Báo cáo Xếp hạng tín nhiệm là tab đầu tiên và mở mặc định.
- Sau khi người dùng chọn tab khác, các lần cập nhật giao diện vẫn giữ tab đã chọn.
- Sửa trục thời gian thành các nhãn năm nguyên: 2021, 2022, 2023, 2024, 2025.
- Không vẽ khung biểu đồ khi toàn bộ điểm không hợp lệ hoặc thiếu.
- Bỏ các đoạn nhận định chung không có số liệu đi kèm ở khối chỉ tiêu trống.
- Màu doanh nghiệp xanh lá, đường bình quân peer màu cam nét đứt.
- Áp dụng kiểm tra biểu đồ trống và nhãn năm cho cả bốn nhóm ngành.
- Giữ tên Word, bìa, header, footer và cơ chế chấm điểm của V8.131.

CAR của ABB: nguồn trong project hiện có mốc 9,87% tại 2025-Q2; các mốc cuối năm và 2026-Q2 trả 0, được coi là thiếu. Giao diện hiển thị rõ mốc công bố thực có. Bản sửa này không bổ sung chuỗi CAR cuối năm, không mang số quý cũ sang cuối năm hoặc quý hiện tại.

3. KIỂM TRA FILE VÀ UP GIT
Mở CMD, chạy từng dòng:

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
git add -f --pathspec-from-file=GIT_FILES_V8_132.txt
git --no-pager diff --cached --stat
git commit -m "V8.132.0 default rating tab and fix empty financial charts"
git pull --rebase origin main
git push origin main
git --no-pager log -1 --oneline
git --no-pager status --short --branch

BUILD_TAG phải là V8.132.0-RATING-FIRST-CHARTS. Đây không phải lệnh để gõ riêng.
Nếu đang ở màn hình less/help của Git, nhấn q đến khi quay lại dấu nhắc E:\...> trước khi gõ lệnh.

4. STREAMLIT
Sau khi ứng dụng nạp commit mới, kiểm tra dòng phiên bản V8.132.0-RATING-FIRST-CHARTS.
Tải lại trang. Tab Báo cáo Xếp hạng tín nhiệm sẽ ở đầu và được chọn.
Chọn ABB: không còn khung CAR trống hoặc các mốc năm 2021,5.
Muốn tải Word mới, bấm Chuẩn bị báo cáo Word rồi tải xuống.

Nếu chạy local:
"C:\Users\HP\.venv\Scripts\python.exe" -m streamlit run app.py
