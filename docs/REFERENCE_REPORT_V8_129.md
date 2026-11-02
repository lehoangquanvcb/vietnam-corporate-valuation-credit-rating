# V8.129 — kế thừa bảng chấm và bố cục TCB

Báo cáo nguồn `TCB_XHTN(1).docx` có bảng tổng kết rõ bốn cấu phần và tổng +5 notch. Bản này khôi phục kết quả mô phỏng TCB 2026-Q2: Anchor A−, SACP/ICR AA+, hỗ trợ 0, triển vọng Ổn định. Không suy ra rằng bậc nguồn đã được phê duyệt hay mọi ngân hàng khác có cùng bậc.

`rating_reference.py` kiểm tra mã, kỳ, số cấu phần, đánh giá/notch hợp lệ và tính khớp Anchor → SACP → ICR trước khi lưu. `bank_method_2026.py` chỉ nạp phiếu đúng mã/kỳ. Phiếu thẩm định riêng ưu tiên hơn bảng nguồn. Chế độ nhập lại không giữ ngầm đánh giá cũ; thay đổi đánh giá sẽ tính lại bậc.

Mẫu Word khôi phục bìa và tiêu đề xanh, khối kết quả/luận điểm, bảng điểm mạnh/rủi ro, các chương theo bốn cấu phần ngân hàng, độ nhạy và bảng tổng kết có cột nâng/hạ bậc. Nội dung nêu rõ nguồn kế thừa. Biểu đồ năm và quý xếp dọc, năm có đường peer trung bình. Nhúng bốn phông Lato, giữ tiêu đề và hình cùng phần nhận định khi ngắt trang.

Chuỗi tài chính 2021–2025 dùng số năm, peer dùng quý II/2026. So sánh loại chính TCB và chỉ tính bình quân khi có tối thiểu 5 peer cùng kỳ/cơ sở. Các nhận định mới phân biệt CASA cao hơn peer với CASA giảm dài hạn; ROA cao hơn đi cùng ROE thấp hơn và đòn bẩy thấp hơn; NPL thấp hơn peer nhưng cao hơn năm đầu chuỗi.

Dữ liệu vẫn còn thiếu CAR đúng kỳ, vốn hữu hình, chi phí dự phòng/dư nợ và chi phí dự phòng/thu nhập hoạt động. Không dùng CAR 15,8% mang kỳ 2022-Q2 của báo cáo mẫu để lấp kỳ hiện tại. Bậc vốn kế thừa đánh giá “Mạnh” trong bảng chấm, không có nghĩa engine đã tính ra CAR kỳ vọng từ BCTC.

Gói cập nhật không chứa phiếu rỗng `config/bank_rating_assessments.json`, không thay các phiếu người dùng đã nhập. Không có thư mục UPDATE. Báo cáo mẫu là kết quả thực thi từ project này, không phải chỉnh sửa trực tiếp Word để tạo bậc.
