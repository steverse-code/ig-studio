#!/usr/bin/env python3
"""
cardnews.py — Instagram 캐러셀(카드뉴스) 슬라이드 렌더러

JSON 포스트 명세를 받아 1080x1350 JPEG 슬라이드를 생성한다.
사용:  python3 scripts/cardnews.py content/2026-08-17-vo2max.json out/
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ─────────────────────────────────────────────────────────────
# 캔버스 / 그리드
# ─────────────────────────────────────────────────────────────
W, H = 1080, 1350
MARGIN = 96
CONTENT_W = W - MARGIN * 2
FOOTER_H = 110          # 하단 핸들/인디케이터 영역
TOP_BIAS = 0.40         # 세로 정렬: 0=위, 0.5=정중앙 (살짝 위가 안정적)

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")
PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "photos")
_FCACHE: dict = {}


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    key = (weight, size)
    if key not in _FCACHE:
        _FCACHE[key] = ImageFont.truetype(os.path.join(FONT_DIR, f"Pretendard-{weight}.otf"), size)
    return _FCACHE[key]


# ─────────────────────────────────────────────────────────────
# 팔레트 — 필러별 액센트만 바뀌고 지면 톤은 통일 (피드 그리드 일관성)
# ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Theme:
    bg: str
    ink: str
    muted: str
    accent: str
    accent_soft: str
    on_accent: str = "#FFFFFF"
    dot_off: str = "#C9C5BC"


THEMES = {
    "longevity": Theme("#F7F5F0", "#14201C", "#6B7A74", "#1F4A3D", "#E4EDE7"),
    "lifestyle": Theme("#F8F5F1", "#221A14", "#7C6E62", "#9C4A24", "#F2E4DA"),
    "fashion":   Theme("#F5F4F2", "#1A1A1F", "#75757F", "#2B2B33", "#E7E4DC"),
    "default":   Theme("#F7F5F0", "#16150F", "#6E6A5F", "#3A4A2F", "#E8EAE1"),
}

PILLAR_LABEL = {"longevity": "LONGEVITY", "lifestyle": "LIFESTYLE", "fashion": "FASHION"}


# ─────────────────────────────────────────────────────────────
# 배경 사진 — 듀오톤(테마 색) + 색 워시로 가독성 확보
# ─────────────────────────────────────────────────────────────
def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _darken(hex_color: str, amt: float = 0.55) -> str:
    return "#%02x%02x%02x" % _mix(_hex(hex_color), (0, 0, 0), amt)


def _cover_crop(img: Image.Image, w: int, h: int) -> Image.Image:
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, int(sw * scale + 0.5)), max(1, int(sh * scale + 0.5))
    img = img.resize((nw, nh), Image.LANCZOS)
    x, y = (nw - w) // 2, (nh - h) // 2
    return img.crop((x, y, x + w, y + h))


def _duotone(gray: Image.Image, dark_hex: str, light_hex: str) -> Image.Image:
    return ImageOps.colorize(gray, black=dark_hex, white=light_hex).convert("RGB")


def photo_bases(photo_name: str, th: "Theme"):
    """포스트 배경 사진 → (일반 슬라이드용, stat 슬라이드용) 듀오톤 베이스 이미지."""
    path = os.path.join(PHOTO_DIR, photo_name)
    gray = ImageOps.autocontrast(Image.open(path).convert("L"), cutoff=1)
    gray = _cover_crop(gray, W, H)

    bg_duo = _duotone(gray, th.ink, th.bg)
    bg_wash = Image.new("RGB", (W, H), th.bg)
    bg = Image.blend(bg_duo, bg_wash, 0.66)

    stat_duo = _duotone(gray, _darken(th.accent, 0.6), th.accent)
    stat_wash = Image.new("RGB", (W, H), th.accent)
    stat = Image.blend(stat_duo, stat_wash, 0.58)

    return bg, stat


# ─────────────────────────────────────────────────────────────
# 텍스트 유틸
# ─────────────────────────────────────────────────────────────
def _wrap(draw, text: str, f, max_w: int) -> list[str]:
    """폭 기준 줄바꿈. 명시적 개행은 보존."""
    lines: list[str] = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        cur = ""
        for word in para.split(" "):
            trial = word if not cur else cur + " " + word
            if draw.textlength(trial, font=f) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                while draw.textlength(word, font=f) > max_w:
                    cut = len(word)
                    while cut > 1 and draw.textlength(word[:cut], font=f) > max_w:
                        cut -= 1
                    lines.append(word[:cut])
                    word = word[cut:]
                cur = word
        lines.append(cur)
    return lines


def fit(draw, text, weight, max_w, max_h, start, min_size, ratio=1.30):
    """박스에 들어갈 때까지 폰트를 줄인다 → (font, lines, line_height)"""
    size = start
    while size > min_size:
        f = font(weight, size)
        lines = _wrap(draw, text, f, max_w)
        lh = int(size * ratio)
        if len(lines) * lh <= max_h:
            return f, lines, lh
        size -= 2
    f = font(weight, min_size)
    return f, _wrap(draw, text, f, max_w), int(min_size * ratio)


# ─────────────────────────────────────────────────────────────
# 수직 스택 레이아웃 (측정 → 배치)
# ─────────────────────────────────────────────────────────────
@dataclass
class Stack:
    draw: ImageDraw.ImageDraw
    x: int = MARGIN
    width: int = CONTENT_W
    items: list = field(default_factory=list)

    def text(self, s, weight, start, min_size, color, max_h=10_000, ratio=1.35, w=None):
        w = w or self.width
        f, lines, lh = fit(self.draw, s, weight, w, max_h, start, min_size, ratio)
        h = len(lines) * lh
        self.items.append(("text", h, (lines, f, lh, color, self.x)))
        return self

    def gap(self, px):
        self.items.append(("gap", px, None))
        return self

    def rule(self, w=72, thickness=3, color="#000", pad=0):
        self.items.append(("rule", thickness + pad * 2, (w, thickness, color, pad, self.x)))
        return self

    def custom(self, h, fn):
        self.items.append(("custom", h, fn))
        return self

    @property
    def height(self):
        return sum(i[1] for i in self.items)

    def render(self, y):
        for kind, h, payload in self.items:
            if kind == "text":
                lines, f, lh, color, x = payload
                yy = y
                for ln in lines:
                    self.draw.text((x, yy), ln, font=f, fill=color)
                    yy += lh
            elif kind == "rule":
                w, t, color, pad, x = payload
                self.draw.line([(x, y + pad), (x + w, y + pad)], fill=color, width=t)
            elif kind == "custom":
                payload(y)
            y += h
        return y

    def render_centered(self, top=MARGIN, bottom=H - FOOTER_H, bias=TOP_BIAS):
        avail = bottom - top
        y = top + max(0, int((avail - self.height) * bias))
        return self.render(y)


# ─────────────────────────────────────────────────────────────
# 공통 요소
# ─────────────────────────────────────────────────────────────
def draw_kicker(draw, text, th, y=MARGIN):
    draw.text((MARGIN, y), " ".join(text), font=font("Bold", 26), fill=th.accent)
    draw.line([(MARGIN, y + 48), (MARGIN + 56, y + 48)], fill=th.accent, width=4)


def draw_footer(draw, th, handle, idx, total, on_dark=False):
    hcol = "#FFFFFF99" if on_dark else th.muted
    draw.text((MARGIN, H - MARGIN - 14), handle, font=font("Medium", 24), fill=hcol)
    r, gap = 5, 20
    x = W - MARGIN - (total * gap - (gap - r * 2))
    cy = H - MARGIN - 2
    for i in range(total):
        if on_dark:
            c = "#FFFFFF" if i == idx else "#FFFFFF55"
        else:
            c = th.accent if i == idx else th.dot_off
        draw.ellipse([x, cy - r, x + r * 2, cy + r], fill=c)
        x += gap


# ─────────────────────────────────────────────────────────────
# 슬라이드 타입
# ─────────────────────────────────────────────────────────────
def slide_cover(draw, s, th, meta, idx, total):
    draw_kicker(draw, PILLAR_LABEL.get(meta.get("pillar"), "NOTE"), th)

    st = Stack(draw)
    st.text(s["headline"], "ExtraBold", 96, 52, th.ink, max_h=640, ratio=1.22)
    if s.get("subline"):
        st.gap(48).text(s["subline"], "Regular", 38, 28, th.muted, max_h=260, ratio=1.52)
    st.render_centered(top=MARGIN + 130, bottom=H - FOOTER_H - 110, bias=0.42)

    draw.rectangle([MARGIN, H - MARGIN - 116, MARGIN + 120, H - MARGIN - 110], fill=th.accent)
    if s.get("badge"):
        draw.text((MARGIN, H - MARGIN - 92), s["badge"], font=font("SemiBold", 26), fill=th.accent)
    draw_footer(draw, th, meta.get("handle", ""), idx, total)


def slide_point(draw, s, th, meta, idx, total):
    num = str(s.get("index") or f"{idx:02d}")
    draw.text((MARGIN, MARGIN - 10), num, font=font("Black", 68), fill=th.accent_soft)

    st = Stack(draw)
    st.text(s["title"], "Bold", 62, 40, th.ink, max_h=300, ratio=1.28)
    st.gap(38).rule(72, 3, th.accent).gap(46)
    st.text(s["body"], "Regular", 38, 26, th.ink, max_h=560, ratio=1.60)
    st.render_centered(top=MARGIN + 110, bias=0.36)

    draw_footer(draw, th, meta.get("handle", ""), idx, total)


def slide_stat(draw, s, th, meta, idx, total):
    if s.get("eyebrow"):
        draw.text((MARGIN, MARGIN + 24), " ".join(s["eyebrow"]), font=font("Bold", 26), fill="#FFFFFFB0")

    note_h = 0
    if s.get("note"):
        f3, l3, lh3 = fit(draw, s["note"], "Regular", CONTENT_W, 200, 27, 20, 1.5)
        note_h = len(l3) * lh3
        for i, ln in enumerate(l3):
            draw.text((MARGIN, H - MARGIN - 78 - note_h + i * lh3), ln, font=f3, fill="#FFFFFFA8")

    st = Stack(draw)
    st.text(s["value"], "Black", 200, 90, th.on_accent, max_h=300, ratio=1.06)
    st.gap(44).text(s["label"], "SemiBold", 46, 30, "#FFFFFFE6", max_h=320, ratio=1.42)
    st.render_centered(top=MARGIN + 120, bottom=H - MARGIN - 110 - note_h, bias=0.40)

    draw_footer(draw, th, meta.get("handle", ""), idx, total, on_dark=True)


def slide_list(draw, s, th, meta, idx, total):
    st = Stack(draw)
    st.text(s["title"], "Bold", 58, 38, th.ink, max_h=220, ratio=1.26)
    st.gap(32).rule(72, 3, th.accent).gap(56)

    items = s["items"]
    # 항목이 많을수록 간격을 좁힌다
    item_gap = 46 if len(items) <= 4 else 34
    tx, tw = MARGIN + 46, CONTENT_W - 46

    for n, it in enumerate(items):
        t = it["t"] if isinstance(it, dict) else str(it)
        d = it.get("d") if isinstance(it, dict) else None
        ft, lt, lht = fit(draw, t, "SemiBold", tw, 160, 36, 25, 1.36)
        th_t = len(lt) * lht

        def mark(y, _y=None):
            draw.ellipse([MARGIN, y + 9, MARGIN + 20, y + 29], outline=th.accent, width=4)
        st.custom(0, mark)
        st.items.append(("text", th_t, (lt, ft, lht, th.ink, tx)))

        if d:
            fd, ld, lhd = fit(draw, d, "Regular", tw, 130, 29, 21, 1.5)
            st.gap(8).items.append(("text", len(ld) * lhd, (ld, fd, lhd, th.muted, tx)))
        if n < len(items) - 1:
            st.gap(item_gap)

    st.render_centered(bias=0.36)
    draw_footer(draw, th, meta.get("handle", ""), idx, total)


def slide_quote(draw, s, th, meta, idx, total):
    draw.text((MARGIN - 8, MARGIN - 20), "“", font=font("Black", 170), fill=th.accent_soft)

    st = Stack(draw)
    st.text(s["text"], "SemiBold", 54, 32, th.ink, max_h=620, ratio=1.44)
    if s.get("by"):
        st.gap(44).rule(48, 3, th.accent).gap(32)
        st.text(s["by"], "Medium", 28, 20, th.muted, max_h=180, ratio=1.5)
    st.render_centered(top=MARGIN + 150, bias=0.34)

    draw_footer(draw, th, meta.get("handle", ""), idx, total)


def slide_source(draw, s, th, meta, idx, total):
    # CTA 박스는 하단 고정
    cta_top = H - FOOTER_H
    if s.get("cta"):
        box_h = 180
        by = H - MARGIN - 66 - box_h
        draw.rounded_rectangle([MARGIN, by, W - MARGIN, by + box_h], radius=10, fill=th.accent)
        fc, lc, lhc = fit(draw, s["cta"], "Bold", CONTENT_W - 80, box_h - 56, 40, 26, 1.35)
        ty = by + (box_h - len(lc) * lhc) // 2
        for i, ln in enumerate(lc):
            draw.text((MARGIN + 40, ty + i * lhc), ln, font=fc, fill=th.on_accent)
        cta_top = by

    st = Stack(draw)
    st.text(s.get("title", "출처"), "Bold", 52, 34, th.ink, max_h=160, ratio=1.26)
    st.gap(28).rule(72, 3, th.accent).gap(46)
    srcs = s.get("sources", [])
    for i, src in enumerate(srcs):
        st.text("· " + src, "Regular", 26, 19, th.muted, max_h=300, ratio=1.5)
        if i < len(srcs) - 1:
            st.gap(24)
    st.render_centered(top=MARGIN, bottom=cta_top - 40, bias=0.30)

    draw_footer(draw, th, meta.get("handle", ""), idx, total)


RENDERERS = {
    "cover": slide_cover, "point": slide_point, "stat": slide_stat,
    "list": slide_list, "quote": slide_quote, "source": slide_source,
}


# ─────────────────────────────────────────────────────────────
def render_post(spec: dict, outdir: str) -> list[str]:
    th = THEMES.get(spec.get("pillar", "default"), THEMES["default"])
    slides = spec["slides"]
    os.makedirs(outdir, exist_ok=True)

    photo = spec.get("photo")
    bg_base = stat_base = None
    if photo:
        bg_base, stat_base = photo_bases(photo, th)

    paths = []
    for i, s in enumerate(slides):
        if photo:
            base = stat_base if s["type"] == "stat" else bg_base
            img = base.copy()
        else:
            img = Image.new("RGB", (W, H), th.accent if s["type"] == "stat" else th.bg)
        draw = ImageDraw.Draw(img)
        RENDERERS[s["type"]](draw, s, th, spec, i, len(slides))
        p = os.path.join(outdir, f"{spec['slug']}_{i+1:02d}.jpg")
        img.save(p, "JPEG", quality=92, subsampling=0, optimize=True)
        paths.append(p)
    return paths


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    outdir = os.path.join(sys.argv[2] if len(sys.argv) > 2 else "out", spec["slug"])
    for p in render_post(spec, outdir):
        print(p)


if __name__ == "__main__":
    main()
