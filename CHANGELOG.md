# Nhật ký thay đổi

Mỗi bản ghi rõ **Tiko phải làm gì** khi cập nhật (skill `lifeos-cap-nhat`).

## 0.2.0 — báo cáo "kế hoạch lên đầu" (31/10)

**Tiko làm:**
1. Chép đè skill `lifeos-bao-cao` và `lifeos-chong-tri-hoan` vào `/home/box/agent-data/workflows/`.
2. Gửi tin ưu tiên cho LifeOS: "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/lifeos.md (đọc toàn văn, thay hướng dẫn cũ). Thêm routine mới 'Tự áp dụng kế hoạch sáng' `40 6 * * *` (exact) đúng bảng Routine." Khôi có thể phải bấm duyệt thẻ thêm routine.

Thay đổi:
- Lệnh mới `plan suggest`: chọn việc cần làm (hạn ≤ 3 ngày, 🔴, cần trả lời) và xếp vào khung trống thật — không đè giờ học/làm/ăn, trước hạn chót, việc nhanh gộp một khối đầu ngày, việc dài chia phiên 2 tiếng.
- Lệnh mới `plan edit` (dời giờ / bỏ khối).
- Báo cáo sáng mở đầu bằng "HÔM NAY LÀM GÌ": khối có giờ + ▶ bước đầu; "ok" → Reminder + báo thức từng khối; im lặng tới 06:40 → tự áp dụng.
- Báo cáo tối: tổng kết kế hoạch hôm nay (xong / chưa xong → dời, bỏ) + kế hoạch mai cùng định dạng.
- Mỗi việc chỉ xuất hiện một lần trong báo cáo; xa hơn 3 ngày chỉ ghi số lượng.

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
