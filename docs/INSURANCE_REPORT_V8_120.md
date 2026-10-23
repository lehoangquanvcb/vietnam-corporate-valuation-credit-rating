# Bản sửa báo cáo bảo hiểm V8.120.0

Bản cập nhật cho V8.119.0 (đã có dữ liệu bảo hiểm trên Git, commit người dùng cung cấp: 674a8de).

## Vấn đề được sửa

- Tách ngoài phạm vi phương pháp, ô ma trận không có bậc, hồ sơ chưa đủ và kết quả mô phỏng.
- BVH/PVI là tập đoàn, PRE/VNR là tái bảo hiểm: không hiển thị 65 đầu vào phi nhân thọ còn trống hoặc mở phiếu không phù hợp. Phân tích tài chính vẫn hoạt động.
- Công ty phi nhân thọ chưa có hồ sơ: một trạng thái tổng hợp; các yếu tố còn thiếu nằm trong mục hồ sơ. Kết quả tính được từ hồ sơ nhập một phần vẫn được giữ.
- Hiển thị độ phủ toàn bộ 34 chỉ tiêu, tách chỉ tiêu có số, thiếu và không áp dụng. Ví dụ BVH có 18/34 chỉ tiêu có số, 11 thiếu, 5 không áp dụng; tỷ lệ trên chỉ tiêu áp dụng là 18/29. Không dùng tỷ lệ này như độ tin cậy XHTN.

## Mẫu Word

Dùng bố cục từ các báo cáo tham chiếu TCB, VDS, HPG: bìa; kết quả/luận điểm; điểm mạnh/rủi ro; tổng quan; vĩ mô; ngành; hồ sơ kinh doanh; sinh lợi; vốn và dự phòng; vị thế rủi ro; thanh khoản; quản trị; hỗ trợ; độ nhạy; tổng kết. Khổ A4, phông Lato, dải mục xanh.

Mỗi chỉ tiêu có dữ liệu gồm chuỗi 3–5 năm theo cơ sở người dùng chọn, biến động từng năm, đối chiếu cùng quý với peer và hàm ý phân tích. Mẫu kèm theo dùng FY 2021–2025 và quý 2026-Q2 từ bộ dữ liệu đã cung cấp. Mẫu nhỏ vẫn đối chiếu trực tiếp từng công ty; không tính bình quân đại diện khi dưới 5 peer. Chỉ tiêu không có số được ghi trong phụ lục cùng lý do, không tạo biểu đồ trống.

## Giới hạn còn lại của dữ liệu và phương pháp

- Phương pháp phi nhân thọ 20.01.2025 không tự mở rộng sang tập đoàn/nhân thọ/tái bảo hiểm. Cần phương pháp đúng loại hình hoặc BCTC riêng đúng phạm vi để chấm XHTN.
- Hồ sơ định tính, dự báo vốn, biên thanh toán, thanh khoản và hỗ trợ chưa được cung cấp thì vẫn phải bổ sung. Các ma trận và điều kiện bằng chứng không được bỏ qua để tạo bậc xếp hạng.
- Phần vĩ mô/ngành sử dụng hồ sơ nghiên cứu trong dữ liệu nếu có; khi chưa có, chỉ nêu cơ chế rủi ro và không gán điểm.
- Dữ liệu nguồn BVH tại `BS_INSURANCE_RESERVES`, 2021-Q4 là 285.420.048.108 đồng, trong khi 2022-Q4 là khoảng 147.665 tỷ đồng. Chưa xác minh nguyên nhân thay đổi phạm vi/ghi nhận hoặc sai lệch nguồn. Giữ nguyên số gốc, đánh dấu bước nhảy hơn 100 lần trong chuỗi dự phòng, ngắt đường nối tại đó và không tính tăng trưởng qua điểm này. Cờ này chỉ phục vụ kiểm tra dữ liệu, không phải ngưỡng chấm tín nhiệm.
- Chưa cập nhật ứng dụng Streamlit Cloud của người dùng. Cần chép bản sửa vào project và push Git.

## Kiểm tra bản cập nhật

Chạy từ thư mục project:

```bat
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_insurance_runtime.py
"C:\Users\HP\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py"
```

Kết quả thực thi trong môi trường kiểm tra: 68 kiểm thử thành công; kiểm tra runtime PASS; AppTest chạy app.py trên màn XHTN cho BVH và ABI không có exception. Bản Word BVH đã được xuất và kiểm tra toàn bộ trang. PASS xác nhận kiểm tra phần mềm trong bộ dữ liệu thử, không xác nhận bậc tín nhiệm hoặc độ chính xác của mọi số liệu nguồn.

Phiên bản hiển thị sau cập nhật: `V8.120.0-INSURANCE-REPORT`. Đây là nhãn phiên bản, không phải lệnh CMD.
