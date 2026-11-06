"""Test việc nhanh tính đúng giờ (SPEC §5g M1-M5) và LifeOS làm hộ (lifeos/lamho.py, H1-H14)."""
from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path

from lifeos import digest, lamho, planner
from lifeos.__main__ import main
from lifeos.common import load_config, parse_dt, path, read_json, read_jsonl, write_json
from lifeos.schema import validate_domain_file, warnings_domain_file

ROOT_DIR = Path(__file__).resolve().parent.parent
NOW = "2026-11-02T21:00+07:00"   # Thứ 2 tối, lên kế hoạch cho Thứ 3


def item(**kw):
    base = {"id": "x", "domain": "canhan", "source": "gmail", "kind": "email", "title": "Việc", "status": "open"}
    base.update(kw)
    return base


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(ROOT_DIR / "config" / "config.example.toml", self.tmp / "config.toml")
        self.env = {"LIFEOS_ROOT": str(self.tmp), "LIFEOS_NOW": NOW}
        self._old = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        self.cfg = load_config()
        self.t = parse_dt(NOW)

    def tearDown(self):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp)

    def write_items(self, items, domain="canhan"):
        data = {"bot": domain, "generated_at": "2026-11-02T20:30+07:00", "sources": {"gmail": {"status": "ok"}}, "items": items}
        write_json(self.tmp / "data" / f"{domain}.json", data)
        digest.build(t=self.t, cfg=self.cfg)

    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(args))
        return code, json.loads(buf.getvalue())


class Estimate(Base):
    """M1-M5: thời lượng việc nhanh."""

    def test_table_m1(self):
        m = lambda **kw: planner._minutes(item(**kw), self.cfg)
        self.assertEqual(m(kind="email"), 3)
        self.assertEqual(m(kind="notice"), 3)
        self.assertEqual(m(kind="email", needs_reply=True), 7)
        self.assertEqual(m(kind="message", needs_reply=True), 7)
        self.assertEqual(m(kind="message", mentions_khoi=True), 7)
        self.assertEqual(m(kind="notice", needs_reply=True), 3)
        self.assertEqual(m(kind="payment"), 10)
        self.assertEqual(m(kind="registration"), 10)
        self.assertEqual(m(kind="task", title="Điền khảo sát học phần"), 10)
        self.assertEqual(m(kind="task", title="Làm form góp ý"), 10)
        self.assertEqual(m(kind="task", title="Viết báo cáo"), 30)
        self.assertEqual(m(kind="deadline", title="Bài lớn"), 90)

    def test_bot_est_minutes_ignored_for_mail_but_not_for_quiz(self):
        self.assertEqual(planner._minutes(item(kind="email", est_minutes=60, needs_reply=True), self.cfg), 7)
        self.assertEqual(planner._minutes(item(kind="payment", est_minutes=60), self.cfg), 10)
        self.assertEqual(planner._minutes(item(kind="quiz", est_minutes=35), self.cfg), 35)
        self.assertEqual(planner._minutes(item(kind="task", title="Điền khảo sát", est_minutes=45), self.cfg), 45)

    def test_config_overrides_table(self):
        self.cfg["estimate"] = {"tra_loi": 5}
        self.assertEqual(planner._minutes(item(kind="email", needs_reply=True), self.cfg), 5)
        self.assertEqual(planner._minutes(item(kind="email"), self.cfg), 3, "khóa không ghi đè giữ mặc định")

    def test_example_config_has_estimate_and_lamho(self):
        self.assertEqual(self.cfg["estimate"]["cum_toi_da"], 30)
        self.assertEqual(self.cfg["lamho"]["bat"], [], "mặc định TẮT hết")
        self.assertEqual(self.cfg["lamho"]["toi_da_thanh_toan"], 0)

    def _quick_items(self, n, **kw):
        return [item(id=f"cn:m{i}", title=f"Mail {i}", needs_reply=True, received_at="2026-11-02T18:00+07:00", **kw)
                for i in range(n)]

    def test_quick_cluster_rounds_to_5_and_caps_at_30(self):
        self.write_items(self._quick_items(1))
        res = planner.suggest(date(2026, 11, 3), self.cfg, t=self.t)
        quick = [b for b in res["blocks"] if b["title"].startswith("Việc nhanh")]
        self.assertEqual(len(quick), 1)
        self.assertEqual(quick[0]["minutes"], 10, "7 phút làm tròn lên 10")

        self.write_items(self._quick_items(8))        # 8 × 7' = 56' → cụm 28' (4 mail) + cụm 28' (4 mail)
        res = planner.suggest(date(2026, 11, 3), self.cfg, t=self.t)
        quick = [b for b in res["blocks"] if b["title"].startswith("Việc nhanh")]
        self.assertTrue(quick)
        self.assertTrue(all(b["minutes"] <= 30 for b in quick), quick)
        self.assertEqual(quick[0]["title"], "Việc nhanh")
        self.assertEqual(sum(len(b["items"]) for b in quick) + len(res["unplaced"]), 8, "không mất việc nào")

    def test_gap_after_quick_cluster_is_5_minutes(self):
        self.write_items(self._quick_items(1))
        res = planner.suggest(date(2026, 11, 3), self.cfg, t=self.t)
        by = {b["title"]: b for b in res["blocks"]}
        quick = by["Việc nhanh"]
        others = sorted((b for b in res["blocks"] if b["title"] != "Việc nhanh"), key=lambda b: b["start"])
        if others:  # có ô khác ngay sau trong cùng khe thì cách đúng 5'
            after = [b for b in others if b["start"] >= quick["end"]]
            if after:
                gap = parse_dt(after[0]["start"]) - parse_dt(quick["end"])
                self.assertGreaterEqual(gap, timedelta(minutes=5))

    def test_quick_cluster_prefers_short_slot_and_leaves_long_one(self):
        """Cụm nhanh vào khe NGẮN nhất đủ chỗ, chừa khe dài cho việc lớn (M2).
        Hôm đó chỉ có 2 khe: 07:30-08:30 (60') và 22:15-23:00 (45'). Xếp "khe đầu tiên" sẽ chọn 07:30; xếp theo khe ngắn nhất chọn 22:15."""
        self.write_items(self._quick_items(1) + [
            item(id="e1", kind="event", title="Họp 1", start="2026-11-03T08:30+07:00", end="2026-11-03T14:00+07:00"),
            item(id="e2", kind="event", title="Họp 2", start="2026-11-03T14:25+07:00", end="2026-11-03T22:15+07:00")])
        res = planner.suggest(date(2026, 11, 3), self.cfg, t=self.t)
        quick = next(b for b in res["blocks"] if b["title"] == "Việc nhanh")
        self.assertEqual(quick["start"], "2026-11-03T22:15+07:00")
        self.assertEqual(quick["minutes"], 10)

    def test_planner_does_not_schedule_item_with_open_ticket(self):
        self.cfg["lamho"]["bat"] = ["gui_mail"]
        self.write_items(self._quick_items(2))
        before = planner.suggest(date(2026, 11, 3), self.cfg, t=self.t)
        ids_before = {i["id"] for b in before["blocks"] for i in b["items"]}
        self.assertIn("cn:m0", ids_before)
        lamho.add("gui_mail", "Trả lời Mail 0", "Dạ em xác nhận ạ.", "mail của bạn A", item_id="cn:m0",
                  nguoi_nhan=[{"ten": "Bạn A", "dia_chi": "a@example.org", "nguon": "Khôi đưa"}], cfg=self.cfg, t=self.t)
        after = planner.suggest(date(2026, 11, 3), self.cfg, t=self.t)
        ids_after = {i["id"] for b in after["blocks"] for i in b["items"]}
        self.assertNotIn("cn:m0", ids_after, "M5: việc đã có phiếu không xếp giờ cho Khôi")
        self.assertIn("cn:m1", ids_after)

    def test_validate_warns_but_does_not_fail(self):
        data = {"bot": "canhan", "generated_at": "2026-11-02T20:30+07:00", "sources": {"gmail_ca_nhan": {"status": "ok"}},
                "items": [item(id="a", source="gmail_ca_nhan", kind="task", title="Trả lời mail bạn A"),
                          item(id="b", source="gmail_ca_nhan", kind="email", title="Mail", est_minutes=60),
                          item(id="c", source="bkel", kind="deadline", title="Bài tập", due="2026-11-05")]}
        self.assertEqual(validate_domain_file(data), [])
        warns = warnings_domain_file(data)
        self.assertEqual(len(warns), 2)
        self.assertIn("'email'", warns[0])
        self.assertIn("est_minutes", warns[1])
        write_json(self.tmp / "data" / "canhan.json", data)
        code, out = self.run_cli("validate", "data/canhan.json")
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["warnings"]), 2)


def gui_mail(cfg, **kw):
    args = dict(loai="gui_mail", tieu_de="Trả lời mail nhóm", noi_dung="Dạ em xác nhận tham gia ạ.",
                nguon="mail nhóm thứ 2", nguoi_nhan=[{"ten": "Bạn A", "dia_chi": "a@example.org", "nguon": "Khôi đưa"}])
    args.update(kw)
    loai, tieu_de, noi_dung, nguon = (args.pop(k) for k in ("loai", "tieu_de", "noi_dung", "nguon"))
    return lamho.add(loai, tieu_de, noi_dung, nguon, cfg=cfg, **args)


class Lamho(Base):
    def setUp(self):
        super().setUp()
        self.cfg["lamho"]["bat"] = ["gui_mail", "gui_tin", "dien_form", "thanh_toan", "xoa", "nop_bai", "dat_nhac"]

    def test_switch_off_means_no_ticket(self):
        self.cfg["lamho"]["bat"] = []
        with self.assertRaisesRegex(ValueError, "chưa bật"):
            gui_mail(self.cfg, t=self.t)
        with self.assertRaisesRegex(ValueError, "không có"):
            lamho.add("lam_xiec", "x", "y", "z", cfg=self.cfg)

    def test_full_flow_and_done_marks_item(self):
        write_json(self.tmp / "digest.json", {"items": [item(id="cn:m1", kind="email", needs_reply=True, title="Mail A")]})
        r = gui_mail(self.cfg, item_id="cn:m1", t=self.t)
        self.assertEqual(r["id"], "V1")
        self.assertIn("Gửi tới: Bạn A a@example.org, nguồn: Khôi đưa", r["text"])
        self.assertIn("~7 phút của bạn", r["text"], "phút tiết kiệm theo bảng M1")
        with self.assertRaisesRegex(ValueError, "chưa được Khôi duyệt"):
            lamho.start("V1", self.cfg, self.t)
        lamho.approve("V1", self.t)
        out = lamho.start("v1", self.cfg, self.t)             # không phân biệt hoa thường
        self.assertTrue(out["ok"])
        done = lamho.result("V1", "ok", "đã gửi 21:05", self.t)
        self.assertEqual(done["status"], "done")
        self.assertIn("cn:m1", read_json(path("done.json")), "xong thì ghi done để không nhắc lại")
        self.assertEqual(lamho.active_item_ids(), set())
        log = read_jsonl(path("log", "lamho.jsonl"))
        self.assertEqual([r["event"] for r in log], ["add", "approve", "start", "result"])
        self.assertEqual(lamho.day_stats(self.t.date()), {"viec": 1, "phut": 7})

    def test_edit_after_approval_requires_new_approval(self):
        gui_mail(self.cfg, t=self.t)
        lamho.approve("V1", self.t)
        r = lamho.edit("V1", noi_dung="Dạ em xin phép vắng ạ.", cfg=self.cfg, t=self.t)
        self.assertIn("xin phép vắng", r["text"])
        with self.assertRaisesRegex(ValueError, "chưa được Khôi duyệt"):
            lamho.start("V1", self.cfg, self.t)

    def test_hash_changed_after_approval_blocks_start(self):
        gui_mail(self.cfg, t=self.t)
        lamho.approve("V1", self.t)
        data = read_json(path("state", "lamho.json"))
        data["items"][0]["noi_dung"] = "Nội dung bị đổi lén"
        write_json(path("state", "lamho.json"), data)
        with self.assertRaisesRegex(ValueError, "đã đổi sau khi Khôi duyệt"):
            lamho.start("V1", self.cfg, self.t)
        self.assertEqual(lamho._find(lamho._state(), "V1")["status"], "proposed")

    def test_switch_turned_off_after_approval_blocks_start(self):
        gui_mail(self.cfg, t=self.t)
        lamho.approve("V1", self.t)
        self.cfg["lamho"]["bat"] = []
        with self.assertRaisesRegex(ValueError, "đang tắt"):
            lamho.start("V1", self.cfg, self.t)

    def test_recipient_needs_source(self):
        with self.assertRaisesRegex(ValueError, "NGUỒN"):
            gui_mail(self.cfg, nguoi_nhan=[{"ten": "Thầy B", "dia_chi": "b@example.org", "nguon": ""}])
        with self.assertRaisesRegex(ValueError, "người nhận"):
            gui_mail(self.cfg, nguoi_nhan=[])

    def test_zalo_message_only_via_zalo_bot(self):
        with self.assertRaisesRegex(ValueError, "bot Zalo"):
            lamho.add("gui_tin", "Nhắn nhóm", "ok", "Khôi nói", cfg=self.cfg,
                      nguoi_nhan=[{"ten": "Nhóm X", "dia_chi": "nhóm X", "nguon": "Khôi đưa"}])
        r = lamho.add("gui_tin", "Nhắn nhóm", "ok", "Khôi nói", lam_o="zalo", cfg=self.cfg,
                      nguoi_nhan=[{"ten": "Nhóm X", "dia_chi": "nhóm X", "nguon": "Khôi đưa"}], t=self.t)
        self.assertIn("Làm ở bot: zalo", r["text"])

    def test_payment_limit(self):
        def pay(so_tien):
            return lamho.add("thanh_toan", "Đóng phí", "Chuyển khoản phí hoạt động", "mail thông báo", so_tien=so_tien,
                             noi_nhan="Quỹ lớp, tài khoản trong mail", cfg=self.cfg, t=self.t)
        pay(120000)
        lamho.approve("V1", self.t)
        with self.assertRaisesRegex(ValueError, "Chưa cho phép thanh toán"):   # mặc định 0
            lamho.start("V1", self.cfg, self.t)
        self.cfg["lamho"]["toi_da_thanh_toan"] = 100000
        with self.assertRaisesRegex(ValueError, "vượt mức"):
            lamho.start("V1", self.cfg, self.t)
        pay(80000)
        lamho.approve("V2", self.t)
        self.assertTrue(lamho.start("V2", self.cfg, self.t)["ok"])
        with self.assertRaisesRegex(ValueError, "so-tien"):
            lamho.add("thanh_toan", "x", "y", "z", cfg=self.cfg)

    def test_delete_only_to_trash(self):
        with self.assertRaisesRegex(ValueError, "thùng rác hoặc lưu trữ"):
            lamho.add("xoa", "Xóa mail rác", "Xóa 3 mail quảng cáo", "mail", cfg=self.cfg)
        r = lamho.add("xoa", "Xóa mail rác", "Bỏ 3 mail quảng cáo", "mail", cach="thung_rac", cfg=self.cfg, t=self.t)
        self.assertIn("thùng rác", r["text"])

    def test_group3_ok_needs_evidence_and_no_blind_retry(self):
        lamho.add("nop_bai", "Nộp bài 3", "Nộp file bai3.pdf", "BKeL", cfg=self.cfg, t=self.t)
        lamho.approve("V1", self.t)
        lamho.start("V1", self.cfg, self.t)
        with self.assertRaisesRegex(ValueError, "bang-chung"):
            lamho.result("V1", "ok", None, self.t)
        r = lamho.result("V1", "khong-chac", None, self.t)
        self.assertIn("chưa thấy xác nhận", r["text"])
        with self.assertRaisesRegex(ValueError, "lập phiếu mới"):          # không tự thử lại
            lamho.start("V1", self.cfg, self.t)
        r2 = lamho.add("nop_bai", "Nộp bài 3 (lại)", "Nộp lại file bai3.pdf", "BKeL", thay="V1", cfg=self.cfg, t=self.t)
        self.assertEqual(r2["id"], "V2")
        self.assertEqual(lamho._find(lamho._state(), "V2")["thay_cho"], "V1")
        with self.assertRaisesRegex(ValueError, "--thay chỉ dùng"):          # V2 đang chờ duyệt, không phải phiếu hỏng
            lamho.add("nop_bai", "x", "y", "z", thay="V2", cfg=self.cfg, t=self.t)

    def test_failed_result_text_tells_not_to_retry(self):
        gui_mail(self.cfg, t=self.t)
        lamho.approve("V1", self.t)
        lamho.start("V1", self.cfg, self.t)
        r = lamho.result("V1", "loi", "trang báo lỗi", self.t)
        self.assertIn("KHÔNG tự thử lại", r["text"])
        self.assertEqual(lamho.report(self.t)["so_viec"], 0)

    def test_list_cuts_to_5_and_marks_asks(self):
        for i in range(7):
            lamho.add("dat_nhac", f"Nhắc {i}", "Nhắc 15:00", "Khôi nói", cfg=self.cfg, t=self.t)
        r = lamho.list_items(de_xuat=True, mark=True, cfg=self.cfg, t=self.t)
        self.assertEqual(len(r["phieu"]), 5)
        self.assertEqual(r["con_lai"], 2)
        self.assertIn("2 việc khác", r["ghi_chu"])
        self.assertEqual(len(lamho.list_items(de_xuat=True, het=True, cfg=self.cfg, t=self.t)["phieu"]), 7)
        asks = [x["asks"] for x in lamho._state()["items"]]
        self.assertEqual(sorted(asks), [0, 0, 1, 1, 1, 1, 1])

    def test_silence_asks_twice_then_expires(self):
        gui_mail(self.cfg, t=self.t)
        lamho.list_items(de_xuat=True, mark=True, cfg=self.cfg, t=self.t)            # báo cáo 1: hỏi lần 1
        self.assertEqual(lamho.tick(self.cfg, self.t + timedelta(hours=8))["expired"], [])
        r = lamho.list_items(de_xuat=True, mark=True, cfg=self.cfg, t=self.t + timedelta(hours=8))
        self.assertIn("Lần hỏi cuối", r["text"])                                      # báo cáo 2: hỏi lại
        out = lamho.tick(self.cfg, self.t + timedelta(hours=16))                       # báo cáo 3: im lặng → hết hạn
        self.assertEqual([x["id"] for x in out["expired"]], ["V1"])
        with self.assertRaisesRegex(ValueError, "hết hạn hỏi"):
            lamho.start("V1", self.cfg, self.t)

    def test_tick_flags_near_deadline_without_doing_anything(self):
        lamho.add("dien_form", "Điền khảo sát", "Chọn 4/5", "form của lớp", han="2026-11-02T23:00+07:00", cfg=self.cfg, t=self.t)
        out = lamho.tick(self.cfg, self.t)
        self.assertEqual([x["id"] for x in out["nhac_gap"]], ["V1"])
        self.assertIn("KHÔNG tự làm", out["text"])
        self.assertEqual(lamho._find(lamho._state(), "V1")["status"], "proposed")

    def test_overdue_ticket_cannot_start(self):
        lamho.add("dien_form", "Điền khảo sát", "Chọn 4/5", "form của lớp", han="2026-11-02T21:30+07:00", cfg=self.cfg, t=self.t)
        lamho.approve("V1", self.t)
        with self.assertRaisesRegex(ValueError, "quá hạn"):
            lamho.start("V1", self.cfg, self.t + timedelta(minutes=45))

    def test_duplicate_ticket_for_same_item_refused(self):
        gui_mail(self.cfg, item_id="cn:m1", t=self.t)
        with self.assertRaisesRegex(ValueError, "đã có phiếu"):
            gui_mail(self.cfg, item_id="cn:m1", t=self.t)

    def test_drop_and_report_and_tong(self):
        gui_mail(self.cfg, t=self.t)
        gui_mail(self.cfg, tieu_de="Mail hai", t=self.t)
        lamho.drop("V1", self.t)
        lamho.approve("V2", self.t)
        lamho.start("V2", self.cfg, self.t)
        lamho.result("V2", "ok", "đã gửi", self.t)
        rep = lamho.report(self.t)
        self.assertIn("🤖 Đã làm giúp hôm nay:", rep["text"])
        self.assertIn("✅ V2 Mail hai", rep["text"])
        self.assertEqual(rep["so_viec"], 1)
        self.assertEqual(lamho.tong(7, self.t)["viec"], 1)
        self.assertEqual(lamho.tong(7, self.t)["phut_tiet_kiem"], 7)
        self.assertEqual(lamho.report(self.t + timedelta(days=1))["text"], "")

    def test_cli_round_trip(self):
        os.environ["LIFEOS_NOW"] = NOW
        (self.tmp / "config.toml").write_text(
            (ROOT_DIR / "config" / "config.example.toml").read_text(encoding="utf-8").replace("bat = []", 'bat = ["gui_mail"]'),
            encoding="utf-8")
        code, out = self.run_cli("lamho", "add", "--loai", "gui_mail", "--tieu-de", "Trả lời bạn A", "--noi-dung", "Dạ ok ạ",
                                 "--nguon", "mail bạn A", "--nguoi-nhan", "Bạn A|a@example.org|Khôi đưa")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["id"], "V1")
        code, out = self.run_cli("lamho", "start", "V1")
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertIn("chưa được Khôi duyệt", out["why"])
        self.assertEqual(self.run_cli("lamho", "approve", "V1")[0], 0)
        self.assertEqual(self.run_cli("lamho", "start", "V1")[0], 0)
        code, out = self.run_cli("lamho", "result", "V1", "--ket-qua", "ok", "--bang-chung", "đã gửi")
        self.assertEqual((code, out["status"]), (0, "done"))
        code, out = self.run_cli("lamho", "tong", "--days", "7")
        self.assertEqual(out["viec"], 1)

    def test_history_counts_lamho(self):
        from lifeos import history
        gui_mail(self.cfg, t=self.t)
        lamho.approve("V1", self.t)
        lamho.start("V1", self.cfg, self.t)
        lamho.result("V1", "ok", "đã gửi", self.t)
        rec = history.close_day(self.t)
        self.assertEqual(rec["lamho"], {"viec": 1, "phut": 7})
        s = history.summarize([rec])
        self.assertEqual((s["H_lamho_viec"], s["H_lamho_phut"]), (1, 7))


if __name__ == "__main__":
    unittest.main()
