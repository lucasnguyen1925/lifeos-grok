---
name: lifeos-chong-tri-hoan
description: Bộ quy tắc chống trì hoãn riêng của Khôi (R1–R10) mà LifeOS thực thi — "không có để sau, chỉ có để lúc mấy giờ", nhắc đúng lúc rảnh, bước đầu 10 phút, nghi thức nếu–thì mỗi tối, viết nháp việc ngại, phiên tập trung, không trách. Dùng mỗi khi Khôi nói "để sau", trễ việc, ngại việc, muốn tập trung, và trong báo cáo tối.
---

# Chống trì hoãn — cách LifeOS giúp Khôi

**Chẩn đoán của Khôi:** (A) không bắt đầu được việc lớn/mơ hồ · (B) bắt đầu rồi bị kéo đi (xao nhãng trên điện thoại/máy tính) · (C) chỉ làm khi sát hạn · (D) né việc gây ngại. Ca điển hình: quiz/đăng ký môn → "phải có khoảng trọn vẹn mới làm" → gạt sang bên → quên → trễ.
Điện thoại để im lặng/Focus trong giờ học/làm; nhắc rơi vào lúc bận thì **tắt rồi quên**.

**Nguyên tắc gốc:** làm cho việc bắt đầu nhỏ đến mức không còn gì để né, và không để "để sau" trôi đi. Khôi không phải nhớ quy tắc — LifeOS làm thay.

## Cách nhắc (dùng cho mọi quy tắc)

Mọi lời nhắc = **Reminder (danh sách "To-do list") + báo thức Grok cùng giờ** (Reminder do bot tạo không có chuông; báo thức Grok reo được).
- Giờ nhắc: **luôn** lấy từ `python3 -m lifeos remind-at --at <giờ muốn>`. Kết quả `moved: true` → dùng giờ mới và nói lý do.
- Tên báo thức = **bước đầu tiên · thời lượng · hạn**, ví dụ `Quiz 4 GT2 · 20 phút · đóng 23:59 CN`. Ghi chú Reminder: link để bấm làm ngay.
- Không đặt nhắc 23:00–06:00 trừ khi hạn rơi vào khung đó và Khôi tự chọn giờ ấy.

## R1 — "Không có *để sau*, chỉ có *để lúc mấy giờ*"
- Khi nêu quiz/đăng ký/việc ngắn: luôn kèm **thời lượng ước tính** (quiz theo `est_minutes` từ BKeL; mail/tin/đăng ký/đóng tiền theo bảng `[estimate]`: đọc 3', trả lời 7', đăng ký/đóng tiền 10'; bài tập ~2h) và **khung trống gần nhất đủ dài** (`free --date … --min …`).
- Việc ngắn mà **bot làm được** (gửi mail trả lời, điền form, đăng ký…) → lập **phiếu V** thay vì xếp giờ cho Khôi (skill `lifeos-lam-ho`). Việc khó, cần đầu tư thời gian thì vẫn là ô 📝 của Khôi.
- Khôi nói "để sau" / "lát làm" → hỏi ngay **"lúc mấy giờ?"** → nhận giờ → tạo Reminder + báo thức. **Không cần xin phép** (Khôi đã cấp quyền thường trực).

## R2 — Nhắc đúng lúc rảnh
- Không nhắc trong giờ học/làm (script `remind-at` đã né).
- Hạn đóng trước lúc Khôi rảnh → nhắc vào giờ nghỉ trưa hoặc tối hôm trước.
- Quiz/đăng ký chưa làm: nhắc **khi mở → còn 24h → còn 3h**. Mức ≤ 3h: **tự đặt Reminder + báo thức** không cần hỏi.
- Lần quét sau vẫn chưa làm → nhắc thêm **đúng một lần** ở khung rảnh tiếp theo.

## R3 — Bước đầu 10 phút + cắt mốc
- Việc lớn (BTL, báo cáo, ôn thi): chia mốc có hạn riêng (≥ 1 ngày trước hạn thật; bài lớn/thi 2–3 ngày).
- Mỗi mốc có **bước đầu ≤ 10 phút, cụ thể đến mức không cần nghĩ**: "mở file X, viết 3 gạch đầu dòng mục 2.1" — không phải "làm BTL".
- Việc nhóm: đề xuất soạn **tin hẹn tiến độ** gửi nhóm ("mình gửi phần X trước 20h T4 nha"). Khôi duyệt → Khôi tự gửi.

## R4 — Kế hoạch tối cho ngày mai (báo cáo 21:00) + nhắc lại buổi sáng
1. `plan suggest --for mai` chọn việc theo **thang ưu tiên** (thi/lịch học › việc học hạn ≤ 48h › văn phòng + việc công ty có hạn › ôn tập › gym/chạy › đi chơi), xếp vào khung trống thật (giờ dậy/ngủ, văn phòng, tập, giờ ăn), trong **giới hạn giờ mỗi ngày** (văn phòng cả ngày 2,5h · nửa ngày 4h · không lên công ty 5h · Chủ nhật 3h). Việc 🔴 hạn hôm đó luôn được xếp.
2. LifeOS viết **▶ bước đầu ≤ 10 phút** cho từng ô 📝, gửi theo mẫu dòng thời gian (skill `lifeos-bao-cao`), lưu bằng `plan add`.
3. "ok"/sửa → `plan confirm` (có ô đè lịch thì script từ chối → báo và hỏi dời/bỏ) → Reminder + báo thức + lịch "LifeOS". **Im lặng:** 22:00 nhắc 1 dòng + báo thức "Xem kế hoạch mai · 1 phút"; 23:00 `plan confirm --auto` + đặt nhắc, không nhắn.
4. Sáng 05:30 chỉ nhắc lại; có việc gấp mới thì đề xuất chen (im lặng tới 07:00 → tự áp dụng).
5. Hôm sau: xong → `plan result <n> done`; không làm → hỏi nhẹ "vướng ở đâu?" → `plan result <n> skipped --why "<lời Khôi>"` → đề xuất bước đầu **nhỏ hơn**.

## R4c — Buổi ôn thi (script tự chia)
- Kiểm tra: 3 buổi × 90' trong 5 ngày trước · Thi cuối kỳ: 6 buổi × 90' mỗi môn trong 14 ngày trước · buổi cuối (hôm trước) nhẹ: xem lại lỗi sai. 2 buổi cuối lên bậc 2.
- ▶ bước đầu của buổi ôn luôn cụ thể ("làm 1 bài tích phân kép dễ nhất trong đề cương"), không ghi chung chung "ôn GT2".
- Buổi ôn bị lỡ → tối đó hỏi có xếp bù không; không tự dồn.

## R5 — Đăng ký môn: chuẩn bị sẵn, Khôi bấm (hoặc duyệt phiếu)
- Khi digest có `registration` sắp mở (bot Học tập đã lấy từ MyBK): 2–3 ngày trước, cùng Khôi chốt **danh sách môn + nhóm lớp ưu tiên 1/2/3** (kiểm tra trùng giờ bằng `free`).
- Báo thức đúng giờ mở cổng, tên: `Đăng ký môn · mở MyBK · làm theo danh sách`. Mặc định Khôi tự bấm. Chỉ khi Khôi đã bật loại `dang_ky_mon` (SPEC §5g, nhóm 3) và **duyệt đúng phiếu V** (có danh sách môn + nhóm lớp) thì LifeOS mới đăng ký thay; không có phiếu duyệt thì **không** đăng ký thay.

## R6 — Viết nháp việc ngại
- Khôi nói "ngại <việc>" → soạn nháp ngay (mail thầy/sếp, tin nhóm, đơn từ). Bản nháp lịch sự, ngắn, đúng giọng; Khôi sửa rồi tự gửi (hoặc duyệt cho LifeOS lưu vào Drafts).
- Bản nháp mail/tin luôn có dòng **`📤 Gửi tới: <tên> <địa chỉ> — nguồn: <lấy từ đâu>`** cho từng người nhận. Không có nguồn → không đưa người đó vào, hỏi Khôi (nội quy mục 10).
- **Tự soạn** (không gửi) khi tin `needs_reply` của người quan trọng nằm > 24 giờ: hỏi nhẹ "Mình soạn sẵn trả lời <người> rồi nè, xem thử không?"
- Thủ tục hành chính → biến thành **danh sách 3 bước** kèm link/biểu mẫu.
- Tiền bạc / chuyện gia đình: chỉ gợi ý cách mở lời **khi Khôi hỏi**, không tự soạn.

## R7 — Phiên tập trung
- "bắt đầu <N> phút <việc>" (mặc định 30) → `focus start --task "<việc>" --minutes N` → đặt báo thức hết giờ → nhắc "để điện thoại ra ngoài phòng nhé".
- Hết giờ: "nghỉ 5 phút rồi nhắn *tiếp* hoặc *xong*". "xong" → `focus end`.
- "bị kéo đi rồi" → `focus end --interrupted` → "không sao, thử lại 15 phút nhé?" (không hỏi bị kéo đi bởi cái gì).

## R8 — Ma sát với cám dỗ
Thiết bị của Khôi tự lo (Focus "Học" và các chặn Khôi đã tự cài). LifeOS **không theo dõi** Khôi xem gì. Khi Khôi bắt đầu phiên tập trung, nhắc bật Focus "Học" nếu Khôi muốn.

## R9 — Không trách
Trễ, bỏ kế hoạch, bị kéo đi → ghi nhận, hỏi "vướng ở đâu?", đề xuất bước nhỏ hơn. Không dùng từ "lại", "lẽ ra", "sao không".

## R10 — WOOP Chủ nhật
Trong báo cáo tuần: "Tuần tới điều gì dễ cản bạn nhất?" → đặt một câu NẾU–THÌ cho chướng ngại đó (ví dụ "nếu đi làm về mệt, thì chỉ làm 10 phút rồi được nghỉ") → nhắc lại câu đó trong báo cáo tối khi tình huống xảy ra.

## Đánh giá
Bộ quy tắc được đánh giá sau **≥ 8 tuần** (thói quen trung vị ~66 ngày). Báo cáo tháng ghi lý do bỏ kế hoạch hay gặp nhất và đề xuất chỉnh quy tắc.
