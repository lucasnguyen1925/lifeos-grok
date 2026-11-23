# Tính cách bot — IDENTITY.md và SOUL.md

Hai file mẫu này hình thành **cách cư xử** của bot (SPEC §5h). Dùng được cho **bất kỳ bot nào** trong đội, kể cả bot làm thêm việc khác ngoài LifeOS.

| File | Là gì | Dùng chung? |
|---|---|---|
| `IDENTITY.md` | Tên, vai trò, phong cách, emoji | Mỗi bot điền riêng 3 chỗ trống |
| `SOUL.md` | Cách làm việc, cách nói chuyện, luật của Khôi (phần KHÔI-LOCKED) | Giống nhau cho cả đội (chỉ thay `{TÊN_BOT}`) |

**Việc làm gì** nằm ở `bots/<vai>.md`; **cư xử thế nào** nằm ở đây. Hai bên khác nhau về việc → `bots/<vai>.md` thắng (luật 5 của SOUL).

## Cách áp cho một bot

1. Mở phần cài đặt tính cách của bot trên Grok (file IDENTITY.md và SOUL.md của bot đó).
2. Chép nội dung `persona/IDENTITY.md` vào, thay:
   - `{TÊN_BOT}` → tên Khôi đặt cho bot.
   - `{VAI_TRÒ}` → một trong các vai dưới đây.
   - `{EMOJI}` → một emoji (gợi ý: 🎩 · 🛰️ · ⚡).
3. Chép nội dung `persona/SOUL.md` vào, thay `{TÊN_BOT}`. Phần trên vạch KHÔI-LOCKED bot được tự sửa dần (có báo Khôi); phần giữa hai vạch chỉ Khôi sửa.
4. Nhắn bot: *"Từ nay bạn giữ vai <vai>. Đọc toàn văn /workspace/lifeos-grok/bots/<file>.md làm hướng dẫn, rồi chạy `python3 -m lifeos bando giu-vai <mã vai> \"<tên bạn>\"`."*

| Vai | Mã | Ghi vào `{VAI_TRÒ}` | Hướng dẫn |
|---|---|---|---|
| LifeOS (trợ lý) | `lifeos` | Trợ lý riêng — người duy nhất nói chuyện với Khôi về việc, lịch, tin nhắn | `bots/lifeos.md` |
| Vận hành | `vanhanh` | Vận hành — giữ LifeOS luôn chạy, chạy đúng giờ, làm ngầm phía sau | `bots/vanhanh.md` |
| Học tập | `hoctap` | Học tập — theo dõi mọi thứ của trường, làm ngầm, báo cho trợ lý | `bots/hoctap.md` |
| Công ty | `congty` | Công ty — theo dõi việc part-time, làm ngầm, báo cho trợ lý | `bots/congty.md` |
| Cá nhân | `canhan` | Cá nhân — theo dõi đời sống, làm ngầm, báo cho trợ lý | `bots/canhan.md` |
| Zalo | `zalo` | Zalo — bot duy nhất mở Zalo Web, thu tin cho cả đội | `bots/zalo.md` |

Bot mảng (Học tập, Công ty, Cá nhân, Zalo) không nói chuyện với Khôi hằng ngày; SOUL vẫn giúp chúng nói gọn, có số, không bịa khi Khôi ghé hỏi.

> Chưa kiểm chứng trên Grok: bot có tự đọc IDENTITY/SOUL mỗi lượt (kể cả routine) và có tôn trọng vạch KHÔI-LOCKED không (SPEC §15 mục 28).
