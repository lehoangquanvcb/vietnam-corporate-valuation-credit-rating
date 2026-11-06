V8.146.0-CORPORATE-WEIGHTED-SCORE
Doanh nghiệp phi tài chính: bốn nhóm rủi ro × tỷ trọng → tổng điểm → bậc xếp hạng

THAY ĐỔI
- Bỏ chuỗi Anchor/SACP/SCA khỏi kết quả doanh nghiệp phi tài chính trên app và Word/PDF.
- Bảng chung có 5 cột: cấu phần, điểm, tỷ trọng, điểm đóng góp, kết quả/căn cứ.
- Dùng chung Bảng 01 để quy đổi tổng điểm trong luồng tự động và chuyên viên.
- Không làm tròn trung gian. Chặn tỷ trọng sai, điểm ngoài 1–6 và dữ liệu thiếu.
- Có thể nhập điểm cả bốn nhóm và tỷ trọng ngành trong phần thẩm định.
- Điều chỉnh thanh khoản/quản trị/hỗ trợ được tách riêng, sau tổng điểm.
- Giữ phương pháp và hỗ trợ Chính phủ của ngân hàng.

ĐỐI CHIẾU
Đã đọc phương pháp doanh nghiệp ngày 17/07/2025, các bản HPG cũ và báo cáo VHM
ngày 06/05/2026 anh cung cấp. Giải thích chi tiết: docs/CORPORATE_METHOD_V8_146.md.
Bộ tỷ trọng 20/30/35/15 hiện là cấu hình nghiên cứu kế thừa, chưa phải bộ KCF ngành
đã được xác nhận. Báo cáo VHM không nêu tỷ trọng; không ép mô hình khớp bậc AA.
Trên dữ liệu đang lưu: HPG 2,839875 → A−; VIC 3,511250 → BBB−.
Các kết quả tự động có giả định được công bố trong app và báo cáo.

CÀI ĐẶT
Đây là bản cập nhật trên V8.145, không phải bản đầy đủ của dự án.
Không cần tải lại bộ data/financial_evidence nếu đã cài V8.145.
1. Giải nén ZIP ra một thư mục tạm.
2. Chép toàn bộ NỘI DUNG trong ZIP vào:
   C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
3. Chọn Replace cho các file trùng tên. app.py nằm ngay trong thư mục dự án.
4. Mẫu Word mới: report_examples/Bao_cao_XHTN_HPG_06-11-2026.docx.
   Mẫu chỉ để xem, không thuộc danh sách đưa lên Git.

ĐƯA LÊN GIT — MỞ CMD VÀ CHẠY TỪNG DÒNG
cd /d C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
findstr /C:"BUILD_TAG=" app.py
git add --pathspec-from-file=GIT_FILES_V8_146.txt
git --no-pager diff --cached --stat
git commit -m "V8.146 corporate four-factor weighted rating"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Kết quả cuối cần là:
BUILD_TAG='V8.146.0-CORPORATE-WEIGHTED-SCORE'
Nếu pull báo conflict, xử lý conflict trước khi push; không dùng push --force.
Chờ Streamlit triển khai; Reboot app trong Manage app nếu vẫn hiện bản cũ.
Chọn HPG/VIC: phần kết quả phải có Tổng điểm có trọng số, Bậc xếp hạng ban đầu,
Kết quả xếp hạng. Tạo lại Word/PDF để nhận bảng bốn nhóm mới.

KIỂM TRA TẠI MÁY (KHÔNG BẮT BUỘC ĐỂ CÀI)
python scripts/check_report_scores.py --tickers HPG VIC VHM VCB SSI
python -m pytest tests/test_corporate_weighted_method.py -q
Chi tiết kiểm thử của gói: docs/validation_v8_146.json.
