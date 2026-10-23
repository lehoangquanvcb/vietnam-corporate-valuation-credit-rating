# Nhóm so sánh bảo hiểm V8.122.0

BVH và PVI được xếp vào nhóm so sánh Phi nhân thọ theo yêu cầu cấu hình ngày 23/10/2026. Nhóm gồm ABI, AIC, BIC, BLI, BMI, BVH, MIG, PGI, PTI và PVI. Mỗi doanh nghiệp có 9 ứng viên peer trong nhóm này. PRE và VNR giữ nhóm Tái bảo hiểm.

Với bộ dữ liệu quý 2026-Q2 đang kiểm tra, phí gốc, phí thuần, lợi nhuận hoạt động bảo hiểm và dự phòng của BVH/PVI có 9 peer hợp lệ. Biểu đồ có 10 cột, gồm doanh nghiệp và 9 peer. Chỉ tiêu tài chính chung tiếp tục tham chiếu cả 12 mã bảo hiểm, tức 11 peer. Các tỷ lệ chưa có số hợp lệ hoặc không áp dụng vẫn có ít peer hơn; không tạo thêm số để đủ số lượng.

## Phân nhóm và phạm vi số liệu

- `InsuranceSubtype`: nhóm so sánh cấu hình trong `config/insurance_entities.csv`; BVH/PVI là `NONLIFE`.
- `InsuranceReportingSubtype`: phạm vi mô hình của số liệu; BVH/PVI vẫn là `GROUP`. Đây là thông tin về BCTC, không phải bộ lọc nhóm peer nghiệp vụ.
- `SamePeerGroup`: quyết định phạm vi so sánh nghiệp vụ trên UI, bảng KPI và Word.
- `SameModel`: so sánh phạm vi BCTC, dùng cho nhận định mạnh/yếu tự động, peer định giá và các kiểm soát phương pháp.

Việc gộp nhóm không biến BCTC hợp nhất thành BCTC riêng của pháp nhân phi nhân thọ. Phạm vi hợp nhất được nêu trên giao diện và trong Word. Không tự mở lại ma trận XHTN phi nhân thọ, tỷ lệ kết hợp hoặc định giá P/B phi nhân thọ cho dữ liệu hợp nhất chỉ vì đổi nhóm so sánh.

Bình quân và trung vị chỉ công bố khi có ít nhất 5 peer hợp lệ đúng quý/cơ sở; loại chính doanh nghiệp khỏi phép tính. Mỗi mã bị loại vẫn có lý do trong bảng chi tiết. Không sử dụng quý cũ thay cho quý đang so sánh.

## Cơ sở xác nhận phạm vi BCTC

- Bảo Việt công bố cả hoạt động bảo hiểm nhân thọ và phi nhân thọ: https://www.baoviet.com.vn/vi
- PVI Holdings mô tả mô hình công ty mẹ/con, bảo hiểm phi nhân thọ, tái bảo hiểm và quản lý tài sản: https://pviholdings.com.vn/vi/pvi-present
- Đối chiếu ngày 23/10/2026. Nhóm peer theo cấu hình người dùng không phải thay đổi định danh pháp lý.

## Cài đặt và kiểm tra

Gói ZIP đặt `app.py`, `VERSION.txt`, `config/`, `scripts/`, `tests/` và `docs/` ngay ở gốc. Giải nén vào thư mục project và cho phép ghi đè tệp cùng tên. Không có thư mục `UPDATE`.

Gói tích lũy các thay đổi V8.120 và V8.121, áp dụng từ V8.119–V8.121. Có cập nhật danh mục `config/insurance_entities.csv`; không kèm dữ liệu raw hay đầu vào thẩm định cá nhân.

Chạy `python scripts/check_insurance_runtime.py`. Build phải là `V8.122.0-INSURANCE-NONLIFE-PEERS`; kiểm tra các trường nhóm peer và số peer của phí gốc/lợi nhuận hoạt động bảo hiểm cho ABI, BVH, PVI. Xuất lại Word sau khi cập nhật; báo cáo đã xuất trước đó không tự thay đổi.
