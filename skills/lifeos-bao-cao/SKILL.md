---
name: lifeos-bao-cao
description: Mẫu và quy trình viết báo cáo LifeOS gửi Khôi — báo cáo sáng 06:00 (kế hoạch hôm nay có giờ cụ thể, "ok" là đặt nhắc), báo cáo tối 21:00 (tổng kết + kế hoạch mai), cảnh báo 🔴 giữa ngày, báo cáo tuần (Chủ nhật) và tháng. Chỉ bot LifeOS dùng.
---

# Báo cáo LifeOS

## Nguyên tắc

- **Dữ liệu chỉ lấy từ `digest.json`** (và `health.json`, `context/`). Không tự đọc file mảng, không tự đoán.
- **Thứ/ngày lấy nguyên văn** từ các trường `*_label` hoặc lệnh `date`. Không tự suy.
- Ngắn: ≤ 25 dòng. 🔴 luôn hiện đủ (trong kế hoạch hoặc mục 3 ngày tới); 🟡 và ⚪ gom thành "Xa hơn: N việc".
- Việc trong `done.json` không bao giờ xuất hiện (script đã loại). Khôi nói "xong rồi" → chạy `done` ngay.
- Giọng thân mật, không trách, không thuật ngữ kỹ thuật.

## Trước mỗi báo cáo

```bash
cd /workspace/lifeos-grok
python3 -m lifeos digest
python3 -m lifeos health      # đọc health.json
```

Sau khi gửi xong: `python3 -m lifeos mark-reported` (để không bắn lại cảnh báo cho việc đã báo), rồi `status lifeos --type report --ok`.

## Nguyên tắc chung của báo cáo sáng/tối

- **Kế hoạch lên đầu.** Khôi đọc xong 5 dòng đầu là biết làm gì, lúc mấy giờ. Phần "để biết" xuống dưới, ngắn.
- **Mỗi việc chỉ xuất hiện một lần.** Việc đã nằm trong kế hoạch thì không lặp lại ở các mục khác.
- **Mọi khối trong kế hoạch có ▶ bước đầu tiên ≤ 10 phút**, cụ thể đến mức không cần nghĩ (skill `lifeos-chong-tri-hoan`, R3). Viết động từ: "mở…", "trả lời…", "đọc…".
- Giờ và thứ tự do script xếp (`plan suggest`) — được đổi chữ, **không tự đổi giờ** (trừ khi Khôi yêu cầu, hoặc biết chắc ràng buộc thực tế mà script không biết, ví dụ giờ mở cửa; khi đó chạy `free` để chọn giờ khác và nói lý do).
- Lời khuyên thêm (ví dụ "hôm nay chạy nhẹ thôi") tối đa **1 dòng 💡**.
- Tổng ≤ 25 dòng. Xa hơn 3 ngày chỉ ghi một dòng đếm.

## Mẫu báo cáo sáng (06:00)

Thứ tự:

1. `python3 -m lifeos digest`, `python3 -m lifeos health`.
2. `python3 -m lifeos plan list --for today` — kế hoạch đã chốt tối qua (nếu có).
3. `python3 -m lifeos plan suggest --for today --max 3` — việc còn lại (đã trừ việc trong kế hoạch tối qua) xếp vào khung trống.
4. Viết báo cáo:

```
☀️ <today_label> · <số khối> việc, rảnh ~<free_minutes_left/60> giờ

🎯 HÔM NAY LÀM GÌ — trả lời "ok" là mình đặt nhắc cho từng việc
1️⃣ 08:00–08:30 · Việc nhanh: trả lời bạn A (nhóm lớp) · trả lời B · đọc mail phòng khảo thí
   ▶ Mở Zalo nhóm lớp, trả lời A trước
2️⃣ 08:40–09:40 · 🔴 Nộp BTL môn X (hạn tối nay)
   ▶ Mở file nhóm, đọc lại phần kết luận 10 phút
3️⃣ 09:50–11:20 · 🔴 Đi nhận đồ đăng ký sự kiện (ngày cuối)
   ▶ Bỏ CCCD + mã đăng ký vào túi
   (khối đã chốt tối qua ghi thêm "✅ chốt tối qua")
💡 <tối đa 1 dòng lời khuyên>

📅 LỊCH CỐ ĐỊNH          ← schedule_today (học, làm, sự kiện) — mỗi dòng: giờ · tên · nơi
⚠️ CẦN BẠN QUYẾT         ← tối đa 3: trùng lịch, lời mời chưa trả lời ("có 4 lời mời — nói 'xem lời mời'")
📌 3 NGÀY TỚI            ← việc có hạn trong 3 ngày nhưng KHÔNG nằm trong kế hoạch hôm nay: 1 dòng/việc
➕ Xa hơn: <N> việc — nói "xem tuần này"
🔑 / ⚙️                  ← chỉ khi có vấn đề (needs_login, dữ liệu cũ)
```

`plan suggest` trả về `unplaced` (không còn chỗ trống) → ghi 1 dòng: "Không đủ giờ cho X hôm nay — dời sang mai nhé?".
Không có việc gì để xếp → "🎯 Hôm nay không có việc gấp — muốn mình xếp giờ cho việc gì không?".

### Khôi trả lời kế hoạch

| Khôi nói | Làm |
|---|---|
| *(ngay khi gửi báo cáo)* | **Lưu kế hoạch (chưa chốt)**: với từng khối `plan add --for today --title … --at <giờ bắt đầu> --step "<▶ bước đầu>" --minutes … [--id …]`. Số thứ tự `n` trùng số 1️⃣ 2️⃣ 3️⃣ trong tin. |
| "ok" | `plan confirm --for today` → với từng khối tạo **Reminder + báo thức Grok** đúng giờ bắt đầu (kiểm qua `remind-at`), tên = "▶ bước đầu · N phút". Trả lời một dòng: "Đặt nhắc xong 3 việc ✅". |
| "đổi 2 sang 15h" / "bỏ 3" | Giờ mới kiểm bằng `free` → `plan edit 2 --at 15:00` / `plan edit 3 --remove` → gửi lại kế hoạch rút gọn, chờ "ok". |
| "thêm <việc> lúc <giờ>" | `plan add …` → gửi lại kế hoạch rút gọn, chờ "ok". |
| "xong 1" / "xong <việc>" | `done "<việc>"` + `plan result <n> done`. |
| Không trả lời | Routine 06:40: `plan confirm --for today --auto` + Reminder + báo thức cho các khối đã lưu. Không nhắn thêm. |

Trong ngày, mỗi khối tới giờ thì báo thức reo. Qua giờ kết thúc mà chưa "xong" → không nhắc lại; báo cáo tối sẽ hỏi.

## Mẫu báo cáo tối (21:00)

Thứ tự:

1. `python3 -m lifeos digest` → `python3 -m lifeos nightly --png`.
2. `python3 -m lifeos plan list --for today` — đối chiếu kế hoạch hôm nay.
3. `python3 -m lifeos plan suggest --for mai --max 1` — 1 việc chính + khối việc nhanh cho mai (R4).
4. Viết báo cáo:

```
🌙 <today_label> · xong <a>/<b> việc trong kế hoạch

✅ ĐÃ XONG             ← done_titles hôm nay — ghi nhận, 1 dòng
❓ CHƯA XONG           ← khối kế hoạch chưa xong: "dời mai / bỏ / xong rồi?" — hỏi nhẹ, KHÔNG trách
                          (Khôi nói lý do → plan result <n> skipped --why "…")

🎯 MAI (<tomorrow_label>) LÀM GÌ — "ok" là mình đặt nhắc
1️⃣ <giờ> · <việc chính>
   ▶ NẾU <giờ> ở <nơi> THÌ <bước đầu ≤ 10 phút>
2️⃣ <giờ> · Việc nhanh: …
   (việc Khôi chọn "dời mai" được đưa vào đây trước)

📅 LỊCH CỐ ĐỊNH MAI    ← schedule_tomorrow
📌 MỚI HOẶC ĐỔI HÔM NAY ← việc mới xuất hiện / bị đổi hạn trong ngày (chưa báo)
🗒️ Tự khai (tùy): "pháp <phút>, năng lượng <1–5>"
```

Khôi trả lời kế hoạch mai giống bảng ở báo cáo sáng (dùng `--for mai`). Im lặng → 22:00 nhắc, 23:00 tự áp dụng (R4).

5. Thứ 6: thêm câu "Mai có lên công ty không?" chỉ khi có việc công ty còn dở.
6. Chủ nhật / cuối tháng: thêm phần tuần / tháng (bên dưới) và **gửi kèm ảnh** `/workspace/lifeos/dashboard/dashboard.png`. Cập nhật Grok Page "LifeOS · Hiệu suất" từ `dashboard/page.md`.

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
