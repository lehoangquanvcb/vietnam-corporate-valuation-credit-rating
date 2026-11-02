# V8.126.0 — khôi phục dữ liệu ngân hàng khi triển khai thiếu raw

## Lỗi đã tái hiện

V8.125 ưu tiên dữ liệu chi tiết trong `data/raw`. `.gitignore` của project loại thư mục này khỏi Git, trong khi `data/bank_history_long.csv` vẫn được đưa lên ứng dụng. Luồng đọc chỉ cho bốn chỉ tiêu ngân hàng dùng bảng lịch sử dự phòng. Khi chạy không có raw, ABB giữ được tiền gửi và CAR nhưng mất tổng tài sản, dư nợ, vốn, lợi nhuận, thu nhập lãi thuần, ROE, NPL, P/B và CASA. Bỏ raw khỏi bản thử nghiệm đã tái hiện đúng ảnh người dùng gửi.

## Thay đổi

- Bổ sung các Metric ngân hàng có định nghĩa rõ ràng trong bảng lịch sử, dùng chung cho mọi mã thuộc BANK.
- Ưu tiên từng quan sát raw hợp lệ; chỉ lấy lịch sử dự phòng đúng mã, đúng Metric và đúng kỳ còn thiếu. Ghi nguồn `data/bank_history_long.csv:<Metric>`.
- Giữ số 0 thật, số âm, các kỳ trống. Không dùng cache để che xung đột raw; xung đột trong cache cũng trả lỗi.
- Bảng lịch sử hiện có dùng tiền tệ VND, tỷ số thập phân và dòng thu nhập theo quý riêng lẻ. Nếu có cột `Basis`, giữ cơ sở khai báo; nguồn YTD được tách quý trước khi cộng.
- YTD/FY/TTM chỉ cộng đủ các quý liên tiếp. Không cộng số dư hoặc ROE/ROA/NIM. Không dùng một dòng snapshot cho chuỗi năm.
- Không áp dụng fallback này cho doanh nghiệp thường, chứng khoán hoặc bảo hiểm. Không lấy EPS/BVPS từ cache ngân hàng cũ chưa rõ đơn vị.
- CAR công bố khác kỳ được ghi rõ kỳ dưới dãy KPI; không đưa CAR cũ vào so sánh quý hiện tại.
- Đổi nhãn `NetInterestIncome` thành `Thu nhập lãi thuần` trong bảng lịch sử.

## Kiểm tra tại máy người dùng

Chạy `python scripts/check_bank_runtime.py`. Script kiểm tra phiên bản, đối chiếu bảng lịch sử cho các ngân hàng và tạo bản thử tạm không có raw. Tệp dữ liệu gốc không bị sửa. Chạy `python -m unittest discover -s tests -p test_bank_history_fallback.py -v` để chạy các kiểm thử độc lập với dữ liệu thị trường.

Ứng dụng cần `data/bank_history_long.csv` hiện có. Bản vá không đóng gói đè số liệu cũ lên số liệu mới và không cần gọi Vnstock để khôi phục các chỉ tiêu đã lưu.

## Phạm vi xác minh

Tái dựng từ project người dùng đã gửi ngày 16/10/2026 và các gói V8.119/V8.125, đối chiếu dữ liệu trong project; không truy cập hay sửa trực tiếp ứng dụng Streamlit Cloud. Ảnh chụp xác nhận build V8.125.0 đang chạy. Bộ kiểm tra mô phỏng điều kiện thiếu raw, không khẳng định đã kiểm tra danh sách tệp trên máy chủ của người dùng.
