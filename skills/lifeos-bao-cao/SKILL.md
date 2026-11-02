---
name: lifeos-bao-cao
description: Mẫu và quy trình viết báo cáo LifeOS gửi Khôi — báo cáo sáng 06:00 (kế hoạch hôm nay có giờ cụ thể, "ok" là đặt nhắc), báo cáo tối 21:00 (tổng kết + kế hoạch mai), cảnh báo 🔴 giữa ngày, báo cáo tuần (Chủ nhật) và tháng. Chỉ bot LifeOS dùng.
---

# Báo cáo LifeOS

## Nguyên tắc

- **Dữ liệu chỉ lấy từ `digest.json`** (và `health.json`, `context/`, sổ nhớ `brain`). Không tự đọc file mảng, không tự đoán.
- **Thứ/ngày lấy nguyên văn** từ các trường `*_label` hoặc lệnh `date`. Không tự suy.
- Ngắn: ≤ 25 dòng. 🔴 luôn hiện đủ (trong kế hoạch hoặc mục 3 ngày tới); 🟡 và ⚪ gom thành "Xa hơn: N việc".
- Việc trong `done.json` không bao giờ xuất hiện (script đã loại). Khôi nói "xong rồi" → chạy `done` ngay.
- Giọng thân mật, không trách, không thuật ngữ kỹ thuật.

## Trước mỗi báo cáo

```bash
cd /workspace/lifeos-grok
python3 -m lifeos digest
python3 -m lifeos health      # đọc health.json
python3 -m lifeos brain core  # hồ sơ ngắn: người quen, thói quen, việc đang dở (skill lifeos-tri-nho)
```

Sau khi gửi xong: `python3 -m lifeos mark-reported` (để không bắn lại cảnh báo cho việc đã báo), rồi `status lifeos --type report --ok`.

## Nguyên tắc chung

- **Tối lên kế hoạch cho ngày mai, sáng chỉ nhắc lại** và chen việc gấp mới. Tối qua chưa có kế hoạch (ngày đầu, hoặc Khôi bỏ qua cả tối) → sáng lên kế hoạch đầy đủ như buổi tối.
- **Kế hoạch là dòng thời gian cả ngày**, lấy nguyên từ `timeline` của script: ⏰ dậy · 🏫 lớp/thi · 🏢 văn phòng · 🏋️/🏃 tập · 📌 sự kiện · 📝 việc. **Không hiện giờ ăn.**
- **Chỉ ô 📝 có dòng ▶ bước đầu tiên ≤ 10 phút** (LifeOS viết, cụ thể, bắt đầu bằng động từ) và có Reminder + báo thức. Gym sáng cũng có báo thức.
- Giờ và thứ tự do script xếp (thang ưu tiên, giờ dậy/ngủ, giới hạn giờ mỗi ngày) — **không tự đổi giờ**. Khôi muốn đổi thì `plan edit` / `free`.
- Việc công ty trong `at_office` → ghi dưới dòng 🏢: "· việc công ty: …". Không xếp ô riêng.
- `unplaced` → một dòng: "Không đủ giờ cho X — dời mai hay bỏ bớt Y?". `overload: true` → "Hôm nay quá tải, mai mình xếp nhẹ lại".
- **Mỗi việc chỉ xuất hiện một lần.** Lời khuyên thêm tối đa 1 dòng 💡 — được dùng điều trong sổ nhớ ("💡 Tuần trước Khôi nói muốn thử học buổi sáng — mai 7:00–8:30 trống đó"), không thêm dòng mới.

## ☀️ Báo cáo sáng (05:30)

1. `digest`, `health`, `plan timeline --for today`.
1b. **Mọi buổi sáng:** `digest.json` có `conflicts_lifeos` (3 ngày tới: văn phòng/buổi tập/ô 📝 LifeOS đã xếp đè lịch thật). Có mục mức `cao` → thêm một dòng ⚠️ ("T4 gym 6:00 đè Lớp B 7:00 — dời gym tối nhé?") và xử lý theo `week train`/`plan edit`. Tối qua/đêm qua có ô hoặc buổi tập bị script **bỏ** vì trùng lịch (`dropped` của `plan confirm --auto` / `week confirm --auto`) → nói rõ một dòng.
2. **Đã có kế hoạch chốt tối qua:** chỉ cần kiểm tra việc 🔴 MỚI từ tối qua (`alerts`). Không có → báo cáo 2–3 dòng:
```
☀️ Thứ 3, 03/11 · đã chốt tối qua
✅ Không có gì mới — khảo sát 8:00 → thí nghiệm 9:00 → văn phòng 13:00 → chạy 18:15
```
   Có việc mới → `plan suggest --for today` và đề xuất chen:
```
🆕 Quiz 5 GT2 vừa mở, đóng 23:59 hôm nay · ~20 phút
   → chen vào 10:40–11:00, "ok" không?
```
3. **Chưa có kế hoạch:** `plan suggest --for today` → gửi theo **mẫu dòng thời gian** (bên dưới), lưu từng ô 📝 bằng `plan add` (chưa chốt).
4. Thứ 2: kế hoạch tuần chưa được "ok" → thêm dòng "📅 Lịch văn phòng tuần này chưa ghi lên lịch công ty — ok không?".
5. 🔑 / ⚙️ chỉ khi có vấn đề.

## 🌙 Báo cáo tối (21:00)

1. `digest` → `nightly --png` → `plan timeline --for today` (đối chiếu hôm nay) → `plan suggest --for mai` (kết quả có `conflicts`: chỗ trùng của ngày mai gồm cả văn phòng/buổi tập LifeOS đã xếp — mức "cao" thì thêm dòng ⚠️ vào tin và đề xuất dời/bỏ, **đừng chốt kế hoạch có trùng**) → `brain report` (khối 🧠).
2. Gửi:
```
🌙 Thứ 2, 02/11 · xong 3/4 việc trong kế hoạch 👏
✅ Kiểm tra GT2 · trả lời nhóm thí nghiệm · đọc mail hoãn thi
❓ Chưa xong: Bài 3 thí nghiệm — dời mai / bỏ / xong rồi?

🎯 MAI — Thứ 3, 03/11 · "ok" là mình đặt nhắc
06:00        ⏰ Dậy
07:00–11:00  🏫 Lớp XSTK (H6-304)
11:30–18:00  🏢 Văn phòng · việc công ty: gửi file test (hạn T4 10:00)
18:15–19:30  🏃 Chạy: INTERVAL
20:30–20:40  📝 Việc nhanh: trả lời A · làm 1 khảo sát học phần
             ▶ Mở Zalo nhóm thí nghiệm, trả lời A trước
20:50–22:20  📝 Bài 3 thí nghiệm MA3020
             ▶ Mở file số liệu, kẻ bảng kết quả 10 phút
Không đủ giờ cho "Báo cáo dài" — để T4 nhé?

📌 Mới hoặc đổi hôm nay: …
🗒️ Tự khai (tùy chọn): "năng lượng 1–5"

🧠 Nhớ thêm: tháng 12 về quê · thích học buổi sáng
❓ Ghi vào sổ không?
   a. Bạn A là trưởng nhóm BTL môn X (Học tập · Zalo nhóm lớp)
   b. Nhóm X họp thứ 5 hằng tuần (Công ty · Mail)
   → "ghi a" · "bỏ b" · "ghi hết"
```
   Khối 🧠 chép **nguyên văn** `text` của `brain report` (rỗng → bỏ cả khối). Ngày cuối tháng nó có thêm tối đa 5 câu "🔎 Còn đúng không?".
3. Ngay khi gửi: lưu từng ô 📝 bằng `plan add --for mai …` (chưa chốt). Việc Khôi chọn "dời mai" → `plan suggest` xếp ưu tiên (đã nằm trong candidates). Rồi `brain report --mark` → `brain page` → **chỉ khi `changed: true`**: cập nhật Grok Page "LifeOS · Trí nhớ" từ `dashboard/tri_nho.md`, xong chạy `brain page --mark`.
4. Chủ nhật/cuối tháng: gửi kèm **ảnh dashboard** + 3 dòng nhận xét. Ghi nhận xét vào file `context/…md`.

## Khôi trả lời kế hoạch (sáng, tối)

| Khôi nói | Làm |
|---|---|
| "ok" | `plan confirm --for <ngày>` (mã thoát 1 / `ok: false` = có ô đè lịch → báo `text`, hỏi dời/bỏ; Khôi nói "giữ nguyên" → `--allow-conflicts`) → mỗi ô 📝: **Reminder + báo thức Grok** đúng giờ bắt đầu (kiểm `remind-at`), tên "▶ bước đầu · N phút" → ghi ô 📝 lên **lịch "LifeOS"** (`calmap set plan:<ngày>:<n> <id>`) → `page` (đăng Page nếu `changed`) → "Đặt nhắc xong ✅". |
| "đổi 2 sang 15h" / "bỏ 3" | Kiểm giờ bằng `free` → `plan edit 2 --at 15:00` (đè lịch → script từ chối và giữ giờ cũ: báo `text`, đề xuất giờ khác; Khôi nói "giữ nguyên" → `--force`) / `plan edit 3 --remove` → gửi lại phần 🎯 rút gọn. Đã chốt trước đó → sửa luôn Reminder/báo thức/sự kiện LifeOS (lấy id từ `calmap get`). |
| "thêm <việc> lúc <giờ>" | `plan add …` → gửi lại phần 🎯 rút gọn. |
| "xong 2" / "xong <việc>" | `done "<việc>"` + `plan result 2 done`. **Không đăng Page ngay** (Page cập nhật ở báo cáo 05:30/21:00 và khi Khôi "ok" kế hoạch — tiết kiệm credit). |
| "ghi a" · "bỏ b" · "ghi hết" · "đúng d" · "sai e" · "quên f" | Sổ nhớ — skill `lifeos-tri-nho` mục 3. **Chữ = sổ nhớ, số = kế hoạch.** |
| Im lặng (tối) | 22:00 nhắc 1 dòng + báo thức "Xem kế hoạch mai · 1 phút". 23:00: `plan confirm --for mai --auto` + nhắc + lịch LifeOS, không nhắn. Ô nào đè lịch bị bỏ (`dropped`) → báo cáo sáng nói rõ. |
| Im lặng (sáng, khi có đề xuất chen việc) | 07:00: tự áp dụng như "ok", không nhắn. |

**Ba lần dậy chỉ để kiểm tra (07:00, 22:00, 23:00):** KHÔNG chạy `brain core`, không đọc thêm skill. Chạy một lệnh duy nhất `python3 -m lifeos plan pending --for <today|mai>` — `need_confirm: false` (và `week_need_confirm: false` với 23:00 Chủ nhật) → **dừng ngay, không làm gì thêm**. Chỉ khi `true` mới làm việc ghi ở bảng trên.

## 📅 Kế hoạch tuần (Chủ nhật 20:00)

1. `digest` → `week propose` (cho tuần bắt đầu Thứ 2 tới) → đọc `history`/`context` tuần này cho phần tổng kết. Rồi gộp điều trùng trong sổ nhớ: `brain dupes` → cặp nào cùng một ý → `brain merge <giữ> <bỏ>` (không hỏi Khôi, không nhắc trong tin).
2. Gửi:
```
📅 Tuần 2–7/11 · tuần này xong 18/22 việc (82%) · ảnh dashboard ⬇️

🏢 VĂN PHÒNG (sếp sẽ thấy trên lịch công ty)
  T2 nghỉ (có kiểm tra) · T3 11:30–18:00 (sau giờ học) · T4 9–18 · T5 9–18 · T6 9–18 · T7 9–18
🏋️ TẬP
  T2 Gym: PUSH 6:00 · T3 Chạy: INTERVAL 18:15 · T4 Gym: PULL 6:00
  T5 Chạy nhóm 18:00 · T6 Gym: LEGS 6:00 · T7 Chạy: LONG RUN 18:15
📚 VIỆC LỚN: Kiểm tra GT2 (T2) · Bài 3 thí nghiệm (T3) · 6 khảo sát (hạn 9/11)
⚠️ T5 12/11: sinh nhật Lab trùng chạy nhóm → gợi ý đi sinh nhật Lab

"ok" là mình ghi lịch · hoặc sửa: "T4 lên 9–12", "bỏ gym T6"
```
   Dòng văn phòng lấy từ `days.*.office` / `office_note`; tập từ `training` (+ `training_note`: gym sáng vướng lớp thì script đã **dời sang tối** hoặc **bỏ** — nói rõ cho Khôi, ví dụ "T4 gym dời 17:45 vì sáng có lớp"); cảnh báo từ `conflicts` (mỗi mục có `text` viết sẵn tiếng Việt) + `notes`.
   - `severity: "cao"` (buổi tập/văn phòng/ô 📝 đè giờ học, thi, sự kiện): **phải xử lý trước khi "ok"** — đề xuất dời/bỏ theo thang ưu tiên (học > làm > tập > đi chơi), Khôi quyết.
   - `severity: "luu-y"` (hai sự kiện trên lịch đè nhau; văn phòng đè một sự kiện cá nhân > 30 phút): báo một dòng để Khôi quyết, không chặn.
   - **Muốn xem lại cả tuần**: `lichtong show --date <thứ 2> --days 7` (mọi lịch + thứ LifeOS xếp, đã đối chiếu). Hình lịch tổng nằm trong ảnh dashboard (mục "Lịch tổng tuần này", viền đỏ = đang trùng). **Không tự đối chiếu bằng mắt qua nhiều lịch** — luôn hỏi script.
3. Khôi sửa → `week set <ngày> --office 09:00-12:00|none` / `--training none|17:30-18:45`; đổi **loại** buổi tập ("tuần này nghỉ chạy, tập PPL") → `week train <ngày> --type gym|run --label "Gym: PUSH"` (không đưa `--time` thì script tự xếp và tự né lịch). Kết quả có `day_conflicts` / `day_ok`: `day_ok=false` → báo chỗ trùng, đừng coi là xong. Gửi lại phần đã đổi.
   **Cấm sửa tay `state/week.json`** (và mọi file trong `state/`): sửa tay bỏ qua bước kiểm tra trùng — chính vì vậy tuần đầu tiên từng có gym đè giờ học mà không ai báo.
4. **"ok"** → `week confirm` (mã thoát 1 / `ok: false` = còn trùng mức cao → báo Khôi, KHÔNG ghi lịch nào; Khôi nói "giữ nguyên" → `week confirm --allow-conflicts`). Chốt được rồi mới, với mỗi ngày:
   - **Lịch công ty** (trình duyệt, tài khoản công ty — phiên do bot Công ty giữ; bị đăng xuất → nhờ bot Công ty đăng nhập lại trước): đặt **Working location = Office** đúng khung giờ. Không mời ai. Ngày nghỉ văn phòng: không ghi. Chỉ sửa/xóa mục Office do LifeOS tạo (`calmap set office:<ngày> <id>`). Xong → `week company-written`.
   - **Lịch "LifeOS"** (Google Calendar cá nhân): tạo sự kiện buổi tập với tiêu đề đúng nhãn ("Gym: PUSH", "Chạy: INTERVAL"…), không ghi chi tiết bài tập (`calmap set train:<ngày> <id>`). Chạy nhóm đã có trên lịch → không tạo thêm.
   - Trước khi tạo/sửa BẤT KỲ sự kiện nào trên lịch (ví dụ Khôi nhờ "thêm deadline này vào lịch"): `lichtong try --start … --end … --title …` — `ok: false` → báo chỗ đè, hỏi lại.
   - `page` → cập nhật Grok Page (theo mục "Grok Page" bên dưới).
5. **Im lặng:** 23:00 Chủ nhật → `week confirm --auto` (buổi tập nào đè lịch thì script **bỏ** và ghi trong `dropped` — báo cáo sáng T2 nói rõ) + ghi buổi tập còn lại lên lịch "LifeOS". **KHÔNG ghi lịch công ty** cho tới khi Khôi "ok" (báo cáo sáng T2 hỏi lại).
6. Trong tuần Khôi nói "mai không lên công ty" / "T5 lên 13h–18h" / "bỏ gym mai" → `week set …` / `week train …` (đọc `day_conflicts`) → sửa/xóa mục Office trên lịch công ty (tin nhắn của Khôi là lời duyệt) → `plan suggest` lại cho ngày đó nếu là hôm nay/mai.

## Grok Page "LifeOS"

Một Page duy nhất, link cố định, ghim sẵn. Nội dung lấy từ `dashboard/page.md` (lệnh `page` dựng lại phần Hôm nay + Tuần này; `nightly` dựng lại cả phần Hiệu suất). **Chỉ đăng lại khi cần** (mỗi lần viết lại Page là tốn credit): chạy `page` → kết quả có `changed`. Chỉ đăng khi `changed: true` **và** đang ở một trong các lúc: báo cáo 05:30, báo cáo 21:00, Khôi "ok" kế hoạch (ngày/tuần), Khôi nhắn xem Page/dashboard. Đăng xong chạy `page --mark` (ghi nhớ bản đã đăng). Các tin lẻ như "xong 1", "đổi 2 sang 15h" **không** đăng Page — chỉ cập nhật file; bản đúng sẽ lên ở lần đăng kế tiếp.

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
- Lý do "mail bạn gửi bị trả về" → báo riêng một dòng: `🚨 Mail gửi <người> lúc <giờ> bị trả về: địa chỉ không dùng được. Mình tìm địa chỉ khác nhé?` Rồi ghi sổ nhớ: địa chỉ đó đang có trong sổ → `brain end <mã> --note "bị trả về <ngày>"`; chưa có → `brain add --section tranh --subject "<người>" --text "Không gửi tới <địa chỉ>: bị trả về <ngày>" --source "thư báo trả về <ngày>"`. Tìm địa chỉ khác theo nội quy mục 10 — không đoán.

## Tổng kết tuần (trong tin Chủ nhật 20:00) và tháng

Chủ nhật 20:00, trước khi gửi kế hoạch tuần: chạy `nightly --png` (chốt sổ hôm nay + chốt tuần + dựng dashboard; 21:00 chạy lại cũng không sao). Ngày cuối tháng 21:00: `nightly` tự chốt tháng.

1. Đọc `context/weekly/<năm>-W<tuần>.md` (hoặc `context/monthly/…`) + kỳ trước.
2. **Viết vào mục "Nhận xét của LifeOS"** trong file .md: 3 điểm sáng · 3 điểm cần cải thiện · 3 đề xuất cho kỳ tới · việc lớn đang dở. Dựa trên số liệu và lý do bỏ kế hoạch Khôi đã nói — không bịa.
   Báo cáo tháng: viết thêm mục **"Chuyện đã nói trong tháng"** — gom `brain journal show --month <YYYY-MM>` thành 3–6 dòng (nhật ký ngày chỉ giữ 90 ngày, mục này giữ lâu dài; chuyện riêng chỉ ghi "có nói chuyện riêng").
3. Trong tin: **1 dòng tổng kết** ("tuần này xong 18/22 việc (82%)") + **ảnh dashboard**. Khôi muốn đọc thêm → gửi phần nhận xét.
4. Chủ nhật: kèm câu hỏi WOOP (skill `lifeos-chong-tri-hoan`, R10) ở cuối tin kế hoạch tuần.

File tuần/tháng là **trí nhớ dài hạn** của LifeOS: Khôi hỏi về tuần trước/tháng trước → đọc các file này trước.

## Dashboard

- Nằm trong Grok Page "LifeOS" (phần Hiệu suất) — không tạo trang riêng.
- Khôi nhắn "cho xem dashboard" → `python3 -m lifeos dashboard --png` rồi gửi ảnh.
