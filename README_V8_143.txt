V8.143.0-DOMESTIC-RESEARCH
Nâng cấp nội dung tổng quan, rủi ro vĩ mô và rủi ro ngành
Ngày rà soát nguồn: 05/11/2026

PHẠM VI ĐÃ THỰC HIỆN
- Bộ xuất Word/PDF dùng chung cho ngân hàng, chứng khoán, bảo hiểm và doanh nghiệp phi tài chính.
- Kiểm tra định tuyến đầy đủ 1.754 mã trong danh mục hiện tại.
- Bổ sung 17 nguồn bối cảnh trong nước: cơ quan quản lý, hiệp hội và công bố ngành.
- Mỗi báo cáo có 4 chủ đề vĩ mô và 4 chủ đề ngành; nội dung phân biệt 4 phương pháp và các nhóm ngành phi tài chính.
- Viết lại hồ sơ nghiên cứu riêng của ABB, OCB, SSI, ABI và HPG. Các hồ sơ biên tập sẵn khác vẫn được giữ.
- Mã chưa có hồ sơ nghiên cứu riêng dùng hồ sơ công khai KBS (có lưu đệm) và phần tổng quan tính theo BCTC của chính mã đó. Bỏ trích đoạn bị cắt giữa câu, bỏ dòng website rời rạc trong phần tổng quan.
- Số liệu công bố mới được ghi rõ kỳ; không đưa số chín tháng vào bảng số quý hai hoặc thay đầu vào xếp hạng.
- Nguồn có hyperlink, ngày công bố/ngày truy cập; không sử dụng nguồn tương lai khi xuất lùi ngày.
- Giữ lịch sử tài chính trong phần tổng quan, hai biểu đồ mỗi chỉ tiêu, không có bảng chen giữa; giữ nhãn CAR gọn của V8.142.
- Rút gọn URL và ghi chú CAR lặp ở phụ lục, vẫn giữ đường dẫn báo cáo gốc, trang và cơ sở số liệu.
- Đổi mã lưu đệm khi hồ sơ nghiên cứu thay đổi để tránh tải lại bản Word cũ trong cùng phiên.

GIỚI HẠN CẦN PHÂN BIỆT
1. Kiểm tra định tuyến 1.754 mã không có nghĩa đã nghiên cứu riêng bằng tay hoặc xuất và xem toàn bộ 1.754 báo cáo.
2. Bộ tin vĩ mô/ngành và 5 hồ sơ nghiên cứu mới có mốc rà soát 05/11/2026. App không tự tìm tin mới và viết lại các nhận định này mỗi ngày. Ngày rà soát thực tế được ghi trong báo cáo.
3. Tra cứu KBS khi xuất chủ yếu bổ sung dữ kiện nhận diện doanh nghiệp; không thay thế nghiên cứu hoạt động và quản trị riêng của từng mã.
4. Không thay đổi phương pháp chấm điểm, hệ số CAR, BCTC hay giả định xếp hạng trong bản này.
5. Mẫu ABB minh họa nội dung và bố cục; bậc trong mẫu là kết quả của bộ máy hiện tại, không phải kết quả thẩm định mới.

CÀI ĐẶT TRÊN MÁY MỚI
Thư mục dự án của bạn:
C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main

Gói này nối tiếp V8.142 trên nhánh main (commit nền 800e337).
Giải nén ra thư mục tạm. Chép NỘI DUNG trong ZIP vào thư mục dự án ở trên và chọn Replace các file trùng tên.
app.py phải nằm trực tiếp trong thư mục dự án, không nằm trong một thư mục UPDATE hay thư mục gói ZIP lồng thêm.
Không xóa các thư mục dữ liệu, file cấu hình hoặc môi trường Python có sẵn.
Không cần cài thêm thư viện.

Mẫu Word đi kèm nằm tại report_examples/Bao_cao_XHTN_ABB_05-11-2026.docx.
Danh sách Git chỉ gồm code, dữ liệu nội dung và tài liệu kiểm tra; không tự đưa báo cáo mẫu hay các báo cáo cũ của bạn lên Git.

ĐƯA LÊN GIT (CMD, CHẠY TỪNG DÒNG)
cd /d C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
findstr /C:"BUILD_TAG=" app.py
git status
git add --pathspec-from-file=GIT_FILES_V8_143.txt
git --no-pager diff --cached --stat
git commit -m "V8.143 improve domestic research and report narratives"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Kết quả cuối cần là:
BUILD_TAG='V8.143.0-DOMESTIC-RESEARCH'

Nếu pull báo conflict, dừng trước bước push và xử lý conflict; không dùng push --force.
Sau khi Streamlit triển khai bản mới, tạo lại báo cáo bằng nút Chuẩn bị báo cáo Word/PDF. File đã tải từ bản cũ sẽ không tự thay đổi.

KIỂM TRA ĐÃ CHẠY
94 kiểm thử mục tiêu đạt, bao gồm định tuyến toàn danh mục, nguồn đúng ngày, tổng quan đúng kỳ số liệu và hồi quy biểu đồ/xuất báo cáo.
Các luồng Word ngân hàng, chứng khoán, bảo hiểm và phi tài chính đã được kiểm tra cấu trúc.
Mẫu ABB đầy đủ đã xuất, chuyển PDF và xem tất cả trang để kiểm tra bố cục.
Chi tiết: docs/validation_v8_143.json.

CẬP NHẬT NỘI DUNG SAU NÀY
data/report_public_context.json: nguồn và nhận định vĩ mô/ngành.
data/report_issuer_research.json: hồ sơ nghiên cứu riêng theo mã, có ngày và nguồn.
data/company_profile_master.csv: hồ sơ biên tập sẵn được giữ lại.
Ngày AccessedOn/ResearchedOn phải là ngày thực sự rà soát; không đổi ngày chỉ để tạo cảm giác thông tin mới.
