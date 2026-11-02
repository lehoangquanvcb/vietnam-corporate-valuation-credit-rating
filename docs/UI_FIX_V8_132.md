# Tab mặc định và biểu đồ tài chính

Lỗi biểu đồ CAR trống xuất hiện vì bảng lịch sử vẫn có năm dòng tương ứng năm năm, dù tất cả giá trị doanh nghiệp và peer đều thiếu. Điều kiện cũ chỉ đếm số dòng hoặc số trace, nên vẫn hiển thị hai trace không có điểm. Plotly đồng thời tự nhận nhãn năm là trục số và sinh các mốc giữa năm.

`scripts/financial_charts.py` chỉ giữ trace có điểm hữu hạn và đặt trục năm dạng danh mục với đúng các nhãn của chuỗi. Năm thiếu vẫn giữ vị trí; không nối qua khoảng trống, nội suy hoặc đổi ô thiếu thành 0. Giá trị 0 thực có của chỉ tiêu được giữ nguyên. Quy tắc loại số CAR 0 do nguồn trả về tiếp tục nằm trong bộ bằng chứng tài chính.

Giao diện dùng chung hàm này cho ngân hàng, chứng khoán và doanh nghiệp phi tài chính. Biểu đồ bảo hiểm sử dụng cùng bước kiểm tra điểm và nhãn năm, giữ các điểm ngắt do thay đổi phạm vi nguồn. Phần nhận định không gọi các câu mặc định khi doanh nghiệp không có số liệu để phân tích.

ABB trong bộ nguồn hiện tại có CAR 9,87% tại 2025-Q2; chưa có CAR cuối năm 2021–2025 hoặc đúng 2026-Q2. Thông tin kỳ cũ chỉ xuất hiện dưới dạng chú thích có ngày, không được đưa vào so sánh quý gần nhất hoặc dùng thay CAR cuối năm.

Điều hướng mở tab Báo cáo Xếp hạng tín nhiệm trước tiên. Các nhánh nội dung được chọn bằng tên tab, không phụ thuộc vị trí số trong danh sách. Phiên đang mở được chuyển một lần khi nhận bản cập nhật; sau đó giữ lựa chọn của người dùng qua các lần rerun.

Không thay công thức tài chính, nguồn dữ liệu hay bậc xếp hạng. Mẫu Word vẫn giữ các cập nhật của V8.131. Tệp `ui_validation_v8_132.json` ghi kết quả kiểm tra thực thi của bản phát hành này.
