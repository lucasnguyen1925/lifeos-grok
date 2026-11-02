"""Đường dẫn, giờ Việt Nam, đọc/ghi file dùng chung cho mọi script LifeOS.

Chỉ dùng thư viện chuẩn của Python (không cần pip install).
"""
from __future__ import annotations

import json
import os
import tempfile
import tomllib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Việt Nam không có giờ mùa hè: dùng cố định UTC+7, không phụ thuộc $TZ hay tzdata.
VN = timezone(timedelta(hours=7))

WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

DOMAINS = ("hoctap", "congty", "canhan")
BOTS = ("lifeos", "tiko", "hoctap", "congty", "canhan", "zalo")


def root() -> Path:
    """Thư mục dữ liệu LifeOS. Mặc định /workspace/lifeos; đổi bằng biến LIFEOS_ROOT (dùng cho test)."""
    return Path(os.environ.get("LIFEOS_ROOT", "/workspace/lifeos"))


def path(*parts: str) -> Path:
    return root().joinpath(*parts)


def now() -> datetime:
    """Giờ hiện tại theo giờ Việt Nam. Đặt LIFEOS_NOW (ISO) để giả lập khi test."""
    fake = os.environ.get("LIFEOS_NOW")
    if fake:
        return parse_dt(fake)
    return datetime.now(VN)


def today() -> date:
    return now().date()


def parse_dt(value: str | None) -> datetime | None:
    """Đọc chuỗi ISO 8601. Chuỗi không có múi giờ được hiểu là giờ Việt Nam."""
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=VN)
    return dt.astimezone(VN)


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(VN).isoformat(timespec="minutes") if dt else None


def vn_date(d: date | datetime) -> str:
    """'Thứ 2, 02/11' — LifeOS dùng chuỗi này, không tự suy thứ."""
    if isinstance(d, datetime):
        d = d.astimezone(VN).date()
    return f"{WEEKDAYS[d.weekday()]}, {d:%d/%m}"


def vn_datetime(dt: datetime) -> str:
    dt = dt.astimezone(VN)
    return f"{dt:%H:%M} {vn_date(dt)}"


def vn_deadline(dt: datetime) -> str:
    """Nhãn hạn chót. Hạn đúng 00:00 thực chất là hết ngày hôm trước: '00:00 Thứ 6, 06/11' dễ bị hiểu nhầm
    thành sáng thứ 6 → ghi 'hết ngày Thứ 5, 05/11 (00:00 Thứ 6, 06/11)'."""
    dt = dt.astimezone(VN)
    if dt.hour == 0 and dt.minute == 0:
        return f"hết ngày {vn_date(dt - timedelta(days=1))} (00:00 {vn_date(dt)})"
    return vn_datetime(dt)


def load_config() -> dict[str, Any]:
    """Đọc config.toml (nằm trên máy bot, không có trong repo)."""
    cfg_path = Path(os.environ.get("LIFEOS_CONFIG", str(path("config.toml"))))
    with cfg_path.open("rb") as f:
        return tomllib.load(f)


def page_changed(key: str, text: str, mark: bool = False) -> bool:
    """Nội dung Grok Page có khác bản bot ĐÃ ĐĂNG lần trước không (bỏ dòng "_Cập nhật …" vì giờ nào cũng đổi).
    Không đổi thì bot khỏi viết lại Page (tiết kiệm credit). `mark=True`: bot vừa đăng xong → ghi nhớ bản này."""
    import hashlib
    body = "\n".join(line for line in text.split("\n") if not line.startswith("_Cập nhật"))
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    state = read_json(path("state", "page_published.json"), {}) or {}
    changed = state.get(key) != digest
    if mark:
        state[key] = digest
        write_json(path("state", "page_published.json"), state)
    return changed


def read_json(p: Path, default: Any = None) -> Any:
    try:
        with p.open(encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_json(p: Path, data: Any) -> None:
    """Ghi an toàn: ghi ra file tạm rồi đổi tên, để bot khác không bao giờ đọc phải file ghi dở."""
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def append_jsonl(p: Path, record: dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    try:
        with p.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []
