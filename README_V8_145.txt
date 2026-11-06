V8.145.0-CORPORATE-CLOUD-DATA
Sửa dữ liệu và báo cáo doanh nghiệp phi tài chính trên Streamlit Cloud

NGUYÊN NHÂN
Git bỏ qua data/raw; bản Cloud không có dữ liệu gốc của doanh nghiệp phi tài chính.
Cache fundamentals_long cũ có mã bị ghi Period=LATEST và Field=value/order nên không đủ
căn cứ dựng lịch sử hay chấm điểm. Ngân hàng có nguồn lịch sử riêng nên vẫn hoạt động.
Bảng ngành cũ còn gộp VIC vào Tài chính, làm sai nhóm so sánh.

BẢN SỬA
- Đưa dữ liệu có mã dòng, kỳ, cơ sở tính và nguồn rõ ràng vào data/financial_evidence.
- Gói có dữ liệu của 1.711 mã ngoài ngân hàng; 15 mã chưa có nguồn gốc phù hợp.
- Máy có data/raw vẫn ưu tiên giá trị nguồn; không che lỗi mâu thuẫn bằng bản dự phòng.
- Refresh/rebuild dữ liệu tự cập nhật file triển khai tương ứng để lần đẩy Git sau giữ số liệu.
- Sửa phân ngành theo ICB công khai của Vietcap: VIC = Bất động sản,
  HPG = Thép và sản phẩm thép, FPT = Phần mềm. 29 mã được đưa về đúng phương pháp
  chứng khoán/bảo hiểm; công ty tài chính cá nhân, quản lý tài sản/quỹ không chấm như DN thường.
- Sửa sai số số thực ở biên 1–6 gây lỗi tính điểm ở ATG, LO5, TCJ, VTJ.
- Hồ sơ VIC có thông tin công khai từ Vingroup; nội dung ngành dùng đúng ngành ICB
  hoặc ngành cha. Trang bìa doanh nghiệp phi tài chính hiển thị tên ngành cụ thể.
- Giữ quy tắc hỗ trợ Chính phủ của ngân hàng; không cộng hỗ trợ đó cho DN phi tài chính.

KẾT QUẢ TRÊN BỘ DỮ LIỆU LƯU HIỆN TẠI
VIC: BBB-; HPG: A-; FPT: A+; VNM: AA-; DGC: A-.
Đây là bậc tự động có giả định, không phải kết luận CRA.
1.670 mã thuộc nhóm CORPORATE: 1.246 có bậc; 417 thiếu đầu vào/peer phù hợp;
7 mã ngoài phạm vi phương pháp. Không tạo số liệu hoặc bậc thay thế cho phần còn thiếu.
Đã kiểm tra cả 1.754 mã của bốn nhóm, không có lỗi chạy trong quy trình kiểm tra điểm.
Chi tiết từng mã: docs/coverage_v8_145.csv; kiểm thử và giới hạn: docs/validation_v8_145.json.

CÀI ĐẶT
Đây là bản cập nhật trên V8.144, không phải toàn bộ dự án mới.
1. Giải nén ZIP ra một thư mục tạm.
2. Chép toàn bộ NỘI DUNG trong ZIP vào:
   C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
3. Chọn Replace các file trùng tên. app.py phải nằm ngay trong thư mục dự án.
   BẮT BUỘC chép cả data/financial_evidence, không chỉ chép app.py hoặc scripts.
4. Không cần xóa dữ liệu gốc hoặc cài thêm thư viện.
5. Mẫu Word ở report_examples/Bao_cao_XHTN_VIC_06-11-2026.docx.
   Mẫu không nằm trong danh sách đưa lên Git.

ĐƯA LÊN GIT — MỞ CMD, CHẠY TỪNG DÒNG
cd /d C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
findstr /C:"BUILD_TAG=" app.py
git add --pathspec-from-file=GIT_FILES_V8_145.txt
git --no-pager diff --cached --stat
git commit -m "V8.145 restore corporate financial data on Cloud"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Kết quả cuối cần là:
BUILD_TAG='V8.145.0-CORPORATE-CLOUD-DATA'
Nếu pull báo conflict, xử lý conflict trước khi push; không dùng push --force.
Sau khi Streamlit triển khai, vào Manage app > Reboot app nếu còn hiện bản cũ.
Chọn VIC: ngành Bất động sản; có lịch sử 2021–2025 và bậc BBB- trên bộ dữ liệu hiện tại.
Tạo lại báo cáo Word/PDF; file đã tải trước đây không tự cập nhật.

CẬP NHẬT DỮ LIỆU VỀ SAU
Refresh/rebuild tự tạo file data/financial_evidence/<Mã>.csv.gz.
Nếu cập nhật raw bằng công cụ khác, chạy:
python scripts/export_financial_evidence.py --tickers VIC HPG FPT
Sau đó đưa các file data/financial_evidence thay đổi lên Git cùng mã nguồn.
Không gọi lệnh xuất trên Cloud khi Cloud không có raw; file triển khai đã đi kèm bản cập nhật.
manifest.json là danh mục của lần xuất toàn bộ; timestamp nội dung của từng file mới
được runtime dùng để làm mới cache sau các lần cập nhật riêng lẻ.

GIỚI HẠN
Sửa khả năng đọc dữ liệu đã lưu, không tự thay toàn bộ BCTC bằng kỳ mới công bố trên mạng.
VIC vẫn dùng số liệu đến Q2/2026 trong bộ gốc; trang công bố có Q3/2026 được ghi riêng
trong phần tổng quan, không trộn số Q3 vào bảng điểm Q2.
Một số mã không đủ chỉ tiêu trả nợ/dòng tiền hoặc peer cùng kỳ; danh sách được ghi rõ.
Các giả định định tính của mô hình vẫn phải được rà soát khi sử dụng kết quả.
