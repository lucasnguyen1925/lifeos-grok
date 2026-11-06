# LifeOS cho Grok Bot

Bộ cài cho đội bot LifeOS chạy trên **Grok Bot**: sổ tay hướng dẫn cho từng bot, nội quy chung, và các script tính toán (độ gấp, trùng lịch, thứ/ngày, chỉ số hiệu suất, dashboard).

**Repo này không chứa dữ liệu cá nhân, mật khẩu hay tin nhắn**, và **không tự chạy gì trên GitHub**. Các bot tải về rồi làm theo. Dữ liệu và cấu hình cá nhân nằm trên máy của Grok Bot (`/workspace/lifeos/`), mật khẩu nằm trong Vault.

Đặc tả đầy đủ (mọi quyết định đã chốt): [SPEC.md](SPEC.md).

## Đội bot

```
                         Khôi
          ┌───────────────┴───────────────┐
   LifeOS — Trợ lý riêng          Tiko — VP Vận hành
   (việc, lịch, tin nhắn)         (các bot chạy ổn)
          │                               │
   ┌──────┼──────────┬──────────┐         │
 Học tập  Công ty  Cá nhân    Zalo ◄──────┘
```

| Bot | Việc | Hướng dẫn |
|---|---|---|
| LifeOS | Báo cáo 6:00/21:00, cảnh báo việc gấp, nhận lệnh, nhắc việc, chống trì hoãn | [bots/lifeos.md](bots/lifeos.md) |
| Tiko | Kiểm tra sức khỏe, tự đăng nhập lại, cập nhật bộ cài, dọn dữ liệu | [bots/tiko.md](bots/tiko.md) |
| Học tập | MyBK, AAO, BKeL, mail và lịch trường | [bots/hoctap.md](bots/hoctap.md) |
| Công ty | Mail và lịch công ty, nhóm Zalo công việc | [bots/congty.md](bots/congty.md) |
| Cá nhân | 2 Gmail, lịch cá nhân, Reminders, Zalo bạn bè/gia đình | [bots/canhan.md](bots/canhan.md) |
| Zalo | Bot duy nhất mở Zalo Web, đọc tin cho cả đội | [bots/zalo.md](bots/zalo.md) |

## Sổ nhớ — cả đội cùng nhớ chuyện của Khôi

Khôi kể chuyện cho LifeOS (hay Tiko) một lần là **cả 6 bot cùng biết**: hồ sơ ngắn về Khôi, người quen, thói quen, lời hứa đang dở, chuyện đã nói mỗi ngày, kho "lưu cái này". Bot tự ghi lặng lẽ, tối 21:00 báo một dòng "🧠 Nhớ thêm…"; Khôi soát ở Grok Page "LifeOS · Trí nhớ", nói "quên giúp…" là xóa. Mỗi đêm sao lưu lên Google Drive. Chi tiết: [SPEC.md §5c](SPEC.md), skill [lifeos-tri-nho](skills/lifeos-tri-nho/SKILL.md).

## Bản đồ phân công — việc nào giao bot nào

LifeOS biết **ai lo mảng nào**: chuyện trường (mail, Drive, BKeL, MyBK) → Học tập · việc công ty → Công ty · đời sống → Cá nhân · Zalo → bot Zalo · sự cố, kết nối → Tiko. Khôi nhờ việc gì, LifeOS giao ngay cho đúng bot và báo lại khi có kết quả (quá 10 phút chưa xong thì báo Khôi). Bản đồ in trong hồ sơ ngắn nên cả đội cùng biết. Chi tiết: [SPEC.md §5e](SPEC.md).

## LifeOS làm hộ — bot đề xuất, Khôi duyệt

Việc nào bot làm được (trả lời mail, điền form, đăng ký, nộp bài, thanh toán…), LifeOS lập một **phiếu V1, V2…** trong báo cáo sáng/tối: Khôi nói "làm V1" là bot làm luôn, "bỏ V2", "sửa V1: …" thì sửa. Im lặng = không làm gì. Việc khó, cần đầu tư thời gian vẫn là của Khôi. Từng loại việc có công tắc, mặc định tắt; thanh toán có mức tối đa mỗi lần do Khôi đặt; xóa chỉ vào thùng rác. Việc nhanh trong kế hoạch tính theo bảng ngắn (đọc mail 3', trả lời 7', đăng ký 10'). Chi tiết: [SPEC.md §5g](SPEC.md), skill [lifeos-lam-ho](skills/lifeos-lam-ho/SKILL.md).

## Lịch một ngày

| Giờ | Việc |
|---|---|
| 04:40 / 20:10 | Bot Zalo đọc Zalo |
| 05:00 / 20:30 | Học tập, Công ty, Cá nhân quét đầy đủ |
| 05:20 / 20:50 | Tiko kiểm tra sức khỏe, sửa sự cố |
| **05:30** | **LifeOS báo cáo sáng** — nhắc lại kế hoạch đã chốt, chen việc gấp mới |
| 07:00 | Tự áp dụng việc chen buổi sáng nếu Khôi chưa trả lời |
| 11:30 · 14:30 · 17:30 | Quét nhẹ nguồn hay có việc gấp → có việc 🔴 mới thì LifeOS báo ngay |
| **Chủ nhật 20:00** | **Kế hoạch tuần**: văn phòng T2–T7 (ghi Office lên lịch công ty khi Khôi "ok"), buổi tập, việc lớn + ảnh dashboard |
| 20:40 | LifeOS soát lại chat cả ngày, bổ sung sổ nhớ |
| **21:00** | **LifeOS báo cáo tối** — tổng kết hôm nay + kế hoạch mai (dòng thời gian có giờ) + 🧠 nhớ thêm |
| 22:00 / 23:00 | Nhắc / tự áp dụng kế hoạch ngày mai nếu Khôi chưa trả lời |
| 02:15 | Tiko dọn dữ liệu cũ, sao lưu sổ nhớ lên Drive |

## Cài đặt

Nhắn **Tiko**: *"Cài LifeOS từ github.com/lucasnguyen1925/lifeos-grok, làm theo file CAI_DAT.md."* — chi tiết ở [CAI_DAT.md](CAI_DAT.md).

## Sau này muốn đổi

| Muốn | Làm |
|---|---|
| Đổi thông tin cá nhân (người quan trọng, giờ quét, thẻ Zalo, mã môn) | Nhắn LifeOS hoặc Tiko — bot sửa `config.toml` trên máy, không cần đụng repo |
| Thêm/đổi tính năng | Mở session Claude trên repo này, nói điều muốn đổi → Claude cập nhật repo → nhắn Tiko *"cập nhật LifeOS"* |
| Bản mới bị lỗi | Nhắn Tiko *"quay lại bản trước"* |

## Cho người sửa code

- Chỉ dùng thư viện chuẩn Python ≥ 3.11 (máy bot: 3.13). Không cần `pip install`.
- Test: `python3 -m unittest discover -s tests`
- Lệnh: `python3 -m lifeos --help`
- Định dạng dữ liệu: [docs/DINH_DANG_DU_LIEU.md](docs/DINH_DANG_DU_LIEU.md)
- Skill (chép vào `/home/box/agent-data/workflows/`): [skills/](skills/)
- Mỗi lần đổi, ghi vào [CHANGELOG.md](CHANGELOG.md) phải làm gì khi cập nhật (Tiko làm theo đó).
