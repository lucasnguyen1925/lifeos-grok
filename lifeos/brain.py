"""Sổ nhớ chung của đội bot LifeOS — bản gốc trí nhớ về Khôi (SPEC §5c).

Chỉ đọc/ghi bằng lệnh `python3 -m lifeos brain …`, không sửa tay file trong brain/.

    brain/so_nho.json            điều đáng nhớ: đang đúng + lịch sử "trước đây"
    brain/de_xuat.json           đề xuất của 4 bot quét nguồn, chờ Khôi duyệt
    brain/kho.json               đồ Khôi bảo "lưu" (link, ảnh, video, ghi chú…)
    brain/nhat_ky/<ngày>.json    nhật ký chuyện đã nói (giữ 90 ngày)
    brain/trang_thai.json        chữ cái a/b/c… của lần báo gần nhất
    brain/da_quen.jsonl          đã quên gì: chỉ id + giờ, KHÔNG giữ nội dung

Ba lớp (để bot không phải đọc cả sổ):
    1. `brain core`    hồ sơ ngắn ~40 dòng — đọc đầu mỗi lượt chat / mỗi lần chạy routine
    2. `brain search`  mục lục tìm nhanh (SQLite FTS5, gõ không dấu vẫn ra)
    3. `brain show`    "trang" chi tiết của một người / môn / dự án
"""
from __future__ import annotations

import fcntl
import re
import sqlite3
import string
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Iterator

from .common import (
    BOTS, append_jsonl, iso, now, parse_dt, path, read_json, vn_date, vn_datetime, write_json, write_text,
)

# Mục của sổ. 6 mục đầu là hồ sơ ngắn; "khac" chỉ nằm trong sổ, không lên hồ sơ.
SECTIONS: dict[str, tuple[str, str]] = {
    "ve_khoi": ("👤", "VỀ KHÔI"),
    "muc_tieu": ("🎯", "MỤC TIÊU"),
    "nguoi_quen": ("👥", "NGƯỜI QUEN"),
    "cach_lam_viec": ("⚙️", "CÁCH LÀM VIỆC"),
    "dang_do": ("🤝", "ĐANG DỞ"),
    "tranh": ("🚫", "TRÁNH"),
    "khac": ("📎", "KHÁC"),
}
CORE_LIMITS = {"ve_khoi": 8, "muc_tieu": 5, "nguoi_quen": 10, "cach_lam_viec": 7, "dang_do": 6, "tranh": 4}
SCAN_BOTS = ("hoctap", "congty", "canhan", "zalo")
BOT_NAMES = {"lifeos": "LifeOS", "tiko": "Tiko", "hoctap": "Học tập", "congty": "Công ty",
             "canhan": "Cá nhân", "zalo": "Zalo"}
ORIGINS = ("chat", "soat_chat", "grok", "notes", "de_xuat")
MIGRATED = {"grok", "notes"}          # chuyển từ trí nhớ cũ: không dồn vào dòng 🧠 tối
KHO_KINDS = ("link", "anh", "video", "file", "ghi_chu")
MAX_TEXT = 300
WEEKDAY_KEYS = ["thu2", "thu3", "thu4", "thu5", "thu6", "thu7", "cn"]
BACKUP_FOLDER = "LifeOS · Sao lưu"
PRIVATE_LINE = "có nói chuyện riêng"


# ---------------------------------------------------------------- tiện ích

def _p(*parts: str) -> Path:
    return path("brain", *parts)


@contextmanager
def _locked() -> Iterator[None]:
    """Nhiều bot cùng ghi sổ: khóa file để không ai ghi đè mất phần của người khác."""
    lock = _p(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def fold(text: str) -> str:
    """Bỏ dấu tiếng Việt, chữ thường, chỉ giữ chữ/số: 'Bạn Đạt' -> 'ban dat'."""
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(re.findall(r"\w+", text.casefold()))


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, fold(a), fold(b)).ratio()


# Chữ đệm: hai câu chỉ khác nhau mấy chữ này thì coi là cùng một ý. Không có "đã/đang/sẽ", "ở", "làm"… vì đổi nghĩa.
FILLER = {"la", "thi", "ma", "va", "voi", "rat", "han", "hon", "nhe", "nha", "oi", "nua", "roi", "cung",
          "nhung", "cac", "mot", "nay", "ay", "kia", "that"}


def same_meaning(a: str, b: str) -> bool:
    """Trùng chắc chắn (dùng khi ghi): giống hệt sau khi bỏ dấu/chấm phẩy, hoặc chỉ lệch nhau chữ đệm.
    'Bạn P …' và 'Bạn Q …' là KHÁC nhau. Trùng kiểu diễn đạt khác thì để LifeOS gộp mỗi Chủ nhật (`dupes`)."""
    fa, fb = fold(a), fold(b)
    return fa == fb or (set(fa.split()) ^ set(fb.split())) <= FILLER


def _settings(cfg: dict[str, Any] | None) -> dict[str, Any]:
    b = (cfg or {}).get("brain", {})
    limits = dict(CORE_LIMITS)
    limits.update({k: int(v) for k, v in b.get("core_limits", {}).items() if k in CORE_LIMITS})
    return {
        "limits": limits,
        "stale_days": int(b.get("stale_days", 180)),
        "stale_per_month": int(b.get("stale_per_month", 5)),
        "proposals_per_night": int(b.get("proposals_per_night", 3)),
        "proposal_max_asks": int(b.get("proposal_max_asks", 2)),
        "report_max_new": int(b.get("report_max_new", 5)),
        "page_recent_days": int(b.get("page_recent_days", 7)),
        "page_kho_items": int(b.get("page_kho_items", 10)),
    }


def _load_facts() -> dict[str, Any]:
    return read_json(_p("so_nho.json"), None) or {"next": 1, "facts": []}


def _load_props() -> dict[str, Any]:
    return read_json(_p("de_xuat.json"), None) or {"next": 1, "items": []}


def _load_kho() -> dict[str, Any]:
    return read_json(_p("kho.json"), None) or {"next": 1, "items": []}


def _state() -> dict[str, Any]:
    return read_json(_p("trang_thai.json"), None) or {}


def _new_id(store: dict[str, Any], prefix: str) -> str:
    n = store.get("next", 1)
    store["next"] = n + 1
    return f"{prefix}{n}"


def _clean_text(text: str | None) -> str:
    text = " ".join((text or "").split())
    if not text:
        raise ValueError("Thiếu nội dung (--text).")
    if len(text) > MAX_TEXT:
        raise ValueError(f"Ghi ngắn thôi: một điều một câu, tối đa {MAX_TEXT} ký tự (đang {len(text)}).")
    return text


def _parse_due(value: str | None) -> str | None:
    if not value:
        return None
    if "T" in value:
        return parse_dt(value).date().isoformat()
    return date.fromisoformat(value).isoformat()


def _check_bot(by: str) -> str:
    if by not in BOTS:
        raise ValueError(f"--by phải là một trong {', '.join(BOTS)}.")
    return by


def _find(facts: list[dict[str, Any]], fid: str) -> dict[str, Any]:
    for f in facts:
        if f["id"] == fid:
            return f
    raise ValueError(f"Không có điều nào mã {fid} trong sổ.")


def _resolve(token: str) -> str:
    """'a' → mã thật theo lần báo gần nhất; mã thật (m12, d3, k5…) giữ nguyên."""
    token = token.strip().rstrip(",").lower()
    if re.fullmatch(r"[a-z]", token):
        letters = _state().get("letters", {})
        if token not in letters:
            raise ValueError(f"Chữ '{token}' không có trong lần báo gần nhất.")
        return letters[token]
    return token


def _due_label(f: dict[str, Any]) -> str:
    return f" (hạn {vn_date(date.fromisoformat(f['due']))})" if f.get("due") else ""


def _month_label(value: str | None) -> str:
    dt = parse_dt(value)
    return f"{dt:%m/%Y}" if dt else "?"


# ---------------------------------------------------------------- ghi / sửa / quên

def add(section: str, text: str, *, subject: str | None = None, tags: Iterable[str] = (), due: str | None = None,
        core: bool = False, pin: bool = False, sensitive: bool = False, by: str = "lifeos", origin: str = "chat",
        replaces: str | None = None, source: str | None = None, t: datetime | None = None) -> dict[str, Any]:
    """Ghi một điều. Trùng với điều đang đúng → không ghi thêm, chỉ làm mới 'lần cuối nhắc tới'.

    source = điều này lấy từ đâu ("trang môn GT2 trên BKeL", "Khôi kể"…). Bắt buộc với dữ kiện dùng để
    liên lạc/làm việc (email, số điện thoại, link, phòng…) — luật "không bịa" (SPEC §5d).
    """
    if section not in SECTIONS:
        raise ValueError(f"--section phải là một trong {', '.join(SECTIONS)}.")
    if origin not in ORIGINS:
        raise ValueError(f"--origin phải là một trong {', '.join(ORIGINS)}.")
    text, by, t = _clean_text(text), _check_bot(by), t or now()
    tags = [x.strip() for x in tags if x and x.strip()]
    with _locked():
        store = _load_facts()
        facts = store["facts"]
        old = None
        if replaces:
            replaces = _resolve(replaces)
            old = _find(facts, replaces)
            if old["status"] != "current":
                raise ValueError(f"{replaces} không còn là điều đang đúng, không thay được.")
        else:
            for f in facts:
                if f["status"] == "current" and f["section"] == section and same_meaning(f["text"], text):
                    f["confirmed_at"] = iso(t)
                    f["unconfirmed"] = False
                    f["tags"] = sorted(set(f.get("tags", [])) | set(tags))
                    f["core"] = f.get("core", False) or core
                    f["pinned"] = f.get("pinned", False) or pin
                    if source:
                        f["source"] = _clean_source(source)
                    write_json(_p("so_nho.json"), store)
                    return {"ok": True, "duplicate_of": f["id"], **_brief(f),
                            "note": "Sổ đã có điều này — chỉ ghi nhận là vừa được nhắc lại."}
        fact = {
            "id": _new_id(store, "m"), "section": section, "text": text,
            "subject": subject or (old or {}).get("subject"), "tags": tags or list((old or {}).get("tags", [])),
            "due": _parse_due(due), "status": "current",
            "core": bool(core or (old or {}).get("core")), "pinned": bool(pin or (old or {}).get("pinned")),
            "sensitive": bool(sensitive), "by": by, "origin": origin, "source": _clean_source(source),
            "created_at": iso(t), "confirmed_at": iso(t), "edited_at": None,
            "ended_at": None, "end_note": None, "replaces": replaces, "replaced_by": None, "merged_into": None,
            # chuyển từ trí nhớ cũ, hoặc Khôi vừa "ghi" từ đề xuất → không báo lại ở dòng 🧠
            "reported": origin in MIGRATED or origin == "de_xuat", "stale_asked_at": None, "unconfirmed": False,
        }
        if old:
            old.update(status="past", ended_at=iso(t), replaced_by=fact["id"])
        facts.append(fact)
        write_json(_p("so_nho.json"), store)
    out = {"ok": True, "id": fact["id"], **_brief(fact)}
    if old:
        out["replaced"] = old["id"]
    return out


def _brief(f: dict[str, Any]) -> dict[str, Any]:
    return {k: f.get(k) for k in ("section", "text", "subject", "due", "source", "core", "pinned", "sensitive", "status")}


def _clean_source(source: str | None) -> str | None:
    source = " ".join((source or "").split())
    if len(source) > 200:
        raise ValueError("Nguồn ghi ngắn thôi (tối đa 200 ký tự): trang nào, mail ngày nào, ai nói.")
    return source or None


def _source_label(f: dict[str, Any]) -> str:
    return f" (nguồn: {f['source']})" if f.get("source") else ""


def edit(fid: str, *, text: str | None = None, section: str | None = None, subject: str | None = None,
         due: str | None = None, source: str | None = None, t: datetime | None = None) -> dict[str, Any]:
    """Sửa vì ghi SAI (không giữ bản sai). Điều đổi theo thời gian thì dùng add --replaces."""
    t = t or now()
    with _locked():
        store = _load_facts()
        f = _find(store["facts"], _resolve(fid))
        if text is not None:
            f["text"] = _clean_text(text)
        if section is not None:
            if section not in SECTIONS:
                raise ValueError(f"--section phải là một trong {', '.join(SECTIONS)}.")
            f["section"] = section
        if subject is not None:
            f["subject"] = subject or None
        if due is not None:
            f["due"] = _parse_due(due) if due else None
        if source is not None:
            f["source"] = _clean_source(source)
        f.update(edited_at=iso(t), confirmed_at=iso(t), unconfirmed=False)
        write_json(_p("so_nho.json"), store)
    return {"ok": True, "id": f["id"], **_brief(f)}


def end(fid: str, note: str | None = None, t: datetime | None = None) -> dict[str, Any]:
    """Không còn đúng / đã xong (không có điều thay thế) → chuyển sang 'trước đây'."""
    t = t or now()
    with _locked():
        store = _load_facts()
        f = _find(store["facts"], _resolve(fid))
        if f["status"] != "current":
            raise ValueError(f"{f['id']} vốn đã không còn là điều đang đúng.")
        f.update(status="past", ended_at=iso(t), end_note=note)
        write_json(_p("so_nho.json"), store)
    return {"ok": True, "id": f["id"], **_brief(f)}


def confirm(tokens: Iterable[str], t: datetime | None = None) -> dict[str, Any]:
    """Khôi nói 'đúng' → điều đó được coi như vừa xác nhận lại."""
    t = t or now()
    done = []
    with _locked():
        store = _load_facts()
        for tok in tokens:
            f = _find(store["facts"], _resolve(tok))
            f.update(confirmed_at=iso(t), unconfirmed=False, stale_asked_at=None)
            done.append(f["id"])
        write_json(_p("so_nho.json"), store)
    return {"ok": True, "confirmed": done}


def set_flags(fid: str, *, pin: bool | None = None, core: bool | None = None) -> dict[str, Any]:
    with _locked():
        store = _load_facts()
        f = _find(store["facts"], _resolve(fid))
        if pin is not None:
            f["pinned"] = pin
        if core is not None:
            f["core"] = core
        write_json(_p("so_nho.json"), store)
    return {"ok": True, "id": f["id"], **_brief(f)}


def forget(tokens: Iterable[str], t: datetime | None = None) -> dict[str, Any]:
    """'Quên giúp': xóa hẳn khỏi sổ, kể cả lịch sử của điều đó. Chỉ ghi lại mã + giờ đã quên."""
    t = t or now()
    ids = [_resolve(x) for x in tokens]
    forgotten: list[dict[str, Any]] = []
    not_found: list[str] = []
    drive: list[str] = []
    with _locked():
        store, props, kho = _load_facts(), _load_props(), _load_kho()
        for fid in ids:
            if fid.startswith("m"):
                chain = _history_chain(store["facts"], fid)
                if not chain:
                    not_found.append(fid)
                    continue
                store["facts"] = [f for f in store["facts"] if f["id"] not in chain]
                for f in store["facts"]:
                    if f.get("replaced_by") in chain:
                        f["replaced_by"] = None
                    if f.get("replaces") in chain:
                        f["replaces"] = None
                forgotten += [{"id": c, "kind": "sổ nhớ", "text": chain[c]} for c in chain]
            elif fid.startswith("d"):
                hit = [x for x in props["items"] if x["id"] == fid]
                props["items"] = [x for x in props["items"] if x["id"] != fid]
                (forgotten.append({"id": fid, "kind": "đề xuất", "text": hit[0]["text"]}) if hit else not_found.append(fid))
            elif fid.startswith("k"):
                hit = [x for x in kho["items"] if x["id"] == fid]
                kho["items"] = [x for x in kho["items"] if x["id"] != fid]
                if hit:
                    forgotten.append({"id": fid, "kind": "kho", "text": hit[0]["title"]})
                    if hit[0].get("drive"):
                        drive.append(hit[0]["drive"])
                else:
                    not_found.append(fid)
            elif fid.startswith("nk"):
                text = _forget_journal_line(fid)
                (forgotten.append({"id": fid, "kind": "nhật ký", "text": text}) if text else not_found.append(fid))
            else:
                not_found.append(fid)
        write_json(_p("so_nho.json"), store)
        write_json(_p("de_xuat.json"), props)
        write_json(_p("kho.json"), kho)
        if forgotten:
            append_jsonl(_p("da_quen.jsonl"), {"at": iso(t), "ids": [x["id"] for x in forgotten]})
    texts = [x["text"] for x in forgotten]
    notify = ("LifeOS — Khôi nhờ quên. Xóa ĐÚNG các điều sau trong trí nhớ riêng của bạn và trong phần "
              "trí nhớ chung do CHÍNH bạn ghi (không xóa gì khác), rồi trả lời \"đã xóa\" hoặc \"không có\":\n"
              + "\n".join(f"• {x}" for x in texts)) if texts else None
    return {"ok": not not_found, "forgotten": forgotten, "not_found": not_found,
            "drive_to_trash": drive, "message_for_other_bots": notify}


def _history_chain(facts: list[dict[str, Any]], fid: str) -> dict[str, str]:
    """Điều fid + các bản cũ hơn nó (replaces) + các điều đã gộp vào nó."""
    by_id = {f["id"]: f for f in facts}
    if fid not in by_id:
        return {}
    chain: dict[str, str] = {}
    todo = [fid]
    while todo:
        cur = todo.pop()
        if cur in chain or cur not in by_id:
            continue
        chain[cur] = by_id[cur]["text"]
        if by_id[cur].get("replaces"):
            todo.append(by_id[cur]["replaces"])
        todo += [f["id"] for f in facts if f.get("merged_into") == cur]
    return chain


# ---------------------------------------------------------------- đọc: hồ sơ, tìm, trang

def _visible_core(facts: list[dict[str, Any]], section: str, today: date) -> list[dict[str, Any]]:
    out = []
    for f in facts:
        if f["status"] != "current" or f["section"] != section:
            continue
        if not (f.get("core") or f.get("pinned")):
            continue
        if f.get("sensitive") and not f.get("pinned"):
            continue  # chuyện nhạy cảm chỉ lên hồ sơ khi Khôi tự ghim
        if f.get("due") and date.fromisoformat(f["due"]) < today:
            continue
        out.append(f)
    out.sort(key=lambda f: (not f.get("pinned"), _neg_time(f.get("confirmed_at"))))
    return out


def _neg_time(value: str | None) -> float:
    dt = parse_dt(value)
    return -dt.timestamp() if dt else 0.0


def core(cfg: dict[str, Any] | None = None, t: datetime | None = None, hint: bool = True) -> dict[str, Any]:
    """Hồ sơ ngắn (~40 dòng). Mỗi mục có giới hạn; quá giới hạn thì điều lâu không nhắc nằm lại trong sổ."""
    t = t or now()
    s = _settings(cfg)
    facts = _load_facts()["facts"]
    lines = [f"🧠 HỒ SƠ NGẮN CỦA KHÔI · sổ nhớ LifeOS · {vn_datetime(t)}"]
    shown = hidden = 0
    for key, limit in s["limits"].items():
        rows = _visible_core(facts, key, t.date())
        if not rows:
            continue
        icon, title = SECTIONS[key]
        lines.append(f"{icon} {title}")
        for f in rows[:limit]:
            lines.append(f"- {'📌 ' if f.get('pinned') else ''}{f['text']}{_due_label(f)}")
        shown += min(len(rows), limit)
        hidden += max(0, len(rows) - limit)
    total = sum(1 for f in facts if f["status"] == "current")
    if shown == 0:
        lines.append("(Sổ nhớ còn trống.)")
    if hint:
        lines.append(f"Sổ có {total} điều đang đúng. Câu hỏi về chuyện cũ / người quen / sở thích → "
                     "python3 -m lifeos brain search \"<từ khóa>\" trước khi trả lời. Sổ khác trí nhớ riêng → theo sổ.")
    return {"text": "\n".join(lines), "shown": shown, "hidden_over_limit": hidden, "current_total": total}


def _fts_available() -> bool:
    try:
        con = sqlite3.connect(":memory:")
        con.execute("create virtual table t using fts5(x)")
        con.close()
        return True
    except sqlite3.OperationalError:
        return False


def _documents() -> list[dict[str, Any]]:
    docs = []
    for f in _load_facts()["facts"]:
        if f["status"] == "merged":
            continue
        label = "đang đúng" if f["status"] == "current" else f"trước đây (tới {_month_label(f.get('ended_at'))})"
        docs.append({"type": "sổ nhớ", "id": f["id"], "text": f["text"] + _due_label(f),
                     "section": SECTIONS[f["section"]][1], "status": label, "source": f.get("source"),
                     "index": " ".join([f["text"], f.get("subject") or "", " ".join(f.get("tags", [])),
                                        f.get("end_note") or ""]),
                     "penalty": 0.0 if f["status"] == "current" else 0.5})
    for k in _load_kho()["items"]:
        docs.append({"type": "kho", "id": k["id"], "text": f"{k['title']} — {k.get('summary') or ''}".strip(" —"),
                     "url": k.get("url"), "drive": k.get("drive"), "saved": vn_date(parse_dt(k["created_at"])),
                     "index": " ".join([k["title"], k.get("summary") or "", " ".join(k.get("tags", [])), k.get("url") or ""]),
                     "penalty": 0.2})
    folder = _p("nhat_ky")
    for fp in sorted(folder.glob("*.json")) if folder.exists() else []:
        day = read_json(fp, {}) or {}
        for ln in day.get("lines", []):
            if ln.get("private"):
                continue
            docs.append({"type": "nhật ký", "id": ln["id"], "text": f"{BOT_NAMES.get(ln['by'], ln['by'])}: {ln['text']}",
                         "date": vn_date(date.fromisoformat(day["date"])), "index": ln["text"], "penalty": 0.3})
    return docs


def search(query: str, limit: int = 8) -> dict[str, Any]:
    """Mục lục tìm nhanh: trả về vài dòng liên quan nhất (không đọc cả sổ)."""
    tokens = fold(query).split()
    if not tokens:
        raise ValueError("Thiếu từ khóa.")
    docs = _documents()
    scored: list[tuple[float, dict[str, Any]]] = []
    if docs and _fts_available():
        con = sqlite3.connect(":memory:")
        con.execute("create virtual table t using fts5(body, tokenize='unicode61')")
        con.executemany("insert into t(rowid, body) values (?, ?)", [(i, fold(d["index"])) for i, d in enumerate(docs)])
        match = " OR ".join(f'"{tok}"*' if len(tok) >= 3 else f'"{tok}"' for tok in tokens)
        for rowid, rank in con.execute("select rowid, bm25(t) from t where t match ? order by bm25(t) limit ?",
                                       (match, limit * 4)):
            scored.append((rank + docs[rowid]["penalty"], docs[rowid]))
        con.close()
    else:  # máy không có FTS5: đếm từ khớp
        for d in docs:
            words = fold(d["index"]).split()
            hits = sum(1 for tok in tokens if any(w.startswith(tok) if len(tok) >= 3 else w == tok for w in words))
            if hits:
                scored.append((-hits + d["penalty"], d))
    scored.sort(key=lambda x: x[0])
    results = [{k: v for k, v in d.items() if k not in {"index", "penalty"}} for _, d in scored[:limit]]
    return {"query": query, "results": results,
            "note": None if results else "Sổ không có gì khớp. Thử từ khóa khác, hoặc tìm trong trí nhớ riêng của bạn "
                                         "(có thì trả lời rồi ghi vào sổ)."}


def show(name: str) -> dict[str, Any]:
    """'Trang' chi tiết kiểu Obsidian của một người / môn / dự án / chủ đề."""
    key = fold(name)
    if not key:
        raise ValueError("Thiếu tên.")

    def match(*fields: str) -> bool:
        return any(key in fold(x) for x in fields if x)

    facts = _load_facts()["facts"]
    cur = [f for f in facts if f["status"] == "current" and match(f.get("subject") or "", *f.get("tags", []), f["text"])]
    past = [f for f in facts if f["status"] == "past" and match(f.get("subject") or "", *f.get("tags", []), f["text"])]
    kho = [k for k in _load_kho()["items"] if match(k["title"], k.get("summary") or "", *k.get("tags", []))]
    journal = [d for d in _documents() if d["type"] == "nhật ký" and match(d["text"])][-10:]
    lines = [f"# {name}"]
    if cur:
        lines += ["## Đang đúng"] + [f"- {f['id']} · {f['text']}{_due_label(f)}{_source_label(f)}" for f in cur]
    if past:
        lines += ["## Trước đây"] + [f"- {f['id']} · {f['text']} (tới {_month_label(f.get('ended_at'))}"
                                     f"{' — ' + f['end_note'] if f.get('end_note') else ''}){_source_label(f)}"
                                     for f in past]
    if kho:
        lines += ["## Kho"] + [f"- {k['id']} · {k['title']} {k.get('url') or k.get('drive') or ''}".rstrip() for k in kho]
    if journal:
        lines += ["## Nhật ký gần đây"] + [f"- {j['date']} · {j['text']}" for j in journal]
    if len(lines) == 1:
        lines.append("(Chưa có gì về chủ đề này trong sổ.)")
    return {"text": "\n".join(lines), "current": len(cur), "past": len(past), "kho": len(kho), "journal": len(journal)}


def tidy(t: datetime | None = None) -> dict[str, Any]:
    """Mục 'Đang dở' tự dọn: lời hứa/dự định đã qua hạn → 'trước đây'."""
    t = t or now()
    moved = []
    with _locked():
        store = _load_facts()
        for f in store["facts"]:
            if f["status"] == "current" and f["section"] == "dang_do" and f.get("due") \
                    and date.fromisoformat(f["due"]) < t.date():
                f.update(status="past", ended_at=iso(t), end_note="qua hạn — tự chuyển sang trước đây")
                moved.append(f["id"])
        if moved:
            write_json(_p("so_nho.json"), store)
    return {"moved_to_past": moved}


def stats() -> dict[str, Any]:
    facts = _load_facts()["facts"]
    by_section: dict[str, dict[str, int]] = {}
    for f in facts:
        row = by_section.setdefault(f["section"], {"current": 0, "past": 0})
        if f["status"] in row:
            row[f["status"]] += 1
    origins: dict[str, int] = {}
    for f in facts:
        if f["status"] == "current":
            origins[f["origin"]] = origins.get(f["origin"], 0) + 1
    return {"current": sum(r["current"] for r in by_section.values()),
            "past": sum(r["past"] for r in by_section.values()),
            "by_section": by_section, "current_by_origin": origins,
            "pending_proposals": sum(1 for p in _load_props()["items"] if p["status"] == "pending"),
            "kho": len(_load_kho()["items"])}


# ---------------------------------------------------------------- đề xuất của bot quét nguồn

def propose(by: str, text: str, source: str, section: str = "khac", subject: str | None = None,
            t: datetime | None = None) -> dict[str, Any]:
    if by not in SCAN_BOTS:
        raise ValueError("Chỉ 4 bot Học tập, Công ty, Cá nhân, Zalo đề xuất. LifeOS/Tiko ghi thẳng bằng `brain add`.")
    if section not in SECTIONS:
        raise ValueError(f"--section phải là một trong {', '.join(SECTIONS)}.")
    text, t = _clean_text(text), t or now()
    for f in _load_facts()["facts"]:
        if f["status"] == "current" and same_meaning(f["text"], text):
            return {"ok": True, "already_known": f["id"], "note": "Sổ đã có điều này, không cần đề xuất."}
    with _locked():
        props = _load_props()
        for p in props["items"]:
            if same_meaning(p["text"], text):
                if p["status"] == "pending":
                    return {"ok": True, "duplicate_of": p["id"], "note": "Đã có đề xuất này, đang chờ Khôi."}
                if p["status"] in {"rejected", "expired"}:
                    return {"ok": False, "id": p["id"],
                            "why": "Khôi đã bỏ (hoặc không trả lời) đề xuất này rồi — đừng đề xuất lại."}
        item = {"id": _new_id(props, "d"), "by": by, "text": text, "source": source, "section": section,
                "subject": subject, "status": "pending", "asks": 0, "asked_at": None,
                "created_at": iso(t), "fact_id": None}
        props["items"].append(item)
        write_json(_p("de_xuat.json"), props)
    return {"ok": True, "id": item["id"]}


def _decide(tokens: Iterable[str], accept_it: bool, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    tokens = list(tokens)
    if len(tokens) == 1 and fold(tokens[0]) in {"all", "het", "tat ca"}:
        pending = {x["id"] for x in _load_props()["items"] if x["status"] == "pending"}
        tokens = [v for v in _state().get("letters", {}).values() if v in pending]
    ids = [_resolve(x) for x in tokens]
    props = _load_props()
    todo = []
    for pid in ids:
        p = next((x for x in props["items"] if x["id"] == pid), None)
        if p is None:
            raise ValueError(f"Không có đề xuất mã {pid}.")
        if p["status"] != "pending":
            raise ValueError(f"Đề xuất {pid} đã xử lý rồi ({p['status']}).")
        todo.append(p)
    results = []
    for p in todo:
        if accept_it:
            res = add(p["section"], p["text"], subject=p.get("subject"), by=p["by"], origin="de_xuat",
                      source=p.get("source"), t=t)
            p.update(status="accepted", fact_id=res.get("id") or res.get("duplicate_of"))
        else:
            p["status"] = "rejected"
        results.append({"id": p["id"], "status": p["status"], "fact_id": p.get("fact_id")})
    with _locked():
        fresh = _load_props()
        for p in fresh["items"]:
            for r in results:
                if p["id"] == r["id"]:
                    p.update(status=r["status"], fact_id=r["fact_id"])
        write_json(_p("de_xuat.json"), fresh)
    return {"ok": True, "results": results}


def accept(tokens: Iterable[str], t: datetime | None = None) -> dict[str, Any]:
    return _decide(tokens, True, t)


def reject(tokens: Iterable[str], t: datetime | None = None) -> dict[str, Any]:
    return _decide(tokens, False, t)


# ---------------------------------------------------------------- dòng 🧠 trong báo cáo tối

def report(cfg: dict[str, Any] | None = None, t: datetime | None = None, mark: bool = False) -> dict[str, Any]:
    """Khối 🧠 cho báo cáo 21:00: điều mới nhớ (dồn từ lần báo trước), ≤ 3 đề xuất, cuối tháng ≤ 5 câu 'còn đúng không?'.

    Chạy không --mark để lấy nội dung; gửi Khôi xong mới chạy lại với --mark.
    """
    from .history import is_last_day_of_month

    t, s = t or now(), _settings(cfg)
    lock = _locked() if mark else _nolock()
    with lock:
        store, props = _load_facts(), _load_props()
        facts = store["facts"]
        new = sorted((f for f in facts if f["status"] == "current" and not f.get("reported")),
                     key=lambda f: f["created_at"])
        if mark:
            for p in props["items"]:
                if p["status"] == "pending" and p["asks"] >= s["proposal_max_asks"]:
                    p["status"] = "expired"
        pending = [p for p in props["items"] if p["status"] == "pending" and p["asks"] < s["proposal_max_asks"]]
        pending.sort(key=lambda p: (-p["asks"], p["created_at"]))
        chosen_props = pending[: s["proposals_per_night"]]

        stale: list[dict[str, Any]] = []
        monthly = is_last_day_of_month(t.date())
        if monthly:
            cutoff = t - timedelta(days=s["stale_days"])
            if mark:
                for f in facts:
                    if f["status"] == "current" and f.get("stale_asked_at") and \
                            parse_dt(f["confirmed_at"]) < parse_dt(f["stale_asked_at"]):
                        f["unconfirmed"] = True
            stale = sorted((f for f in facts if f["status"] == "current" and not f.get("unconfirmed")
                            and not f.get("stale_asked_at") and parse_dt(f["confirmed_at"]) < cutoff),
                           key=lambda f: f["confirmed_at"])[: s["stale_per_month"]]

        letters: dict[str, str] = {}
        abc = iter(string.ascii_lowercase)
        lines: list[str] = []
        if new:
            shown = new[: s["report_max_new"]]
            secret = sum(1 for f in shown if f.get("sensitive"))
            texts = [f["text"] for f in shown if not f.get("sensitive")]
            if secret:
                texts.append(f"🔒 {secret} chuyện riêng")
            more = len(new) - len(shown)
            lines.append("🧠 Nhớ thêm: " + " · ".join(texts) + (f" · và {more} điều khác (xem Page Trí nhớ)" if more else ""))
        chosen_letters: list[str] = []
        if chosen_props:
            lines.append("❓ Ghi vào sổ không?")
            for p in chosen_props:
                ch = next(abc)
                letters[ch] = p["id"]
                chosen_letters.append(ch)
                again = " · hỏi lại lần cuối" if p["asks"] >= 1 else ""
                lines.append(f"   {ch}. {p['text']} ({BOT_NAMES[p['by']]} · {p['source']}{again})")
            first, last = chosen_letters[0], chosen_letters[-1]
            lines.append(f'   → "ghi {first}" · "bỏ {last}"' + (' · "ghi hết"' if len(chosen_letters) > 1 else ""))
        if stale:
            lines.append("🔎 Còn đúng không? (lâu rồi không ai nhắc)")
            for f in stale:
                ch = next(abc)
                letters[ch] = f["id"]
                shown_text = "🔒 chuyện riêng (hỏi trong chat)" if f.get("sensitive") else f["text"]
                lines.append(f"   {ch}. {shown_text} (ghi từ {_month_label(f['created_at'])})")
            sl = [k for k, v in letters.items() if v.startswith("m")]
            lines.append(f'   → "đúng {sl[0]}" · "sai {sl[-1]}" rồi nói điều đúng · "quên {sl[-1]}"')

        if mark:
            for f in new:
                f["reported"] = True
            for f in stale:
                f["stale_asked_at"] = iso(t)
            for p in chosen_props:
                p["asks"] += 1
                p["asked_at"] = iso(t)
            write_json(_p("so_nho.json"), store)
            write_json(_p("de_xuat.json"), props)
            st = _state()
            st.update(letters=letters, letters_at=iso(t), last_report_at=iso(t))
            write_json(_p("trang_thai.json"), st)
    return {"text": "\n".join(lines), "new": [f["id"] for f in new], "letters": letters,
            "monthly_check": monthly, "marked": mark}


@contextmanager
def _nolock() -> Iterator[None]:
    yield


# ---------------------------------------------------------------- nhật ký chuyện đã nói

def _journal_path(d: date) -> Path:
    return _p("nhat_ky", f"{d.isoformat()}.json")


def journal_add(by: str, text: str | None = None, private: bool = False, t: datetime | None = None) -> dict[str, Any]:
    t, by = t or now(), _check_bot(by)
    text = PRIVATE_LINE if private else _clean_text(text)
    with _locked():
        p = _journal_path(t.date())
        day = read_json(p, None) or {"date": t.date().isoformat(), "lines": []}
        n = max([int(x["id"].rsplit("-", 1)[1]) for x in day["lines"]] + [0]) + 1
        line = {"id": f"nk{t:%Y%m%d}-{n}", "at": iso(t), "by": by, "text": text, "private": private}
        day["lines"].append(line)
        write_json(p, day)
    warn = "Hôm nay đã quá 5 dòng — cuối ngày gộp lại còn 3–5 dòng (`brain journal replace`)." if len(day["lines"]) > 5 else None
    return {"ok": True, "id": line["id"], "lines_today": len(day["lines"]), "warning": warn}


def journal_replace(d: date, texts: list[str], by: str = "lifeos", t: datetime | None = None) -> dict[str, Any]:
    """Gộp nhật ký một ngày còn 3–5 dòng. Dòng 'chuyện riêng' (nếu có) được giữ lại đúng một dòng."""
    t, by = t or now(), _check_bot(by)
    texts = [_clean_text(x) for x in texts]
    with _locked():
        p = _journal_path(d)
        day = read_json(p, None) or {"date": d.isoformat(), "lines": []}
        had_private = any(x.get("private") for x in day["lines"])
        lines = [{"id": f"nk{d:%Y%m%d}-{i + 1}", "at": iso(t), "by": by, "text": x, "private": False}
                 for i, x in enumerate(texts)]
        if had_private:
            lines.append({"id": f"nk{d:%Y%m%d}-{len(lines) + 1}", "at": iso(t), "by": by,
                          "text": PRIVATE_LINE, "private": True})
        day["lines"] = lines
        write_json(p, day)
    return {"ok": True, "date": d.isoformat(), "lines": len(lines)}


def journal_show(d: date | None = None, days: int | None = None, month: str | None = None,
                 t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    if month:
        first = date.fromisoformat(f"{month}-01")
        last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    elif days:
        last, first = t.date(), t.date() - timedelta(days=days - 1)
    else:
        first = last = d or t.date()
    out = []
    cur = first
    while cur <= last:
        day = read_json(_journal_path(cur), None)
        if day and day.get("lines"):
            out.append({"date": cur.isoformat(), "label": vn_date(cur),
                        "lines": [{"id": x["id"], "by": BOT_NAMES.get(x["by"], x["by"]), "text": x["text"]}
                                  for x in day["lines"]]})
        cur += timedelta(days=1)
    return {"days": out}


def _forget_journal_line(lid: str) -> str | None:
    m = re.fullmatch(r"nk(\d{8})-\d+", lid)
    if not m:
        return None
    d = datetime.strptime(m.group(1), "%Y%m%d").date()
    p = _journal_path(d)
    day = read_json(p, None)
    if not day:
        return None
    hit = [x for x in day["lines"] if x["id"] == lid]
    if not hit:
        return None
    day["lines"] = [x for x in day["lines"] if x["id"] != lid]
    write_json(p, day)
    return hit[0]["text"]


# ---------------------------------------------------------------- kho "lưu cái này"

def kho_add(title: str, summary: str | None = None, tags: Iterable[str] = (), url: str | None = None,
            drive: str | None = None, kind: str = "link", by: str = "lifeos", t: datetime | None = None) -> dict[str, Any]:
    if kind not in KHO_KINDS:
        raise ValueError(f"--kind phải là một trong {', '.join(KHO_KINDS)}.")
    t, by = t or now(), _check_bot(by)
    title = _clean_text(title)
    summary = _clean_text(summary) if summary else None
    with _locked():
        kho = _load_kho()
        item = {"id": _new_id(kho, "k"), "kind": kind, "title": title, "summary": summary,
                "tags": [x.strip() for x in tags if x and x.strip()], "url": url, "drive": drive,
                "by": by, "created_at": iso(t)}
        kho["items"].append(item)
        write_json(_p("kho.json"), kho)
    return {"ok": True, "id": item["id"], "item": item}


def kho_list(tag: str | None = None, limit: int = 10) -> dict[str, Any]:
    items = _load_kho()["items"]
    if tag:
        key = fold(tag)
        items = [k for k in items if any(key in fold(x) for x in k.get("tags", []))]
    items = sorted(items, key=lambda k: k["created_at"], reverse=True)[:limit]
    return {"items": [{"id": k["id"], "saved": vn_date(parse_dt(k["created_at"])), "kind": k["kind"],
                       "title": k["title"], "summary": k.get("summary"), "tags": k.get("tags", []),
                       "url": k.get("url"), "drive": k.get("drive")} for k in items]}


# ---------------------------------------------------------------- gộp điều trùng (Chủ nhật)

def dupes(limit: int = 20) -> dict[str, Any]:
    """Cặp điều có vẻ trùng (cùng mục). LifeOS xem rồi `brain merge GIỮ BỎ` — không hỏi Khôi."""
    cur = [f for f in _load_facts()["facts"] if f["status"] == "current"]
    pairs = []
    for i, a in enumerate(cur):
        for b in cur[i + 1:]:
            if a["section"] != b["section"]:
                continue
            ratio = _similar(a["text"], b["text"])
            same_subject = a.get("subject") and fold(a["subject"]) == fold(b.get("subject") or "")
            if ratio >= 0.75 or (same_subject and ratio >= 0.55):
                keep, drop = (a, b) if (a.get("pinned"), a["created_at"]) >= (b.get("pinned"), b["created_at"]) else (b, a)
                pairs.append({"keep": keep["id"], "drop": drop["id"], "keep_text": keep["text"],
                              "drop_text": drop["text"], "similar": round(ratio, 2)})
    pairs.sort(key=lambda x: -x["similar"])
    return {"pairs": pairs[:limit]}


def merge(keep: str, drop: str, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    with _locked():
        store = _load_facts()
        k, d = _find(store["facts"], keep), _find(store["facts"], drop)
        if k["status"] != "current" or d["status"] != "current":
            raise ValueError("Chỉ gộp được hai điều đang đúng.")
        if k["id"] == d["id"]:
            raise ValueError("Hai mã giống nhau.")
        k["tags"] = sorted(set(k.get("tags", [])) | set(d.get("tags", [])))
        k["core"] = k.get("core") or d.get("core")
        k["pinned"] = k.get("pinned") or d.get("pinned")
        k["confirmed_at"] = max(k["confirmed_at"], d["confirmed_at"], key=lambda v: parse_dt(v))
        d.update(status="merged", merged_into=k["id"], ended_at=iso(t))
        write_json(_p("so_nho.json"), store)
    return {"ok": True, "keep": k["id"], "merged": d["id"]}


def unmerge(fid: str) -> dict[str, Any]:
    """Gộp nhầm → tách lại."""
    with _locked():
        store = _load_facts()
        f = _find(store["facts"], fid)
        if f["status"] != "merged":
            raise ValueError(f"{fid} không phải điều đã gộp.")
        f.update(status="current", merged_into=None, ended_at=None)
        write_json(_p("so_nho.json"), store)
    return {"ok": True, "id": f["id"], **_brief(f)}


# ---------------------------------------------------------------- Grok Page "LifeOS · Trí nhớ"

def page(cfg: dict[str, Any] | None = None, t: datetime | None = None) -> dict[str, Any]:
    t, s = t or now(), _settings(cfg)
    facts = _load_facts()["facts"]
    st = stats()
    lines = ["# LifeOS · Trí nhớ",
             f"_Cập nhật {vn_datetime(t)} · {st['current']} điều đang đúng · {st['past']} điều trước đây · "
             f"{st['kho']} món trong kho_", "",
             "Sai thì nhắn LifeOS: \"sửa m12: …\" · \"quên m12\" · \"ghim m12\" · \"bỏ m12 khỏi hồ sơ\"", ""]
    lines += ["## Hồ sơ ngắn", "", core(cfg, t, hint=False)["text"].split("\n", 1)[-1], ""]

    since = t - timedelta(days=s["page_recent_days"])
    recent = [f for f in facts if f["status"] == "current" and f["origin"] not in MIGRATED
              and parse_dt(f["created_at"]) >= since]
    lines += [f"## Nhớ thêm {s['page_recent_days']} ngày qua", ""]
    lines += [f"- {vn_date(parse_dt(f['created_at']))} · {_page_text(f)} · {BOT_NAMES.get(f['by'], f['by'])}"
              for f in sorted(recent, key=lambda f: f["created_at"], reverse=True)] or ["- (không có)"]
    lines.append("")

    letters = {v: k for k, v in _state().get("letters", {}).items()}
    pending = [p for p in _load_props()["items"] if p["status"] == "pending" and p["asks"] >= 1]
    if pending:
        lines += ["## Đang chờ Khôi duyệt", ""]
        lines += [f"- {letters.get(p['id'], p['id'])}. {p['text']} ({BOT_NAMES[p['by']]} · {p['source']})" for p in pending]
        lines.append("")

    kho = kho_list(limit=s["page_kho_items"])["items"]
    lines += [f"## Kho — {s['page_kho_items']} món lưu gần đây", ""]
    for k in kho:
        links = " · ".join(x for x in (f"[link]({k['url']})" if k.get("url") else "",
                                        f"[Drive]({k['drive']})" if k.get("drive") else "") if x)
        tags = " ".join(f"#{x}" for x in k["tags"])
        lines.append(f"- {k['saved']} · **{k['title']}** {tags} {links}".rstrip())
    if not kho:
        lines.append("- (trống)")
    lines.append("")

    lines += ["## Toàn bộ sổ (đang đúng)", ""]
    for key, (icon, title) in SECTIONS.items():
        rows = [f for f in facts if f["status"] == "current" and f["section"] == key]
        if not rows:
            continue
        lines.append(f"**{icon} {title}** ({len(rows)})")
        lines += [f"- {f['id']} · {_page_text(f)}{_due_label(f)}{' 📌' if f.get('pinned') else ''}"
                  f"{' ⚠️ chưa xác nhận lại' if f.get('unconfirmed') else ''}" for f in rows]
        lines.append("")
    out = path("dashboard", "tri_nho.md")
    text = "\n".join(lines) + "\n"
    write_text(out, text)
    return {"page_md": str(out), "chars": len(text)}


def _page_text(f: dict[str, Any]) -> str:
    return "🔒 chuyện riêng (hỏi LifeOS trong chat)" if f.get("sensitive") else f["text"]


# ---------------------------------------------------------------- sao lưu / khôi phục (Tiko, 02:15)

def _backup_files() -> list[Path]:
    base = path()
    files = [f for f in _p().rglob("*") if f.is_file() and f.name != ".lock"] if _p().exists() else []
    files += [base / "config.toml", base / "done.json"]
    monthly = path("context", "monthly")
    files += sorted(monthly.glob("*")) if monthly.exists() else []
    return [f for f in files if f.is_file()]


def backup(t: datetime | None = None) -> dict[str, Any]:
    """Gói sổ nhớ + config.toml + done.json + báo cáo tháng vào MỘT file JSON, đặt tên theo thứ (7 bản xoay vòng)."""
    t = t or now()
    base = path()
    files = {str(f.relative_to(base)): f.read_text(encoding="utf-8") for f in _backup_files()}
    name = f"lifeos_saoluu_{WEEKDAY_KEYS[t.weekday()]}.json"
    out = path("backup", name)
    write_json(out, {"lifeos_backup": 1, "created_at": iso(t), "label": vn_datetime(t), "files": files})
    return {"file": str(out), "drive_folder": BACKUP_FOLDER, "drive_name": name, "files": len(files),
            "bytes": out.stat().st_size,
            "next": f"Tải đè file này lên Drive, thư mục \"{BACKUP_FOLDER}\", cùng tên {name} (không tạo file mới)."}


_RESTORE_OK = re.compile(r"^(brain/[^/].*|config\.toml|done\.json|context/monthly/[^/]+)$")


def restore(file: str, apply: bool = False, t: datetime | None = None) -> dict[str, Any]:
    """Khôi phục từ một bản sao lưu. Mặc định chỉ xem trước; --apply mới ghi (sau khi tự sao lưu bản hiện tại)."""
    t = t or now()
    data = read_json(Path(file), None)
    if not data or data.get("lifeos_backup") != 1 or not isinstance(data.get("files"), dict):
        raise ValueError("File này không phải bản sao lưu LifeOS.")
    bad = [k for k in data["files"] if ".." in k or not _RESTORE_OK.match(k)]
    if bad:
        raise ValueError(f"Bản sao lưu có đường dẫn lạ, không khôi phục: {bad[:3]}")
    out: dict[str, Any] = {"from": data.get("label"), "files": sorted(data["files"]), "applied": False}
    if apply:
        base = path()
        safety = {str(f.relative_to(base)): f.read_text(encoding="utf-8") for f in _backup_files()}
        keep = path("backup", f"truoc_khoi_phuc_{t:%Y%m%d_%H%M}.json")
        write_json(keep, {"lifeos_backup": 1, "created_at": iso(t), "label": vn_datetime(t), "files": safety})
        for rel, text in data["files"].items():
            write_text(base / rel, text)
        out.update(applied=True, safety_copy=str(keep))
    return out
