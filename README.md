# Vietnam Corporate Valuation, M&A & Credit Rating Intelligence Platform — V8.1 Foundation

Nền tảng đa ngành cho doanh nghiệp niêm yết Việt Nam, tách 3 engine theo loại hình:

1. **Ngân hàng** — kế thừa Bank Engine/XHTN từ V7.x.
2. **Công ty chứng khoán** — Anchor CTCK, Hồ sơ kinh doanh, Vốn & Lợi nhuận, Vị thế rủi ro, Nguồn vốn & Thanh khoản, SACP, hỗ trợ bên ngoài, ICR.
3. **Doanh nghiệp phi tài chính** — Rủi ro Vĩ mô & Ngành, Rủi ro Kinh doanh, Rủi ro Tài chính, Quản trị & Quản lý → Anchor → Modifier → SCA → Support → ICR.

## Kiến trúc dữ liệu

**Vnstock Bronze chạy LOCAL → CSV ACTUAL → GitHub → Streamlit Cloud chỉ đọc CSV.** Không gọi vnstock_data ở runtime Streamlit.

## Repo mới

Tên khuyến nghị:

`Vietnam_Corporate_Valuation_MA_Credit_Rating_Intelligence`

Chạy `INIT_NEW_GITHUB_REPO.bat`, sau đó tạo một repository **rỗng** trên GitHub và gắn `origin` theo hướng dẫn của BAT.

## Streamlit mới

- Repository: repo mới nói trên
- Branch: `main`
- Main file: `app.py`
- Python: `3.12`
- URL đề xuất: `vietnam-corporate-valuation-ma-credit-rating.streamlit.app`

## Refresh

- `RUN_REFRESH_ONE_COMPANY.bat`: nhanh nhất, nhập SSI/HPG/VHM...
- `RUN_SECURITIES.bat`: refresh seed universe CTCK
- `RUN_CORPORATES.bat`: refresh seed universe phi tài chính
- `RUN_FULL_REFRESH.bat`: CTCK + corporate + validate + push
- `RUN_FAST.bat`: chỉ validate + commit + push dữ liệu/code hiện có

Ngân hàng vẫn sử dụng data/pipeline ngân hàng đã được kiểm thử ở V7.x; V8 đọc lại `bank_snapshot.csv` và `bank_history_long.csv`.

## Methodology governance

### CTCK

Methodology source: `Phương pháp XHTN Công ty Chứng khoán 2025.docx` do người dùng cung cấp, được route thành `SECURITIES_2025` trong app để đồng nhất kỳ báo cáo hiện hành. Engine giữ cấu trúc methodology và không coi auto-score là kết quả phát hành chính thức.

- BICRA ngân hàng tham chiếu `a-`; CTCK thông thường điều chỉnh -2 notch để ra Anchor `bbb`.
- Hồ sơ Kinh doanh / Vốn & Lợi nhuận / Vị thế rủi ro: 6 mức; notch +2/+1/0/-1/-2~-3/-4~-5.
- Nguồn vốn và Thanh khoản được đánh giá riêng và kết hợp.
- KPI quan trọng: tỷ lệ vốn khả dụng, Nợ/VCSH, Nợ/EBITDA, ICGR, CIR, ROE, ROA, cơ cấu doanh thu môi giới/tự doanh/margin và thanh khoản.

### Doanh nghiệp phi tài chính

Methodology source: `170725_Phương pháp XHTN doanh nghiệp.docx` do người dùng cung cấp; engine được route thành `CORPORATE_2025`, đúng năm của tài liệu nguồn.

- 4 nhóm trọng yếu: Vĩ mô & Ngành; Kinh doanh; Tài chính; Quản trị & Quản lý.
- Điểm 1–6, trọng số theo ngành/KCF → Anchor.
- Rating scale 1.00=vnAAA ... 6.00=vnCCC-vnC nằm trong `corporate_rating_scale.csv`.
- Modifier: đa dạng hóa, nghĩa vụ nợ, thanh khoản, yếu tố rủi ro khác → SCA; sau đó Group/Government Support → ICR.
- **Eligibility Gate:** project finance, IHC và hàng không được gắn `EXCLUDED_SPECIALIZED`, không phát hành XHTN tự động bằng corporate methodology.

### Lưu ý quan trọng về trọng số ngành

File methodology nêu rõ trọng số có thể khác nhau theo ngành và cần KCF/benchmark ngành. V8.1 Foundation chứa `corporate_sector_weights.csv` với cấu trúc kỹ thuật mặc định để app chạy; các dòng `PLACEHOLDER_TO_BE_KCF_CALIBRATED` **không được coi là trọng số methodology đã phê duyệt**. Cần nhập KCF/trọng số chính thức trước khi dùng cho rating phát hành.

## Universe

`config/company_universe.csv` là **seed universe**, hiện gồm ngân hàng, CTCK và một nhóm doanh nghiệp đại diện nhiều ngành. Architecture chấp nhận thêm ticker bất kỳ bằng cách bổ sung một dòng vào file này. Mục tiêu production là mở rộng tới toàn bộ HOSE/HNX/UPCoM sau khi hoàn thiện classification/KCF.

## Reports

App xuất:

- Báo cáo Phân tích, Định giá & M&A (.docx/.pdf)
- Báo cáo Xếp hạng tín nhiệm (.docx/.pdf)

Font Lato được yêu cầu qua `packages.txt`; Word dùng Lato, body 11pt, bảng 10pt; PDF fallback an toàn nếu runtime chưa nhận font.


## V8.1 - FULL MARKET COVERAGE
- `RUN_FULL_MARKET_COVERAGE.bat`: phát hiện universe HOSE/HNX/UPCoM từ Vnstock LOCAL và tạo audit theo sàn/loại hình.
- `data/coverage_matrix.csv`: đo mức sẵn sàng dữ liệu từng mã: PRODUCTION_READY / PARTIAL / INSUFFICIENT_DATA.
- App có tab **Phủ dữ liệu toàn thị trường**; không đánh đồng có ticker với đủ dữ liệu định giá/XHTN.
- Report Engine mới có kiến trúc **30 trang A4** cho cả Phân tích-Định giá-M&A và XHTN; mỗi trang là một module phân tích riêng, Lato, số kiểu Việt Nam, chart tách riêng tránh rối.
- Các ngành cần methodology chuyên biệt tiếp tục được gắn `EXCLUDED_SPECIALIZED`; không tự động phát hành XHTN.


## V8.2 - AUTO INDUSTRY & SECTOR BENCHMARK
- Tự động lấy phân ngành ICB từ Vnstock Reference/Listing và gán doanh nghiệp vào ngành phù hợp.
- Corporate mặc định dùng ICB cấp 2 để benchmark; nếu thiếu thì fallback cấp 3/1/4.
- Ngân hàng: benchmark toàn bộ ngân hàng niêm yết/ĐKGD trong universe; CTCK: toàn bộ CTCK niêm yết/ĐKGD.
- Mọi chart tài chính dùng thêm line **Trung bình ngành** theo từng kỳ; bảng KPI có **Trung bình ngành** và số doanh nghiệp có dữ liệu.
- `RUN_UPDATE_INDUSTRY_BENCHMARK.bat`: cập nhật nhanh phân ngành + benchmark mà không refresh toàn bộ BCTC.
- `RUN_FULL_MARKET_COVERAGE.bat`: Universe → ICB → Coverage → Industry Benchmark → Validation.


## V8.3 - SECTOR-SPECIFIC FINANCIAL ANALYSIS
- Tự route ICB Vnstock -> mẫu phân tích chuyên ngành.
- 14 template: Bank, Securities, Real Estate, Steel/Materials, Power/Utilities, Oil & Gas, Retail, Technology, Logistics, Consumer/Food, Construction/Infrastructure, Chemicals, Industrials, Generic Corporate.
- Mỗi template có bộ KPI, trọng tâm phân tích và phương pháp định giá ưu tiên riêng.
- Bảng so sánh hiển thị Doanh nghiệp / Trung bình ngành / Trung vị ngành / số DN có dữ liệu / chênh lệch.
- Không bịa KPI vận hành chưa có trong Vnstock: các KPI như presales, SSSG, công suất, backlog... được coi là focus/KCF và chỉ tính khi có dữ liệu bổ sung.
- Report 30 trang sử dụng template chuyên ngành để thay đổi nội dung phân tích theo ngành.


## V8.4 - INTELLIGENT ANALYST
Tự diễn giải KPI so với trung bình ngành, nhận diện tín hiệu chéo, đối chiếu benchmark Vnstock peer_compare và đưa nhận định vào report 30 trang. Không tự tạo dữ liệu thiếu; kết quả không phải khuyến nghị mua/bán.


## V8.5 – DUAL MISSION ARCHITECTURE
Platform có đúng 2 nhiệm vụ cốt lõi:
1. **Phân tích giá cổ phiếu**: Fundamental → Industry Benchmark → Intelligent Analyst → Valuation Regime → Valuation → M&A/Control Premium → Stress → báo cáo 30 trang.
2. **Xếp hạng tín nhiệm**: Macro/Industry → Business Risk → Financial Risk → Anchor → notch/adjustment → SACP/SCA → Support → ICR → Rating Sensitivity → báo cáo 30 trang.

Hai nhiệm vụ dùng chung Data Layer, ICB auto-classification và Industry Benchmark nhưng không trộn methodology hoặc kết luận.
Vnstock chỉ chạy LOCAL; Streamlit Cloud đọc CSV/model outputs từ repo.
`RUN_VALUATION_REGIME_REFRESH.bat` cập nhật benchmark định giá ngành/thị trường + Intelligent Analyst.


## V8.6 – THREE CREDIT RATING METHODOLOGIES
Rating Router tự động chọn đúng 1 trong 3 methodology: BANK / SECURITIES / CORPORATE. Bank và Securities dùng BICRA/Anchor/SACP theo tài liệu phương pháp; Corporate dùng 4 nhóm rủi ro thang 1–6 → weighted Anchor → Modifiers → SCA → Support → ICR. Không dùng chung một scorecard cho ba loại hình.


## V8.7 – Rating Committee + Fair Value Range
Kế thừa toàn bộ V8.6 và các sửa đổi trước đó. Không thay kiến trúc Vnstock Bronze.
- Nhiệm vụ 1: thêm Bear/Base/Bull + Strategic/M&A Value; không hard-code giả định STB cho doanh nghiệp khác.
- Nhiệm vụ 2: giữ nguyên 3 methodology độc lập và thêm Rating Committee Waterfall, checklist, audit trail.
- Hai nhiệm vụ dùng chung Data Layer/Industry Benchmark nhưng không trộn logic định giá và XHTN.


## V8.8 - PROFESSIONAL REPORT ENGINE
Kế thừa V8.7 và toàn bộ các sửa đổi trước đó.
- Giữ 2 nhiệm vụ cốt lõi: Phân tích giá cổ phiếu và Xếp hạng tín nhiệm.
- Giữ 3 methodology XHTN độc lập: Ngân hàng / CTCK / Doanh nghiệp phi tài chính.
- Report Word: A4, Lato 11 phần chữ, bảng/biểu đồ 10, justify.
- Bỏ cơ chế cưỡng bức 1 mục = 1 trang; report tự dồn trang, chỉ page-break tại chương lớn.
- Biểu đồ rộng gần hết chiều ngang trang A4; chuỗi thời gian được sort cũ -> mới; 1 chart/1 KPI để tránh rối.
- Việt hóa tên KPI và số theo định dạng Việt Nam.
- Báo cáo Phân tích giá: Intelligent Analyst + peer + Bear/Base/Bull + Strategic/M&A.
- Báo cáo XHTN: methodology router + waterfall + SACP/SCA + Support + ICR + audit trail.
- Hai BAT riêng: RUN_REPORT_PHAN_TICH_GIA.bat và RUN_REPORT_XHTN.bat.


## V8.9 - DECISION INTELLIGENCE
Kế thừa V8.8 và toàn bộ sửa đổi trước, trừ phần xung đột với nâng cấp mới.
- Giữ 2 nhiệm vụ cốt lõi và 3 methodology XHTN độc lập.
- Thêm Data Quality/Confidence Engine: coverage dữ liệu cốt lõi theo loại hình.
- Thêm Valuation Triangulation: Base + relative regime + Bear/Bull + Strategic/M&A, kèm analytical confidence.
- Thêm Rating Evidence Ledger: phân biệt calculation/methodology với judgment cần chuyên viên xác nhận.
- Report 30 trang tiếp tục Lato 11, bảng/chart 10, số Việt Nam, chart full-width và timeline cũ -> mới.
- Không hard-code giả định STB cho doanh nghiệp khác; không biến rating tự động thành rating chính thức.


## V8.10 - CLEAN ARCHITECTURE & ONE-CLICK OPERATIONS
Kế thừa toàn bộ engine và sửa lỗi từ V8.9; chỉ dọn interface vận hành ở root.

### Root operation files
- `CONTROL_CENTER.bat`: menu vận hành chính.
- `START_LOCAL_APP.bat`: chạy Streamlit local.
- `SETUP_LOCAL_ENV.bat`: tạo/cập nhật môi trường local.
- `RUN_FAST.bat`: rebuild benchmark/analyst từ dữ liệu hiện có.
- `RUN_REFRESH_ONE_COMPANY.bat`: cập nhật một ticker.
- `RUN_FULL_REFRESH.bat`: orchestration full market.
- `RUN_REPORT.bat`: xuất báo cáo Phân tích giá / XHTN / cả hai.

### Legacy
Các BAT cũ không bị xóa mà chuyển vào `tools/legacy_operations/` để bảo toàn khả năng khôi phục/audit.
`__pycache__` được loại khỏi package và thêm vào `.gitignore`.

Hai nhiệm vụ cốt lõi vẫn giữ nguyên:
1. Phân tích giá cổ phiếu / định giá / M&A.
2. Xếp hạng tín nhiệm theo 3 methodology độc lập.


## V8.10.1 - STREAMLIT RUNTIME FIX
- Xóa import legacy `securities_rating`, `corporate_rating`, `DESC6`, `DESC4` từ `multisector_rating`.
- Xóa duplicate legacy rating UI còn sót sau Clean Architecture.
- XHTN trong dashboard và report cùng dùng duy nhất `three_methodology_rating.rate_company`.
- Giữ nguyên 3 methodology: Ngân hàng / CTCK / Doanh nghiệp phi tài chính.
- Không thay đổi Data Layer, Industry Benchmark, Valuation, Decision Intelligence hay Professional Report Engine.


## V8.10.2 - STREAMLIT SECTOR TEMPLATE FIX
- Fix `NameError: sector_template is not defined` tại tab Hồ sơ doanh nghiệp.
- Khởi tạo `sector_template_key, sector_template = get_template(EntityType, Sector)` ngay sau khi chọn doanh nghiệp.
- Giữ nguyên V8.10.1 fix: một XHTN router duy nhất cho 3 methodology.
- Không thay đổi valuation, peer benchmark, data layer hay report engine.


## V8.11 - DEEP ANALYSIS & PEER CHARTS
Mỗi chương report có thêm phân tích định lượng so với trung bình/trung vị ngành, peer bar charts theo từng KPI, ROE-P/B scatter và phụ lục peer chuyên sâu. Kế thừa toàn bộ V8.10.2.


## V8.12 - ANALYST NARRATIVE
- Kế thừa toàn bộ V8.11.
- Mỗi chương trọng yếu bổ sung lớp phân tích 4 câu hỏi: Số liệu nói gì? Tại sao đáng chú ý? So với peer thế nào? Tác động tới định giá/XHTN ra sao?
- Tách logic implication giữa báo cáo phân tích cổ phiếu và báo cáo XHTN.
- Không tự bịa nguyên nhân: nếu dữ liệu chưa đủ, report chuyển thành driver cần kiểm chứng.
- Giữ peer charts, individual-peer bars, ROE-P/B scatter, trung bình/trung vị ngành.


## V8.13 - METHODOLOGY KPI EXPANSION
- Mở rộng ma trận chỉ tiêu theo 3 methodology: Ngân hàng, Công ty chứng khoán, Doanh nghiệp phi tài chính.
- Báo cáo không còn chỉ 5 KPI; thêm nhóm quy mô, hiệu quả, vốn/đòn bẩy, vị thế rủi ro, nguồn vốn/thanh khoản và định giá.
- Tự tính các tỷ lệ có thể suy ra từ BCTC: Cho vay/TTS, Tiền gửi/TTS, VCSH/TTS, NII/Operating income, EBITDA margin, Debt/Assets, CFO/Debt, FOCF/Debt, CAPEX/Revenue...
- CTCK hỗ trợ thêm vốn khả dụng, thị phần môi giới, tài sản khách hàng, dư nợ margin, margin/VCSH, ICGR khi nguồn/manual input có dữ liệu.
- Doanh nghiệp phi tài chính bám methodology dòng tiền/đòn bẩy: Debt/EBITDA, CFO/Debt, FOCF/Debt, EBITDA margin, current ratio...
- Chỉ tiêu thiếu dữ liệu hiển thị N/A – cần bổ sung nguồn; tuyệt đối không tự bịa.
- Peer appendix lấy danh sách KPI theo methodology thay vì danh sách cố định ngắn.


## V8.14 - UI & REPORT CLEANUP
- Gộp 6 tab phân tích nền tảng thành 1 tab `Hồ sơ doanh nghiệp`.
- Gộp Định giá + M&A/Quyền kiểm soát + Tái cấu trúc + Kịch bản/Stress + Intelligent Analyst thành 1 tab `Phân tích, định giá & M&A`.
- Giữ 1 tab riêng `Báo cáo Xếp hạng tín nhiệm`.
- Chuyển nút xuất report xuống cuối đúng 2 tab nghiệp vụ chính; bỏ tab Báo cáo & Quản trị riêng.
- `Dữ liệu & Quản trị` chỉ giữ coverage/universe/governance.
- Fix KeyError do khác tên cột KPI giữa V8.12/V8.13 bằng normalize columns trước khi hiển thị.
- Không còn show JSON/code raw trong tab XHTN.
- Report: bảng KPI chỉ xuất ở các chương cần thiết; loại bỏ việc lặp bảng nhiều trang liên tiếp.
- Report: bỏ page-break cưỡng bức ở mọi mục; chỉ ngắt tại chương lớn để dồn trang và giảm khoảng trắng.
- Matrix methodology có guard để chỉ xuất một lần.
