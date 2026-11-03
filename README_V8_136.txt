V8.136.0-VERIFIED-VCB-CAR

CẬP NHẬT CAR TỪ BÁO CÁO GỐC

VCB: CAR hợp nhất 30/06/2026 là 11,71%, riêng lẻ 11,03% (Biểu 1, trang PDF 2). Không dùng 11,14% trong bảng tổng hợp hoặc ước tính 12,50% của bản trước.
HDB: hợp nhất 14,27% tại 30/06/2026 và 16,72% tại 31/12/2025, theo cùng bảng trang PDF 5.
Bổ sung/đối chiếu VIB 11,80%; EIB 12,60%; BVB 12,08%; KLB 13,50%; SGB 15,48% hợp nhất. PGB 12,51% riêng lẻ vì không có công ty con.
Giữ ưu tiên số gốc đã đối chiếu: ABB 12,72%; TCB 14,95%; SSB 12,06%; STB 9,89% hợp nhất. Không làm tròn TCB thành 15% vì có thể đổi ngưỡng điểm.
MBB dùng khoảng 11,60% và MSB 12,28% tại 30/06/2026 từ bảng mới của người dùng. Giữ nhãn nguồn và dấu ước tính; không ghi thành đã đối chiếu báo cáo gốc.

Kỳ CAR, phạm vi hợp nhất/riêng lẻ và TT41/TT14 đi cùng số liệu. Lịch sử vẫn là 5 năm tài chính đã kết thúc; số quý II không được ghi thành số cuối năm. Cơ chế dùng cuối 2025 khi thiếu Q2/2026 vẫn giữ và đã được kiểm thử bằng tình huống giả lập. Hiện 24 mã có số đúng Q2 nên không phải dùng cơ chế này.

CÀI ĐẶT

Đây là bản vá tích lũy dành cho project hiện có. Đóng app local nếu đang chạy; giải nén ZIP và chép toàn bộ NỘI DUNG bên trong trực tiếp vào:
E:\Valuation_and_Credit_Rating_Intelligence

Chọn Replace khi trùng tệp. app.py phải nằm tại E:\Valuation_and_Credit_Rating_Intelligence\app.py; không đưa vào thư mục UPDATE.
Gói không ghi đè config/bank_rating_assessments.json hoặc config/insurance_metric_inputs.csv. Bảng chấm riêng người dùng đã lưu vẫn được ưu tiên.

KIỂM TRA TRONG CMD

Chạy từng lệnh, nhấn Enter và đợi xong mới chạy lệnh tiếp theo:

cd /d E:\Valuation_and_Credit_Rating_Intelligence

findstr /C:"BUILD_TAG=" app.py

"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_bank_car.py --period 2026-Q2

"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py --tickers VCB HDB VIB EIB BVB KLB PGB SGB MBB MSB ABB TCB SSI ABI HPG

Build đúng: V8.136.0-VERIFIED-VCB-CAR.
Dữ liệu của gói: Available 24; CurrentPeriodAvailable 24; VerifiedDisclosures 22; UserInputsUsed 2; Fallback2025 0; Result PARTIAL.
PARTIAL phản ánh còn NVB, PCB, TPB, VBB chưa có CAR được nạp, không phải lỗi thực thi hoặc kết luận các ngân hàng chưa công bố. PCB cần xác minh định danh; 28 mã BANK trong ứng dụng không phải số ngân hàng niêm yết được xác minh.
Bậc tại dữ liệu và cấu hình kèm gói: VCB A; HDB BBB-; VIB B+; BVB BB; KLB BBB; PGB BBB-; SGB BB. Bậc tự động có giả định và có thể thay đổi khi dữ liệu, peer hoặc bảng chấm riêng thay đổi.

UP LÊN GIT

Chạy từng lệnh riêng. Tệp GIT_FILES_V8_136.txt giới hạn đúng các tệp của bản vá:

git status --short

git add -f --pathspec-from-file=GIT_FILES_V8_136.txt

git --no-pager diff --cached --stat

git commit -m "Verify bank CAR disclosures V8.136.0"

git pull --rebase origin main

git push origin main

git fetch origin

git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

git status

Chỉ tiếp tục push sau khi commit và pull thành công. Nếu có xung đột, dừng ở lệnh đó; không dùng reset --hard. Nếu nothing to commit, kiểm tra lại build local và origin/main.
Build trên origin/main phải là V8.136.0-VERIFIED-VCB-CAR.

STREAMLIT

Sau khi Cloud cập nhật, kiểm tra phiên bản ở sidebar. Nếu vẫn bản cũ, Manage app > Reboot app. Mở VCB: CAR 11,71%, kỳ 30/06/2026, nguồn đã đối chiếu; HDB: CAR 14,27%. Bấm Chuẩn bị báo cáo Word để tạo bản mới.

Chi tiết đối chiếu: docs/BANK_CAR_VERIFIED_V8_136.md.
Kết quả chạy: docs/validation_v8_136.json và docs/bank_car_coverage_v8_136.json.
