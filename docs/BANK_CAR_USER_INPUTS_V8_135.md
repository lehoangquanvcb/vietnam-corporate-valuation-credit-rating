# CAR ngân hàng V8.135.0

Ngày cập nhật 03/11/2026. Bản này thực hiện chỉ định về CAR của Lê Hoàng Quân: ưu tiên số đã đối chiếu báo cáo gốc; bổ sung bảng người dùng khi còn thiếu; cho phép số 31/12/2025 làm đầu vào bảng điểm 30/6/2026; > 12% dùng ước 12,5%.

## Chọn nguồn và kỳ

1. Cùng mã và kỳ: nguồn đã đối chiếu báo cáo gốc được ưu tiên, kể cả nguồn riêng lẻ ABB trước số hợp nhất ước tính do người dùng cung cấp.
2. Khi thiếu nguồn đã đối chiếu cùng kỳ, dùng số người dùng cung cấp. Số ước tính và số xấp xỉ giữ nhãn riêng; không gắn nhãn đã xác minh.
3. Khi không có CAR 30/6/2026, được dùng CAR 31/12/2025 cho bảng điểm, giữ kỳ gốc và ghi rõ việc sử dụng thay thế. Quy tắc này không tự kéo sang quý III/2026 hoặc các kỳ tương lai.
4. Lỗi/xung đột nguồn không bị che bằng một dòng số khác. Các cấu phần thẩm định nhập riêng hoặc đã lưu vẫn được ưu tiên theo cơ chế hiện hành.
5. Lịch sử 5 năm chỉ nhận số cuối năm đúng kỳ. Peer quý không nhận số cuối 2025 như thể đó là CAR quý II/2026. CAR người dùng chưa xác định TT41/TT14 không gộp bình quân với CAR đã xác định cơ sở quy định.

## Nguồn mới đã đối chiếu

- BAB: 8,95% hợp nhất và 8,88% riêng lẻ, tại 30/6/2026; PDF trang 6, trang in 3, Bảng 2. TT41.
  https://www.baca-bank.vn/SiteAssets/Folder%20Upload/97.2026_Cong%20bo%20thong%20tin_30.06.2026%20VI%20signed.pdf
- STB: 9,89% hợp nhất và 9,40% riêng lẻ, tại 30/6/2026; PDF trang 5, trang in 4, Bảng 4. TT41.
  https://www.sacombank.com.vn/content/dam/sacombank/files/nhadautu/cong-bo-thong-tin/2026/ty-le-an-toan-von-Tieng-Viet.pdf

Bảng người dùng được giữ nguyên nội dung đầu vào trong data/bank_car_user_inputs.csv, gồm cả các dòng không được chọn do đã có nguồn ưu tiên. Agribank và Indovina Bank không có mã CK trong bảng, được lưu tham chiếu theo tên, không tự thêm mã vào danh mục niêm yết. Dấu * được giữ nguyên vì chưa có chú giải kèm bảng; không tự suy diễn ý nghĩa.

## Kết quả kiểm tra thực thi

Đã kiểm tra tất cả 28 mã được cấu hình EntityType=BANK trong ứng dụng (con số này không phải xác nhận có 28 ngân hàng niêm yết; riêng mã PCB cần rà soát định danh). Có 20 mã có CAR dùng được và ra bậc; 17 mã có CAR đúng kỳ 30/6/2026, 3 mã dùng số cuối 2025. Trong 17 mã đúng kỳ có 14 nguồn đã đối chiếu và 3 nguồn người dùng cung cấp/ước tính.

| Mã | CAR dùng (%) | Kỳ số liệu | Loại nguồn | Bậc từ app |
|---|---:|---|---|---|
| ABB | 12.72 | 2026-Q2 | VERIFIED_DISCLOSURE | vnA- |
| ACB | 11.80 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBBB- |
| BAB | 8.95 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBB+ |
| BID | 10.01 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBBB |
| BVB | — | 2026-Q2 | NOT_YET_INGESTED | N/A |
| CTG | 10.10 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBBB+ |
| EIB | 12.60 | 2026-Q2 | USER_PROVIDED | vnBB |
| HDB | 16.00 | 2025-Q4 | FALLBACK_2025_USER_PROVIDED | vnA- |
| KLB | — | 2026-Q2 | NOT_YET_INGESTED | N/A |
| LPB | 11.18 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBB+ |
| MBB | 11.50 | 2025-Q4 | FALLBACK_2025_USER_ESTIMATE | vnBBB- |
| MSB | 12.28 | 2026-Q2 | USER_PROVIDED | vnBBB |
| NAB | 10.94 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBBB- |
| NVB | — | 2026-Q2 | NOT_YET_INGESTED | N/A |
| OCB | 13.07 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBB |
| PCB | — | 2026-Q2 | NOT_YET_INGESTED | N/A |
| PGB | — | 2026-Q2 | NOT_YET_INGESTED | N/A |
| SGB | — | 2026-Q2 | NOT_YET_INGESTED | N/A |
| SHB | 11.81 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBBB- |
| SSB | 12.06 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBB |
| STB | 9.89 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBB+ |
| TCB | 14.95 | 2026-Q2 | VERIFIED_DISCLOSURE | vnAA+ |
| TPB | — | 2026-Q2 | NOT_YET_INGESTED | N/A |
| VAB | 9.34 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBBB+ |
| VBB | — | 2026-Q2 | NOT_YET_INGESTED | N/A |
| VCB | 12.50 | 2026-Q2 | USER_ESTIMATE | vnA |
| VIB | 12.20 | 2025-Q4 | FALLBACK_2025_USER_PROVIDED | vnBB- |
| VPB | 13.29 | 2026-Q2 | VERIFIED_DISCLOSURE | vnBB |

Các mã còn thiếu CAR: BVB, KLB, NVB, PCB, PGB, SGB, TPB, VBB. Không có các mã này trong bảng bổ sung có mã CK của người dùng và chưa có số được nạp ở hai kỳ được phép. Đây là giới hạn nguồn hiện có trong app, không phải kết luận ngân hàng chưa công bố.

Kết quả tự động có trạng thái ESTIMATED và công khai giả định; không chuyển thành thẩm định đã duyệt. TCB giữ bảng chấm đã lưu vnAA+. Dữ liệu người dùng hoặc số kỳ cũ không tự tạo triển vọng hoặc điều chỉnh hỗ trợ bên ngoài.

Đối chiếu kết quả máy tại docs/car_coverage_v8_135.json, docs/score_validation_v8_135.json và docs/validation_v8_135.json.
