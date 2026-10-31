"""Đề xuất kế hoạch trong ngày: chọn việc cần làm và xếp vào khung trống thật.

    python3 -m lifeos plan suggest              # kế hoạch hôm nay (từ bây giờ)
    python3 -m lifeos plan suggest --for mai    # kế hoạch ngày mai (báo cáo 21:00)

Script chỉ chọn việc và xếp giờ. LifeOS viết "bước đầu tiên" cho từng khối, gửi Khôi,
rồi lưu từng khối bằng `plan add` (Khôi "ok" → `plan confirm`).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from . import agenda, urgency
from .common import VN, iso, now, path, read_json
from .tracking import all_items, plan_list

# Thời lượng mặc định (phút) khi nguồn không ghi est_minutes
DEFAULT_MINUTES = {
    "quiz": 20, "registration": 15, "payment": 15, "deadline": 90, "task": 30,
    "notice": 10, "email": 10, "message": 10,
}
ACTIONABLE = set(DEFAULT_MINUTES)
QUICK_KINDS = {"email", "message", "notice", "payment", "registration"}
MAX_BLOCK = 120  # việc dài hơn thì chỉ xếp một phiên 2 tiếng, phần còn lại để hôm sau


def _minutes(it: dict[str, Any]) -> int:
    return it.get("est_minutes") or DEFAULT_MINUTES.get(it["kind"], 30)


def _candidates(items: list[dict[str, Any]], day: date) -> list[dict[str, Any]]:
    """Việc nên làm trong ngày `day`: hạn trong 3 ngày tới, 🔴, cần trả lời, hoặc 🟠 không có hạn.
    Việc 🟠 chỉ vì "mới xuất hiện" mà hạn còn xa thì chưa xếp (báo cáo vẫn liệt kê)."""
    horizon = datetime.combine(day, time(23, 59), VN) + timedelta(days=3)
    out = []
    for it in items:
        if it["kind"] not in ACTIONABLE:
            continue
        due = urgency.due_dt(it)
        if due and due < datetime.combine(day, time(0, 0), VN):
            continue  # đã quá hạn từ trước ngày này: báo cáo nhắc riêng, không xếp lịch
        level = it.get("level", 4)
        if (due and due <= horizon) or level == urgency.RED or it.get("needs_reply") or (due is None and level <= urgency.ORANGE):
            out.append(it)
    out.sort(key=lambda x: (x.get("level", 4), urgency.due_dt(x) or horizon + timedelta(days=30)))
    return out


def suggest(day: date | None = None, max_main: int = 3, cfg: dict[str, Any] | None = None,
            t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    day = day or t.date()
    cfg = cfg or {}
    digest = read_json(path("digest.json"), {}) or {}
    ranked = digest.get("items", [])
    events = all_items()

    not_before = None
    if day == t.date():
        # bắt đầu sớm nhất 15 phút sau bây giờ, làm tròn lên mốc 15 phút kế tiếp
        start = (t + timedelta(minutes=15)).replace(second=0, microsecond=0)
        not_before = start + timedelta(minutes=(-start.minute) % 15)
    slots = [list(s) for s in agenda.free_slots(events, day, cfg, min_minutes=10, not_before=not_before)]

    already = {p.get("item_id") for p in plan_list(day) if p.get("item_id")}
    cands = [c for c in _candidates(ranked, day) if c["id"] not in already]
    quick = [c for c in cands if c["kind"] in QUICK_KINDS]
    main = [c for c in cands if c["kind"] not in QUICK_KINDS][:max_main]

    blocks, unplaced = [], []

    def place(title: str, minutes: int, items: list[dict[str, Any]], deadline: datetime | None) -> bool:
        need = timedelta(minutes=minutes)
        for slot in slots:
            s, e = slot
            if e - s < need:
                continue
            if deadline and s + need > deadline:
                continue
            blocks.append({"start": iso(s), "end": iso(s + need), "minutes": minutes, "title": title,
                           "items": [{k: it.get(k) for k in ("id", "title", "kind", "level_label", "due_label", "url", "from")} for it in items]})
            slot[0] = s + need + timedelta(minutes=10)  # nghỉ 10 phút giữa các việc
            return True
        return False

    # Việc nhanh (trả lời tin, đọc thông báo) xếp TRƯỚC: ngắn, dễ bắt đầu, người khác đang chờ.
    if quick:
        mins = min(sum(_minutes(q) for q in quick), 45)
        earliest_due = min((urgency.due_dt(q) for q in quick if urgency.due_dt(q)), default=None)
        if not place("Việc nhanh gộp lại", mins, quick, earliest_due):
            unplaced += [{"id": q["id"], "title": q["title"], "why": "không còn khung trống"} for q in quick]
    for it in main:
        mins = min(_minutes(it), MAX_BLOCK)
        if not place(it["title"], mins, [it], urgency.due_dt(it)):
            unplaced.append({"id": it["id"], "title": it["title"], "why": "không còn khung trống đủ dài trước hạn"})
        elif _minutes(it) > MAX_BLOCK:
            blocks[-1]["note"] = f"việc dài ~{_minutes(it)} phút: hôm nay làm phiên đầu {MAX_BLOCK} phút"

    blocks.sort(key=lambda b: b["start"])
    free_left = sum(int((e - s).total_seconds() // 60) for s, e in slots if e > s)
    return {"date": day.isoformat(), "blocks": blocks, "unplaced": unplaced,
            "free_minutes_left": free_left, "already_planned": sorted(x for x in already if x)}
