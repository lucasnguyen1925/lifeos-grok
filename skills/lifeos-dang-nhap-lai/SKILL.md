---
name: lifeos-dang-nhap-lai
description: Quy trình tự đăng nhập lại khi một nguồn LifeOS (SSO HCMUT/MyBK/BKeL, Google công ty, Zalo) đòi đăng nhập trong lúc chạy routine. Dùng khi gặp trang đăng nhập, phiên hết hạn, hoặc khi nhận tin "đăng nhập lại <nguồn>".
---

# Tự đăng nhập lại

**Vì sao cần vòng này:** khi chạy theo routine, bot KHÔNG điền được login từ Vault. Ở chat chính (lượt chat thường) thì được, không cần hỏi Khôi. Nên routine **chuyển việc lại cho chat chính** của chính bot đó — chat chính tự dậy và làm ngay (đã chạy trọn ở bot Công ty ngày 31/10).

## A. Trong routine — gặp trang đăng nhập

1. **Không thử đăng nhập trong routine.** Không thử nhiều lần.
2. Ghi nguồn đó là `needs_login` trong file mảng (giữ lại các việc cũ của nguồn đó), quét tiếp các nguồn khác, chạy `validate`, `digest`, `status … --source <nguồn>=needs_login:"<mô tả>"`.
3. Kết thúc lần chạy bằng việc **chuyển lại cho chat chính** (routine không tự nhắn được, kể cả cho chính mình — nội quy mục 9):
   `"Chuyển cho chat chính: đăng nhập lại <nguồn> bằng Vault rồi quét lại riêng phần <nguồn> (skill lifeos-dang-nhap-lai, mục B)."`
   Có việc 🔴 mới cần báo LifeOS thì ghi chung vào lần chuyển này.

## B. Ở chat chính — routine chuyển lại, hoặc nhận tin "đăng nhập lại <nguồn>"

1. Mở trang đăng nhập của nguồn, dùng login đã lưu trong Vault.
2. Riêng **MyBK**: nếu trang SSO báo đã đăng nhập nhưng MyBK vẫn coi là chưa đăng nhập → bấm **"Tài khoản HCMUT"** rồi đăng nhập lại. Link MyBK cũ dạng `/app/sinh-vien/...` bị đá về trang đăng nhập → vào từ trang chủ MyBK rồi bấm menu.
3. Riêng **Zalo** (chỉ bot Zalo): trang `id.zalo.me` mặc định **chỉ hiện mã QR — đừng dừng ở đó**. Bấm menu **☰ ở góc phải → "Đăng nhập với mật khẩu"**, rồi điền login Zalo trong Vault.
4. Riêng **Google công ty**: trang **"Verify it's you" chỉ có nút Next** là bước xác nhận lại bình thường → bấm Next, đăng nhập SSO bằng Vault. Chỉ dừng khi Google đòi bấm trên điện thoại, nhập mã, hoặc chọn cách xác minh khác.
5. Tick **"Ghi nhớ đăng nhập"** nếu trang có.
6. Đăng nhập được → **quét lại ngay** phần của nguồn đó, cập nhật file mảng, `validate`, `digest`, `alerts`, `status … --source <nguồn>=ok`. Đang trước giờ báo cáo 06:00/21:00 thì phải xong bước này **trước giờ báo cáo**, để báo cáo không ghi nhầm là còn lỗi.
7. Ghi lại **IP trình duyệt** lúc đăng nhập (mở `https://ifconfig.co/json` trong **trình duyệt**, không đo bằng terminal) vào `--note` của lệnh `status`. Lần sau có lỗi thì so được.
8. **CAPTCHA — chỉ với Zalo và SSO HCMUT** (tài khoản cá nhân, Khôi đã cho phép ngày 31/10 và chấp nhận rủi ro bị khóa): được **tự giải tối đa 1 lần** mỗi lượt. Giải sai, CAPTCHA hiện lại, hoặc nền tảng không cho bot giải → dừng như mục 9. Ghi vào `--note` của `status` là đã gặp CAPTCHA và kết quả, để Tiko theo dõi tần suất.
9. **Dừng ngay và báo Tiko** (tin thường, không ưu tiên) nếu gặp bất kỳ thứ nào dưới đây — KHÔNG tìm cách vượt:
   - CAPTCHA ở **Google công ty** hoặc nguồn khác ngoài Zalo/SSO HCMUT; CAPTCHA đã thử 1 lần không qua
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
| SSO HCMUT | 1 lần mỗi lượt | Không CAPTCHA/OTP theo kiểm tra 30/10 — tự động được. Có CAPTCHA → tự giải 1 lần (mục 8) |
| Google công ty | 1 lần mỗi lượt | "Verify it's you" chỉ có Next → tự làm được (31/10). Đòi điện thoại/mã hoặc CAPTCHA → dừng, cần Khôi (tài khoản công ty, không tự giải CAPTCHA) |
| Zalo | 1 lần mỗi lượt quét, chỉ bot Zalo | Đăng nhập bằng mật khẩu qua menu ☰ (bước 3). CAPTCHA → tự giải 1 lần (mục 8). Cảnh báo bất thường, đòi xác minh qua điện thoại, tài khoản bị khóa → dừng ngay. Zalo bị khóa phiền hơn nhiều so với thiếu dữ liệu một buổi |
