# Biểu đồ và phân tích bảo hiểm V8.125

Áp dụng cho trang phân tích trên Streamlit và báo cáo Word phân tích/XHTN bảo hiểm. Tham khảo bố cục và cách liên kết xu hướng, peer, hàm ý trong hai báo cáo HPG do người dùng cung cấp. Giữ nội dung chuyên ngành bảo hiểm đã đối chiếu báo cáo PAC; không sao chép nhận định, số liệu hay bậc tín nhiệm HPG/PAC.

Mỗi chỉ tiêu có hai biểu đồ riêng theo chiều dọc. Biểu đồ lịch sử ở trên, có đường doanh nghiệp và đường bình quân peer. Bảng phía dưới chứa số doanh nghiệp, bình quân và số peer từng mốc; nhận xét lịch sử nêu vị trí/khoảng cách với peer. Biểu đồ cột so sánh đúng quý gần nhất nằm phía dưới, tiếp theo là nhận xét so sánh, liên hệ các chỉ tiêu và kết luận.

Bình quân lịch sử là trung bình số học không gia quyền, loại doanh nghiệp đang phân tích. Dùng danh mục peer tự chọn hiện tại, tính lại tại đúng kỳ lịch sử của doanh nghiệp và đúng cơ sở FY/QUARTER/YTD/TTM đang chọn. Không thay bằng quý gần nhất của riêng peer, không lấp thiếu bằng 0, không nội suy. Giữ giá trị âm hợp lệ. Tỷ số được lấy bình quân từ tỷ số từng peer, không chia tổng tử số cho tổng mẫu số.

Chỉ tiêu chung đối chiếu toàn nhóm bảo hiểm; chỉ tiêu nghiệp vụ dùng nhóm cấu hình. Quy tắc áp dụng theo phạm vi BCTC vẫn được giữ, ví dụ không đưa tỷ lệ kết hợp từ BCTC hợp nhất BVH/PVI vào mẫu. Với mẫu lịch sử nhỏ, vẫn hiển thị số bình quân kèm N để đối chiếu; không gọi đó là đại diện toàn ngành. Ngưỡng công bố bình quân/trung vị trong nhận xét quý vẫn là 5 peer như trước.

Đường lịch sử không nối qua mốc thiếu, thay đổi thành phần mẫu/cơ sở hoặc đứt gãy nguồn dự phòng. Phần nhận xét không suy luận xu hướng khoảng cách xuyên qua các điểm này. Phụ lục Word có danh sách peer từng mốc; giao diện có bảng truy xuất nguồn, giá trị, trạng thái và lý do loại.

Gói tích lũy từ V8.120 đến V8.125, các tệp mã nguồn ở ngay thư mục gốc ZIP. Build: V8.125.0-INSURANCE-HISTORY-PEERS. Không cần thêm thư viện so với ứng dụng hiện tại.
