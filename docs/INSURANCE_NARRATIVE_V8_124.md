# Phân tích và kết luận bảo hiểm V8.124

Bản trước trình bày chuỗi số liệu và đối chiếu peer nhưng nhiều đoạn hàm ý chỉ là hướng dẫn chung. Bản này tạo lập luận từ số của từng doanh nghiệp và tổng hợp thành kết luận tài chính. Màn hình và Word dùng cùng gói bằng chứng.

## Cách trình bày

Bố cục tham khảo báo cáo VDS do người dùng cung cấp: trang bìa, kết quả và luận điểm, điểm mạnh/rủi ro, tổng quan, vĩ mô/ngành, hồ sơ kinh doanh, sinh lời, vốn, vị thế rủi ro, thanh khoản, kết luận, quản trị, hỗ trợ bên ngoài, độ nhạy và tổng kết cấu phần. Giữ A4, Lato, các dải tiêu đề xanh và biểu đồ cặp.

Mỗi chỉ tiêu có nguồn được trình bày theo chuỗi:

1. Biểu đồ và bảng các năm gần nhất theo cơ sở lựa chọn.
2. Biểu đồ đối chiếu đúng quý gần nhất của doanh nghiệp.
3. Diễn biến toàn chuỗi và thay đổi năm cuối.
4. Bình quân, trung vị và khoảng cách với peer cùng kỳ/cơ sở; mẫu nhỏ đối chiếu trực tiếp.
5. Lập luận nối chỉ tiêu với lợi nhuận, vốn, nghĩa vụ hoặc rủi ro liên quan.
6. Kết luận riêng của chỉ tiêu.

Mỗi nhóm có nhận định tổng hợp và kết luận. Cuối báo cáo có kết luận toàn hồ sơ và điều kiện cải thiện/gây sức ép xuất phát từ số liệu hiện tại. Chi tiết số peer và lý do loại được đưa vào phụ lục để thân báo cáo tập trung vào lập luận.

## Cách vận dụng báo cáo bảo hiểm tham khảo

Báo cáo thực tế do người dùng cung cấp được dùng để xây dựng cách nối bằng chứng với ý nghĩa tín dụng:

| Nội dung phương pháp | Lập luận từ số liệu của mã đang chọn |
| --- | --- |
| Quy mô và vị thế | Tăng phí/doanh thu so với tăng lợi nhuận và vốn; không lấy tổng phí mẫu niêm yết làm thị phần toàn ngành |
| Hiệu quả nghiệp vụ | Phân rã thay đổi tỷ lệ kết hợp thành bồi thường và chi phí; chỉ quy nguyên nhân số học khi tổng cấu phần khớp |
| Chất lượng lợi nhuận | Đối chiếu lợi nhuận hoạt động bảo hiểm với lợi nhuận ròng; phân biệt thu nhập đầu tư với lợi nhuận đầu tư ròng |
| Vốn và dự phòng | Đối chiếu tăng tài sản với tăng vốn, thay đổi vốn/tài sản; không coi dự phòng là nợ vay hoặc số dự phòng lớn là đủ dự phòng |
| Vị thế rủi ro | Nợ vay, nợ đến hạn, tập trung đầu tư và ngoại tệ theo dữ liệu được thẩm định |
| Thanh khoản | Tài sản sau khấu trừ so với nghĩa vụ hợp đồng; biên thanh toán là phép đo riêng |
| Quản trị và hỗ trợ | Đưa lập luận và nguồn đã nhập vào đúng cấu phần; không lấy lợi nhuận thay bằng chứng quản trị |

Không sao chép số liệu, đánh giá quản trị, kế hoạch vốn, hỗ trợ cổ đông hoặc bậc tín nhiệm của công ty trong báo cáo mẫu sang mã khác. Bản cập nhật không thay ma trận XHTN 2025, không cấp điểm hoặc triển vọng mặc định.

## Giới hạn bằng chứng được kiểm soát

- Không tính tăng trưởng qua năm thiếu, khác cơ sở hoặc điểm đứt gãy nguồn.
- Không nối chỉ tiêu quý khác nhau để giải thích nguyên nhân.
- Phân biệt kết quả âm, giảm lỗ, hòa vốn và có lãi; không coi giảm lỗ là lợi nhuận dương.
- Khi bình quân và trung vị cho vị trí khác nhau, báo cáo giải thích độ phân tán của mẫu.
- Chỉ tiêu tài chính chung giữ nhóm so sánh bảo hiểm rộng; kết luận ưu thế sinh lời trong bảng điểm mạnh/rủi ro dùng phạm vi BCTC tương đồng.
- BVH/PVI vẫn thuộc nhóm so sánh Phi nhân thọ theo cấu hình. Phạm vi BCTC hợp nhất vẫn được giữ nguyên; không suy kết quả hợp nhất thành kết quả riêng của pháp nhân phi nhân thọ.
- Thiếu thanh khoản hoặc biên thanh toán được diễn giải là thiếu bằng chứng, không thành kết luận mất khả năng chi trả.
- P/B, P/E không tạo điểm mạnh tín nhiệm hoặc khuyến nghị mua cổ phiếu.

## Sử dụng

Ghi đè các tệp của gói cập nhật vào thư mục project gốc. Không có thư mục `UPDATE` trung gian. Mã mới hiển thị `V8.124.0-INSURANCE-NARRATIVE`.

Chạy `python scripts/check_insurance_runtime.py`, mở một mã bảo hiểm và xuất lại Word. Tệp Word đã tải trước đó không tự thay đổi. Báo cáo mẫu kèm gói dùng dữ liệu đã có trong project đến 2026-Q2, lịch sử FY 2021–2025; không phải lần tải mới từ Vnstock.

Kiểm thử: `python -m unittest discover -s tests -v`. Các ca mới kiểm tra chuyển lãi/lỗ, cấu phần tỷ lệ kết hợp, đòn bẩy, mốc thanh khoản, khác kỳ, thiếu dữ liệu, đứt gãy nguồn, mẫu peer phân tán và phạm vi BVH.
