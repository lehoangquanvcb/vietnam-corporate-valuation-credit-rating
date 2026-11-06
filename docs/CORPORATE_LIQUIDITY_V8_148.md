# V8.148 — Điều chỉnh thanh khoản chỉ nâng hoặc giữ bậc

Áp dụng **chỉ cho doanh nghiệp phi tài chính (CORPORATE) trong phạm vi phương pháp**. Thay thế quy tắc điều chỉnh thanh khoản V8.147 theo yêu cầu chủ mô hình ngày 06/11/2026.

| Mức thanh khoản | Điều chỉnh bậc |
|---|---:|
| Rất Mạnh | +2 notch |
| Mạnh | +1 notch |
| Phù Hợp | 0 notch |
| Trung Bình / Dưới trung bình | 0 notch |
| Yếu | 0 notch |

Không hạ bậc hoặc áp trần hạ bậc do yếu tố thanh khoản. Khi bậc sau điều chỉnh vượt AAA, kết quả được giới hạn tại AAA, lưu cả số bậc đề nghị và số bậc thực tế.

## Phạm vi và trình tự

- Dòng **Yếu tố thanh khoản** nằm sau bậc ban đầu và trước kết quả cuối trong bảng điểm, bảng diễn giải quá trình hình thành bậc và báo cáo doanh nghiệp phi tài chính.
- Tổng điểm bốn nhóm rủi ro → bậc ban đầu → thanh khoản → các điều chỉnh/giới hạn khác nếu có → kết quả cuối. Yếu tố thanh khoản không thay đổi tổng điểm bốn nhóm.
- Ngân hàng, chứng khoán và bảo hiểm tiếp tục dùng phương pháp thanh khoản và điều chỉnh bậc riêng. Không thêm dòng hoặc áp quy tắc thanh khoản doanh nghiệp vào ba loại hình này.
- Loại bỏ nhánh API cũ còn áp trần B− hoặc hạ bậc khi thanh khoản yếu/dưới trung bình. Đầu vào mức do chuyên viên nhập và mức tính từ BCTC dùng cùng bảng trên.
- Không thay đổi bộ chỉ tiêu, ngưỡng phân loại, điều kiện cộng bậc hoặc yêu cầu dữ liệu của V8.147. Dùng số dư cuối kỳ và dòng tiền TTM; không yêu cầu dự phóng. Thiếu dữ liệu vẫn ghi rõ và tạm giữ 0 notch.
- Các điều chỉnh khác và giới hạn quản trị vẫn hoạt động độc lập. Đây là quy tắc nghiên cứu theo cấu hình chủ mô hình, không phải tuyên bố về ngưỡng chính thức của CRA.
- Việc bỏ P/E, P/B và giá thị trường khỏi tab/báo cáo XHTN của mọi loại hình được giữ lại. Phạm vi loại bỏ chỉ tiêu thị trường khác với phạm vi điều chỉnh thanh khoản.

## Kết quả đối chiếu dữ liệu 2026-Q2

| Mã | Bậc ban đầu | Thanh khoản | Notch thanh khoản | Kết quả cuối |
|---|---|---|---:|---|
| VIC | BBB− | Trung Bình | 0 | BBB− |
| VHM | A− | Phù Hợp | 0 | A− |
| HPG | A− | Trung Bình | 0 | A− |
| FPT | A+ | Mạnh | +1 | AA− |
| VNM | AA− | Rất Mạnh | +2 | AA+ |

Kết quả là phép tính của mô hình trên dữ liệu lưu trong ứng dụng. Không ép bậc theo mã. VHM tiếp tục ở mức Phù Hợp sau điều kiện kiểm soát thanh toán hiện hành.

## Kiểm chứng

- Kiểm tra đủ năm mức thanh khoản, số notch âm bị từ chối, số notch phải khớp mức đánh giá, giới hạn AAA, không áp hai lần, giữ nguyên tổng điểm bốn nhóm và thứ tự các dòng.
- Kiểm tra đầu vào trực tiếp không còn hạ bậc do thanh khoản, kể cả nhánh tương thích lời gọi cũ.
- Kiểm tra bộ thanh khoản doanh nghiệp không được gọi khi xếp hạng VCB, SSI, ABI; chạy lại các kiểm thử huy động/thanh khoản ngân hàng và quy trình bảo hiểm.
- Đối chiếu 15 mã với bản trước: kết quả các định chế tài chính giữ nguyên; doanh nghiệp phi tài chính thay đổi đúng bảng trên.
- Kiểm tra giao diện và xuất báo cáo theo dữ liệu thực tế. Kết quả chi tiết nằm trong validation_v8_148.json và các tệp bằng chứng cùng phiên bản.

## Cập nhật

Gói cập nhật tích lũy gồm các tệp chương trình cần thiết từ V8.146/V8.147 lên V8.148, bao gồm sửa P/E và dòng thanh khoản. Không bao gồm dữ liệu tài chính hoặc bản cài độc lập.

Giải nén nội dung vào thư mục gốc đang có app.py, chọn thay thế các tệp cùng tên rồi chạy:

```bat
cd /d C:\Users\Admin\vietnam-corporate-valuation-credit-rating-main
git add --pathspec-from-file=GIT_FILES_V8_148.txt
git commit -m "V8.148 corporate liquidity uplift only"
git pull --rebase origin main
git push origin main
```

Sidebar sau cập nhật: **V8.148.0-CORPORATE-LIQUIDITY-UPLIFT**.
