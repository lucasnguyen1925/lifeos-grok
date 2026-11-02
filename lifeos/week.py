"""Kế hoạch tuần (Chủ nhật 20:00): lịch văn phòng T2–T7 + buổi tập + việc lớn trong tuần.

    python3 -m lifeos week propose            # đề xuất cho tuần tới (từ Thứ 2 kế tiếp)
    python3 -m lifeos week show
    python3 -m lifeos week set 2026-11-04 --office 09:00-12:00   # hoặc --office none
    python3 -m lifeos week set 2026-11-05 --training none        # hoặc --training 17:30-18:45 (dời giờ)
    python3 -m lifeos week train 2026-11-04 --type gym --label "Gym: PUSH"   # đổi buổi tập của một ngày (tự né lịch)
    python3 -m lifeos week confirm             # Khôi "ok" (từ chối nếu còn trùng mức "cao")
    python3 -m lifeos week company-written     # LifeOS đã ghi Office lên lịch công ty

MỌI thay đổi kế hoạch tuần phải đi qua các lệnh này — bot KHÔNG được sửa tay `state/week.json`
(sửa tay bỏ qua bước kiểm tra trùng lịch). Lịch tổng và mức trùng: xem `lichtong.py`.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from . import agenda, lichtong, urgency
from .common import iso, now, parse_dt, path, read_json, vn_date, write_json
from .daymodel import hm, training_label
from .tracking import all_items

DEADLINE_KINDS = {"deadline", "quiz", "registration", "payment", "exam"}


def next_monday(t: datetime) -> date:
    d = t.date()
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def _fmt(dt: datetime) -> str:
    return f"{dt:%H:%M}"


def _day_timed(items: list[dict[str, Any]], day: date) -> list[dict[str, Any]]:
    """Mục có giờ cụ thể bắt đầu trong ngày `day` (bỏ mục chỉ có ngày)."""
    return [it for it in agenda.timed_items(items) if "T" in it["start"] and "T" in it["end"]
            and parse_dt(it["start"]).date() == day]


def _padded(it: dict[str, Any], cfg: dict[str, Any]) -> tuple[datetime, datetime]:
    """Khoảng chiếm chỗ của một mục lịch; lớp/thi/ca làm cần thêm thời gian di chuyển hai đầu."""
    s, e = parse_dt(it["start"]), parse_dt(it["end"])
    if it["kind"] in lichtong._travel_kinds(cfg):
        return s - lichtong._travel(cfg), e + lichtong._travel(cfg)
    return s, e


def _hits(events: list[dict[str, Any]], start: datetime, end: datetime, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    return [it for it in events if _padded(it, cfg)[0] < end and _padded(it, cfg)[1] > start]


def _office_for_day(day: date, items: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[list[str] | None, str | None]:
    """Khung văn phòng trong 9–18 sau khi trừ giờ học/thi (+ di chuyển) và mọi sự kiện có giờ bên trường
    (thí nghiệm, họp nhóm…). Sự kiện cá nhân không tự trừ: nếu đè thì hiện trong `conflicts` để Khôi quyết."""
    off = cfg.get("office", {})
    if day.isoweekday() not in off.get("days", [1, 2, 3, 4, 5, 6]):
        return None, None
    day_items = _day_timed(items, day)
    if any(it["kind"] == "exam" for it in day_items):
        return None, "có thi/kiểm tra"
    a, b = (hm(x, day) for x in off.get("hours", ["09:00", "18:00"]))
    soft = lichtong._soft_minutes(cfg)
    busy = []
    for it in day_items:
        s, e = parse_dt(it["start"]), parse_dt(it["end"])
        if it["kind"] == "class":
            busy.append(_padded(it, cfg))
        elif it["domain"] == "hoctap" and it["kind"] in ("meeting", "event") and (e - s).total_seconds() / 60 > soft:
            busy.append((s, e))
    busy.sort()
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


def _evening(day: date, label: str, ttype: str, minutes: int, office: list[str] | None,
             day_events: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Xếp buổi tập vào buổi tối: sau văn phòng, dời sau các sự kiện đè (kèm di chuyển), không quá giờ muộn nhất."""
    tr = cfg.get("training", {})
    start_hm = tr.get("run_start_office_day", "18:15") if office and office[1] >= "18:00" else tr.get("run_start_free_day", "17:00")
    start = hm(start_hm, day)
    if office:
        start = max(start, hm(office[1], day) + timedelta(minutes=15))
    latest = hm(tr.get("run_latest_end", "21:00"), day)
    for it in sorted(day_events, key=lambda x: x["start"]):
        ps, pe = _padded(it, cfg)
        if ps < start + timedelta(minutes=minutes) and pe > start:
            start = pe if it["kind"] in lichtong._travel_kinds(cfg) else pe + timedelta(minutes=15)
    if start + timedelta(minutes=minutes) > latest:
        return None, f"không còn giờ cho {label} — bỏ buổi này"
    return {"type": ttype, "label": label, "start": _fmt(start), "end": _fmt(start + timedelta(minutes=minutes))}, None


def _place_training(day: date, ttype: str, label: str, office: list[str] | None, items: list[dict[str, Any]],
                    cfg: dict[str, Any], minutes: int | None = None) -> tuple[dict[str, Any] | None, str | None]:
    """Xếp một buổi tập vào ngày, TỰ NÉ lịch. Gym: sáng như cấu hình; sáng vướng lớp/thi/sự kiện → dời sang tối cùng
    ngày; tối cũng kín → bỏ buổi đó (kèm lý do). Chạy: luôn buổi tối."""
    tr = cfg.get("training", {})
    day_events = _day_timed(items, day)
    if ttype == "gym":
        s, e = tr.get("gym_time", ["06:00", "08:00"])
        start, end = hm(s, day), hm(e, day)
        hit = _hits(day_events, start, end, cfg)
        if not hit:
            return {"type": "gym", "label": label, "start": s, "end": e}, None
        length = int(minutes or tr.get("gym_evening_minutes", (end - start).total_seconds() // 60))
        placed, why = _evening(day, label, "gym", length, office, day_events, cfg)
        if placed is None:
            return None, f"sáng vướng {hit[0]['title']} và tối không còn giờ — bỏ {label}"
        return placed, f"sáng vướng {hit[0]['title']} → dời {label} sang tối"
    length = int(minutes or tr.get("run_minutes", {}).get(str(day.isoweekday()), 60))
    return _evening(day, label, "run", length, office, day_events, cfg)


def _training_for_day(day: date, office: list[str] | None, items: list[dict[str, Any]],
                      cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    tr = cfg.get("training", {})
    lab = training_label(day, cfg)
    if not lab:
        return None, None
    kind, label = lab
    if kind == "run":
        keyword = tr.get("group_run_keyword", "").casefold()
        if keyword:
            day_events = _day_timed(items, day)
            group = next((it for it in day_events if keyword in it["title"].casefold() and not it.get("needs_reply")), None)
            if group:
                return {"type": "run", "label": f"Chạy nhóm: {group['title']}", "start": _fmt(parse_dt(group["start"])),
                        "end": _fmt(parse_dt(group["end"])), "group_event_id": group["id"]}, f"thay {label} bằng buổi chạy nhóm"
    return _place_training(day, kind, label, office, items, cfg)


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

    week = {"week_start": start.isoformat(), "proposed_at": iso(t), "confirmed": False,
            "company_written": False, "days": days, "big_items": big, "conflicts": [], "notes": notes}
    write_json(path("state", "week.json"), week)  # lịch tổng đọc kế hoạch từ file → ghi trước rồi mới đối chiếu
    week["conflicts"] = lichtong.conflicts(_week_days(week), cfg)
    return _save(week)


def show() -> dict[str, Any]:
    return read_json(path("state", "week.json"), {}) or {}


def _save(week: dict[str, Any]) -> dict[str, Any]:
    write_json(path("state", "week.json"), week)
    return week


def _week_days(week: dict[str, Any]) -> list[date]:
    return [date.fromisoformat(k) for k in week.get("days", {})]


def set_day(day: date, cfg: dict[str, Any], office: str | None = None, training: str | None = None) -> dict[str, Any]:
    """office: '09:00-12:00' hoặc 'none'. training: 'none' (bỏ buổi tập) hoặc '17:30-18:45' (dời giờ).
    Kết quả kèm `day_conflicts`: chỗ trùng của ngày đó SAU khi sửa — có mức "cao" thì phải xử lý trước khi ghi lịch."""
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
    return _with_conflicts(_save(week), day, cfg)


def train_day(day: date, cfg: dict[str, Any], ttype: str, label: str, time_range: str | None = None,
              minutes: int | None = None) -> dict[str, Any]:
    """Đổi buổi tập của MỘT ngày trong kế hoạch tuần (ví dụ "tuần này nghỉ chạy, tập PPL").
    Không đưa `time_range` → script tự xếp giờ và né lớp/thi/sự kiện (gym sáng vướng thì dời tối, tối kín thì từ chối)."""
    if ttype not in ("gym", "run"):
        raise ValueError("type phải là gym hoặc run.")
    week = show()
    entry = week.get("days", {}).get(day.isoformat())
    if entry is None:
        raise KeyError(f"{day} không nằm trong kế hoạch tuần hiện tại — chạy `week propose` trước.")
    if time_range:
        s, e = time_range.split("-")
        training, note = {"type": ttype, "label": label, "start": s, "end": e}, None
    else:
        training, note = _place_training(day, ttype, label, entry.get("office"), all_items(), cfg, minutes)
        if training is None:
            raise ValueError(note or "Không xếp được buổi tập vào ngày này.")
    entry["training"] = training
    entry["training_note"] = "đổi theo lời Khôi" + (f" · {note}" if note else "")
    entry["training_changed_at"] = iso(now())
    return _with_conflicts(_save(week), day, cfg)


def _with_conflicts(week: dict[str, Any], day: date, cfg: dict[str, Any]) -> dict[str, Any]:
    found = lichtong.conflicts([day], cfg)
    out = dict(week)
    out["day_conflicts"] = found
    out["day_ok"] = not lichtong.high(found)
    return out


def confirm(cfg: dict[str, Any], auto: bool = False, allow_conflicts: bool = False) -> dict[str, Any]:
    """Khôi "ok" (hoặc 23:00 Chủ nhật tự áp dụng). Còn trùng mức "cao" thì:
      · Khôi "ok" → TỪ CHỐI (ok=false), LifeOS báo trùng và hỏi dời/bỏ; Khôi nói "giữ nguyên" → chạy lại với --allow-conflicts.
      · tự áp dụng khi im lặng → bỏ các buổi tập đang đè (ghi lý do trong `dropped`), KHÔNG ghi lịch có trùng."""
    week = show()
    found = lichtong.conflicts(_week_days(week), cfg)
    cao, dropped = lichtong.high(found), []
    if cao and not allow_conflicts:
        if not auto:
            return {"ok": False, "confirmed": False, "conflicts": cao,
                    "why": "Còn chỗ trùng lịch mức cao — báo Khôi, dời/bỏ rồi chốt lại (hoặc Khôi nói giữ nguyên → --allow-conflicts)."}
        for c in cao:
            for mid in c["movable"]:
                if mid.startswith("_train:"):
                    entry = week["days"].get(mid.split(":", 1)[1])
                    if entry and entry.get("training"):
                        dropped.append({"date": mid.split(":", 1)[1], "label": entry["training"]["label"], "why": c["text"]})
                        entry["training"] = None
                        entry["training_note"] = f"bỏ vì trùng lịch: {c['text']}"
        found = lichtong.conflicts(_week_days(_save(week)), cfg)
    week["conflicts"] = found
    week.update(confirmed=True, confirmed_at=iso(now()), auto_applied=auto, allowed_conflicts=bool(cao) and allow_conflicts)
    out = dict(_save(week))
    out.update(ok=True, dropped=dropped, remaining_conflicts=[c for c in found if c["severity"] == lichtong.HIGH])
    return out


def mark_company_written(day: date | None = None) -> dict[str, Any]:
    week = show()
    if day is None:
        week["company_written"] = True
        for entry in week.get("days", {}).values():
            entry["company_synced"] = True
    else:
        week["days"][day.isoformat()]["company_synced"] = True
    return _save(week)
