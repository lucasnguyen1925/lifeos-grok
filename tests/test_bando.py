"""Test bản đồ phân công + việc đã giao (lifeos/bando.py)."""
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

from lifeos import bando, brain
from lifeos.__main__ import main
from lifeos.common import load_config, parse_dt

ROOT_DIR = Path(__file__).resolve().parent.parent
NOW = "2026-11-02T20:50+07:00"


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


class Map(Base):
    def test_map_in_core_with_connection_status(self):
        text = brain.core(self.cfg, self.t)["text"]
        self.assertIn("🗺️ BẢN ĐỒ PHÂN CÔNG", text)
        for name in ("Học tập", "Công ty", "Cá nhân", "Zalo", "LifeOS", "Tiko"):
            self.assertIn(f"- {name} · ", text, "bot nào đọc hồ sơ cũng thấy cả bản đồ")
        self.assertIn("Kết nối: chưa ghi", text)

        bando.set_connection("Drive trường", "ok", kind="Drive", t=self.t)
        bando.set_connection("drive truong", "het_phien", note="cần đăng nhập lại", t=self.t)  # cùng một kết nối
        self.assertEqual(len(bando.connections()), 1)
        text = bando.render(self.cfg)
        self.assertIn("Drive trường (⚠️ hết phiên đăng nhập)", text, "nguồn đang hỏng hiện ngay trong dòng phân công")
        self.assertIn("Drive trường: ⚠️ hết phiên đăng nhập — cần đăng nhập lại", text)
        bando.set_connection("Drive trường", "ok", note="", t=self.t)
        self.assertIn("✅ Drive trường", bando.render(self.cfg))
        self.assertTrue(bando.remove_connection("Drive trường")["ok"])
        with self.assertRaises(ValueError):
            bando.set_connection("Sheets", "lung_tung")

    def test_owner_and_config_override(self):
        self.assertEqual(bando.owner_of("drive truong"), "hoctap")
        self.assertEqual(bando.owner_of("BKeL"), "hoctap")
        self.assertEqual(bando.owner_of("mail công ty"), "congty")
        self.assertEqual(bando.owner_of("danh bạ"), "canhan")
        self.assertEqual(bando.owner_of("đặt reminder"), "lifeos")
        self.assertIsNone(bando.owner_of("Notion"))
        cfg = {"phan_cong": {"hoctap": {"nguon": ["Mail trường", "Notion nhóm"]}}}
        self.assertEqual(bando.owner_of("notion", cfg), "hoctap")
        self.assertEqual(bando.assignments(cfg)["hoctap"]["mang"], "Mọi thứ của trường", "đè một phần, giữ phần còn lại")

    def test_page_has_map(self):
        md = Path(brain.page(self.cfg, self.t)["page_md"]).read_text(encoding="utf-8")
        self.assertIn("## Bản đồ phân công", md)
        self.assertIn("- Học tập · Mọi thứ của trường", md)


class Delegation(Base):
    def test_delegate_wait_and_escalate(self):
        res = bando.delegate("hoctap", "Tìm sheet phân công nhóm X trong Drive trường", t=self.t)
        self.assertEqual((res["id"], res["due"]), ("g1", "21:00"))
        self.assertIn("NGUỒN", res["message"])
        self.assertIn("⏳ ĐANG CHỜ BOT KHÁC TRẢ LỜI", brain.core(self.cfg, self.t)["text"])
        self.assertEqual(bando.overdue(self.t + timedelta(minutes=9))["late"], [])
        late_t = self.t + timedelta(minutes=11)
        self.assertIn("QUÁ HẠN: báo Khôi + nhờ Tiko", brain.core(self.cfg, late_t)["text"])
        self.assertEqual(bando.overdue(late_t, mark=True)["late"][0]["id"], "g1")
        self.assertEqual(bando.overdue(late_t)["late"], [], "báo rồi thì không báo lại")
        self.assertIn("đã báo Khôi", bando.render_waiting(late_t))
        bando.finish("g1", "Không thấy: sheet chưa chia sẻ cho mail trường", t=late_t)
        self.assertEqual(bando.open_items(), [])
        self.assertNotIn("⏳", brain.core(self.cfg, late_t)["text"])

    def test_validation_and_cli(self):
        with self.assertRaises(ValueError):
            bando.delegate("lifeos", "x")
        with self.assertRaises(ValueError):
            bando.delegate("hoctap", "  ")
        with self.assertRaises(ValueError):
            bando.finish("g99")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["giao", "add", "--to", "congty", "--viec", "Tìm mail sếp về lịch tuần sau", "--phut", "5"])
        self.assertEqual((code, json.loads(buf.getvalue())["due"]), (0, "20:55"))
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["bando", "ket-noi", "Sheets", "--trang-thai", "sai"])
        self.assertEqual(code, 1)
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["bando", "ai", "mail", "trường"])
        self.assertEqual(json.loads(buf.getvalue())["name"], "Học tập")


if __name__ == "__main__":
    unittest.main()
