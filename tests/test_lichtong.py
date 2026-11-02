"""Lịch tổng (0.5.0): buổi tập né giờ học, trùng lịch tính cả thứ LifeOS tự xếp, chốt kế hoạch có kiểm tra,
giờ dậy không bị kéo về 23:00, nhãn hạn 00:00. Tên môn/sự kiện trong test là tên chung."""
from __future__ import annotations

import json
import os
from datetime import date

from lifeos import dashboard, digest, lichtong, tracking, week
from lifeos.__main__ import main
from lifeos.common import page_changed, parse_dt, vn_deadline, write_json
from lifeos.daymodel import profile
from lifeos.schema import validate_item
from tests.test_lifeos import Base, item

WED = date(2026, 11, 4)    # Thứ 4 — config mẫu: gym T2/T4/T6, chạy T3/T5/T7
SUN_EVENING = "2026-11-01T20:00+07:00"


def klass(i, title, start, end, **kw):
    return item(id=i, kind="class", title=title, start=start, end=end, **kw)


class LichTongBase(Base):
    def setUp(self):
        super().setUp()
        os.environ["LIFEOS_NOW"] = SUN_EVENING
        self.t = parse_dt(SUN_EVENING)

    def propose(self, hoctap=(), congty=(), canhan=()):
        self.write_domains(hoctap=list(hoctap), congty=list(congty), canhan=list(canhan))
        digest.build(t=self.t, cfg=self.cfg)
        return week.propose(date(2026, 11, 2), self.cfg, t=self.t)

    def set_week(self, days: dict):
        write_json(self.tmp / "state" / "week.json", {"week_start": "2026-11-02", "confirmed": False, "days": days})


class TrainingAvoidsClass(LichTongBase):
    def test_gym_free_morning_stays(self):
        w = self.propose()
        self.assertEqual(w["days"]["2026-11-04"]["training"], {"type": "gym", "label": "Gym: PULL", "start": "06:00", "end": "08:00"})
        self.assertEqual(w["conflicts"], [])

    def test_gym_moves_to_evening_when_morning_has_class(self):
        # Chuyện thật 0.4.0: gym 6–8 đè lớp 7–9. Nay gym phải dời sang tối cùng ngày.
        w = self.propose(hoctap=[klass("c1", "Lớp A", "2026-11-04T07:00+07:00", "2026-11-04T08:50+07:00")])
        d = w["days"]["2026-11-04"]
        tr = d["training"]
        self.assertEqual((tr["type"], tr["label"]), ("gym", "Gym: PULL"))
        self.assertEqual((tr["start"], tr["end"]), ("18:15", "20:15"))   # sau văn phòng (tới 18:00)
        self.assertIn("dời", d["training_note"])
        self.assertEqual(lichtong.high(w["conflicts"]), [])
        # gym tối: không dậy 5:30, không báo thức gym sáng
        self.assertFalse(profile(WED, self.cfg)["gym_day"])

    def test_gym_dropped_when_evening_is_full_too(self):
        w = self.propose(hoctap=[klass("c1", "Lớp A", "2026-11-04T07:00+07:00", "2026-11-04T08:50+07:00"),
                                 klass("c2", "Lớp tối", "2026-11-04T17:00+07:00", "2026-11-04T21:30+07:00")])
        d = w["days"]["2026-11-04"]
        self.assertIsNone(d["training"])
        self.assertIn("bỏ", d["training_note"])

    def test_class_right_after_gym_needs_travel_time(self):
        # lớp 8:10: gym tới 8:00 + 30' đi lại → sát quá → dời tối
        w = self.propose(hoctap=[klass("c1", "Lớp A", "2026-11-04T08:10+07:00", "2026-11-04T10:00+07:00")])
        self.assertEqual(w["days"]["2026-11-04"]["training"]["start"], "18:15")

    def test_run_also_avoids_event_with_travel(self):
        w = self.propose(hoctap=[klass("c1", "Lớp A", "2026-11-03T15:00+07:00", "2026-11-03T18:00+07:00")])
        run = w["days"]["2026-11-03"]["training"]
        self.assertEqual(run["type"], "run")
        self.assertGreaterEqual(run["start"], "18:30")   # lớp tới 18:00 + 30' di chuyển


class OfficeAvoidsSchoolEvents(LichTongBase):
    def test_office_skips_school_lab_event_but_not_short_reminder(self):
        lab = item(id="lab", kind="event", title="Thí nghiệm B", start="2026-11-04T13:00+07:00", end="2026-11-04T17:30+07:00")
        remind = item(id="chk", domain="canhan", kind="event", title="Kiểm tra file", start="2026-11-04T17:00+07:00",
                      end="2026-11-04T17:30+07:00")
        w = self.propose(hoctap=[lab], canhan=[remind])
        self.assertEqual(w["days"]["2026-11-04"]["office"], ["09:00", "13:00"])
        office_vs = [c for c in w["conflicts"] if "_office:2026-11-04" in (c["a"], c["b"])]
        self.assertFalse([c for c in office_vs if "Kiểm tra file" in (c["a_title"], c["b_title"])],
                         "sự kiện ngắn ≤ 30' không làm hỏng ngày văn phòng")

    def test_personal_event_inside_office_is_a_note_not_a_block(self):
        talk = item(id="talk", domain="canhan", kind="event", title="Buổi nói chuyện", start="2026-11-04T15:00+07:00",
                    end="2026-11-04T16:00+07:00")
        w = self.propose(canhan=[talk])
        self.assertEqual(w["days"]["2026-11-04"]["office"], ["09:00", "18:00"])   # không tự bỏ văn phòng
        c = next(c for c in w["conflicts"] if "Buổi nói chuyện" in (c["a_title"], c["b_title"]))
        self.assertEqual(c["severity"], lichtong.NOTE)   # báo Khôi quyết, không chặn


class UnifiedConflicts(LichTongBase):
    def test_hand_edited_plan_is_caught(self):
        # Kế hoạch bị sửa tay (gym 6–8 + chạy sáng đè lớp 7–9) — trước 0.5.0 không báo gì.
        self.write_domains(hoctap=[klass("c1", "Lớp A", "2026-11-03T07:00+07:00", "2026-11-03T08:50+07:00")])
        self.set_week({"2026-11-03": {"label": "Thứ 3, 03/11", "office": None,
                                      "training": {"type": "gym", "label": "Gym: PULL", "start": "06:00", "end": "08:00"}}})
        found = lichtong.conflicts([date(2026, 11, 3)], self.cfg)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "cao")
        self.assertIn("Gym: PULL", found[0]["text"])
        self.assertIn("_train:2026-11-03", found[0]["movable"])
        # digest cũ chỉ so lịch với lịch nên không thấy; lịch tổng thì thấy
        d = digest.build(t=parse_dt("2026-11-02T20:00+07:00"), cfg=self.cfg)
        self.assertEqual(d["conflicts"], [])
        self.assertEqual(len(d["conflicts_lifeos"]), 1)

    def test_same_event_on_two_calendars_is_not_a_conflict(self):
        a = klass("a", "Lớp A", "2026-11-04T09:00+07:00", "2026-11-04T10:00+07:00")
        b = item(id="b", domain="canhan", kind="event", title="lớp a", start="2026-11-04T09:00+07:00", end="2026-11-04T10:00+07:00")
        self.write_domains(hoctap=[a], canhan=[b])
        self.assertEqual(lichtong.conflicts([WED], self.cfg), [])

    def test_all_day_event_does_not_block(self):
        self.write_domains(canhan=[item(id="d", domain="canhan", kind="event", title="Cả ngày", start="2026-11-04", end="2026-11-05")])
        self.assertEqual(lichtong.events_for(WED, self.cfg), [])

    def test_try_event(self):
        self.propose()
        res = lichtong.try_event(parse_dt("2026-11-04T06:30+07:00"), parse_dt("2026-11-04T07:30+07:00"), "Họp thử", self.cfg)
        self.assertFalse(res["ok"])
        self.assertIn("Gym: PULL", res["text"][0])
        free = lichtong.try_event(parse_dt("2026-11-04T20:30+07:00"), parse_dt("2026-11-04T21:00+07:00"), "Rảnh", self.cfg)
        self.assertTrue(free["ok"])

    def test_plan_block_vs_class(self):
        self.write_domains(hoctap=[klass("c1", "Lớp A", "2026-11-03T18:00+07:00", "2026-11-03T20:00+07:00")])
        tracking.plan_add(date(2026, 11, 3), "Việc X", "19:00", "Mở file", minutes=60)
        found = lichtong.conflicts([date(2026, 11, 3)], self.cfg)
        self.assertEqual([c["severity"] for c in found], ["cao"])
        self.assertIn("_plan:2026-11-03:1", found[0]["movable"])


class ConfirmNeedsNoConflict(LichTongBase):
    def conflicted_week(self):
        self.write_domains(hoctap=[klass("c1", "Lớp A", "2026-11-03T07:00+07:00", "2026-11-03T08:50+07:00")])
        self.set_week({"2026-11-03": {"label": "Thứ 3, 03/11", "office": None,
                                      "training": {"type": "gym", "label": "Gym: PULL", "start": "06:00", "end": "08:00"}},
                       "2026-11-04": {"label": "Thứ 4, 04/11", "office": None,
                                      "training": {"type": "gym", "label": "Gym: PUSH", "start": "06:00", "end": "08:00"}}})

    def test_ok_from_khoi_is_refused_while_conflicts_remain(self):
        self.conflicted_week()
        res = week.confirm(self.cfg)
        self.assertFalse(res["ok"])
        self.assertFalse(week.show()["confirmed"])
        self.assertEqual(main(["week", "confirm"]), 1)   # mã thoát 1 → bot biết không được ghi lịch

    def test_khoi_can_insist(self):
        self.conflicted_week()
        res = week.confirm(self.cfg, allow_conflicts=True)
        self.assertTrue(res["ok"])
        self.assertTrue(week.show()["confirmed"])

    def test_silent_auto_drops_conflicting_training_only(self):
        self.conflicted_week()
        res = week.confirm(self.cfg, auto=True)
        self.assertTrue(res["ok"])
        days = week.show()["days"]
        self.assertIsNone(days["2026-11-03"]["training"])
        self.assertIn("bỏ vì trùng", days["2026-11-03"]["training_note"])
        self.assertEqual(days["2026-11-04"]["training"]["label"], "Gym: PUSH")   # ngày không trùng giữ nguyên
        self.assertEqual([d["date"] for d in res["dropped"]], ["2026-11-03"])
        self.assertEqual(res["remaining_conflicts"], [])

    def test_clean_week_confirms(self):
        self.propose()
        self.assertTrue(week.confirm(self.cfg)["ok"])


class WeekTrainCommand(LichTongBase):
    def test_change_weekly_training_with_auto_placement(self):
        self.propose()
        # "tuần này nghỉ chạy, tập PPL": T3 (vốn là chạy) đổi sang gym
        out = week.train_day(date(2026, 11, 3), self.cfg, "gym", "Gym: PUSH")
        self.assertEqual(out["days"]["2026-11-03"]["training"], {"type": "gym", "label": "Gym: PUSH", "start": "06:00", "end": "08:00"})
        self.assertTrue(out["day_ok"])
        self.assertIn("lời Khôi", out["days"]["2026-11-03"]["training_note"])

    def test_auto_placement_dodges_class(self):
        self.propose(hoctap=[klass("c1", "Lớp A", "2026-11-03T07:00+07:00", "2026-11-03T08:50+07:00")])
        out = week.train_day(date(2026, 11, 3), self.cfg, "gym", "Gym: PUSH")
        self.assertEqual(out["days"]["2026-11-03"]["training"]["start"], "18:15")
        self.assertTrue(out["day_ok"])

    def test_explicit_time_that_conflicts_is_reported(self):
        self.propose(hoctap=[klass("c1", "Lớp A", "2026-11-03T07:00+07:00", "2026-11-03T08:50+07:00")])
        out = week.train_day(date(2026, 11, 3), self.cfg, "gym", "Gym: PUSH", "06:00-08:00")
        self.assertFalse(out["day_ok"])
        self.assertTrue(out["day_conflicts"])

    def test_set_training_time_reports_conflicts(self):
        self.propose(hoctap=[klass("c1", "Lớp A", "2026-11-04T17:00+07:00", "2026-11-04T19:00+07:00")])
        out = week.set_day(WED, self.cfg, training="17:30-19:30")
        self.assertFalse(out["day_ok"])

    def test_cli_train_and_errors(self):
        self.propose()
        self.assertEqual(main(["week", "train", "2026-11-03", "--type", "gym", "--label", "Gym: PUSH"]), 0)
        self.assertEqual(main(["week", "train", "2026-12-25", "--type", "gym", "--label", "Gym: PUSH"]), 1)  # ngoài kế hoạch tuần


class PlanChecks(LichTongBase):
    def setUp(self):
        super().setUp()
        self.day = date(2026, 11, 3)
        self.write_domains(hoctap=[klass("c1", "Lớp A", "2026-11-03T17:00+07:00", "2026-11-03T19:00+07:00")])

    def test_confirm_refuses_overlapping_block(self):
        tracking.plan_add(self.day, "Việc X", "18:00", "Mở file", minutes=60)
        with self.assertRaises(tracking.PlanConflict) as cm:
            tracking.plan_confirm(self.day, cfg=self.cfg)
        self.assertTrue(cm.exception.conflicts)
        self.assertFalse(any(r.get("confirmed") for r in tracking.plan_list(self.day)))
        tracking.plan_confirm(self.day, cfg=self.cfg, allow_conflicts=True)
        self.assertTrue(tracking.plan_list(self.day)[0]["confirmed"])

    def test_auto_confirm_drops_overlapping_block_and_says_why(self):
        tracking.plan_add(self.day, "Việc X", "18:00", "Mở file", minutes=60)
        tracking.plan_add(self.day, "Việc Y", "20:30", "Mở file", minutes=30)
        tracking.plan_confirm(self.day, auto=True, cfg=self.cfg)
        self.assertEqual([r["title"] for r in tracking.plan_list(self.day)], ["Việc Y"])
        self.assertEqual([d["title"] for d in tracking.plan_dropped(self.day)], ["Việc X"])

    def test_edit_into_busy_time_is_refused_and_reverted(self):
        tracking.plan_add(self.day, "Việc X", "20:30", "Mở file", minutes=60)
        with self.assertRaises(tracking.PlanConflict):
            tracking.plan_edit(self.day, 1, at="18:00", cfg=self.cfg)
        self.assertEqual(tracking.plan_list(self.day)[0]["at"], "20:30")
        tracking.plan_edit(self.day, 1, at="18:00", cfg=self.cfg, force=True)   # Khôi nói giữ nguyên
        self.assertEqual(tracking.plan_list(self.day)[0]["at"], "18:00")

    def test_pending_is_a_cheap_check(self):
        import io
        from contextlib import redirect_stdout
        tracking.plan_add(self.day, "Việc Y", "20:30", "Mở file", minutes=30)

        def run(*argv):
            buf = io.StringIO()
            with redirect_stdout(buf):
                main(list(argv))
            return json.loads(buf.getvalue())

        self.assertTrue(run("plan", "pending", "--for", "2026-11-03")["need_confirm"])
        tracking.plan_confirm(self.day, cfg=self.cfg)
        self.assertFalse(run("plan", "pending", "--for", "2026-11-03")["need_confirm"])
        self.assertFalse(run("plan", "pending", "--for", "2026-11-09")["need_confirm"])   # ngày không có ô nào


class WakeAndDeadlineLabels(LichTongBase):
    def test_date_only_exam_does_not_push_wake_to_23h(self):
        # Chuyện thật 0.4.0: "bài kiểm tra trên lớp" chỉ có ngày → đọc thành 00:00 → "Dậy 23:00" tối hôm trước.
        self.write_domains(hoctap=[item(id="kt", kind="exam", title="Kiểm tra trên lớp", start="2026-11-02")])
        wake = profile(date(2026, 11, 2), self.cfg)["wake"]
        self.assertEqual((wake.date(), f"{wake:%H:%M}"), (date(2026, 11, 2), "05:30"))   # T2 gym sáng

    def test_timed_exam_still_moves_wake_earlier(self):
        self.write_domains(hoctap=[item(id="kt", kind="exam", title="Kiểm tra", start="2026-11-03T06:30+07:00", end="2026-11-03T07:30+07:00")])
        self.assertEqual(f"{profile(date(2026, 11, 3), self.cfg)['wake']:%H:%M}", "05:30")

    def test_schema_rejects_date_only_class_or_exam(self):
        errs = validate_item(item(id="kt", kind="exam", title="Kiểm tra", start="2026-11-02"))
        self.assertTrue(any("GIỜ" in e for e in errs), errs)
        self.assertEqual(validate_item(item(id="kt", kind="exam", title="Kiểm tra", start="2026-11-02T13:00+07:00")), [])

    def test_midnight_deadline_label(self):
        self.assertEqual(vn_deadline(parse_dt("2026-11-06T00:00+07:00")), "hết ngày Thứ 5, 05/11 (00:00 Thứ 6, 06/11)")
        self.assertEqual(vn_deadline(parse_dt("2026-11-06T09:30+07:00")), "09:30 Thứ 6, 06/11")
        self.write_domains(hoctap=[item(id="b3", kind="deadline", title="Bài 3", due="2026-11-06T00:00+07:00")])
        d = digest.build(t=self.t, cfg=self.cfg)
        self.assertTrue(d["items"][0]["due_label"].startswith("hết ngày Thứ 5"))

    def test_deadline_at_midnight_is_not_planned_on_the_day_it_already_passed(self):
        from lifeos import planner
        self.write_domains(hoctap=[item(id="b3", kind="deadline", title="Bài 3", due="2026-11-06T00:00+07:00", est_minutes=60)])
        t = parse_dt("2026-11-05T21:00+07:00")
        digest.build(t=t, cfg=self.cfg)
        thu = planner.suggest(date(2026, 11, 5), self.cfg, t=t)
        fri = planner.suggest(date(2026, 11, 6), self.cfg, t=t)
        self.assertIn("Bài 3", [b["title"] for b in thu["blocks"]])
        self.assertNotIn("Bài 3", [b["title"] for b in fri["blocks"]])


class PageChangedFlag(LichTongBase):
    def test_only_republish_when_content_changed(self):
        self.assertTrue(page_changed("k", "# A\n_Cập nhật 05:30_\nnội dung"))
        self.assertTrue(page_changed("k", "# A\n_Cập nhật 05:30_\nnội dung", mark=True))   # bot đăng xong
        self.assertFalse(page_changed("k", "# A\n_Cập nhật 21:00_\nnội dung"), "chỉ khác giờ cập nhật")
        self.assertTrue(page_changed("k", "# A\n_Cập nhật 21:00_\nnội dung mới"))

    def test_unpublished_changes_stay_pending(self):
        # "xong 1" ghi file nhưng bot chưa đăng → lần sau vẫn phải báo changed (không mark thì không coi là đã đăng)
        page_changed("k", "bản 1", mark=True)
        self.assertTrue(page_changed("k", "bản 2"))
        self.assertTrue(page_changed("k", "bản 2"))

    def test_dashboard_page_reports_changed(self):
        first = dashboard.build_page(self.cfg)
        self.assertTrue(first["changed"])
        dashboard.build_page(self.cfg, mark=True)
        self.assertFalse(dashboard.build_page(self.cfg)["changed"])

    def test_week_calendar_svg_and_page_list_conflicts(self):
        self.write_domains(hoctap=[klass("c1", "Lớp A", "2026-11-03T07:00+07:00", "2026-11-03T08:50+07:00")])
        self.set_week({"2026-11-03": {"label": "Thứ 3, 03/11", "office": None,
                                      "training": {"type": "gym", "label": "Gym: PULL", "start": "06:00", "end": "08:00"}}})
        dashboard.build(cfg=self.cfg)
        html_doc = (self.tmp / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Lịch tổng tuần này", html_doc)
        self.assertIn("Gym: PULL", html_doc)
        page = (self.tmp / "dashboard" / "page.md").read_text(encoding="utf-8")
        self.assertIn("Đang trùng lịch", page)
        self.assertIn("🔴", page)


class CliLichTong(LichTongBase):
    def test_check_exit_code(self):
        self.write_domains(hoctap=[klass("c1", "Lớp A", "2026-11-03T07:00+07:00", "2026-11-03T08:50+07:00")])
        self.set_week({"2026-11-03": {"label": "Thứ 3, 03/11", "office": None,
                                      "training": {"type": "gym", "label": "Gym: PULL", "start": "06:00", "end": "08:00"}}})
        self.assertEqual(main(["lichtong", "check", "--date", "2026-11-03", "--days", "1"]), 1)
        self.assertEqual(main(["lichtong", "check", "--date", "2026-11-04", "--days", "1"]), 0)
        self.assertEqual(main(["lichtong", "show", "--date", "2026-11-03", "--days", "2"]), 0)
        self.assertEqual(main(["lichtong", "try", "--start", "2026-11-03T20:00", "--end", "2026-11-03T21:00", "--title", "Thử"]), 0)
        self.assertEqual(main(["lichtong", "try", "--start", "2026-11-03T21:00", "--end", "2026-11-03T20:00"]), 1)


if __name__ == "__main__":
    import unittest
    unittest.main()
