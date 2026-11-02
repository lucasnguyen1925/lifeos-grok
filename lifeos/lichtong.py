"""Lịch tổng: MỘT nơi gom mọi thứ có giờ để đối chiếu — do script tính, bot không phải "nhìn" nhiều lịch.

Gồm hai lớp:
  · lớp "lich"   — mọi sự kiện có giờ từ các nguồn (lịch Google các tài khoản, lịch học/thi MyBK, lịch trường, lịch công ty…)
  · lớp "lifeos" — những gì LifeOS tự xếp: văn phòng, buổi tập (gym/chạy), ô 📝 trong kế hoạch ngày

    python3 -m lifeos lichtong show [--date HÔM-NAY] [--days 1]    # lịch tổng theo ngày/tuần + chỗ trùng
    python3 -m lifeos lichtong check [--date …] [--days 7]         # chỉ chỗ trùng (thoát mã 1 nếu có trùng mức "cao")
    python3 -m lifeos lichtong try --start 2026-11-04T15:00 --end 2026-11-04T16:00 --title "…"   # thử một sự kiện mới

Mức trùng:
  · "cao"   — buổi tập/ô 📝 đè giờ học, thi, sự kiện; văn phòng đè lớp/thi; hai thứ LifeOS tự xếp đè nhau.
              Phải xử lý (dời/bỏ) hoặc Khôi nói rõ "giữ nguyên" TRƯỚC khi ghi lên bất kỳ lịch nào.
  · "luu-y" — hai sự kiện trên lịch đè nhau (LifeOS không tự sửa được), hoặc văn phòng đè một sự kiện cá nhân/trường
              dài hơn `soft_event_minutes` (mặc định 30 phút; sự kiện ngắn kiểu nhắc việc không tính) → báo Khôi quyết.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Iterable

from . import agenda
from .common import VN, iso, parse_dt, vn_date
from .tracking import all_items, plan_list

FIXED, LIFEOS = "lich", "lifeos"
HIGH, NOTE = "cao", "luu-y"
DEFAULT_SOFT_MINUTES = 30


def _sched(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("schedule", {})


def _soft_minutes(cfg: dict[str, Any]) -> int:
    return int(_sched(cfg).get("soft_event_minutes", DEFAULT_SOFT_MINUTES))


def _travel(cfg: dict[str, Any]) -> timedelta:
    return timedelta(minutes=int(_sched(cfg).get("travel_minutes", 30)))


def _travel_kinds(cfg: dict[str, Any]) -> set[str]:
    return set(_sched(cfg).get("travel_kinds", ["class", "exam", "work_shift"]))


# ---------- dựng lịch tổng ----------

def events_for(day: date, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Mọi sự kiện CÓ GIỜ chạm vào ngày `day`, sắp theo giờ bắt đầu.

    Văn phòng và buổi tập chỉ có khi ngày đó đã nằm trong kế hoạch tuần (`state/week.json`)."""
    from .daymodel import hm, week_entry

    day_start = datetime.combine(day, time(0, 0), VN)
    day_end = day_start + timedelta(days=1)
    entry = week_entry(day)
    training = (entry or {}).get("training")
    group_id = (training or {}).get("group_event_id")  # buổi chạy nhóm CHÍNH LÀ sự kiện này, không tính hai lần
    out: list[dict[str, Any]] = []

    for it in agenda.timed_items(all_items()):
        if "T" not in it["start"] or "T" not in it["end"]:
            continue  # sự kiện cả ngày không chặn giờ nào
        s, e = parse_dt(it["start"]), parse_dt(it["end"])
        if e <= day_start or s >= day_end or it["id"] == group_id:
            continue
        out.append({"id": it["id"], "title": it["title"], "start": s, "end": e, "layer": FIXED, "kind": it["kind"],
                    "domain": it["domain"], "source": it["source"], "location": it.get("location")})

    if entry:
        if entry.get("office"):
            a, b = entry["office"]
            out.append({"id": f"_office:{day}", "title": "Văn phòng", "start": hm(a, day), "end": hm(b, day),
                        "layer": LIFEOS, "kind": "office", "domain": "congty", "source": "week"})
        if training:
            out.append({"id": f"_train:{day}", "title": training["label"], "start": hm(training["start"], day),
                        "end": hm(training["end"], day), "layer": LIFEOS, "kind": "training",
                        "domain": "canhan", "source": "week", "type": training["type"]})

    for p in plan_list(day):
        if p.get("status") != "planned":
            continue
        h, m = (int(x) for x in p["at"].split(":"))
        s = datetime.combine(day, time(h, m), VN)
        out.append({"id": f"_plan:{day}:{p['n']}", "title": p["title"], "start": s,
                    "end": s + timedelta(minutes=p.get("minutes") or 30), "layer": LIFEOS, "kind": "plan",
                    "domain": "lifeos", "source": "plan"})

    out.sort(key=lambda ev: (ev["start"], ev["end"]))
    return out


# ---------- tìm chỗ trùng ----------

def _same(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Cùng một sự kiện nằm ở hai lịch (ví dụ lịch trường và lịch cá nhân) thì không phải trùng."""
    return a["start"] == b["start"] and a["end"] == b["end"] and a["title"].strip().casefold() == b["title"].strip().casefold()


def _span(ev: dict[str, Any], cfg: dict[str, Any], pad: bool) -> tuple[datetime, datetime]:
    """Khoảng chiếm chỗ của sự kiện. `pad`: lớp/thi/ca làm cần thêm thời gian di chuyển hai đầu."""
    if pad and ev["layer"] == FIXED and ev["kind"] in _travel_kinds(cfg):
        return ev["start"] - _travel(cfg), ev["end"] + _travel(cfg)
    return ev["start"], ev["end"]


def _pair(a: dict[str, Any], b: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any] | None:
    if a["id"] == b["id"] or _same(a, b):
        return None
    lifeos = [x for x in (a, b) if x["layer"] == LIFEOS]
    pad = bool(lifeos)  # đệm di chuyển chỉ khi đối chiếu với thứ LifeOS tự xếp (lịch–lịch giữ nguyên như digest)
    (as_, ae), (bs, be) = _span(a, cfg, pad), _span(b, cfg, pad)
    if ae <= bs or be <= as_:
        return None

    severity, loai = HIGH, "lifeos-lich"
    if not lifeos:
        severity, loai = NOTE, "lich-lich"
    elif len(lifeos) == 2:
        loai = "lifeos-lifeos"
        kinds = {a["kind"], b["kind"]}
        if kinds == {"office", "plan"}:
            severity = NOTE  # làm việc riêng trong giờ văn phòng: Khôi quyết
    else:
        fixed, mine = (b, a) if a["layer"] == LIFEOS else (a, b)
        if mine["kind"] == "office":
            if fixed["domain"] == "congty" or fixed["kind"] == "work_shift":
                return None  # họp/ca của công ty diễn ra ngay tại văn phòng
            if fixed["kind"] not in ("class", "exam"):
                minutes = (fixed["end"] - fixed["start"]).total_seconds() / 60
                if minutes <= _soft_minutes(cfg):
                    return None  # sự kiện ngắn kiểu nhắc việc: không làm hỏng ngày văn phòng
                severity = NOTE

    real = min(a["end"], b["end"]) > max(a["start"], b["start"])
    o_s, o_e = (max(a["start"], b["start"]), min(a["end"], b["end"])) if real else (max(as_, bs), min(ae, be))
    day = o_s.astimezone(VN).date()

    def label(ev: dict[str, Any]) -> str:
        return f"{ev['title']} {ev['start']:%H:%M}–{ev['end']:%H:%M}"

    text = f"{vn_date(day)}: {label(a)} đè {label(b)}" if real else (
        f"{vn_date(day)}: {label(a)} sát {label(b)} — cần ~{int(_travel(cfg).total_seconds() // 60)} phút di chuyển")
    return {
        "a": a["id"], "b": b["id"], "a_title": a["title"], "b_title": b["title"],
        "a_domain": a["domain"], "b_domain": b["domain"],
        "overlap_start": iso(o_s), "overlap_end": iso(o_e), "date": day.isoformat(),
        "severity": severity, "loai": loai, "text": text,
        "movable": [x["id"] for x in lifeos],
    }


def conflicts_in(events: Iterable[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    evs = sorted(events, key=lambda ev: (ev["start"], ev["end"]))
    out = []
    for i, a in enumerate(evs):
        for b in evs[i + 1:]:
            c = _pair(a, b, cfg)
            if c:
                out.append(c)
    return out


def conflicts(days: Iterable[date], cfg: dict[str, Any], *, include_lich_lich: bool = True) -> list[dict[str, Any]]:
    """Mọi chỗ trùng trong các ngày `days` (đã gom, không lặp khi sự kiện kéo qua nửa đêm)."""
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for day in days:
        for c in conflicts_in(events_for(day, cfg), cfg):
            key = tuple(sorted((c["a"], c["b"])))
            if key in seen or (c["loai"] == "lich-lich" and not include_lich_lich):
                continue
            seen.add(key)
            out.append(c)
    out.sort(key=lambda c: (c["overlap_start"], c["a"]))
    return out


def high(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in found if c["severity"] == HIGH]


def check(start: date, days: int, cfg: dict[str, Any]) -> dict[str, Any]:
    found = conflicts([start + timedelta(days=i) for i in range(days)], cfg)
    cao = high(found)
    return {"ok": not cao, "from": start.isoformat(), "days": days,
            "cao": cao, "luu_y": [c for c in found if c["severity"] == NOTE],
            "text": [c["text"] for c in found]}


def try_event(start: datetime, end: datetime, title: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Thử một sự kiện sắp tạo (ví dụ Khôi nhờ thêm vào lịch): có đè gì trong lịch tổng không? Không ghi gì cả."""
    if end <= start:
        raise ValueError("Giờ kết thúc phải sau giờ bắt đầu.")
    cand = {"id": "_thu", "title": title or "(sự kiện mới)", "start": start, "end": end, "layer": FIXED,
            "kind": "event", "domain": "canhan", "source": "thu"}
    days, d = [], start.astimezone(VN).date()
    while d <= end.astimezone(VN).date():
        days.append(d)
        d += timedelta(days=1)
    found, seen = [], set()
    for day in days:
        for ev in events_for(day, cfg):
            if ev["id"] in seen:
                continue
            seen.add(ev["id"])
            c = _pair(cand, ev, cfg)
            if c:
                found.append(c)
    return {"ok": not found, "conflicts": found, "text": [c["text"] for c in found]}


# ---------- hiển thị ----------

def show(start: date, days: int, cfg: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for i in range(days):
        day = start + timedelta(days=i)
        rows.append({"date": day.isoformat(), "label": vn_date(day), "events": [
            {"start": f"{ev['start']:%H:%M}" if ev["start"].date() == day else "00:00",
             "end": f"{ev['end']:%H:%M}" if ev["end"].date() == day else "24:00",
             "title": ev["title"], "layer": ev["layer"], "kind": ev["kind"], "location": ev.get("location")}
            for ev in events_for(day, cfg)]})
    found = conflicts([start + timedelta(days=i) for i in range(days)], cfg)
    return {"from": start.isoformat(), "days": rows, "conflicts": found, "text": [c["text"] for c in found]}
