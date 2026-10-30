"""Những thứ LifeOS ghi lại khi nói chuyện với Khôi: việc đã xong, phiên tập trung,
tự khai (tiếng Pháp, năng lượng), kế hoạch "nếu–thì", và đánh dấu đã báo cảnh báo."""
from __future__ import annotations

import unicodedata
from datetime import date, datetime, timedelta
from typing import Any

from . import agenda
from .common import (
    DOMAINS, append_jsonl, iso, now, parse_dt, path, read_json, read_jsonl, vn_date, vn_datetime, write_json,
)
from .urgency import RED, due_dt


def _fold(text: str) -> str:
    """Bỏ dấu + chữ thường để tìm 'quiz sa0004' khớp 'Quiz SA0004'."""
    text = unicodedata.normalize("NFD", text.casefold()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


# ---------- việc đã xong ----------

def find_items(query: str) -> list[dict[str, Any]]:
    digest = read_json(path("digest.json"), {}) or {}
    items = digest.get("items", [])
    exact = [it for it in items if it["id"] == query]
    if exact:
        return exact
    q = _fold(query)
    return [it for it in items if q in _fold(it["title"]) or q in _fold(it["id"])]


def mark_done(item_id: str, by: str = "khoi", title: str | None = None, t: datetime | None = None) -> dict[str, Any]:
    """Ghi vào done.json. Mọi bot và script đọc file này nên việc đã xong không bao giờ bị nhắc lại."""
    t = t or now()
    done = read_json(path("done.json"), {}) or {}
    match = next((it for it in (read_json(path("digest.json"), {}) or {}).get("items", []) if it["id"] == item_id), None)
    seen = (read_json(path("state", "seen.json"), {}) or {}).get(item_id, {})
    due = due_dt(match) if match else None
    record = {
        "title": title or (match["title"] if match else item_id),
        "done_at": iso(t),
        "by": by,
        "due": iso(due),
        "kind": match["kind"] if match else None,
        "domain": match["domain"] if match else None,
        "first_seen": seen.get("first_seen"),
    }
    done[item_id] = record
    write_json(path("done.json"), done)
    append_jsonl(path("log", "done.jsonl"), {"id": item_id, **record})
    return record


def undo_done(item_id: str) -> bool:
    done = read_json(path("done.json"), {}) or {}
    if item_id not in done:
        return False
    del done[item_id]
    write_json(path("done.json"), done)
    return True


def prune_done(t: datetime | None = None, keep_days: int = 30) -> int:
    """Bỏ khỏi done.json những việc xong đã lâu và không còn xuất hiện ở nguồn nào."""
    t = t or now()
    done = read_json(path("done.json"), {}) or {}
    live = set()
    for d in DOMAINS:
        live |= {it["id"] for it in (read_json(path("data", f"{d}.json"), {}) or {}).get("items", [])}
    old = [k for k, v in done.items() if k not in live and t - parse_dt(v["done_at"]) > timedelta(days=keep_days)]
    for k in old:
        del done[k]
    write_json(path("done.json"), done)
    return len(old)


# ---------- cảnh báo ----------

def pending_alerts(t: datetime | None = None, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Việc 🔴 chưa từng báo. Trong giờ yên lặng thì không báo (dồn vào báo cáo 6:00)."""
    t = t or now()
    cfg = cfg or {}
    quiet = cfg.get("alerts", {}).get("quiet_hours", ["23:00", "06:00"])
    qs, qe = (int(x.split(":")[0]) * 60 + int(x.split(":")[1]) for x in quiet)
    minute = t.hour * 60 + t.minute
    in_quiet = (qs <= minute or minute < qe) if qs > qe else (qs <= minute < qe)
    digest = read_json(path("digest.json"), {}) or {}
    alerted = read_json(path("state", "alerts_sent.json"), {}) or {}
    items = [it for it in digest.get("items", []) if it["level"] == RED and it["id"] not in alerted]
    return {"quiet_hours": in_quiet, "send": [] if in_quiet else items, "held": items if in_quiet else []}


def mark_alerted(ids: list[str] | None = None, t: datetime | None = None) -> int:
    """Ghi nhận đã báo. Không truyền ids = đánh dấu mọi việc 🔴 hiện có (dùng sau mỗi báo cáo 6:00/21:00)."""
    t = t or now()
    alerted = read_json(path("state", "alerts_sent.json"), {}) or {}
    if ids is None:
        digest = read_json(path("digest.json"), {}) or {}
        ids = [it["id"] for it in digest.get("items", []) if it["level"] == RED]
    for i in ids:
        alerted.setdefault(i, iso(t))
    cutoff = t - timedelta(days=30)
    alerted = {k: v for k, v in alerted.items() if parse_dt(v) >= cutoff}
    write_json(path("state", "alerts_sent.json"), alerted)
    return len(ids)


# ---------- phiên tập trung ----------

def focus_start(task: str, minutes: int, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    rec = {"event": "start", "task": task, "planned_minutes": minutes, "at": iso(t), "ends_at": iso(t + timedelta(minutes=minutes))}
    append_jsonl(path("log", "focus.jsonl"), rec)
    return rec


def focus_end(interrupted: bool = False, note: str | None = None, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    log = read_jsonl(path("log", "focus.jsonl"))
    start = next((r for r in reversed(log) if r["event"] == "start"), None)
    if start is None or (log and log[-1]["event"] == "end"):
        return {"error": "Không có phiên tập trung nào đang mở."}
    actual = int((t - parse_dt(start["at"])).total_seconds() // 60)
    rec = {"event": "end", "task": start["task"], "at": iso(t), "started_at": start["at"],
           "minutes": max(actual, 0), "interrupted": interrupted, "note": note}
    append_jsonl(path("log", "focus.jsonl"), rec)
    return rec


# ---------- tự khai ----------

def self_report(french_minutes: int | None, energy: int | None, day: date | None = None) -> dict[str, Any]:
    day = day or now().date()
    if energy is not None and not 1 <= energy <= 5:
        raise ValueError("Năng lượng phải từ 1 đến 5.")
    rec = {"date": day.isoformat(), "french_minutes": french_minutes, "energy": energy, "at": iso(now())}
    append_jsonl(path("log", "self.jsonl"), rec)
    return rec


# ---------- kế hoạch "nếu–thì" (R4) ----------

def plan_add(for_day: date, title: str, at: str, step: str, item_id: str | None = None,
             minutes: int | None = None, auto: bool = False) -> dict[str, Any]:
    plans = read_json(path("state", "plans.json"), {}) or {}
    day_plans = plans.setdefault(for_day.isoformat(), [])
    rec = {"n": len(day_plans) + 1, "title": title, "at": at, "first_step": step, "item_id": item_id,
           "minutes": minutes, "auto_applied": auto, "status": "planned", "created_at": iso(now())}
    day_plans.append(rec)
    write_json(path("state", "plans.json"), plans)
    return rec


def plan_result(for_day: date, n: int, status: str, why: str | None = None) -> dict[str, Any]:
    if status not in {"done", "skipped", "moved"}:
        raise ValueError("status phải là done, skipped hoặc moved.")
    plans = read_json(path("state", "plans.json"), {}) or {}
    for rec in plans.get(for_day.isoformat(), []):
        if rec["n"] == n:
            rec.update(status=status, why=why, result_at=iso(now()))
            write_json(path("state", "plans.json"), plans)
            return rec
    raise KeyError(f"Không có kế hoạch số {n} cho ngày {for_day}.")


def plan_confirm(for_day: date, auto: bool = False) -> list[dict[str, Any]]:
    """Khôi trả lời "ok" (hoặc 23:00 tự áp dụng khi im lặng): đánh dấu kế hoạch ngày đó đã chốt."""
    plans = read_json(path("state", "plans.json"), {}) or {}
    day_plans = plans.get(for_day.isoformat(), [])
    for rec in day_plans:
        rec.update(confirmed=True, auto_applied=auto or rec.get("auto_applied", False), confirmed_at=iso(now()))
    write_json(path("state", "plans.json"), plans)
    return day_plans


def plan_list(for_day: date) -> list[dict[str, Any]]:
    return (read_json(path("state", "plans.json"), {}) or {}).get(for_day.isoformat(), [])


# ---------- khung trống & giờ đặt nhắc (R1, R2) ----------

def all_items() -> list[dict[str, Any]]:
    items = []
    for d in DOMAINS:
        items += (read_json(path("data", f"{d}.json"), {}) or {}).get("items", [])
    return items


def remind_at(wanted: datetime, cfg: dict[str, Any], minutes: int = 15) -> dict[str, Any]:
    """Giờ đặt Reminder + báo thức. Rơi vào giờ học/làm thì dời sang 5 phút sau khi rảnh (quy tắc R2)."""
    items = all_items()
    if not agenda.is_busy(items, wanted, cfg):
        return {"at": iso(wanted), "label": vn_datetime(wanted), "moved": False}
    slots = agenda.free_slots(items, wanted.date(), cfg, min_minutes=minutes, not_before=wanted)
    if slots:
        at = slots[0][0] + timedelta(minutes=5)
        return {"at": iso(at), "label": vn_datetime(at), "moved": True,
                "reason": "giờ bạn chọn đang bận học/làm, dời sang lúc rảnh"}
    return {"at": None, "moved": True, "reason": f"{vn_date(wanted)} không còn khung trống đủ {minutes} phút"}
