# LifeOS trên Grok Bot — Đặc tả hệ thống

> Phiên bản 0.1 · chốt qua buổi grill 29–31/10/2026.
> Thay thế hoàn toàn spec cũ (LifeOS chạy trên Claude + Supabase — đã tắt ngày 31/10/2026).
> Repo này public: không ghi thông tin cá nhân vào đây; thông tin cá nhân nằm trong `config.toml` trên máy bot.

## 1. Mục tiêu

Khôi (sinh viên, đang làm part-time) có thông tin rải ở nhiều nơi — nhiều Gmail và Google Calendar, cổng trường MyBK/AAO, LMS BKeL, Zalo, Reminders iPhone — nên hay sót thông báo và deadline. LifeOS là một đội bot Grok Bot chạy 24/7 để:

1. **Không sót việc**: mọi deadline, lịch thi, thay đổi lịch, tin nhắn cần trả lời được gom về một chỗ, xếp độ gấp bằng luật cố định.
2. **Báo đúng lúc**: báo cáo 06:00 và 21:00; việc 🔴 phát sinh giữa ngày được báo ngay.
3. **Giúp làm, không chỉ nhắc**: chống trì hoãn theo bộ quy tắc riêng của Khôi (§10).
4. **Nhìn lại được**: chỉ số hiệu suất, báo cáo tuần/tháng, dashboard (§11).
5. **Ít phải động tay**: tự đăng nhập lại, tự theo dõi sức khỏe; Khôi phải can thiệp ≤ 1 lần/tuần.

## 2. Nguyên tắc thiết kế

| # | Nguyên tắc | Hệ quả |
|---|---|---|
| P1 | **Khôi chỉ làm việc với LifeOS** | Bot mảng không nhắn Khôi. Tiko chỉ nhắn khi cần Khôi ra tay |
| P2 | **Việc có luật cố định → script; việc cần diễn đạt/hiểu → AI** | Độ gấp, trùng lịch, thứ/ngày, khung trống, chỉ số do Python tính. AI đọc nguồn và viết báo cáo |
| P3 | **Một chuẩn dữ liệu duy nhất** | Bot mảng ghi JSON chuẩn, `validate` trước khi dùng |
| P4 | **Chỉ đọc, mọi việc gửi đi phải Khôi duyệt** | Bot không gửi/nộp/đăng ký/thanh toán/xóa thay Khôi. Lời "Khôi đồng ý" do bot khác chuyển lại không tính |
| P5 | **Mật khẩu chỉ ở Vault** | Không xuất hiện trong chat, file, repo |
| P6 | **Không lách lớp bảo mật — trừ CAPTCHA trên tài khoản cá nhân** | Zalo và SSO HCMUT: bot được tự giải CAPTCHA tối đa 1 lần/lượt (Khôi cho phép 31/10). Xác minh 2 bước, cảnh báo bất thường, CAPTCHA ở tài khoản công ty → dừng, chuyển Khôi |
| P7 | **Một bot giữ một phiên dễ vỡ** | Chỉ bot Zalo mở Zalo Web |
| P8 | **Repo là sổ tay, không phải nơi chạy** | Không có job nào chạy trên GitHub. Bot `git pull` rồi làm theo |

## 3. Nền tảng (đã kiểm tra thực tế 29–31/10/2026)

- Grok Bot: các bot dùng chung **một máy Linux trên cloud** (ổ đĩa, trình duyệt, phiên đăng nhập, terminal). Python 3.13, git, Chromium headless, ra được internet.
- Bot **không phải ranh giới bảo mật**: dữ liệu bot này ghi, bot khác đọc được.
- Routine: cron giờ VN, có chế độ **exact**; mỗi bot chỉ xem/sửa routine của chính nó; routine **không điền login từ Vault được**, lượt chat thường thì được; routine chuyển việc cho bot chính bằng tin nhắn ưu tiên.
- Skill: `/home/box/agent-data/workflows/<tên>/SKILL.md`, dùng chung mọi bot.
- iPhone: đọc/ghi Reminders, đọc danh bạ, đặt báo thức. **Reminder do bot tạo không có chuông**; **báo thức Grok reo được** (kể cả lúc bận).
- Grok **Page**: trang riêng tư xem trên điện thoại, link cố định, bot cập nhật nội dung (không nhận nguyên file HTML).

## 4. Tổ chức

```
                                Khôi
                 ┌────────────────┴────────────────┐
        LifeOS — Trợ lý riêng              Tiko — VP Vận hành
        (nội dung: việc, lịch, tin)        (bộ máy: các bot chạy ổn)
                 │                                  │
        ┌────────┬────────┬────────┐                │
     Học tập   Công ty  Cá nhân   Zalo  ◄────────────┘
     (phân tích)               (thu thập)
```

| Bot | Vai trò | Hướng dẫn |
|---|---|---|
| LifeOS | Người duy nhất nói chuyện với Khôi về nội dung; báo cáo, cảnh báo, nhận lệnh, nhắc, chống trì hoãn | `bots/lifeos.md` |
| Tiko | Sức khỏe hệ thống, đăng nhập lại, cập nhật bộ cài, dọn dữ liệu; báo cáo hệ thống tuần | `bots/tiko.md` |
| Học tập | MyBK, AAO, BKeL, mail + lịch trường, Zalo "Trường học" | `bots/hoctap.md` |
| Công ty | Mail + lịch công ty (trình duyệt), Zalo "Công việc" | `bots/congty.md` |
| Cá nhân | 2 Gmail, 2 lịch, Reminders, danh bạ, Zalo "Bạn bè"/"Gia đình" | `bots/canhan.md` |
| Zalo | **Bot duy nhất mở Zalo Web**, thu tin cho cả đội, không đánh giá | `bots/zalo.md` |

## 5. Lịch chạy (giờ VN, chế độ exact)

| Giờ | Bot | Việc |
|---|---|---|
| 05:10 · 20:10 | Zalo | Đọc Zalo → `data/zalo.json` |
| 05:30 · 20:30 | Học tập · Công ty · Cá nhân | Quét đầy đủ |
| 11:30 · 14:30 · 17:30 | Học tập · Công ty · Cá nhân | Quét nhẹ: BKeL + mail/lịch trường · mail/lịch công ty · lịch cá nhân |
| 05:50 · 20:50 | Tiko | Kiểm tra sức khỏe, xử lý sự cố trước giờ báo cáo |
| **06:00 · 21:00** | **LifeOS** | **Báo cáo** (21:00: chốt sổ ngày, kế hoạch nếu–thì) |
| 22:00 · 23:00 | LifeOS | Nhắc xem kế hoạch mai · tự áp dụng nếu Khôi im lặng |
| 02:15 | Tiko | Dọn dữ liệu quá hạn |
| CN 10:00 | Tiko | Báo cáo hệ thống tuần |
| CN 21:00 · ngày cuối tháng 21:00 | LifeOS | Báo cáo tuần / tháng + ảnh dashboard |

## 6. Dữ liệu

| File (trong `/workspace/lifeos/`) | Ai ghi | Nội dung |
|---|---|---|
| `config.toml` | Tiko/LifeOS theo lời Khôi | Thông tin cá nhân, người quan trọng, giờ, thẻ Zalo |
| `data/{hoctap,congty,canhan}.json` | Bot mảng | Việc/sự kiện theo chuẩn — `docs/DINH_DANG_DU_LIEU.md` |
| `data/zalo.json` | Bot Zalo | Tin Zalo theo thẻ |
| `digest.json` | Script `digest` | Tổng hợp đã xếp độ gấp, trùng lịch, lịch hôm nay/mai |
| `done.json` | Script `done` | Việc Khôi đã xác nhận xong — không bao giờ nhắc lại |
| `_status/<bot>.json`, `health.json` | Script `status`/`health` | Nhịp tim, sức khỏe |
| `state/` | Script | Đã thấy gì (phát hiện mới/đổi), đã báo gì, kế hoạch nếu–thì |
| `log/` | Script | Việc xong, phiên tập trung, tự khai |
| `history/daily/`, `context/weekly/`, `context/monthly/` | Script + LifeOS viết nhận xét | Sổ ngày, tóm tắt tuần/tháng (trí nhớ dài hạn của LifeOS) |
| `dashboard/` | Script | `index.html`, `page.md`, `dashboard.png` |

Script tự phát hiện **việc mới** và **việc bị đổi** (hạn, giờ, phòng) bằng cách so với lần trước — không phụ thuộc bot mảng tự ghi.

## 7. Độ gấp (luật viết cứng — `lifeos/urgency.py`)

Mỗi việc lấy mức cao nhất mà nó thỏa:

| Mức | Điều kiện |
|---|---|
| 🔴 GẤP | Hạn ≤ 24h · quá hạn ≤ 7 ngày chưa xong · thay đổi lịch/hạn diễn ra trong 48h · trùng lịch trong 48h · thông báo có từ khóa khẩn (hoãn thi, nghỉ học, đổi phòng…) trong 72h · người quan trọng chờ trả lời > 12h |
| 🟠 CAO | Hạn 24–72h · deadline/quiz/thi/đăng ký mới xuất hiện (≤ 24h) · khoản phải đóng ≤ 7 ngày · cần trả lời · sắp mở đăng ký (≤ 72h) · có thay đổi (xa hơn 48h) |
| 🟡 TRUNG BÌNH | Hạn 3–7 ngày · thông báo · tin nhắc đến Khôi |
| ⚪ ĐỂ BIẾT | Còn lại |

Hạn chỉ có ngày = 23:59. Lịch thi: hạn = giờ thi. Người quan trọng: danh sách trong `config.toml` (sếp/quản lý, giảng viên, gia đình).
Báo cáo: 🔴 hiện đủ, 🟠 tối đa 7, 🟡/⚪ gom thành "và N việc khác".

## 8. Cảnh báo giữa ngày

Bot mảng quét xong → `digest` → `alerts`. Có việc 🔴 **chưa từng báo** → tin ưu tiên cho LifeOS → LifeOS gửi Khôi **một tin gộp** kèm khung trống gần nhất → đánh dấu đã báo. **23:00–06:00 không báo** (dồn vào báo cáo 06:00). Sau mỗi báo cáo 06:00/21:00, mọi việc 🔴 hiện có được đánh dấu đã báo.

## 9. Đăng nhập & sự cố

- **Tự đăng nhập lại** (skill `lifeos-dang-nhap-lai`): routine gặp trang đăng nhập → ghi `needs_login`, quét tiếp nguồn khác → tin ưu tiên cho chính mình → lượt chat thường đăng nhập bằng Vault → quét lại nguồn đó. MyBK: nếu SSO báo đã đăng nhập mà MyBK chưa nhận → bấm "Tài khoản HCMUT".
- **Tối đa 1 lần đăng nhập mỗi lượt.** Zalo đăng nhập bằng mật khẩu qua menu ☰. CAPTCHA ở Zalo/SSO HCMUT → bot tự giải 1 lần. OTP / xác nhận điện thoại / cảnh báo bất thường / CAPTCHA ở tài khoản công ty → dừng, Tiko nhắn Khôi hướng dẫn 30 giây.
- **Zalo**: chỉ bot Zalo mở (3 bot cùng mở làm phiên bị đá liên tục). Đọc xong, hội thoại vốn chưa đọc được **đánh dấu lại "chưa đọc"**; người gửi vẫn thấy "Đã xem" — Khôi chấp nhận. Không bấm "Đồng bộ ngay".
- **Sức khỏe** (Tiko, 05:50/20:50): bot lỡ lần chạy → nhắc chạy lại; lỗi ≥ 2 lần liên tiếp → tìm nguyên nhân; nguồn lỗi > 36h → 🔴, báo Khôi. Báo cáo LifeOS có dòng ⚙️ mảng nào dữ liệu cũ.

## 10. Chống trì hoãn

Chi tiết: skill `lifeos-chong-tri-hoan`. Chẩn đoán: không bắt đầu được việc lớn · bị xao nhãng kéo đi · chỉ làm khi sát hạn · né việc gây ngại · quiz/đăng ký bị "để sau" rồi quên.

| Quy tắc | Tóm tắt |
|---|---|
| R1 | "Không có *để sau*, chỉ có *để lúc mấy giờ*" — kèm thời lượng ước tính + khung trống gần nhất |
| R2 | Nhắc = **Reminder + báo thức Grok**, không bao giờ trong giờ học/làm (script `remind-at`); quiz/đăng ký nhắc khi mở → 24h → 3h |
| R3 | Việc lớn cắt mốc, mỗi mốc có bước đầu ≤ 10 phút; việc nhóm hẹn tiến độ với người khác |
| R4 | Tối 21:00: 1 việc chính + ≤ 2 việc nhanh, câu NẾU–THÌ; "ok" là xong; im lặng → 22:00 nhắc, 23:00 tự áp dụng |
| R5 | Đăng ký môn: chuẩn bị danh sách trước, báo thức giờ mở cổng, Khôi tự bấm |
| R6 | LifeOS viết nháp việc ngại; tin người quan trọng > 24h → tự soạn nháp (không gửi) |
| R7 | Phiên tập trung 30 phút mặc định, nghỉ 5 phút, bị kéo đi thì thử lại 15 phút |
| R8 | Ma sát mức vừa trên thiết bị của Khôi (Focus và các chặn Khôi tự cài); bot không theo dõi nội dung |
| R9 | Không trách — hỏi "vướng ở đâu?", bước đầu nhỏ hơn |
| R10 | WOOP mỗi Chủ nhật |

Quyền thường trực của LifeOS: tự đặt Reminder + báo thức khi Khôi nói "để lúc X", khi quiz/đăng ký còn ≤ 3h, khi 23:00 tự áp dụng kế hoạch. Đánh giá bộ quy tắc sau ≥ 8 tuần.

## 11. Hiệu suất, báo cáo tuần/tháng, dashboard

**Chỉ số (chạy thử 1 tuần rồi xem lại):**

| Nhóm | Chỉ số |
|---|---|
| A. Hoàn thành | Việc xong · % xong đúng hạn · việc trễ |
| B. Học tập | Quiz/đăng ký bị trễ (mục tiêu 0) · điểm TB có trọng số tín chỉ |
| D. Cân bằng | Giờ học/làm/cá nhân theo lịch · ngày có trùng lịch · tối có lịch sau 22:00 |
| G. Chống trì hoãn | % kế hoạch nếu–thì làm được · phút/phiên tập trung · số lần bị kéo đi · giờ từ lúc thấy tới lúc xong · ngày có tin quan trọng chờ > 24h |
| F. Tự khai | Phút tiếng Pháp · năng lượng 1–5 (một dòng trong báo cáo tối) |

**Vòng đời dữ liệu:** 21:00 chốt sổ ngày → Chủ nhật chốt tuần → ngày cuối tháng chốt tháng (script tính số, LifeOS viết nhận xét: 3 điểm sáng, 3 cần cải thiện, 3 đề xuất). Giữ: ngày + tuần **90 ngày**, Zalo thô **7 ngày**, tháng **lâu dài**.

**Dashboard:** script dựng HTML + SVG (Python thuần) → Grok Page "LifeOS · Hiệu suất" cập nhật mỗi tối + ảnh PNG gửi kèm báo cáo tuần/tháng.

## 12. Quyền

| Hành động | LifeOS | Bot mảng / Zalo | Tiko |
|---|---|---|---|
| Đọc nguồn, ghi file của mình | ✔ | ✔ | ✔ |
| Soạn nháp | ✔ | — | — |
| Reminder + báo thức | ✔ trong 3 trường hợp thường trực; còn lại hỏi | — | — |
| Tạo/sửa sự kiện lịch | Hỏi Khôi | — | — |
| Gửi mail/tin | Chỉ khi Khôi nói "gửi đi" sau khi xem bản cuối | ✘ | ✘ |
| Nộp bài, làm quiz, đăng ký, thanh toán, xóa | ✘ | ✘ | ✘ |
| Mở Zalo | ✘ | Chỉ bot Zalo | ✘ |
| Sửa `config.toml` | Theo lời Khôi | ✘ | Theo lời Khôi |

## 13. Cập nhật & mở rộng

- Đổi thông tin cá nhân → nhắn LifeOS/Tiko, sửa `config.toml`, không đụng repo.
- Đổi/thêm tính năng → Claude sửa repo, ghi `CHANGELOG.md` → Khôi nhắn Tiko "cập nhật LifeOS" → Tiko `git pull`, chạy test, áp dụng theo CHANGELOG (skill `lifeos-cap-nhat`). Lỗi → "quay lại bản trước".
- Thêm nguồn mới = thêm `source` vào bot mảng phù hợp (hoặc một bot mảng mới với `domain` mới — cần sửa `lifeos/common.py` → `DOMAINS`).
- Bot không tự sửa hướng dẫn của mình cho thay đổi lớn; yêu cầu ghi vào `state/yeu_cau_cho_repo.md`.

## 14. Rủi ro đã chấp nhận

- Tự động đọc MyBK/BKeL/Zalo bằng trình duyệt là vùng xám về điều khoản dịch vụ; Zalo có thể khóa tạm khi thấy đăng nhập lạ từ cloud (giới hạn 1 lần đăng nhập/lượt, dừng khi có cảnh báo).
- **Bot tự giải CAPTCHA khi đăng nhập Zalo và SSO HCMUT** (Khôi quyết định 31/10, chấp nhận rủi ro tài khoản bị khóa). Đây là lách cơ chế chống bot của dịch vụ, có thể vi phạm điều khoản của Zalo/trường; nền tảng Grok có thể không cho bot làm — khi đó quay về nhờ Khôi.
- Đọc mail/lịch công ty qua trình duyệt trên máy dùng chung: chỉ lưu dữ liệu tối thiểu (tiêu đề, hạn, người yêu cầu, link).
- Người gửi tin Zalo riêng thấy "Đã xem" khi bot đọc.
- Báo thức Grok có thể reo cả lúc máy im lặng → luật "không nhắc trong giờ học/làm" là bắt buộc.
- Việc 🔴 phát sinh sau 17:30 chỉ được bắt ở lần quét 20:30.

## 15. Chưa kiểm chứng — Tiko chạy khi cài (CAI_DAT.md bước 7)

1. Bot Zalo một mình mở Zalo thì phiên ổn định (hết "Đang đăng nhập...").
2. "Đánh dấu chưa đọc" trên Zalo Web có đồng bộ về iPhone.
3. Vòng tự đăng nhập SSO chạy trọn không cần Khôi.
4. Routine gửi được ảnh (nếu không: báo cáo tuần gửi link Page thay ảnh).
5. Grok Page tạo và cập nhật được từ `page.md`.

## 16. Tiêu chí thành công

- Tuần chạy thử: báo cáo 06:00/21:00 đúng giờ 7/7 ngày; **0 deadline BKeL bị sót**; 0 việc đã xong bị nhắc lại; 0 sai thứ/ngày.
- Khôi phải đăng nhập tay ≤ 1 lần/tuần.
- Sau 8 tuần: quiz/đăng ký trễ = 0; % kế hoạch nếu–thì làm được có xu hướng tăng.
