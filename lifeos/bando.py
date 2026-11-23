"""Bản đồ phân công + việc LifeOS đã giao cho bot khác (SPEC §5e).

Hai phần của bản đồ:
    1. Phân công  — mảng nào, nguồn nào, loại việc nào → bot nào phụ trách (config.toml [phan_cong.<bot>],
                    thiếu thì dùng mặc định bên dưới).
    2. Kết nối    — kết nối của tài khoản Grok (chung cho mọi bot) đang có hay chưa. Vận hành ghi bằng lệnh,
                    lưu ở state/ket_noi.json.
    Mỗi vai còn ghi bot thật nào đang giữ (state/doi_bot.json) — repo không ghi tên riêng của bot.

    python3 -m lifeos bando show
    python3 -m lifeos bando ket-noi "Drive trường" --trang-thai ok --loai Drive        # Vận hành
    python3 -m lifeos bando giu-vai vanhanh "<tên bot>"                                # ai đang giữ vai
    python3 -m lifeos bando xoa-ket-noi "<tên>"
    python3 -m lifeos giao add --to hoctap --viec "Tìm sheet phân công nhóm X trong Drive trường"   # LifeOS
    python3 -m lifeos giao done g3 --ket-qua "…"
    python3 -m lifeos giao list | check [--mark]

Bản đồ được in luôn trong `brain core`, nên cả 6 bot đọc mỗi lượt.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .common import BOTS, ROLE_NAMES, bot_id, iso, now, parse_dt, path, read_json, role_name, write_json

DEFAULT_PHAN_CONG: dict[str, dict[str, Any]] = {
    "hoctap": {"mang": "Mọi thứ của trường",
               "nguon": ["Mail trường", "Lịch trường", "Drive trường", "BKeL", "MyBK", "AAO", "Zalo nhóm lớp"],
               "viec": ["tìm tài liệu, thông tin môn học", "đọc file nhóm môn", "kiểm tra hạn, điểm, lịch thi",
                        "quét lại ngay"]},
    "congty": {"mang": "Việc part-time",
               "nguon": ["Mail công ty", "Lịch công ty", "Zalo công việc"],
               "viec": ["tìm mail, lịch công ty", "quét lại ngay"]},
    "canhan": {"mang": "Đời sống",
               "nguon": ["Gmail cá nhân", "Lịch cá nhân", "Reminders (đọc)", "Danh bạ", "Zalo bạn bè, gia đình"],
               "viec": ["tìm mail, lịch cá nhân", "ai là ai trong danh bạ", "quét lại ngay"]},
    "zalo": {"mang": "Zalo Web (bot duy nhất được mở)",
             "nguon": ["Phiên Zalo Web"],
             "viec": ["đọc lại một nhóm/hội thoại khi được nhờ (chỉ đọc)"]},
    "lifeos": {"mang": "Nói chuyện với Khôi",
               "nguon": ["Drive cá nhân", "Đặt Reminder + báo thức", "Lịch LifeOS", "Sổ nhớ"],
               "viec": ["kế hoạch, nhắc, soạn nháp, nhớ, lưu kho", "giao việc cho đúng bot"]},
    "vanhanh": {"mang": "Giữ LifeOS luôn chạy, chạy đúng giờ",
                "nguon": ["Kết nối, đăng nhập", "Sao lưu"],
                "viec": ["sự cố, bot lỡ giờ, kết nối mới, cập nhật bộ cài"]},
}
ORDER = ["hoctap", "congty", "canhan", "zalo", "lifeos", "vanhanh"]
NAMES = ROLE_NAMES
STATUSES = {"ok": "✅", "chua_ket_noi": "❌ chưa kết nối", "chua_cai": "❌ chưa cài",
            "het_phien": "⚠️ hết phiên đăng nhập", "hong": "⚠️ hỏng"}
DEFAULT_WAIT_MINUTES = 10


def _fold(text: str) -> str:
    from .brain import fold
    return fold(text)


# ---------------------------------------------------------------- phân công

def assignments(cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Phân công hiện hành: mặc định, đè bằng config.toml [phan_cong.<bot>] nếu có."""
    out = {bot: dict(v) for bot, v in DEFAULT_PHAN_CONG.items()}
    for bot, v in ((cfg or {}).get("phan_cong") or {}).items():
        if bot in out and isinstance(v, dict):
            out[bot].update({k: v[k] for k in ("mang", "nguon", "viec") if k in v})
    return out


def owner_of(source: str, cfg: dict[str, Any] | None = None) -> str | None:
    """Nguồn này do bot nào phụ trách (so khớp không dấu, một phần tên)."""
    key = _fold(source)
    for bot in ORDER:
        if any(key and (key in _fold(n) or _fold(n) in key) for n in assignments(cfg)[bot]["nguon"]):
            return bot
    return None


# ---------------------------------------------------------------- bot nào đang giữ vai

def _holders_path():
    return path("state", "doi_bot.json")


def holders() -> dict[str, str]:
    """{vai: tên bot thật đang giữ}. Tên thật chỉ nằm trên máy bot, không lên repo."""
    items = (read_json(_holders_path(), None) or {}).get("items", {})
    return {bot_id(k): v["ten"] for k, v in items.items() if v.get("ten")}


def set_holder(role: str, name: str | None, t: datetime | None = None) -> dict[str, Any]:
    """Ghi bot nào đang giữ vai. name rỗng/None = bỏ ghi."""
    role = bot_id(role)
    if role not in BOTS:
        raise ValueError(f"Vai phải là một trong {', '.join(BOTS)}.")
    name = " ".join((name or "").split())
    data = read_json(_holders_path(), None) or {"items": {}}
    if name:
        data["items"][role] = {"ten": name, "updated_at": iso(t or now())}
    else:
        data["items"].pop(role, None)
    write_json(_holders_path(), data)
    return {"ok": True, "vai": NAMES[role], "dang_giu": name or None}


def holder_label(role: str) -> str:
    """'Vận hành (bot <tên>)' nếu đã ghi, không thì 'Vận hành'."""
    role = bot_id(role)
    who = holders().get(role)
    return f"{NAMES[role]} (bot {who})" if who else NAMES[role]


# ---------------------------------------------------------------- kết nối

def _conn_path():
    return path("state", "ket_noi.json")


def connections() -> list[dict[str, Any]]:
    return (read_json(_conn_path(), None) or {}).get("items", [])


def set_connection(name: str, status: str, kind: str | None = None, note: str | None = None,
                   t: datetime | None = None) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"--trang-thai phải là một trong {', '.join(STATUSES)}.")
    name = " ".join(name.split())
    if not name:
        raise ValueError("Thiếu tên kết nối.")
    t = t or now()
    data = read_json(_conn_path(), None) or {"items": []}
    hit = next((c for c in data["items"] if _fold(c["name"]) == _fold(name)), None)
    if hit is None:
        hit = {"name": name}
        data["items"].append(hit)
    hit.update(status=status, updated_at=iso(t))
    if kind is not None:
        hit["kind"] = kind or None
    if note is not None:
        hit["note"] = note or None
    write_json(_conn_path(), data)
    return {"ok": True, "connection": hit}


def remove_connection(name: str) -> dict[str, Any]:
    data = read_json(_conn_path(), None) or {"items": []}
    before = len(data["items"])
    data["items"] = [c for c in data["items"] if _fold(c["name"]) != _fold(name)]
    write_json(_conn_path(), data)
    return {"ok": len(data["items"]) < before}


# ---------------------------------------------------------------- hiển thị

def render(cfg: dict[str, Any] | None = None) -> str:
    """Bản đồ gọn (~9 dòng) để in trong hồ sơ ngắn."""
    conns = connections()
    bad = {_fold(c["name"]): c for c in conns if c["status"] != "ok"}

    def mark(src: str) -> str:
        c = bad.get(_fold(src))
        return f"{src} ({STATUSES[c['status']]})" if c else src

    who = holders()
    lines = ["🗺️ BẢN ĐỒ PHÂN CÔNG — việc thuộc mảng nào thì giao đúng bot đó, đừng tự lục nguồn của bot khác"]
    for bot in ORDER:
        a = assignments(cfg)[bot]
        held = f" (bot {who[bot]})" if bot in who else ""
        lines.append(f"- {NAMES[bot]}{held} · {a['mang']}: {', '.join(mark(s) for s in a['nguon'])} → {'; '.join(a['viec'])}")
    if conns:
        parts = []
        for c in conns:
            note = f" — {c['note']}" if c.get("note") else ""
            parts.append(f"{STATUSES[c['status']]} {c['name']}{note}" if c["status"] == "ok"
                         else f"{c['name']}: {STATUSES[c['status']]}{note}")
        lines.append("🔌 Kết nối (chung cho mọi bot, Vận hành cập nhật): " + " · ".join(parts))
    else:
        lines.append("🔌 Kết nối: chưa ghi — Vận hành ghi bằng `python3 -m lifeos bando ket-noi …`")
    return "\n".join(lines)


def show(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"text": render(cfg), "assignments": assignments(cfg), "holders": holders(), "connections": connections()}


# ---------------------------------------------------------------- việc đã giao (LifeOS)

def _giao_path():
    return path("state", "giao_viec.json")


def _giao() -> dict[str, Any]:
    return read_json(_giao_path(), None) or {"next": 1, "items": []}


def delegate(to: str, task: str, minutes: int = DEFAULT_WAIT_MINUTES, t: datetime | None = None) -> dict[str, Any]:
    to = bot_id(to)
    if to not in BOTS or to == "lifeos":
        raise ValueError(f"--to phải là một trong {', '.join(b for b in BOTS if b != 'lifeos')}.")
    task = " ".join((task or "").split())
    if not task:
        raise ValueError("Thiếu --viec: giao việc gì, tìm ở đâu, cần trả lời gì.")
    t = t or now()
    data = _giao()
    gid = f"g{data['next']}"
    data["next"] += 1
    item = {"id": gid, "to": to, "task": task, "created_at": iso(t), "due_at": iso(t + timedelta(minutes=minutes)),
            "status": "open", "result": None, "done_at": None, "escalated_at": None}
    data["items"] = [x for x in data["items"] if x["status"] == "open"
                     or parse_dt(x["created_at"]) > t - timedelta(days=7)] + [item]
    write_json(_giao_path(), data)
    return {"ok": True, "id": gid, "due": f"{parse_dt(item['due_at']):%H:%M}",
            "message": f"[{gid}] {task} — làm xong trả lời LifeOS kèm mã {gid} và NGUỒN (nội quy mục 10, 11). "
                       "Không vào được nguồn nào thì nói rõ là không vào được."}


def finish(gid: str, result: str | None = None, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    data = _giao()
    item = next((x for x in data["items"] if x["id"] == gid), None)
    if item is None:
        raise ValueError(f"Không có việc đã giao mã {gid}.")
    item.update(status="done", result=result, done_at=iso(t))
    write_json(_giao_path(), data)
    return {"ok": True, "item": item}


def open_items() -> list[dict[str, Any]]:
    return [x for x in _giao()["items"] if x["status"] in {"open", "escalated"}]


def overdue(t: datetime | None = None, mark: bool = False) -> dict[str, Any]:
    """Việc quá hạn chờ (mặc định 10 phút) chưa có trả lời. --mark sau khi đã báo Khôi + nhờ Vận hành."""
    t = t or now()
    data = _giao()
    late = [x for x in data["items"] if x["status"] == "open" and parse_dt(x["due_at"]) <= t]
    if mark and late:
        for x in late:
            x.update(status="escalated", escalated_at=iso(t))
        write_json(_giao_path(), data)
    return {"late": [{"id": x["id"], "to": role_name(x["to"]), "task": x["task"],
                      "since": f"{parse_dt(x['created_at']):%H:%M %d/%m}"} for x in late], "marked": mark}


def render_waiting(t: datetime | None = None) -> str:
    """Dòng '⏳' cho hồ sơ ngắn: việc đang chờ bot khác trả lời."""
    t = t or now()
    rows = []
    for x in open_items():
        late = parse_dt(x["due_at"]) <= t
        flag = " — QUÁ HẠN, đã báo Khôi" if x["status"] == "escalated" else (" — QUÁ HẠN: báo Khôi + nhờ Vận hành" if late else "")
        rows.append(f"- {x['id']} {role_name(x['to'])}: {x['task']} (giao {parse_dt(x['created_at']):%H:%M}){flag}")
    return "\n".join(["⏳ ĐANG CHỜ BOT KHÁC TRẢ LỜI"] + rows) if rows else ""
