"""Nhịp tim và kiểm tra sức khỏe cả đội bot (việc của Tiko).

Mỗi bot chạy xong ghi nhịp tim:
    python3 -m lifeos status hoctap --type full --ok --source mybk=ok --source bkel=needs_login:"SSO hết phiên"
Tiko kiểm tra:
    python3 -m lifeos health
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from .common import BOTS, VN, iso, now, parse_dt, path, read_json, vn_datetime, write_json

SOURCE_STATES = {"ok", "needs_login", "error", "skipped"}


def write_status(bot: str, run_type: str, ok: bool, sources: dict[str, tuple[str, str | None]],
                 note: str | None = None, t: datetime | None = None) -> dict[str, Any]:
    if bot not in BOTS:
        raise ValueError(f"bot phải là một trong {BOTS}.")
    if run_type not in {"full", "light", "report", "check"}:
        raise ValueError("--type phải là full, light, report hoặc check.")
    t = t or now()
    p = path("_status", f"{bot}.json")
    st = read_json(p, {}) or {"bot": bot, "sources": {}, "runs": []}
    run = {"at": iso(t), "type": run_type, "ok": ok, "note": note,
           "sources": {k: {"status": s, "detail": d} for k, (s, d) in sources.items()}}
    st["runs"] = (st.get("runs", []) + [run])[-30:]
    st["last_run"] = run
    if ok:
        st["last_ok"] = iso(t)
        if run_type in {"full", "report"}:
            st["last_ok_full"] = iso(t)
        st["consecutive_failures"] = 0
    else:
        st["consecutive_failures"] = st.get("consecutive_failures", 0) + 1
    for name, (state, detail) in sources.items():
        if state not in SOURCE_STATES:
            raise ValueError(f"trạng thái nguồn {name} phải là một trong {sorted(SOURCE_STATES)}.")
        rec = st["sources"].setdefault(name, {})
        if state == "ok":
            rec.update(status="ok", detail=None, last_ok=iso(t), failing_since=None)
        elif state != "skipped":
            rec.update(status=state, detail=detail)
            rec.setdefault("failing_since", None)
            rec["failing_since"] = rec["failing_since"] or iso(t)
    write_json(p, st)
    return st


def _last_expected(times: list[str], t: datetime) -> datetime | None:
    """Lần chạy theo lịch gần nhất trước thời điểm t (theo giờ VN)."""
    candidates = []
    for day_offset in (0, 1):
        day = (t - timedelta(days=day_offset)).date()
        for hm in times:
            h, m = (int(x) for x in hm.split(":"))
            dt = datetime.combine(day, time(h, m), VN)
            if dt <= t:
                candidates.append(dt)
    return max(candidates) if candidates else None


def check(cfg: dict[str, Any], t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    grace = timedelta(minutes=cfg.get("health", {}).get("grace_minutes", 45))
    source_red = timedelta(hours=cfg.get("health", {}).get("source_red_hours", 36))
    schedules = cfg.get("health", {}).get("expected", {})
    report: dict[str, Any] = {"checked_at": iso(t), "bots": {}, "problems": [], "needs_login": []}
    for bot in BOTS:
        st = read_json(path("_status", f"{bot}.json"))
        expected_times = schedules.get(bot, [])
        info: dict[str, Any] = {"ok": True}
        if st is None:
            if expected_times:
                info = {"ok": False, "why": "chưa có nhịp tim nào"}
                report["problems"].append({"bot": bot, "level": "error", "text": f"{bot}: chưa từng ghi nhịp tim."})
            report["bots"][bot] = info
            continue
        last_ok_full = parse_dt(st.get("last_ok_full"))
        expected = _last_expected(expected_times, t - grace) if expected_times else None
        if expected and (last_ok_full is None or last_ok_full < expected - timedelta(minutes=30)):
            info = {"ok": False, "why": f"lỡ lần chạy {vn_datetime(expected)}"}
            report["problems"].append({"bot": bot, "level": "late", "text": f"{bot}: chưa chạy thành công lần {vn_datetime(expected)}."})
        if st.get("consecutive_failures", 0) >= 2:
            report["problems"].append({"bot": bot, "level": "error", "text": f"{bot}: lỗi {st['consecutive_failures']} lần liên tiếp."})
            info["ok"] = False
        for name, src in st.get("sources", {}).items():
            if src.get("status") in {"needs_login", "error"}:
                since = parse_dt(src.get("failing_since"))
                entry = {"bot": bot, "source": name, "status": src["status"], "detail": src.get("detail"),
                         "since": vn_datetime(since) if since else None,
                         "red": bool(since and t - since > source_red)}
                if src["status"] == "needs_login":
                    report["needs_login"].append(entry)
                else:
                    report["problems"].append({"bot": bot, "level": "source", "text": f"{bot}/{name}: {src.get('detail') or 'lỗi'}", **entry})
        info.update(last_ok=st.get("last_ok"), last_run=st.get("last_run", {}).get("at"))
        report["bots"][bot] = info
    report["all_ok"] = not report["problems"] and not report["needs_login"]
    write_json(path("health.json"), report)
    return report
