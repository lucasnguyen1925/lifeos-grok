---
name: lifeos-tri-nho
description: Sổ nhớ chung của đội LifeOS — đọc hồ sơ ngắn, tìm, ghi điều đáng nhớ về Khôi, sửa, quên, đề xuất, nhật ký chuyện đã nói, kho "lưu cái này", soát chat 20:40, gộp trùng, sao lưu, chuyển trí nhớ cũ. LifeOS và Tiko đọc toàn bộ; bot Học tập, Công ty, Cá nhân, Zalo đọc mục 0, 1, 2, 6.
---

# Sổ nhớ LifeOS

Mọi lệnh chạy trong thư mục bộ cài: `cd /workspace/lifeos-grok && python3 -m lifeos brain …`. Kết quả in JSON — đọc, đừng đoán.

## 0. Nguyên tắc (SPEC §5c)

- Sổ nhớ `/workspace/lifeos/brain/` là **bản gốc** trí nhớ về Khôi, **chung cho cả 6 bot**. Chỉ đọc/ghi bằng lệnh `brain`, không sửa tay file.
- **Không cất chuyện của Khôi vào trí nhớ của Grok** — cả phần riêng của bot lẫn phần chung cho mọi bot. Grok vẫn tự ghi vào trí nhớ riêng và không tắt được → **sổ và trí nhớ riêng nói khác nhau thì theo sổ.**
- Không hiện mã (m12, d3…) hay tên lệnh cho Khôi, trừ khi Khôi đang soát sổ trên Page.

## 1. Đọc — mọi bot

| Khi | Làm |
|---|---|
| Đầu **mỗi** lượt chat với Khôi, đầu **mỗi** lần chạy routine | `brain core` → hồ sơ ngắn (~40 dòng) |
| Câu hỏi/việc đụng chuyện cũ, người quen, sở thích, dự định, "hôm trước nói gì" | `brain search "<từ khóa>"` **trước khi trả lời** (gõ không dấu cũng được). Nhiều kết quả về một người/môn/dự án → `brain show "<tên>"` |
| Sổ không có | Tìm trong trí nhớ riêng Grok của bạn. Có → trả lời; LifeOS/Tiko ghi luôn vào sổ (`--origin grok`); bot quét nguồn thì `propose` |

Kết quả ghi `trước đây (tới 11/2026)` = chuyện cũ không còn đúng → nói rõ "trước đây…".

## 2. Ai được ghi gì

| Bot | Được |
|---|---|
| **LifeOS, Tiko** | Ghi thẳng (`brain add`) chuyện **Khôi kể** trong khung chat của mình. Ghi **lặng lẽ** — không báo từng điều; 21:00 LifeOS báo gộp một dòng 🧠 |
| **Học tập, Công ty, Cá nhân, Zalo** | Chỉ **đề xuất** (`brain propose`, mục 6). Khôi duyệt trong báo cáo tối |

**Đáng nhớ:** về Khôi (học gì, làm gì, đang ở đâu…) · mục tiêu · người quen (ai là ai, liên quan tới Khôi thế nào) · thói quen, sở thích làm việc · lời hứa, dự định (có ngày → `--due`) · điều nên tránh.

**Không ghi:** chuyện phiếm · deadline/lịch học/lịch họp (bot quét nguồn đã lo) · mật khẩu, mã, cookie · nội dung tài liệu công ty.

**Chuyện nhạy cảm** — sức khỏe · tình cảm · tiền nong, nợ · chuyện riêng gia đình · chuyện riêng người khác kể cho Khôi: **không tự ghi**. Chỉ khi Khôi nói rõ "nhớ giúp…" → hỏi lại một câu *"Chuyện này cả đội bot đều đọc được, vẫn ghi nhé?"* → Khôi đồng ý → ghi kèm `--sensitive`. Bot quét nguồn **không bao giờ** đề xuất chuyện nhạy cảm.

### Cách viết một điều

- **Một điều một câu ngắn, đọc riêng vẫn hiểu**: "Bạn A là trưởng nhóm BTL môn X" (không viết "nó là trưởng nhóm").
- **Ngày tháng cụ thể** (dùng lệnh `date` nếu cần): "Tháng 12/2026 về quê", không "tháng sau".
- `--section`: `ve_khoi` · `muc_tieu` · `nguoi_quen` · `cach_lam_viec` · `dang_do` · `tranh` · `khac` (khác = không lên hồ sơ).
- `--subject "<tên>"` khi điều đó nói về một người/môn/dự án (để `show` gom thành trang).
- `--core` nếu đáng nằm trên hồ sơ ngắn: người hay nhắc tới, thói quen ảnh hưởng kế hoạch, lời hứa đang mở, mục tiêu hiện tại. Không chắc → không `--core`. Mỗi mục hồ sơ có giới hạn dòng; quá thì điều lâu không nhắc tự nằm lại trong sổ.
- Kết quả có `duplicate_of` → sổ đã có (chỉ khác chữ đệm), không làm gì thêm.

```bash
python3 -m lifeos brain add --by lifeos --section nguoi_quen --subject "bạn A" --core --text "Bạn A là trưởng nhóm BTL môn X"
python3 -m lifeos brain add --by lifeos --section dang_do --core --due 2026-11-06 --text "Hứa gửi bạn A file BTL"
python3 -m lifeos brain add --by tiko   --section ve_khoi --replaces m12 --text "Đã nghỉ làm ở chỗ A từ 11/2026"   # m12 thành "trước đây"
```

## 3. Khôi nói gì → làm gì (LifeOS; Tiko làm như vậy trong khung chat Tiko)

Trả lời Khôi: **chữ a, b, c… là sổ nhớ**; **số 1, 2, 3… là kế hoạch** ("bỏ 3" = bỏ ô 3 của kế hoạch, "bỏ b" = bỏ đề xuất b).

| Khôi nói | Làm |
|---|---|
| Kể chuyện có điều đáng nhớ | `add` lặng lẽ + nhật ký (mục 5). Không báo |
| "nhớ giúp …" | `add` (nhạy cảm → hỏi lại trước) → "✅ Nhớ rồi" |
| Điều cũ không còn đúng ("mình nghỉ chỗ A rồi") | `search` tìm mã → `add … --replaces <mã>` |
| Bot nhớ sai, "sửa m12: …" | `edit <mã> --text "…"` (không giữ bản sai) |
| Lời hứa/dự định xong hoặc thôi | `end <mã>` |
| "ghim …" / "bỏ … khỏi hồ sơ" | `pin <mã>` / `unpin <mã>` |
| "bạn nhớ gì về X?" | `show "X"` → trả lời ngắn, kèm "xem đủ ở Page Trí nhớ" |
| "bạn nhớ gì về mình?" | `core` → tóm tắt 5–8 dòng + link Page "LifeOS · Trí nhớ" |
| "hôm thứ 3 bàn gì về BTL?" | `search "btl"` / `journal show --date <ngày>` |
| "quên giúp …" | Mục 4 |
| "ghi a" · "bỏ b" · "ghi hết" (sau báo cáo tối) | `accept a` · `reject b` · `accept hết` |
| "đúng d" · "sai e" · "quên f" (báo cáo tháng) | `confirm d` · hỏi điều đúng rồi `edit e --text …` (hoặc `add --replaces e` nếu chuyện đã đổi) · mục 4 cho `f` |
| "lưu" + link/ảnh/video/ghi chú | Mục 7 |
| "tìm cái … hôm trước", "kho môn X có gì" | `search "…"` / `kho list --tag "môn X"` |
| Lời hứa/dự định **có ngày** | `add --section dang_do --due …` → hỏi ngay **"Thêm vào việc cần làm không?"** → "ok" → tạo Reminder trong danh sách việc (`config.toml` → `sources.canhan.reminders_list`); bot Cá nhân sẽ quét thấy và đưa vào kế hoạch |
| Sở thích **đụng cách xếp lịch** (giờ ngủ, giờ dậy, giới hạn giờ, giờ tập…) | `add` → hỏi **"Đổi luôn cách xếp lịch: <thay đổi> nhé?"** → "ok" → sửa đúng khóa trong `config.toml` → báo đã đổi. **Không bao giờ tự đổi lặng lẽ.** Sở thích không có khóa cấu hình (vd "học sáng vào hơn") → chỉ nhớ, dùng để khuyên |
| Nhắc tới người mới quan trọng (sếp mới, giảng viên mới) | `add --section nguoi_quen` → hỏi "Thêm vào danh sách người quan trọng không?" (ảnh hưởng độ gấp) |

Nhắc chủ động: chỉ trong dòng 💡 sẵn có của báo cáo (tối đa 1 dòng), ví dụ "💡 Tuần trước Khôi nói muốn thử học buổi sáng — mai 7:00–8:30 trống đó".

## 4. "Quên giúp …"

1. `search` → tìm đúng mã. Nhiều điều khớp → hỏi lại Khôi điều nào. "Quên hết đi" → hỏi lại từng nhóm, **không** xóa hàng loạt.
2. `brain forget <mã…>` (xóa hẳn khỏi sổ, kể cả lịch sử của điều đó; sổ chỉ giữ mã + giờ đã quên).
3. Gửi **tin ưu tiên** nguyên văn `message_for_other_bots` cho **Tiko, Học tập, Công ty, Cá nhân, Zalo**. Chính bạn cũng xóa điều đó trong trí nhớ riêng và phần trí nhớ chung do bạn ghi.
4. `drive_to_trash` có link → bỏ file đó vào thùng rác Drive.
5. Báo Khôi thật: *"Đã xóa trong sổ và trí nhớ các bot. Khung chat cũ thì Grok không cho xóa."* Bot nào không trả lời "đã xóa/không có" sau ~10 phút → nêu tên để Khôi nhắn thẳng bot đó.

Ngoại lệ cho các bot nhận lời nhờ quên: xem nội quy `lifeos-noi-quy` mục 4.

## 5. Nhật ký chuyện đã nói (LifeOS, Tiko)

- Lượt chat có chuyện đáng kể → `brain journal add --by lifeos --text "Bàn chia việc BTL, chốt Khôi làm phần 2"`. Một dòng một chủ đề, tóm tắt, **không chép nguyên văn**.
- Chuyện nhạy cảm → `brain journal add --by lifeos --private` (chỉ lưu "có nói chuyện riêng").
- Mỗi ngày còn **3–5 dòng**: kết quả báo quá 5 dòng → cuối ngày gộp: `brain journal replace --date today --text "…" --text "…"`.
- Giữ 90 ngày. Ngày cuối tháng LifeOS gom `journal show --month <YYYY-MM>` thành 3–6 dòng trong mục "Chuyện đã nói trong tháng" của báo cáo tháng (giữ lâu dài).

## 6. Bot quét nguồn: đề xuất

Thấy trong mail/Zalo/lịch một điều **lâu dài** về Khôi hoặc người quanh Khôi — ai là trưởng nhóm, ai dạy môn nào, nhóm nào làm dự án gì, lịch họp cố định, người mới trong nhóm:

```bash
python3 -m lifeos brain propose --by hoctap --section nguoi_quen --subject "bạn A" --source "Zalo nhóm lớp" --text "Bạn A là trưởng nhóm BTL môn X"
```

- **Không đề xuất:** việc có hạn (đã thành item), chuyện nhạy cảm, nội dung tài liệu công ty, điều chỉ đúng một lần.
- Kết quả `already_known` / `duplicate_of` / `"ok": false` → thôi, không đề xuất lại.
- Không cần tự giới hạn số lượng — báo cáo tối tự lấy tối đa 3 đề xuất mỗi tối.

## 7. Kho "lưu cái này" (LifeOS)

**Chỉ khi Khôi nói "lưu"** (gửi kèm chữ "lưu", hoặc "lưu cái trên"). Khôi gửi để hỏi thì không lưu.

1. Xem/đọc nội dung → tóm tắt 2–3 dòng: là gì, vì sao lưu (nếu Khôi nói).
2. Ảnh/video/file: lưu vào `/workspace/lifeos/state/kho_tam/`, tải lên Google Drive thư mục **"LifeOS · Kho"** (giữ nguyên định dạng), lấy link Drive, **xóa bản trên máy**. Link và ghi chú chữ thì không cần Drive.
3. `brain kho add --title "…" --summary "…" --tag "<môn/dự án>" --url "<link gốc>" --drive "<link Drive>" --kind link|anh|video|file|ghi_chu`
4. Trả lời một dòng: "📥 Lưu rồi: Trang ưu đãi cho sinh viên (#học-bổng)".

## 8. Việc định kỳ

| Khi | Ai | Làm |
|---|---|---|
| 20:40 hằng ngày | LifeOS | Soát chat (mục 9) |
| 21:00 | LifeOS | Báo cáo tối: `brain report` → thêm khối 🧠 vào cuối báo cáo → gửi → `brain report --mark` → `brain page` → cập nhật Grok Page "LifeOS · Trí nhớ" từ `dashboard/tri_nho.md` |
| Chủ nhật 20:00 | LifeOS | `brain dupes` → từng cặp: cùng một ý → `brain merge <giữ> <bỏ>`; khác ý → bỏ qua. **Không hỏi Khôi** (gộp nhầm → `unmerge`) |
| Ngày cuối tháng 21:00 | LifeOS | `brain report` tự có tối đa 5 câu "Còn đúng không?" · gom nhật ký tháng (mục 5) |
| 02:15 | Tiko | Sao lưu (mục 10) |

## 9. Soát chat cuối ngày (LifeOS, 20:40)

Routine 20:40 chỉ gửi **tin ưu tiên cho chính LifeOS**: "Soát chat hôm nay theo skill lifeos-tri-nho mục 9." Trong lượt chat được đánh thức:

1. `brain core` + `brain journal show` → biết hôm nay đã ghi gì.
2. Mở lại khung chat **hôm nay** giữa Khôi với LifeOS, và giữa Khôi với Tiko (chỉ phần từ 00:00 hôm nay).
3. Điều đáng nhớ bị sót → `brain add … --origin soat_chat` (vẫn theo mục 2: nhạy cảm không tự ghi). Nhật ký thiếu → `journal add`; quá 5 dòng → `journal replace`.
4. **Không đọc được chat** (không có công cụ) → bỏ qua, nhắn Tiko một lần "Soát chat 20:40: không đọc được chat" để Tiko ghi vào `state/yeu_cau_cho_repo.md`.
5. Không nhắn Khôi.

## 10. Sao lưu và khôi phục (Tiko)

**02:15** (routine Dọn dẹp đêm), sau `cleanup`:
1. `brain backup` → gói sổ nhớ + `config.toml` + `done.json` + báo cáo tháng vào **một file** `lifeos_saoluu_<thứ>.json`.
2. Tải lên Google Drive thư mục **"LifeOS · Sao lưu"**, **ghi đè** file cùng tên (lần đầu thì tạo) → luôn có 7 bản xoay vòng theo thứ.
3. `status tiko --type check --ok --note "sao lưu <tên file> ok"` (lỗi → `--fail --note "sao lưu: <lý do>"`).

**Khôi: "khôi phục sổ nhớ bản hôm thứ 4"** (trong khung chat Tiko):
1. Tải `lifeos_saoluu_thu4.json` từ Drive về `/workspace/lifeos/backup/`.
2. `brain restore <file>` (chỉ xem trước) → báo Khôi bản lúc mấy giờ, gồm những file nào → chờ Khôi "ok".
3. `brain restore <file> --apply` → báo xong (bản hiện tại đã được tự sao lưu thành `truoc_khoi_phuc_…json` phòng khi lỡ tay).

## 11. Chuyển trí nhớ cũ vào sổ (một lần, khi cập nhật lên 0.3.0)

LifeOS và Tiko **mỗi bot tự làm với trí nhớ riêng của mình**, khi Khôi nhắn thẳng:

1. Tìm trong trí nhớ riêng **theo từng chủ đề** (mỗi lần tìm tối đa 50 kết quả): học, trường, môn, thi, làm, công ty, sếp, đồng nghiệp, bạn, gia đình, người, thói quen, sở thích, thích, ghét, mục tiêu, kế hoạch, hứa, tập, chạy, gym, tiếng Pháp, ở, nhà, quê, sức khỏe, tiền. Gộp lại, bỏ trùng.
2. Bỏ chuyện máy móc của bot (đăng nhập, trang web, lỗi…). Chỉ giữ điều nói về Khôi và người quanh Khôi.
3. Điều thường → `brain add --by <bot> --origin grok …` (không cần hỏi; kết quả trùng thì thôi).
4. Điều **nhạy cảm** → không ghi. Gom thành **một** tin hỏi Khôi trong khung chat của mình: "Có N chuyện riêng mình đang nhớ: 1… 2… Muốn ghi cái nào vào sổ (cả đội đọc được)?" → chỉ ghi cái Khôi chọn, kèm `--sensitive`.
5. Riêng LifeOS: đọc `/workspace/lifeos/notes.md` (nếu có) → mỗi điều → `brain add --origin notes …` → đổi tên file thành `notes.da_chuyen.md`.
6. `brain stats` → `brain page` → cập nhật Page → nhắn Khôi: *"Đã chuyển N điều vào sổ. Xem ở Page 'LifeOS · Trí nhớ', mục Toàn bộ sổ; sai thì nhắn 'quên m5, m12' hoặc 'sửa m7: …'. Có thể sót vài điều — lần sau nhắc tới mình sẽ ghi."*

**Không xóa** trí nhớ riêng sau khi chuyển.
