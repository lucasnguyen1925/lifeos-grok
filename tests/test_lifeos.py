"""Chạy:  python3 -m unittest discover -s tests -v   (chỉ cần Python, không cần cài gì)"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from lifeos import agenda, dashboard, digest, health, history, tracking, urgency
from lifeos.common import load_config, parse_dt, vn_date, write_json
from lifeos.schema import validate_domain_file

ROOT_DIR = Path(__file__).resolve().parent.parent
NOW = "2026-11-02T14:00+07:00"  # Thứ 2


def item(**kw):
    base = {"id": "x", "domain": "hoctap", "source": "bkel", "kind": "deadline", "title": "Việc", "status": "open"}
    base.update(kw)
    return base


def domain_file(bot, items, generated_at="2026-11-02T11:30+07:00", sources=None):
    return {"bot": bot, "generated_at": generated_at, "sources": sources or {"x": {"status": "ok"}}, "items": items}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(ROOT_DIR / "config" / "config.example.toml", self.tmp / "config.toml")
        self.env = {"LIFEOS_ROOT": str(self.tmp), "LIFEOS_NOW": NOW}
        self._old = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        self.cfg = load_config()
        self.now = parse_dt(NOW)

    def tearDown(self):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp)

    def write_domains(self, hoctap=(), congty=(), canhan=()):
        for name, items in (("hoctap", hoctap), ("congty", congty), ("canhan", canhan)):
            write_json(self.tmp / "data" / f"{name}.json", domain_file(name, list(items)))


class DateLabels(unittest.TestCase):
    def test_weekday_labels(self):
        self.assertEqual(vn_date(date(2026, 11, 2)), "Thứ 2, 02/11")
        self.assertEqual(vn_date(date(2026, 11, 1)), "Chủ nhật, 01/11")
        self.assertEqual(vn_date(parse_dt("2026-10-31T23:30:00+07:00")), "Thứ 7, 31/10")

    def test_naive_string_is_vietnam_time(self):
        self.assertEqual(parse_dt("2026-11-02T08:00").utcoffset(), timedelta(hours=7))


class Validation(unittest.TestCase):
    def test_good_file(self):
        f = domain_file("hoctap", [item(id="a", due="2026-11-03T23:59+07:00")])
        self.assertEqual(validate_domain_file(f, "hoctap"), [])

    def test_errors_are_actionable(self):
        f = domain_file("hoctap", [
            item(id="a", due="2026-11-03T23:59"),
            item(id="a", kind="homework"),
            item(id="c", kind="class", start="2026-11-03T08:00+07:00"),
            {**item(id="d"), "priority": "high"},
        ])
        errs = "\n".join(validate_domain_file(f, "hoctap"))
        self.assertIn("thiếu múi giờ", errs)
        self.assertIn("bị trùng", errs)
        self.assertIn("'homework' không hợp lệ", errs)
        self.assertIn("cần có 'start' và 'end'", errs)
        self.assertIn("trường lạ", errs)


class Urgency(Base):
    def level(self, it, **kw):
        return urgency.classify(it, self.now, self.cfg, **kw)[0]

    def test_due_windows(self):
        self.assertEqual(self.level(item(due="2026-11-03T08:00+07:00")), urgency.RED)
        self.assertEqual(self.level(item(due="2026-11-04T20:00+07:00")), urgency.ORANGE)
        self.assertEqual(self.level(item(due="2026-11-07T20:00+07:00")), urgency.YELLOW)
        self.assertEqual(self.level(item(due="2026-11-20T20:00+07:00")), urgency.WHITE)

    def test_date_only_due_means_end_of_day(self):
        self.assertEqual(urgency.due_dt(item(due="2026-11-02")).hour, 23)
        self.assertEqual(self.level(item(due="2026-11-02")), urgency.RED)

    def test_overdue_is_red(self):
        self.assertEqual(self.level(item(kind="quiz", due="2026-11-01T23:59+07:00")), urgency.RED)

    def test_vip_waiting_over_12h(self):
        msg = item(kind="message", domain="congty", needs_reply=True, received_at="2026-11-01T20:00+07:00", **{"from": "Anh Minh (quản lý)"})
        self.assertEqual(self.level(msg), urgency.RED)
        other = dict(msg, **{"from": "Bạn cùng lớp"})
        self.assertEqual(self.level(other), urgency.ORANGE)

    def test_changed_schedule_within_48h(self):
        cls = item(kind="class", start="2026-11-03T07:00+07:00", end="2026-11-03T09:00+07:00", changed=True, change_note="đổi phòng")
        level, reasons = urgency.classify(cls, self.now, self.cfg)
        self.assertEqual(level, urgency.RED)
        self.assertIn("đổi phòng", reasons[0])

    def test_urgent_keyword_notice(self):
        n = item(kind="notice", title="Thông báo HOÃN THI giữa kỳ", received_at="2026-11-02T10:00+07:00")
        self.assertEqual(self.level(n), urgency.RED)

    def test_new_quiz_is_orange(self):
        q = item(kind="quiz", due="2026-11-12T23:59+07:00")
        self.assertEqual(self.level(q, first_seen=self.now - timedelta(hours=2)), urgency.ORANGE)


class Digest(Base):
    def test_conflict_done_and_change_detection(self):
        cls = item(id="hoc:1", kind="class", title="CNPM", start="2026-11-03T13:00+07:00", end="2026-11-03T15:00+07:00")
        work = item(id="ct:1", domain="congty", source="cal", kind="work_shift", title="Ca chiều",
                    start="2026-11-03T13:00+07:00", end="2026-11-03T18:00+07:00")
        quiz = item(id="hoc:q", kind="quiz", title="Quiz SA0004", due="2026-11-04T23:59+07:00")
        same_class_personal = item(id="cn:1", domain="canhan", source="cal", kind="class", title="cnpm",
                                   start="2026-11-03T13:00+07:00", end="2026-11-03T15:00+07:00")
        self.write_domains(hoctap=[cls, quiz], congty=[work], canhan=[same_class_personal])

        d = digest.build(cfg=self.cfg)
        self.assertEqual(len(d["conflicts"]), 2)  # lớp ↔ ca làm (lịch trường và bản sao lịch cá nhân), không tính bản sao với nhau
        levels = {x["id"]: x["level"] for x in d["items"]}
        self.assertEqual(levels["hoc:1"], urgency.RED)
        self.assertEqual(d["tomorrow_label"], "Thứ 3, 03/11")
        self.assertIn("hoc:q", d["new_red"] + [x["id"] for x in d["items"]])

        tracking.mark_done("hoc:q")
        d = digest.build(cfg=self.cfg)
        self.assertNotIn("hoc:q", [x["id"] for x in d["items"]])

        moved = dict(cls, start="2026-11-03T15:00+07:00", end="2026-11-03T17:00+07:00")
        self.write_domains(hoctap=[moved], congty=[], canhan=[])
        d = digest.build(cfg=self.cfg)
        it = next(x for x in d["items"] if x["id"] == "hoc:1")
        self.assertTrue(it["changed"])
        self.assertIn("đổi giờ", it["change_note"])

    def test_stale_and_needs_login(self):
        write_json(self.tmp / "data" / "hoctap.json",
                   domain_file("hoctap", [], generated_at="2026-11-01T05:30+07:00",
                               sources={"mybk": {"status": "needs_login", "detail": "SSO hết phiên"}}))
        d = digest.build(cfg=self.cfg)
        self.assertTrue(d["domains"]["hoctap"]["stale"])
        self.assertTrue(d["domains"]["congty"]["missing"])
        self.assertEqual(d["needs_login"][0]["source"], "mybk")


class Alerts(Base):
    def test_quiet_hours_and_no_repeat(self):
        self.write_domains(hoctap=[item(id="q", kind="quiz", due="2026-11-02T17:00+07:00")])
        digest.build(cfg=self.cfg)
        res = tracking.pending_alerts(t=self.now, cfg=self.cfg)
        self.assertEqual([x["id"] for x in res["send"]], ["q"])
        tracking.mark_alerted(["q"])
        self.assertEqual(tracking.pending_alerts(t=self.now, cfg=self.cfg)["send"], [])

        self.write_domains(hoctap=[item(id="q2", kind="quiz", due="2026-11-03T05:00+07:00")])
        digest.build(cfg=self.cfg)
        night = parse_dt("2026-11-02T23:30+07:00")
        res = tracking.pending_alerts(t=night, cfg=self.cfg)
        self.assertEqual(res["send"], [])
        self.assertEqual([x["id"] for x in res["held"]], ["q2"])


class Reminders(Base):
    def test_never_during_class(self):
        cls = item(id="c", kind="class", start="2026-11-02T13:00+07:00", end="2026-11-02T15:00+07:00")
        self.write_domains(hoctap=[cls])
        res = tracking.remind_at(parse_dt("2026-11-02T14:00+07:00"), self.cfg)
        self.assertTrue(res["moved"])
        # T2 mặc định lên văn phòng 9–18 (+30' di chuyển) rồi ăn tối 18:30–19:30 → 19:35
        self.assertEqual(res["at"], "2026-11-02T19:35+07:00")
        free = tracking.remind_at(parse_dt("2026-11-02T19:30+07:00"), self.cfg)
        self.assertFalse(free["moved"])

    def test_free_slots(self):
        work = item(id="w", domain="congty", kind="work_shift", start="2026-11-03T09:00+07:00", end="2026-11-03T18:00+07:00")
        self.write_domains(congty=[work])
        slots = agenda.free_slots(tracking.all_items(), date(2026, 11, 3), self.cfg, 20)
        self.assertEqual(slots[0][1].strftime("%H:%M"), "08:30")
        self.assertTrue(all(s >= parse_dt("2026-11-03T18:30+07:00") for s, _ in slots[1:]))


class Health(Base):
    def test_missed_run_and_login(self):
        health.write_status("hoctap", "full", True, {"mybk": ("needs_login", "SSO")}, t=parse_dt("2026-11-01T20:35+07:00"))
        rep = health.check(self.cfg, t=parse_dt("2026-11-02T07:00+07:00"))
        texts = " ".join(p["text"] for p in rep["problems"])
        self.assertIn("hoctap", texts)
        self.assertEqual(rep["needs_login"][0]["source"], "mybk")
        health.write_status("hoctap", "full", True, {"mybk": ("ok", None)}, t=parse_dt("2026-11-02T05:35+07:00"))
        rep = health.check(self.cfg, t=parse_dt("2026-11-02T07:00+07:00"))
        self.assertFalse([p for p in rep["problems"] if p["bot"] == "hoctap"])
        self.assertFalse(rep["needs_login"])


class History(Base):
    def test_day_week_dashboard_cleanup(self):
        os.environ["LIFEOS_NOW"] = "2026-11-08T21:00+07:00"  # Chủ nhật
        for offset in range(7):
            day = date(2026, 11, 2) + timedelta(days=offset)
            t = parse_dt(f"{day.isoformat()}T21:00+07:00")
            os.environ["LIFEOS_NOW"] = t.isoformat()
            self.write_domains(hoctap=[item(id=f"q{offset}", kind="quiz", title=f"Quiz {offset}", due=f"{day.isoformat()}T23:59+07:00"),
                                       item(id=f"c{offset}", kind="class", start=f"{day.isoformat()}T07:00+07:00", end=f"{day.isoformat()}T09:00+07:00")])
            digest.build(cfg=self.cfg)
            if offset % 2 == 0:
                tracking.mark_done(f"q{offset}", t=t)
            tracking.focus_start("BTL", 30, t=t - timedelta(hours=2))
            tracking.focus_end(interrupted=offset == 3, t=t - timedelta(hours=1, minutes=30))
            tracking.self_report(20, 4, day=day)
            history.close_day(t=t)
        week = history.close_week(t=parse_dt("2026-11-08T21:00+07:00"))
        m = week["metrics"]
        self.assertEqual(m["days_recorded"], 7)
        self.assertEqual(m["A_done"], 4)
        self.assertEqual(m["A_on_time_pct"], 100)
        self.assertEqual(m["D_hours_hoc"], 14.0)
        self.assertEqual(m["G_focus_minutes"], 210)
        self.assertEqual(m["G_interruptions"], 1)
        self.assertEqual(m["F_french_minutes"], 140)
        self.assertTrue((self.tmp / "context" / "weekly" / "2026-W45.md").exists())

        out = dashboard.build(cfg=self.cfg)
        html = Path(out["html"]).read_text(encoding="utf-8")
        self.assertIn("<svg", html)
        self.assertIn("% xong đúng hạn", html)

        write_json(self.tmp / "history" / "daily" / "2026-07-01.json", {})
        write_json(self.tmp / "history" / "zalo" / "2026-10-30.json", {})
        write_json(self.tmp / "context" / "monthly" / "2026-07.json", {})
        history.cleanup(t=parse_dt("2026-11-08T22:00+07:00"), cfg=self.cfg)
        self.assertFalse((self.tmp / "history" / "daily" / "2026-07-01.json").exists())
        self.assertFalse((self.tmp / "history" / "zalo" / "2026-10-30.json").exists())
        self.assertTrue((self.tmp / "context" / "monthly" / "2026-07.json").exists())
        self.assertTrue((self.tmp / "history" / "daily" / "2026-11-02.json").exists())


class Cli(Base):
    def test_date_and_done_ambiguity(self):
        from lifeos.__main__ import main
        self.write_domains(hoctap=[item(id="a", title="Quiz Giải tích 1", due="2026-11-05T23:59+07:00"),
                                   item(id="b", title="Quiz Giải tích 2", due="2026-11-06T23:59+07:00")])
        digest.build(cfg=self.cfg)
        self.assertEqual(main(["done", "giai tich"]), 1)
        self.assertEqual(main(["done", "giai tich", "--pick", "2"]), 0)
        self.assertIn("b", json.loads((self.tmp / "done.json").read_text(encoding="utf-8")))


class Plans(Base):
    def test_plan_flow(self):
        tomorrow = date(2026, 11, 3)
        tracking.plan_add(tomorrow, "BTL CNPM phần 2", "20:00", "Mở file, viết 3 gạch đầu dòng mục 2.1", minutes=10)
        tracking.plan_add(tomorrow, "Quiz 4 GT2", "12:15", "Mở BKeL làm quiz", minutes=20)
        self.assertFalse(any(x.get("confirmed") for x in tracking.plan_list(tomorrow)))
        tracking.plan_confirm(tomorrow, auto=True)
        self.assertTrue(all(x["confirmed"] and x["auto_applied"] for x in tracking.plan_list(tomorrow)))
        tracking.plan_edit(tomorrow, 2, at="13:00")
        self.assertEqual(tracking.plan_list(tomorrow)[1]["at"], "13:00")
        tracking.plan_add(tomorrow, "Việc thừa", "21:00", "…")
        tracking.plan_edit(tomorrow, 3, remove=True)
        self.assertEqual(len(tracking.plan_list(tomorrow)), 2)
        tracking.plan_result(tomorrow, 1, "skipped", why="đi làm về mệt")
        self.assertEqual(tracking.plan_list(tomorrow)[0]["why"], "đi làm về mệt")


class Planner(Base):
    """Tuần 2–8/11/2026: T2 kiểm tra GT2, T3 có lớp sáng, T5 chạy nhóm, thi cuối kỳ 16/11."""

    def setUp(self):
        super().setUp()
        from lifeos import week
        self.cfg["training"]["group_run_keyword"] = "Công viên X"
        os.environ["LIFEOS_NOW"] = "2026-11-01T20:00+07:00"  # Chủ nhật
        self.t = parse_dt("2026-11-01T20:00+07:00")
        self.write_domains(
            hoctap=[
                item(id="hoc:kt", kind="exam", title="Kiểm tra giữa kỳ GT2", start="2026-11-02T13:00+07:00", end="2026-11-02T14:00+07:00"),
                item(id="hoc:final", kind="exam", title="Thi cuối kỳ CNPM", start="2026-11-16T07:00+07:00", end="2026-11-16T09:00+07:00"),
                item(id="hoc:lop", kind="class", title="Lớp XSTK", start="2026-11-03T07:00+07:00", end="2026-11-03T11:00+07:00"),
                item(id="hoc:bt", kind="deadline", title="Bài 3 thí nghiệm", due="2026-11-03T23:00+07:00", est_minutes=90),
                item(id="hoc:far", kind="deadline", title="Báo cáo dài", due="2026-11-05T23:59+07:00", est_minutes=180),
                item(id="hoc:msg", kind="message", title="Trả lời bạn A", needs_reply=True),
            ],
            congty=[item(id="ct:task", domain="congty", kind="deadline", title="Gửi file test", due="2026-11-04T10:00+07:00", est_minutes=60)],
            canhan=[item(id="cn:sala", domain="canhan", kind="event", title="Chạy nhóm Công viên X",
                         start="2026-11-05T18:00+07:00", end="2026-11-05T20:00+07:00")],
        )
        digest.build(t=self.t, cfg=self.cfg)
        self.week = week.propose(date(2026, 11, 2), self.cfg, t=self.t)

    def test_week_proposal(self):
        d = self.week["days"]
        self.assertIsNone(d["2026-11-02"]["office"])                       # có kiểm tra → nghỉ văn phòng
        self.assertEqual(d["2026-11-03"]["office"], ["11:30", "18:00"])     # sau lớp 7–11 + 30' di chuyển
        self.assertEqual(d["2026-11-04"]["office"], ["09:00", "18:00"])
        self.assertIsNone(d["2026-11-08"]["office"])                        # Chủ nhật
        self.assertEqual(d["2026-11-02"]["training"]["label"], "Gym: PUSH")
        self.assertEqual(d["2026-11-02"]["training"]["start"], "06:00")
        self.assertEqual(d["2026-11-03"]["training"]["label"], "Chạy: INTERVAL")
        self.assertEqual(d["2026-11-03"]["training"]["start"], "18:15")     # ngày văn phòng tới 18:00
        self.assertIn("Công viên X", d["2026-11-05"]["training"]["label"])    # thay buổi EASY
        self.assertEqual(d["2026-11-07"]["training"]["label"], "Chạy: LONG RUN")
        self.assertIsNone(d["2026-11-08"]["training"])
        self.assertIn("Bài 3 thí nghiệm", [b["title"] for b in self.week["big_items"]])

    def test_day_profile(self):
        from lifeos.daymodel import profile
        mon = profile(date(2026, 11, 2), self.cfg)        # gym
        self.assertEqual(f"{mon['wake']:%H:%M}", "05:30")
        self.assertEqual(f"{mon['task_start']:%H:%M}", "08:15")
        tue = profile(date(2026, 11, 3), self.cfg)        # chạy tối, hôm sau gym
        self.assertEqual(f"{tue['wake']:%H:%M}", "06:00")   # lớp 07:00 → dậy trước 60 phút
        self.assertEqual(f"{tue['task_end']:%H:%M}", "23:00")
        dinner = tue["meals"][1]
        self.assertEqual(f"{dinner[1]:%H:%M}", "19:45")   # ăn sau buổi chạy 18:15–19:30
        self.assertEqual(tue["day_type"], "office_full")
        self.assertEqual(profile(date(2026, 11, 8), self.cfg)["day_type"], "sunday")

    def test_day_plan(self):
        from lifeos import planner
        t = parse_dt("2026-11-02T21:00+07:00")
        os.environ["LIFEOS_NOW"] = t.isoformat()
        digest.build(t=t, cfg=self.cfg)
        res = planner.suggest(date(2026, 11, 3), self.cfg, t=t)
        titles = [b["title"] for b in res["blocks"]]
        self.assertEqual(titles[0], "Việc nhanh")
        self.assertIn("Bài 3 thí nghiệm", titles)
        busy = tracking.all_items()
        from lifeos.daymodel import profile, synthetic_events
        busy += synthetic_events(profile(date(2026, 11, 3), self.cfg))
        for b in res["blocks"]:
            s, e = parse_dt(b["start"]), parse_dt(b["end"])
            self.assertGreaterEqual(s, parse_dt("2026-11-03T07:30+07:00"))
            self.assertLessEqual(e, parse_dt("2026-11-03T23:00+07:00"))
            self.assertFalse(agenda.is_busy(busy, s, self.cfg), b)
            self.assertFalse(agenda.is_busy(busy, e - timedelta(minutes=1), self.cfg), b)
        # ngày văn phòng cả ngày: tối đa 150 phút / 3 ô
        self.assertLessEqual(res["planned_minutes"], 150)
        self.assertLessEqual(len(res["blocks"]), 3)
        self.assertTrue(any(u["why"].startswith("vượt giới hạn") for u in res["unplaced"]))
        # việc công ty hạn T4 10:00 → để làm trong giờ văn phòng (T3 11:30–18:00), không chiếm giờ tối
        self.assertIn("ct:task", [x["id"] for x in res["at_office"]])
        self.assertNotIn("Gửi file test", titles)
        rows = res["timeline"]
        self.assertEqual(rows[0]["start"], "06:00")  # có lớp 07:00 → dậy trước 60 phút
        quick = next(b for b in res["blocks"] if b["title"] == "Việc nhanh")
        self.assertGreaterEqual(parse_dt(quick["start"]), parse_dt("2026-11-03T19:45+07:00"))
        # việc học hạn ≤ 48h (bậc 2) được xếp trước việc công ty (bậc 3)
        tiers = {b["title"]: b["tier"] for b in res["blocks"]}
        self.assertEqual(tiers["Bài 3 thí nghiệm"], 2)
        types = [r["type"] for r in res["timeline"]]
        self.assertEqual(types[0], "wake")
        self.assertIn("office", types)
        self.assertIn("training", types)

    def test_exam_prep_sessions(self):
        from lifeos import planner
        items = tracking.all_items()
        sessions = {}
        for i in range(15):
            day = date(2026, 11, 2) + timedelta(days=i)
            for s in planner.prep_sessions(day, items, self.cfg):
                sessions.setdefault(s["exam_id"], []).append((day, s))
        final = sessions["hoc:final"]
        self.assertEqual(len(final), 6)
        self.assertEqual(final[-1][0], date(2026, 11, 15))
        self.assertIn("nhẹ", final[-1][1]["title"])
        self.assertEqual([s["_prep_tier"] for _, s in final], [4, 4, 4, 4, 2, 2])
        self.assertNotIn("hoc:kt", sessions)  # kiểm tra 2/11 — cửa sổ ôn đã qua trước 2/11

    def test_plan_saved_excluded_and_timeline(self):
        from lifeos import planner
        tue = date(2026, 11, 3)
        tracking.plan_add(tue, "Bài 3 thí nghiệm", "20:30", "Mở file số liệu", item_id="hoc:bt", minutes=90)
        res = planner.suggest(tue, self.cfg, t=parse_dt("2026-11-02T21:00+07:00"))
        self.assertNotIn("Bài 3 thí nghiệm", [b["title"] for b in res["blocks"]])
        rows = planner.timeline(tue, self.cfg)
        plan_row = next(r for r in rows if r["type"] == "plan")
        self.assertEqual((plan_row["start"], plan_row["end"]), ("20:30", "22:00"))


if __name__ == "__main__":
    unittest.main()
