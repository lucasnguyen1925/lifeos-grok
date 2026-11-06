# Nhật ký thay đổi

Mỗi bản ghi rõ **Tiko phải làm gì** khi cập nhật (skill `lifeos-cap-nhat`).

## 0.6.0 — Việc nhanh tính đúng giờ + LifeOS làm hộ (03/11)

Chuyện xảy ra: Khôi thấy kế hoạch xếp quá nhiều thời gian cho việc nhanh (check mail, phản hồi mail…) và muốn bot **tự giải quyết những việc nó làm được, Khôi chỉ duyệt**; việc khó thì Khôi làm. Về thời gian: mỗi mail/tin tính 10' (đóng tiền, đăng ký 15'), cả ô "Việc nhanh" tới 45', nghỉ 10' sau mỗi ô, và mail bị bot quét ghi thành `task` (30') hoặc `deadline` (90') thì thành ô dài riêng. Quyết định: SPEC §5g (M1–M5, H1–H14). **Giao diện mới (ảnh từ khuôn) để bản sau.**

**Tiko làm:**
1. `git pull`, chạy test (phải OK, **110 bài**).
2. Chép đè skill vào `/home/box/agent-data/workflows/`: `lifeos-noi-quy`, `lifeos-bao-cao`, `lifeos-chong-tri-hoan`, và chép **mới** `lifeos-lam-ho` (chạy lại vòng chép skill ở CAI_DAT bước 3 là đủ; phải thấy 8 skill).
3. Gửi tin ưu tiên cho **cả 5 bot** LifeOS, Học tập, Công ty, Cá nhân, Zalo (Tiko không đổi hướng dẫn): "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md (đọc toàn văn, thay hướng dẫn cũ)."
4. Thêm hai mục mới vào `/workspace/lifeos/config.toml`, chép từ `config/config.example.toml` (không ghi đè gì Khôi đã điền): `[estimate]` (bảng thời lượng việc nhanh, không cần chỉnh) và `[lamho]` (**giữ nguyên `bat = []` và `toi_da_thanh_toan = 0`**: chưa bật loại việc nào).
5. Không có routine mới; LifeOS không đổi giờ routine nào.
6. Kiểm ngay (chỉ đọc), ghi vào `state/cai_dat.md`:
   - `python3 -m lifeos validate data/<mảng>.json` cho 3 mảng vẫn `ok: true` (có thể có `warnings`, không phải lỗi: chuyển cho bot mảng sửa theo thông báo).
   - `python3 -m lifeos plan suggest --for mai`: ô "Việc nhanh" ngắn lại (mỗi cụm ≤ 30', nghỉ 5' sau cụm).
   - `python3 -m lifeos lamho list` in `{"items": []}`; `lamho add --loai gui_mail …` báo "chưa bật" (đúng, vì công tắc đang tắt).
7. **Thử "làm hộ", từng loại một** theo CAI_DAT bước 7 (mục 13–19) và SPEC §15 mục 21–27. Việc thử phải diễn ra **trong khung chat LifeOS với lời duyệt của chính Khôi** (Grok không tính lời duyệt do bot khác chuyển lại). Chỉ dùng dữ liệu thử (mail gửi chính Khôi, sự kiện "[thử LifeOS]"). Loại nào qua thử thì thêm vào `[lamho] bat`. **Nhóm 3 (nộp bài, làm quiz, đăng ký môn/thi, thanh toán, xóa) không có cách thử vô hại**: chỉ "chạy khô" tới sát nút cuối với form đăng ký/khảo sát (không thử với quiz); bật từng loại khi có việc thật và Khôi đồng ý đúng loại đó. `toi_da_thanh_toan` do **Khôi tự đặt**, Tiko không đặt hộ.
8. Sau tuần đầu: gửi Khôi số ô "Việc nhanh" và thời lượng trong kế hoạch, và `python3 -m lifeos lamho tong --days 7`.

**Khôi làm:** nhắn Tiko "Cập nhật LifeOS lên bản 0.6.0, làm theo CHANGELOG". Khi LifeOS đưa phiếu V: trả lời "làm V1", "bỏ V2", "sửa V1: …" (im lặng = không làm gì). Tự đặt `toi_da_thanh_toan` nếu muốn cho bot thanh toán. Đồng ý từng loại ở nhóm 3 trước khi Tiko bật. Bấm duyệt thẻ Grok nếu hiện.

Thay đổi:
- **Thời lượng việc nhanh (M1–M5)**: bảng `[estimate]` (đọc mail/thông báo 3' · trả lời mail/tin 7' · đóng tiền, đăng ký 10' · khảo sát/form 10'); mỗi cụm ≤ 30' (cũ 45'), làm tròn lên 5', nghỉ 5' sau cụm, xếp vào khe NGẮN nhất đủ chỗ; cụm dư vào cụm sau nếu còn giờ, không thì để sáng mai. Script **bỏ `est_minutes`** của `email`/`message`/`notice`/`payment`/`registration`; `validate` có thêm `warnings` (không phải lỗi) khi `task`/`deadline` đến từ nguồn mail/Zalo hoặc khi ghi `est_minutes` cho mail/tin. Việc đã có phiếu V không xếp giờ cho Khôi. `lifeos/planner.py`, `lifeos/schema.py`.
- **Làm hộ**: `lifeos/lamho.py` + lệnh `lamho add|list|show|approve|start|result|edit|drop|tick|report|tong`. 15 loại việc / 3 nhóm, mỗi loại một công tắc `[lamho] bat` (mặc định tắt); `start` là cổng kiểm tra (đã duyệt đúng bản, loại đang bật, còn hạn, thanh toán ≤ `toi_da_thanh_toan` và mặc định 0 = không cho, xóa chỉ vào thùng rác/lưu trữ, người nhận mail/tin phải có nguồn); sửa phiếu là mất duyệt; tiền/nộp bài/xóa không tự thử lại (phiếu mới + duyệt mới); nhóm 3 báo `ok` phải kèm bằng chứng; tối đa 5 phiếu mỗi tin; hỏi 2 lần mà Khôi im lặng thì hết hạn; phiếu có hạn ≤ 3h chưa duyệt → nhắc Reminder + báo thức, không tự làm. State `state/lamho.json`, sổ `log/lamho.jsonl`.
- **Số liệu**: sổ ngày có `lamho`; chỉ số tuần `H_lamho_viec`, `H_lamho_phut` (Page, bảng so tuần, thêm một ô trong dashboard hiện tại, không đổi thiết kế).
- **P4 sửa**: "Mọi việc gửi đi/làm thay phải có phiếu Khôi duyệt" (SPEC §2, §12, rủi ro §14). Khôi chấp nhận rủi ro nhóm 3 và cho biết đang thí điểm có phép của trường (không kiểm chứng ở repo).
- Hướng dẫn: skill mới `lifeos-lam-ho`; sửa `lifeos-noi-quy` (mục 2, 3, 4), `lifeos-bao-cao` (mục "Phiếu làm hộ"), `lifeos-chong-tri-hoan` (R1, R5); `bots/lifeos.md`, `bots/hoctap.md`, `bots/congty.md`, `bots/canhan.md`, `bots/zalo.md`, `bots/tiko.md`; `docs/DINH_DANG_DU_LIEU.md`; `config/config.example.toml`; `CAI_DAT.md` bước 3 và 7; `docs/NEN_TANG_GROK.md` (kết quả thử 02–03/11).
- Test: `tests/test_lamho.py` (28 bài mới).

Chưa kiểm chứng trên máy Grok: **toàn bộ phần làm hộ thật** (gửi mail, điền form, nộp, thanh toán… SPEC §15 mục 21–27). Đã thử 03/11: LifeOS vào được BKeL và mail trường bằng phiên dùng chung (MyBK hết phiên, mail công ty bị Google hỏi xác minh). Chưa làm: giao diện mới (khuôn HTML, ảnh, Page).

## 0.5.0 — Lịch tổng: hết xếp đè giờ học + bớt tốn credit (02/11)

Chuyện xảy ra: tuần đầu chạy thật, kế hoạch tuần có gym 6:00–8:00 đè lớp 7:00, chạy sáng đè buổi thí nghiệm, văn phòng đè một buổi thí nghiệm — LifeOS không báo trùng gì (giờ gym đóng cứng; dò trùng không tính thứ LifeOS tự xếp; LifeOS sửa tay file kế hoạch nên bỏ qua mọi kiểm tra). Kèm "⏰ Dậy 23:00" và hạn "00:00 Thứ 6" dễ đọc nhầm. Đo credit: LifeOS dùng nhiều nhất. Quyết định: SPEC §5f (L1–L9, C1–C3).

**Tiko làm:**
1. `git pull`, chạy test (phải OK, 82 bài).
2. Chép đè 4 skill vào `/home/box/agent-data/workflows/`: `lifeos-bao-cao`, `lifeos-tri-nho`, `lifeos-chong-tri-hoan`, `lifeos-noi-quy`.
3. Gửi tin ưu tiên cho **LifeOS** và **Học tập** (4 bot còn lại không đổi): "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md (đọc toàn văn, thay hướng dẫn cũ)."
4. **LifeOS đổi nội dung 3 routine của chính nó** (07:00, 22:00, 23:00) theo bảng "Routine của bạn" trong `bots/lifeos.md` (giờ giữ nguyên, chỉ đổi câu lệnh: chạy `plan pending` trước, không có việc thì dừng). Khôi bấm duyệt thẻ nếu có. Các routine khác giữ nguyên.
5. Thêm khóa mới `soft_event_minutes = 30` vào mục `[schedule]` của `/workspace/lifeos/config.toml` (không bắt buộc — mặc định cũng là 30). Không đổi gì khác, không ghi đè giá trị Khôi đã điền.
6. **Kiểm lại tuần 2–8/11 bằng lịch tổng — Tiko KHÔNG tự sửa kế hoạch, KHÔNG chạy lại `week propose`** (sẽ đè kế hoạch tuần đang dùng):
   ```bash
   cd /workspace/lifeos-grok
   python3 -m lifeos digest
   python3 -m lifeos lichtong check --date 2026-11-02 --days 7
   ```
   Gửi **nguyên kết quả** cho LifeOS (tin ưu tiên). LifeOS báo Khôi từng chỗ trùng mức `cao` (gym/chạy/văn phòng đè lớp, thi, sự kiện), hỏi dời/bỏ, rồi sửa bằng `week train <ngày> --type gym|run --label "…"` hoặc `week set <ngày> --training none` và sửa sự kiện tương ứng trên lịch "LifeOS" (lấy id từ `calmap get train:<ngày>`). Tuần này Khôi đã tập PPL: LifeOS dùng `week train` đặt lại cho đúng, **không** sửa tay `state/week.json`.
7. **Page:** LifeOS chạy `python3 -m lifeos page` và `python3 -m lifeos brain page` → đăng Page "LifeOS" và Page "Trí nhớ" (lần đầu `changed: true`; Page Trí nhớ không còn mục "Toàn bộ sổ" — bình thường) → rồi chạy `python3 -m lifeos page --mark` và `python3 -m lifeos brain page --mark`.
8. Thử (chỉ đọc, không ghi lịch), ghi kết quả vào `state/cai_dat.md`:
   - `python3 -m lifeos lichtong show --date 2026-11-04 --days 1` in đúng lịch ngày đó (gồm Văn phòng, buổi tập, ô 📝 nếu có).
   - `python3 -m lifeos lichtong try --start 2026-11-04T06:30 --end 2026-11-04T07:30 --title "Thử"` báo đè đúng buổi tập/lớp nếu có.
   - `python3 -m lifeos plan pending --for mai` in `need_confirm` / `week_need_confirm`.
   - Khôi nhắn LifeOS "tuần này nghỉ chạy, tập PPL" (hoặc một yêu cầu đổi tập tương tự) → LifeOS phải dùng `week train` (không sửa tay file), báo `day_conflicts`.
   - Bot Học tập quét lần kế tiếp: bài kiểm tra trên lớp có `start` có giờ; `validate` OK.
9. Sau 2–3 ngày thường: nhìn trang **Mức sử dụng**, gửi Khôi % mỗi bot mỗi ngày (ghi chú: ngày tính theo UTC) để chốt đợt cắt credit tiếp theo.

**Khôi làm:** nhắn Tiko "Cập nhật LifeOS lên bản 0.5.0, làm theo CHANGELOG". Trả lời LifeOS khi nó hỏi dời/bỏ buổi tập trùng giờ học. Bấm duyệt thẻ routine nếu hiện. Muốn soát sổ nhớ → nhắn LifeOS "xem toàn bộ sổ".

Thay đổi:
- **Lịch tổng** `lifeos/lichtong.py` + lệnh `lichtong show|check|try`: gom mọi lịch + văn phòng + buổi tập + ô 📝, tìm chỗ trùng (mức `cao` / `luu-y`), đệm ~30' di chuyển quanh lớp/thi. `digest.json` có thêm `conflicts_lifeos` (3 ngày tới).
- **Gym né lịch**: sáng vướng → dời tối cùng ngày, tối kín → bỏ (có lý do trong `training_note`); chạy cũng đệm di chuyển; không chồng văn phòng. Gym tối không tính "ngày gym sáng" (giờ dậy, báo thức, giờ ngủ).
- **Văn phòng** né mọi sự kiện có giờ của trường (không chỉ buổi học); sự kiện cá nhân > 30' đè văn phòng → mục `luu-y` để Khôi quyết.
- **Chốt có kiểm tra**: `week confirm` / `plan confirm` từ chối khi còn trùng mức cao (mã thoát 1; `--allow-conflicts` khi Khôi nói giữ nguyên); tự áp dụng lúc im lặng thì bỏ buổi tập/ô đang đè (`dropped`). `plan edit --at` từ chối giờ đè lịch (`--force`). `week set --training` báo `day_conflicts`; lệnh mới `week train` (đổi loại buổi tập theo ngày, tự xếp giờ).
- **Dậy 23:00**: giờ dậy chỉ tính mục có giờ cụ thể; `validate` từ chối `class`/`exam` có `start` chỉ ngày. Hạn 00:00 hiện "hết ngày Thứ 5 (00:00 Thứ 6)"; kế hoạch ngày không xếp việc đã quá hạn kiểu này.
- **Dashboard**: khối "Lịch tổng tuần này" (viền đỏ = trùng) + danh sách ⚠️ trong phần Tuần này của Page.
- **Tiết kiệm credit**: Page "Trí nhớ" hằng đêm bỏ mục "Toàn bộ sổ" (`brain page --full` khi Khôi cần); `page` / `brain page` báo `changed`, bot chỉ đăng khi đổi và ở 05:30 / 21:00 / Khôi "ok" (`--mark` sau khi đăng); lệnh `plan pending` cho 3 routine kiểm tra (không đọc hồ sơ nếu không có việc).
- Hướng dẫn: `bots/lifeos.md` (routine, lệnh mới, cấm sửa tay `state/`), `bots/hoctap.md` (kiểm tra trên lớp phải có giờ), skill `lifeos-bao-cao`, `lifeos-tri-nho`, `lifeos-chong-tri-hoan`, `lifeos-noi-quy` (mục 1: kế hoạch/lịch chỉ đổi qua lệnh). `docs/NEN_TANG_GROK.md`: số liệu credit, cổng BKeL cho app điện thoại.
- Test: `tests/test_lichtong.py` (35 bài mới) + sửa `tests/test_brain.py` cho Page rút gọn.

Chưa kiểm chứng trên máy Grok: xem SPEC §15 mục 17–20. Chưa làm: lấy BKeL qua cổng app (SPEC §5f), bớt lần quét nhẹ bot Cá nhân.

## 0.4.0 — Bản đồ phân công: LifeOS biết ai lo mảng nào để giao đúng (31/10)

Chuyện xảy ra: hỏi việc nhóm thí nghiệm, LifeOS tự lục Zalo rồi Drive cá nhân, Khôi phải nhắc 2 lần mới chuyển cho Học tập. Quyết định: SPEC §5e (G1–G5).

**Tiko làm:**
1. `git pull`, chạy test (phải OK, 47 bài).
2. Chép đè skill `lifeos-noi-quy` vào `/home/box/agent-data/workflows/`.
3. **Ghi phần Kết nối của bản đồ** theo đúng thực tế (chỉ tên gọi, không ghi địa chỉ), ví dụ:
   ```bash
   cd /workspace/lifeos-grok
   python3 -m lifeos bando ket-noi "Gmail cá nhân" --trang-thai ok --loai Gmail
   python3 -m lifeos bando ket-noi "Mail trường" --trang-thai ok --loai Gmail
   python3 -m lifeos bando ket-noi "Lịch cá nhân" --trang-thai ok --loai Lịch
   python3 -m lifeos bando ket-noi "Lịch trường" --trang-thai ok --loai Lịch
   python3 -m lifeos bando ket-noi "Drive cá nhân" --trang-thai ok --loai Drive
   python3 -m lifeos bando ket-noi "Drive trường" --trang-thai ok --loai Drive
   python3 -m lifeos bando ket-noi "Sheets" --trang-thai chua_cai --ghi-chu "đọc sheet được qua Drive, chưa sửa ô được"
   python3 -m lifeos bando ket-noi "Mail công ty" --trang-thai <ok|het_phien> --loai "Trình duyệt"
   python3 -m lifeos bando show
   ```
4. Gửi tin ưu tiên cho **cả 6 bot** (Tiko tự áp dụng): "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md (đọc toàn văn, thay hướng dẫn cũ)." Không routine cố định nào phải đổi.
5. Thử rồi ghi vào `state/cai_dat.md`: Khôi hỏi LifeOS một việc của trường (ví dụ "môn X tuần này có tài liệu mới không?") → LifeOS phải **giao ngay** cho Học tập (không tự lục), báo Khôi một dòng; Học tập trả lời LifeOS kèm nguồn; LifeOS báo lại. Ghi luôn: LifeOS có tạo được routine "chạy 1 lần sau 10 phút" không, có hiện thẻ duyệt không.

**Khôi làm:** nhắn Tiko cập nhật. Nếu LifeOS hỏi bấm thẻ tạo routine kiểm tra 10 phút thì bấm duyệt.

Thay đổi:
- `lifeos/bando.py` + lệnh `bando` (show, ket-noi, xoa-ket-noi, ai) và `giao` (add, done, list, check). Bản đồ phân công + kết nối + việc đang chờ bot khác được in trong `brain core` và Page Trí nhớ.
- Nội quy mục 11 (mới): bản đồ phân công, cách nhận việc LifeOS giao. LifeOS: mục "Giao việc theo bản đồ phân công". Tiko: giữ phần Kết nối. 4 bot: mục "Nhận việc LifeOS giao".
- `docs/NEN_TANG_GROK.md`: kết nối chung cho cả tài khoản, Drive đọc được Sheet, Drive trường đã kết nối.

## 0.3.2 — không bịa dữ kiện, bản nháp ghi nguồn, báo mail bị trả về (31/10)

Chuyện xảy ra: mail gửi thầy bị trả về vì địa chỉ không dùng được, và Khôi duyệt gửi mà không biết địa chỉ lấy từ đâu. Quyết định: SPEC §5d (N1–N4).

**Tiko làm:**
1. `git pull`, chạy test (phải OK, 42 bài).
2. Chép đè skill `lifeos-noi-quy`, `lifeos-tri-nho`, `lifeos-bao-cao`, `lifeos-chong-tri-hoan` vào `/home/box/agent-data/workflows/`.
3. Thêm khóa `bounce_keywords` vào mục `[rules]` của `/workspace/lifeos/config.toml` (chép từ `config/config.example.toml`, giữ các khóa khác).
4. Gửi tin ưu tiên cho **LifeOS, Học tập, Công ty, Cá nhân** (Tiko tự áp dụng): "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md (đọc toàn văn, thay hướng dẫn cũ)." Zalo không đổi. **Không routine nào phải đổi.**
5. Sao lưu đêm từ nay: tải bản mới lên Drive **trước**, thấy lên đủ rồi mới bỏ file cũ cùng tên vào thùng rác (mỗi tên chỉ còn 1 file). Dọn luôn các file trùng tên đang có.
6. Thử rồi ghi vào `state/cai_dat.md`: nhắn LifeOS "soạn thử một mail cho <một người có trong sổ nhớ>, chưa gửi" → bản nháp phải có dòng `📤 Gửi tới: … — nguồn: …`. Nhắn LifeOS "soạn thử mail cho bạn thử nghiệm Z" (không có trong sổ) → LifeOS phải nói không tìm thấy địa chỉ, không được tự nghĩ ra.

**Khôi làm:** không có gì thêm ngoài việc nhắn Tiko cập nhật. Nếu thấy bot nào đưa ra địa chỉ, số điện thoại hay phòng mà không nói được lấy từ đâu thì chụp lại gửi Claude.

Thay đổi:
- Nội quy mục 10 (mới): không bịa dữ kiện. LifeOS + R6: bản nháp có dòng `📤 Gửi tới … — nguồn …`, người nhận không có nguồn thì không đưa vào.
- Sổ nhớ: trường `source` (`brain add/edit --source`), hiện trong `search`/`show`; đề xuất được duyệt mang theo nguồn. Địa chỉ liên lạc lưu kèm nguồn; số điện thoại cá nhân chỉ lưu khi "nhớ giúp".
- `lifeos/urgency.py`: thư báo mail bị trả về (`rules.bounce_keywords`) → 🔴 "mail bạn gửi bị trả về — người nhận CHƯA nhận được" trong 72 giờ. Học tập, Công ty, Cá nhân ghi thư trả về thành `notice` "Mail bị trả về: …"; LifeOS báo ngay và đánh dấu địa chỉ trong sổ.
- Sao lưu: tải mới trước, bỏ cũ sau (Drive không ghi đè được file `.json`).

## 0.3.1 — sửa hướng dẫn cho khớp cách routine chạy thật (31/10)

Thử thật 31/10: routine **không nhắn được bot khác** (kể cả tự nhắn cho chính mình), nhưng khi có việc chuyển lại thì **chat chính của bot đó tự dậy và làm**. Báo 🔴 và tự đăng nhập lại vẫn chạy được là nhờ bot tự xoay xở theo đường này; bản này ghi đúng cách làm vào hướng dẫn. Không đổi quyết định nào.

**Tiko làm:**
1. Đang ở bản 0.2.0 → làm hết các bước của **0.3.0** trước (bên dưới), **bỏ qua bước 5** của 0.3.0 (đã thử: chat chính đọc được chat), rồi làm tiếp các bước này.
2. Chép đè skill `lifeos-noi-quy`, `lifeos-dang-nhap-lai`, `lifeos-tri-nho` vào `/home/box/agent-data/workflows/`.
3. Gửi tin ưu tiên cho **LifeOS, Học tập, Công ty, Cá nhân** (Tiko tự áp dụng): "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md (đọc toàn văn, thay hướng dẫn cũ)." Bot Zalo không đổi.
4. **LifeOS**: sửa nội dung routine **Soát chat** 20:40 đúng bảng mới ("Không tự làm gì. Chuyển lại cho chat chính đúng câu: …"). Không routine nào khác phải đổi.
5. Theo dõi rồi ghi vào `state/cai_dat.md`: lần đầu Học tập hoặc Cá nhân có việc 🔴 → LifeOS có nhận không; lần đầu có bot lỡ lần chạy → Tiko có nhắc được không; tối đầu tiên 20:40 → LifeOS soát chat xong lúc mấy giờ (trước 21:00 không).

**Khôi làm:** không có gì thêm. Chưa cập nhật 0.3.0 thì nhắn Tiko một lần "Cập nhật LifeOS lên bản 0.3.1, làm theo CHANGELOG" và làm phần "Khôi làm" của 0.3.0.

Thay đổi:
- Nội quy mục 9 (mới): trong routine, việc cần nhắn bot khác / đăng nhập bằng Vault / đọc chat → chuyển lại cho chat chính, ghi rõ từng câu việc cần làm.
- Báo 🔴 (nội quy mục 6, 3 bot mảng), tự đăng nhập lại (skill `lifeos-dang-nhap-lai` mục A), Tiko kiểm tra sức khỏe, routine 20:40 của LifeOS: đổi "gửi tin ưu tiên" thành "chuyển lại cho chat chính".
- `docs/NEN_TANG_GROK.md`, SPEC §3, §8, §9, §15: ghi các điều đã kiểm chứng 31/10.

## 0.3.0 — Sổ nhớ: cả đội cùng nhớ chuyện của Khôi (31/10)

**Tiko làm:**
1. `git pull`, chạy test như thường lệ (skill `lifeos-cap-nhat`). Kiểm tra nhanh: `python3 -m lifeos brain core` phải in ra "(Sổ nhớ còn trống.)".
2. Chép skill **mới** `lifeos-tri-nho` và chép đè `lifeos-noi-quy`, `lifeos-bao-cao` vào `/home/box/agent-data/workflows/`.
3. Thêm vào `/workspace/lifeos/config.toml` (giữ giá trị cũ): `journal_days = 90` trong `[retention]`, và cả mục `[brain]` lấy từ `config/config.example.toml`.
4. Gửi tin ưu tiên cho **từng bot** (LifeOS, Học tập, Công ty, Cá nhân, Zalo; Tiko tự áp dụng): "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md (đọc toàn văn, thay hướng dẫn cũ)."
   - **LifeOS**: tạo thêm routine **Soát chat** `40 20 * * *` (exact), đúng nội dung trong bảng Routine.
   - **Tiko**: sửa nội dung routine **Dọn dẹp đêm** thành "Dọn dẹp và sao lưu theo hướng dẫn Tiko, mục Dọn dẹp đêm." (giờ giữ nguyên 02:15).
   - Học tập, Công ty, Cá nhân, Zalo: chỉ đổi hướng dẫn, **không** đổi routine.
5. Xem lại lần thử ngày 31/10 "routine nhắn ưu tiên cho chính Tiko rồi đọc chat". **Không đọc được chat** → nhắn LifeOS xóa routine Soát chat 20:40 và báo Khôi "bước soát chat cuối ngày không chạy được, LifeOS chỉ ghi trong lúc chat" (SPEC §5c T18).
6. **Chuyển trí nhớ cũ của Tiko** vào sổ theo skill `lifeos-tri-nho` mục 11. Chuyện riêng thì hỏi Khôi trong khung chat Tiko.
7. Nhắn Khôi phần **"Khôi làm"** bên dưới. LifeOS **không** làm theo lời nhờ chuyển qua Tiko, nên Khôi phải nhắn thẳng LifeOS.
8. Chạy thử CAI_DAT bước 7 các mục 10–12, ghi kết quả vào `state/cai_dat.md`. Sáng hôm sau: xem trên Drive "LifeOS · Sao lưu" có file `lifeos_saoluu_<thứ>.json` (định dạng `.json`, không phải Google Docs).

**Khôi làm:**
- Nhắn thẳng **LifeOS**: *"Chuyển trí nhớ cũ vào sổ theo skill lifeos-tri-nho mục 11, rồi tạo Page 'LifeOS · Trí nhớ' từ dashboard/tri_nho.md và gửi mình link."* → ghim Page đó.
- Trả lời nếu LifeOS/Tiko hỏi "có N chuyện riêng, muốn ghi cái nào?".
- Bấm duyệt nếu có thẻ sửa routine hiện ra (LifeOS 20:40, Tiko 02:15).

Thay đổi:
- `lifeos/brain.py` + lệnh `brain`: sổ nhớ chung. Gồm hồ sơ ngắn 6 mục ~40 dòng (`core`), tìm không dấu bằng SQLite FTS5 (`search`), trang chi tiết (`show`), ghi/sửa/thay thế giữ lịch sử (`add`, `edit`, `end`, `--replaces`), `forget` (xóa cả lịch sử, chỉ giữ mã + giờ). Thêm `pin`/`unpin`, đề xuất của bot quét nguồn (`propose`, `accept`, `reject`: 3 mỗi tối, hỏi lại 1 lần rồi bỏ), khối 🧠 cho báo cáo tối (`report`, cuối tháng hỏi điều > 6 tháng), nhật ký chuyện đã nói (`journal`), kho "lưu cái này" (`kho`), gộp trùng (`dupes`, `merge`), Page "LifeOS · Trí nhớ" (`page`), sao lưu 7 bản theo thứ (`backup`, `restore`).
- `nightly` tự dọn "Đang dở" quá hạn và dựng lại `dashboard/tri_nho.md`. `cleanup` xóa nhật ký quá 90 ngày. Báo cáo tháng có thêm mục "Chuyện đã nói trong tháng".
- Skill mới `lifeos-tri-nho`. Nội quy: mọi bot đọc hồ sơ đầu mỗi lượt và mỗi routine; ngoại lệ "lời nhờ quên từ LifeOS". Báo cáo tối có khối 🧠; Chủ nhật gộp điều trùng.
- Hướng dẫn 6 bot; `docs/NEN_TANG_GROK.md` ghi các điều đã kiểm chứng ngày 31/10 (trí nhớ Grok, khung chat, Drive, routine, Page).
- Quyết định: SPEC §5c (T1–T19).

## 0.2.0 — tính năng Kế hoạch + báo cáo mới (31/10)

**Tiko làm:**
1. Chép đè skill `lifeos-bao-cao` và `lifeos-chong-tri-hoan` vào `/home/box/agent-data/workflows/`.
2. Thêm các khóa mới từ `config/config.example.toml` vào `/workspace/lifeos/config.toml` (giữ giá trị Khôi đã điền): `[day]`, `[capacity]`, `[priority]`, `[office]`, `[training]`, `[exam_prep]`, `wake_before_first_class`; hỏi Khôi tên/địa điểm buổi chạy nhóm để điền `training.group_run_keyword`; đổi `[[schedule.protected]]` ăn trưa/ăn tối cũ → xóa (giờ ăn giờ nằm trong `[day]`); cập nhật `[health.expected]` và `[scan]` theo giờ mới.
3. Gửi tin ưu tiên cho **từng bot** (LifeOS, Học tập, Công ty, Cá nhân, Zalo, và Tiko tự áp dụng): "Cập nhật hướng dẫn theo /workspace/lifeos-grok/bots/<bot>.md, sửa routine đúng bảng Routine mới (exact)." Giờ mới: Zalo 04:40 · bot mảng 05:00 · Tiko 05:20 · LifeOS báo cáo 05:30, 07:00, CN 20:00 (mới). Khôi phải bấm duyệt thẻ sửa routine.
4. Nhắc Khôi: Grok Page "LifeOS" (gộp trang Hiệu suất cũ) — LifeOS tạo một lần, ghim lại.

Thay đổi:
- `lifeos/daymodel.py`: mô hình một ngày (dậy/ngủ, văn phòng, tập, giờ ăn, giới hạn giờ).
- `lifeos/week.py` + lệnh `week`: kế hoạch tuần (văn phòng quanh lịch học/thi, buổi tập theo giáo án, chạy nhóm thay buổi chạy, việc lớn, trùng lịch).
- `lifeos/planner.py`: thang ưu tiên 6 bậc, giới hạn giờ mỗi ngày, buổi ôn thi tự chia, việc công ty để trong giờ văn phòng, dòng thời gian cả ngày. Lệnh `plan suggest`, `plan timeline`, `plan edit`.
- Lệnh `calmap` (nhớ id sự kiện bot tạo), `page` (Grok Page: Hôm nay · Tuần này · Hiệu suất).
- `remind-at` và `free` tính cả văn phòng, buổi tập, giờ ăn.
- Mẫu báo cáo sáng/tối/kế hoạch tuần mới (skill `lifeos-bao-cao`), R4/R4c (skill `lifeos-chong-tri-hoan`).
- Quyết định: SPEC §5b.

## 0.1.2 — cho phép tự giải CAPTCHA (31/10)

**Tiko làm:** chép đè skill `lifeos-dang-nhap-lai` vào `/home/box/agent-data/workflows/`.

- Zalo và SSO HCMUT: bot được tự giải CAPTCHA tối đa 1 lần mỗi lượt (Khôi cho phép, chấp nhận rủi ro bị khóa). Google công ty vẫn dừng và nhờ Khôi.
- Mỗi lần gặp CAPTCHA ghi vào nhịp tim để theo dõi tần suất.

## 0.1.1 — sửa sau lần chạy đầu tiên (31/10)

**Tiko làm:** chép đè 2 skill `lifeos-dang-nhap-lai` và `lifeos-zalo` vào `/home/box/agent-data/workflows/`. Không phải sửa hướng dẫn bot hay routine.

- Zalo: trang đăng nhập mặc định chỉ hiện QR — hướng dẫn bot vào menu ☰ → "Đăng nhập với mật khẩu".
- Google công ty: "Verify it's you" chỉ có nút Next là tự làm được; chỉ dừng khi đòi điện thoại/mã.
- Đăng nhập lại xong phải quét lại ngay, kịp trước giờ báo cáo.
- Ghi IP trình duyệt (đo trong trình duyệt, không đo bằng terminal) mỗi lần đăng nhập lại.
- CAI_DAT bước 4: Tiko tự tạo được bot Zalo.

## 0.1.0 — bản đầu tiên

Cài mới theo [CAI_DAT.md](CAI_DAT.md) (không phải cập nhật).

- 6 bot: LifeOS, Tiko, Học tập, Công ty, Cá nhân, **Zalo (mới)**.
- 6 skill chung: `lifeos-noi-quy`, `lifeos-dang-nhap-lai`, `lifeos-zalo`, `lifeos-bao-cao`, `lifeos-chong-tri-hoan`, `lifeos-cap-nhat`.
- Dữ liệu mảng chuyển từ `*.md` tự do sang `data/*.json` chuẩn; script tính độ gấp (4 mức), trùng lịch, thứ/ngày, khung trống, giờ đặt nhắc.
- Nhịp tim + kiểm tra sức khỏe; tự đăng nhập lại qua vòng routine → bot chính → Vault.
- Chốt sổ ngày/tuần/tháng, dashboard (HTML/SVG, ảnh PNG, nội dung cho Grok Page), dọn dữ liệu (ngày/tuần 90 ngày, Zalo thô 7 ngày, tháng giữ lâu dài).
- Bộ quy tắc chống trì hoãn R1–R10.
