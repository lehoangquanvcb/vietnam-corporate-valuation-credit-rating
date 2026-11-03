# V8.133 — giữ kết quả cấu phần khi chưa đủ căn cứ tổng hợp

Trước bản sửa, `_financial_institution` trả về ngay tại cấu phần đầu tiên thiếu dữ liệu. Với ABB, thiếu CAR đúng kỳ làm mất `Factors`/`FactorNotches` đã có và bỏ qua bước đánh giá huy động/thanh khoản. Phiếu nhập tay dùng nhãn “Chưa xác định” khiến người dùng hiểu rằng toàn bộ phân tích chưa được thực hiện.

Bộ tính hiện thu thập mọi cấu phần độc lập trước khi kiểm tra khả năng tổng hợp. Mỗi phần thiếu có khóa và lý do riêng trong `MissingEvidence`; không tạo notch trung tính cho phần thiếu. `InternalNotches`, SACP và ICR chưa được tổng hợp khi còn thiếu đầu vào. Anchor phương pháp, các điểm đã tính và đánh giá hỗ trợ (kể cả trạng thái giả định) vẫn được giữ để đối chiếu.

Bảng chấm đã lưu, kết luận nhập riêng, notch riêng và giới hạn vốn pháp định được giữ khi bổ sung phần còn thiếu bằng tín hiệu tự động. Ước tính không được ghi thành đánh giá đã thẩm định. Không thay đổi ngưỡng CAR, ma trận huy động/thanh khoản hay quy tắc xếp hạng của các ngành khác.

Giao diện dùng tùy chọn chung cho bốn ngành để mở phiếu nhập riêng; bảng điểm tự động nằm trước phần phân tích chi tiết. Tắt tùy chọn trở về kết quả tự động hoặc bảng chấm đã lưu trên đĩa. Nguồn dữ liệu, bảng chấm lưu trên đĩa và phiếu bảo hiểm người dùng không bị ghi đè bởi gói cập nhật.

Kiểm tra hồi quy trong `tests/test_partial_factor_scores.py` bao gồm thiếu CAR, thiếu cấu phần đầu tiên, nhiều phần thiếu đồng thời, bảo toàn huy động khi thiếu thanh khoản, bật/tắt kết luận vốn riêng, kế thừa notch/giới hạn, CAR cũ và bảng điểm Word. Biên bản chạy thực tế được lưu cùng bản phát hành; không suy từ kiểm tra định tuyến ra việc mọi mã đều có bậc.
