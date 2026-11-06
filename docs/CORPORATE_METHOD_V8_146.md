# Doanh nghiệp phi tài chính — tổng hợp bốn nhóm rủi ro

Ngày đối chiếu: 06/11/2026. Bản mã nguồn: V8.146.0-CORPORATE-WEIGHTED-SCORE.

## Vấn đề và thay đổi

Giao diện cũ trình bày doanh nghiệp phi tài chính thành Anchor → SACP/SCA → ICR giống ngân hàng. Luồng báo cáo tự động thực ra đã cộng bốn điểm theo tỷ trọng, nhưng dùng chung hàm hoàn tất và nhãn của định chế tài chính. Ngoài ra, luồng đánh giá chuyên viên có bảng quy đổi điểm khác với luồng tự động và tự suy thanh khoản từ các tỷ số hiện tại.

Bản này dùng chung một hàm tổng hợp và quy đổi cho hai luồng. Kết quả doanh nghiệp phi tài chính có các trường WeightedContributions, WeightedScore, InitialRating, StandaloneRating và ICR; không chứa Anchor, SACP hoặc SCA. Giao diện và Word/PDF thể hiện điểm, tỷ trọng, đóng góp của từng nhóm, tổng điểm, bậc ban đầu và kết quả cuối cùng. Điều chỉnh có căn cứ được tách riêng sau tổng điểm. Không dùng một bậc ngành cố định để nâng/hạ theo bốn nhóm.

Công thức: tổng điểm = Σ(điểm nhóm × tỷ trọng nhóm). Bốn nhóm là vĩ mô/ngành, kinh doanh, tài chính, quản trị/quản lý. Thang điểm 1–6; điểm càng thấp thì rủi ro càng thấp. Không làm tròn trung gian; chỉ làm tròn phần hiển thị. Tổng tỷ trọng phải bằng 100%; dữ liệu thiếu không được chuyển thành số 0.

## Tài liệu đã đối chiếu

- `170725_Phương pháp XHTN doanh nghiệp.docx`: bốn nhóm, thang 1–6, không làm tròn trung gian, Bảng hướng dẫn phân tích số 01; các bảng điều chỉnh 02–04 và giới hạn quản trị. Tài liệu gọi bậc quy đổi sau tổng điểm là mức ban đầu/Anchor, khác với bậc đầu vào cố định của ngân hàng. Theo yêu cầu, giao diện dùng tên tiếng Việt “Bậc xếp hạng ban đầu”.
- `Báo cáo XHTN không chỉ định HPG 02-11-2026.docx`: bốn điểm 3,000 / 1,810 / 3,5625 / 3,000, tỷ trọng 20% / 30% / 35% / 15%; tổng không làm tròn 2,839875 và bậc A−. Các bản HPG cũ hơn có cấu hình khác; không dùng bậc cũ làm mức đích.
- `6.5_Vinhomes_BCXHTN_VN_dịch bản này(1).docx`: ngày 06/05/2026, bốn điểm 4 / 1 / 2 / 1, bậc ban đầu vnAA, thanh khoản 0 bậc, nhóm/cp 0 bậc, kết quả vnAA. Báo cáo không nêu tỷ trọng bốn nhóm. Không thể suy ra duy nhất tỷ trọng từ kết quả đó; không gán điểm VHM cho VIC và không ép kết quả mô hình thành AA. Báo cáo còn sử dụng các số điều chỉnh và dự phóng, khác với bộ số thực tế đang lưu trong app.

Không sao chép toàn văn các tài liệu tham chiếu vào gói mã nguồn.

## Tỷ trọng và giới hạn hiện còn

Phương pháp yêu cầu tỷ trọng phù hợp từng ngành/KCF, nhưng các tài liệu được cung cấp chưa chứa một bộ tỷ trọng số đầy đủ theo ngành. Tỷ trọng mặc định 20% / 30% / 35% / 15% vẫn là cấu hình nghiên cứu kế thừa. Nội dung này được ghi ngay dưới bảng kết quả và trong phần giả định. Người dùng có thể nhập bốn điểm và bộ tỷ trọng có căn cứ trong phần thẩm định của app.

Điểm kinh doanh/tài chính tự động vẫn là quy tắc định lượng của ứng dụng. Ngành và quản trị chưa được thẩm định thì dùng giả định công bố; không tự nhận các giá trị đó là điểm đánh giá của CRA. Chưa có dự phóng hai năm nên không tạo số giả để mô phỏng trọng số lịch sử/dự phóng của phương pháp. Bản sửa này không phải việc thẩm định đầy đủ mọi doanh nghiệp hay tái tạo kết quả CRA thực tế.

## Quy đổi và điều chỉnh

Bảng 01 dùng bước chính xác 0,3125, bắt đầu trần AAA = 1. Các trần tiếp theo: AA+ = 1,3125; AA = 1,625; AA− = 1,9375; A+ = 2,25; A = 2,5625; A− = 2,875; BBB+ = 3,1875; BBB = 3,5; BBB− = 3,8125; BB+ = 4,125; BB = 4,4375; BB− = 4,75; B+ = 5,0625; B = 5,375; B− = 5,6875. Nguồn gộp phần còn lại đến 6 thành CCC–C; máy dùng CCC đại diện, không suy diễn sự kiện vỡ nợ.

Điều chỉnh không làm thay đổi tổng điểm. Giới hạn quản trị 4/5/6 tương ứng BB+/BB−/B. Điều chỉnh thanh khoản chỉ dùng đánh giá được nhập rõ ràng; không tăng/hạ từ Current Ratio. Thanh khoản mạnh chỉ cho +1 ở bậc ban đầu B+ hoặc thấp hơn nếu chính sách tài chính được xác nhận không yếu. Hỗ trợ bên ngoài được nhập riêng; mặc định nghiên cứu 0 bậc có công bố. Phương pháp ngân hàng/chứng khoán/bảo hiểm không bị chuyển sang công thức này.

## Triển khai

Cập nhật dùng chung cho mọi mã được định tuyến CORPORATE, không riêng VIC, HPG hay VHM. Bốn nhóm có bằng chứng vẫn được hiển thị khi chưa đủ để tổng hợp. Các ngành ngoài phạm vi phương pháp tiếp tục bị chặn. Word/PDF cũ đã tải xuống không tự thay đổi; phải tạo lại sau cập nhật.
