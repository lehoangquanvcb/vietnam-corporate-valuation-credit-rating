# V8.123.0 — Peer tự động cho toàn thị trường

Báo cáo tự chọn peer cho mọi mã đang hoạt động trong `company_universe.csv`, dùng chung bộ phân ngành và dữ liệu tài chính. Không phải chạy prepare theo từng mã. Word, các bảng chỉ tiêu và Streamlit dùng cùng bộ chọn peer.

## Nguồn phân ngành

- API Sponsor hiện có trên máy người dùng: `from vnstock_data import Reference`.
- Listing ưu tiên `Reference().equity.list_by_exchange()`; tên công ty hỗ trợ cả `organ_name` và `org_name`.
- Hai API ngành dùng chung: `Reference().industry.sectors(lang='vi')` và `Reference().industry.list(lang='vi')`.
- Đọc schema long theo `symbol + icb_level`; lưu từng cấp riêng. Hỗ trợ schema wide `icb_code1`, `ICBCode1`, `icb_code_lv2`… Không khớp chuỗi con khiến `icb_code` bị gán cho cả bốn cấp.
- Giữ mã dạng chuỗi, không mất số 0 đầu. Chỉ bổ sung tổ tiên mã ICB 4 chữ số khi tổ tiên tồn tại trong taxonomy nguồn.
- Có xung đột hai mã ICB cùng cấp/cùng ticker: dừng và báo lỗi. Mã thiếu trong lần cập nhật không bị xóa phân ngành đã có.
- Nguồn và bảng chuẩn hóa được lưu tại `config/vnstock_industry_source.csv`, `config/vnstock_icb_taxonomy.csv`, `config/vnstock_industry_map.csv`.

Tài liệu schema chính thức: https://vnstocks.com/docs/vnstock/vnstock-data-v3/cau-truc-du-lieu/reference

## Quy tắc chọn

1. Chỉ lấy mã Active, cùng loại hình; loại chính doanh nghiệp và ticker trùng.
2. Corporate: giữ cấu hình analyst override hiện có; ngoài ra ưu tiên ICB cấp 4 → 3 → 2. Chỉ lùi cấp khi không có peer ở cấp chi tiết, không ép ngành ít công ty thành 5 hoặc 10 peer.
3. Khi chưa có ICB chi tiết, dùng đúng Sector hiện có và ghi rõ giới hạn. Nếu không có ngành hợp lệ, báo thiếu phân ngành; không lấy toàn thị trường làm peer.
4. Bank và Securities dùng danh mục cùng loại hình. Insurance giữ quy tắc V8.122: BVH/PVI thuộc nhóm so sánh NONLIFE, dữ liệu hợp nhất vẫn là GROUP; peer định giá cùng phạm vi BCTC, peer nghiệp vụ/tài chính chung giữ chính sách bảo hiểm riêng.
5. Trong nhóm đủ điều kiện, lấy tối đa 10 peer. Ưu tiên mức tương đồng của chỉ tiêu đã xác minh cùng kỳ và cơ sở tính. Điểm không có đủ chứng cứ để trống; peer thiếu raw vẫn hiện với lý do, không tạo số giả.

Số peer đủ điều kiện, số được chọn và số có số liệu so sánh là các con số khác nhau. Mỗi biểu đồ/chỉ tiêu tiếp tục kiểm tra kỳ, cơ sở và dữ liệu hợp lệ trước khi tính bình quân. Ngành chỉ có một doanh nghiệp có thể không có peer.

## Cập nhật chung và tái sử dụng

Chạy từ thư mục gốc dự án:

```bat
"C:\Users\HP\.venv\Scripts\python.exe" scripts\refresh_market_peers.py
```

Hoặc chạy `RUN_REFRESH_PEERS_ALL.bat`. Luồng này:

1. Lấy listing/ICB một lần cho toàn thị trường.
2. Tải tài chính cho các mã chưa tải thành công hoặc lần tải quá 7 ngày; mỗi mã chỉ xuất hiện một lần trong hàng đợi. Mỗi lần thành công được lưu để chạy lại có thể tiếp tục.
3. Xây `data/dynamic_peer_map.csv` và `data/dynamic_peer_summary.csv` cho toàn bộ mã, kể cả mã không có dữ liệu. Báo cáo đọc cache này nếu nguồn không thay đổi.

Không cần cài thêm hoặc thay phiên bản Vnstock cho bản vá này. Máy chạy lệnh cần môi trường Sponsor đang dùng của người dùng. Lần đầu có thể lâu vì phạm vi toàn thị trường; các lần sau dùng trạng thái tải thành công. `--max-age-days` thay đổi thời hạn, `--force` tải lại toàn bộ. Trạng thái DOWNLOADED chỉ xác nhận lần tải, không khẳng định doanh nghiệp đã công bố quý mới nhất.

Các chế độ bổ sung:

```bat
REM Chỉ cập nhật phân ngành toàn thị trường; dùng tài chính sẵn có
"C:\Users\HP\.venv\Scripts\python.exe" scripts\refresh_market_peers.py --catalog-only

REM Không gọi API; xây lại peer từ dữ liệu trên máy
"C:\Users\HP\.venv\Scripts\python.exe" scripts\refresh_market_peers.py --offline
```

Khi thêm/sửa/xóa raw, cấu hình, snapshot hoặc đổi engine, cache tự hết hiệu lực. Báo cáo tự tính lại bằng danh mục chung; không cần chạy prepare riêng. Dữ liệu đã sửa cũng làm hết hạn báo cáo Word/PDF lưu trong session Streamlit.

`data/market_peer_refresh_state.json` dùng để tiếp tục tải; `data/market_peer_refresh_audit.csv` ghi kỳ quan sát và trạng thái từng mã. Nếu API/tệp thiếu, chương trình báo mã lỗi và trả mã thoát 2, vẫn giữ các lần tải thành công và danh mục peer. Chạy lại cùng lệnh để thử lại. Không dùng state này làm bằng chứng cho điểm xếp hạng tín nhiệm.

## Lưu ý dữ liệu cũ và triển khai

Bộ nguồn được gửi trước đây chứa phân ngành lặp cùng mã ở cả bốn cấp. Engine đánh dấu `LEGACY_ICB_REFRESH_REQUIRED`, tạm dùng Sector hiện có. Cần chạy cập nhật phân ngành chung một lần để lấy lại các cấp thật từ Vnstock; đổi nhãn phiên bản hoặc chỉ reboot Streamlit không sửa được nội dung CSV cũ.

Streamlit Cloud dùng tệp trong repository. Sau cập nhật chung ở máy local, đưa `config/company_universe.csv`, các bảng ICB, `data/raw/`, snapshot, lịch sử và peer map cần thiết lên Git. Thông tin đăng nhập, `.env`, backup và state tải local không cần đưa lên Git. Bản ZIP không chứa dữ liệu tài chính giả hay thông tin xác thực và không ghi đè bảng universe người dùng bằng dữ liệu mẫu.

## Kiểm chứng

Xem `verification/` trong ZIP: kiểm thử schema, phân ngành, peer thiếu dữ liệu, ngành ít doanh nghiệp, kỳ/cơ sở khác nhau, cache, resume; kiểm thử hồi quy các mảng hiện có; chạy xây peer cho toàn universe local và đối chiếu giao diện. API Vnstock Sponsor trực tiếp chưa được chạy trong môi trường kiểm thử này.
