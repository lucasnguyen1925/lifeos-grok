"""Test 0.7.0: vai Vận hành (mã cũ tiko), hộp thư Vận hành → LifeOS, lượt tìm việc nhỏ."""
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

from lifeos import health, lamho, timviec, vanhanh
from lifeos.__main__ import main
from lifeos.common import bot_id, load_config, parse_dt, read_json, role_name, write_json

ROOT_DIR = Path(__file__).resolve().parent.parent
NOW = "2026-11-24T08:45+07:00"


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

    def cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(args))
        return code, json.loads(buf.getvalue())


class OldName(Base):
    def test_bot_id_and_role_name(self):
        self.assertEqual(bot_id(" Tiko "), "vanhanh")
        self.assertEqual(bot_id("hoctap"), "hoctap")
        self.assertEqual(role_name("tiko"), "Vận hành")
        self.assertEqual(role_name("lifeos"), "LifeOS")

    def test_old_status_file_moves_and_old_command_works(self):
        write_json(self.tmp / "_status" / "tiko.json", {"bot": "tiko", "sources": {}, "runs": [], "consecutive_failures": 0})
        code, out = self.cli("status", "tiko", "--type", "check", "--ok")
        self.assertEqual(code, 0)
        self.assertFalse((self.tmp / "_status" / "tiko.json").exists())
        st = read_json(self.tmp / "_status" / "vanhanh.json")
        self.assertEqual((st["bot"], len(st["runs"])), ("vanhanh", 1))
        self.assertIn("vanhanh", health.check(self.cfg, self.t)["bots"])

    def test_lamho_cannot_run_at_ops_role(self):
        with self.assertRaises(ValueError):
            lamho.add("luu_nhap", "Lưu nháp", "nội dung", "Khôi đưa", lam_o="vanhanh",
                      cfg={"lamho": {"bat": ["luu_nhap"]}}, t=self.t)


class Mailbox(Base):
    def test_add_list_mark_and_dedupe(self):
        vanhanh.add("Bot Học tập lỡ lần quét 05:00, đã cho chạy lại, ổn", t=self.t)
        again = vanhanh.add("Bot Học tập  lỡ lần quét 05:00, đã cho chạy lại, ổn", t=self.t)
        self.assertTrue(again["already"], "tin trùng đang chờ thì không ghi lại")
        vanhanh.add("Tuần qua: 98% lần quét thành công\n7/7 đêm sao lưu ok", loai="tuan", t=self.t)
        vanhanh.add("Đã nhắn Khôi: Zalo cần xác nhận đồng bộ", loai="gap", t=self.t)
        res = vanhanh.list_items(t=self.t)
        self.assertEqual(res["count"], 2, "tin gấp đã nhắn thẳng Khôi, không đưa vào báo cáo nữa")
        self.assertIn("⚙️ Bot Học tập lỡ lần quét", res["text"])
        self.assertIn("🛠 Hệ thống tuần qua (Vận hành):\nTuần qua: 98%", res["text"])
        self.assertEqual(len(res["gap_24h"]), 1)
        vanhanh.list_items(mark=True, t=self.t)
        self.assertEqual(vanhanh.list_items(t=self.t)["count"], 0, "đưa rồi thì không đưa lại")
        self.assertEqual(vanhanh.list_items(t=self.t + timedelta(hours=25))["gap_24h"], [])

    def test_cli(self):
        code, out = self.cli("vanhanh", "add", "--text", "  ")
        self.assertEqual(code, 1)
        code, out = self.cli("vanhanh", "add", "--gap", "--text", "Mất đăng nhập mail công ty, đã nhắn Khôi")
        self.assertEqual((code, out["id"]), (0, "vh1"))
        code, out = self.cli("vanhanh", "list", "--mark")
        self.assertEqual(out["count"], 0)


def _item(i, **kw):
    base = {"id": f"hoctap:{i}", "domain": "hoctap", "kind": "deadline", "title": f"Việc {i}",
            "status": "open", "due": "2026-11-27T23:59+07:00", "level_label": "🟡 TRUNG BÌNH"}
    return base | kw


class FindWork(Base):
    def write_digest(self, items, today=()):
        write_json(self.tmp / "digest.json", {"generated_label": "08:30 Thứ 3, 24/11", "items": items,
                                              "schedule_today": list(today)})

    def test_nothing_new_means_stop(self):
        res = timviec.check(t=self.t)
        self.assertFalse(res["co_moi"])
        self.write_digest([])
        res = timviec.check(t=self.t + timedelta(hours=3))
        self.assertFalse(res["co_moi"])
        self.assertIn("Dừng ngay", res["note"])

    def test_new_items_then_marked_then_changed(self):
        self.write_digest([_item(1), _item(2)])
        t = self.t + timedelta(hours=3)                       # 11:45, lượt ngày
        res = timviec.check(t=t)
        self.assertEqual((res["co_moi"], res["luot"], [x["id"] for x in res["viec"]]),
                         (True, "ngày", ["hoctap:1", "hoctap:2"]))
        self.assertEqual(res["chuan_bi"], [])
        timviec.check(mark=True, t=t)
        self.assertFalse(timviec.check(t=t)["co_moi"], "đã xem thì lần sau không xem lại")
        self.write_digest([_item(1, due="2026-11-26T23:59+07:00"), _item(2)])
        self.assertEqual([x["id"] for x in timviec.check(t=t)["viec"]], ["hoctap:1"], "đổi hạn → xem lại")
        write_json(self.tmp / "done.json", {"hoctap:1": {"at": "2026-11-24T11:00+07:00"}})
        self.assertFalse(timviec.check(t=t)["co_moi"], "việc đã xong thì bỏ qua")

    def test_morning_prepares_today_once(self):
        ev = {"id": "hoctap:ev1", "domain": "hoctap", "kind": "event", "title": "Họp nhóm môn X",
              "start": "2026-11-24T14:00+07:00", "status": "open"}
        past = dict(ev, id="hoctap:ev0", start="2026-11-24T07:00+07:00")
        self.write_digest([], today=[past, ev])
        res = timviec.check(t=self.t)
        self.assertEqual((res["luot"], [x["id"] for x in res["chuan_bi"]]), ("sáng", ["hoctap:ev1"]),
                         "chỉ lịch còn lại trong ngày")
        timviec.check(mark=True, t=self.t)
        self.assertFalse(timviec.check(t=self.t)["co_moi"], "chuẩn bị rồi thì thôi")
        self.assertEqual(timviec.check(t=self.t + timedelta(hours=3))["chuan_bi"], [], "lượt ngày không chuẩn bị")
        code, out = self.cli("timviec", "check", "--sang")
        self.assertEqual((code, out["luot"]), (0, "sáng"))


if __name__ == "__main__":
    unittest.main()
