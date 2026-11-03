V8.135.0-BANK-CAR-FALLBACK

CAR THEO NGUỒN ĐÃ ĐỐI CHIẾU VÀ BẢNG NGƯỜI DÙNG CUNG CẤP

Ưu tiên CAR đã đối chiếu báo cáo gốc. Bổ sung EIB 12,60%, MSB 12,28%, VCB ước 12,50% tại 30/6/2026. HDB 16,00%, VIB 12,20% và MBB khoảng 11,50% dùng kỳ 31/12/2025 cho bảng điểm 30/6/2026.

Bổ sung nguồn gốc BAB 8,95% và STB 9,89% tại 30/6/2026. ABB giữ 12,72%, TCB 14,95%, SSB 12,06%. TCB cuối 2025 giữ 14,61% từ nguồn gốc thay vì làm tròn 14,60%.

Không ghi số cuối 2025 thành số quý II/2026. Không chuyển số ước tính thành số đã xác minh. Hai loại nguồn được lưu riêng; sửa nguồn làm mới cache và báo cáo tải xuống. Giữ bảng chấm/thẩm định riêng đã lưu.

CÀI ĐẶT

Đóng ứng dụng local nếu đang chạy. Giải nén ZIP, chép app.py, VERSION.txt và các thư mục scripts, data, config, assets, tests, docs cùng các tệp hướng dẫn trực tiếp vào:
E:\Valuation_and_Credit_Rating_Intelligence

Chọn Replace khi trùng tệp. app.py trong gói phải nằm trực tiếp tại E:\Valuation_and_Credit_Rating_Intelligence\app.py. Không đặt trong thư mục UPDATE.
Đây là bản vá tích lũy, cần chép vào project hiện có. Gói không ghi đè config/bank_rating_assessments.json hoặc config/insurance_metric_inputs.csv.

KIỂM TRA TRONG CMD

Chạy TỪNG lệnh, nhấn Enter và đợi xong mới chạy lệnh tiếp theo:

cd /d E:\Valuation_and_Credit_Rating_Intelligence

findstr /C:"BUILD_TAG=" app.py

"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_bank_car.py --period 2026-Q2

"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py --tickers ABB TCB SSB BAB STB EIB MSB VCB HDB VIB MBB SSI ABI HPG

Build đúng: V8.135.0-BANK-CAR-FALLBACK.
Dữ liệu kèm gói: Available 20; CurrentPeriodAvailable 17; VerifiedDisclosures 14; Fallback2025 3; UserInputsUsed 6; Result PARTIAL.
PARTIAL phản ánh còn 8 mã thiếu CAR trong dữ liệu ứng dụng, không phải lỗi thực thi hoặc kết luận chưa công bố. Danh mục ứng dụng có 28 mã BANK, trong đó PCB cần xác minh định danh; không dùng con số 28 như số lượng niêm yết đã xác minh.

Bậc tự động tại dữ liệu của gói: EIB BB, MSB BBB, VCB A, HDB A-, VIB BB-, MBB BBB-. Bảng chấm riêng đã lưu có thể cho kết quả khác và vẫn được ưu tiên.

UP LÊN GIT

Chạy TỪNG lệnh riêng:

git status --short

git add -f --pathspec-from-file=GIT_FILES_V8_135.txt

git --no-pager diff --cached --stat

git commit -m "Add user CAR inputs and dated fallback V8.135.0"

git pull --rebase origin main

git push origin main

git fetch origin

git --no-pager show origin/main:app.py | findstr /C:"BUILD_TAG="

git status

Chỉ tiếp tục push sau khi commit và pull thành công. Nếu báo xung đột, dừng ở lệnh đó; không dùng reset --hard. Nếu commit báo nothing to commit thì kiểm tra build local và build origin/main trước khi kết luận đã cập nhật.
Lệnh cuối kiểm tra origin/main phải trả V8.135.0-BANK-CAR-FALLBACK.

STREAMLIT

Sau khi Cloud cập nhật, kiểm tra đúng phiên bản ở sidebar. Nếu vẫn bản cũ, Manage app > Reboot app. Mở HDB: CAR 16,00% kèm kỳ 31/12/2025 và bậc tự động A-. Mở VCB: CAR 12,50% được ghi ước tính, bậc tự động A. Bấm Chuẩn bị báo cáo Word để tạo file mới.

Chi tiết nguồn và phạm vi: docs/BANK_CAR_USER_INPUTS_V8_135.md.
Kết quả kiểm tra thực thi: docs/validation_v8_135.json.
