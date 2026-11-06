# Cài đặt LifeOS — hướng dẫn cho Tiko

> Khôi chỉ cần nhắn Tiko: **"Cài LifeOS từ github.com/lucasnguyen1925/lifeos-grok, làm theo file CAI_DAT.md."**
> Tiko làm lần lượt từng bước, báo Khôi khi cần Khôi trả lời hoặc bấm duyệt. Tổng thời gian khoảng 30–45 phút.
> Mỗi bước xong ghi ✅ vào `/workspace/lifeos/state/cai_dat.md` để lỡ bị ngắt thì làm tiếp được.

## Bước 0 — Sao lưu hệ thống cũ

```bash
mkdir -p /workspace/_backup_lifeos_cu
cp -r /workspace/lifeos /workspace/mybk /workspace/zalo-congviec /workspace/_backup_lifeos_cu/ 2>/dev/null
```

Không xóa gì. Các file cũ `congty.md`, `canhan.md`, `hoctap.md` để nguyên cho tới khi chạy thử xong.

## Bước 1 — Tải bộ cài và tự kiểm tra

```bash
cd /workspace && git clone https://github.com/lucasnguyen1925/lifeos-grok.git
cd /workspace/lifeos-grok && python3 -m unittest discover -s tests
```

Phải thấy `OK`. Không OK → dừng, gửi Khôi nguyên văn lỗi để Khôi chuyển cho Claude.

## Bước 2 — Cấu hình cá nhân (hỏi Khôi)

```bash
mkdir -p /workspace/lifeos/{data,state,_status,log,history,context,dashboard}
cp /workspace/lifeos-grok/config/config.example.toml /workspace/lifeos/config.toml
```

Hỏi Khôi **gom vào một tin** rồi điền vào `/workspace/lifeos/config.toml`:

1. **Người quan trọng** (`[[people.vip]]`): tên/cách gọi sếp và quản lý trực tiếp, các giảng viên học kỳ này, người nhà. Mỗi người một mục, `aliases` là các cách gọi khác.
2. **Mã các khóa học BKeL học kỳ này** (`sources.hoctap.lms_course_ids`): lấy từ brief cũ trong `/workspace/brief/` hoặc hỏi bot Học tập, rồi nhờ Khôi xác nhận.
3. **Thẻ Zalo** (`[zalo] tags`): mặc định Công việc → congty, Trường học → hoctap, Bạn bè và Gia đình → canhan.
4. **Một ngày của Khôi** (`[day]`, `[office]`, `[training]`): giờ dậy/ngủ, giờ ăn, văn phòng, giáo án tập — giá trị mẫu đã theo lịch Khôi chốt 31/10; hỏi thêm **tên/địa điểm buổi chạy nhóm** (`training.group_run_keyword`).
5. Kiểm tra: `cd /workspace/lifeos-grok && python3 -m lifeos date today` chạy được (đọc được config).

Không ghi mật khẩu vào config. Mật khẩu đã ở Vault.

## Bước 3 — Cài skill chung

```bash
for s in /workspace/lifeos-grok/skills/*/; do
  name=$(basename "$s"); mkdir -p /home/box/agent-data/workflows/$name
  cp "$s/SKILL.md" /home/box/agent-data/workflows/$name/SKILL.md
done
ls /home/box/agent-data/workflows
```

Phải thấy 8 skill: `lifeos-noi-quy`, `lifeos-dang-nhap-lai`, `lifeos-zalo`, `lifeos-bao-cao`, `lifeos-chong-tri-hoan`, `lifeos-cap-nhat`, `lifeos-tri-nho`, `lifeos-lam-ho`.

## Bước 4 — Tạo bot Zalo

Tiko tạo bot mới tên **Zalo** (không tạo được thì nhờ Khôi). Khi có, gửi bot Zalo:
"Đọc toàn văn /workspace/lifeos-grok/bots/zalo.md, dùng làm hướng dẫn hệ thống của bạn, rồi tạo routine đúng như bảng Routine trong đó (chế độ exact)."

## Bước 5 — Cập nhật từng bot

Gửi **lần lượt** cho Học tập, Công ty, Cá nhân, LifeOS (và chính Tiko tự áp dụng `bots/tiko.md`):

> "LifeOS chuyển sang bộ cài mới. Đọc toàn văn /workspace/lifeos-grok/bots/<bot>.md, thay hướng dẫn hệ thống cũ bằng nội dung đó. Xóa routine cũ của bạn, tạo routine mới đúng bảng Routine (chế độ exact). Xong báo lại danh sách routine mới."

- Bot Học tập: lần trước sửa routine bị lỗi khi duyệt — nếu lại lỗi, báo Khôi mở khung chat bot Học tập để bấm duyệt trực tiếp.
- Từ giờ **chỉ bot Zalo mở Zalo**: nhắc Học tập, Công ty, Cá nhân đóng mọi tab `chat.zalo.me` đang mở.

Khôi sẽ phải bấm duyệt vài thẻ sửa routine — báo Khôi trước để Khôi biết.

## Bước 6 — Thông báo trên iPhone

Nhắn Khôi: "Trong app Grok Bot: bật thông báo cho **LifeOS** và **Tiko**; tắt thông báo cho Học tập, Công ty, Cá nhân, Zalo (ô thông tin của bot → bánh răng)."

## Bước 7 — Chạy thử (bắt buộc trước khi dùng thật)

Làm từng mục, ghi kết quả vào `state/cai_dat.md`:

| # | Thử | Đạt khi |
|---|---|---|
| 1 | Bot Zalo chạy một lần (nhắn bot: "chạy quét Zalo ngay") | `data/zalo.json` có hội thoại; trang **không** bị đá về "Đang đăng nhập..." |
| 2 | Đánh dấu lại chưa đọc | Hội thoại vốn chưa đọc vẫn hiện chưa đọc trên **iPhone** của Khôi sau khi bot đọc (hỏi Khôi) |
| 3 | Học tập, Công ty, Cá nhân mỗi bot quét đầy đủ một lần | 3 file `data/*.json` qua `validate`; `python3 -m lifeos digest` chạy không lỗi |
| 4 | Vòng tự đăng nhập SSO | Đăng xuất MyBK trong trình duyệt → nhắn bot Học tập "chạy quét đầy đủ như routine" → routine chuyển lại cho chat chính, chat chính tự đăng nhập lại bằng Vault và quét lại, không cần Khôi |
| 5 | Nhịp tim | `python3 -m lifeos health` liệt kê đủ bot, không có `chưa từng ghi nhịp tim` |
| 6 | Routine gửi ảnh | Tạo tạm cho LifeOS một routine chạy sau 5 phút: "chạy `python3 -m lifeos dashboard --png` và gửi ảnh dashboard.png". Ghi lại gửi được ảnh hay chỉ chữ, rồi xóa routine tạm |
| 7 | Grok Page | LifeOS tạo Page "LifeOS · Hiệu suất" từ `dashboard/page.md`, gửi Khôi link |
| 8 | Nhắc | LifeOS: `remind-at` cho 3 phút sau → tạo Reminder + báo thức "Test LifeOS" → Khôi xác nhận báo thức reo |
| 9 | Báo cáo | Nhắn LifeOS "làm thử báo cáo tối" → đúng mẫu, thứ/ngày đúng |
| 10 | Sổ nhớ | Khôi kể LifeOS một điều thử ("bạn thử nghiệm C là bạn cùng phòng") → hỏi **Tiko** "bạn thử nghiệm C là ai?" → Tiko trả lời đúng. Rồi Khôi nói LifeOS "quên giúp bạn thử nghiệm C" → các bot trả lời "đã xóa/không có" |
| 11 | Page Trí nhớ | LifeOS `brain page`, tạo Page "LifeOS · Trí nhớ" từ `dashboard/tri_nho.md`, gửi Khôi link để ghim |
| 12 | Sao lưu | Tiko `brain backup`, tải lên Drive "LifeOS · Sao lưu" → file trên Drive vẫn là `.json` (không thành Google Docs) |

Mục 6 không đạt (routine chỉ gửi được chữ) → không sao: báo cáo tuần gửi link Page thay cho ảnh.

**Thử "làm hộ" (bản 0.6.0, SPEC §15 mục 21-27).** Việc thử làm hộ phải diễn ra **trong khung chat LifeOS với lời duyệt của chính Khôi** (Grok không tính lời duyệt do bot khác chuyển lại). Chỉ dùng dữ liệu thử: mail gửi cho chính Khôi, sự kiện "[thử LifeOS]". **Không thử bằng việc thật.** Tiko đưa Khôi tin sau để dán vào khung chat LifeOS, rồi ghi kết quả vào `state/cai_dat.md`:

| # | Thử | Đạt khi |
|---|---|---|
| 13 | Mở (chỉ xem, không bấm gì, không đăng nhập) BKeL, MyBK, mail trường, mail công ty trong cửa sổ trình duyệt của LifeOS | Mỗi nơi báo: đã đăng nhập sẵn / hiện trang đăng nhập / lỗi |
| 14 | Gửi một mail "[thử LifeOS]" tới chính Gmail cá nhân của Khôi (địa chỉ lấy từ kết nối, ghi nguồn), Khôi nói "gửi đi" | Biết gửi được thật hay chỉ lưu được nháp |
| 15 | Trên đúng mail thử đó: gắn nhãn, lưu trữ, bỏ thùng rác | Từng thao tác làm được và lấy lại được hay không |
| 16 | Tạo sự kiện "[thử LifeOS]" trên lịch "LifeOS", sửa giờ, rồi xóa; mỗi bước hỏi Khôi duyệt | Làm được từng bước |
| 17 | "Chạy khô": với một form đăng ký hoặc khảo sát đang mở (**không phải quiz**: mở quiz có thể bắt đầu tính giờ), đi tới sát nút cuối, chụp màn hình, KHÔNG bấm nút cuối | Tới được nút cuối và chụp được màn hình |
| 18 | Với một việc thử có phiếu ghi "làm ở bot <X>": Khôi nhắn "làm V…" trong khung chat bot X | Bot X chạy `lamho show/approve/start/result` đúng |
| 19 | Sau tuần đầu: số ô "Việc nhanh" và thời lượng trong kế hoạch | Ô ngắn lại; bot quét không còn ghi `est_minutes` cho mail |

Loại nào qua thử thì thêm vào `[lamho] bat`. **Nhóm 3 không có cách thử vô hại**: chỉ có "chạy khô" (mục 17); bật từng loại khi có việc thật và Khôi đồng ý đúng loại đó, theo dõi lần đầu.

## Bước 8 — Bắt đầu tuần chạy thử

Nhắn Khôi:

> ✅ Cài xong LifeOS bản mới. Mai 6:00 có báo cáo đầu tiên. Tuần này là **tuần chạy thử**: thấy gì sai/thiếu cứ nói với LifeOS. Chủ nhật tới mình và LifeOS sẽ tổng kết xem chỉ số nào hữu ích.

Sau 7 ngày, gửi Khôi: các mục chạy thử, sự cố trong tuần, `state/yeu_cau_cho_repo.md`. Khôi chuyển cho Claude để cập nhật bộ cài.

## Gỡ hệ thống cũ (sau tuần chạy thử, khi Khôi đồng ý)

Xóa `congty.md`, `canhan.md`, `hoctap.md` cũ trong `/workspace/lifeos/`. Giữ `/workspace/_backup_lifeos_cu` thêm 30 ngày rồi xóa.
