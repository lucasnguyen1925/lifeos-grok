"""Gộp dữ liệu 3 mảng thành digest.json — thứ duy nhất LifeOS cần đọc để viết báo cáo.

    python3 -m lifeos digest            # tạo /workspace/lifeos/digest.json
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from . import agenda, lichtong, urgency
from .common import DOMAINS, iso, now, parse_dt, path, read_json, vn_date, vn_datetime, vn_deadline, write_json
from .schema import validate_domain_file

TRACKED_FIELDS = ("due", "start", "end", "location", "title")
CHANGE_LABELS = {"due": "đổi hạn", "start": "đổi giờ", "end": "đổi giờ", "location": "đổi phòng/địa điểm", "title": "đổi tên"}


def load_done() -> dict[str, Any]:
    return read_json(path("done.json"), {}) or {}


def load_domains() -> tuple[dict[str, Any], list[str]]:
    files, problems = {}, []
    for d in DOMAINS:
        data = read_json(path("data", f"{d}.json"))
        if data is None:
            problems.append(f"Chưa có file dữ liệu mảng {d}.")
            continue
        errs = validate_domain_file(data, d)
        if errs:
            problems.append(f"File mảng {d} sai định dạng ({len(errs)} lỗi), bỏ qua lần này: {errs[0]}")
            continue
        files[d] = data
    return files, problems


def track_changes(items: list[dict[str, Any]], t: datetime) -> dict[str, Any]:
    """So với lần trước để tự phát hiện việc MỚI và việc BỊ ĐỔI, không phụ thuộc bot có ghi 'changed' hay không."""
    seen = read_json(path("state", "seen.json"), {}) or {}
    for it in items:
        rec = seen.get(it["id"])
        if rec is None:
            seen[it["id"]] = {"first_seen": iso(t), **{f: it.get(f) for f in TRACKED_FIELDS}}
            continue
        diffs = [f for f in TRACKED_FIELDS if f != "title" and rec.get(f) != it.get(f) and rec.get(f) is not None]
        if diffs:
            notes = sorted({CHANGE_LABELS[f] for f in diffs})
            rec["changed_at"] = iso(t)
            rec["change_note"] = ", ".join(notes)
        rec.update({f: it.get(f) for f in TRACKED_FIELDS})
    # Quên những việc đã biến mất quá 30 ngày để file không phình mãi
    live = {it["id"] for it in items}
    cutoff = t - timedelta(days=30)
    for key in [k for k, v in seen.items() if k not in live and parse_dt(v.get("first_seen")) < cutoff]:
        del seen[key]
    write_json(path("state", "seen.json"), seen)
    return seen


def build(t: datetime | None = None, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    from .common import load_config

    t = t or now()
    cfg = cfg if cfg is not None else load_config()
    stale_hours = cfg.get("rules", {}).get("stale_hours", 14)
    files, problems = load_domains()
    done = load_done()

    domains_info, needs_login, all_items = {}, [], []
    for d, data in files.items():
        gen = parse_dt(data["generated_at"])
        age = (t - gen).total_seconds() / 3600
        domains_info[d] = {
            "generated_at": data["generated_at"],
            "generated_label": vn_datetime(gen),
            "age_hours": round(age, 1),
            "stale": age > stale_hours,
            "sources": data["sources"],
        }
        for name, src in data["sources"].items():
            if src["status"] == "needs_login":
                needs_login.append({"domain": d, "source": name, "detail": src.get("detail")})
        all_items += [it for it in data["items"] if it["status"] == "open" and it["id"] not in done]
    for d in DOMAINS:
        if d not in domains_info:
            domains_info[d] = {"missing": True, "stale": True}

    seen = track_changes(all_items, t)
    for it in all_items:
        rec = seen.get(it["id"], {})
        changed_at = parse_dt(rec.get("changed_at"))
        if changed_at and t - changed_at <= timedelta(hours=48) and not it.get("changed"):
            it["changed"], it["change_note"] = True, rec.get("change_note")

    conflicts = agenda.find_conflicts(all_items, t)
    # Lịch tổng: chỗ trùng giữa thứ LifeOS tự xếp (văn phòng, buổi tập, ô 📝) với lịch thật — 3 ngày tới.
    # Để riêng khỏi `conflicts`: lịch học không nên bị tô 🔴 chỉ vì buổi tập đè lên nó (buổi tập phải dời).
    try:
        conflicts_lifeos = lichtong.conflicts([t.date() + timedelta(days=i) for i in range(3)], cfg, include_lich_lich=False)
    except (KeyError, ValueError, TypeError) as exc:
        conflicts_lifeos = []
        problems.append(f"Không dựng được lịch tổng: {exc}")
    in_conflict = {c["a"] for c in conflicts} | {c["b"] for c in conflicts}

    ranked = []
    for it in all_items:
        first_seen = parse_dt(seen.get(it["id"], {}).get("first_seen"))
        level, reasons = urgency.classify(it, t, cfg, first_seen=first_seen, in_conflict=it["id"] in in_conflict)
        out = dict(it, level=level, level_label=urgency.LABELS[level], reasons=reasons)
        due = urgency.due_dt(it)
        if due:
            out["due_label"] = vn_deadline(due)
            out["minutes_left"] = int((due - t).total_seconds() // 60)
        if it.get("start"):
            out["start_label"] = vn_datetime(parse_dt(it["start"]))
        ranked.append(out)
    far_future = datetime.max.replace(tzinfo=t.tzinfo)
    ranked.sort(key=lambda x: (x["level"], urgency.due_dt(x) or parse_dt(x.get("start")) or far_future))

    def schedule_for(day):
        evs = [x for x in ranked if x.get("start") and parse_dt(x["start"]).date() == day and x["kind"] in urgency.SCHEDULE_KINDS]
        return sorted(evs, key=lambda x: x["start"])

    tomorrow = (t + timedelta(days=1)).date()
    alerted = read_json(path("state", "alerts_sent.json"), {}) or {}
    digest = {
        "generated_at": iso(t),
        "generated_label": vn_datetime(t),
        "today_label": vn_date(t),
        "tomorrow_label": vn_date(tomorrow),
        "domains": domains_info,
        "problems": problems,
        "needs_login": needs_login,
        "counts": {urgency.LABELS[l]: sum(1 for x in ranked if x["level"] == l) for l in urgency.LABELS},
        "items": ranked,
        "schedule_today": schedule_for(t.date()),
        "schedule_tomorrow": schedule_for(tomorrow),
        "conflicts": conflicts,
        "conflicts_lifeos": conflicts_lifeos,
        "new_red": [x["id"] for x in ranked if x["level"] == urgency.RED and x["id"] not in alerted],
    }
    write_json(path("digest.json"), digest)
    return digest
