# Xuất báo cáo và bảng điểm tự động

## Phạm vi thay đổi

Mọi mã được định tuyến qua một mẫu Word chung cho ngân hàng, chứng khoán, bảo hiểm và doanh nghiệp phi tài chính. Hai đường CLI, nút Word/PDF của Streamlit và adapter bảo hiểm cùng sử dụng mẫu này.

- Tên Word: `Báo cáo XHTN không chỉ định TCB 02-11-2026.docx`. Ngày lấy tại Việt Nam khi tạo file, không lấy ngày của BCTC.
- Bìa bỏ câu nghiên cứu đứng riêng phía trên; giữ tên báo cáo, doanh nghiệp, ngành, quốc gia, kỳ so sánh, chuỗi năm và tác giả.
- Dòng tác giả: `Tác giả: Lê Hoàng Quân, phát hành ngày 02/11/2026`.
- Header: `TCB - Báo cáo xếp hạng tín nhiệm không chỉ định - ban hành ngày 02/11/2026`.
- Bìa và footer: `Tài liệu này chỉ phục vụ mục đích nghiên cứu không có giá trị thay thế Báo cáo xếp hạng tín nhiệm thông thường`.
- Không đưa phiên bản ứng dụng vào nội dung Word. Phiên bản kỹ thuật vẫn xuất hiện trên giao diện để kiểm tra triển khai.
- Ngành chứng khoán ghi `NGÀNH: CHỨNG KHOÁN`.
- Lịch sử vẫn là 5 năm tài chính hoàn chỉnh; mỗi chỉ tiêu có hai biểu đồ xếp dọc, đường bình quân peer theo từng năm và so sánh peer quý gần nhất.

## Hai loại kết quả được giữ riêng

`scripts/three_methodology_rating.py` và các bộ máy thẩm định gốc vẫn giữ nguyên yêu cầu bằng chứng. Không ghi các giả định vào phiếu thẩm định hoặc dữ liệu nguồn.

`scripts/report_rating.py` cung cấp bậc nghiên cứu tự động cho giao diện và báo cáo. Kết quả có `RatingOrigin=AUTO_RESEARCH`, `RatingStatus=ESTIMATED`, `AssessmentComplete=False`. Báo cáo ghi **Bậc ước tính tự động** ngay cạnh bậc, kèm bảng cấu phần, căn cứ định lượng và các giả định. Không tự gán triển vọng “Ổn định”.

Kết quả ngân hàng/bảo hiểm đã có bảng chấm đầy đủ được ưu tiên. TCB tiếp tục tính lại từ bảng chấm tham chiếu đúng kỳ; không sao chép bậc TCB sang mã khác. Những chỉ tiêu thiếu, phạm vi pháp nhân khác, hoặc ô ma trận không có bậc không được biến thành số 0 hay một bậc cố định.

## Cách tính và phần cần phân biệt với phương pháp gốc

### Ngân hàng

Giữ Anchor A-, bảng CAR, ma trận huy động/thanh khoản và giới hạn vốn theo phương pháp 2026. Khi chưa có bảng chấm đầy đủ, mô hình dùng bằng chứng cùng kỳ, không lấy CAR cũ làm CAR hiện tại. Việc giữ CAR hiện tại cho kịch bản, dùng peer để lượng hóa kinh doanh/rủi ro, CASA/LDR làm tín hiệu nguồn vốn và giả định hỗ trợ 0 bậc được công bố riêng. Các tín hiệu này không thay thế thẩm định định tính hoặc dự báo stress.

### Chứng khoán

Anchor BBB = A- giảm 2 bậc. Vốn/lợi nhuận dùng các benchmark của phương pháp về Nợ/EBITDA, vốn khả dụng và **tổng nợ phải trả/VCSH**, không nhầm với riêng nợ vay/VCSH. Cách gộp lấy mức yếu nhất trong benchmark có dữ liệu là lựa chọn của mô hình tự động. Hồ sơ kinh doanh và vị thế rủi ro dùng điểm peer cùng kỳ; nguồn vốn/thanh khoản dùng proxy định lượng rồi áp ma trận notch. Những proxy này được ghi rõ, không tuyên bố là ngưỡng định tính do phương pháp quy định. Không tự cộng ngoại lệ nguồn vốn mạnh khi thiếu xác nhận.

### Doanh nghiệp phi tài chính

Bảng 01 quy đổi điểm sang Anchor theo bước chính xác 0,3125, giữ số lẻ khi tổng hợp. Điểm tài chính dùng các ngưỡng tuyệt đối Phụ lục 2, gồm Nợ/EBITDA, FFO/Nợ khi có nguồn, EBITDA/lãi vay, CFO/Nợ và FOCF/Nợ. EBITDA âm không bị coi là đòn bẩy thấp. Dòng tiền âm vẫn có điểm rủi ro cao dù peer cũng âm.

Phương pháp đòi hỏi phân tích ngành và yếu tố định tính, có thể có trọng số riêng theo KCF. Khi chưa có các đánh giá này, báo cáo dùng giả định ngành/quản trị 3/6 và giữ cấu hình trọng số bốn nhóm 20/30/35/15 của ứng dụng; đây **không phải trọng số ngành đã được phương pháp xác nhận**. Trọng số nội bộ tài chính và cách dùng peer chấm kinh doanh cũng được công bố. Không tạo số dự báo để lấp hai năm tương lai. Thanh khoản không tự được nâng bậc chỉ vì Current Ratio cao.

HPG không có nhánh gán cứng bậc hoặc điểm. Cùng một hàm áp dụng cho các mã thuộc phạm vi, với dữ liệu và peer riêng. Khi dữ liệu xấu đi, điểm và bậc thay đổi.

### Bảo hiểm

Giữ Ma trận 01 (ngành × kinh doanh), Bảng 12 (vốn thực góp/vốn tham chiếu), Ma trận 02 (rủi ro tổng hợp × rủi ro tài chính), rồi Ma trận 16–17 về quản trị/chính sách và điều chỉnh thanh khoản/hỗ trợ. Ô có hai lựa chọn mặc định lấy kết quả thận trọng hơn, ghi rõ lựa chọn; không ngoại suy ô trống.

Nguồn hiện có chưa cung cấp vốn pháp định theo giấy phép và dự báo vốn hai năm cho mọi công ty. Vì vậy, khi thiếu mẫu số xác minh, bậc tự động là **kịch bản có điều kiện với vốn tham chiếu 500 tỷ đồng**, giữ nguyên vốn thực góp hiện tại. Mức này không được ghi vào `RequiredCapital`, không được gọi là vốn pháp định thực tế của công ty và không xác nhận tuân thủ pháp luật. Có thể thay bằng `ResearchCapitalReference` hoặc nhập đánh giá `CapitalAdequacy` đã xác minh. Chính sách/đầu tư/thanh khoản chưa được đánh giá riêng sử dụng giả định công bố; bậc có thể thay đổi đáng kể khi thay các giả định.

BVH và PVI vẫn thuộc nhóm peer phi nhân thọ theo cấu hình người dùng. Tuy nhiên BCTC nguồn hiện tại là BCTC tập đoàn/holding, còn PRE và VNR là tái bảo hiểm. Mẫu bìa và phân tích vẫn áp dụng, nhưng không tự áp ma trận pháp nhân phi nhân thọ trực tiếp cho các phạm vi này. Muốn có bậc phù hợp cần BCTC của pháp nhân thuộc phạm vi hoặc phương pháp tập đoàn/tái bảo hiểm tương ứng. Thay nhóm peer không thể tự thay đổi phạm vi số liệu.

## Chạy kiểm tra tại máy

```bat
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_scores.py
"C:\Users\HP\.venv\Scripts\python.exe" scripts\check_report_runtime.py --tickers TCB SSI ABI HPG
```

Kiểm tra nhiều mã: thêm `--tickers` và danh sách mã. `--all` chạy toàn bộ danh mục, có thể mất thời gian. `PASS` là kết quả kiểm tra phần mềm; không có nghĩa mọi mã đã đủ hồ sơ để được thẩm định hoặc có bậc.

Sau cập nhật phải **chuẩn bị lại** báo cáo trong ứng dụng. Các file Word đã tải trước đây không tự đổi. Khóa bộ nhớ đệm đã bao gồm phiên bản và ngày phát hành để nội dung, tên tải xuống, header và bìa khớp nhau.
