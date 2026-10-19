# Bổ sung bằng chứng bảo hiểm

## Dữ liệu định lượng

Mở `config/insurance_metric_inputs.csv` bằng Excel hoặc trình sửa CSV. Giữ tên
các cột và lưu UTF-8. Danh mục chỉ tiêu nằm ở `docs/insurance_input_dictionary.csv`.

| Cột | Nội dung |
| --- | --- |
| Ticker | Mã công ty, ví dụ ABI. |
| Period | Quý theo dạng 2026-Q2. Số cả năm 2025 dùng 2025-Q4 và Basis=FY. |
| Metric | Mã trong danh mục; không đổi tên tự do. |
| Value | Tiền: đồng, không phải tỷ đồng. Tỷ số: số thập phân, 14% nhập 0.14; 2,2 lần nhập 2.2. Số 0 chỉ nhập khi nguồn xác nhận. |
| Basis | END_PERIOD cho số dư/tỷ số tại ngày báo cáo. QUARTER, YTD, FY hoặc TTM cho EBITDA, lãi vay và các tỷ lệ khai thác tương ứng. |
| Source | Tên công bố, ngày, trang/thuyết minh, URL hoặc đường dẫn chứng từ. |
| ReviewedBy | Người đã đối chiếu và xác nhận. |
| Scope | Phạm vi pháp nhân/BCTC; nêu rõ hợp nhất hay riêng và phi nhân thọ, không trộn pháp nhân. |
| Definition | Định nghĩa và công thức. Tỷ lệ LossRatio/ExpenseRatio/CombinedRatio phải dùng NET_EARNED_CLAIMS_OPS_ADMIN_OTHER_V1 để so sánh cùng bộ. |

Mỗi chỉ tiêu/quý/cơ sở có đúng một dòng. Để có chuỗi 5 năm, bổ sung đủ từng kỳ;
một số mới nhất không được sao chép lùi về các năm. Dòng tỷ lệ cả năm không được
dùng thay tỷ lệ quý. Bản ghi thiếu nguồn/người duyệt không được xem là đã xác minh.

## Tài sản thanh khoản

Nhập đủ bảy cấu phần sau, kể cả số 0 được nguồn xác nhận: LiquidCash,
DepositsIGUnder6M, DepositsOtherUnder6M, GovernmentBondsLiquid,
RatedBondsIGLiquid, RatedBondsOtherLiquid, ListedEquitiesLiquid.

Tiền gửi phải có kỳ hạn dưới sáu tháng. IG là vnBBB− trở lên; Other là các
hạng khác nằm trên vnCCC, không gồm tài sản chưa được chứng minh đủ điều kiện.
Tài sản vnCCC trở xuống và tài sản khác bị khấu trừ 100%, không nhập vào các
nhóm đủ điều kiện. Nếu chưa xếp hạng nhưng có mức tín nhiệm tương đương đáng
tin cậy, hồ sơ thẩm định phải ghi rõ căn cứ phân loại. Tỷ số dùng tổng nghĩa vụ
hợp đồng InsuranceContractObligations, không tự lấy số dư InsuranceReserves.

## Thẩm định và lưu bản nháp

Trong màn hình XHTN, mở phiếu phương pháp bảo hiểm 2025. Điền đánh giá, lập luận
và nguồn cho từng yếu tố; sau đó nhập các điểm tổng hợp và quyết định điều chỉnh.
Các ô chưa nhập giữ “Chưa thẩm định”. Số 0 biểu thị đã kết luận không điều chỉnh.

Quyết định tổng hợp cần giải thích vốn/dự báo, mức độ rủi ro, cách xử lý các
trường hợp định tính hoặc chồng lấn, tác động thanh khoản, hỗ trợ đã loại trùng.
Nếu ma trận 01 có 6/7 hoặc ma trận 02 có nhiều bậc, chọn đúng một phương án
Hội đồng đã xem xét. Tập đoàn/tái bảo hiểm cần phương pháp khác hoặc dữ liệu
riêng của pháp nhân được đánh giá; checkbox không mở rộng phạm vi phương pháp.

Bản nháp giữ khi chuyển màn hình trong cùng phiên chạy; tải JSON để lưu hồ sơ
lâu dài. JSON không tự ghi vào dữ liệu tài chính và không phải phê duyệt xếp hạng.
