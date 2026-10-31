"""Kế hoạch tuần (Chủ nhật 20:00): lịch văn phòng T2–T7 + buổi tập + việc lớn trong tuần.

    python3 -m lifeos week propose            # đề xuất cho tuần tới (từ Thứ 2 kế tiếp)
    python3 -m lifeos week show
    python3 -m lifeos week set 2026-11-04 --office 09:00-12:00   # hoặc --office none
    python3 -m lifeos week set 2026-11-05 --training none
    python3 -m lifeos week confirm             # Khôi "ok"
    python3 -m lifeos week company-written     # LifeOS đã ghi Office lên lịch công ty
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from . import agenda, urgency
from .common import iso, now, parse_dt, path, read_json, vn_date, write_json
from .daymodel import hm, training_label
from .tracking import all_items

DEADLINE_KINDS = {"deadline", "quiz", "registration", "payment", "exam"}


def next_monday(t: datetime) -> date:
    d = t.date()
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def _fmt(dt: datetime) -> str:
    return f"{dt:%H:%M}"


def _office_for_day(day: date, items: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[list[str] | None, str | None]:
    """Khung văn phòng trong 9–18 sau khi trừ giờ học/thi (+ di chuyển). Ngày có thi/kiểm tra → nghỉ."""
    off = cfg.get("office", {})
    if day.isoweekday() not in off.get("days", [1, 2, 3, 4, 5, 6]):
        return None, None
    day_items = [it for it in agenda.timed_items(items) if parse_dt(it["start"]).date() == day]
    if any(it["kind"] == "exam" for it in day_items):
        return None, "có thi/kiểm tra"
    a, b = (hm(x, day) for x in off.get("hours", ["09:00", "18:00"]))
    travel = timedelta(minutes=int(cfg.get("schedule", {}).get("travel_minutes", 30)))
    busy = sorted((parse_dt(it["start"]) - travel, parse_dt(it["end"]) + travel)
                  for it in day_items if it["kind"] == "class")
    windows, cursor = [], a
    for s, e in busy:
        if s > cursor:
            windows.append((cursor, min(s, b)))
        cursor = max(cursor, e)
    if cursor < b:
        windows.append((cursor, b))
    windows = [(s, e) for s, e in windows if e > s]
    if not windows:
        return None, "kín lịch học"
    s, e = max(windows, key=lambda w: w[1] - w[0])
    if (e - s) < timedelta(hours=off.get("min_hours", 4)):
        return None, "khung trống quá ngắn"
    note = "sau giờ học" if busy and s > a else None
    return [_fmt(s), _fmt(e)], note


def _training_for_day(day: date, office: list[str] | None, items: list[dict[str, Any]],
                      cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    tr = cfg.get("training", {})
    lab = training_label(day, cfg)
    if not lab:
        return None, None
    kind, label = lab
    day_events = [it for it in agenda.timed_items(items) if parse_dt(it["start"]).date() == day]
    if kind == "gym":
        s, e = tr.get("gym_time", ["06:00", "08:00"])
        return {"type": "gym", "label": label, "start": s, "end": e}, None

    keyword = tr.get("group_run_keyword", "").casefold()
    if keyword:
        group = next((it for it in day_events if keyword in it["title"].casefold() and not it.get("needs_reply")), None)
        if group:
            return {"type": "run", "label": f"Chạy nhóm: {group['title']}", "start": _fmt(parse_dt(group["start"])),
                    "end": _fmt(parse_dt(group["end"])), "group_event_id": group["id"]}, f"thay {label} bằng buổi chạy nhóm"
    minutes = int(tr.get("run_minutes", {}).get(str(day.isoweekday()), 60))
    start_hm = tr.get("run_start_office_day", "18:15") if office and office[1] >= "18:00" else tr.get("run_start_free_day", "17:00")
    start = hm(start_hm, day)
    latest = hm(tr.get("run_latest_end", "21:00"), day)
    # dời sau các sự kiện ưu tiên cao hơn (lớp, thi, sự kiện đã có trên lịch) nếu đè
    for it in sorted(day_events, key=lambda x: x["start"]):
        s, e = parse_dt(it["start"]), parse_dt(it["end"])
        if s < start + timedelta(minutes=minutes) and e > start:
            start = e + timedelta(minutes=15)
    if start + timedelta(minutes=minutes) > latest:
        return None, f"không còn giờ cho {label} — bỏ buổi này"
    return {"type": "run", "label": label, "start": _fmt(start),
            "end": _fmt(start + timedelta(minutes=minutes))}, None


def propose(start: date | None = None, cfg: dict[str, Any] | None = None, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    cfg = cfg or {}
    start = start or next_monday(t)
    items = all_items()
    days: dict[str, Any] = {}
    notes: list[str] = []
    for i in range(7):
        day = start + timedelta(days=i)
        office, why_off = _office_for_day(day, items, cfg)
        training, why_tr = _training_for_day(day, office, items, cfg)
        days[day.isoformat()] = {"label": vn_date(day), "office": office, "office_note": why_off,
                                 "training": training, "training_note": why_tr}
        for why in (why_off, why_tr):
            if why and day.isoweekday() in cfg.get("office", {}).get("days", [1, 2, 3, 4, 5, 6]):
                notes.append(f"{vn_date(day)}: {why}")

    end = datetime.combine(start + timedelta(days=7), datetime.min.time(), t.tzinfo)
    begin = datetime.combine(start, datetime.min.time(), t.tzinfo)
    digest = read_json(path("digest.json"), {}) or {}
    big = []
    for it in digest.get("items", []):
        due = urgency.due_dt(it)
        if it["kind"] in DEADLINE_KINDS and due and begin <= due < end:
            big.append({"id": it["id"], "title": it["title"], "kind": it["kind"], "due_label": it.get("due_label")})
    conflicts = [c for c in agenda.find_conflicts(items, begin, horizon_hours=24 * 7)
                 if parse_dt(c["overlap_start"]) < end]

    week = {"week_start": start.isoformat(), "proposed_at": iso(t), "confirmed": False,
            "company_written": False, "days": days, "big_items": big, "conflicts": conflicts, "notes": notes}
    write_json(path("state", "week.json"), week)
    return week


def show() -> dict[str, Any]:
    return read_json(path("state", "week.json"), {}) or {}


def _save(week: dict[str, Any]) -> dict[str, Any]:
    write_json(path("state", "week.json"), week)
    return week


def set_day(day: date, office: str | None = None, training: str | None = None) -> dict[str, Any]:
    """office: '09:00-12:00' hoặc 'none'. training: 'none' (bỏ buổi tập) hoặc '17:30-18:45' (dời giờ)."""
    week = show()
    entry = week.get("days", {}).get(day.isoformat())
    if entry is None:
        raise KeyError(f"{day} không nằm trong kế hoạch tuần hiện tại — chạy `week propose` trước.")
    if office is not None:
        entry["office"] = None if office == "none" else office.split("-")
        entry["office_changed_at"] = iso(now())
        entry["company_synced"] = False
    if training is not None:
        if training == "none":
            entry["training"] = None
        elif entry.get("training"):
            s, e = training.split("-")
            entry["training"].update(start=s, end=e)
    return _save(week)


def confirm(auto: bool = False) -> dict[str, Any]:
    week = show()
    week.update(confirmed=True, confirmed_at=iso(now()), auto_applied=auto)
    return _save(week)


def mark_company_written(day: date | None = None) -> dict[str, Any]:
    week = show()
    if day is None:
        week["company_written"] = True
        for entry in week.get("days", {}).values():
            entry["company_synced"] = True
    else:
        week["days"][day.isoformat()]["company_synced"] = True
    return _save(week)
