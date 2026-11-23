"""Hộp thư Vận hành → trợ lý LifeOS (SPEC §5h, V3).

Vận hành chạy ngầm. Việc THƯỜNG (sự cố đã tự xử lý, nguồn lỗi lâu, việc cần Khôi quyết, báo cáo hệ thống tuần)
không nhắn thẳng Khôi mà bỏ vào hộp thư này; LifeOS đưa vào báo cáo kế tiếp. Việc GẤP cần Khôi làm ngay
(mất đăng nhập cần Khôi ra tay, Zalo đòi xác nhận trên điện thoại) thì Vận hành nhắn thẳng Khôi và vẫn ghi
vào đây với --gap để LifeOS biết mà không nhắc lại.

    python3 -m lifeos vanhanh add --text "Bot Học tập lỡ lần quét 11:30, đã cho chạy lại, ổn"
    python3 -m lifeos vanhanh add --tuan --text "<báo cáo hệ thống tuần, ≤ 10 dòng>"
    python3 -m lifeos vanhanh add --gap --text "Đã nhắn Khôi: Zalo cần xác nhận đồng bộ trên điện thoại"
    python3 -m lifeos vanhanh list [--mark]        # LifeOS, trong báo cáo / kế hoạch tuần
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .common import iso, now, parse_dt, path, read_json, write_json

KEEP_DAYS = 30
LOAI = {"viec": "⚙️", "tuan": "🛠", "gap": "🚨"}


def _path():
    return path("state", "vanhanh_hopthu.json")


def _load() -> dict[str, Any]:
    return read_json(_path(), None) or {"next": 1, "items": []}


def add(text: str, loai: str = "viec", t: datetime | None = None) -> dict[str, Any]:
    if loai not in LOAI:
        raise ValueError(f"loại phải là một trong {', '.join(LOAI)}.")
    text = " ".join((text or "").split()) if loai != "tuan" else (text or "").strip()
    if not text:
        raise ValueError("Thiếu --text.")
    t = t or now()
    data = _load()
    for x in data["items"]:
        if x["status"] == "moi" and x["loai"] == loai and x["text"] == text:
            return {"ok": True, "id": x["id"], "already": True, "note": "Tin này đang chờ LifeOS đưa Khôi, không ghi lại."}
    item = {"id": f"vh{data['next']}", "at": iso(t), "loai": loai, "text": text,
            "status": "da_bao" if loai == "gap" else "moi"}
    data["next"] += 1
    cutoff = t - timedelta(days=KEEP_DAYS)
    data["items"] = [x for x in data["items"] if parse_dt(x["at"]) > cutoff] + [item]
    write_json(_path(), data)
    return {"ok": True, "id": item["id"]}


def list_items(mark: bool = False, t: datetime | None = None) -> dict[str, Any]:
    """Tin mới cho báo cáo của LifeOS. `gap_24h`: việc gấp Vận hành đã nhắn thẳng Khôi — đừng nhắc lại y nguyên."""
    t = t or now()
    data = _load()
    new = [x for x in data["items"] if x["status"] == "moi"]
    gap = [x for x in data["items"] if x["loai"] == "gap" and parse_dt(x["at"]) > t - timedelta(hours=24)]
    lines = []
    for x in new:
        if x["loai"] == "tuan":
            lines.append(f"{LOAI['tuan']} Hệ thống tuần qua (Vận hành):\n{x['text']}")
        else:
            lines.append(f"{LOAI['viec']} {x['text']}")
    if mark and new:
        for x in new:
            x.update(status="da_dua", dua_at=iso(t))
        write_json(_path(), data)
    return {"count": len(new), "text": "\n".join(lines),
            "items": [{k: x[k] for k in ("id", "at", "loai", "text")} for x in new],
            "gap_24h": [{"at": x["at"], "text": x["text"]} for x in gap], "marked": bool(mark and new)}
