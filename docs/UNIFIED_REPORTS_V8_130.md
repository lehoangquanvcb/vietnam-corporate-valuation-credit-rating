# Báo cáo thống nhất bốn lĩnh vực — V8.130.0

Báo cáo Word của mọi mã dùng chung bộ dựng tại `scripts/professional_report.py`. Cấu trúc phân tích chọn theo loại hình doanh nghiệp, không theo danh sách mã mẫu. PDF được chuyển từ cùng bản Word. Các báo cáo đã xuất trước khi cập nhật cần được tạo lại.

## Cấu trúc và nội dung

Tông xanh lá; bảng kết quả xếp hạng, luận điểm, điểm mạnh/rủi ro, lịch sử tài chính năm và các chương theo phương pháp tương ứng:

| Loại hình | Phương pháp tham chiếu | Trọng tâm |
| --- | --- | --- |
| Ngân hàng | Phương pháp XHTN Ngân hàng 2026 | Kinh doanh; vốn và lợi nhuận; rủi ro; nguồn vốn và thanh khoản; điều chỉnh và hỗ trợ |
| Chứng khoán | Phương pháp XHTN Công ty Chứng khoán 2025 | Kinh doanh; vốn và lợi nhuận; rủi ro danh mục; nguồn vốn và thanh khoản; điều chỉnh và hỗ trợ |
| Doanh nghiệp phi tài chính | Phương pháp XHTN doanh nghiệp ngày 17/07/2025 | Kinh doanh; sinh lời; dòng tiền và đòn bẩy; thanh khoản; quản trị và điều chỉnh |
| Bảo hiểm | Phương pháp XHTN Công ty Bảo hiểm Phi Nhân thọ 2025 | Kinh doanh và khai thác; vốn và lợi nhuận; rủi ro; linh hoạt tài chính; thanh khoản; điều chỉnh và hỗ trợ |

Mỗi chỉ tiêu có bằng chứng được phân tích bằng hai biểu đồ xếp dọc:

1. Trên: năm tài chính đã kết thúc gần nhất và bốn năm liền trước, cùng đường bình quân peer từng năm. Số dư dùng cuối năm; doanh thu, lợi nhuận và dòng tiền dùng cả năm; tỷ số dùng đúng cơ sở của nguồn.
2. Dưới: doanh nghiệp và các peer tại cùng quý gần nhất. Dòng thu nhập dùng quý riêng lẻ; số dư dùng cuối quý; tỷ số trả nợ dùng 12 tháng kết thúc tại quý đó khi công thức yêu cầu.

Phân tích nêu mức biến động, chênh lệch với peer và liên hệ giữa các chỉ tiêu: tăng trưởng với khả năng sinh lời, vốn với tài sản, tiền với lợi nhuận, nợ với khả năng tạo thu nhập, bồi thường với chi phí khai thác. Các yếu tố định tính có hồ sơ được dùng trong chương tương ứng; thiếu hồ sơ được ghi ngắn gọn ở phần cuối.

Bình quân peer loại chính doanh nghiệp, yêu cầu ít nhất năm peer có số liệu tương thích. Khoảng trống và thay đổi phạm vi dữ liệu bảo hiểm được giữ nguyên; không điền số 0 hoặc lấy số 6 tháng thay số năm. Chỉ tiêu không có bằng chứng được liệt kê ở phụ lục, không tạo biểu đồ giả.

## Ba cụm từ áp dụng trên đầu ra

- Báo cáo Xếp hạng tín nhiệm không chỉ định
- Tài liệu này chỉ phục vụ mục đích nghiên cứu
- Tài liệu này không thay thế Báo cáo xếp hạng tín nhiệm thông thường

## Kết quả xếp hạng

Bảng kết quả tiếp tục lấy kết quả của động cơ xếp hạng và hồ sơ đánh giá hiện có. Không suy ra bậc cuối cùng chỉ từ tỷ lệ chỉ tiêu có dữ liệu. Tham chiếu TCB trong gói trước chỉ áp dụng đúng TCB và kỳ tham chiếu; không sao chép bậc cho mã khác. Gói cập nhật không chứa file nhập tay `insurance_metric_inputs.csv` hoặc `bank_rating_assessments.json`, nhằm giữ các đánh giá của người dùng.

BVH/PVI vẫn thuộc nhóm peer phi nhân thọ theo cấu hình đã yêu cầu; phạm vi BCTC hợp nhất được giữ để tránh coi tỷ số hợp nhất là tỷ số nghiệp vụ phi nhân thọ riêng biệt.

## Kiểm chứng bản phát hành

- Chạy thật: 233 bài kiểm thử và 22 kiểm tra con đạt.
- Kiểm tra định tuyến 1.754 mã: 28 ngân hàng, 15 chứng khoán, 12 bảo hiểm, 1.699 doanh nghiệp phi tài chính.
- Kiểm tra gói bằng chứng 75 mã, với 2.049 chỉ tiêu có dữ liệu: toàn bộ ngân hàng, chứng khoán, bảo hiểm trong danh mục và 20 doanh nghiệp phi tài chính.
- Chạy giao diện Streamlit và xuất Word cho TCB, SSI, FPT, ABI.
- Kiểm tra trực quan toàn bộ 122 trang của bốn bản Word mẫu, gồm 222 biểu đồ. Không phát hiện trang trắng hoặc nội dung tràn ngang.

Đây là phạm vi kiểm thử phần mềm; không có nghĩa đã xác minh nguồn BCTC, xuất và đọc từng báo cáo của cả 1.754 mã, hoặc hoàn tất thẩm định xếp hạng cho mọi doanh nghiệp.

Chạy kiểm tra tại project:

```bat
python scripts\check_report_runtime.py
python scripts\check_report_runtime.py --all --output report_runtime_all.json
python scripts\check_insurance_runtime.py
python -m pytest -q tests
```

Lệnh `--all` kiểm tra bằng chứng cho mọi mã trong dữ liệu cục bộ, có thể chạy lâu. Không tải mới dữ liệu từ mạng. Chi tiết kết quả phát hành: `docs/report_validation_v8_130.json`.
