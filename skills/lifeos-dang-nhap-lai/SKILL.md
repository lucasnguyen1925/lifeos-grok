---
name: lifeos-dang-nhap-lai
description: Quy trình tự đăng nhập lại khi một nguồn LifeOS (SSO HCMUT/MyBK/BKeL, Google công ty, Zalo) đòi đăng nhập trong lúc chạy routine. Dùng khi gặp trang đăng nhập, phiên hết hạn, hoặc khi nhận tin "đăng nhập lại <nguồn>".
---

# Tự đăng nhập lại

**Vì sao cần vòng này:** khi chạy theo routine, bot KHÔNG điền được login từ Vault. Ở lượt chat thường thì được, không cần hỏi Khôi. Nên routine chuyển việc cho chính bot đó ở lượt chat thường.

## A. Trong routine — gặp trang đăng nhập

1. **Không thử đăng nhập trong routine.** Không thử nhiều lần.
2. Ghi nguồn đó là `needs_login` trong file mảng (giữ lại các việc cũ của nguồn đó), quét tiếp các nguồn khác, chạy `validate`, `digest`, `status … --source <nguồn>=needs_login:"<mô tả>"`.
3. Gửi **tin ưu tiên cho CHÍNH MÌNH**:
   `"Đăng nhập lại <nguồn> bằng Vault rồi quét lại riêng phần <nguồn> (skill lifeos-dang-nhap-lai, mục B)."`

## B. Ở lượt chat thường — nhận tin "đăng nhập lại <nguồn>"

1. Mở trang đăng nhập của nguồn, dùng login đã lưu trong Vault.
2. Riêng **MyBK**: nếu trang SSO báo đã đăng nhập nhưng MyBK vẫn coi là chưa đăng nhập → bấm **"Tài khoản HCMUT"** rồi đăng nhập lại. Link MyBK cũ dạng `/app/sinh-vien/...` bị đá về trang đăng nhập → vào từ trang chủ MyBK rồi bấm menu.
3. Tick **"Ghi nhớ đăng nhập"** nếu trang có.
4. Đăng nhập được → quét lại phần của nguồn đó, cập nhật file mảng, `validate`, `digest`, `alerts`, `status … --source <nguồn>=ok`.
5. **Dừng ngay và báo Tiko** (tin thường, không ưu tiên) nếu gặp bất kỳ thứ nào dưới đây — KHÔNG tìm cách vượt:
   - CAPTCHA
   - mã OTP / xác minh 2 bước / xác nhận trên điện thoại
   - cảnh báo đăng nhập bất thường, tài khoản bị khóa
   - Vault không có login cho nguồn này
   Tin cho Tiko: `"<nguồn> cần Khôi đăng nhập tay: <thấy gì>."` Ghi `status … --source <nguồn>=needs_login:"cần Khôi: <thấy gì>"`.

## C. Tiko — khi nhận báo "cần Khôi đăng nhập tay"

Nhắn Khôi MỘT tin ngắn, hướng dẫn 30 giây, ví dụ:

> 🔑 **MyBK cần bạn đăng nhập.** Mở khung chat bot **Học tập**, gõ `đăng nhập MyBK`. Bot mở trang, bạn bấm **Tiếp quản**, nhập mã, xong gõ `xong`.

Không nhắn lại cùng nội dung trong 12 giờ. Báo cáo của LifeOS sẽ nhắc tiếp ở mục 🔑.

## Giới hạn riêng từng nguồn

| Nguồn | Tối đa | Ghi chú |
|---|---|---|
| SSO HCMUT | 1 lần mỗi lượt | Không CAPTCHA/OTP theo kiểm tra 30/10 — tự động được |
| Google công ty | 1 lần mỗi lượt | Hỏi xác minh 2 bước → dừng, cần Khôi |
| Zalo | 1 lần mỗi lượt quét, chỉ bot Zalo | Có cảnh báo bất thường / đòi xác minh qua điện thoại → dừng ngay. Zalo bị khóa phiền hơn nhiều so với thiếu dữ liệu một buổi |
