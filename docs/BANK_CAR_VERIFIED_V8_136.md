# CAR đối chiếu báo cáo gốc ngày 03/11/2026

Bản V8.136.0 cập nhật nguồn CAR dùng chung cho KPI, chấm điểm, biểu đồ và báo cáo Word/PDF. Nguồn đã đối chiếu cùng kỳ được ưu tiên hơn bảng tổng hợp người dùng; không thay thế bảng thẩm định riêng đã lưu.

## Báo cáo mới đọc trực tiếp

Số trang dưới đây là thứ tự trang PDF, kể cả trang bìa. Tài liệu là bản công bố của ngân hàng được lưu trên Vietstock; không dùng bài báo thứ cấp để đánh dấu đã xác minh.

| Mã | Kỳ | Riêng lẻ (%) | Hợp nhất (%) | Cơ sở | Trang PDF / dòng |
|---|---|---:|---:|---|---|
| VCB | 30/06/2026 | 11,03 | 11,71 | TT14 | 2, Biểu 1 dòng 3 |
| HDB | 30/06/2026 | 12,80 | 14,27 | TT41 | 5, mục 3.b dòng 6 |
| HDB | 31/12/2025 | 16,37 | 16,72 | TT41 | 5, mục 3.b dòng 6, cột cuối 2025 |
| VIB | 30/06/2026 | 11,6 | 11,8 | TT14 | 6, cột VIB, dòng Tỷ lệ an toàn vốn (bao gồm CCB) |
| EIB | 30/06/2026 | 12,55 | 12,60 | TT41 | 4, Biểu 2 tiếp trang 3 |
| BVB | 30/06/2026 | 12,03 | 12,08 | TT41 | 2, Biểu 2 dòng G |
| KLB | 30/06/2026 | 13,1 | 13,5 | TT14 | 5 (trang in 3), mục 1.1.b dòng 3 |
| PGB | 30/06/2026 | 12,51 | Không phát sinh | TT41 | 5 (trang in 4), Bảng 02 dòng F |
| SGB | 30/06/2026 | 14,22 | 15,48 | TT41 | 5, mục 3.2 dòng 5.b |

VCB: báo cáo gốc không ghi 11,14% ở dòng CAR hợp nhất. Đối chiếu phụ số vốn tự có 252.649.555 triệu đồng / RWA 2.158.120.481 triệu đồng = 11,7069%, làm tròn 11,71%. Không lấy CET1/Tier 1 11,43% hoặc cộng thêm CCB 0,625% ở dòng riêng.

HDB: dữ liệu gốc thay cả số 12,60% trong bảng mới và số 16,00% cuối 2025 trước đây. VIB: giữ nguyên giá trị ngân hàng công bố trong cột thực tế; cột yêu cầu 8,625% không phải CAR của ngân hàng. Không tự cộng/trừ CCB khỏi giá trị công bố. KLB: CCB được công bố riêng, không cộng vào CAR dòng 3. PGB: trang PDF 4 xác nhận không có công ty con/công ty liên kết; giữ phạm vi riêng lẻ và tỷ lệ được ngân hàng công bố, không tự gán hợp nhất.

## Ưu tiên và phạm vi sử dụng

- Giữ TCB 14,95%, ABB 12,72%, SSB 12,06%, STB 9,89% hợp nhất từ nguồn đã đối chiếu. STB 9,40% trong bảng người dùng là số riêng lẻ trên báo cáo gốc.
- Giữ OCB cuối 2025 là 12,32% hợp nhất đã đối chiếu ở bản trước, thay cho 12,61% trong bảng mới. TCB cuối 2025 giữ 14,61% thay cho số làm tròn 14,60%.
- MBB khoảng 11,60% và MSB 12,28% tại Q2/2026 lấy từ bảng mới của người dùng. MBB mang SourceKind USER_ESTIMATE; MSB mang USER_PROVIDED. Chưa gán TT41/TT14 khi chưa đối chiếu tài liệu số liệu; không trộn nhóm peer CAR có cơ sở chưa biết.
- Bảng người dùng được giữ nguyên nội dung và dấu > hoặc ~ trong tệp riêng. Chỉ >12% được quy đổi 12,5% theo chỉ định; ~12% giữ 12%. Agribank và Indovina chưa có mã trong bảng nên chỉ lưu tham chiếu, không tự thêm mã hoặc peer.
- Chỉ fallback cuối 2025 cho bảng điểm Q2/2026 khi thiếu số đúng Q2. Lưu kỳ gốc, không đưa số cuối 2025 vào biểu đồ Q2 hoặc tự chuyển sang Q3. Cơ chế vẫn tồn tại dù 24 mã có dữ liệu hiện đều đã có số Q2.
- Lịch sử tài chính vẫn là 2021–2025; không dùng CAR Q2/2026 để lấp năm 2025. Không trộn TT14 và TT41 trong bình quân peer CAR.

## Độ phủ

22 mã có CAR Q2/2026 đã đối chiếu báo cáo gốc; 2 mã dùng bảng người dùng. Tổng 24/28 mã BANK trong danh mục ứng dụng có CAR đúng kỳ. Còn NVB, PCB, TPB, VBB chưa nạp được CAR đủ căn cứ; không suy ra các ngân hàng chưa công bố. PCB cần xác minh định danh trước khi dùng để thống kê ngân hàng niêm yết.

Đã thử đường dẫn Vietstock theo mẫu người dùng và tra trang nhà đầu tư. Đường dẫn theo mẫu của MBB, MSB, NVB, TPB, VBB trả 404. Trang công bố MSB Q2/2026 được tìm thấy nhưng chưa lấy được bảng đính kèm. TPB có tin về mức CAR theo IRB chuẩn bị chuyển đổi; chưa dùng mức đó thay cho tỷ lệ báo cáo theo cơ sở đang áp dụng. Danh sách thiếu được giữ công khai trong kiểm kê.

Liên kết nguồn, ngày đối chiếu và trang bảng nằm ở `data/bank_car_disclosures.csv`; mã SHA-256 các PDF mới đọc nằm ở `docs/bank_car_source_files_v8_136.json`. Bảng tổng hợp người dùng nằm ở `data/bank_car_user_inputs.csv` và luôn được phân biệt với nguồn đã đối chiếu.
