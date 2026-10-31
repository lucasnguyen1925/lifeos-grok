"""Mô hình một ngày của Khôi: giờ dậy, tập luyện, văn phòng, giờ ăn, giờ ngủ, giới hạn giờ việc.

Lịch văn phòng và lịch tập của từng ngày lấy từ kế hoạch tuần (state/week.json).
Chưa có kế hoạch tuần thì dùng mặc định trong config.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from .common import VN, path, read_json

FIXED_KINDS = {"class", "exam"}


def hm(value: str, day: date) -> datetime:
    """'18:15' → datetime trong ngày `day`; '24:00' → 00:00 ngày hôm sau."""
    h, m = (int(x) for x in value.split(":"))
    return datetime.combine(day, time(0, 0), VN) + timedelta(hours=h, minutes=m)


def week_entry(day: date) -> dict[str, Any] | None:
    week = read_json(path("state", "week.json"), {}) or {}
    return week.get("days", {}).get(day.isoformat())


def training_label(day: date, cfg: dict[str, Any]) -> tuple[str, str] | None:
    """('gym'|'run', nhãn) theo giáo án cố định trong config, hoặc None."""
    tr = cfg.get("training", {})
    key = str(day.isoweekday())
    if key in tr.get("gym", {}):
        return "gym", tr["gym"][key]
    if key in tr.get("run", {}):
        return "run", tr["run"][key]
    return None


def is_gym_day(day: date, cfg: dict[str, Any]) -> bool:
    entry = week_entry(day)
    if entry is not None:
        t = entry.get("training")
        return bool(t and t.get("type") == "gym")
    lab = training_label(day, cfg)
    return bool(lab and lab[0] == "gym")


def office_of(day: date, cfg: dict[str, Any]) -> tuple[datetime, datetime] | None:
    entry = week_entry(day)
    if entry is not None:
        o = entry.get("office")
        return (hm(o[0], day), hm(o[1], day)) if o else None
    off = cfg.get("office", {})
    if day.isoweekday() in off.get("days", [1, 2, 3, 4, 5, 6]):
        a, b = off.get("hours", ["09:00", "18:00"])
        return hm(a, day), hm(b, day)
    return None


def training_of(day: date, cfg: dict[str, Any]) -> dict[str, Any] | None:
    entry = week_entry(day)
    if entry is not None:
        t = entry.get("training")
        if not t:
            return None
        return {**t, "start_dt": hm(t["start"], day), "end_dt": hm(t["end"], day)}
    return None


def profile(day: date, cfg: dict[str, Any]) -> dict[str, Any]:
    d = cfg.get("day", {})
    gym = is_gym_day(day, cfg)
    office = office_of(day, cfg)
    training = training_of(day, cfg)

    wake = hm(d.get("wake_gym", "05:30") if gym else d.get("wake_normal", "07:00"), day)
    from .tracking import all_items  # tránh import vòng
    from .common import parse_dt
    first_fixed = min((parse_dt(it["start"]) for it in all_items()
                       if it["kind"] in FIXED_KINDS and it.get("start") and it["status"] == "open"
                       and parse_dt(it["start"]).date() == day), default=None)
    before = timedelta(minutes=d.get("wake_before_first_class", 60))
    if first_fixed and first_fixed - before < wake:
        wake = first_fixed - before
    if gym and training:
        task_start = training["end_dt"] + timedelta(minutes=d.get("first_task_after_gym", 15))
    else:
        task_start = wake + timedelta(minutes=d.get("first_task_after_wake", 30))

    next_gym = is_gym_day(day + timedelta(days=1), cfg)
    bedtime = hm(d.get("bedtime_before_gym", "23:30") if next_gym else d.get("bedtime", "24:00"), day)
    task_end = bedtime - timedelta(minutes=d.get("wind_down_minutes", 30))

    meals = [("Ăn trưa", *(hm(x, day) for x in d.get("lunch", ["12:00", "13:00"])))]
    dinner = [hm(x, day) for x in d.get("dinner", ["18:30", "19:30"])]
    if training and training.get("type") == "run" and training["end_dt"] > dinner[0]:
        start = training["end_dt"] + timedelta(minutes=15)
        dinner = [start, start + timedelta(minutes=d.get("dinner_after_run_minutes", 45))]
    meals.append(("Ăn tối", *dinner))

    office_minutes = int((office[1] - office[0]).total_seconds() // 60) if office else 0
    cap = cfg.get("capacity", {})
    if day.isoweekday() == 7:
        kind, c = "sunday", cap.get("sunday", {"minutes": 180, "blocks": 3})
    elif office_minutes >= 360:
        kind, c = "office_full", cap.get("office_full", {"minutes": 150, "blocks": 3})
    elif office_minutes > 0:
        kind, c = "office_half", cap.get("office_half", {"minutes": 240, "blocks": 4})
    else:
        kind, c = "no_office", cap.get("no_office", {"minutes": 300, "blocks": 5})

    return {
        "date": day, "gym_day": gym, "wake": wake, "task_start": task_start, "task_end": task_end,
        "bedtime": bedtime, "office": office, "training": training, "meals": meals,
        "day_type": kind, "capacity_minutes": c["minutes"], "capacity_blocks": c["blocks"],
    }


def synthetic_events(prof: dict[str, Any]) -> list[dict[str, Any]]:
    """Văn phòng, buổi tập, giờ ăn dưới dạng sự kiện để tính khung bận."""
    day = prof["date"].isoformat()
    evs = []
    if prof["office"]:
        s, e = prof["office"]
        evs.append({"id": f"_office:{day}", "domain": "congty", "source": "week", "kind": "work_shift",
                    "title": "Văn phòng", "status": "open", "start": s.isoformat(), "end": e.isoformat()})
    t = prof["training"]
    if t:
        rest = timedelta(minutes=15)  # nghỉ, tắm sau buổi tập
        evs.append({"id": f"_train:{day}", "domain": "canhan", "source": "week", "kind": "event",
                    "title": t["label"], "status": "open",
                    "start": t["start_dt"].isoformat(), "end": (t["end_dt"] + rest).isoformat()})
    for label, s, e in prof["meals"]:
        evs.append({"id": f"_meal:{day}:{label}", "domain": "canhan", "source": "day", "kind": "event",
                    "title": label, "status": "open", "start": s.isoformat(), "end": e.isoformat()})
    return evs
