BẢN CẬP NHẬT V8.131.0 — TÊN FILE, BÌA, HEADER, FOOTER VÀ BẢNG ĐIỂM

1. GIẢI NÉN
Giải nén toàn bộ nội dung ZIP trực tiếp vào:
E:\Valuation_and_Credit_Rating_Intelligence

app.py và VERSION.txt phải nằm ngay tại thư mục này. Đồng ý ghi đè file trong gói.
KHÔNG đặt trong UPDATE hoặc tạo thêm một thư mục project lồng bên trong.
Đây là gói cập nhật tích lũy cho project hiện có, không phải bộ cài độc lập.
Gói không chứa .git, .venv, secrets, phiếu nhập tay insurance_metric_inputs.csv hoặc bank_rating_assessments.json.

2. KIỂM TRA
Mở CMD và chạy lần lượt:

cd /d E:\Valuation_and_Credit_Rating_Intelligence
findstr /C:"BUILD_TAG=" app.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_runtime.py --tickers TCB SSI ABI HPG

BUILD_TAG phải là V8.131.0-REPORT-SCORES. Đây là tên phiên bản, không phải lệnh để gõ riêng.
PASS xác nhận kiểm tra phần mềm, không xác nhận đã thẩm định mọi công ty.

3. UP LÊN GIT
Chạy từng lệnh trong cùng cửa sổ CMD:

git add -f --pathspec-from-file=GIT_FILES_V8_131.txt
git diff --cached --stat
git commit -m "V8.131.0 unify report exports and add conditional rating scorecards"
git pull --rebase origin main
git push origin main
git status

Danh sách GIT_FILES_V8_131.txt chỉ gồm file thuộc bản cập nhật. Không cần thêm backup hoặc các thư mục untracked khác.
Nếu rebase có xung đột, giải quyết xung đột trước khi push; không dùng force push.

4. STREAMLIT
Sau khi ứng dụng nạp commit mới, thanh bên phải hiển thị V8.131.0-REPORT-SCORES.
Vào BÁO CÁO XẾP HẠNG TÍN NHIỆM > Chuẩn bị báo cáo Word > Tải báo cáo Word.
Tên file có dạng: Báo cáo XHTN không chỉ định TCB 02-11-2026.docx.
Ngày trên tên file, bìa và header là ngày thực tế chuẩn bị file theo giờ Việt Nam.
Phiên bản chỉ hiển thị trong ứng dụng, không in trên báo cáo.

Nếu chạy local:
"C:\Users\HP\.venv\Scripts\python.exe" -m streamlit run app.py

5. PHẦN ĐIỂM
Cùng một luồng áp dụng cho mọi mã trong bốn nhóm. Kết quả tự động có nhãn Bậc ước tính tự động, bảng cấu phần và giả định sử dụng; không ghi đè phiếu đã thẩm định.
Không gán bậc khi thiếu dữ liệu tài chính cốt lõi hoặc ngoài phạm vi phương pháp. Riêng BVH/PVI là BCTC tập đoàn, PRE/VNR là tái bảo hiểm: có mẫu báo cáo nhưng chưa có phương pháp xếp hạng phù hợp trong bộ tài liệu hiện tại.
Chi tiết phần nào là bảng phương pháp gốc và phần nào là giả định: docs\REPORT_EXPORT_AND_SCORING_V8_131.md.
