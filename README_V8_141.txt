V8.141.0-COMPACT-PUBLIC-REPORTS
Phát hành: 05/11/2026

1. CÀI ĐẶT
Đây là gói cập nhật cho dự án V8.140 đang có dữ liệu tài chính.
Giải nén NỘI DUNG ZIP trực tiếp vào:
E:\Valuation_and_Credit_Rating_Intelligence
Chấp nhận thay thế các file trùng tên. app.py phải nằm ngay tại thư mục trên.
Không tạo thư mục UPDATE và không xóa dữ liệu hiện có.

2. ÁP DỤNG CHUNG CHO BỐN NGÀNH
- Bìa được thu gọn thành khối tiêu đề đầu báo cáo, nối tiếp kết quả xếp hạng.
- Bỏ ngắt trang cưỡng bức. Bảng lịch sử được phép tiếp sang trang sau, lặp tiêu đề.
- Lịch sử BCTC 5 năm là mục con của Thông tin tổng quan, trước rủi ro vĩ mô/ngành.
- Điểm mạnh/điểm yếu có số quý, vị thế peer và diễn biến năm. Thâm hụt tiền sau đầu tư được giữ trong rủi ro dù tỷ số tương đối tốt hơn peer.
- Mỗi chỉ tiêu có biểu đồ năm phía trên và biểu đồ peer quý phía dưới; bỏ bảng lặp giữa hai biểu đồ. Chỉ tiêu không có dữ liệu không được dựng số giả.
- Nội dung vĩ mô/ngành mở rộng, có nguồn bấm được, ngày công bố và ngày truy cập. Nhận định tác động tín nhiệm tách khỏi sự kiện nguồn.
- Định tuyến nội dung cho BANK, SECURITIES, INSURANCE và các nhóm ngành CORPORATE.
- Word và PDF cùng dùng bộ dựng báo cáo này. Kết quả xếp hạng, phương pháp và dữ liệu CAR không đổi.

3. HỒ SƠ DOANH NGHIỆP VÀ NGUỒN PUBLIC
- Hồ sơ biên tập từ trang doanh nghiệp được ưu tiên; đã bổ sung OCB, SSI, ABI, HPG.
- Mã khác tự lấy hồ sơ công khai KBS khi xuất báo cáo, kiểm tra đúng mã và lưu đệm 30 ngày. Không tải hồ sơ hàng loạt lúc mở app.
- Gói có một tập hồ sơ đã lưu sẵn; không có nghĩa mọi mã đã được nghiên cứu thủ công. Số lượng cụ thể trong docs/public_profile_coverage_v8_141.json.
- Nguồn mạng có timeout; nếu không tải được thì dùng hồ sơ cũ hoặc báo thiếu, không bịa thông tin và không chặn các phần tài chính.
- Có thể chủ động lưu thêm bằng lệnh: python scripts\refresh_public_profiles.py --tickers TCB VCB FPT
- Không cần Excel CAR mới, API key mới hoặc cài thêm vnstock để dùng bản sửa này.
- Bộ bối cảnh được nghiên cứu ngày 05/11/2026; không tự tuyên bố là tin mới của các ngày xuất sau. Nguồn và phạm vi từng đoạn được ghi trong báo cáo.

4. KIỂM TRA VÀ UP GIT
Nhập TỪNG DÒNG RIÊNG trong CMD, chờ lệnh xong rồi nhập dòng tiếp theo.

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_layout.py --tickers OCB SSI ABI HPG
git add -f --pathspec-from-file=GIT_FILES_V8_141.txt
git --no-pager diff --cached --stat
git commit -m "V8.141 compact reports and public issuer context"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Kết quả phiên bản cần thấy (không nhập dòng này như lệnh):
BUILD_TAG='V8.141.0-COMPACT-PUBLIC-REPORTS'

Nếu git pull báo CONFLICT, dừng trước khi push để xử lý xung đột.
Sau khi Streamlit nhận bản mới, mở lại app và bấm Chuẩn bị báo cáo Word/PDF để xuất lại.
File Word cũ đã tải xuống sẽ không tự thay đổi.

5. KIỂM CHỨNG
Đã kiểm tra định tuyến nội dung trên toàn bộ danh mục 1.754 mã, không phải xuất và thẩm định 1.754 báo cáo.
Đã xuất Word thực tế OCB, SSI, ABI, HPG và soát trang qua LibreOffice.
Đã kiểm tra API xuất PDF và các bài kiểm thử định dạng, dữ liệu thiếu, ngày xuất, tính điểm hiện có.
Chi tiết kết quả cuối cùng: docs/report_validation_v8_141.json.
Dữ liệu raw từ project gốc đã được phục hồi chỉ để kiểm thử trong môi trường sửa; gói cập nhật này không ghi đè bộ BCTC của bạn.
