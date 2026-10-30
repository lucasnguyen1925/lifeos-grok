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

## Lịch một ngày

| Giờ | Việc |
|---|---|
| 05:10 / 20:10 | Bot Zalo đọc Zalo |
| 05:30 / 20:30 | Học tập, Công ty, Cá nhân quét đầy đủ |
| 05:50 / 20:50 | Tiko kiểm tra sức khỏe, sửa sự cố |
| **06:00 / 21:00** | **LifeOS báo cáo** (tối có kế hoạch nếu–thì cho ngày mai) |
| 11:30 · 14:30 · 17:30 | Quét nhẹ nguồn hay có việc gấp → có việc 🔴 mới thì LifeOS báo ngay |
| 22:00 / 23:00 | Nhắc / tự áp dụng kế hoạch ngày mai nếu Khôi chưa trả lời |
| Chủ nhật 21:00 | Báo cáo tuần + ảnh dashboard · ngày cuối tháng: báo cáo tháng |

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
