"""LifeOS làm hộ: phiếu V1, V2… Khôi duyệt đúng phiếu thì bot làm luôn (SPEC §5g, H1-H14).

    python3 -m lifeos lamho add --loai gui_mail --tieu-de "…" --noi-dung "…" --nguon "…" \\
        --nguoi-nhan "Bạn A|địa chỉ|nguồn: sổ nhớ"                 # lập phiếu (chỉ loại đã bật trong config.toml [lamho] bat)
    python3 -m lifeos lamho list --de-xuat --mark                    # tối đa 5 phiếu cho báo cáo; --het = "xem thêm"
    python3 -m lifeos lamho approve V1                               # Khôi nói "làm V1" (xem đúng bản phiếu)
    python3 -m lifeos lamho start V1                                 # cổng kiểm tra: qua rồi mới được gửi/bấm
    python3 -m lifeos lamho result V1 --ket-qua ok --bang-chung "…"  # báo lại: ok | loi | khong-chac
    python3 -m lifeos lamho edit V1 --noi-dung "…"                   # sửa nội dung → mất duyệt, phải duyệt lại
    python3 -m lifeos lamho drop V1 | show V1 | tick | report | tong --days 7

Script giữ những thứ có luật cố định (công tắc từng loại, mức tiền, thùng rác thay vì xóa vĩnh viễn, hash nội dung đã duyệt,
hết hạn hỏi, không tự thử lại). AI chỉ quyết việc nào đáng lập phiếu và viết nội dung phiếu.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from typing import Any

from . import tracking
from .common import BOTS, append_jsonl, iso, now, parse_dt, path, read_json, read_jsonl, write_json

# loại việc → (nhóm, tên gọi). Nhóm 1: đã được phép từ trước · nhóm 2: rủi ro thấp · nhóm 3: khó sửa (SPEC §5g H2).
LOAI: dict[str, tuple[int, str]] = {
    "gui_mail": (1, "Gửi mail"),
    "gui_tin": (1, "Gửi tin Zalo"),
    "dat_nhac": (1, "Đặt nhắc"),
    "luu_nhap": (1, "Lưu nháp"),
    "tra_loi_moi_hop": (2, "Trả lời lời mời họp"),
    "tao_lich": (2, "Tạo sự kiện lịch"),
    "dien_form": (2, "Điền khảo sát/form"),
    "dang_ky_mien_phi": (2, "Đăng ký sự kiện miễn phí"),
    "don_mail": (2, "Dọn mail"),
    "sap_xep_drive": (2, "Sắp xếp file Drive"),
    "nop_bai": (3, "Nộp bài"),
    "lam_quiz": (3, "Làm quiz"),
    "dang_ky_mon": (3, "Đăng ký môn/thi"),
    "thanh_toan": (3, "Thanh toán"),
    "xoa": (3, "Xóa (thùng rác/lưu trữ)"),
}
GUI = {"gui_mail", "gui_tin"}                      # có người nhận → mỗi người phải có nguồn (N2)
CACH_XOA = {"thung_rac": "thùng rác", "luu_tru": "lưu trữ"}
ACTIVE = {"proposed", "approved", "running"}
FINISHED = {"done", "failed", "unknown"}
CLOSED = FINISHED | {"dropped", "expired"}
STATUS_VN = {"done": "làm xong", "failed": "làm không được", "unknown": "làm nhưng chưa rõ kết quả",
             "dropped": "bị bỏ", "expired": "hết hạn hỏi"}
DEFAULTS = {"bat": [], "toi_da_thanh_toan": 0, "toi_da_phieu_moi_lan": 5, "hoi_lai_toi_da": 2, "han_gap_gio": 3}
DEFAULT_PHUT = 7          # ước phút Khôi tiết kiệm khi phiếu không gắn việc cụ thể
KEEP_DAYS = 14            # phiếu đã đóng giữ trong state chừng này ngày (sổ lâu hơn nằm ở log/lamho.jsonl)


def _opts(cfg: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULTS)
    out.update((cfg or {}).get("lamho", {}) or {})
    return out


def _tien(n: int) -> str:
    return f"{n:,}".replace(",", ".") + "đ"


# ---------------------------------------------------------------- state + log

def _state_path():
    return path("state", "lamho.json")


def _state() -> dict[str, Any]:
    return read_json(_state_path(), None) or {"next": 1, "items": []}


def _save(data: dict[str, Any], t: datetime) -> None:
    cutoff = t - timedelta(days=KEEP_DAYS)
    data["items"] = [x for x in data["items"]
                     if x["status"] not in CLOSED or parse_dt(x.get("closed_at") or x["created_at"]) > cutoff]
    write_json(_state_path(), data)


def _log(event: str, it: dict[str, Any], t: datetime, **extra: Any) -> None:
    append_jsonl(path("log", "lamho.jsonl"), {
        "at": iso(t), "event": event, "id": it["id"], "loai": it["loai"], "nhom": it["nhom"],
        "lam_o": it["lam_o"], "status": it["status"], **extra})


def _find(data: dict[str, Any], vid: str) -> dict[str, Any]:
    vid = (vid or "").strip().upper()
    it = next((x for x in data["items"] if x["id"] == vid), None)
    if it is None:
        raise ValueError(f"Không có phiếu {vid or '(trống)'}.")
    return it


def _hash(it: dict[str, Any]) -> str:
    """Dấu vân tay của đúng thứ Khôi đã xem và duyệt: đổi chữ nào cũng phải duyệt lại (H9)."""
    keys = ("loai", "noi_dung", "so_tien", "noi_nhan", "cach", "nguoi_nhan", "lam_o")
    return hashlib.sha1(json.dumps({k: it.get(k) for k in keys}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def _check_fields(it: dict[str, Any]) -> None:
    """Luật cố định cho từng loại. Lỗi → ValueError với câu bot đọc là hiểu."""
    if it["loai"] not in LOAI:
        raise ValueError(f"Loại '{it['loai']}' không có. Dùng một trong: {', '.join(LOAI)}.")
    for key, label in (("tieu_de", "tiêu đề"), ("noi_dung", "nội dung (đúng thứ sẽ làm)"), ("nguon", "nguồn của dữ kiện (N1)")):
        if not (it.get(key) or "").strip():
            raise ValueError(f"Thiếu {label}.")
    if it["lam_o"] not in BOTS or it["lam_o"] == "tiko":
        raise ValueError("--lam-o phải là lifeos hoặc bot mảng (hoctap, congty, canhan, zalo).")
    if it["loai"] in GUI:
        people = it.get("nguoi_nhan") or []
        if not people:
            raise ValueError("Phiếu gửi cần người nhận: --nguoi-nhan \"tên|địa chỉ|nguồn\". Không có nguồn thì đừng đưa vào (nội quy mục 10).")
        for p in people:
            if not (p.get("ten") and p.get("dia_chi") and p.get("nguon")):
                raise ValueError(f"Người nhận '{p.get('ten') or '?'}' thiếu tên, địa chỉ hoặc NGUỒN. Không đoán: hỏi Khôi hoặc nhờ đúng bot tìm.")
    if it["loai"] == "gui_tin" and it["lam_o"] != "zalo":
        raise ValueError("Tin Zalo chỉ bot Zalo mở được: đặt --lam-o zalo (Khôi duyệt ở khung chat bot Zalo), hoặc soạn sẵn cho Khôi tự gửi.")
    if it["loai"] == "thanh_toan":
        if not isinstance(it.get("so_tien"), int) or it["so_tien"] <= 0 or not (it.get("noi_nhan") or "").strip():
            raise ValueError("Thanh toán cần --so-tien (đồng, số nguyên > 0) và --noi-nhan (trả cho ai, vào đâu).")
    if it["loai"] == "xoa" and it.get("cach") not in CACH_XOA:
        raise ValueError("Xóa chỉ được đưa vào thùng rác hoặc lưu trữ: --cach thung_rac | luu_tru. Không xóa vĩnh viễn.")


def phieu_text(it: dict[str, Any], opts: dict[str, Any] | None = None, asking: bool = False) -> str:
    """Phiếu cho Khôi đọc (chép nguyên văn vào báo cáo)."""
    nhom, ten = LOAI[it["loai"]]
    lines = [f"{it['id']}  {it['tieu_de']}   (~{it['phut_tiet_kiem']} phút của bạn)"]
    for p in it.get("nguoi_nhan") or []:
        lines.append(f"    Gửi tới: {p['ten']} {p['dia_chi']}, nguồn: {p['nguon']}")
    if it.get("so_tien"):
        lines.append(f"    Số tiền: {_tien(it['so_tien'])}, trả cho: {it['noi_nhan']}")
    if it.get("cach"):
        lines.append(f"    Cách xóa: {CACH_XOA[it['cach']]} (lấy lại được)")
    lines.append(f"    Nội dung: {it['noi_dung']}")
    lines.append(f"    Nguồn thông tin: {it['nguon']}")
    if it["lam_o"] != "lifeos":
        lines.append(f"    Làm ở bot: {it['lam_o']} (bạn nhắn \"làm {it['id']}\" ở khung chat bot đó)")
    if it.get("han"):
        d = parse_dt(it["han"])
        lines.append(f"    Hạn: {d:%H:%M %d/%m}")
    if asking and opts and it["asks"] + 1 >= int(opts["hoi_lai_toi_da"]) > 1:
        lines.append("    (Lần hỏi cuối: không trả lời thì mình bỏ phiếu này, việc về lại danh sách của bạn.)")
    lines.append(f"    → \"làm {it['id']}\" · \"bỏ {it['id']}\" · \"sửa {it['id']}: …\"")
    return "\n".join(lines)


# ---------------------------------------------------------------- lập, duyệt, sửa, bỏ

def _estimate_minutes(item_id: str | None, cfg: dict[str, Any] | None, phut: int | None) -> int:
    if phut:
        return int(phut)
    if item_id:
        from . import planner  # nhập muộn: planner cũng đọc phiếu để bỏ việc đã có phiếu
        found = next((x for x in (read_json(path("digest.json"), {}) or {}).get("items", []) if x["id"] == item_id), None) \
            or next((x for x in tracking.all_items() if x["id"] == item_id), None)
        if found:
            return int(planner._minutes(found, cfg))
    return DEFAULT_PHUT


def add(loai: str, tieu_de: str, noi_dung: str, nguon: str, *, item_id: str | None = None, han: str | None = None,
        so_tien: int | None = None, noi_nhan: str | None = None, cach: str | None = None, lam_o: str = "lifeos",
        nguoi_nhan: list[dict[str, str]] | None = None, phut: int | None = None, thay: str | None = None,
        cfg: dict[str, Any] | None = None, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    o = _opts(cfg)
    if loai not in LOAI:
        raise ValueError(f"Loại '{loai}' không có. Dùng một trong: {', '.join(LOAI)}.")
    if loai not in o["bat"]:
        raise ValueError(f"Loại '{loai}' chưa bật trong config.toml [lamho] bat nên không lập phiếu. "
                         "Chuẩn bị sẵn cho Khôi tự làm (ghi vào ▶ bước đầu của ô 📝); nhờ Tiko thử rồi bật.")
    data = _state()
    if item_id and any(x.get("item_id") == item_id and x["status"] in ACTIVE for x in data["items"]):
        raise ValueError("Việc này đã có phiếu đang chờ hoặc đang làm. Dùng lamho list để xem.")
    old = None
    if thay:
        old = _find(data, thay)
        if old["status"] not in {"failed", "unknown", "expired"}:
            raise ValueError(f"--thay chỉ dùng cho phiếu làm không được / chưa rõ kết quả / hết hạn, {old['id']} đang là {old['status']}.")
    it = {
        "id": f"V{data['next']}", "loai": loai, "nhom": LOAI[loai][0], "tieu_de": " ".join((tieu_de or "").split()),
        "noi_dung": (noi_dung or "").strip(), "nguon": (nguon or "").strip(), "nguoi_nhan": nguoi_nhan or [],
        "item_id": item_id, "han": han, "so_tien": so_tien, "noi_nhan": (noi_nhan or "").strip() or None, "cach": cach,
        "lam_o": lam_o, "phut_tiet_kiem": _estimate_minutes(item_id, cfg, phut), "status": "proposed", "asks": 0,
        "created_at": iso(t), "approved_at": None, "approved_hash": None, "started_at": None, "finished_at": None,
        "closed_at": None, "ket_qua": None, "bang_chung": None, "thay_cho": old["id"] if old else None,
    }
    _check_fields(it)
    if han:
        parse_dt(han)
    data["next"] += 1
    data["items"].append(it)
    _save(data, t)
    _log("add", it, t)
    return {"ok": True, "id": it["id"], "nhom": it["nhom"], "text": phieu_text(it, o)}


def approve(vid: str, t: datetime | None = None) -> dict[str, Any]:
    """Khôi vừa nói 'làm V…' trong khung chat bot thực hiện. Ghi dấu vân tay của đúng bản phiếu."""
    t = t or now()
    data = _state()
    it = _find(data, vid)
    if it["status"] != "proposed":
        raise ValueError(f"{it['id']} đang ở trạng thái {it['status']}, không duyệt được.")
    it.update(status="approved", approved_at=iso(t), approved_hash=_hash(it))
    _save(data, t)
    _log("approve", it, t)
    return {"ok": True, "id": it["id"], "text": f"{it['id']} đã được duyệt. Chạy `lamho start {it['id']}` trước khi làm."}


def edit(vid: str, *, tieu_de: str | None = None, noi_dung: str | None = None, so_tien: int | None = None,
         noi_nhan: str | None = None, cach: str | None = None, nguoi_nhan: list[dict[str, str]] | None = None,
         han: str | None = None, cfg: dict[str, Any] | None = None, t: datetime | None = None) -> dict[str, Any]:
    """Khôi nói 'sửa V1: …'. Sửa là mất duyệt: phải duyệt lại đúng bản mới (H9)."""
    t = t or now()
    data = _state()
    it = _find(data, vid)
    if it["status"] not in {"proposed", "approved"}:
        raise ValueError(f"{it['id']} đang ở trạng thái {it['status']}, không sửa được.")
    new = dict(it)
    for key, val in (("tieu_de", tieu_de), ("noi_dung", noi_dung), ("so_tien", so_tien), ("noi_nhan", noi_nhan),
                     ("cach", cach), ("nguoi_nhan", nguoi_nhan), ("han", han)):
        if val is not None:
            new[key] = val
    _check_fields(new)
    it.clear()
    it.update(new, status="proposed", approved_at=None, approved_hash=None)
    _save(data, t)
    _log("edit", it, t)
    return {"ok": True, "id": it["id"], "text": phieu_text(it, _opts(cfg))}


def drop(vid: str, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    data = _state()
    it = _find(data, vid)
    if it["status"] not in {"proposed", "approved"}:
        raise ValueError(f"{it['id']} đang ở trạng thái {it['status']}, không bỏ được.")
    it.update(status="dropped", closed_at=iso(t))
    _save(data, t)
    _log("drop", it, t)
    return {"ok": True, "id": it["id"], "text": f"Đã bỏ {it['id']}. Việc quay về danh sách của Khôi."}


# ---------------------------------------------------------------- làm: cổng kiểm tra và báo lại

def start(vid: str, cfg: dict[str, Any] | None = None, t: datetime | None = None) -> dict[str, Any]:
    """Cổng kiểm tra TRƯỚC khi bấm/gửi. Qua rồi mới được làm; không qua thì dừng và nói với Khôi (xem `why`)."""
    t = t or now()
    o = _opts(cfg)
    data = _state()
    it = _find(data, vid)
    st = it["status"]
    if st == "proposed":
        raise ValueError(f"{it['id']} chưa được Khôi duyệt. Chờ Khôi nói \"làm {it['id']}\" trong khung chat này, rồi chạy `lamho approve {it['id']}`.")
    if st == "running":
        raise ValueError(f"{it['id']} đang làm rồi. Không bấm lần hai: kiểm tra trạng thái ở nguồn rồi chạy `lamho result`.")
    if st in CLOSED:
        raise ValueError(f"{it['id']} đã {STATUS_VN[st]}. Muốn làm lại phải lập phiếu mới (`lamho add --thay {it['id']} …`) và Khôi duyệt lại.")
    if it["loai"] not in o["bat"]:
        raise ValueError(f"Loại '{it['loai']}' đang tắt trong config.toml [lamho] bat. Chuẩn bị sẵn cho Khôi tự làm; nhờ Tiko thử rồi bật.")
    if _hash(it) != it["approved_hash"]:
        it.update(status="proposed", approved_at=None, approved_hash=None)
        _save(data, t)
        raise ValueError(f"Nội dung {it['id']} đã đổi sau khi Khôi duyệt. Gửi lại phiếu và hỏi Khôi duyệt lại.")
    _check_fields(it)
    if it.get("han") and parse_dt(it["han"]) <= t:
        raise ValueError(f"{it['id']} đã quá hạn ({parse_dt(it['han']):%H:%M %d/%m}). Báo Khôi, không làm.")
    if it["loai"] == "thanh_toan":
        limit = int(o["toi_da_thanh_toan"])
        if limit <= 0:
            raise ValueError("Chưa cho phép thanh toán: Khôi chưa đặt [lamho] toi_da_thanh_toan trong config.toml. Chỉ chuẩn bị, Khôi tự bấm.")
        if it["so_tien"] > limit:
            raise ValueError(f"{_tien(it['so_tien'])} vượt mức tối đa {_tien(limit)} mỗi lần. Chỉ chuẩn bị, Khôi tự bấm.")
    it.update(status="running", started_at=iso(t))
    _save(data, t)
    _log("start", it, t)
    return {"ok": True, "id": it["id"], "loai": it["loai"], "lam_o": it["lam_o"], "noi_dung": it["noi_dung"],
            "text": f"Được làm {it['id']}. Làm ĐÚNG nội dung phiếu, không thêm bớt. Xong chạy "
                    f"`lamho result {it['id']} --ket-qua ok|loi|khong-chac --bang-chung \"…\"`."}


def result(vid: str, ket_qua: str, bang_chung: str | None = None, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    status = {"ok": "done", "loi": "failed", "khong-chac": "unknown"}.get(ket_qua)
    if status is None:
        raise ValueError("--ket-qua phải là ok, loi hoặc khong-chac.")
    data = _state()
    it = _find(data, vid)
    if it["status"] != "running":
        raise ValueError(f"{it['id']} đang ở trạng thái {it['status']}: phải qua `lamho start` rồi mới báo kết quả.")
    chung = " ".join((bang_chung or "").split())
    if ket_qua == "ok" and it["nhom"] == 3 and not chung:
        raise ValueError("Việc nhóm 3 báo 'ok' phải kèm --bang-chung (mã xác nhận, ảnh chụp màn hình xác nhận). "
                         "Không thấy xác nhận thì báo --ket-qua khong-chac, đừng khẳng định đã xong.")
    it.update(status=status, finished_at=iso(t), closed_at=iso(t), ket_qua=ket_qua, bang_chung=chung or None)
    if status == "done" and it.get("item_id"):
        tracking.mark_done(it["item_id"], by="lifeos", title=it["tieu_de"], t=t)
    _save(data, t)
    _log("result", it, t, ket_qua=ket_qua, phut_tiet_kiem=it["phut_tiet_kiem"] if status == "done" else 0)
    if status == "done":
        text = f"✅ {it['id']} xong: {it['tieu_de']}" + (f" ({chung})" if chung else "")
    elif status == "failed":
        text = (f"❌ {it['id']} chưa làm được. Báo Khôi ngay và chuyển thành việc của Khôi (plan add). "
                "Tiền, nộp bài, xóa: KHÔNG tự thử lại, kiểm tra trạng thái ở nguồn trước.")
    else:
        text = (f"❓ {it['id']}: mình chưa thấy xác nhận. Nói thẳng với Khôi như vậy, đừng khẳng định đã xong; "
                "kiểm tra trạng thái ở nguồn, muốn làm lại phải lập phiếu mới và Khôi duyệt.")
    return {"ok": True, "id": it["id"], "status": status, "text": text}


# ---------------------------------------------------------------- báo cáo, nhắc, thống kê

def _order(it: dict[str, Any]):
    """Phiếu có hạn gần xếp trước, không hạn xếp sau, cùng hạn thì phiếu cũ trước."""
    return (0, parse_dt(it["han"]).timestamp(), it["created_at"]) if it.get("han") else (1, 0, it["created_at"])


def list_items(de_xuat: bool = False, het: bool = False, mark: bool = False, cfg: dict[str, Any] | None = None,
               t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    o = _opts(cfg)
    data = _state()
    if not de_xuat:
        return {"items": [{k: x[k] for k in ("id", "loai", "tieu_de", "status", "han", "lam_o")} for x in data["items"]]}
    rows = sorted((x for x in data["items"] if x["status"] == "proposed"), key=_order)
    shown = rows if het else rows[:int(o["toi_da_phieu_moi_lan"])]
    rest = len(rows) - len(shown)
    texts = [{"id": x["id"], "text": phieu_text(x, o, asking=True)} for x in shown]
    if mark and shown:
        for x in shown:
            x["asks"] += 1
            x.setdefault("asked_at", []).append(iso(t))
            _log("ask", x, t, lan=x["asks"])
        _save(data, t)
    return {"ok": True, "phieu": texts, "text": "\n\n".join(p["text"] for p in texts), "con_lai": rest,
            "ghi_chu": f"…và {rest} việc khác, nói 'xem thêm'." if rest else ""}


def tick(cfg: dict[str, Any] | None = None, t: datetime | None = None) -> dict[str, Any]:
    """Gọi đầu báo cáo 05:30 / 21:00: phiếu đã hỏi đủ lần mà Khôi vẫn im → hết hạn (H8); phiếu có hạn gần → nhắc."""
    t = t or now()
    o = _opts(cfg)
    data = _state()
    expired = []
    for x in data["items"]:
        if x["status"] == "proposed" and x["asks"] >= int(o["hoi_lai_toi_da"]):
            x.update(status="expired", closed_at=iso(t))
            _log("expire", x, t)
            expired.append({"id": x["id"], "tieu_de": x["tieu_de"]})
    soon = t + timedelta(hours=float(o["han_gap_gio"]))
    nhac = [{"id": x["id"], "tieu_de": x["tieu_de"], "han": x["han"]} for x in data["items"]
            if x["status"] == "proposed" and x.get("han") and t < parse_dt(x["han"]) <= soon]
    if expired:
        _save(data, t)
    return {"ok": True, "expired": expired, "nhac_gap": nhac,
            "text": ("Phiếu có hạn gần mà Khôi chưa duyệt: KHÔNG tự làm; đặt Reminder + báo thức (R2) và nhắc Khôi."
                     if nhac else "")}


def show(vid: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    it = _find(_state(), vid)
    return {"ok": True, "phieu": it, "text": phieu_text(it, _opts(cfg))}


def report(t: datetime | None = None) -> dict[str, Any]:
    """Dòng '🤖 Đã làm giúp hôm nay' cho báo cáo 21:00. Rỗng nếu hôm nay không có gì."""
    t = t or now()
    rows = [x for x in _state()["items"] if x["status"] in FINISHED and x.get("finished_at")
            and parse_dt(x["finished_at"]).date() == t.date()]
    if not rows:
        return {"text": "", "so_viec": 0, "phut_tiet_kiem": 0}
    marks = {"done": "✅", "failed": "❌", "unknown": "❓"}
    tail = {"done": "", "failed": ": chưa làm được, đã chuyển thành việc của bạn", "unknown": ": chưa thấy xác nhận"}
    lines = ["🤖 Đã làm giúp hôm nay:"] + [f"  {marks[x['status']]} {x['id']} {x['tieu_de']}{tail[x['status']]}" for x in rows]
    done = [x for x in rows if x["status"] == "done"]
    return {"text": "\n".join(lines), "so_viec": len(done), "phut_tiet_kiem": sum(x["phut_tiet_kiem"] for x in done)}


def _results() -> list[dict[str, Any]]:
    return [r for r in read_jsonl(path("log", "lamho.jsonl")) if r.get("event") == "result" and r.get("ket_qua") == "ok"]


def day_stats(day: date) -> dict[str, int]:
    rows = [r for r in _results() if parse_dt(r["at"]).date() == day]
    return {"viec": len(rows), "phut": sum(r.get("phut_tiet_kiem") or 0 for r in rows)}


def tong(days: int = 7, t: datetime | None = None) -> dict[str, Any]:
    t = t or now()
    first = t.date() - timedelta(days=days - 1)
    rows = [r for r in _results() if parse_dt(r["at"]).date() >= first]
    by: dict[str, int] = {}
    for r in rows:
        by[r["loai"]] = by.get(r["loai"], 0) + 1
    return {"days": days, "viec": len(rows), "phut_tiet_kiem": sum(r.get("phut_tiet_kiem") or 0 for r in rows), "theo_loai": by}


def active_item_ids() -> set[str]:
    """Việc đang có phiếu chưa kết thúc: kế hoạch của Khôi không xếp giờ cho chúng (M5)."""
    return {x["item_id"] for x in _state()["items"] if x.get("item_id") and x["status"] in ACTIVE}
