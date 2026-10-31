# Nhật ký thay đổi

Mỗi bản ghi rõ **Tiko phải làm gì** khi cập nhật (skill `lifeos-cap-nhat`).

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
