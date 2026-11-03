# Hiệu chỉnh xếp hạng ngân hàng trong nước

Ngày cấu hình: 03/11/2026. Người yêu cầu: Lê Hoàng Quân.

## Vấn đề và kết quả

Bản trước lấy bảng chấm AA+ từ báo cáo mẫu TCB cho riêng TCB, trong khi VCB và phần lớn ngân hàng dùng quy tắc định lượng tự động. Hai nguồn đánh giá không đồng nhất. Bản này bỏ ưu tiên bảng mẫu trong chế độ hiệu chỉnh; bảng mẫu vẫn được lưu nguyên và có thể chạy lại khi tắt chế độ này. Phiếu thẩm định nhập riêng vẫn được ưu tiên.

Khung mới là **hiệu chỉnh mức đích theo nhóm do chủ mô hình lựa chọn**, không phải một phương pháp đã được kiểm định để chứng minh các ngân hàng phải có những bậc này. Điểm tài chính gốc vẫn thể hiện cả điểm mạnh và điểm yếu; không thay CAR hoặc đánh giá cấu phần để tạo ra bậc mong muốn.

| Nhóm | Quy tắc |
| --- | --- |
| VCB, BID, CTG, Agribank | Mức đích AAA |
| TCB, VPB, ACB | Mức đích AA- |
| ABB | Mức đích A- |
| OCB, KLB, STB | Trần A-; giữ các bậc thấp hơn theo bảng điểm gốc |
| Các ngân hàng khác | Giữ cơ chế tính theo đầu vào hiện có; không gán thêm bậc từ bảng tham khảo |

“CTC” trong yêu cầu được hiểu là CTG (VietinBank), BIDV tương ứng BID. Không đổi định danh mã CTC trong danh mục doanh nghiệp. Agribank chưa có BCTC trong bộ dữ liệu, nên AAA chỉ xuất hiện trong khung tham chiếu, không tạo SACP/ICR tính từ dữ liệu trống và không thêm Agribank vào peer niêm yết.

## Trình tự tính

1. Tính Anchor, từng cấu phần, SACP và hỗ trợ bên ngoài từ bộ tính gốc.
2. Giữ bậc trước hiệu chỉnh cùng toàn bộ đầu vào và bảng điểm gốc trong kết quả kiểm tra.
3. Áp mức đích hoặc trần theo cấu hình; số notch hiệu chỉnh là khoảng cách giữa hai bậc trong cùng thang nội địa.
4. Hiển thị riêng bậc trước hiệu chỉnh, notch hiệu chỉnh và ICR sau hiệu chỉnh trên ứng dụng và Word/PDF. Không ghi notch hiệu chỉnh vào hỗ trợ Nhà nước.

Không áp mức đích khi thiếu đầu vào cốt lõi, có giới hạn vốn, sự kiện vỡ nợ/kiểm soát đặc biệt được ghi nhận, hoặc CAR dưới 8% theo ngưỡng cảnh báo của mô hình hiện tại. Phiếu nhập riêng kể cả phiếu từng phần được ưu tiên. Ngưỡng cảnh báo này không phải xác nhận tuân thủ mọi quy định pháp luật.

Mức đích sẽ giữ nguyên khi số liệu biến động trong vùng đủ điều kiện. Đây là giới hạn có chủ ý của cơ chế hiệu chỉnh; không được trình bày như một kết quả tự do thay đổi hoàn toàn theo tài chính. Bảng độ nhạy tác động lên **bậc trước hiệu chỉnh**; chủ mô hình phải xem xét lại nhóm khi hồ sơ rủi ro thay đổi. Không suy diễn AAA đồng nghĩa bảo lãnh nghĩa vụ nợ của Nhà nước.

## Tham khảo trong nước

Chỉ lưu thang xếp hạng tổ chức phát hành trong nước, tách khỏi trái phiếu và các thang quốc tế. Các mục đã rút/ngừng vẫn giữ trạng thái và ngày, không coi là mức đang còn hiệu lực. Không chép triển vọng CRA vào triển vọng của mô hình.

- VCB: đã đối chiếu công bố của ngân hàng về mức FiinRatings AAA ngày 11/12/2025: https://www.vietcombank.com.vn/vi-VN/Trang-thong-tin-dien-tu/Articles/2026/01/12/20260112_VCB_Truyen-thong-XHTN-trai-phieu-ben-vung
- TCB: trang nhà đầu tư hiển thị FiinRatings AA-: https://techcombank.com/nha-dau-tu
- ACB: đã đối chiếu công bố lần đầu FiinRatings AA+ ngày 10/09/2024: https://cms.fiinratings.vn/UploadFile/10-09-2024/%5BVN%5D_FiinRatings_ACB_PA_Initial_Issuer_Credit_Rating_10092024.pdf . Mức AA- của app là yêu cầu hiệu chỉnh nội bộ; không được gán cho FiinRatings. Tham chiếu tháng 09/2026 trong bảng người dùng chưa được kiểm tra lại tại lần cập nhật này.
- Các dòng còn lại lưu theo bảng người dùng cung cấp, kèm loại nguồn USER_PROVIDED; chưa xác nhận lại tất cả các công bố CRA gốc.

## Cấu hình và kiểm tra

`config/bank_domestic_calibration.json` chứa các nhóm và mức đích/trần. `config/bank_domestic_benchmarks.json` chứa tham khảo CRA riêng. Thay đổi một trong hai tệp làm thay đổi mã nhận diện báo cáo tải xuống, tránh dùng báo cáo đã tạo với cấu hình cũ.

Có thể bỏ chọn “Áp dụng khung hiệu chỉnh xếp hạng trong nước” trên tab XHTN, hoặc đặt Enabled=false trong cấu hình. `rate_company(ticker, {'UseDomesticCalibration': False})` chạy chế độ trước hiệu chỉnh; strict engine và bảng mẫu TCB không bị viết lại.

Chạy `python scripts/check_bank_domestic_rating.py` để kiểm tra phép tính; `python scripts/check_report_scores.py --tickers VCB BID CTG TCB VPB ACB ABB OCB KLB STB` để xem toàn bộ chuỗi kết quả.

Gói phát hành không chứa `config/bank_rating_assessments.json` và không ghi đè `config/insurance_metric_inputs.csv`. PASS trong các công cụ chỉ xác nhận kiểm tra phần mềm, không xác nhận hiệu lực hoặc độ chính xác tín dụng của các bậc hiệu chỉnh.
