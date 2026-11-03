# Nguồn CAR ngân hàng và phạm vi cập nhật V8.134

Ngày đối chiếu: 03/11/2026.

Trong bộ nguồn nhận được, 27 tệp tỷ số ngân hàng trả CAR bằng 0 tại 2026-Q2; PCB không có tệp tỷ số tương ứng. Đây là khoảng trống dữ liệu của ứng dụng, không phải bằng chứng ngân hàng chưa công bố.

Bản sửa bổ sung nguồn CAR công bố vào cùng luồng chuẩn hóa đang phục vụ ảnh chụp tài chính, chấm điểm tự động, biểu đồ và báo cáo Word/PDF. Mọi mã BANK đều đi qua cùng cơ chế; số mã có số đã đối chiếu được thống kê riêng bên dưới.

## Quy tắc sử dụng nguồn

- Ưu tiên bản công bố đã đối chiếu hơn feed trả 0 hoặc số làm tròn. Chỉ dùng CAR tổng vốn tự có/tài sản có rủi ro, không dùng tỷ lệ vốn cấp 1, TCE hoặc CAR dự kiến.
- Ghép chính xác mã và kỳ. Không chuyển CAR 30/6 thành số cuối năm hoặc kéo sang quý III.
- Ưu tiên hợp nhất nếu nguồn có cả hai phạm vi. Khi chỉ có riêng lẻ, giữ rõ phạm vi; ABB không còn công ty con tại 30/6/2026.
- Lưu nguồn, trang/bảng, chế độ quy định, ngày đối chiếu và ghi chú. Không trộn TT41 với TT14 trong bình quân peer CAR. Cấu phần vốn dùng bảng chấm đang có của dự án, với giả định CAR hiện tại duy trì được nêu rõ.
- Giữ độ chính xác trước chấm điểm: CAR hợp nhất TCB là 14,95%, không làm tròn thành 15,0% để vượt ngưỡng. Bảng chấm TCB đã lưu vẫn được ưu tiên.
- Xung đột cùng mã/kỳ/phạm vi hoặc dòng nguồn không hợp lệ phải hiện ERROR, không lấy một số tùy ý.
- Thay tệp CAR sẽ làm mới cả bộ nhớ đệm số liệu, peer và khóa báo cáo tải về. Không cần prepare riêng từng mã.
- Dữ liệu cập nhật theo bản công bố đã đối chiếu. Chưa có bộ tải/đọc PDF tự động bao phủ toàn bộ ngân hàng và các kỳ tương lai.

## CAR tại 30/6/2026 đã bổ sung

| Mã | CAR dùng trong app | Phạm vi | Quy định | Nguồn |
|---|---:|---|---|---|
| ABB | 12.72% | Riêng lẻ | TT41 | [Bản công bố](https://abbank.vn/uploads/files/2026/09/11/a375a3/phpbgmkmk-cong-bo-thong-tin-ty-le-an-toan-von-30062026-final-6aa3c5563a0ba.pdf), trang 4 |
| ACB | 11.80% | Hợp nhất | TT14 | [Bản công bố](https://acb.com.vn/ve-chung-toi/kqkd-6-thang-2026-acb-dat-loi-nhuan-hon-10700-ty-dong-ban-le-va-sme-hoi-phuc-tich-cuc), trang HTML - đoạn CAR sau chi trả cổ tức |
| BID | 10.01% | Hợp nhất | TT41 | [Bản công bố](https://bidv.com.vn/wps/wcm/connect/b2f1a1ab-2711-461b-828f-a07bc0dd22a0/Bao%2Bcao%2BCBTT%2B30.06.2026_VIE.pdf?CACHEID=ROOTWORKSPACE-b2f1a1ab-2711-461b-828f-a07bc0dd22a0-q2aSuuC&MOD=AJPERES), trang 6 |
| CTG | 10.10% | Hợp nhất | TT41 | [Bản công bố](https://investor.vietinbank.vn/documents/20126/0/Bao%2Bcao%2BCong%2Bbo%2Bthong%2Btin%2BTy%2Ble%2Ban%2Btoan%2Bvon%2B30.06.2026.pdf/580cf317-d9f5-9a7f-d334-8d15b2f3bb42?t=1790131048136), trang 4 |
| LPB | 11.18% | Hợp nhất | TT41 | [Bản công bố](https://cdn.financialreports.eu/financialreports/media/filings/66881/2026/RNS/66881_rns_2026-09-11_6d7f6681-6c5b-4cf4-bd5c-18d384248b76.pdf), trang 6 |
| NAB | 10.94% | Hợp nhất | TT14 | [Bản công bố](https://namabank.com.vn/Data/Sites/1/media/nha-dau-tu/ty-le-an-toan-von/2026/c%C3%B4ng-b%E1%BB%91-th%C3%B4ng-tin-car-th%C3%A1ng-06.2026_ti%E1%BA%BFng-vi%E1%BB%87t.pdf), trang 4 |
| OCB | 13.07% | Hợp nhất | TT41 | [Bản công bố](https://webocb-api.ocb.com.vn/Resources/Files/20261009152943_3.1bancongbothongtinantoanvon30.06.2026vie.pdf), trang 10–11 |
| SHB | 11.81% | Hợp nhất | TT41 | [Bản công bố](https://www.shb.com.vn/wp-content/uploads/2026/09/260929_SHB_CONG-BO-TY-LE-AN-TOAN-VON-Ky-30-06-2026_VN_A4.pdf), trang 5 |
| SSB | 12.06% | Hợp nhất | TT41 | [Bản công bố](https://cloud-cdn.seabank.com.vn/seabank-web/SeABank_CAR_C%C3%B4ng%20b%E1%BB%91%20th%C3%B4ng%20tin_2026.06.30.pdf), trang 5 |
| TCB | 14.95% | Hợp nhất | TT41 | [Bản công bố](https://techcombank.com/content/dam/techcombank/public-site/documents/cong-bo-thong-tin-ty-le-an-toan-von-1h2026-publish.pdf), trang 6 |
| VAB | 9.34% | Hợp nhất | TT41 | [Bản công bố](https://www.vietabank.com.vn/Uploads/Download/Investors/CBTT%20T%E1%BB%B7%20l%E1%BB%87%20ATV%20b%C3%A1n%20ni%C3%AAn%202026.pdf), trang 2 |
| VPB | 13.29% | Hợp nhất | TT41 | [Bản công bố](https://www.vpbank.com.vn/-/media/vpbank-latest/5nha-dau-tu/cong-bo-thong-tin-ty-le-an-toan-von/2026/CBTT-ty-le-an-toan-von-Q2-2026.pdf), trang 7 |

NAB: dùng dòng C3 (vốn tự có / RWA) 10,94% hợp nhất. Dòng C trong tài liệu là 11,57%, gồm thêm đệm CCB 0,625 điểm phần trăm; hai dòng được phân biệt rõ trong ghi chú nguồn. ACB: thông cáo KQKD chính thức nêu CAR hợp nhất TT14 11,8%, độ chính xác một chữ số thập phân. LPB: dùng bản sao nguyên văn báo cáo có chữ ký của ngân hàng gửi sở giao dịch.

Ngoài kỳ 2026-Q2, các cột đối chiếu 31/12/2025 của OCB, TCB và VPB được lưu đúng 2025-Q4; không lấp các năm còn thiếu.

## Phần chưa hoàn thành

Đã đưa vào ứng dụng 12/28 mã. Còn chờ bổ sung/đối chiếu nguồn: BAB, BVB, EIB, HDB, KLB, MBB, MSB, NVB, PCB, PGB, SGB, STB, TPB, VBB, VCB, VIB. Không gán trạng thái ‘chưa công bố’ cho các mã này. Các trang công bố của MSB, VIB, SGB và BAB đã được tìm thấy nhưng chưa lấy được đầy đủ số và phạm vi hợp lệ để nhập. VCB có thông tin khác nhau giữa thông cáo sơ kết và tài liệu kết quả kinh doanh, cần đối chiếu báo cáo gốc thay vì gán số theo tin tóm tắt.

Chạy `python scripts/check_bank_car.py --period 2026-Q2` để xem bao phủ. `Result: PARTIAL` phản ánh dữ liệu chưa đủ toàn danh mục; chỉ báo `COMPLETE` khi tất cả mã BANK có CAR hợp lệ đúng kỳ. Thêm `--require-complete` để quy trình kiểm tra tự động trả mã lỗi 2 nếu còn thiếu.

## Kết quả kiểm tra thực thi

- ABB nhận CAR 12,72%, cấu phần vốn/lợi nhuận Phù Hợp, bậc ước tính vnA- với giả định công bố; không ghi thành đánh giá đã thẩm định.
- TCB giữ bậc vnAA+ từ bảng chấm nguồn đã lưu.
- Kiểm tra chấm điểm 46 mã qua cả bốn phương pháp; kiểm tra giao diện 7 mã, tab mặc định XHTN và thao tác điều chỉnh riêng.
- Có kiểm thử sai kỳ, sai mã, đơn vị, phạm vi, xung đột nguồn, làm mới cache và dữ liệu quý không trở thành chuỗi năm.
- Đã xuất báo cáo ABB thực tế và render sang PDF để kiểm tra vùng CAR, bìa, trang kết quả và nguồn.
- Các kết quả chi tiết ở `docs/car_coverage_v8_134.json`, `docs/score_validation_v8_134.json`, `docs/ui_validation_v8_134.json` và `docs/validation_v8_134.json`. Kiểm tra phần mềm đạt không đồng nghĩa đủ dữ liệu cho mọi mã.
