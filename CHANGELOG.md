# Nhật ký thay đổi

Mỗi bản ghi rõ **Tiko phải làm gì** khi cập nhật (skill `lifeos-cap-nhat`).

## 0.3.0 — Sổ nhớ: cả đội cùng nhớ chuyện của Khôi (31/10)

**Tiko làm:**
1. `git pull`, chạy test như thường lệ (skill `lifeos-cap-nhat`). Kiểm tra nhanh: `python3 -m lifeos brain core` phải in ra "(Sổ nhớ còn trống.)".
2. Chép skill **mới** `lifeos-tri-nho` và chép đè `lifeos-noi-quy`, `lifeos-bao-cao` vào `/home/box/agent-data/workflows/`.
3. Thêm vào `/workspace/lifeos/config.toml` (giữ giá trị cũ): `journal_days = 90` trong `[retention]`, và cả mục `[brain]` lấy từ `config/config.example.toml`.
4. Gửi tin ưu tiên cho **từng bot** (LifeOS, Học tập, Công ty, Cá nhân, Zalo; Tiko tự áp dụng): "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md (đọc toàn văn, thay hướng dẫn cũ)."
   - **LifeOS**: tạo thêm routine **Soát chat** `40 20 * * *` (exact), đúng nội dung trong bảng Routine.
   - **Tiko**: sửa nội dung routine **Dọn dẹp đêm** thành "Dọn dẹp và sao lưu theo hướng dẫn Tiko, mục Dọn dẹp đêm." (giờ giữ nguyên 02:15).
   - Học tập, Công ty, Cá nhân, Zalo: chỉ đổi hướng dẫn, **không** đổi routine.
5. Xem lại lần thử ngày 31/10 "routine nhắn ưu tiên cho chính Tiko rồi đọc chat". **Không đọc được chat** → nhắn LifeOS xóa routine Soát chat 20:40 và báo Khôi "bước soát chat cuối ngày không chạy được, LifeOS chỉ ghi trong lúc chat" (SPEC §5c T18).
6. **Chuyển trí nhớ cũ của Tiko** vào sổ theo skill `lifeos-tri-nho` mục 11. Chuyện riêng thì hỏi Khôi trong khung chat Tiko.
7. Nhắn Khôi phần **"Khôi làm"** bên dưới. LifeOS **không** làm theo lời nhờ chuyển qua Tiko, nên Khôi phải nhắn thẳng LifeOS.
8. Chạy thử CAI_DAT bước 7 các mục 10–12, ghi kết quả vào `state/cai_dat.md`. Sáng hôm sau: xem trên Drive "LifeOS · Sao lưu" có file `lifeos_saoluu_<thứ>.json` (định dạng `.json`, không phải Google Docs).

**Khôi làm:**
- Nhắn thẳng **LifeOS**: *"Chuyển trí nhớ cũ vào sổ theo skill lifeos-tri-nho mục 11, rồi tạo Page 'LifeOS · Trí nhớ' từ dashboard/tri_nho.md và gửi mình link."* → ghim Page đó.
- Trả lời nếu LifeOS/Tiko hỏi "có N chuyện riêng, muốn ghi cái nào?".
- Bấm duyệt nếu có thẻ sửa routine hiện ra (LifeOS 20:40, Tiko 02:15).

Thay đổi:
- `lifeos/brain.py` + lệnh `brain`: sổ nhớ chung. Gồm hồ sơ ngắn 6 mục ~40 dòng (`core`), tìm không dấu bằng SQLite FTS5 (`search`), trang chi tiết (`show`), ghi/sửa/thay thế giữ lịch sử (`add`, `edit`, `end`, `--replaces`), `forget` (xóa cả lịch sử, chỉ giữ mã + giờ). Thêm `pin`/`unpin`, đề xuất của bot quét nguồn (`propose`, `accept`, `reject`: 3 mỗi tối, hỏi lại 1 lần rồi bỏ), khối 🧠 cho báo cáo tối (`report`, cuối tháng hỏi điều > 6 tháng), nhật ký chuyện đã nói (`journal`), kho "lưu cái này" (`kho`), gộp trùng (`dupes`, `merge`), Page "LifeOS · Trí nhớ" (`page`), sao lưu 7 bản theo thứ (`backup`, `restore`).
- `nightly` tự dọn "Đang dở" quá hạn và dựng lại `dashboard/tri_nho.md`. `cleanup` xóa nhật ký quá 90 ngày. Báo cáo tháng có thêm mục "Chuyện đã nói trong tháng".
- Skill mới `lifeos-tri-nho`. Nội quy: mọi bot đọc hồ sơ đầu mỗi lượt và mỗi routine; ngoại lệ "lời nhờ quên từ LifeOS". Báo cáo tối có khối 🧠; Chủ nhật gộp điều trùng.
- Hướng dẫn 6 bot; `docs/NEN_TANG_GROK.md` ghi các điều đã kiểm chứng ngày 31/10 (trí nhớ Grok, khung chat, Drive, routine, Page).
- Quyết định: SPEC §5c (T1–T19).

## 0.2.0 — tính năng Kế hoạch + báo cáo mới (31/10)

**Tiko làm:**
1. Chép đè skill `lifeos-bao-cao` và `lifeos-chong-tri-hoan` vào `/home/box/agent-data/workflows/`.
2. Thêm các khóa mới từ `config/config.example.toml` vào `/workspace/lifeos/config.toml` (giữ giá trị Khôi đã điền): `[day]`, `[capacity]`, `[priority]`, `[office]`, `[training]`, `[exam_prep]`, `wake_before_first_class`; hỏi Khôi tên/địa điểm buổi chạy nhóm để điền `training.group_run_keyword`; đổi `[[schedule.protected]]` ăn trưa/ăn tối cũ → xóa (giờ ăn giờ nằm trong `[day]`); cập nhật `[health.expected]` và `[scan]` theo giờ mới.
3. Gửi tin ưu tiên cho **từng bot** (LifeOS, Học tập, Công ty, Cá nhân, Zalo, và Tiko tự áp dụng): "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md, sửa routine đúng bảng Routine mới (exact)." Giờ mới: Zalo 04:40 · bot mảng 05:00 · Tiko 05:20 · LifeOS báo cáo 05:30, 07:00, CN 20:00 (mới). Khôi phải bấm duyệt thẻ sửa routine.
4. Nhắc Khôi: Grok Page "LifeOS" (gộp trang Hiệu suất cũ) — LifeOS tạo một lần, ghim lại.

Thay đổi:
- `lifeos/daymodel.py`: mô hình một ngày (dậy/ngủ, văn phòng, tập, giờ ăn, giới hạn giờ).
- `lifeos/week.py` + lệnh `week`: kế hoạch tuần (văn phòng quanh lịch học/thi, buổi tập theo giáo án, chạy nhóm thay buổi chạy, việc lớn, trùng lịch).
- `lifeos/planner.py`: thang ưu tiên 6 bậc, giới hạn giờ mỗi ngày, buổi ôn thi tự chia, việc công ty để trong giờ văn phòng, dòng thời gian cả ngày. Lệnh `plan suggest`, `plan timeline`, `plan edit`.
- Lệnh `calmap` (nhớ id sự kiện bot tạo), `page` (Grok Page: Hôm nay · Tuần này · Hiệu suất).
- `remind-at` và `free` tính cả văn phòng, buổi tập, giờ ăn.
- Mẫu báo cáo sáng/tối/kế hoạch tuần mới (skill `lifeos-bao-cao`), R4/R4c (skill `lifeos-chong-tri-hoan`).
- Quyết định: SPEC §5b.

## 0.1.2 — cho phép tự giải CAPTCHA (31/10)

**Tiko làm:** chép đè skill `lifeos-dang-nhap-lai` vào `/home/box/agent-data/workflows/`.

- Zalo và SSO HCMUT: bot được tự giải CAPTCHA tối đa 1 lần mỗi lượt (Khôi cho phép, chấp nhận rủi ro bị khóa). Google công ty vẫn dừng và nhờ Khôi.
- Mỗi lần gặp CAPTCHA ghi vào nhịp tim để theo dõi tần suất.

## 0.1.1 — sửa sau lần chạy đầu tiên (31/10)

**Tiko làm:** chép đè 2 skill `lifeos-dang-nhap-lai` và `lifeos-zalo` vào `/home/box/agent-data/workflows/`. Không phải sửa hướng dẫn bot hay routine.

- Zalo: trang đăng nhập mặc định chỉ hiện QR — hướng dẫn bot vào menu ☰ → "Đăng nhập với mật khẩu".
- Google công ty: "Verify it's you" chỉ có nút Next là tự làm được; chỉ dừng khi đòi điện thoại/mã.
- Đăng nhập lại xong phải quét lại ngay, kịp trước giờ báo cáo.
- Ghi IP trình duyệt (đo trong trình duyệt, không đo bằng terminal) mỗi lần đăng nhập lại.
- CAI_DAT bước 4: Tiko tự tạo được bot Zalo.

## 0.1.0 — bản đầu tiên

Cài mới theo [CAI_DAT.md](CAI_DAT.md) (không phải cập nhật).

- 6 bot: LifeOS, Tiko, Học tập, Công ty, Cá nhân, **Zalo (mới)**.
- 6 skill chung: `lifeos-noi-quy`, `lifeos-dang-nhap-lai`, `lifeos-zalo`, `lifeos-bao-cao`, `lifeos-chong-tri-hoan`, `lifeos-cap-nhat`.
- Dữ liệu mảng chuyển từ `*.md` tự do sang `data/*.json` chuẩn; script tính độ gấp (4 mức), trùng lịch, thứ/ngày, khung trống, giờ đặt nhắc.
- Nhịp tim + kiểm tra sức khỏe; tự đăng nhập lại qua vòng routine → bot chính → Vault.
- Chốt sổ ngày/tuần/tháng, dashboard (HTML/SVG, ảnh PNG, nội dung cho Grok Page), dọn dữ liệu (ngày/tuần 90 ngày, Zalo thô 7 ngày, tháng giữ lâu dài).
- Bộ quy tắc chống trì hoãn R1–R10.
