# Định dạng dữ liệu LifeOS

Áp dụng cho `/workspace/lifeos/data/hoctap.json`, `congty.json`, `canhan.json`. Ghi xong luôn chạy:

```bash
cd /workspace/lifeos-grok && python3 -m lifeos validate data/<mảng>.json
```

## Cấp ngoài cùng

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `bot` | ✔ | `"hoctap"`, `"congty"` hoặc `"canhan"` |
| `generated_at` | ✔ | Giờ ghi file, ISO có múi giờ: `"2026-11-02T05:41+07:00"` |
| `sources` | ✔ | `{ "<nguồn>": {"status": "ok" \| "needs_login" \| "error" \| "skipped", "detail": "…"} }` |
| `items` | ✔ | Danh sách việc/sự kiện (bên dưới) |
| `grades` | | Chỉ Học tập: `[{"course","name","score" (thang 10),"credits","term"}]` |

## Mỗi item

| Trường | Bắt buộc | Kiểu | Ghi chú |
|---|---|---|---|
| `id` | ✔ | chuỗi | **Cố định giữa các lần quét.** `<mảng>:<nguồn>:<mã gốc>`, ví dụ `hoctap:bkel:quiz:88123`, `congty:cal:<event id>`, `canhan:zalo:Gia đình:2026-11-01T21:40` |
| `domain` | ✔ | chuỗi | trùng `bot` |
| `source` | ✔ | chuỗi | tên nguồn, trùng khóa trong `sources` |
| `kind` | ✔ | chuỗi | xem bảng dưới |
| `title` | ✔ | chuỗi | ngắn, đủ hiểu: "Quiz 4 – Giải tích 2" |
| `status` | ✔ | chuỗi | `open` · `done` (đã nộp/đã làm ở nguồn) · `cancelled` |
| `due` | | ISO | hạn chót. Chỉ có ngày → `"2026-11-08"` (hiểu là 23:59) |
| `start`, `end` | | ISO | bắt buộc với `class`, `work_shift`, `meeting`, `event`; `exam` cần ít nhất `start` |
| `url` | | chuỗi | link để bấm vào làm ngay |
| `from` | | chuỗi | người gửi/người yêu cầu (tên như Khôi gọi) |
| `needs_reply` | | true/false | có người đang chờ Khôi trả lời |
| `mentions_khoi` | | true/false | tin nhắc/gọi tên Khôi |
| `received_at` | | ISO | lúc tin/mail/thông báo đến |
| `changed`, `change_note` | | | không bắt buộc — script tự phát hiện đổi hạn/giờ/phòng |
| `est_minutes` | | số nguyên | thời lượng ước tính (quiz: lấy từ BKeL) |
| `location` | | chuỗi | phòng học/phòng thi/địa điểm |
| `keywords` | | danh sách | từ khóa đáng chú ý |
| `notes` | | chuỗi | ghi chú ngắn. Trường nào không có trong bảng này → đưa vào đây |

### `kind`

| kind | Dùng cho |
|---|---|
| `deadline` | bài tập, việc có hạn nộp |
| `quiz` | quiz/bài kiểm tra LMS (có giờ đóng) |
| `exam` | lịch thi |
| `registration` | đợt đăng ký môn/thi (`start` = mở cổng, `due` = đóng) |
| `payment` | học phí, khoản phải đóng |
| `class` | buổi học |
| `work_shift` | ca/buổi lên công ty |
| `meeting` | cuộc họp, lời mời họp |
| `event` | sự kiện lịch khác |
| `notice` | thông báo trường/khoa/công ty |
| `message` | tin Zalo |
| `email` | mail |
| `task` | việc khác |

## Không ghi

- Độ gấp, "quan trọng", "ưu tiên" — **script tính**.
- Thứ trong tuần — **script tính** (`python3 -m lifeos date …`).
- Mật khẩu, mã, cookie, nội dung tài liệu nội bộ công ty.

## Ví dụ đầy đủ

```json
{
  "bot": "hoctap",
  "generated_at": "2026-11-02T05:41+07:00",
  "sources": {
    "bkel": {"status": "ok"},
    "mybk": {"status": "needs_login", "detail": "SSO hết phiên, đã nhờ chính mình đăng nhập lại"},
    "gmail_truong": {"status": "ok"},
    "cal_truong": {"status": "ok"},
    "zalo": {"status": "ok"}
  },
  "items": [
    {"id": "hoctap:bkel:quiz:88123", "domain": "hoctap", "source": "bkel", "kind": "quiz",
     "title": "Quiz 4 – Giải tích 2", "status": "open",
     "start": "2026-11-01T08:00+07:00", "due": "2026-11-08T23:59+07:00",
     "est_minutes": 20, "url": "https://lms.hcmut.edu.vn/mod/quiz/view.php?id=88123"},
    {"id": "hoctap:cal_truong:abc123", "domain": "hoctap", "source": "cal_truong", "kind": "class",
     "title": "Công nghệ phần mềm", "status": "open",
     "start": "2026-11-03T07:00+07:00", "end": "2026-11-03T09:00+07:00", "location": "H6-304"},
    {"id": "hoctap:mybk:exam:CO3001", "domain": "hoctap", "source": "mybk", "kind": "exam",
     "title": "Thi giữa kỳ CNPM", "status": "open",
     "start": "2026-11-12T13:00+07:00", "end": "2026-11-12T14:30+07:00", "location": "H1-201"},
    {"id": "hoctap:gmail_truong:18c2f", "domain": "hoctap", "source": "gmail_truong", "kind": "email",
     "title": "Thầy Nam hỏi link repo nhóm", "status": "open", "from": "Thầy Nam",
     "needs_reply": true, "received_at": "2026-11-01T16:20+07:00"}
  ],
  "grades": [{"course": "CO3001", "name": "Công nghệ phần mềm", "score": 8.5, "credits": 3, "term": "HK251"}]
}
```

## File Zalo (`data/zalo.json`)

Chỉ bot Zalo ghi; định dạng trong skill `lifeos-zalo`. Bot mảng đọc các hội thoại có `domain` của mình và chuyển tin đáng chú ý thành item `kind: "message"`.
