# Sửa luồng dữ liệu doanh nghiệp phi tài chính — V8.145

Bản trên Git trước khi sửa là commit `9b247bf`, build V8.144.0-BANK-GOVERNMENT-SUPPORT.
Lỗi VIC trên Cloud bắt nguồn từ việc nguồn tài chính semantic chỉ nằm trong `data/raw`,
trong khi thư mục đó bị bỏ qua khi đẩy Git. Cache cũ thiếu kỳ hoặc mã dòng tài chính
không được dùng làm bằng chứng thay thế.

## Nguồn và phạm vi

Dữ liệu được khôi phục từ bản lưu người dùng đã tải lên:
`Valuation_and_Credit_Rating_Intelligence(20261016-075045).zip`.
Chỉ xuất mã dòng dùng bởi `financial_evidence.MAP`, giữ nguyên kỳ, đơn vị, cơ sở,
nguồn gốc và giá trị. Không sinh chuỗi thời gian, không điền 0, không ngoại suy kỳ thiếu.
Các file gốc không được đưa vào gói phát hành.

`data/financial_evidence/manifest.json` ghi phạm vi kỳ, số dòng và SHA-256 của từng file
trong lần xuất này: 1.711 file có dữ liệu, 15 mã không có nguồn.
Nguồn BCTC tại máy người dùng ưu tiên theo dòng/kỳ. Giá trị mâu thuẫn của raw phải
báo lỗi; không dùng dữ liệu dự phòng để che mâu thuẫn. Cache được làm mới theo
chữ ký file khi thay dữ liệu hoặc phân ngành.

Phân ngành ICB lấy ngày 06/11/2026 từ endpoint công khai Vietcap:
https://iq.vietcap.com.vn/api/iq-insight-service/v2/company/search-bar?language=1

Bản trích phân ngành nằm ở `config/vnstock_industry_source.csv`, gồm bốn cấp ICB;
không lưu các trường đánh giá/giá của payload ngoài nhu cầu phân ngành.
`config/industry_classification_audit.csv` lưu kết quả định tuyến.
Hồ sơ BHI đối chiếu website doanh nghiệp https://bshc.com.vn/.
Hồ sơ VIC và nguồn công khai được ghi trong `data/report_issuer_research.json`.
Bối cảnh bất động sản bổ sung từ phần công khai của báo cáo VARS:
https://varsvietnam.vn/nghien-cuu-thi-truong/bao-cao-thi-truong-bat-dong-san-viet-nam-quy-iii-2026-73
Phân tích tác động tín nhiệm là suy luận của mô hình, tách khỏi dữ kiện nguồn.

## Tính điểm

Không đặt bậc mục tiêu theo mã và không đưa lại hiệu chỉnh thang trong nước.
Bốn cấu phần doanh nghiệp phi tài chính và các giới hạn phương pháp được giữ nguyên.
Sai số số thực của tổng điểm tự động tại biên 1/6 và 6/6 được chặn đúng biên;
điểm override ngoài thang vẫn bị từ chối. Quy tắc hỗ trợ Chính phủ chỉ dành cho
nhóm ngân hàng đã cấu hình trong V8.144, không áp cho doanh nghiệp phi tài chính.

VIC được so sánh với nhóm bất động sản theo phân ngành công khai. Vì đây là tập đoàn
đa ngành, độ tương đồng kinh tế của nhóm peer còn hạn chế; hạn chế được nêu trong
hồ sơ. Không suy ra tiền công ty con có thể tự do chuyển để trả nợ tại công ty mẹ.

## Kiểm chứng

Kiểm tra sử dụng checkout không có CSV trong `data/raw`, không cài vnstock, không
khóa API. Cùng luồng `get_snapshot`/`build_pack`/`rate_company` phục vụ app và Word.

- Toàn danh sách: 1.754 mã; không có exception tính điểm.
- CORPORATE: 1.670 mã, gồm 1.246 ESTIMATED, 417 INSUFFICIENT_DATA, 7 ngoài phạm vi.
- BANK: 26 ESTIMATED, 2 INSUFFICIENT_DATA.
- SECURITIES: 42 ESTIMATED, 1 INSUFFICIENT_DATA.
- INSURANCE: 9 ESTIMATED, 4 NOT_APPLICABLE.
- Giao diện: VIC, HPG, FPT, VNM, VCB, SSI, BHI không phát sinh exception.
- Word VIC: xuất bằng hàm của app, render và xem 29 trang; hai đồ thị cho mỗi chỉ tiêu,
  lịch sử tài chính trong tổng quan, ngành Bất động sản trên bìa.

Trong 417 mã phi tài chính thiếu đầu vào, 14 mã không có kỳ BCTC hợp lệ; 403 mã có kỳ
nhưng thiếu tổ hợp chỉ tiêu/peer cần thiết. Có dữ liệu gốc không đồng nghĩa đủ bằng
chứng tổng hợp bậc. Chưa bổ sung dự báo tài chính hoặc thẩm định định tính cho các mã.

`docs/rating_coverage_v8_145.json` và `docs/coverage_v8_145.csv` ghi chi tiết từng mã.
`PASS` xác nhận quy trình phần mềm, không xác nhận độ chính xác dự báo vỡ nợ hoặc
sự tương đương với xếp hạng CRA. Gói này chưa được đẩy GitHub hay triển khai từ phiên làm việc.
