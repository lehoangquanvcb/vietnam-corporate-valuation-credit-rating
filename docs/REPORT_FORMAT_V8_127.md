# Báo cáo V8.127.0

Bản này sửa đồng thời bộ xuất báo cáo và luồng đọc dữ liệu ngân hàng trên nền V8.125 hoặc V8.126. Mẫu rút gọn trước đó làm mất trang bìa, các nhóm luận điểm và biểu đồ khi xuất Word. Điểm vào `multisector_report.generate_docx` nay sử dụng bộ trình bày thống nhất cho ngân hàng, chứng khoán và doanh nghiệp phi tài chính. PDF tiếp tục chuyển từ chính Word đó. Bảo hiểm giữ bộ báo cáo đã sửa ở V8.125.

## Nội dung và trình bày

- Khổ A4, màu xanh theo báo cáo tham chiếu, phông Lato được nhúng vào Word, nội dung căn đều, bảng có tiêu đề lặp và số trang.
- Có trang bìa, kết quả và luận điểm, hồ sơ và bối cảnh, bảng lịch sử, phân tích theo nhóm, các điểm thiếu và bảng cấu phần xếp hạng.
- Mỗi chỉ tiêu có bằng chứng được phân tích một lần. Chuỗi doanh nghiệp và bình quân peer ở trên; so sánh quý gần nhất ở dưới. Biểu đồ đủ chiều rộng trang.
- Có nhận xét thay đổi nhiều năm, thay đổi cùng kỳ gần nhất, vị thế peer, ý nghĩa tài chính và kết luận theo bằng chứng.
- Các chỉ tiêu hoàn toàn thiếu được giải thích trong phụ lục; không tạo số hoặc tự gán mức tín nhiệm để lấp thiếu.

## Dữ liệu và peer

- Bao gồm sửa lỗi lịch sử ngân hàng của V8.126. Số tiền được đổi sang tỷ đồng; không cộng tỷ số hay số dư.
- Bổ sung vào gói 27 tệp tỷ số ngân hàng đã có trong dự án và bảng lịch sử ngân hàng. Đây là dữ liệu lưu sẵn đến 2026-Q2, không phải một lần tải mới từ vnstock.
- So sánh hiện tại dùng cùng quý và cơ sở: dòng tiền quý riêng lẻ, số dư cuối kỳ, tỷ số nguồn tại kỳ. Các tỷ số trả nợ giữ cửa sổ 12 tháng.
- Bình quân loại chính doanh nghiệp và cần tối thiểu 5 peer hợp lệ. Chuỗi bình quân dùng nhóm peer hiện được chọn, đối chiếu riêng từng năm; số lượng có số được ghi trong bảng.
- Dòng tiền lũy kế có thể lưu kỳ dưới dạng `2026-Q1|2026-Q2`; bộ báo cáo kiểm tra cả cơ sở tính và quý kết thúc, tránh làm mất đường bình quân vì chỉ so chuỗi ký tự với `2026-Q2`.
- CAR cũ không được đưa vào bảng peer quý mới. Các trạng thái thẩm định độc lập với tình trạng dữ liệu tài chính. Kết quả định tính và bậc xếp hạng không được mặc định là trung tính.

## Kiểm chứng thực thi ngày 30/10/2026

- Toàn bộ kiểm thử: 158 passed, 22 subtests passed.
- Kiểm tra ngân hàng: PASS cho 28 ngân hàng trong chế độ không có tệp raw; kiểm tra bảo hiểm: PASS.
- 5 tình huống giao diện Streamlit đã chạy, không có ngoại lệ, trên bản mô phỏng chỉ có các tệp tỷ số ngân hàng được đóng gói cùng bảng lịch sử.
- Đã xuất thật VCB, SSI và FPT qua điểm vào của ứng dụng; báo cáo VCB có 48 biểu đồ và 4 phông nhúng. Bản Word VCB 30 trang đã được kết xuất và kiểm tra trực quan.
- VCB có 23/27 chỉ tiêu đúng quý 2026-Q2. Bốn chỉ tiêu chưa đủ là CAR hiện tại, vốn hữu hình/tài sản, chi phí dự phòng/dư nợ và chi phí dự phòng/thu nhập hoạt động. Chúng không được tự điền.

Kết quả trên xác nhận bản mã và dữ liệu đã thử trong môi trường kiểm tra; không xác nhận ứng dụng Streamlit Cloud của người dùng đã nhận commit mới. Sau khi push, cần thấy build `V8.127.0-REPORT-FORMAT-DATA` trên app và xuất lại báo cáo. Các tệp Word đã tải trước đây không tự thay đổi.

## Tệp chính

`report_evidence.py` thu thập bằng chứng và tạo lập luận. `professional_report.py` trình bày và nhúng phông. `evidence_report.py` giữ API gọi chung. `check_report_runtime.py` thực sự xuất Word và kiểm tra cấu trúc. Phông Lato đi kèm giấy phép OFL trong `assets/fonts`.

Tham chiếu kỹ thuật nhúng phông: Microsoft Open XML Font Part, https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/ea097c57-5794-4624-b08e-017b47051b1d .
