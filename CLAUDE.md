# Hướng dẫn cho Claude khi làm việc với repo này

## Bối cảnh

Repo này (`lucasnguyen1925/lifeos`, trước 0.7.0 tên `lifeos-grok`) là **bộ cài LifeOS** cho một đội bot chạy trên **Grok Bot** (xAI). Chủ sở hữu là **Khôi**: sinh viên, đang làm part-time, **không rành kỹ thuật**, nói tiếng Việt thân mật. Luôn trả lời Khôi bằng **tiếng Việt, dễ hiểu, không thuật ngữ** (nếu buộc phải dùng thì giải thích ngay).

- **Repo không tự chạy gì.** Các bot Grok `git pull` repo về máy cloud dùng chung (`/workspace/lifeos-grok` — tên thư mục giữ nguyên dù repo đã đổi tên) rồi làm theo. Dữ liệu và cấu hình cá nhân nằm trên máy bot (`/workspace/lifeos/`, `config.toml`), mật khẩu nằm trong Vault của Grok.
- **Claude không vào được máy của Grok.** Muốn biết trạng thái thật → soạn sẵn tin để Khôi gửi **bot giữ vai Vận hành**, yêu cầu bot **làm thử thật** và báo kết quả, Khôi dán lại.

Đọc trước khi làm bất cứ thay đổi nào:

1. `SPEC.md` — mọi quyết định đã chốt (§5b là tính năng Kế hoạch).
2. `CHANGELOG.md` — các bản đã phát hành và bot Vận hành phải làm gì khi cập nhật.
3. `docs/NEN_TANG_GROK.md` — những gì đã kiểm chứng thực tế về Grok Bot (đừng đoán lại).
4. `bots/*.md` (hướng dẫn từng vai), `skills/*/SKILL.md` (skill dùng chung) và `persona/` (tính cách chung: IDENTITY.md + SOUL.md) khi đụng tới hành vi bot.

## Quy tắc bắt buộc

- **Grill trước, sửa sau.** Khôi muốn thay đổi/thêm tính năng → hỏi từng câu một, mỗi câu kèm đề xuất, cho tới khi chốt. Khôi nói "chốt" mới sửa code. Quyết định mới ghi vào `SPEC.md`.
- **Repo PUBLIC — không bao giờ ghi thông tin cá nhân**: tên người thật ngoài "Khôi", tên công ty, tên nhóm Zalo, mã môn/mã khóa học, số tài khoản/email, địa điểm thường lui tới (nơi chạy bộ, phòng gym), thói quen nhạy cảm. Ví dụ trong tài liệu/test dùng tên chung ("bạn A", "Công viên X"). Giá trị thật để bot Vận hành hỏi Khôi rồi ghi vào `config.toml` trên máy bot. Trước mỗi commit: `grep` lại.
- **Repo chỉ ghi vai, không ghi tên riêng của bot** (0.7.0): LifeOS, Vận hành, Học tập, Công ty, Cá nhân, Zalo. Bot thật nào giữ vai nào ghi trên máy bot (`bando giu-vai`). Tên cũ chỉ còn trong lịch sử CHANGELOG, SPEC §5h và đoạn code nhận mã cũ `tiko`.
- **Việc tất định → script Python** (`lifeos/`), việc cần hiểu/diễn đạt → hướng dẫn bot. Thứ/ngày, độ gấp, xếp giờ, chỉ số luôn do script tính.
- **Chỉ thư viện chuẩn Python ≥ 3.11** (máy bot: 3.13, không cài được pip vào hệ thống).
- An toàn: bot chỉ đọc; gửi/nộp/đăng ký/thanh toán/xóa luôn cần Khôi duyệt **trong khung chat của bot thực hiện** (Grok không tính lời duyệt do bot khác chuyển lại). Không lách CAPTCHA/2FA, trừ ngoại lệ Khôi đã chấp nhận ghi trong SPEC (CAPTCHA Zalo + SSO trường, 1 lần/lượt).

## Quy trình ra bản mới

1. Sửa code/tài liệu trên branch `claude/lifeos-grok`.
2. `python3 -m pyflakes lifeos tests` (nếu có) và `python3 -m unittest discover -s tests` — phải OK. Thêm test cho logic mới.
3. Tăng số bản trong `CHANGELOG.md`, ghi rõ mục **"Vận hành làm:"** từng bước (chép skill nào, thêm khóa config nào, bot nào phải cập nhật hướng dẫn/routine, Khôi có phải bấm duyệt gì). Cập nhật `SPEC.md` nếu có quyết định mới.
4. `grep` thông tin cá nhân → commit → push branch → đưa vào `main` bằng fast-forward (`git push origin claude/lifeos-grok:main`). Không ghi đè lịch sử.
5. Báo Khôi ngắn gọn: bản mới có gì, câu cần nhắn bot Vận hành (thường: *"Cập nhật LifeOS lên bản X, làm theo CHANGELOG"*), Khôi phải làm gì, phần nào **chưa kiểm chứng được** trên máy Grok.

## Đội bot (tóm tắt)

LifeOS (trợ lý, người duy nhất nói chuyện nội dung với Khôi) · Vận hành (giữ LifeOS luôn chạy, đúng giờ: cài đặt, sức khỏe, đăng nhập lại, sao lưu; chạy ngầm) · Học tập · Công ty · Cá nhân (quét nguồn từng mảng, ghi `data/*.json`) · Zalo (bot duy nhất mở Zalo Web). Chi tiết: `README.md`, `SPEC.md` §4.
