---
name: lifeos-zalo
description: Cách bot Zalo đọc Zalo Web (chat.zalo.me) cho LifeOS — lọc theo thẻ, đọc tin mới, khôi phục dấu chưa đọc, ghi data/zalo.json. Chỉ bot Zalo dùng; bot khác không được mở Zalo.
---

# Đọc Zalo cho LifeOS

Chỉ bot **Zalo** làm việc này. Các bot khác lấy phần của mình trong `/workspace/lifeos/data/zalo.json`.

## Trước khi bắt đầu

1. Đọc `/workspace/lifeos/config.toml` mục `[zalo]`: danh sách thẻ → mảng, `restore_unread`.
2. Đọc `/workspace/lifeos/state/zalo.json` (nếu có): lần trước đã đọc tới tin nào ở từng hội thoại.
3. Mở `chat.zalo.me` trong **một** tab duy nhất. Kẹt ở "Đang đăng nhập..." quá 60 giây → tải lại trang một lần. Vẫn kẹt hoặc thấy trang đăng nhập (kể cả trang chỉ có mã QR) → làm theo skill `lifeos-dang-nhap-lai`: đăng nhập bằng mật khẩu qua **menu ☰ → "Đăng nhập với mật khẩu"**, tối đa 1 lần.
4. Danh sách chat trống / "Chưa có tin nhắn" → lịch sử chưa đồng bộ. **Không bấm "Đồng bộ ngay"** (cần Khôi xác nhận trên điện thoại). Ghi `"status": "needs_sync"` và báo Tiko.

## Với mỗi thẻ (Công việc, Trường học, Bạn bè, Gia đình)

1. Bật bộ lọc **Phân loại** = thẻ đó.
2. Với mỗi hội thoại có tin mới kể từ lần trước:
   1. **Ghi nhớ trước khi mở:** hội thoại đang hiện "chưa đọc" (chấm/số đỏ) không? → `was_unread`.
   2. Mở hội thoại, đọc các tin MỚI (sau mốc trong `state/zalo.json`; lần đầu: 24 giờ gần nhất).
   3. Nếu `was_unread` và `restore_unread = true` → nhấn chuột phải (hoặc nút "…") vào hội thoại trong danh sách → **"Đánh dấu chưa đọc"**. Ghi `restored_unread: true`. Không tìm thấy lựa chọn này → ghi `restored_unread: false` và báo Tiko một lần.
   4. Hội thoại vốn đã đọc rồi → giữ nguyên, không đánh dấu gì.
3. **Xóa bộ lọc** trước khi sang thẻ khác và khi xong việc.

Không trả lời, không thả cảm xúc, không rời nhóm, không mở link lạ, không tải tệp đính kèm (chỉ ghi tên tệp).

## Ghi kết quả

`/workspace/lifeos/data/zalo.json` (ghi đè cả file):

```json
{
  "generated_at": "2026-11-02T05:18+07:00",
  "status": "ok",
  "detail": null,
  "conversations": [
    {
      "tag": "Công việc",
      "domain": "congty",
      "name": "Nhóm dự án ABC",
      "type": "group",
      "was_unread": true,
      "restored_unread": true,
      "messages": [
        {"from": "Anh Minh", "at": "2026-11-01T21:40+07:00",
         "text": "Khôi ơi mai gửi anh bản báo cáo trước 10h nhé",
         "mentions_khoi": true, "attachments": []}
      ]
    }
  ]
}
```

- `status`: `ok` · `needs_login` · `needs_sync` · `error`. Không đọc được → vẫn ghi file với `conversations: []` và `status` tương ứng.
- `mentions_khoi`: tin gọi tên Khôi, @Khôi, hoặc hỏi thẳng Khôi.
- Cập nhật `/workspace/lifeos/state/zalo.json`: `{ "<tên hội thoại>": "<thời điểm tin cuối đã đọc>" }`.

Cuối cùng: `python3 -m lifeos status zalo --type full --ok --source zalo=ok` (hoặc trạng thái tương ứng). Script tự lưu bản sao 7 ngày rồi xóa.
