# Grok Bot — những gì đã kiểm chứng thực tế

Ghi lại kết quả Tiko/các bot **làm thử thật** trên tài khoản của Khôi. Tài liệu trên mạng về Grok Bot (beta, 08/2026) có chỗ không khớp — ưu tiên file này. Phát hiện mới → bổ sung kèm ngày.

## Máy và công cụ (29–30/10/2026)

- Mọi bot dùng chung **một máy Linux cloud**: chung ổ đĩa, chung cookie/phiên đăng nhập trình duyệt; mỗi bot có cửa sổ trình duyệt riêng. Không phải ranh giới bảo mật giữa các bot.
- Python 3.13.5, git 2.47.3, curl, Chromium chạy ngầm (chụp màn hình PNG được). `$TZ` trống nhưng giờ hệ thống là UTC+7.
- `pip install` vào Python hệ thống bị chặn; venv thì được. → Bộ cài chỉ dùng thư viện chuẩn.
- Ra internet được (GitHub OK). **IP đo bằng terminal** (mạng Grok, Mỹ) **khác IP trình duyệt** (đi qua mạng Việt Nam). Muốn biết IP mà trang web thấy → mở `ifconfig.co` **trong trình duyệt**.
- Một lệnh terminal chờ tối đa ~13 phút.
- (31/10) Một lần gọi lệnh terminal mất ~25–75 ms tính cả đi về (lệnh `python3 -c "print(1)"` tự nó ~10 ms). Không đo được thời gian cả lượt chat (phần lớn là lúc bot suy nghĩ).
- (31/10) SQLite 3.46.1 có sẵn FTS5 (tìm chữ nhanh) → sổ nhớ dùng được mà không cài gì.

## Routine

- Cron 5 trường theo giờ VN; chế độ **flexible** (±15', mặc định) hoặc **exact**; tối thiểu 5' giữa hai lần chạy.
- Mỗi bot chỉ xem/sửa routine của **chính nó**. Sửa routine cần Khôi bấm duyệt thẻ (bot Học tập từng bị lỗi khi duyệt).
- **Lần chạy routine KHÔNG điền login từ Vault được**; lượt chat thường thì được, không cần hỏi Khôi → vòng tự đăng nhập lại: routine gửi tin ưu tiên cho chính bot (skill `lifeos-dang-nhap-lai`).
- Routine không tự hỏi Khôi được; muốn hỏi phải qua lượt chat thường của bot.
- (31/10) Chế độ **exact vẫn trễ 1–6 phút**. Một routine thử (exact) **không chạy**, không rõ lý do. Bot tạo routine **cho chính nó** thì không hiện thẻ duyệt.
- (31/10) Routine **thấy** trí nhớ chung và một phần trí nhớ riêng, tìm trong trí nhớ được; **ghi đè được file trên Google Drive**.
- (31/10) Routine **không có công cụ đọc lịch sử chat** (cả chat của chính bot lẫn bot khác).

## Nhắn tin, phê duyệt

- Bot nhắn bot bằng id; chế độ **ưu tiên** đánh thức bot kia ngay, chế độ thường chờ lượt sau.
- Bot nhắn Khôi trong khung chat của bot đó (app Grok Bot). Không gửi email/SMS cho Khôi.
- **Lời "Khôi đồng ý" do bot khác chuyển lại không được tính** → việc cần duyệt do chính LifeOS làm.
- (31/10) Bot còn **từ chối cả việc nhỏ khi lời nhờ đi qua bot khác**: Tiko nhờ hộ LifeOS tạo thư mục Drive → LifeOS không làm; Khôi nhắn thẳng LifeOS → làm ngay. Ngược lại, LifeOS nhờ Tiko xóa một điều trong trí nhớ riêng → Tiko xóa, nhưng nói "lẽ ra nên hỏi Khôi trước" → không ổn định; ngoại lệ "quên" được ghi rõ trong nội quy.

## Khung chat (31/10/2026)

- **Không xóa được tin** trong khung chat (của chính bot lẫn bot khác). Chưa biết chat được giữ bao lâu.
- Chat dài: phần cũ chỉ còn bản tóm tắt trong đầu bot, nhưng lượt chat thường **mở lại được nguyên văn** (chưa đo lùi được bao xa).
- Lượt chat thường **đọc được khung chat của bot khác** (chỉ phần nói qua lại, không thấy bot kia làm gì bên trong).
- Khôi gửi được cho bot: **ảnh** (bot xem được nội dung, lưu được thành file trên máy), **link trang công khai** (đọc được), **video .mp4** (xem và nghe được). Tin thoại có giọng nói: chưa thử.

## Trí nhớ của Grok (31/10/2026)

- Mỗi bot có **trí nhớ riêng** (đang bật) + **một phần trí nhớ chung** cho mọi bot.
- Bot **tự ghi** vào trí nhớ riêng khi thấy điều đáng nhớ, không cần ai bảo (sau vài ngày Tiko đã có ~50 điều về Khôi). **Chưa tìm thấy cách tắt** cho từng bot.
- Trí nhớ riêng: chỉ một phần tự hiện đầu lượt, còn lại phải tìm. Tìm theo từ khóa, **tối đa 50 kết quả/lần** → không liệt kê đủ được cả danh sách.
- Trí nhớ chung: bot nào cũng ghi được; mỗi lượt (kể cả routine) mọi bot **thấy sẵn phần mới nhất**, phần cũ hơn phải tìm (thử: Tiko ghi một câu, LifeOS trả lời đúng mà không cần tìm). Mỗi điều là một câu ngắn; sức chứa chưa biết; chưa thấy chỗ cho Khôi xem/xóa trong app.
- **Chỉ bot đã ghi một điều trong trí nhớ chung mới xóa được điều đó**; bot khác chỉ ghi thêm câu mới để thay.
- → LifeOS **không dùng** trí nhớ Grok cho chuyện của Khôi; dùng sổ nhớ chung (SPEC §5c).

## Skill, Page

- Skill: `/home/box/agent-data/workflows/<tên>/SKILL.md` (frontmatter name + description), dùng chung mọi bot.
- **Page**: trang riêng tư, link cố định, xem tốt trên điện thoại, bot (kể cả routine) cập nhật được. Không nhận nguyên file HTML — bot dựng lại từ nội dung (`dashboard/page.md`).
- Bot gửi được ảnh/file vào chat; routine gửi ảnh: về lý thuyết được, cần thử (CAI_DAT bước 7).
- (31/10) Tạo được **Page thứ hai**. Bot **không xóa được Page** — Khôi tự xóa trong Library.

## Google Drive cá nhân (31/10/2026)

- LifeOS và Tiko đều có kết nối Drive cá nhân của Khôi (cùng loại kết nối).
- Bot tạo được thư mục, tải file lên, **ghi đè cùng một file** (mã file giữ nguyên, không sinh file mới) — cả trong lượt chat lẫn routine.
- File `.md`, `.json` do Tiko tải lên **giữ nguyên định dạng**, tải về giống từng byte; ảnh JPG giữ nguyên. Một lần LifeOS tải file chữ lên lại thành **Google Docs** → khi tải phải giữ định dạng gốc.
- Xóa = bỏ vào thùng rác, Drive tự xóa hẳn sau ~30 ngày; bot **không xóa vĩnh viễn** được.
- GitHub repo riêng tư: hiện **chưa ghi được** (kết nối GitHub không có lệnh ghi file, máy chưa đăng nhập GitHub).

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
