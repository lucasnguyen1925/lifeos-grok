"""Lệnh LifeOS cho các bot. Chạy từ thư mục bộ cài:  python3 -m lifeos <lệnh> ...

Mọi lệnh in kết quả dạng JSON (tiếng Việt, đọc được) để bot dùng tiếp.
Xem danh sách lệnh:  python3 -m lifeos --help
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from . import dashboard, digest, health, history, tracking
from .common import load_config, now, parse_dt, path, read_json, vn_date
from .schema import validate_domain_file


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _day(value: str | None) -> date:
    if value in (None, "today", "hom-nay"):
        return now().date()
    if value in ("tomorrow", "mai"):
        return now().date() + timedelta(days=1)
    return date.fromisoformat(value)


def _source(arg: str) -> tuple[str, tuple[str, str | None]]:
    """'bkel=needs_login:SSO hết phiên' -> ('bkel', ('needs_login', 'SSO hết phiên'))"""
    name, _, rest = arg.partition("=")
    state, _, detail = rest.partition(":")
    return name.strip(), (state.strip(), detail.strip() or None)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python3 -m lifeos", description="Lệnh LifeOS cho các bot.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("validate", help="Kiểm tra file dữ liệu mảng đúng định dạng chưa")
    s.add_argument("file")

    sub.add_parser("digest", help="Gộp 3 mảng → digest.json (độ gấp, trùng lịch, lịch hôm nay/mai)")

    s = sub.add_parser("alerts", help="Việc 🔴 chưa báo (tôn trọng giờ yên lặng)")
    s.add_argument("--mark", nargs="*", metavar="ID", help="Đánh dấu đã báo các id này sau khi gửi xong")

    sub.add_parser("mark-reported", help="Sau báo cáo 6:00/21:00: đánh dấu mọi việc 🔴 hiện có là đã báo")

    s = sub.add_parser("done", help="Ghi việc đã xong (tìm theo id hoặc một phần tên)")
    s.add_argument("query")
    s.add_argument("--by", default="khoi", choices=["khoi", "bot"])
    s.add_argument("--pick", type=int, help="Khi tìm ra nhiều việc: chọn việc số mấy (bắt đầu từ 1)")

    s = sub.add_parser("undone", help="Bỏ đánh dấu xong (lỡ đánh nhầm)")
    s.add_argument("id")

    s = sub.add_parser("status", help="Ghi nhịp tim sau mỗi lần chạy")
    s.add_argument("bot")
    s.add_argument("--type", required=True, choices=["full", "light", "report", "check"])
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--ok", action="store_true")
    g.add_argument("--fail", action="store_true")
    s.add_argument("--source", action="append", default=[], help="nguồn=trạng_thái[:chi tiết]")
    s.add_argument("--note")

    sub.add_parser("health", help="Kiểm tra sức khỏe cả đội (Tiko)")

    s = sub.add_parser("focus", help="Phiên tập trung")
    fs = s.add_subparsers(dest="action", required=True)
    f1 = fs.add_parser("start")
    f1.add_argument("--task", required=True)
    f1.add_argument("--minutes", type=int, default=30)
    f2 = fs.add_parser("end")
    f2.add_argument("--interrupted", action="store_true")
    f2.add_argument("--note")

    s = sub.add_parser("self", help="Khôi tự khai: phút tiếng Pháp, năng lượng 1–5")
    s.add_argument("--french", type=int)
    s.add_argument("--energy", type=int)
    s.add_argument("--date")

    s = sub.add_parser("plan", help="Kế hoạch nếu–thì cho ngày mai (R4)")
    ps = s.add_subparsers(dest="action", required=True)
    pa = ps.add_parser("add")
    pa.add_argument("--for", dest="for_day", default="tomorrow")
    pa.add_argument("--title", required=True)
    pa.add_argument("--at", required=True, help="HH:MM")
    pa.add_argument("--step", required=True, help="Bước đầu tiên ≤ 10 phút")
    pa.add_argument("--id", dest="item_id")
    pa.add_argument("--minutes", type=int)
    pa.add_argument("--auto", action="store_true", help="Tự áp dụng vì Khôi không trả lời tới 23:00")
    pl = ps.add_parser("list")
    pl.add_argument("--for", dest="for_day", default="today")
    pc = ps.add_parser("confirm", help="Khôi trả lời ok (hoặc --auto khi im lặng tới 23:00)")
    pc.add_argument("--for", dest="for_day", default="tomorrow")
    pc.add_argument("--auto", action="store_true")
    pr = ps.add_parser("result")
    pr.add_argument("n", type=int)
    pr.add_argument("status", choices=["done", "skipped", "moved"])
    pr.add_argument("--for", dest="for_day", default="today")
    pr.add_argument("--why")

    s = sub.add_parser("free", help="Khung trống trong ngày")
    s.add_argument("--date", default="today")
    s.add_argument("--min", type=int, default=20)

    s = sub.add_parser("remind-at", help="Giờ đặt Reminder + báo thức (né giờ học/làm — R2)")
    s.add_argument("--at", required=True, help="YYYY-MM-DDTHH:MM")
    s.add_argument("--min", type=int, default=15)

    s = sub.add_parser("date", help="Đổi ngày thành 'Thứ 2, 02/11' (không tự suy thứ!)")
    s.add_argument("value", nargs="?", default="today")

    sub.add_parser("close-day", help="Chốt sổ ngày (21:00)")
    sub.add_parser("close-week", help="Chốt tuần (CN 21:00)")
    sub.add_parser("close-month", help="Chốt tháng (ngày cuối tháng 21:00)")
    s = sub.add_parser("nightly", help="21:00: chốt ngày + tuần/tháng nếu đến kỳ + dashboard")
    s.add_argument("--png", action="store_true")
    sub.add_parser("cleanup", help="Xóa dữ liệu quá hạn giữ (Tiko, mỗi đêm)")

    s = sub.add_parser("dashboard", help="Dựng dashboard (HTML, nội dung Page, PNG)")
    s.add_argument("--png", action="store_true")

    a = p.parse_args(argv)

    if a.cmd == "validate":
        data = read_json(Path(a.file) if a.file.startswith("/") else path(a.file))
        if data is None:
            _print({"ok": False, "errors": [f"Không tìm thấy file {a.file}."]})
            return 1
        errors = validate_domain_file(data)
        _print({"ok": not errors, "errors": errors})
        return 0 if not errors else 1

    if a.cmd == "date":
        d = _day(a.value)
        _print({"date": d.isoformat(), "label": vn_date(d)})
        return 0

    cfg = load_config()

    if a.cmd == "digest":
        d = digest.build(cfg=cfg)
        _print({k: d[k] for k in ("generated_label", "counts", "needs_login", "problems", "new_red")}
               | {"conflicts": len(d["conflicts"]), "file": str(path("digest.json"))})
    elif a.cmd == "alerts":
        if a.mark is not None:
            _print({"marked": tracking.mark_alerted(a.mark)})
        else:
            res = tracking.pending_alerts(cfg=cfg)
            _print({"quiet_hours": res["quiet_hours"],
                    "send": [_brief(x) for x in res["send"]],
                    "held_until_morning": [_brief(x) for x in res["held"]]})
    elif a.cmd == "mark-reported":
        _print({"marked": tracking.mark_alerted(None)})
    elif a.cmd == "done":
        matches = tracking.find_items(a.query)
        if not matches:
            _print({"ok": False, "why": "Không tìm thấy việc nào khớp. Thử một phần tên khác, hoặc dùng id trong digest."})
            return 1
        if len(matches) > 1 and not a.pick:
            _print({"ok": False, "why": "Có nhiều việc khớp — hỏi lại Khôi rồi chạy lại với --pick N.",
                    "candidates": [{"n": i + 1, "id": m["id"], "title": m["title"], "due": m.get("due_label")}
                                   for i, m in enumerate(matches)]})
            return 1
        item = matches[(a.pick or 1) - 1]
        _print({"ok": True, "id": item["id"], **tracking.mark_done(item["id"], by=a.by)})
    elif a.cmd == "undone":
        _print({"ok": tracking.undo_done(a.id)})
    elif a.cmd == "status":
        st = health.write_status(a.bot, a.type, a.ok, dict(_source(x) for x in a.source), a.note)
        _print({"ok": True, "consecutive_failures": st.get("consecutive_failures", 0)})
    elif a.cmd == "health":
        _print(health.check(cfg))
    elif a.cmd == "focus":
        _print(tracking.focus_start(a.task, a.minutes) if a.action == "start" else tracking.focus_end(a.interrupted, a.note))
    elif a.cmd == "self":
        _print(tracking.self_report(a.french, a.energy, _day(a.date)))
    elif a.cmd == "plan":
        day = _day(a.for_day)
        if a.action == "add":
            _print(tracking.plan_add(day, a.title, a.at, a.step, a.item_id, a.minutes, a.auto))
        elif a.action == "list":
            plans = tracking.plan_list(day)
            _print({"date": vn_date(day), "confirmed": bool(plans) and all(x.get("confirmed") for x in plans), "plans": plans})
        elif a.action == "confirm":
            _print({"date": vn_date(day), "plans": tracking.plan_confirm(day, a.auto)})
        else:
            _print(tracking.plan_result(day, a.n, a.status, a.why))
    elif a.cmd == "free":
        from . import agenda
        day = _day(a.date)
        slots = agenda.free_slots(tracking.all_items(), day, cfg, a.min, not_before=now() if day == now().date() else None)
        _print({"date": vn_date(day), "slots": [{"from": f"{s:%H:%M}", "to": f"{e:%H:%M}",
                                                 "minutes": int((e - s).total_seconds() // 60)} for s, e in slots]})
    elif a.cmd == "remind-at":
        _print(tracking.remind_at(parse_dt(a.at), cfg, a.min))
    elif a.cmd == "close-day":
        _print(history.close_day())
    elif a.cmd == "close-week":
        _print(history.close_week())
    elif a.cmd == "close-month":
        _print(history.close_month())
    elif a.cmd == "nightly":
        out = {"day": history.close_day()["date"]}
        t = now()
        if t.weekday() == 6:
            out["week"] = history.close_week()["period"]
        if history.is_last_day_of_month(t.date()):
            out["month"] = history.close_month()["period"]
        out["dashboard"] = dashboard.build(png=a.png, cfg=cfg)
        _print(out)
    elif a.cmd == "cleanup":
        _print({"removed": history.cleanup(cfg=cfg), "done_pruned": tracking.prune_done()})
    elif a.cmd == "dashboard":
        _print(dashboard.build(png=a.png, cfg=cfg))
    return 0


def _brief(item: dict) -> dict:
    return {k: item.get(k) for k in ("id", "domain", "title", "level_label", "reasons", "due_label", "start_label", "url")}


if __name__ == "__main__":
    sys.exit(main())
