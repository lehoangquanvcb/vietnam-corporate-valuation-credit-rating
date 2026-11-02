# Báo cáo 5 năm tài chính và áp dụng phương pháp — V8.128

## Hành vi

Lịch sử sử dụng năm hoàn tất gần nhất theo kỳ BCTC: Q1–Q3 của Y kết thúc chuỗi tại Y−1; Q4 kết thúc tại Y. Có đúng 5 nhãn năm liên tiếp. Số dư lấy cuối năm, dòng kết quả/dòng tiền cộng bốn quý riêng lẻ hợp lệ hoặc dùng nguồn năm hợp lệ, tỷ số giữ giá trị công bố cuối năm. Không đổi nhãn 6T thành năm mà giữ nguyên số.

Xuất Word bỏ qua trạng thái lịch sử YTD/3 năm cũ. Peer quý giữ kỳ đích, loại chính doanh nghiệp và không trộn cửa sổ. Tỷ số trả nợ vẫn sử dụng TTM theo định nghĩa. Nguồn hiện có đến 2026-Q2: lịch sử 2021–2025.

`financial_narrative.py` liên kết các chỉ tiêu và dấu biến động. Không khẳng định nguyên nhân chưa có bằng chứng, không dùng định nghĩa KPI làm nhận định. Nợ xấu tuyệt đối nhân từ tỷ lệ nguồn và dư nợ được ghi rõ là ước tính. Tăng tài sản không được tự hiểu là tăng mức tín nhiệm.

## Phương pháp ngân hàng

Đối chiếu tài liệu người dùng: **1. Phương pháp XHTN Ngân hàng 2026.docx**, bảng 2, bảng 8 và ma trận huy động/thanh khoản. CAR kỳ vọng: >18% Rất Mạnh; 15–18% Mạnh; 12–15% Phù Hợp; 9–12% Trung Bình; 8–9% Yếu; <8% Rất Yếu. Biên chung 8/9/12/15% đặt vào dải cao hơn. Các mức Yếu/Rất Yếu cho phép lựa chọn -2/-3 và -4/-5 bậc theo kết luận đánh giá. Ma trận huy động/thanh khoản tối đa +1, không +2; trường hợp Mạnh/Mạnh cần xác nhận điều kiện ngoại lệ. Cờ rủi ro/vi phạm vốn pháp định áp trần SACP.

Không dùng trung bình điểm ROE, ROA, NIM thay CAR kỳ vọng. Không suy hồ sơ quản trị, đa dạng hóa, tập trung hoặc hỗ trợ từ mã cổ phiếu và quy mô. Điểm định lượng/so sánh peer là luận cứ, không thay kết luận của toàn bộ cấu phần.

Khi có đầy đủ đánh giá nội tại: trả SACP. Khi có đánh giá hỗ trợ: trả ICR. Chưa có đánh giá hỗ trợ không xóa SACP. Không tự đặt triển vọng.

## Lưu phiếu

`config/bank_rating_assessments.json` có trường `assessments` là danh sách. Mỗi phiếu cần `Ticker`, `Period` dạng YYYY-Qn, `Source`, `Rationale`. Chỉ dùng phiếu đúng kỳ có nguồn/lập luận; tham số giao diện ghi đè trường đã nhập. Kết quả là mô phỏng, không đánh dấu đã phê duyệt.

Các trường đánh giá: `BusinessProfile`, `CapitalEarnings`, `RiskPosition` theo sáu mức; `Funding`, `Liquidity` theo bốn mức Mạnh, Phù Hợp, Trung Bình, Yếu; `ExternalSupportNotches` số nguyên 0–8; `Outlook` khi đã có kết luận. Có thể thay đánh giá vốn cuối cùng bằng `ForecastCAR` dạng thập phân cùng `CapitalAdjustmentNotches` số nguyên -2…2. `FundingStrongExceptionConfirmed` xác nhận ngoại lệ +1. Không dùng dữ liệu kiểm thử làm phiếu thực tế. Tệp gửi kèm để trống có chủ đích vì chưa nhận được kết luận thẩm định cho kỳ hiện tại.

## Phạm vi còn mở

VCB không có CAR cuối năm 2021–2025 trong nguồn hiện có; không lấy CAR quý 2 thay cho số năm. Chưa có CAR kỳ vọng và đánh giá đầy đủ cho các cấu phần để tạo bậc XHTN VCB. Không khôi phục mức vnAA+ cũ chỉ bằng các mặc định. Các đánh giá pháp nhân bảo hiểm/hỗ trợ vẫn tuân thủ phạm vi và bằng chứng của engine bảo hiểm hiện hành.

## Kiểm chứng

Có kiểm thử năm đầy đủ, cửa sổ quý, dòng lợi nhuận cộng từ bốn quý nguồn, số dư cuối năm, lựa chọn YTD cũ không quay lại trong Word, bảng CAR, toàn bộ 16 ô ma trận huy động/thanh khoản, SACP khi thiếu hỗ trợ, phiếu sai kỳ. Các kiểm tra runtime xuất DOCX thật; kết quả kỹ thuật không chứng nhận một mức XHTN. Báo cáo mẫu được render và xem từng trang.
