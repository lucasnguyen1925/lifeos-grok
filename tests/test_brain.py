"""Test sổ nhớ (lifeos/brain.py). Chạy:  python3 -m unittest discover -s tests -v"""
from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import timedelta
from pathlib import Path
from unittest import mock

from lifeos import brain, history
from lifeos.__main__ import main
from lifeos.common import load_config, parse_dt, read_json, write_json

ROOT_DIR = Path(__file__).resolve().parent.parent
NOW = "2026-11-02T14:00+07:00"  # Thứ 2


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

    def facts(self):
        return {f["id"]: f for f in read_json(self.tmp / "brain" / "so_nho.json")["facts"]}


class Facts(Base):
    def test_add_dedup_and_core_profile(self):
        a = brain.add("nguoi_quen", "Bạn A là trưởng nhóm BTL", subject="bạn A", core=True, t=self.t)
        dup = brain.add("nguoi_quen", "bạn A là trưởng nhóm btl.", t=self.t + timedelta(days=1))
        self.assertEqual(dup["duplicate_of"], a["id"])
        self.assertEqual(len(self.facts()), 1, "trùng thì không ghi thêm")
        other = brain.add("nguoi_quen", "Bạn B là trưởng nhóm BTL", t=self.t)
        self.assertNotIn("duplicate_of", other, "khác tên người là khác điều")
        brain.forget([other["id"]], t=self.t)
        self.assertEqual(self.facts()[a["id"]]["confirmed_at"], "2026-11-03T14:00+07:00", "nhắc lại = làm mới")

        brain.add("cach_lam_viec", "Không học nổi sau 22h", core=True, t=self.t)
        brain.add("khac", "Thích màu xanh", core=True, t=self.t)          # mục 'khác' không lên hồ sơ
        brain.add("ve_khoi", "Đang học tiếng Pháp", t=self.t)              # không chọn core → chỉ nằm trong sổ
        text = brain.core(self.cfg, self.t)["text"]
        self.assertIn("👥 NGƯỜI QUEN", text)
        self.assertIn("Bạn A là trưởng nhóm BTL", text)
        self.assertIn("Không học nổi sau 22h", text)
        self.assertNotIn("Thích màu xanh", text)
        self.assertNotIn("tiếng Pháp", text)
        self.assertIn("brain search", text)

    def test_core_limits_pin_sensitive_and_due(self):
        for i in range(12):
            brain.add("nguoi_quen", f"Người số {i} là bạn cùng lớp môn {i}", core=True, t=self.t + timedelta(minutes=i))
        old = brain.add("nguoi_quen", "Anh B là quản lý trực tiếp", core=True, t=self.t - timedelta(days=30))
        brain.set_flags(old["id"], pin=True)
        secret = brain.add("ve_khoi", "Chuyện sức khỏe riêng", core=True, sensitive=True, t=self.t)
        late = brain.add("dang_do", "Hứa gửi file cho bạn A", due="2026-11-01", core=True, t=self.t)
        soon = brain.add("dang_do", "Nộp đơn xin nghỉ", due="2026-11-05", core=True, t=self.t)
        res = brain.core(self.cfg, self.t)
        lines = res["text"].splitlines()
        people = lines[lines.index("👥 NGƯỜI QUEN") + 1:]
        self.assertTrue(people[0].startswith("- 📌 Anh B"), "điều ghim lên đầu, không bị đẩy ra")
        self.assertEqual(sum(1 for x in people if x.startswith("- ") and ("Người số" in x or "Anh B" in x)), 10)
        self.assertEqual(res["hidden_over_limit"], 3, "quá giới hạn thì nằm lại trong sổ")
        self.assertNotIn("Người số 0 ", res["text"], "điều lâu không nhắc nhất bị đẩy xuống trước")
        self.assertNotIn("sức khỏe", res["text"], "chuyện nhạy cảm không tự lên hồ sơ")
        self.assertNotIn("bạn A", res["text"], "lời hứa quá hạn không còn trên hồ sơ")
        self.assertIn("Nộp đơn xin nghỉ (hạn Thứ 5, 05/11)", res["text"])
        brain.set_flags(secret["id"], pin=True)
        self.assertIn("sức khỏe", brain.core(self.cfg, self.t)["text"], "Khôi tự ghim thì mới lên")

        self.assertEqual(brain.tidy(self.t)["moved_to_past"], [late["id"]])
        self.assertEqual(self.facts()[late["id"]]["status"], "past")
        self.assertEqual(self.facts()[soon["id"]]["status"], "current")

    def test_history_search_show(self):
        old = brain.add("ve_khoi", "Làm part-time ở Công ty X", subject="Công ty X", core=True, t=self.t - timedelta(days=60))
        new = brain.add("ve_khoi", "Đã nghỉ làm ở Công ty X", replaces=old["id"], t=self.t)
        f = self.facts()
        self.assertEqual(f[old["id"]]["status"], "past")
        self.assertEqual(f[old["id"]]["replaced_by"], new["id"])
        self.assertTrue(f[new["id"]]["core"], "điều thay thế giữ chỗ trên hồ sơ")
        self.assertEqual(f[new["id"]]["subject"], "Công ty X")
        text = brain.core(self.cfg, self.t)["text"]
        self.assertIn("Đã nghỉ", text)
        self.assertNotIn("Làm part-time", text, "hồ sơ chỉ hiện điều đang đúng")

        hits = brain.search("cong ty x lam")["results"]
        statuses = {h["id"]: h["status"] for h in hits}
        self.assertEqual(statuses[new["id"]], "đang đúng")
        self.assertTrue(statuses[old["id"]].startswith("trước đây (tới 11/2026)"), "hỏi 'hồi trước' vẫn trả lời được")

        page = brain.show("công ty x")["text"]
        self.assertIn("## Đang đúng", page)
        self.assertIn("## Trước đây", page)

        with self.assertRaises(ValueError):
            brain.add("ve_khoi", "x", replaces=old["id"], t=self.t)  # điều cũ đã không còn đúng

        brain.end(new["id"], "Khôi nói đã xong", t=self.t)
        self.assertEqual(self.facts()[new["id"]]["status"], "past")

    def test_search_without_diacritics_and_fallback(self):
        brain.add("cach_lam_viec", "Đọc sách 20 phút trước khi ngủ", t=self.t)
        brain.add("cach_lam_viec", "Ghét họp buổi tối", t=self.t)
        brain.kho_add("Trang ưu đãi sinh viên Y", "Ưu đãi cho sinh viên", tags=["học bổng"], url="https://example.com", t=self.t)
        brain.journal_add("lifeos", "Bàn chia việc BTL với nhóm", t=self.t)
        self.assertEqual(brain.search("doc sach")["results"][0]["text"], "Đọc sách 20 phút trước khi ngủ")
        self.assertEqual(brain.search("hop toi")["results"][0]["text"], "Ghét họp buổi tối")
        self.assertEqual(brain.search("uu dai")["results"][0]["type"], "kho")
        self.assertEqual(brain.search("chia viec")["results"][0]["type"], "nhật ký")
        self.assertIsNotNone(brain.search("khong co gi")["note"])
        with mock.patch.object(brain, "_fts_available", return_value=False):
            self.assertEqual(brain.search("doc sach")["results"][0]["text"], "Đọc sách 20 phút trước khi ngủ")

    def test_forget_removes_history_and_keeps_no_text(self):
        old = brain.add("ve_khoi", "Ở trọ quận Y", t=self.t - timedelta(days=10))
        new = brain.add("ve_khoi", "Chuyển về ở nhà", replaces=old["id"], t=self.t)
        keep = brain.add("ve_khoi", "Đang học tiếng Pháp", t=self.t)
        k = brain.kho_add("Ảnh giấy tờ", kind="anh", drive="https://drive.example/abc", t=self.t)
        j = brain.journal_add("lifeos", "Kể chuyện chuyển nhà", t=self.t)
        res = brain.forget([new["id"], k["id"], j["id"], "m999"], t=self.t)
        self.assertEqual({x["id"] for x in res["forgotten"]}, {new["id"], old["id"], k["id"], j["id"]})
        self.assertEqual(res["not_found"], ["m999"])
        self.assertEqual(res["drive_to_trash"], ["https://drive.example/abc"])
        self.assertIn("Chuyển về ở nhà", res["message_for_other_bots"])
        self.assertIn("ĐÚNG", res["message_for_other_bots"])
        self.assertEqual(set(self.facts()), {keep["id"]})
        log = (self.tmp / "brain" / "da_quen.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("nhà", log, "nhật ký quên chỉ giữ mã, không giữ nội dung")
        self.assertNotIn("Kể chuyện", json.dumps(brain.journal_show(t=self.t), ensure_ascii=False))

    def test_validation(self):
        with self.assertRaises(ValueError):
            brain.add("lung_tung", "x", t=self.t)
        with self.assertRaises(ValueError):
            brain.add("ve_khoi", "x" * 400, t=self.t)
        with self.assertRaises(ValueError):
            brain.add("ve_khoi", "x", by="nguoi_la", t=self.t)


class Proposals(Base):
    def night(self, n):
        return parse_dt(f"2026-11-{2 + n:02d}T21:00+07:00")

    def test_three_per_night_ask_twice_then_drop(self):
        ids = [brain.propose("hoctap", f"Bạn {c} học chung nhóm môn {c}", "Zalo nhóm học", "nguoi_quen", t=self.t)["id"]
               for c in "PQRS"]
        r1 = brain.report(self.cfg, self.night(0))
        self.assertEqual(list(r1["letters"]), ["a", "b", "c"], "tối đa 3 đề xuất mỗi tối")
        self.assertIn('"ghi a" · "bỏ c" · "ghi hết"', r1["text"])
        brain.report(self.cfg, self.night(0), mark=True)

        r2 = brain.report(self.cfg, self.night(1), mark=True)
        self.assertEqual(list(r2["letters"].values()), ids[:3], "im lặng → tối sau hỏi lại")
        self.assertIn("hỏi lại lần cuối", r2["text"])

        r3 = brain.report(self.cfg, self.night(2), mark=True)
        self.assertEqual(list(r3["letters"].values()), [ids[3]], "hỏi 2 lần vẫn im → bỏ")
        props = {p["id"]: p for p in read_json(self.tmp / "brain" / "de_xuat.json")["items"]}
        self.assertEqual([props[i]["status"] for i in ids[:3]], ["expired"] * 3)
        again = brain.propose("hoctap", "Bạn P học chung nhóm môn P", "Zalo", t=self.t)
        self.assertFalse(again["ok"], "đề xuất đã bị bỏ thì không đề xuất lại")

        res = brain.accept(["a"], t=self.night(2))
        fact = self.facts()[res["results"][0]["fact_id"]]
        self.assertEqual((fact["by"], fact["origin"], fact["section"]), ("hoctap", "de_xuat", "nguoi_quen"))
        self.assertNotIn(fact["id"], brain.report(self.cfg, self.night(3))["new"], "đã duyệt thì không báo lại")
        with self.assertRaises(ValueError):
            brain.accept(["a"])

    def test_accept_all_reject_and_rules(self):
        brain.add("nguoi_quen", "Bạn A là trưởng nhóm BTL", t=self.t)
        known = brain.propose("zalo", "bạn A là trưởng nhóm BTL", "Zalo", "nguoi_quen", t=self.t)
        self.assertIn("already_known", known)
        with self.assertRaises(ValueError):
            brain.propose("lifeos", "x", "chat")
        brain.propose("congty", "Nhóm X họp thứ 5 hằng tuần", "Mail", t=self.t)
        brain.propose("canhan", "Em C sắp thi đại học", "Zalo gia đình", t=self.t)
        dup = brain.propose("canhan", "Em C sắp thi đại học.", "Zalo", t=self.t)
        self.assertIn("duplicate_of", dup)
        brain.report(self.cfg, self.t, mark=True)
        brain.reject(["b"], t=self.t)
        brain.accept(["hết"], t=self.t)
        statuses = sorted(p["status"] for p in read_json(self.tmp / "brain" / "de_xuat.json")["items"])
        self.assertEqual(statuses, ["accepted", "rejected"])


class Report(Base):
    def test_new_facts_roll_over_and_migrated_are_quiet(self):
        brain.add("ve_khoi", "Tháng 12 về quê", t=self.t)
        brain.add("ve_khoi", "Có em gái học lớp 10", origin="grok", t=self.t)
        brain.add("ve_khoi", "Chuyện riêng", sensitive=True, t=self.t)
        r = brain.report(self.cfg, self.t)
        self.assertIn("🧠 Nhớ thêm: Tháng 12 về quê · 🔒 1 chuyện riêng", r["text"])
        self.assertNotIn("em gái", r["text"], "chuyển từ trí nhớ cũ thì không dồn vào dòng 🧠")
        self.assertIn("Tháng 12", brain.report(self.cfg, self.t + timedelta(days=1))["text"], "lỡ báo thì lần sau dồn đủ")
        brain.report(self.cfg, self.t, mark=True)
        self.assertEqual(brain.report(self.cfg, self.t)["text"], "", "báo rồi thì thôi")
        for i in range(7):
            brain.add("khac", f"Điều thứ {i} rất khác nhau số {i * 7}", t=self.t)
        self.assertIn("và 2 điều khác (xem Page Trí nhớ)", brain.report(self.cfg, self.t)["text"])

    def test_monthly_stale_questions(self):
        old_t = parse_dt("2026-03-01T10:00+07:00")
        a = brain.add("cach_lam_viec", "Thích chạy bộ buổi tối", t=old_t)
        b = brain.add("ve_khoi", "Ở chung với bạn cùng phòng", t=old_t)
        brain.add("ve_khoi", "Mới vào làm part-time", t=parse_dt("2026-10-01T10:00+07:00"))
        brain.report(self.cfg, old_t, mark=True)
        self.assertNotIn("🔎", brain.report(self.cfg, parse_dt("2026-11-02T21:00+07:00"))["text"], "chỉ hỏi ngày cuối tháng")
        end_nov = parse_dt("2026-11-30T21:00+07:00")
        r = brain.report(self.cfg, end_nov, mark=True)
        self.assertIn("🔎 Còn đúng không?", r["text"])
        self.assertEqual(set(r["letters"].values()), {a["id"], b["id"]})
        self.assertNotIn("part-time", r["text"])
        brain.confirm([k for k, v in r["letters"].items() if v == a["id"]], t=end_nov)
        r2 = brain.report(self.cfg, parse_dt("2026-12-31T21:00+07:00"), mark=True)
        self.assertNotIn("🔎", r2["text"], "đã hỏi rồi thì không hỏi lại")
        f = self.facts()
        self.assertFalse(f[a["id"]]["unconfirmed"])
        self.assertTrue(f[b["id"]]["unconfirmed"], "không trả lời → giữ, đánh dấu chưa xác nhận lại")
        self.assertEqual(f[b["id"]]["status"], "current", "không tự xóa")
        self.assertIn("chưa xác nhận lại", Path(brain.page(self.cfg, end_nov)["page_md"]).read_text(encoding="utf-8"))


class JournalKhoPage(Base):
    def test_journal(self):
        for i in range(6):
            res = brain.journal_add("lifeos", f"Chuyện số {i}", t=self.t)
        self.assertIsNotNone(res["warning"])
        p = brain.journal_add("tiko", "Nội dung nhạy cảm không được lưu", private=True, t=self.t)
        day = read_json(self.tmp / "brain" / "nhat_ky" / "2026-11-02.json")
        self.assertNotIn("nhạy cảm", json.dumps(day, ensure_ascii=False))
        self.assertEqual(day["lines"][-1]["id"], p["id"])
        brain.journal_replace(self.t.date(), ["LifeOS: bàn BTL", "Tiko: đăng nhập lại Zalo"], t=self.t)
        lines = brain.journal_show(self.t.date(), t=self.t)["days"][0]["lines"]
        self.assertEqual([x["text"] for x in lines], ["LifeOS: bàn BTL", "Tiko: đăng nhập lại Zalo", brain.PRIVATE_LINE])
        self.assertEqual(len(brain.journal_show(month="2026-11", t=self.t)["days"]), 1)

        write_json(self.tmp / "brain" / "nhat_ky" / "2026-07-01.json", {"date": "2026-07-01", "lines": []})
        history.cleanup(t=self.t, cfg=self.cfg)
        self.assertFalse((self.tmp / "brain" / "nhat_ky" / "2026-07-01.json").exists(), "nhật ký giữ 90 ngày")
        self.assertTrue((self.tmp / "brain" / "nhat_ky" / "2026-11-02.json").exists())

    def test_kho_and_page(self):
        for i in range(12):
            brain.kho_add(f"Link số {i}", tags=["môn X" if i % 2 else "dự án Y"], url=f"https://e.com/{i}",
                          t=self.t + timedelta(minutes=i))
        self.assertEqual(len(brain.kho_list(tag="mon x", limit=20)["items"]), 6)
        brain.add("nguoi_quen", "Bạn A là trưởng nhóm BTL", core=True, t=self.t)
        brain.add("ve_khoi", "Chuyện riêng tư", sensitive=True, t=self.t)
        brain.propose("hoctap", "Nhóm học họp thứ 5", "Zalo", t=self.t)
        brain.report(self.cfg, self.t, mark=True)
        md = Path(brain.page(self.cfg, self.t)["page_md"]).read_text(encoding="utf-8")
        for part in ("# LifeOS · Trí nhớ", "## Hồ sơ ngắn", "## Nhớ thêm 7 ngày qua", "## Đang chờ Khôi duyệt",
                     "## Kho — 10 món lưu gần đây", "## Toàn bộ sổ (đang đúng)", "m1 · Bạn A", "a. Nhóm học"):
            self.assertIn(part, md)
        self.assertNotIn("Chuyện riêng tư", md, "Page không hiện nội dung chuyện riêng")
        self.assertIn("Link số 11", md)
        self.assertNotIn("Link số 1 ", md, "chỉ 10 món gần nhất")


class DupesBackup(Base):
    def test_dupes_merge_unmerge(self):
        a = brain.add("cach_lam_viec", "Học buổi sáng vào đầu hơn", t=self.t)
        same = brain.add("cach_lam_viec", "Buổi sáng học vào đầu hơn hẳn", t=self.t + timedelta(minutes=30))
        self.assertEqual(same["duplicate_of"], a["id"], "chỉ lệch chữ đệm → trùng ngay khi ghi")
        b = brain.add("cach_lam_viec", "Học buổi sáng vào đầu hơn buổi chiều", t=self.t + timedelta(hours=1))
        brain.add("tranh", "Học buổi sáng vào đầu hơn", t=self.t)  # khác mục → không ghép
        pairs = brain.dupes()["pairs"]
        self.assertEqual(len(pairs), 1)
        self.assertEqual({pairs[0]["keep"], pairs[0]["drop"]}, {a["id"], b["id"]})
        brain.merge(pairs[0]["keep"], pairs[0]["drop"], t=self.t)
        self.assertEqual(self.facts()[pairs[0]["drop"]]["status"], "merged")
        self.assertNotIn(pairs[0]["drop"], [r["id"] for r in brain.search("buoi sang")["results"]])
        brain.unmerge(pairs[0]["drop"])
        self.assertEqual(self.facts()[pairs[0]["drop"]]["status"], "current")
        brain.merge(pairs[0]["keep"], pairs[0]["drop"], t=self.t)
        gone = {x["id"] for x in brain.forget([pairs[0]["keep"]], t=self.t)["forgotten"]}
        self.assertEqual(gone, {a["id"], b["id"]}, "quên thì quên luôn điều đã gộp vào")

    def test_backup_and_restore(self):
        write_json(self.tmp / "done.json", {"x": 1})
        write_json(self.tmp / "context" / "monthly" / "2026-10.json", {"m": 1})
        write_json(self.tmp / "context" / "weekly" / "2026-W44.json", {"w": 1})
        a = brain.add("ve_khoi", "Đang học tiếng Pháp", t=self.t)
        brain.journal_add("lifeos", "Bàn kế hoạch tuần", t=self.t)
        res = brain.backup(self.t)
        self.assertEqual(res["drive_name"], "lifeos_saoluu_thu2.json", "7 bản xoay vòng theo thứ")
        bundle = read_json(Path(res["file"]))
        self.assertTrue({"brain/so_nho.json", "config.toml", "done.json", "context/monthly/2026-10.json",
                         "brain/nhat_ky/2026-11-02.json"} <= set(bundle["files"]))
        self.assertNotIn("context/weekly/2026-W44.json", bundle["files"], "chỉ sao lưu thứ không tạo lại được")

        brain.forget([a["id"]], t=self.t)
        preview = brain.restore(res["file"], t=self.t)
        self.assertFalse(preview["applied"])
        self.assertNotIn(a["id"], self.facts(), "xem trước thì chưa ghi gì")
        done = brain.restore(res["file"], apply=True, t=self.t)
        self.assertIn(a["id"], self.facts())
        self.assertTrue(Path(done["safety_copy"]).exists(), "khôi phục xong vẫn còn bản trước khi khôi phục")

        evil = self.tmp / "evil.json"
        write_json(evil, {"lifeos_backup": 1, "files": {"../ngoai.txt": "x"}})
        with self.assertRaises(ValueError):
            brain.restore(str(evil))
        self.assertEqual(brain.backup(parse_dt("2026-11-08T02:15+07:00"))["drive_name"], "lifeos_saoluu_cn.json")


class BrainCli(Base):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["brain", *args])
        return code, json.loads(buf.getvalue())

    def test_cli_flow(self):
        code, out = self.run_cli("add", "--section", "nguoi_quen", "--text", "Bạn A là trưởng nhóm", "--core")
        self.assertEqual((code, out["id"]), (0, "m1"))
        code, out = self.run_cli("add", "--section", "lung_tung", "--text", "x")
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertIn("--section", out["why"])
        code, out = self.run_cli("search", "ban", "a")
        self.assertEqual(out["results"][0]["id"], "m1")
        code, out = self.run_cli("unpin", "m1")
        self.assertFalse(out["core"])
        code, out = self.run_cli("forget", "z")
        self.assertEqual(code, 1, "chữ không có trong lần báo gần nhất")
        code, out = self.run_cli("journal", "add", "--by", "tiko", "--text", "Đăng nhập lại Zalo")
        self.assertEqual(out["id"], "nk20261102-1")


if __name__ == "__main__":
    unittest.main()
