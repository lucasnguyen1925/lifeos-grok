"""Dashboard hiệu suất: HTML + SVG tự vẽ (không cần thư viện), ảnh PNG, và nội dung cho Grok Page.

    python3 -m lifeos dashboard            # tạo dashboard/index.html + dashboard/page.md
    python3 -m lifeos dashboard --png      # thêm dashboard/dashboard.png (cần Chromium)
"""
from __future__ import annotations

import html
import shutil
import subprocess
from datetime import timedelta
from typing import Any

from .common import now, path, vn_datetime, write_text
from .history import LABELS, LOWER_IS_BETTER, _load_days, summarize

# Bảng màu: dễ đọc trên nền sáng, phân biệt được với người mù màu đỏ–lục.
INK, MUTED, GRID, BG, CARD = "#1f2328", "#656d76", "#e6e8eb", "#f6f7f9", "#ffffff"
C_HOC, C_LAM, C_CANHAN = "#2f6fdf", "#e0892b", "#7a5af8"
C_GOOD, C_BAD, C_NEUTRAL = "#1a7f5a", "#c2412d", "#2f6fdf"

TILES = [
    ("A_on_time_pct", "% xong đúng hạn", "%"),
    ("B_late_quiz_or_registration", "Quiz/đăng ký trễ", ""),
    ("G_plan_pct", "% kế hoạch nếu–thì", "%"),
    ("G_focus_minutes", "Phút tập trung", ""),
    ("G_vip_waiting_days", "Ngày tin quan trọng chờ >24h", ""),
    ("F_french_minutes", "Phút tiếng Pháp", ""),
]


def _bars(values: list[float | None], labels: list[str], color: str, height: int = 150, unit: str = "") -> str:
    w, pad_l, pad_b, pad_t = 640, 34, 26, 14
    n = max(len(values), 1)
    vmax = max([v for v in values if v is not None] + [1])
    slot = (w - pad_l) / n
    bar_w = slot * 0.62
    out = [f'<svg viewBox="0 0 {w} {height}" width="100%" role="img">']
    for frac in (0, 0.5, 1):
        y = pad_t + (height - pad_t - pad_b) * (1 - frac)
        out.append(f'<line x1="{pad_l}" x2="{w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{pad_l - 6}" y="{y + 4:.1f}" font-size="14" fill="{MUTED}" text-anchor="end">{vmax * frac:.0f}</text>')
    for i, (v, lab) in enumerate(zip(values, labels)):
        x = pad_l + slot * i + (slot - bar_w) / 2
        if v:
            h = (height - pad_t - pad_b) * v / vmax
            y = height - pad_b - h
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="3" fill="{color}"/>')
        out.append(f'<text x="{x + bar_w / 2:.1f}" y="{height - 8}" font-size="14" fill="{MUTED}" text-anchor="middle">{html.escape(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


def _stacked(rows: list[tuple[str, float, float, float]], height: int = 170) -> str:
    w, pad_l, pad_b, pad_t = 640, 34, 26, 14
    n = max(len(rows), 1)
    vmax = max([a + b + c for _, a, b, c in rows] + [1])
    slot = (w - pad_l) / n
    bar_w = slot * 0.62
    scale = (height - pad_t - pad_b) / vmax
    out = [f'<svg viewBox="0 0 {w} {height}" width="100%" role="img">']
    for frac in (0, 0.5, 1):
        y = pad_t + (height - pad_t - pad_b) * (1 - frac)
        out.append(f'<line x1="{pad_l}" x2="{w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{pad_l - 6}" y="{y + 4:.1f}" font-size="14" fill="{MUTED}" text-anchor="end">{vmax * frac:.0f}h</text>')
    for i, (lab, hoc, lam, canhan) in enumerate(rows):
        x = pad_l + slot * i + (slot - bar_w) / 2
        y = height - pad_b
        for val, color in ((hoc, C_HOC), (lam, C_LAM), (canhan, C_CANHAN)):
            if val:
                h = val * scale
                y -= h
                out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}"/>')
        out.append(f'<text x="{x + bar_w / 2:.1f}" y="{height - 8}" font-size="14" fill="{MUTED}" text-anchor="middle">{html.escape(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


def _short_day(iso_date: str) -> str:
    from datetime import date
    d = date.fromisoformat(iso_date)
    return ("CN" if d.weekday() == 6 else f"T{d.weekday() + 2}") + f" {d:%d}"


def _tile(key: str, label: str, unit: str, cur: Any, prev: Any) -> str:
    value = "—" if cur is None else f"{cur}{unit}"
    delta = ""
    if isinstance(cur, (int, float)) and isinstance(prev, (int, float)) and cur != prev:
        better = (cur < prev) if key in LOWER_IS_BETTER else (cur > prev)
        color = C_GOOD if better else C_BAD
        delta = f'<div class="delta" style="color:{color}">{"▲" if cur > prev else "▼"} so với tuần trước ({prev}{unit})</div>'
    elif prev is not None:
        delta = '<div class="delta">như tuần trước</div>'
    return f'<div class="tile"><div class="tl">{html.escape(label)}</div><div class="tv">{value}</div>{delta}</div>'


def build(png: bool = False, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    t = now()
    today = t.date()
    days = _load_days(today - timedelta(days=13), today)
    week_start = today - timedelta(days=today.weekday())
    this_week = summarize(_load_days(week_start, today))
    last_week = summarize(_load_days(week_start - timedelta(days=7), week_start - timedelta(days=1)))
    labels = [_short_day(d["date"]) for d in days]

    tiles = "".join(_tile(k, lab, u, this_week.get(k), last_week.get(k) if last_week["days_recorded"] else None)
                    for k, lab, u in TILES)
    on_time = [round(100 * d["tasks"]["on_time"] / d["tasks"]["done_with_due"]) if d["tasks"]["done_with_due"] else None for d in days]
    sections = [
        ("Việc xong mỗi ngày", _bars([d["tasks"]["done"] for d in days], labels, C_NEUTRAL)),
        ("% xong đúng hạn mỗi ngày", _bars(on_time, labels, C_GOOD)),
        ("Giờ học · làm · cá nhân (theo lịch)",
         _stacked([(lab, d["hours"]["hoc"], d["hours"]["lam"], d["hours"]["canhan"]) for lab, d in zip(labels, days)])
         + f'<div class="legend"><span style="background:{C_HOC}"></span>Học <span style="background:{C_LAM}"></span>Làm '
           f'<span style="background:{C_CANHAN}"></span>Cá nhân</div>'),
        ("Phút tập trung mỗi ngày", _bars([d["focus"]["minutes"] for d in days], labels, C_HOC)),
    ]
    grade = this_week.get("B_grade_avg")
    body = "".join(f'<section class="card"><h2>{html.escape(title)}</h2>{svg}</section>' for title, svg in sections)
    doc = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>LifeOS · Hiệu suất</title>
<style>
body{{margin:0;background:{BG};color:{INK};font:15px/1.45 -apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif}}
main{{max-width:720px;margin:0 auto;padding:20px 16px 32px}}
h1{{font-size:22px;margin:0 0 2px}} .sub{{color:{MUTED};font-size:13px;margin-bottom:16px}}
.tiles{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}}
.tile,.card{{background:{CARD};border:1px solid {GRID};border-radius:12px}}
.tile{{padding:12px}} .tl{{color:{MUTED};font-size:12px}} .tv{{font-size:24px;font-weight:650;margin-top:2px}}
.delta{{font-size:11px;color:{MUTED};margin-top:2px}}
.card{{padding:14px 14px 8px;margin-bottom:12px}} h2{{font-size:15px;margin:0 0 8px}}
.legend{{font-size:12px;color:{MUTED};padding:2px 0 6px}} .legend span{{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 10px}}
@media (max-width:520px){{.tiles{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><main>
<h1>LifeOS · Hiệu suất</h1>
<div class="sub">Cập nhật {vn_datetime(t)} · Tuần này: {this_week['days_recorded']} ngày có dữ liệu{f' · Điểm TB {grade}' if grade else ''}</div>
<div class="tiles">{tiles}</div>
{body}
</main></body></html>"""
    out_dir = path("dashboard")
    write_text(out_dir / "index.html", doc)
    write_text(out_dir / "page.md", _page_markdown(t, this_week, last_week, days))

    result: dict[str, Any] = {"html": str(out_dir / "index.html"), "page_md": str(out_dir / "page.md")}
    if png:
        result["png"] = _screenshot(out_dir / "index.html", out_dir / "dashboard.png", cfg or {})
    return result


def _page_markdown(t, this_week, last_week, days) -> str:
    """Nội dung cho Grok Page (Page không nhận nguyên file HTML — bot dựng lại từ nội dung này)."""
    lines = ["# LifeOS · Hiệu suất", f"_Cập nhật {vn_datetime(t)}_", "", "## Tuần này so với tuần trước", "",
             "| Chỉ số | Tuần này | Tuần trước |", "|---|---|---|"]
    for key, label in LABELS.items():
        cur, prev = this_week.get(key), last_week.get(key) if last_week["days_recorded"] else None
        lines.append(f"| {label} | {'—' if cur is None else cur} | {'—' if prev is None else prev} |")
    lines += ["", "## 14 ngày gần nhất", "", "| Ngày | Xong | Đúng hạn | Học (h) | Làm (h) | Tập trung (phút) |", "|---|---|---|---|---|---|"]
    for d in days:
        lines.append(f"| {d['label']} | {d['tasks']['done']} | {d['tasks']['on_time']}/{d['tasks']['done_with_due']} | "
                     f"{d['hours']['hoc']} | {d['hours']['lam']} | {d['focus']['minutes']} |")
    return "\n".join(lines) + "\n"


def _screenshot(src, dst, cfg: dict[str, Any]) -> str | None:
    binary = cfg.get("dashboard", {}).get("chromium") or next(
        (b for b in ("chromium", "chromium-browser", "google-chrome", "chrome") if shutil.which(b)), None)
    if not binary:
        return None
    subprocess.run(
        [binary, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         "--force-device-scale-factor=2", "--window-size=720,1460", f"--screenshot={dst}", f"file://{src}"],
        check=True, capture_output=True, timeout=120,
    )
    return str(dst)
