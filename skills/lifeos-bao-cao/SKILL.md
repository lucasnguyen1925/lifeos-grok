---
name: lifeos-bao-cao
description: Mẫu và quy trình viết báo cáo LifeOS gửi Khôi — báo cáo sáng 06:00, báo cáo tối 21:00 (kèm kế hoạch nếu–thì cho ngày mai), cảnh báo 🔴 giữa ngày, báo cáo tuần (Chủ nhật) và tháng. Chỉ bot LifeOS dùng.
---

# Báo cáo LifeOS

## Nguyên tắc

- **Dữ liệu chỉ lấy từ `digest.json`** (và `health.json`, `context/`). Không tự đọc file mảng, không tự đoán.
- **Thứ/ngày lấy nguyên văn** từ các trường `*_label` hoặc lệnh `date`. Không tự suy.
- Ngắn: báo cáo thường ≤ 20 dòng. 🔴 luôn hiện đủ; 🟠 tối đa 7; 🟡 và ⚪ gom thành "và N việc khác".
- Việc trong `done.json` không bao giờ xuất hiện (script đã loại). Khôi nói "xong rồi" → chạy `done` ngay.
- Giọng thân mật, không trách, không thuật ngữ kỹ thuật.

## Trước mỗi báo cáo

```bash
cd /workspace/lifeos-grok
python3 -m lifeos digest
python3 -m lifeos health      # đọc health.json
```

Sau khi gửi xong: `python3 -m lifeos mark-reported` (để không bắn lại cảnh báo cho việc đã báo), rồi `status lifeos --type report --ok`.

## Mẫu báo cáo sáng (06:00)

```
☀️ <today_label> — <số 🔴> việc gấp, <số 🟠> việc cần chú ý

🔑 CẦN BẠN GIÚP              ← chỉ khi needs_login/health có vấn đề cần Khôi
  • MyBK cần đăng nhập: mở bot Học tập, gõ "đăng nhập MyBK"

🔴 GẤP
  • Quiz 4 GT2 — đóng 23:59 hôm nay · ~20 phút · <lý do>

⚠️ TRÙNG LỊCH                  ← chỉ khi conflicts không rỗng
  • 13:00 Thứ 3: CNPM (trường) ↔ Ca chiều (công ty)

📅 HÔM NAY                     ← schedule_today
  07:00–09:00 CNPM (H6-304)
  12:15 🎯 Quiz 4 GT2 (kế hoạch nếu–thì đã chốt tối qua)

🟠 CẦN CHÚ Ý (tối đa 7)
📬 TIN CẦN TRẢ LỜI             ← needs_reply; có nháp sẵn thì ghi "đã soạn nháp, nói 'xem nháp'"
➕ và N việc khác — hỏi mình nếu muốn xem

⚙️ Dữ liệu: Học tập 05:41 · Công ty 05:38 · Cá nhân ⚠️ cũ từ 20:41 hôm qua
```

Dòng ⚙️ lấy từ `domains.*.generated_label` / `stale` / `missing`. Mọi mảng ổn → chỉ một dòng "⚙️ Dữ liệu đầy đủ".

## Mẫu báo cáo tối (21:00)

Thứ tự trong routine 21:00:

1. `python3 -m lifeos digest` → `python3 -m lifeos nightly --png` (chốt ngày; Chủ nhật/cuối tháng tự chốt tuần/tháng; dựng dashboard).
2. Viết báo cáo:

```
🌙 <today_label> — hôm nay xong <N> việc

✅ ĐÃ XONG HÔM NAY             ← từ history/daily/<hôm nay>.json done_titles
❓ CÒN MỞ HÔM NAY             ← việc hạn hôm nay chưa xong: hỏi "xong chưa?" — KHÔNG trách
🔴 / 🟠 cho ngày mai và 3 ngày tới
📅 MAI (<tomorrow_label>)      ← schedule_tomorrow

🎯 MAI LÀM GÌ TRƯỚC?           ← theo skill lifeos-chong-tri-hoan, mục R4
  Việc chính: … → NẾU <giờ, nơi> THÌ <bước đầu ≤10 phút>
  Việc nhanh: … (tối đa 2)
  Trả lời "ok" · hoặc sửa

🗒️ Tự khai: "pháp <phút>, năng lượng <1–5>"   ← một dòng, không bắt buộc
```

3. Thứ 6: thêm câu "Mai có lên công ty không?" chỉ khi lịch công ty tuần này chưa đủ giờ hoặc có việc công ty còn dở.
4. Chủ nhật / cuối tháng: thêm phần tuần / tháng (bên dưới) và **gửi kèm ảnh** `/workspace/lifeos/dashboard/dashboard.png`. Cập nhật Grok Page "LifeOS · Hiệu suất" từ `dashboard/page.md`.

## Cảnh báo 🔴 giữa ngày

Nhận tin ưu tiên từ bot mảng → `python3 -m lifeos digest` → `python3 -m lifeos alerts`.
- `send` rỗng → không làm gì (bot khác đã gửi, hoặc đang giờ yên lặng).
- Có → MỘT tin gộp:
  ```
  🚨 <N> việc gấp mới
  • Quiz 5 GT2 vừa mở — đóng 17:00 hôm nay · ~20 phút
  → Khung trống gần nhất: 12:15–12:45. Mình đặt nhắc lúc 12:15 nhé?
  ```
  rồi `python3 -m lifeos alerts --mark <các id vừa gửi>`.
- Việc quiz/đăng ký còn ≤ 3 giờ chưa làm → **tự đặt Reminder + báo thức** (đã được Khôi cấp quyền), giờ lấy từ `remind-at`.

## Báo cáo tuần (Chủ nhật 21:00) và tháng

`nightly` đã tạo `context/weekly/<năm>-W<tuần>.md` (hoặc `context/monthly/<năm>-<tháng>.md`) có sẵn bảng chỉ số so với kỳ trước.

1. Đọc file đó + file tuần/tháng trước.
2. **Viết vào mục "Nhận xét của LifeOS"** trong file .md (thay dòng chú thích): 3 điểm sáng · 3 điểm cần cải thiện · 3 đề xuất cụ thể cho kỳ tới · việc lớn đang dở cần nhớ. Dựa trên số liệu và lý do bỏ kế hoạch Khôi đã nói — không bịa.
3. Gửi Khôi bản rút gọn (≤ 15 dòng) + ảnh dashboard.
4. Chủ nhật: kèm câu hỏi WOOP (skill `lifeos-chong-tri-hoan`, R10).

File tuần/tháng là **trí nhớ dài hạn** của LifeOS: khi Khôi hỏi về tuần trước/tháng trước, đọc các file này trước.

## Dashboard

- Grok Page "LifeOS · Hiệu suất": tạo một lần, sau đó mỗi tối 21:00 cập nhật nội dung từ `dashboard/page.md`. Không tạo trang mới mỗi ngày.
- Khôi nhắn "cho xem dashboard" → `python3 -m lifeos dashboard --png` rồi gửi ảnh.
