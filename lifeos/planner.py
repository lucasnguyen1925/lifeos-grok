"""Kế hoạch trong ngày: chọn việc theo thang ưu tiên và xếp vào khung trống thật.

    python3 -m lifeos plan suggest --for mai     # báo cáo 21:00 (kế hoạch chính)
    python3 -m lifeos plan suggest --for today   # báo cáo 5:30 khi tối qua chưa có kế hoạch / chen việc gấp mới
    python3 -m lifeos plan timeline --for today  # dòng thời gian cả ngày (lịch cố định + kế hoạch đã lưu)

Thang ưu tiên: 1 thi/lịch học (cố định) · 2 việc học hạn ≤ 48h + 2 buổi ôn cuối · 3 văn phòng + việc công ty có hạn
· 4 ôn tập, việc học còn xa · 5 gym/chạy (cố định theo tuần) · 6 đi chơi (sự kiện trên lịch).
Script chỉ chọn việc và xếp giờ; LifeOS viết "▶ bước đầu tiên" cho từng ô 📝.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, time, timedelta
from typing import Any

from . import agenda, lichtong, urgency
from .common import VN, iso, now, parse_dt, path, read_json
from .daymodel import is_morning, profile, synthetic_events
from .tracking import all_items, plan_list

DEFAULT_MINUTES = {
    "quiz": 20, "registration": 15, "payment": 15, "deadline": 90, "task": 30,
    "notice": 10, "email": 10, "message": 10,
}
ACTIONABLE = set(DEFAULT_MINUTES)
QUICK_KINDS = {"email", "message", "notice", "payment", "registration"}
MAX_BLOCK = 120
ICONS = {"class": "🏫", "exam": "🏫", "work_shift": "🏢", "meeting": "👥", "event": "📌", "gym": "🏋️", "run": "🏃"}


def _minutes(it: dict[str, Any]) -> int:
    return it.get("est_minutes") or DEFAULT_MINUTES.get(it["kind"], 30)


def _tier(it: dict[str, Any], day_start: datetime, cfg: dict[str, Any]) -> int:
    if it.get("_prep_tier"):
        return it["_prep_tier"]
    due = urgency.due_dt(it)
    hours = cfg.get("priority", {}).get("academic_urgent_hours", 48)
    if it["domain"] == "hoctap":
        return 2 if due and due - day_start <= timedelta(hours=hours) else 4
    if it["domain"] == "congty" and due:
        return 3
    return 4


# ---------- buổi ôn thi ----------

def _exam_kind(it: dict[str, Any], cfg: dict[str, Any]) -> str:
    kw = cfg.get("exam_prep", {}).get("test", {}).get("keywords", ["kiểm tra", "giữa kỳ"])
    return "test" if any(k in it["title"].casefold() for k in kw) else "final"


def prep_sessions(day: date, items: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Buổi ôn rơi vào ngày `day`: chia đều trong cửa sổ trước ngày thi, buổi cuối là hôm trước."""
    ep = cfg.get("exam_prep", {})
    out = []
    for it in items:
        if it["kind"] != "exam" or it["status"] != "open" or not it.get("start"):
            continue
        exam_day = urgency.due_dt(it).date()
        kind = _exam_kind(it, cfg)
        rule = ep.get(kind, {"sessions": 3, "minutes": 90, "days_before": 5} if kind == "test"
                      else {"sessions": 6, "minutes": 90, "days_before": 14})
        n, window = rule["sessions"], rule["days_before"]
        first, last = exam_day - timedelta(days=window), exam_day - timedelta(days=1)
        span = (last - first).days
        if span < 0:
            continue
        targets = sorted({first + timedelta(days=round(i * span / max(n - 1, 1))) for i in range(n)})
        if day not in targets:
            continue
        k = targets.index(day) + 1
        light = k == len(targets)
        urgent = k > len(targets) - ep.get("urgent_last_sessions", 2)
        out.append({
            "id": f"prep:{it['id']}:{k}", "domain": "hoctap", "source": "prep", "kind": "task",
            "title": f"Ôn {it['title']} (buổi {k}/{len(targets)}{' · nhẹ: xem lại lỗi sai' if light else ''})",
            "status": "open", "est_minutes": 60 if light else rule["minutes"],
            "due": datetime.combine(exam_day, time(0, 0), VN).isoformat(), "_prep_tier": 2 if urgent else 4,
            "level": 2, "level_label": urgency.LABELS[urgency.ORANGE], "exam_id": it["id"],
        })
    return out


# ---------- chọn việc ----------

def _candidates(ranked: list[dict[str, Any]], day: date) -> list[dict[str, Any]]:
    horizon = datetime.combine(day, time(23, 59), VN) + timedelta(days=3)
    out = []
    for it in ranked:
        if it["kind"] not in ACTIONABLE:
            continue
        due = urgency.due_dt(it)
        if due and due <= datetime.combine(day, time(0, 0), VN):
            continue  # đã quá hạn (hạn đúng 00:00 = hết ngày hôm trước)
        level = it.get("level", 4)
        if (due and due <= horizon) or level == urgency.RED or it.get("needs_reply") or (due is None and level <= urgency.ORANGE):
            out.append(it)
    return out


def suggest(day: date | None = None, cfg: dict[str, Any] | None = None, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    day = day or t.date()
    cfg = cfg or {}
    prof = profile(day, cfg)
    digest = read_json(path("digest.json"), {}) or {}
    ranked = digest.get("items", [])
    items = all_items()
    events = items + synthetic_events(prof)
    day_start = datetime.combine(day, time(0, 0), VN)

    window_cfg = copy.deepcopy(cfg)
    sched = window_cfg.setdefault("schedule", {})
    sched["active_from"] = f"{prof['task_start']:%H:%M}"
    sched["active_to"] = "23:59" if prof["task_end"].date() > day else f"{prof['task_end']:%H:%M}"
    not_before = None
    if day == t.date():
        start = (t + timedelta(minutes=15)).replace(second=0, microsecond=0)
        not_before = start + timedelta(minutes=(-start.minute) % 15)
    slots = [list(s) for s in agenda.free_slots(events, day, window_cfg, min_minutes=10, not_before=not_before)]

    planned = plan_list(day)
    already = {p.get("item_id") for p in planned if p.get("item_id")}
    used_minutes = sum(p.get("minutes") or 0 for p in planned)
    used_blocks = len(planned)

    cands = [c for c in _candidates(ranked, day) + prep_sessions(day, items, cfg) if c["id"] not in already]
    for c in cands:
        c["_tier"] = _tier(c, day_start, cfg)
    cands.sort(key=lambda x: (x["_tier"], urgency.due_dt(x) or day_start + timedelta(days=60)))
    quick = [c for c in cands if c["kind"] in QUICK_KINDS]
    main = [c for c in cands if c["kind"] not in QUICK_KINDS]

    blocks, unplaced, overload, at_office = [], [], False, []

    # Việc công ty: ưu tiên làm trong giờ văn phòng. Chỉ xếp vào giờ riêng khi hạn rơi trước buổi văn phòng kế tiếp.
    def office_before_due(it: dict[str, Any]) -> str | None:
        due = urgency.due_dt(it)
        mins = timedelta(minutes=_minutes(it))
        for i in range(0, 7):
            d = day + timedelta(days=i)
            o = prof["office"] if i == 0 else profile(d, cfg)["office"]
            if o and (due is None or o[0] + mins <= due) and (i > 0 or o[1] > (not_before or o[0])):
                return "today" if i == 0 else d.isoformat()
            if due and datetime.combine(d, time(23, 59), VN) >= due:
                break
        return None

    keep = []
    for it in main:
        if it["domain"] == "congty":
            where = office_before_due(it)
            if where == "today":
                at_office.append({k: it.get(k) for k in ("id", "title", "due_label", "url")})
                continue
            if where:
                continue  # sẽ làm trong buổi văn phòng ngày khác
        keep.append(it)
    main = keep
    cap_min, cap_blocks = prof["capacity_minutes"], prof["capacity_blocks"]

    def place(title: str, minutes: int, its: list[dict[str, Any]], deadline: datetime | None, tier: int) -> bool:
        need = timedelta(minutes=minutes)
        for slot in slots:
            s, e = slot
            if e - s < need or (deadline and s + need > deadline):
                continue
            blocks.append({"start": iso(s), "end": iso(s + need), "minutes": minutes, "title": title, "tier": tier,
                           "items": [{k: it.get(k) for k in ("id", "title", "kind", "level_label", "due_label", "url", "from", "exam_id")}
                                     for it in its]})
            slot[0] = s + need + timedelta(minutes=10)
            return True
        return False

    def must_do_today(it: dict[str, Any]) -> bool:
        due = urgency.due_dt(it)
        return it.get("level") == urgency.RED and due is not None and due.date() == day

    if quick:
        mins = min(sum(_minutes(q) for q in quick), 45)
        earliest = min((urgency.due_dt(q) for q in quick if urgency.due_dt(q)), default=None)
        if place("Việc nhanh", mins, quick, earliest, min(q["_tier"] for q in quick)):
            used_minutes += mins
            used_blocks += 1
        else:
            unplaced += [{"id": q["id"], "title": q["title"], "why": "không còn khung trống"} for q in quick]

    for it in main:
        mins = min(_minutes(it), MAX_BLOCK)
        forced = must_do_today(it)
        if not forced and (used_minutes + mins > cap_min or used_blocks >= cap_blocks):
            unplaced.append({"id": it["id"], "title": it["title"], "why": "vượt giới hạn giờ việc hôm nay"})
            continue
        if place(it["title"], mins, [it], urgency.due_dt(it), it["_tier"]):
            used_minutes += mins
            used_blocks += 1
            if forced and (used_minutes > cap_min or used_blocks > cap_blocks):
                overload = True
            if _minutes(it) > MAX_BLOCK:
                blocks[-1]["note"] = f"việc dài ~{_minutes(it)} phút: hôm nay làm phiên đầu {MAX_BLOCK} phút"
        else:
            unplaced.append({"id": it["id"], "title": it["title"], "why": "không còn khung trống đủ dài trước hạn"})

    blocks.sort(key=lambda b: b["start"])
    return {
        "date": day.isoformat(), "day_type": prof["day_type"],
        "capacity_minutes": cap_min, "planned_minutes": used_minutes, "overload": overload,
        "blocks": blocks, "unplaced": unplaced, "at_office": at_office,
        "conflicts": lichtong.conflicts([day], cfg),  # lịch tổng: kể cả văn phòng/buổi tập/ô 📝 LifeOS tự xếp
        "timeline": timeline(day, cfg, extra_blocks=blocks),
    }


# ---------- dòng thời gian ----------

def timeline(day: date, cfg: dict[str, Any], extra_blocks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Cả ngày theo giờ: dậy, lịch học/thi, văn phòng, tập, sự kiện, ô 📝 đã lưu (+ ô đề xuất nếu có)."""
    prof = profile(day, cfg)
    rows = [{"start": f"{prof['wake']:%H:%M}", "end": None, "icon": "⏰", "title": "Dậy", "type": "wake",
             "alarm": prof["gym_day"]}]
    if prof["training"]:
        tr = prof["training"]
        rows.append({"start": tr["start"], "end": tr["end"], "icon": ICONS[tr["type"]], "title": tr["label"],
                     "type": "training", "alarm": tr["type"] == "gym" and is_morning(tr)})
    if prof["office"]:
        s, e = prof["office"]
        rows.append({"start": f"{s:%H:%M}", "end": f"{e:%H:%M}", "icon": "🏢", "title": "Văn phòng", "type": "office"})
    group_ids = {prof["training"].get("group_event_id")} if prof["training"] else set()
    for it in agenda.timed_items(all_items()):
        if it["id"] in group_ids:
            continue
        s, e = it["start"], it["end"]
        sd = parse_dt(s)
        if sd.date() != day:
            continue
        rows.append({"start": f"{sd:%H:%M}", "end": f"{parse_dt(e):%H:%M}", "icon": ICONS.get(it["kind"], "📌"),
                     "title": it["title"], "type": it["kind"], "location": it.get("location")})
    for p in plan_list(day):
        start = p["at"]
        end = None
        if p.get("minutes"):
            h, m = (int(x) for x in start.split(":"))
            end_dt = datetime.combine(day, time(h, m)) + timedelta(minutes=p["minutes"])
            end = f"{end_dt:%H:%M}"
        rows.append({"start": start, "end": end, "icon": "📝", "title": p["title"], "type": "plan",
                     "n": p["n"], "first_step": p.get("first_step"), "status": p["status"],
                     "confirmed": p.get("confirmed", False)})
    for b in extra_blocks or []:
        rows.append({"start": b["start"][11:16], "end": b["end"][11:16], "icon": "📝", "title": b["title"],
                     "type": "proposed", "items": b["items"], "note": b.get("note")})
    rows.sort(key=lambda r: r["start"])
    return rows
