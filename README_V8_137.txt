BẢN CẬP NHẬT V8.137.0-DOMESTIC-BANK-RATING

1. Giải nén toàn bộ nội dung ZIP TRỰC TIẾP vào:
E:\Valuation_and_Credit_Rating_Intelligence
Chọn thay thế các tệp trùng tên. app.py phải nằm ngay trong thư mục project, không đặt trong UPDATE.

2. Kết quả mặc định khi đủ đầu vào và không có phiếu đánh giá riêng:
VCB, BID, CTG: AAA.
TCB, VPB, ACB: AA-.
ABB: A-.
OCB, KLB, STB: trần A-, các bậc thấp hơn tiếp tục phân hóa theo số liệu.
Agribank: AAA trong bảng khung tham chiếu; chưa có BCTC để tạo điểm/báo cáo tính toán.

Đây là hiệu chỉnh mức đích do chủ mô hình lựa chọn, không phải ý kiến xếp hạng của CRA. CAR, SACP và bảng điểm gốc được giữ nguyên. ACB AA- trong app khác mức AA+ của FiinRatings trong nguồn tham khảo. Không chuyển thang quốc tế thành thang trong nước.
TCB không còn ưu tiên bảng mẫu cũ khi chạy chế độ hiệu chỉnh mặc định. Có thể bỏ chọn Áp dụng khung hiệu chỉnh xếp hạng trong nước để chạy lại cơ chế cũ. Phiếu nhập riêng vẫn được ưu tiên.

3. Mở CMD, chạy TỪNG DÒNG sau. Chỉ chuyển bước khi dòng trước thành công:

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_bank_domestic_rating.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py --tickers VCB BID CTG TCB VPB ACB ABB OCB KLB STB

git add -f --pathspec-from-file=GIT_FILES_V8_137.txt
git --no-pager diff --cached --stat
git commit -m "Calibrate domestic bank ratings V8.137.0"
git pull --rebase origin main
git push origin main
git fetch origin
git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

Kết quả dòng cuối phải có:
BUILD_TAG='V8.137.0-DOMESTIC-BANK-RATING'
Không gõ nối hai lệnh vào một dòng. Nếu rebase báo xung đột, dừng tại đó và gửi nguyên thông báo.

4. Trên Streamlit Cloud, chờ cập nhật hoặc Manage app > Reboot app nếu cần. Kiểm tra phiên bản trên sidebar là V8.137.0-DOMESTIC-BANK-RATING. Chọn lại mã và bấm Chuẩn bị báo cáo Word/PDF để tạo bản mới.

5. Chi tiết và giới hạn: docs/DOMESTIC_BANK_RATING_V8_137.md.
Gói không ghi đè config/bank_rating_assessments.json hoặc config/insurance_metric_inputs.csv.
Các kiểm tra PASS xác nhận phần mềm, không xác nhận chất lượng tín dụng của mức đích. Gói này được kiểm tra ở môi trường thử nghiệm; chưa tự push vào GitHub hay thay đổi Streamlit Cloud của bạn.
