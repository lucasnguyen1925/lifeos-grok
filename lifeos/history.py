"""Chốt sổ ngày → tuần → tháng, và dọn dữ liệu cũ.

    python3 -m lifeos close-day      # 21:00 mỗi ngày
    python3 -m lifeos close-week     # 21:00 Chủ nhật (sau close-day)
    python3 -m lifeos close-month    # 21:00 ngày cuối tháng (sau close-day)
    python3 -m lifeos cleanup        # mỗi đêm (Tiko)

Giữ lại: dữ liệu ngày + tóm tắt tuần 90 ngày; Zalo thô 7 ngày; tóm tắt tháng giữ lâu dài.
"""
from __future__ import annotations

import shutil
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any

from . import urgency
from .common import (
    iso, now, parse_dt, path, read_json, read_jsonl, vn_date, write_json, write_text,
)
from .tracking import all_items, plan_list

WORK_KINDS = {"work_shift", "meeting"}


def _hours_by_area(items: list[dict[str, Any]], day: date) -> dict[str, float]:
    """Giờ học / làm / cá nhân trong ngày, tính từ 3 bộ lịch."""
    hours = {"hoc": 0.0, "lam": 0.0, "canhan": 0.0}
    seen = set()
    late_evening = False
    for it in items:
        if it["kind"] not in urgency.SCHEDULE_KINDS or not it.get("start") or not it.get("end"):
            continue
        start, end = parse_dt(it["start"]), parse_dt(it["end"])
        if start.date() != day:
            continue
        key = (it["start"], it["end"], it["title"].casefold())
        if key in seen:
            continue
        seen.add(key)
        h = (end - start).total_seconds() / 3600
        if it["domain"] == "hoctap":
            hours["hoc"] += h
        elif it["domain"] == "congty" or it["kind"] in WORK_KINDS:
            hours["lam"] += h
        else:
            hours["canhan"] += h
        if end.hour >= 22 or end.date() > day:
            late_evening = True
    return {k: round(v, 2) for k, v in hours.items()} | {"late_evening": late_evening}


def close_day(t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    day = t.date()
    done_log = [r for r in read_jsonl(path("log", "done.jsonl")) if parse_dt(r["done_at"]).date() == day]
    with_due = [r for r in done_log if r.get("due")]
    on_time = [r for r in with_due if parse_dt(r["done_at"]) <= parse_dt(r["due"])]
    lead_hours = [
        (parse_dt(r["due"]) - parse_dt(r["done_at"])).total_seconds() / 3600 for r in with_due
    ]
    start_delay = [
        (parse_dt(r["done_at"]) - parse_dt(r["first_seen"])).total_seconds() / 3600
        for r in done_log if r.get("first_seen")
    ]

    digest = read_json(path("digest.json"), {}) or {}
    items = digest.get("items", [])
    late_today = [
        it for it in items
        if it.get("minutes_left") is not None and it["minutes_left"] < 0
        and urgency.due_dt(it) and urgency.due_dt(it).date() == day
    ]
    vip_waiting = [it for it in items if any("người quan trọng" in r for r in it.get("reasons", []))]

    focus = [r for r in read_jsonl(path("log", "focus.jsonl"))
             if r["event"] == "end" and parse_dt(r["at"]).date() == day]
    selfrep = [r for r in read_jsonl(path("log", "self.jsonl")) if r["date"] == day.isoformat()]
    plans = plan_list(day)

    record = {
        "date": day.isoformat(),
        "label": vn_date(day),
        "closed_at": iso(t),
        "tasks": {
            "done": len(done_log),
            "done_with_due": len(with_due),
            "on_time": len(on_time),
            "late_open": len(late_today),
            "late_quiz_or_registration": sum(1 for it in late_today if it["kind"] in {"quiz", "registration"}),
            "avg_hours_before_due": round(mean(lead_hours), 1) if lead_hours else None,
            "avg_hours_seen_to_done": round(mean(start_delay), 1) if start_delay else None,
            "open_by_level": digest.get("counts", {}),
        },
        "hours": _hours_by_area(all_items(), day),
        "conflicts": len(digest.get("conflicts", [])),
        "focus": {
            "sessions": len(focus),
            "minutes": sum(r["minutes"] for r in focus),
            "interrupted": sum(1 for r in focus if r.get("interrupted")),
        },
        "plans": {
            "planned": len(plans),
            "done": sum(1 for p in plans if p["status"] == "done"),
            "skipped": [p.get("why") for p in plans if p["status"] == "skipped"],
        },
        "self": {
            "french_minutes": next((r["french_minutes"] for r in reversed(selfrep) if r.get("french_minutes") is not None), None),
            "energy": next((r["energy"] for r in reversed(selfrep) if r.get("energy") is not None), None),
        },
        "vip_waiting_over_24h": len(vip_waiting),
        "grades": (read_json(path("data", "hoctap.json"), {}) or {}).get("grades"),
        "done_titles": [r["title"] for r in done_log],
    }
    write_json(path("history", "daily", f"{day.isoformat()}.json"), record)
    _archive_zalo(day)
    return record


def _archive_zalo(day: date) -> None:
    src = path("data", "zalo.json")
    if src.exists():
        dst = path("history", "zalo", f"{day.isoformat()}.json")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


def _load_days(first: date, last: date) -> list[dict[str, Any]]:
    days, d = [], first
    while d <= last:
        rec = read_json(path("history", "daily", f"{d.isoformat()}.json"))
        if rec:
            days.append(rec)
        d += timedelta(days=1)
    return days


def summarize(days: list[dict[str, Any]]) -> dict[str, Any]:
    """Các chỉ số A, B, D, G + tự khai của một kỳ (tuần hoặc tháng)."""
    def total(f):
        return sum(f(d) or 0 for d in days)

    def avg(values):
        values = [v for v in values if v is not None]
        return round(mean(values), 1) if values else None

    with_due = total(lambda d: d["tasks"]["done_with_due"])
    on_time = total(lambda d: d["tasks"]["on_time"])
    planned = total(lambda d: d["plans"]["planned"])
    plan_done = total(lambda d: d["plans"]["done"])
    grades_last = next((d["grades"] for d in reversed(days) if d.get("grades")), None)
    return {
        "days_recorded": len(days),
        "A_done": total(lambda d: d["tasks"]["done"]),
        "A_on_time_pct": round(100 * on_time / with_due) if with_due else None,
        "A_late": total(lambda d: d["tasks"]["late_open"]),
        "B_late_quiz_or_registration": total(lambda d: d["tasks"]["late_quiz_or_registration"]),
        "B_grade_avg": _grade_avg(grades_last),
        "D_hours_hoc": round(total(lambda d: d["hours"]["hoc"]), 1),
        "D_hours_lam": round(total(lambda d: d["hours"]["lam"]), 1),
        "D_hours_canhan": round(total(lambda d: d["hours"]["canhan"]), 1),
        "D_conflict_days": sum(1 for d in days if d["conflicts"]),
        "D_late_evenings": sum(1 for d in days if d["hours"]["late_evening"]),
        "G_plan_pct": round(100 * plan_done / planned) if planned else None,
        "G_focus_minutes": total(lambda d: d["focus"]["minutes"]),
        "G_focus_sessions": total(lambda d: d["focus"]["sessions"]),
        "G_interruptions": total(lambda d: d["focus"]["interrupted"]),
        "G_avg_hours_seen_to_done": avg(d["tasks"]["avg_hours_seen_to_done"] for d in days),
        "G_vip_waiting_days": sum(1 for d in days if d["vip_waiting_over_24h"]),
        "F_french_minutes": total(lambda d: d["self"]["french_minutes"]),
        "F_energy_avg": avg(d["self"]["energy"] for d in days),
        "skip_reasons": [w for d in days for w in d["plans"]["skipped"] if w],
    }


def _grade_avg(grades: list[dict[str, Any]] | None) -> float | None:
    """Điểm trung bình (thang 10) có trọng số tín chỉ, từ danh sách grades bot Học tập ghi."""
    if not grades:
        return None
    pairs = [(g["score"], g.get("credits") or 1) for g in grades if isinstance(g.get("score"), (int, float))]
    if not pairs:
        return None
    return round(sum(s * c for s, c in pairs) / sum(c for _, c in pairs), 2)


ARROWS = {True: "↑", False: "↓"}
LOWER_IS_BETTER = {"A_late", "B_late_quiz_or_registration", "D_conflict_days", "D_late_evenings",
                   "G_interruptions", "G_avg_hours_seen_to_done", "G_vip_waiting_days"}
LABELS = {
    "A_done": "Việc đã xong",
    "A_on_time_pct": "% xong đúng hạn",
    "A_late": "Việc trễ hạn",
    "B_late_quiz_or_registration": "Quiz/đăng ký bị trễ",
    "B_grade_avg": "Điểm TB (thang 10)",
    "D_hours_hoc": "Giờ học (theo lịch)",
    "D_hours_lam": "Giờ làm (theo lịch)",
    "D_hours_canhan": "Giờ cá nhân (theo lịch)",
    "D_conflict_days": "Số ngày có trùng lịch",
    "D_late_evenings": "Số tối có lịch sau 22:00",
    "G_plan_pct": "% kế hoạch nếu–thì làm được",
    "G_focus_minutes": "Phút tập trung",
    "G_focus_sessions": "Số phiên tập trung",
    "G_interruptions": "Số lần bị kéo đi",
    "G_avg_hours_seen_to_done": "Giờ từ lúc thấy tới lúc xong (TB)",
    "G_vip_waiting_days": "Số ngày có tin quan trọng chờ > 24h",
    "F_french_minutes": "Phút tiếng Pháp",
    "F_energy_avg": "Năng lượng TB (1–5)",
}


def compare_table(cur: dict[str, Any], prev: dict[str, Any] | None) -> str:
    rows = ["| Chỉ số | Kỳ này | Kỳ trước | |", "|---|---|---|---|"]
    for key, label in LABELS.items():
        a, b = cur.get(key), (prev or {}).get(key)
        trend = ""
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a != b:
            better = (a < b) if key in LOWER_IS_BETTER else (a > b)
            trend = f"{ARROWS[a > b]} {'tốt hơn' if better else 'kém hơn'}"
        rows.append(f"| {label} | {_fmt(a)} | {_fmt(b)} | {trend} |")
    return "\n".join(rows)


def _fmt(v: Any) -> str:
    return "—" if v is None else str(v)


def _write_period(kind: str, key: str, title: str, days: list[dict[str, Any]], prev_key: str | None) -> dict[str, Any]:
    summary = summarize(days)
    prev = read_json(path("context", kind, f"{prev_key}.json")) if prev_key else None
    record = {"period": key, "title": title, "closed_at": iso(now()), "metrics": summary,
              "done_titles": [x for d in days for x in d.get("done_titles", [])]}
    write_json(path("context", kind, f"{key}.json"), record)
    reasons = [f"- {w}" for w in summary["skip_reasons"]] or ["- (không có)"]
    md = [
        f"# {title}",
        "",
        f"_Chốt lúc {now():%H:%M %d/%m/%Y}. Số ngày có dữ liệu: {summary['days_recorded']}._",
        "",
        "## Chỉ số",
        compare_table(summary, (prev or {}).get("metrics")),
        "",
        "## Việc đã xong",
        *(f"- {x}" for x in record["done_titles"][:40]),
        "",
        "## Lý do kế hoạch bị bỏ (Khôi tự nói)",
        *reasons,
        "",
        "## Nhận xét của LifeOS",
        "<!-- LifeOS viết vào đây: 3 điểm sáng, 3 điểm cần cải thiện, 3 đề xuất cho kỳ tới, việc đang dở cần nhớ. -->",
        "",
    ]
    write_text(path("context", kind, f"{key}.md"), "\n".join(md))
    return record


def close_week(t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    last = t.date()
    first = last - timedelta(days=last.weekday())  # Thứ 2 của tuần
    year, week, _ = first.isocalendar()
    prev_year, prev_week, _ = (first - timedelta(days=7)).isocalendar()
    title = f"Tuần {week} ({first:%d/%m}–{last:%d/%m/%Y})"
    return _write_period("weekly", f"{year}-W{week:02d}", title, _load_days(first, last), f"{prev_year}-W{prev_week:02d}")


def close_month(t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    last = t.date()
    first = last.replace(day=1)
    prev = first - timedelta(days=1)
    title = f"Tháng {first:%m/%Y}"
    return _write_period("monthly", f"{first:%Y-%m}", title, _load_days(first, last), f"{prev:%Y-%m}")


def is_last_day_of_month(d: date) -> bool:
    return (d + timedelta(days=1)).day == 1


def cleanup(t: datetime | None = None, cfg: dict[str, Any] | None = None) -> dict[str, int]:
    t = t or now()
    keep = (cfg or {}).get("retention", {})
    rules = [
        (path("history", "daily"), keep.get("daily_days", 90)),
        (path("context", "weekly"), keep.get("weekly_days", 90)),
        (path("history", "zalo"), keep.get("zalo_raw_days", 7)),
    ]
    removed: dict[str, int] = {}
    today = t.date()
    for folder, days in rules:
        count = 0
        for f in folder.glob("*") if folder.exists() else []:
            stamp = _file_date(f.stem)
            if stamp and (today - stamp).days > days:
                f.unlink()
                count += 1
        removed[folder.name] = count
    for log_name in ("done.jsonl", "focus.jsonl", "self.jsonl"):
        removed[log_name] = _trim_log(path("log", log_name), today - timedelta(days=keep.get("daily_days", 90)))
    plans = read_json(path("state", "plans.json"), {}) or {}
    cutoff = (today - timedelta(days=keep.get("daily_days", 90))).isoformat()
    write_json(path("state", "plans.json"), {k: v for k, v in plans.items() if k >= cutoff})
    return removed


def _file_date(stem: str) -> date | None:
    try:
        if "-W" in stem:
            y, w = stem.split("-W")
            return date.fromisocalendar(int(y), int(w), 7)
        return date.fromisoformat(stem)
    except ValueError:
        return None


def _trim_log(p, cutoff: date) -> int:
    rows = read_jsonl(p)
    if not rows:
        return 0
    keep = []
    for r in rows:
        stamp = r.get("date") or r.get("done_at") or r.get("at")
        if stamp is None or (parse_dt(stamp) if "T" in stamp else datetime.fromisoformat(stamp)).date() >= cutoff:
            keep.append(r)
    if len(keep) != len(rows):
        import json
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep), encoding="utf-8")
    return len(rows) - len(keep)


