"""Trùng lịch giữa các mảng và tìm khung trống — tính bằng code, chính xác đến phút."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Iterable

from .common import VN, parse_dt
from .urgency import SCHEDULE_KINDS

Interval = tuple[datetime, datetime]


def timed_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for it in items:
        if it["kind"] in SCHEDULE_KINDS and it.get("start") and it.get("end") and it["status"] == "open":
            out.append(it)
    return out


def _same_event(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Cùng một sự kiện xuất hiện ở hai lịch (ví dụ lịch trường và lịch cá nhân) thì không tính là trùng."""
    return (
        a["start"] == b["start"]
        and a["end"] == b["end"]
        and a["title"].strip().casefold() == b["title"].strip().casefold()
    )


def find_conflicts(items: Iterable[dict[str, Any]], now: datetime, horizon_hours: int = 48) -> list[dict[str, Any]]:
    """Các cặp sự kiện chồng giờ nhau, có ít nhất một cái bắt đầu trong `horizon_hours` tới."""
    events = sorted(timed_items(items), key=lambda it: parse_dt(it["start"]))
    limit = now + timedelta(hours=horizon_hours)
    conflicts = []
    for i, a in enumerate(events):
        a_start, a_end = parse_dt(a["start"]), parse_dt(a["end"])
        for b in events[i + 1:]:
            b_start, b_end = parse_dt(b["start"]), parse_dt(b["end"])
            if b_start >= a_end:
                break
            if _same_event(a, b) or a["id"] == b["id"]:
                continue
            overlap_start, overlap_end = max(a_start, b_start), min(a_end, b_end)
            if overlap_end <= now or overlap_start > limit:
                continue
            conflicts.append({
                "a": a["id"],
                "b": b["id"],
                "a_title": a["title"],
                "b_title": b["title"],
                "a_domain": a["domain"],
                "b_domain": b["domain"],
                "overlap_start": overlap_start.isoformat(timespec="minutes"),
                "overlap_end": overlap_end.isoformat(timespec="minutes"),
            })
    return conflicts


def _hm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


def busy_intervals(items: Iterable[dict[str, Any]], day: date, cfg: dict[str, Any]) -> list[Interval]:
    """Khoảng bận trong ngày: sự kiện lịch + thời gian di chuyển + khung giờ được bảo vệ."""
    sched = cfg.get("schedule", {})
    travel = timedelta(minutes=int(sched.get("travel_minutes", 30)))
    travel_kinds = set(sched.get("travel_kinds", ["class", "exam", "work_shift"]))
    day_start = datetime.combine(day, time(0, 0), VN)
    day_end = day_start + timedelta(days=1)
    busy: list[Interval] = []
    for it in timed_items(items):
        start, end = parse_dt(it["start"]), parse_dt(it["end"])
        if it["kind"] in travel_kinds:
            start, end = start - travel, end + travel
        if end > day_start and start < day_end:
            busy.append((max(start, day_start), min(end, day_end)))
    for block in sched.get("protected", []):
        if block.get("weekdays") and day.isoweekday() not in block["weekdays"]:
            continue
        busy.append((datetime.combine(day, _hm(block["from"]), VN), datetime.combine(day, _hm(block["to"]), VN)))
    return _merge(busy)


def _merge(intervals: list[Interval]) -> list[Interval]:
    merged: list[Interval] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def free_slots(
    items: Iterable[dict[str, Any]],
    day: date,
    cfg: dict[str, Any],
    min_minutes: int = 15,
    not_before: datetime | None = None,
) -> list[Interval]:
    """Khung trống trong giờ hoạt động (mặc định 07:00–23:00) đủ dài ít nhất `min_minutes`."""
    sched = cfg.get("schedule", {})
    window_start = datetime.combine(day, _hm(sched.get("active_from", "07:00")), VN)
    window_end = datetime.combine(day, _hm(sched.get("active_to", "23:00")), VN)
    if not_before and not_before > window_start:
        window_start = not_before
    cursor = window_start
    slots: list[Interval] = []
    for b_start, b_end in busy_intervals(items, day, cfg):
        if b_start > cursor:
            slots.append((cursor, min(b_start, window_end)))
        cursor = max(cursor, b_end)
        if cursor >= window_end:
            break
    if cursor < window_end:
        slots.append((cursor, window_end))
    need = timedelta(minutes=min_minutes)
    return [(s, e) for s, e in slots if e - s >= need]


def is_busy(items: Iterable[dict[str, Any]], at: datetime, cfg: dict[str, Any]) -> bool:
    """Giờ `at` có rơi vào giờ học/làm/sự kiện không (để không đặt báo thức vào đó — quy tắc R2)."""
    return any(s <= at < e for s, e in busy_intervals(items, at.date(), cfg))
