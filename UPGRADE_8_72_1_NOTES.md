# V8.72.1 Hotfix — Peer Benchmark Integrity + Bronze Retry Fix

## Lỗi được sửa
1. `NameError: name 'time' is not defined` trong `refresh_vnstock_multisector.py` khi dùng `--ticker-delay`.
2. Benchmark trước đây có thể bao gồm chính doanh nghiệp mục tiêu. Nếu chỉ HPG có dữ liệu thì `TB ngành = HPG`, khiến đường benchmark trùng hoàn toàn đường HPG.
3. Trung bình/trung vị peer trước đây vẫn có thể hiển thị với mẫu quá nhỏ. V8.72.1 yêu cầu tối thiểu **5 peer có dữ liệu** cho từng chỉ tiêu/kỳ; dưới ngưỡng sẽ để N/A và không vẽ đường benchmark.
4. ICB của Vnstock hiện quá rộng cho HPG (Nguyên vật liệu), nên peer có thể chọn các doanh nghiệp không tương đồng. V8.72.1 thêm file override peer chuyên ngành có thể chỉnh tay.

## Peer HPG khởi tạo
HSG, NKG, VGS, TVN, SMC, TLH, POM, HMC, TIS, DTL.

## Quy tắc benchmark mới
- Target không bao giờ tham gia tính mean/median của chính nó.
- Tối thiểu 5 peer có số liệu hợp lệ cho metric đó.
- Lịch sử cũng áp dụng ngưỡng 5 peer theo từng kỳ.
- UI đổi tên đường từ `Trung bình ngành` thành `Trung bình peer` để phản ánh đúng bản chất.

## File mới
- `config/dynamic_peer_overrides.csv`
- `scripts/refresh_target_peers.py`
- `RUN_REFRESH_PEERS.bat`

## Cách dùng ngay cho HPG
1. Copy patch đè lên project.
2. Chạy `RUN_REFRESH_PEERS.bat`, nhập `HPG`.
3. Script chỉ refresh 10 peer của HPG, Bronze-safe (1 worker, 3 giây/ticker), rồi rebuild peer map và benchmark HPG.
4. Nếu một số peer lỗi API, script lưu `data/failed_peers_HPG.csv`; có thể chạy lại sau.
5. Không cần chạy lại `RUN_FULL_REFRESH.bat` chỉ để sửa benchmark HPG.

## Lưu ý
Nếu chưa có tối thiểu 5 peer được refresh thành công, app sẽ chủ động không hiển thị đường `Trung bình peer`; đây là hành vi đúng, tránh benchmark giả do n=1.
