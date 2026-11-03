# Sửa đánh giá huy động và thanh khoản ngân hàng

Bản 8.138.0 sửa quy tắc đã biến cho vay/tiền gửi BCTC > 1,2 lần thành thanh khoản Yếu. Tỷ số này phản ánh khoảng chênh tài trợ, không đồng nhất với LDR riêng lẻ công bố và không đủ để đánh giá dòng tiền trong điều kiện căng thẳng.

## Cơ sở đối chiếu

- Phương pháp XHTN Ngân hàng người dùng cung cấp, mục 6, trang 31–37: nguồn huy động và thanh khoản phải đánh giá riêng; áp ma trận tại trang 32. Huy động xét độ ổn định, đa dạng, kỳ hạn và chi phí. Thanh khoản xét nguồn, nhu cầu sử dụng và khả năng chịu đựng căng thẳng.
- Báo cáo TCB_XHTN chuẩn.docx người dùng gửi ngày 03/11/2026: bảng kết luận Huy động vốn và Thanh khoản Mạnh, +1 bậc. Xác nhận trong hội thoại chỉ được lưu cho cấu phần này và kỳ 2026-Q2; không dùng lại toàn bộ bảng chấm, số CAR cũ hoặc bậc AA+ làm kết quả mặc định.
- Techcombank, Chỉ số nổi bật, bảng quý II/2026: https://techcombank.com/nha-dau-tu/thong-tin-tai-chinh/chi-so-noi-bat . LDR 80,1%, vốn ngắn hạn cho vay trung dài hạn 27,8%, cùng phạm vi ngân hàng riêng lẻ theo chú thích (2). Chi phí vốn quý II 4,8%, quý I 4,2%. Đối chiếu ngày 03/11/2026.

## Thứ tự ưu tiên và giới hạn

1. Đánh giá nhập riêng / phiếu đã lưu tiếp tục được ưu tiên.
2. Cấu phần được chủ mô hình xác nhận áp đúng mã và kỳ, có nguồn và lý do. Không tự chuyển sang ngân hàng khác hoặc kỳ sau. Ngoại lệ +1 phải được xác nhận riêng.
3. Khi chỉ có dữ liệu BCTC, CASA vẫn là tín hiệu nguồn huy động. Thanh khoản Phù Hợp được ghi rõ là giả định trung tính trong kết quả ước tính có điều kiện; không phải kết luận thẩm định hay kết quả stress test. Thiếu đầu vào cơ bản vẫn chặn tổng hợp bậc.
4. LDR công bố và tỷ số BCTC lưu riêng, không ghép hai cơ sở trong biểu đồ hoặc bình quân peer. Không lấy số kỳ sau điền vào kỳ trước.
5. Mức Mạnh của TCB là nhận định chuyên gia do người dùng xác nhận; chưa có kiểm định dòng tiền stress độc lập. CAR chính xác 14,95% được giữ nguyên, không làm tròn lên 15% để thay bậc vốn.

## Kết quả tính lại TCB

| Nội dung | Trước | Sau |
|---|---|---|
| Huy động / Thanh khoản | Mạnh / Yếu | Mạnh / Mạnh |
| Tác động cấu phần | -2 bậc | +1 bậc |
| SACP | BBB | A |
| Hiệu chỉnh thang trong nước | +5 bậc | +2 bậc |
| ICR trong khung người dùng chọn | AA- | AA- |

Các cấu phần còn lại vẫn là Hồ sơ kinh doanh Trung Bình (-1), Vốn và lợi nhuận Phù Hợp (0), Vị thế rủi ro Mạnh (+1). Bậc A được tính từ Anchor A- và tổng điều chỉnh nội tại +1. Hỗ trợ bên ngoài 0 bậc. Hiệu chỉnh trong nước được trình bày riêng, không ghi thành hỗ trợ Nhà nước hay ý kiến CRA.

## Bố cục và phân tích

App gom các chỉ tiêu theo bốn cấu phần, cùng phần nhận định sử dụng trong Word. Bảng cấu phần chính được rút gọn; chi tiết phép tính ở phần mở rộng/phụ lục. Bổ sung phân tích lợi thế CASA, khoảng chênh tài trợ, LDR riêng lẻ và áp lực chi phí vốn của TCB. Giữ tông xanh, lịch sử BCTC năm 2021–2025 với đường bình quân peer và biểu đồ peer quý gần nhất đặt dưới. Tên tải từ app, trang bìa, header/footer giữ quy ước ngày xuất, không ghi phiên bản trong báo cáo.

Các tệp cấu phần và tỷ lệ công bố được đưa vào dấu vân tay dữ liệu để báo cáo tải lại khi dữ liệu thay đổi. Gói không ghi đè phiếu thẩm định riêng hoặc dữ liệu nhập tay bảo hiểm.
