# Đối chiếu phương pháp bảo hiểm phi nhân thọ 2025

Phiên bản triển khai: **8.119.0**. Tài liệu đối chiếu là bản người dùng cung cấp
`4. Phương pháp XHTN Công ty Bảo hiểm Phi Nhân thọ 2025(1).docx`, cập nhật
20.01.2025. Đã đọc toàn văn, gồm sơ đồ cấu trúc và 18 bảng đánh số.

## Phạm vi và cách trình bày

34 chỉ tiêu định lượng được tổ chức thành sáu nhóm. Mỗi chỉ tiêu dùng một gói
dữ liệu chung cho UI và Word: lịch sử 3–5 năm, biểu đồ doanh nghiệp; dữ liệu,
biểu đồ doanh nghiệp và peer đúng quý gần nhất; nhận xét lịch sử, nhận xét peer,
công thức và liên hệ phương pháp. Mặc định lịch sử bảo hiểm là cả năm; có thể
chọn lũy kế cùng kỳ, quý cùng kỳ hoặc TTM. So sánh ngang vẫn dùng quý riêng lẻ.

Số dư là cuối kỳ. ROE/ROA/PB/PE là tỷ số nguồn tại kỳ báo cáo, không đổi thành
tỷ suất quý. Dự phòng/phí trong so sánh quý dùng phí thuần TTM và ghi rõ. Không
nội suy năm thiếu, không thay quý thiếu bằng quý cũ. Peer loại doanh nghiệp đang
phân tích; bình quân/trung vị cần ít nhất 5 quan sát cùng cơ sở.

Registry phân biệt phi nhân thọ trực tiếp, tái bảo hiểm và tập đoàn. ABI có
7 peer trực tiếp trong bộ dữ liệu. BVH/PVI và PRE/VNR có mẫu cùng loại nhỏ; vẫn
so sánh từng doanh nghiệp nhưng không suy ra trung bình ngành. Cơ cấu hai tập
đoàn vẫn khác nhau. Không gán phương pháp phi nhân thọ cho BCTC tập đoàn hoặc
tái bảo hiểm chỉ bằng cách đánh dấu xác nhận.

## Đối chiếu từng bảng

| Tài liệu | Triển khai và giới hạn |
| --- | --- |
| Sơ đồ cấu trúc | Vĩ mô/ngành, kinh doanh, tài chính → Anchor; quản trị/thanh khoản/điều chỉnh → SCA; hỗ trợ ròng → ICR. |
| Bảng 01 | Đối chiếu 36 ô; ba ô rủi ro ngành 1/2/3 và kinh doanh 6 cần chọn 6 hoặc 7, không mặc định 6. |
| Bảng 02 | Đối chiếu 70 ô. Giữ N/A và lựa chọn nhiều bậc; không tự chọn Anchor tốt nhất. |
| Bảng 03 | Phiếu bằng chứng vĩ mô: tăng trưởng, lạm phát, tín dụng, nợ xấu, lãi suất/tỷ giá, trái phiếu, thể chế. Không tạo dữ liệu vĩ mô hoặc điểm mặc định. |
| Bảng 04–05 | Hướng dẫn ROE kỳ vọng >10% / 4–10% / <4%; ROS và kết hợp; yêu cầu mẫu ROE tối thiểu 60% số doanh nghiệp. Hàm điểm ngành tính trung bình 5 yếu tố khi có đủ đầu vào. Không dùng mẫu 8 cổ phiếu thay toàn ngành. |
| Bảng 06–07 | Phiếu đánh giá rào cản pháp lý/hoạt động và phí thực năm hiện tại cộng hai năm dự báo. Chuỗi quá khứ không thay dự báo. |
| Bảng 08 | Hàm ma trận thể chế 1–5 và cộng 1 điểm nếu yếu về chuẩn quản trị/minh bạch; tổng hợp vĩ mô/ngành vẫn là kết luận chuyên viên. |
| Bảng 09–10 | Sáu yếu tố kinh doanh có đánh giá, lập luận và nguồn. Hiệu quả tiêu cực giới hạn điểm kinh doanh không tốt hơn 3; cảnh báo vị thế/đa dạng tích cực khi hiệu quả yếu. Không tự gán trọng số cho các mô tả định tính. |
| Bảng 11 | Vốn/lợi nhuận là điểm đầu. Điều chỉnh tài chính nhập có lập luận; cùng mức vị thế và linh hoạt thì kiểm tra đúng −1/0/+1/+2. Mức vị thế 5 đòi hỏi +3 hoặc xấu hơn. Hai yếu tố khác mức chưa có phép gộp duy nhất trong tài liệu, không tự đặt công thức. Áp giới hạn chất lượng tài sản; rủi ro vốn pháp định đáng kể → tài chính 10, SCA tối đa B+. |
| Bảng 12 | Vốn thực góp = vốn điều lệ + thặng dư. Cần vốn pháp định đúng giấy phép và dự báo hai năm. Các giá trị đúng biên 1; 1,5; 2; 2,5; 3; 3,5; 4 yêu cầu chuyên viên xác định, không tự xử lý cách diễn đạt chồng lấn. Tính điều chỉnh mô hình vốn theo khoảng điểm được ghi trong nguồn. |
| Bảng 13 | Phiếu rủi ro tỷ giá, đầu tư, đa dạng danh mục và rủi ro khác. Giữ điểm vị thế 1–5 do chuyên viên chọn vì mô tả mức 4/5 có phần trùng về trọng yếu. |
| Bảng 14–15 | 18 tiêu chí quản trị/chính sách tài chính trong phiếu bằng chứng; mức tổng hợp do chuyên viên chọn theo hướng dẫn. Không coi giá trị chưa nhập là trung lập. |
| Bảng 16 | Ma trận 4×4 kết hợp quản trị và chính sách tài chính. “Khá” của bảng này được nối vào cột “Khá mạnh” Bảng 17. |
| Bảng 17 | Đối chiếu đủ 90 ô. Áp trần BB khi cả hai mức yếu hoặc đánh giá gây hại trọng yếu. Anchor dưới B− không có hàng trong bảng: dừng chờ xử lý, không ngoại suy. |
| Bảng 18 | Tính chỉ số tài sản thanh khoản sau haircut/nghĩa vụ bảo hiểm. Chỉ số >2,2; 1–2,2; <1 khác với đánh giá thanh khoản tổng thể 1–5. Bảng có trường hợp tiêu cực trùng mức 3/4 nên mức tổng thể và tác động notch cần quyết định có bằng chứng. |

Các điều chỉnh khác thông thường và điều chỉnh so sánh chỉ ±1. Ngoại lệ hạ hơn
một bậc chỉ mở khi có thu hồi giấy phép, nguồn chứng minh và quyết định Hội đồng.
Các giới hạn SCA được áp sau điều chỉnh để không bị vô hiệu hóa bởi cộng bậc.
Phương pháp hỗ trợ tập đoàn/Chính phủ được tài liệu dẫn chiếu nhưng không nằm
trong file này: phần mềm yêu cầu nguồn hồ sơ và hỗ trợ ròng đã loại trùng; không
tự cộng hai mức hỗ trợ để nâng hạng.

Phiếu có **43 yếu tố bằng chứng**, ngoài các quyết định tổng hợp. Nhập đủ số
không đồng nghĩa đã thẩm định. ICR mô phỏng chỉ hình thành khi có đánh giá,
lập luận, nguồn và các quyết định bắt buộc. Đây không phải xác nhận độc lập
chất lượng bằng chứng hoặc thay thế Hội đồng XHTN.

## Quy ước tỷ lệ khai thác

Các dòng chi phí trong raw có dấu âm. Giữ dấu hoàn nhập, không dùng trị tuyệt
đối để biến khoản hoàn nhập thành chi phí.

- Tỷ lệ bồi thường = −`IS_TOTAL_INSURANCE_CLAIMS_EXPENSES` / phí bảo hiểm thuần.
- Chi phí khai thác thuần = −tổng chi phí kinh doanh bảo hiểm + chi phí bồi thường
  có dấu − chi phí quản lý bảo hiểm có dấu − thu hoa hồng và thu khác.
- Tỷ lệ chi phí = chi phí khai thác thuần / phí bảo hiểm thuần.
- Tỷ lệ kết hợp = tỷ lệ bồi thường + tỷ lệ chi phí.

Định nghĩa dùng chung là `NET_EARNED_CLAIMS_OPS_ADMIN_OTHER_V1`. Đây là quy ước
tính từ BCTC, không tuyên bố là một công thức chi tiết được tài liệu 2025 quy
định. Chuyên viên phải đối chiếu phạm vi thuyết minh trước khi dùng để chấm điểm.
Kiểm thử đối chiếu `(1 − tỷ lệ kết hợp) × phí thuần` với lợi nhuận hoạt động
bảo hiểm của 8 công ty trực tiếp trong dữ liệu quý 2026-Q2.

Phương pháp gốc có xét nợ vay/VCSH và EBITDA/lãi vay. Bản mới dùng nợ vay đúng
dòng, đồng thời cho nhập EBITDA đã đối chiếu và lãi vay cùng kỳ; không sử dụng
EBITDA sai của nguồn hoặc hệ số nợ/EBITDA doanh nghiệp thông thường. Lãi vay
bằng 0 trả “không áp dụng”, không tạo vô cực hoặc mặc định điểm trung lập.

## Dữ liệu còn phải bổ sung

Thuyết minh vốn pháp định, biên thanh toán, tài sản thanh khoản phân theo hạng
và kỳ hạn, nghĩa vụ hợp đồng bảo hiểm, cấu trúc sản phẩm, thị phần toàn ngành,
lệch ngoại tệ, tập trung đầu tư, đáo hạn nợ và dự báo chưa đầy đủ trong ZIP.
Các ô thiếu vẫn được trình bày trong cả hai phần lịch sử/peer, nêu rõ lý do.
Không thay nghĩa vụ hợp đồng bằng tổng nợ phải trả hoặc riêng dự phòng nghiệp vụ.

Nhập bổ sung qua `config/insurance_metric_inputs.csv`; danh mục và hướng dẫn
ở `insurance_input_dictionary.csv` và `INSURANCE_INPUT_GUIDE.md`. Mỗi bản ghi
có Ticker, Period, Metric, Value, Basis, Source, ReviewedBy, Scope, Definition.
Không kèm số liệu giả trong mẫu. Dữ liệu này được đọc lại khi tệp thay đổi.

Nguồn phân loại pháp nhân nằm trong `config/insurance_entities.csv`; ngày rà
soát 19.10.2026. Giá trị tài chính vẫn là dữ liệu project đã cung cấp, không
phải một lần cập nhật trực tuyến hoặc kiểm toán BCTC.
