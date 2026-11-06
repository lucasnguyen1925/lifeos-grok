"""Định dạng chuẩn của file dữ liệu mỗi mảng (data/<mảng>.json) và kiểm tra lỗi.

Bot mảng ghi file xong phải chạy:  python3 -m lifeos validate data/hoctap.json
Có lỗi thì sửa theo thông báo rồi chạy lại cho tới khi báo OK.
"""
from __future__ import annotations

from typing import Any

from .common import DOMAINS, parse_dt

KINDS = {
    "deadline",      # hạn nộp bài/việc có hạn chót
    "quiz",          # quiz/bài kiểm tra trên LMS (có giờ đóng)
    "exam",          # lịch thi
    "registration",  # đăng ký môn/thi (có cửa sổ mở–đóng)
    "payment",       # học phí, BKPay, khoản phải trả
    "class",         # buổi học (có start/end)
    "work_shift",    # ca/buổi lên công ty (có start/end)
    "meeting",       # cuộc họp, lời mời họp
    "event",         # sự kiện lịch khác (có start/end)
    "notice",        # thông báo trường/khoa/công ty
    "message",       # tin nhắn Zalo
    "email",         # mail
    "task",          # việc cần làm khác
}
STATUSES = {"open", "done", "cancelled"}
SOURCE_STATUSES = {"ok", "needs_login", "error", "skipped"}
TIMED_KINDS = {"class", "work_shift", "meeting", "event", "exam"}

ITEM_FIELDS: dict[str, tuple[type | tuple[type, ...], bool]] = {
    # tên: (kiểu, bắt buộc?)
    "id": (str, True),
    "domain": (str, True),
    "source": (str, True),
    "kind": (str, True),
    "title": (str, True),
    "status": (str, True),
    "due": ((str, type(None)), False),
    "start": ((str, type(None)), False),
    "end": ((str, type(None)), False),
    "url": ((str, type(None)), False),
    "from": ((str, type(None)), False),
    "needs_reply": (bool, False),
    "mentions_khoi": (bool, False),
    "changed": (bool, False),
    "change_note": ((str, type(None)), False),
    "first_seen": ((str, type(None)), False),
    "received_at": ((str, type(None)), False),
    "keywords": (list, False),
    "est_minutes": ((int, type(None)), False),
    "location": ((str, type(None)), False),
    "notes": ((str, type(None)), False),
}


def validate_domain_file(data: Any, expected_domain: str | None = None) -> list[str]:
    """Trả về danh sách lỗi (rỗng = hợp lệ). Thông báo viết sao cho bot tự sửa được."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["File phải là một object JSON {bot, generated_at, sources, items}."]

    for key in ("bot", "generated_at", "sources", "items"):
        if key not in data:
            errors.append(f"Thiếu trường '{key}' ở cấp ngoài cùng.")
    if errors:
        return errors

    if data["bot"] not in DOMAINS:
        errors.append(f"'bot' phải là một trong {sorted(DOMAINS)}, đang là {data['bot']!r}.")
    if expected_domain and data["bot"] != expected_domain:
        errors.append(f"'bot' phải là {expected_domain!r} cho file này.")
    errors += _check_dt(data["generated_at"], "generated_at")

    if not isinstance(data["sources"], dict):
        errors.append("'sources' phải là object {tên_nguồn: {status, detail}}.")
    else:
        for name, src in data["sources"].items():
            if not isinstance(src, dict) or src.get("status") not in SOURCE_STATUSES:
                errors.append(
                    f"sources.{name}.status phải là một trong {sorted(SOURCE_STATUSES)}."
                )

    if not isinstance(data["items"], list):
        errors.append("'items' phải là một danh sách.")
        return errors

    seen: set[str] = set()
    for i, item in enumerate(data["items"]):
        errors += [f"items[{i}]: {e}" for e in validate_item(item)]
        item_id = item.get("id") if isinstance(item, dict) else None
        if item_id in seen:
            errors.append(f"items[{i}]: id {item_id!r} bị trùng.")
        seen.add(item_id)
    return errors


MAIL_ZALO_HINTS = ("mail", "zalo")
READ_KINDS = {"email", "message", "notice"}


def warnings_domain_file(data: Any) -> list[str]:
    """Cảnh báo (KHÔNG phải lỗi, không chặn bot): chỗ ghi sai làm kế hoạch xếp việc nhanh quá dài (SPEC §5g M3)."""
    out: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return out
    for i, item in enumerate(data["items"]):
        if not isinstance(item, dict):
            continue
        kind, src = item.get("kind"), str(item.get("source") or "")
        label = f"items[{i}] ({item.get('id')})"
        if kind in {"task", "deadline"} and any(h in src.casefold() for h in MAIL_ZALO_HINTS):
            out.append(f"{label}: việc từ nguồn '{src}' ghi loại '{kind}'. Mail ghi 'email', tin Zalo ghi 'message' "
                       "(script tính thời lượng theo loại này; chỉ giữ 'task'/'deadline' nếu đó là việc thật cần làm lâu).")
        if kind in READ_KINDS and item.get("est_minutes"):
            out.append(f"{label}: 'est_minutes' của loại '{kind}' bị bỏ qua (script tự tính thời lượng). Xóa trường này đi.")
    return out


def validate_item(item: Any) -> list[str]:
    if not isinstance(item, dict):
        return ["mỗi item phải là object."]
    errors: list[str] = []
    for name, (typ, required) in ITEM_FIELDS.items():
        if name not in item:
            if required:
                errors.append(f"thiếu trường bắt buộc '{name}'.")
            continue
        if not isinstance(item[name], typ) or (typ is int and isinstance(item[name], bool)):
            errors.append(f"'{name}' sai kiểu dữ liệu.")
    unknown = set(item) - set(ITEM_FIELDS)
    if unknown:
        errors.append(f"trường lạ {sorted(unknown)} — xóa đi hoặc đưa vào 'notes'.")
    if errors:
        return errors

    if item["domain"] not in DOMAINS:
        errors.append(f"'domain' phải là một trong {sorted(DOMAINS)}.")
    if item["kind"] not in KINDS:
        errors.append(f"'kind' {item['kind']!r} không hợp lệ; dùng một trong {sorted(KINDS)}.")
    if item["status"] not in STATUSES:
        errors.append(f"'status' phải là một trong {sorted(STATUSES)}.")
    if not item["title"].strip():
        errors.append("'title' không được rỗng.")
    for field in ("due", "start", "end", "first_seen", "received_at"):
        if item.get(field):
            errors += _check_dt(item[field], field)
    if item["kind"] in TIMED_KINDS and not (item.get("start") and item.get("end")):
        if not (item["kind"] == "exam" and item.get("start")):
            errors.append(f"kind {item['kind']!r} cần có 'start' và 'end'.")
    if item["kind"] in ("class", "exam") and item.get("start") and "T" not in item["start"]:
        errors.append(
            f"kind {item['kind']!r} cần 'start' có GIỜ cụ thể, ví dụ 2026-11-02T13:00+07:00. Chỉ có ngày sẽ bị hiểu là 00:00 "
            "(kế hoạch tính sai giờ dậy). Bài kiểm tra trên lớp: lấy giờ buổi học của môn đó hôm đó; không biết giờ thì "
            "ghi kind 'deadline' với 'due' là ngày.")
    if item.get("start") and item.get("end") and not errors:
        if parse_dt(item["end"]) <= parse_dt(item["start"]):
            errors.append("'end' phải sau 'start'.")
    return errors


def _check_dt(value: Any, field: str) -> list[str]:
    if not isinstance(value, str):
        return [f"'{field}' phải là chuỗi ngày giờ ISO, ví dụ 2026-11-02T23:59+07:00."]
    try:
        dt = parse_dt(value)
    except ValueError:
        return [f"'{field}' = {value!r} không đúng dạng ISO, ví dụ 2026-11-02T23:59+07:00."]
    if "T" in value and value[-6] not in "+-" and not value.endswith("Z"):
        return [f"'{field}' = {value!r} thiếu múi giờ; thêm '+07:00'."]
    return [] if dt else [f"'{field}' rỗng."]
