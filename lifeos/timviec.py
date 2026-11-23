"""Lượt tìm việc nhỏ trong ngày (SPEC §5h): 08:45 · 11:45 · 14:45 · 17:45.

Mỗi lượt, LifeOS chạy `timviec check` TRƯỚC khi nghĩ gì:
    python3 -m lifeos timviec check            # co_moi false → dừng ngay, không nhắn Khôi (đỡ credit)
    python3 -m lifeos timviec check --mark     # xem xong (đã làm sẵn / lập phiếu / thấy không có gì) → ghi đã xem

`viec`: việc mới xuất hiện (hoặc vừa đổi hạn/giờ) trong digest từ lần xem trước, chưa xong, chưa có phiếu V.
`chuan_bi` (chỉ lượt sáng, trước 10:00 hoặc --sang): lịch còn lại hôm nay chưa chuẩn bị (họp, học, hẹn) để
chuẩn bị trước — mở sẵn tài liệu, soạn sẵn tin, nhắc giờ phải đi.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .common import iso, now, parse_dt, path, read_json, write_json

MAX_ITEMS = 10
MORNING_BEFORE_HOUR = 10
KEEP_DAYS = 30
BRIEF = ("id", "domain", "kind", "title", "level_label", "due_label", "start_label", "change_note", "url")


def _path():
    return path("state", "timviec.json")


def _sig(it: dict[str, Any]) -> str:
    """Việc đổi hạn/giờ thì coi như mới để xem lại."""
    return f"{it.get('due') or ''}|{it.get('start') or ''}"


def _brief(it: dict[str, Any]) -> dict[str, Any]:
    return {k: it[k] for k in BRIEF if it.get(k) is not None}


def _scan(t: datetime, morning: bool | None) -> tuple[dict[str, Any], list[dict], list[dict], dict[str, Any]]:
    from . import lamho

    state = read_json(_path(), None) or {"seen": {}, "prepared": {}}
    dg = read_json(path("digest.json"), None)
    if dg is None:
        return state, [], [], {"why": "Chưa có digest.json — chưa có gì để xem."}
    done = read_json(path("done.json"), {}) or {}
    active = lamho.active_item_ids()
    seen = state.get("seen", {})
    fresh = [it for it in dg.get("items", [])
             if it["id"] not in done and it["id"] not in active
             and (seen.get(it["id"]) or {}).get("sig") != _sig(it)][:MAX_ITEMS]
    if morning is None:
        morning = t.hour < MORNING_BEFORE_HOUR
    prep: list[dict] = []
    if morning:
        done_prep = set(state.get("prepared", {}).get(t.date().isoformat(), []))
        prep = [ev for ev in dg.get("schedule_today", [])
                if ev["id"] not in done_prep and ev["id"] not in done
                and (parse_dt(ev.get("start")) or t) > t][:MAX_ITEMS]
    info = {"digest_label": dg.get("generated_label"), "morning": morning}
    return state, fresh, prep, info


def check(mark: bool = False, morning: bool | None = None, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    state, fresh, prep, info = _scan(t, morning)
    out = {"co_moi": bool(fresh or prep), "luot": "sáng" if info.get("morning") else "ngày",
           "viec": [_brief(x) for x in fresh], "chuan_bi": [_brief(x) for x in prep], **info}
    if not out["co_moi"]:
        out["note"] = "Không có gì mới. Dừng ngay, không nhắn Khôi."
    if mark:
        seen = state.setdefault("seen", {})
        for it in fresh:
            seen[it["id"]] = {"sig": _sig(it), "at": iso(t)}
        cutoff = t - timedelta(days=KEEP_DAYS)
        state["seen"] = {k: v for k, v in seen.items() if (parse_dt(v.get("at")) or t) > cutoff}
        key = t.date().isoformat()
        prepared = state.get("prepared", {}).get(key, [])
        state["prepared"] = {key: prepared + [ev["id"] for ev in prep if ev["id"] not in prepared]}
        state["last_check"] = iso(t)
        write_json(_path(), state)
        out["marked"] = len(fresh) + len(prep)
    return out
