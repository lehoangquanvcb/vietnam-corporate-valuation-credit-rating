# Phạm vi peer bảo hiểm V8.121.0

Biểu đồ BVH trước đây chỉ có BVH/PVI vì mọi chỉ tiêu dùng bộ lọc cùng
InsuranceSubtype. Danh mục và nguồn quý II/2026 của project có 12 mã bảo hiểm:
ABI, AIC, BIC, BLI, BMI, BVH, MIG, PGI, PRE, PTI, PVI, VNR.
Đây là phạm vi dữ liệu của project, không phải xác nhận số doanh nghiệp niêm yết
trên từng sàn tại thời điểm chạy.

## Quy tắc mới

- Chỉ tiêu tài chính chung trong `insurance_peers.SECTOR_METRICS` dùng tất cả
  công ty INSURANCE đang hoạt động trong universe, loại chính doanh nghiệp,
  loại trùng và không cắt top 10. Bao gồm tài sản, doanh thu, LNST, ROE, ROA,
  biên ròng, vốn chủ sở hữu, vốn/tài sản, vốn thực góp, thu nhập tài chính,
  nợ vay/vốn, nợ đến hạn/vốn, P/B và P/E.
- Chỉ tiêu nghiệp vụ và pháp định dùng cùng loại hình. BVH/PVI là tập đoàn;
  PRE/VNR là tái bảo hiểm; 8 mã còn lại là phi nhân thọ trực tiếp.
- Mỗi mã được đọc đúng quý gần nhất của doanh nghiệp đang phân tích. Không lấy
  số quý khác hoặc cơ sở YTD/TTM thay cho quý riêng lẻ.
- Mã thiếu số vẫn có mặt trong bảng kiểm tra. Cột Included và ExclusionReason
  quyết định thống nhất dữ liệu trên biểu đồ, số peer và thống kê.
- Bình quân/trung vị loại doanh nghiệp đang phân tích, chỉ có khi ít nhất
  5 peer hợp lệ. Nhãn hiển thị là bình quân nhóm tham chiếu; không suy ra đại
  diện toàn thị trường hay mức bao phủ phương pháp chỉ từ số mã cổ phiếu.
- Peer dùng định giá và nhận xét điểm mạnh/yếu vẫn xét cùng loại hình.
  Mở rộng biểu đồ không mở rộng phương pháp XHTN phi nhân thọ cho tập đoàn.

## Hiển thị

Streamlit có danh sách bảo hiểm, loại hình và độ phủ đúng quý; mỗi chỉ tiêu có
số peer thực dùng và lý do loại từng mã. Báo cáo Word dùng cùng tập Included,
bảng giá trị chia cặp mã/giá trị khi có nhiều công ty, giữ bố cục báo cáo chung.

## Kiểm chứng trên bộ dữ liệu project

- BVH: TotalAssets, Revenue, NPAT, ROE... có 11 peer hợp lệ ở 2026-Q2,
  biểu đồ gồm 12 doanh nghiệp.
- ABI: CombinedRatio có 7 peer cùng loại hình, biểu đồ gồm 8 doanh nghiệp.
- BVH: dự phòng nghiệp vụ vẫn đối chiếu PVI; các mã khác có lý do loại.
- 76 kiểm thử toàn bộ thành công; sau chỉnh bố cục/diễn đạt chạy lại 10 kiểm thử
  peer và Word thành công. AppTest chạy BVH/ABI không có exception, kiểm tra
  13 biểu đồ chỉ tiêu chung của mỗi mã có 12 cột và bảng danh mục có 12 hàng.
- Word BVH được kết xuất và kiểm tra hình ảnh đủ 16 trang.

Lệnh chẩn đoán: `python scripts/check_insurance_runtime.py`.
Phiên bản hiển thị: `V8.121.0-INSURANCE-PEERS`.
