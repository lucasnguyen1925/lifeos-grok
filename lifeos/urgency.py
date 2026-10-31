"""Luật xếp độ gấp — viết cứng, bot không tự đánh giá.

Mức: 1 = 🔴 GẤP · 2 = 🟠 CAO · 3 = 🟡 TRUNG BÌNH · 4 = ⚪ ĐỂ BIẾT
Mỗi việc lấy mức CAO NHẤT mà nó thỏa (số nhỏ nhất).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .common import parse_dt

RED, ORANGE, YELLOW, WHITE = 1, 2, 3, 4
LABELS = {RED: "🔴 GẤP", ORANGE: "🟠 CAO", YELLOW: "🟡 TRUNG BÌNH", WHITE: "⚪ ĐỂ BIẾT"}

DEFAULT_URGENT_KEYWORDS = ["hoãn thi", "nghỉ học", "đổi phòng", "đổi lịch thi", "khẩn", "hoãn", "huỷ", "hủy"]
# Thư báo mail của Khôi bị trả về (SPEC §5d). Bot đọc mail ghi thành notice "Mail bị trả về: …".
DEFAULT_BOUNCE_KEYWORDS = ["bị trả về", "không tìm thấy địa chỉ", "address not found", "undeliverable",
                           "delivery status notification", "mail delivery subsystem", "delivery has failed",
                           "message not delivered", "không gửi được thư"]
SCHEDULE_KINDS = {"class", "exam", "work_shift", "meeting", "event"}
DEADLINE_KINDS = {"deadline", "quiz", "registration", "payment", "task"}
NEW_ITEM_KINDS = {"deadline", "quiz", "exam", "registration"}


def due_dt(item: dict[str, Any]) -> datetime | None:
    """Hạn chót của việc. Hạn chỉ có ngày (không giờ) = 23:59 ngày đó. Lịch thi: hạn = giờ bắt đầu."""
    raw = item.get("due") or (item.get("start") if item.get("kind") == "exam" else None)
    if not raw:
        return None
    dt = parse_dt(raw)
    if "T" not in raw:
        dt = dt.replace(hour=23, minute=59)
    return dt


def is_vip(sender: str | None, cfg: dict[str, Any]) -> bool:
    if not sender:
        return False
    s = sender.casefold()
    for person in cfg.get("people", {}).get("vip", []):
        names = [person.get("name", "")] + person.get("aliases", [])
        if any(n and n.casefold() in s for n in names):
            return True
    return False


def classify(
    item: dict[str, Any],
    now: datetime,
    cfg: dict[str, Any],
    *,
    first_seen: datetime | None = None,
    in_conflict: bool = False,
) -> tuple[int, list[str]]:
    """Trả về (mức, lý do). Lý do là câu ngắn tiếng Việt để LifeOS dẫn lại."""
    candidates: list[tuple[int, str]] = []
    kind = item["kind"]
    due = due_dt(item)
    start = parse_dt(item.get("start"))
    keywords = [k.casefold() for k in cfg.get("rules", {}).get("urgent_keywords", DEFAULT_URGENT_KEYWORDS)]
    text = f"{item['title']} {item.get('notes') or ''}".casefold()

    if due:
        left = due - now
        if left < timedelta(0):
            if -left <= timedelta(days=7) and kind in DEADLINE_KINDS | {"exam"}:
                candidates.append((RED, "đã quá hạn, chưa đánh dấu xong"))
        elif left <= timedelta(hours=24):
            candidates.append((RED, "hạn trong 24 giờ"))
        elif left <= timedelta(hours=72):
            candidates.append((ORANGE, "hạn trong 3 ngày"))
        elif left <= timedelta(days=7):
            candidates.append((YELLOW, "hạn trong 7 ngày"))
        if kind == "payment" and timedelta(0) <= left <= timedelta(days=7):
            candidates.append((ORANGE, "khoản phải đóng trong 7 ngày"))

    if item.get("changed"):
        when = start or due
        if when and timedelta(0) <= when - now <= timedelta(hours=48):
            note = item.get("change_note") or "có thay đổi"
            candidates.append((RED, f"vừa thay đổi ({note}), diễn ra trong 48 giờ"))
        else:
            candidates.append((ORANGE, "vừa có thay đổi"))

    if in_conflict:
        candidates.append((RED, "trùng lịch trong 48 giờ tới"))

    bounce = [k.casefold() for k in cfg.get("rules", {}).get("bounce_keywords", DEFAULT_BOUNCE_KEYWORDS)]
    if kind == "notice" and any(k in text for k in bounce):
        received = parse_dt(item.get("received_at")) or first_seen
        if received is None or now - received <= timedelta(hours=72):
            candidates.append((RED, "mail bạn gửi bị trả về — người nhận CHƯA nhận được"))
    elif kind == "notice" and any(k in text for k in keywords):
        received = parse_dt(item.get("received_at")) or first_seen
        if received is None or now - received <= timedelta(hours=72):
            candidates.append((RED, "thông báo có từ khóa khẩn"))

    if item.get("needs_reply"):
        received = parse_dt(item.get("received_at")) or first_seen
        vip = is_vip(item.get("from"), cfg)
        if vip and received and now - received > timedelta(hours=12):
            candidates.append((RED, "người quan trọng chờ trả lời hơn 12 giờ"))
        else:
            candidates.append((ORANGE, "cần bạn trả lời"))

    if kind in NEW_ITEM_KINDS and first_seen and now - first_seen <= timedelta(hours=24):
        candidates.append((ORANGE, "mới xuất hiện"))

    if kind == "registration" and start and timedelta(0) <= start - now <= timedelta(hours=72):
        candidates.append((ORANGE, "sắp mở đăng ký"))

    if kind == "notice" or item.get("mentions_khoi"):
        candidates.append((YELLOW, "thông báo / có nhắc đến bạn"))

    if not candidates:
        return WHITE, []
    level = min(c[0] for c in candidates)
    return level, [reason for lvl, reason in candidates if lvl == level]
