# Nhật ký thay đổi

Mỗi bản ghi rõ **Tiko phải làm gì** khi cập nhật (skill `lifeos-cap-nhat`).

## 0.1.0 — bản đầu tiên

Cài mới theo [CAI_DAT.md](CAI_DAT.md) (không phải cập nhật).

- 6 bot: LifeOS, Tiko, Học tập, Công ty, Cá nhân, **Zalo (mới)**.
- 6 skill chung: `lifeos-noi-quy`, `lifeos-dang-nhap-lai`, `lifeos-zalo`, `lifeos-bao-cao`, `lifeos-chong-tri-hoan`, `lifeos-cap-nhat`.
- Dữ liệu mảng chuyển từ `*.md` tự do sang `data/*.json` chuẩn; script tính độ gấp (4 mức), trùng lịch, thứ/ngày, khung trống, giờ đặt nhắc.
- Nhịp tim + kiểm tra sức khỏe; tự đăng nhập lại qua vòng routine → bot chính → Vault.
- Chốt sổ ngày/tuần/tháng, dashboard (HTML/SVG, ảnh PNG, nội dung cho Grok Page), dọn dữ liệu (ngày/tuần 90 ngày, Zalo thô 7 ngày, tháng giữ lâu dài).
- Bộ quy tắc chống trì hoãn R1–R10.
