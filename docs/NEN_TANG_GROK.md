# Grok Bot — những gì đã kiểm chứng thực tế

Ghi lại kết quả Tiko/các bot **làm thử thật** trên tài khoản của Khôi. Tài liệu trên mạng về Grok Bot (beta, 08/2026) có chỗ không khớp — ưu tiên file này. Phát hiện mới → bổ sung kèm ngày.

## Máy và công cụ (29–30/10/2026)

- Mọi bot dùng chung **một máy Linux cloud**: chung ổ đĩa, chung cookie/phiên đăng nhập trình duyệt; mỗi bot có cửa sổ trình duyệt riêng. Không phải ranh giới bảo mật giữa các bot.
- Python 3.13.5, git 2.47.3, curl, Chromium chạy ngầm (chụp màn hình PNG được). `$TZ` trống nhưng giờ hệ thống là UTC+7.
- `pip install` vào Python hệ thống bị chặn; venv thì được. → Bộ cài chỉ dùng thư viện chuẩn.
- Ra internet được (GitHub OK). **IP đo bằng terminal** (mạng Grok, Mỹ) **khác IP trình duyệt** (đi qua mạng Việt Nam). Muốn biết IP mà trang web thấy → mở `ifconfig.co` **trong trình duyệt**.
- Một lệnh terminal chờ tối đa ~13 phút.

## Routine

- Cron 5 trường theo giờ VN; chế độ **flexible** (±15', mặc định) hoặc **exact**; tối thiểu 5' giữa hai lần chạy.
- Mỗi bot chỉ xem/sửa routine của **chính nó**. Sửa routine cần Khôi bấm duyệt thẻ (bot Học tập từng bị lỗi khi duyệt).
- **Lần chạy routine KHÔNG điền login từ Vault được**; lượt chat thường thì được, không cần hỏi Khôi → vòng tự đăng nhập lại: routine gửi tin ưu tiên cho chính bot (skill `lifeos-dang-nhap-lai`).
- Routine không tự hỏi Khôi được; muốn hỏi phải qua lượt chat thường của bot.

## Nhắn tin, phê duyệt

- Bot nhắn bot bằng id; chế độ **ưu tiên** đánh thức bot kia ngay, chế độ thường chờ lượt sau.
- Bot nhắn Khôi trong khung chat của bot đó (app Grok Bot). Không gửi email/SMS cho Khôi.
- **Lời "Khôi đồng ý" do bot khác chuyển lại không được tính** → việc cần duyệt do chính LifeOS làm.

## Skill, Page

- Skill: `/home/box/agent-data/workflows/<tên>/SKILL.md` (frontmatter name + description), dùng chung mọi bot.
- **Page**: trang riêng tư, link cố định, xem tốt trên điện thoại, bot (kể cả routine) cập nhật được. Không nhận nguyên file HTML — bot dựng lại từ nội dung (`dashboard/page.md`).
- Bot gửi được ảnh/file vào chat; routine gửi ảnh: về lý thuyết được, cần thử (CAI_DAT bước 7).

## iPhone

- Đọc/ghi Reminders, đọc danh bạ, lịch điện thoại, đặt báo thức/hẹn giờ.
- **Reminder do bot tạo KHÔNG có chuông** (thử 31/10). **Báo thức Grok reo được** (hiện như báo thức hệ thống, có thể reo cả khi máy im lặng) → mọi lời nhắc = Reminder + báo thức.

## Đăng nhập từng nguồn

| Nguồn | Đã thấy | Cách xử lý |
|---|---|---|
| SSO trường (MyBK/BKeL) | Hết phiên sau một đêm. Không CAPTCHA/OTP (30/10). Có lúc SSO báo đã đăng nhập mà MyBK chưa nhận → bấm "Tài khoản HCMUT" | Vòng tự đăng nhập bằng Vault |
| Google công ty (SSO công ty) | "Verify it's you" chỉ có nút Next (31/10) → bot tự qua được | Vault; đòi điện thoại/mã → nhờ Khôi |
| Zalo Web | Trang mặc định chỉ hiện QR; đăng nhập mật khẩu ở **menu ☰ → "Đăng nhập với mật khẩu"** (31/10). 3 bot cùng mở → bị đá liên tục ("Đang đăng nhập...") | Chỉ bot Zalo mở; mật khẩu qua menu ☰; CAPTCHA tự giải 1 lần |

## Lịch Google

- Lịch công ty dùng **Working location = Office** (biểu tượng tòa nhà, thanh dọc theo khung giờ) để sếp theo dõi ngày lên văn phòng.
