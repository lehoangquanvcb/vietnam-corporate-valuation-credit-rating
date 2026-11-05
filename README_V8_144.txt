V8.144.0-BANK-GOVERNMENT-SUPPORT
Nâng cấp cấu phần ngân hàng và hỗ trợ Chính phủ

THAY ĐỔI CHÍNH
- Tách SACP, Hỗ trợ từ Chính phủ, Hỗ trợ cổ đông/khác và ICR trên app và báo cáo.
- Chỉ VCB, BID, CTG, AGRIBANK được cộng hỗ trợ Chính phủ.
- Chính sách nghiên cứu mới: tối đa 6 notch, trần AAA; không tạo bậc khi thiếu dữ liệu, không vượt giới hạn pháp định, không cộng chồng tổng hỗ trợ đã nhập.
- Bổ sung điều kiện bền vững lợi nhuận và chất lượng tài sản qua nhiều năm khi đánh giá nội tại, áp dụng chung cho mọi ngân hàng.
- Giữ thay đổi báo cáo/nội dung của V8.143 và nhãn CAR gọn của V8.142.

KẾT QUẢ KIỂM TRA VỚI BỘ DỮ LIỆU HIỆN CÓ
VCB: SACP AA, Chính phủ +2, ICR AAA.
BID: SACP A, Chính phủ +5, ICR AAA.
CTG: SACP A+, Chính phủ +4, ICR AAA.
TCB: SACP/ICR AA, Chính phủ 0.
OCB: SACP/ICR A, Chính phủ 0.
ABB: SACP/ICR A-, Chính phủ 0.
Agribank: thuộc phạm vi hỗ trợ, nhưng thiếu dữ liệu tài chính nên chưa có SACP/ICR.

LƯU Ý VỀ PHƯƠNG PHÁP
Bảng 13 của phương pháp gốc đã có hỗ trợ bốn ngân hàng quốc doanh. Giới hạn 6 notch và trần AAA là giả định nâng cấp của mô hình theo yêu cầu nghiên cứu; không phải nguyên văn bảng gốc hay kết luận CRA. Không chuyển xếp hạng quốc tế trực tiếp sang thang trong nước.
Chính sách hiện áp dụng kỳ 2026-Q2 đến 2026-Q4; kỳ ngoài phạm vi cần rà soát lại. Không thay đổi số liệu BCTC/CAR và không đưa lại bước Hiệu chỉnh thang trong nước.
Các bậc tự động vẫn có giả định về dữ liệu định tính. Chi tiết: docs/BANK_SUPPORT_V8_144.md.

CÀI ĐẶT
Gói cập nhật nối tiếp V8.142/V8.143, không phải toàn bộ dự án mới.
Giải nén ra thư mục tạm, rồi chép toàn bộ NỘI DUNG trong ZIP vào:
C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
Chọn Replace các file trùng tên. app.py phải nằm trực tiếp trong thư mục dự án.
Giữ các thư mục dữ liệu và môi trường Python có sẵn. Không cần cài thêm thư viện.
Mẫu Word: report_examples/Bao_cao_XHTN_VCB_05-11-2026.docx.
GIT_FILES_V8_144.txt không đưa báo cáo mẫu lên Git.

ĐƯA LÊN GIT — MỞ CMD, CHẠY TỪNG DÒNG
cd /d C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
findstr /C:"BUILD_TAG=" app.py
git status
git add --pathspec-from-file=GIT_FILES_V8_144.txt
git --no-pager diff --cached --stat
git commit -m "V8.144 add government support and durable bank factor evidence"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Kết quả cuối cần là:
BUILD_TAG='V8.144.0-BANK-GOVERNMENT-SUPPORT'

Nếu pull báo conflict, xử lý conflict trước khi push; không dùng push --force.
Sau khi Streamlit triển khai, kiểm tra phiên bản và tạo lại báo cáo Word/PDF.
Các file báo cáo đã tải trước đó không tự cập nhật.

KIỂM THỬ
Toàn bộ bộ kiểm thử: 441 passed, 22 subtests passed.
Đã chạy đối chiếu 28 mã ngân hàng, Agribank và 5 mã thuộc các nhóm ngành khác.
Đã kiểm tra luồng giao diện của ABB, VCB, BID, CTG, TCB, OCB và kịch bản tắt/bật hỗ trợ VCB.
Báo cáo Word VCB được render và xem toàn bộ 24 trang.
Chi tiết kết quả trong docs/validation_v8_144.json và docs/bank_validation_v8_144.json.
PASS là kiểm tra phần mềm, không phải xác nhận thẩm định hoặc kiểm định thống kê với CRA.
