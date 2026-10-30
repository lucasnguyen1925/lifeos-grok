---
name: lifeos-cap-nhat
description: Cách Tiko cập nhật bộ cài LifeOS từ GitHub (git pull), áp dụng thay đổi cho từng bot, và quay lại bản trước khi lỗi. Dùng khi Khôi nói "cập nhật LifeOS" hoặc "quay lại bản trước".
---

# Cập nhật LifeOS (Tiko)

Bộ cài ở `/workspace/lifeos-grok`, lấy từ `https://github.com/lucasnguyen1925/lifeos-grok`.

## "Cập nhật LifeOS"

```bash
cd /workspace/lifeos-grok
git rev-parse --short HEAD > /workspace/lifeos/state/previous_version.txt
git pull --ff-only
git log --oneline <bản cũ>..HEAD        # danh sách thay đổi
python3 -m unittest discover -s tests   # phải OK; lỗi → quay lại bản cũ ngay, báo Khôi
```

Rồi xem `CHANGELOG.md` mục mới nhất, áp dụng đúng những gì nó ghi:

| Thay đổi | Việc phải làm |
|---|---|
| `skills/<tên>/` | Chép đè vào `/home/box/agent-data/workflows/<tên>/` |
| `bots/<bot>.md` | Gửi tin ưu tiên cho bot đó: "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md (đọc toàn văn, thay hướng dẫn cũ)". Nếu đổi routine: bot sửa routine của chính nó — Khôi có thể phải bấm duyệt thẻ |
| `config/config.example.toml` có khóa mới | Thêm khóa mới vào `/workspace/lifeos/config.toml` với giá trị mẫu; **không** ghi đè giá trị Khôi đã điền |
| Chỉ `lifeos/*.py` | Không phải làm gì thêm |

Cuối cùng nhắn Khôi một tin ngắn: bản mới có gì (2–3 dòng, không thuật ngữ), Khôi có cần bấm duyệt gì không.

## "Quay lại bản trước"

```bash
cd /workspace/lifeos-grok
git checkout $(cat /workspace/lifeos/state/previous_version.txt)
```

Áp dụng lại skill/hướng dẫn của bản đó như trên. Báo Khôi đã quay lại bản nào.

## Thay đổi nhỏ Khôi yêu cầu trực tiếp

- Đổi thông tin cá nhân (người quan trọng, giờ quét, thẻ Zalo, mã môn) → sửa `/workspace/lifeos/config.toml`. Không cần đụng repo.
- Đổi cách làm việc của bot → **không sửa tay** hướng dẫn bot (lần cập nhật sau sẽ ghi đè). Ghi yêu cầu vào `/workspace/lifeos/state/yeu_cau_cho_repo.md` và nói Khôi: "Mình ghi lại rồi, lần tới nhờ Claude đưa vào bộ cài." Việc gấp thì làm tạm, ghi rõ là tạm.
