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

from . import brain, dashboard, digest, health, history, tracking
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
    pg = ps.add_parser("suggest", help="Đề xuất việc + xếp giờ vào khung trống, kèm dòng thời gian")
    pg.add_argument("--for", dest="for_day", default="today")
    pt = ps.add_parser("timeline", help="Dòng thời gian cả ngày (lịch cố định + kế hoạch đã lưu)")
    pt.add_argument("--for", dest="for_day", default="today")
    pe = ps.add_parser("edit", help="Dời giờ (--at) hoặc bỏ (--remove) khối số n")
    pe.add_argument("n", type=int)
    pe.add_argument("--for", dest="for_day", default="today")
    pe.add_argument("--at")
    pe.add_argument("--remove", action="store_true")
    pc = ps.add_parser("confirm", help="Khôi trả lời ok (hoặc --auto khi im lặng tới 23:00)")
    pc.add_argument("--for", dest="for_day", default="tomorrow")
    pc.add_argument("--auto", action="store_true")
    pr = ps.add_parser("result")
    pr.add_argument("n", type=int)
    pr.add_argument("status", choices=["done", "skipped", "moved"])
    pr.add_argument("--for", dest="for_day", default="today")
    pr.add_argument("--why")

    s = sub.add_parser("week", help="Kế hoạch tuần: văn phòng + tập + việc lớn (CN 20:00)")
    ws = s.add_subparsers(dest="action", required=True)
    wp = ws.add_parser("propose")
    wp.add_argument("--start", help="Thứ 2 của tuần (mặc định: Thứ 2 kế tiếp)")
    ws.add_parser("show")
    wset = ws.add_parser("set")
    wset.add_argument("date")
    wset.add_argument("--office", help="09:00-12:00 hoặc none")
    wset.add_argument("--training", help="17:30-18:45 hoặc none")
    wc = ws.add_parser("confirm")
    wc.add_argument("--auto", action="store_true")
    wcw = ws.add_parser("company-written", help="Đã ghi Office lên lịch công ty (cả tuần, hoặc --date)")
    wcw.add_argument("--date")

    s = sub.add_parser("calmap", help="Nhớ id sự kiện bot đã tạo trên lịch (để sửa/xóa đúng cái)")
    cs = s.add_subparsers(dest="action", required=True)
    c1 = cs.add_parser("set")
    c1.add_argument("key", help="ví dụ office:2026-11-03, train:2026-11-03, plan:2026-11-03:2")
    c1.add_argument("event_id")
    c2 = cs.add_parser("get")
    c2.add_argument("key")
    c3 = cs.add_parser("del")
    c3.add_argument("key")

    s = sub.add_parser("page", help="Nội dung Grok Page LifeOS: Hôm nay · Tuần này · Hiệu suất")

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

    _brain_parser(sub)

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
        if a.action == "suggest":
            from . import planner
            _print(planner.suggest(day, cfg) | {"date_label": vn_date(day)})
        elif a.action == "timeline":
            from . import planner
            _print({"date": day.isoformat(), "date_label": vn_date(day), "timeline": planner.timeline(day, cfg)})
        elif a.action == "add":
            _print(tracking.plan_add(day, a.title, a.at, a.step, a.item_id, a.minutes, a.auto))
        elif a.action == "list":
            plans = tracking.plan_list(day)
            _print({"date": vn_date(day), "confirmed": bool(plans) and all(x.get("confirmed") for x in plans), "plans": plans})
        elif a.action == "edit":
            _print({"date": vn_date(day), "plans": tracking.plan_edit(day, a.n, a.at, a.remove)})
        elif a.action == "confirm":
            _print({"date": vn_date(day), "plans": tracking.plan_confirm(day, a.auto)})
        else:
            _print(tracking.plan_result(day, a.n, a.status, a.why))
    elif a.cmd == "week":
        from . import week
        if a.action == "propose":
            _print(week.propose(date.fromisoformat(a.start) if a.start else None, cfg))
        elif a.action == "show":
            _print(week.show())
        elif a.action == "set":
            _print(week.set_day(_day(a.date), a.office, a.training))
        elif a.action == "confirm":
            _print(week.confirm(a.auto))
        else:
            _print(week.mark_company_written(_day(a.date) if a.date else None))
    elif a.cmd == "calmap":
        cm = read_json(path("state", "calendar_map.json"), {}) or {}
        if a.action == "set":
            cm[a.key] = a.event_id
        elif a.action == "del":
            cm.pop(a.key, None)
        if a.action != "get":
            from .common import write_json
            write_json(path("state", "calendar_map.json"), cm)
        _print({"key": a.key, "event_id": cm.get(a.key)})
    elif a.cmd == "page":
        _print(dashboard.build_page(cfg))
    elif a.cmd == "free":
        from . import agenda, daymodel
        day = _day(a.date)
        prof = daymodel.profile(day, cfg)
        items = tracking.all_items() + daymodel.synthetic_events(prof)
        slots = agenda.free_slots(items, day, cfg, a.min, not_before=now() if day == now().date() else None)
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
        out["brain"] = {"tidy": brain.tidy(), "page": brain.page(cfg)}
        _print(out)
    elif a.cmd == "brain":
        try:
            _print(_brain_run(a, cfg))
        except ValueError as exc:
            _print({"ok": False, "why": str(exc)})
            return 1
    elif a.cmd == "cleanup":
        _print({"removed": history.cleanup(cfg=cfg), "done_pruned": tracking.prune_done()})
    elif a.cmd == "dashboard":
        _print(dashboard.build(png=a.png, cfg=cfg))
    return 0


def _brain_parser(sub) -> None:
    s = sub.add_parser("brain", help="Sổ nhớ chung: hồ sơ ngắn, tìm, ghi, quên, đề xuất, nhật ký, kho, sao lưu")
    bs = s.add_subparsers(dest="action", required=True)
    bs.add_parser("core", help="Hồ sơ ngắn ~40 dòng — đọc đầu MỖI lượt chat / mỗi lần chạy routine")
    x = bs.add_parser("search", help="Tìm trong sổ + kho + nhật ký (gõ không dấu cũng được)")
    x.add_argument("query", nargs="+")
    x.add_argument("--limit", type=int, default=8)
    x = bs.add_parser("show", help="Trang chi tiết của một người / môn / dự án")
    x.add_argument("name", nargs="+")
    x = bs.add_parser("add", help="Ghi một điều đáng nhớ (LifeOS, Tiko)")
    x.add_argument("--section", required=True, help="ve_khoi · muc_tieu · nguoi_quen · cach_lam_viec · dang_do · tranh · khac")
    x.add_argument("--text", required=True)
    x.add_argument("--subject", help="Người/môn/dự án mà điều này nói về (để mở trang chi tiết)")
    x.add_argument("--tag", action="append", default=[])
    x.add_argument("--due", help="Hạn (mục dang_do): YYYY-MM-DD")
    x.add_argument("--core", action="store_true", help="Đưa lên hồ sơ ngắn")
    x.add_argument("--pin", action="store_true", help="Khôi nói 'ghim'")
    x.add_argument("--sensitive", action="store_true", help="Chuyện nhạy cảm (chỉ khi Khôi nói 'nhớ giúp' và đã xác nhận)")
    x.add_argument("--by", default="lifeos")
    x.add_argument("--origin", default="chat", help="chat · soat_chat · grok · notes")
    x.add_argument("--replaces", help="Mã điều cũ không còn đúng (giữ lại làm 'trước đây')")
    x.add_argument("--source", help="Lấy từ đâu: 'trang môn GT2 trên BKeL', 'mail ngày 20/10', 'Khôi kể'…")
    x = bs.add_parser("edit", help="Sửa vì ghi SAI")
    x.add_argument("id")
    x.add_argument("--text")
    x.add_argument("--section")
    x.add_argument("--subject")
    x.add_argument("--due")
    x.add_argument("--source")
    x = bs.add_parser("end", help="Không còn đúng / đã xong → 'trước đây'")
    x.add_argument("id")
    x.add_argument("--note")
    x = bs.add_parser("forget", help="Quên giúp: xóa hẳn khỏi sổ (kể cả lịch sử)")
    x.add_argument("ids", nargs="+")
    x = bs.add_parser("confirm", help="Khôi nói 'đúng' cho điều cũ")
    x.add_argument("ids", nargs="+")
    for name, hlp in (("pin", "Ghim lên hồ sơ"), ("promote", "LifeOS đưa lên hồ sơ"), ("unpin", "Bỏ khỏi hồ sơ")):
        x = bs.add_parser(name, help=hlp)
        x.add_argument("id")
    x = bs.add_parser("propose", help="Bot quét nguồn đề xuất một điều (Khôi duyệt trong báo cáo tối)")
    x.add_argument("--by", required=True)
    x.add_argument("--text", required=True)
    x.add_argument("--source", required=True, help="Thấy ở đâu, ví dụ 'Zalo nhóm học'")
    x.add_argument("--section", default="khac")
    x.add_argument("--subject")
    x = bs.add_parser("report", help="Khối 🧠 cho báo cáo 21:00 (--mark sau khi đã gửi)")
    x.add_argument("--mark", action="store_true")
    x = bs.add_parser("accept", help='Khôi: "ghi a" / "ghi hết"')
    x.add_argument("ids", nargs="+")
    x = bs.add_parser("reject", help='Khôi: "bỏ b"')
    x.add_argument("ids", nargs="+")
    x = bs.add_parser("journal", help="Nhật ký chuyện đã nói")
    js = x.add_subparsers(dest="jaction", required=True)
    j = js.add_parser("add")
    j.add_argument("--by", default="lifeos")
    j.add_argument("--text")
    j.add_argument("--private", action="store_true", help="Chuyện nhạy cảm: chỉ ghi 'có nói chuyện riêng'")
    j = js.add_parser("show")
    j.add_argument("--date")
    j.add_argument("--days", type=int)
    j.add_argument("--month", help="YYYY-MM")
    j = js.add_parser("replace", help="Gộp nhật ký một ngày còn 3–5 dòng")
    j.add_argument("--date", default="today")
    j.add_argument("--text", action="append", required=True)
    j.add_argument("--by", default="lifeos")
    x = bs.add_parser("kho", help='Kho "lưu cái này"')
    ks = x.add_subparsers(dest="kaction", required=True)
    k = ks.add_parser("add")
    k.add_argument("--title", required=True)
    k.add_argument("--summary")
    k.add_argument("--tag", action="append", default=[])
    k.add_argument("--url")
    k.add_argument("--drive", help="Link file gốc trên Drive (thư mục 'LifeOS · Kho')")
    k.add_argument("--kind", default="link", help="link · anh · video · file · ghi_chu")
    k.add_argument("--by", default="lifeos")
    k = ks.add_parser("list")
    k.add_argument("--tag")
    k.add_argument("--limit", type=int, default=10)
    bs.add_parser("dupes", help="Cặp điều có vẻ trùng (Chủ nhật)")
    x = bs.add_parser("merge", help="Gộp: giữ KEEP, gộp DROP vào")
    x.add_argument("keep")
    x.add_argument("drop")
    x = bs.add_parser("unmerge", help="Gộp nhầm → tách lại")
    x.add_argument("id")
    bs.add_parser("tidy", help="'Đang dở' quá hạn → 'trước đây' (nightly tự chạy)")
    bs.add_parser("page", help="Dựng dashboard/tri_nho.md cho Grok Page 'LifeOS · Trí nhớ'")
    bs.add_parser("stats", help="Đếm số điều theo mục / nguồn")
    bs.add_parser("backup", help="Gói bản sao lưu theo thứ (Tiko 02:15)")
    x = bs.add_parser("restore", help="Khôi phục từ bản sao lưu (mặc định chỉ xem trước)")
    x.add_argument("file")
    x.add_argument("--apply", action="store_true")


def _brain_run(a, cfg) -> dict:
    act = a.action
    if act == "core":
        return brain.core(cfg)
    if act == "search":
        return brain.search(" ".join(a.query), a.limit)
    if act == "show":
        return brain.show(" ".join(a.name))
    if act == "add":
        return brain.add(a.section, a.text, subject=a.subject, tags=a.tag, due=a.due, core=a.core, pin=a.pin,
                         sensitive=a.sensitive, by=a.by, origin=a.origin, replaces=a.replaces, source=a.source)
    if act == "edit":
        return brain.edit(a.id, text=a.text, section=a.section, subject=a.subject, due=a.due, source=a.source)
    if act == "end":
        return brain.end(a.id, a.note)
    if act == "forget":
        return brain.forget(a.ids)
    if act == "confirm":
        return brain.confirm(a.ids)
    if act == "pin":
        return brain.set_flags(a.id, pin=True, core=True)
    if act == "promote":
        return brain.set_flags(a.id, core=True)
    if act == "unpin":
        return brain.set_flags(a.id, pin=False, core=False)
    if act == "propose":
        return brain.propose(a.by, a.text, a.source, a.section, a.subject)
    if act == "report":
        return brain.report(cfg, mark=a.mark)
    if act == "accept":
        return brain.accept(a.ids)
    if act == "reject":
        return brain.reject(a.ids)
    if act == "journal":
        if a.jaction == "add":
            return brain.journal_add(a.by, a.text, a.private)
        if a.jaction == "replace":
            return brain.journal_replace(_day(a.date), a.text, a.by)
        return brain.journal_show(_day(a.date) if a.date else None, a.days, a.month)
    if act == "kho":
        if a.kaction == "add":
            return brain.kho_add(a.title, a.summary, a.tag, a.url, a.drive, a.kind, a.by)
        return brain.kho_list(a.tag, a.limit)
    if act == "dupes":
        return brain.dupes()
    if act == "merge":
        return brain.merge(a.keep, a.drop)
    if act == "unmerge":
        return brain.unmerge(a.id)
    if act == "tidy":
        return brain.tidy()
    if act == "page":
        return brain.page(cfg)
    if act == "stats":
        return brain.stats()
    if act == "backup":
        return brain.backup()
    return brain.restore(a.file, a.apply)


def _brief(item: dict) -> dict:
    return {k: item.get(k) for k in ("id", "domain", "title", "level_label", "reasons", "due_label", "start_label", "url")}


if __name__ == "__main__":
    sys.exit(main())
