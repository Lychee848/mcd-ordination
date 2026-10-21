#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_svg.py —— L0 卡面：纯 SVG，零依赖、零 Key、零等待

为什么它是默认渲染器（而不是备胎）：
  同类作品最常见的死法是"要 API Key 才能看见一张卡"，7 个作品全是 0 星。
  所以本项目的默认路径必须是：**不装 Pillow、不填 Token，也能看到完整卡面。**

L0 只做程序化图形（光芒 / 光环 / 剪影 / 徽记），不假装是人像；
真正的人像由 L1（官方商品图）或 L2（AI 出图）在画面窗内替换，文字与版式永不变。
"""
from __future__ import annotations

import math
import random

W, H, OUT = 750, 1100, 26
FONT = "'Songti SC','Noto Serif CJK SC','Source Han Serif SC',serif"


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def rgb(c) -> str:
    return "#%02X%02X%02X" % tuple(c[:3])


def mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1[:3], c2[:3]))


def cw(ch: str, size: float) -> float:
    """单字宽度估算：汉字按字号，ASCII 按 0.55"""
    return size if ord(ch) > 0x2E80 else size * 0.55


def wrap(text: str, size: float, maxw: float) -> list:
    lines, cur, w = [], "", 0.0
    for ch in str(text):
        if ch == "\n":
            lines.append(cur)
            cur, w = "", 0.0
            continue
        c = cw(ch, size)
        if w + c > maxw and cur:
            lines.append(cur)
            cur, w = ch, c
        else:
            cur += ch
            w += c
    if cur:
        lines.append(cur)
    return lines


def text_block(x, y, text, size, fill, maxw, lh=1.55, weight="400", anchor="start"):
    out = []
    for i, ln in enumerate(wrap(text, size, maxw)):
        out.append(
            f'<text x="{x}" y="{y + i * size * lh:.1f}" font-family="{FONT}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{esc(ln)}</text>')
    return "\n".join(out), y + len(wrap(text, size, maxw)) * size * lh


# ---------------------------------------------------------------- 程序化画面

LAYOUT_TO_ART = {"monster": "effect", "relic": "item", "rite": "spell", "field": "field"}


def _art(kind: str, x, y, w, h, st, seed: int) -> str:
    kind = LAYOUT_TO_ART.get(kind, kind)
    fr, rnd = st["frame"], random.Random(seed)
    ink = mix(fr["ink"], (0, 0, 0), 0.2)
    gold = "#C79A3A"
    cx, cy = x + w / 2, y + h * 0.62
    base = mix(fr["glow"], fr["bg"], 0.35)
    g = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{rgb(base)}"/>']

    # 光芒
    rays = rnd.choice([12, 16, 20])
    for i in range(rays):
        a = (i / rays) * math.tau
        x2, y2 = cx + math.cos(a) * w, cy + math.sin(a) * h
        g.append(f'<line x1="{cx:.0f}" y1="{cy:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
                 f'stroke="{gold}" stroke-width="1.2" opacity="0.30"/>')
    # 同心环
    for r, op in ((h * 0.34, 0.55), (h * 0.28, 0.35)):
        g.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="none" '
                 f'stroke="{gold}" stroke-width="2" opacity="{op}"/>')
    g.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{h * 0.22:.0f}" '
             f'fill="{rgb(mix(fr["glow"], (255, 255, 255), 0.5))}" opacity="0.75"/>')

    # 剪影：L0 不画像，只画"形"
    s = min(w, h)
    if kind in ("effect", "normal_monster", "ritual", "fusion", "xyz", "link", "synchro"):
        hr = s * 0.048
        hy = cy - s * 0.175
        g.append(f'<circle cx="{cx:.0f}" cy="{hy:.0f}" r="{hr:.0f}" fill="{rgb(ink)}" opacity="0.92"/>')
        g.append(f'<ellipse cx="{cx:.0f}" cy="{hy + s * 0.065:.0f}" rx="{s * 0.062:.0f}" ry="{s * 0.05:.0f}" '
                 f'fill="{rgb(ink)}" opacity="0.92"/>')
        g.append(f'<polygon points="{cx - s * 0.062:.0f},{hy + s * 0.065:.0f} {cx + s * 0.062:.0f},{hy + s * 0.065:.0f} '
                 f'{cx + s * 0.115:.0f},{cy + s * 0.145:.0f} {cx - s * 0.115:.0f},{cy + s * 0.145:.0f}" '
                 f'fill="{rgb(ink)}" opacity="0.92"/>')
        r2 = hr * 2.0
        g.append(f'<circle cx="{cx:.0f}" cy="{hy:.0f}" r="{r2:.0f}" fill="none" '
                 f'stroke="{gold}" stroke-width="3" opacity="0.92"/>')
        g.append(f'<line x1="{cx - s * 0.155:.0f}" y1="{cy + s * 0.148:.0f}" '
                 f'x2="{cx + s * 0.155:.0f}" y2="{cy + s * 0.148:.0f}" '
                 f'stroke="{gold}" stroke-width="2" opacity="0.6"/>')
    elif kind == "item":
        g.append(f'<circle cx="{cx:.0f}" cy="{cy - s * 0.06:.0f}" r="{s * 0.12:.0f}" '
                 f'fill="none" stroke="{rgb(ink)}" stroke-width="{s * 0.035:.0f}"/>')
        g.append(f'<line x1="{cx:.0f}" y1="{cy + s * 0.06:.0f}" x2="{cx:.0f}" '
                 f'y2="{cy + s * 0.26:.0f}" stroke="{rgb(ink)}" stroke-width="{s * 0.03:.0f}"/>')
        g.append(f'<path d="M{cx - s * 0.11:.0f} {cy + s * 0.26:.0f} '
                 f'q{s * 0.11:.0f} {s * 0.06:.0f} {s * 0.22:.0f} 0" fill="none" '
                 f'stroke="{rgb(ink)}" stroke-width="{s * 0.03:.0f}"/>')
    elif kind in ("spell", "trap"):
        g.append(f'<rect x="{cx - s * 0.16:.0f}" y="{cy - s * 0.22:.0f}" '
                 f'width="{s * 0.32:.0f}" height="{s * 0.42:.0f}" fill="{rgb(ink)}" opacity="0.86"/>')
        g.append(f'<rect x="{cx - s * 0.12:.0f}" y="{cy - s * 0.18:.0f}" '
                 f'width="{s * 0.24:.0f}" height="{s * 0.34:.0f}" fill="none" '
                 f'stroke="{rgb(mix(fr["glow"], (255, 255, 255), 0.7))}" stroke-width="2"/>')
        g.append(f'<line x1="{cx:.0f}" y1="{cy - s * 0.10:.0f}" x2="{cx:.0f}" '
                 f'y2="{cy + s * 0.10:.0f}" stroke="{rgb(mix(fr["glow"], (255,255,255),0.8))}" stroke-width="4"/>')
        g.append(f'<line x1="{cx - s * 0.06:.0f}" y1="{cy - s * 0.03:.0f}" x2="{cx + s * 0.06:.0f}" '
                 f'y2="{cy - s * 0.03:.0f}" stroke="{rgb(mix(fr["glow"], (255,255,255),0.8))}" stroke-width="4"/>')
    else:  # field：一间有拱门的店
        bw, bh = s * 0.58, s * 0.30
        bx0, by0 = cx - bw / 2, cy - s * 0.08
        g.append(f'<rect x="{bx0:.0f}" y="{by0:.0f}" width="{bw:.0f}" height="{bh:.0f}" '
                 f'fill="{rgb(ink)}" opacity="0.88"/>')
        dw = bw * 0.32
        g.append(f'<path d="M{cx - dw / 2:.0f} {by0 + bh:.0f} L{cx - dw / 2:.0f} {by0 + bh * 0.44:.0f} '
                 f'a{dw / 2:.0f} {dw / 2:.0f} 0 0 1 {dw:.0f} 0 L{cx + dw / 2:.0f} {by0 + bh:.0f} Z" '
                 f'fill="{rgb(base)}"/>')
        g.append(f'<path d="M{cx - bw * 0.44:.0f} {by0:.0f} a{bw * 0.44:.0f} {s * 0.06:.0f} 0 0 1 {bw * 0.88:.0f} 0" '
                 f'fill="none" stroke="{gold}" stroke-width="4" opacity="0.85"/>')
        g.append(f'<circle cx="{cx:.0f}" cy="{by0 - s * 0.073:.0f}" r="{s * 0.032:.0f}" '
                 f'fill="none" stroke="{gold}" stroke-width="3"/>')
        g.append(f'<line x1="{bx0 - s * 0.06:.0f}" y1="{by0 + bh:.0f}" '
                 f'x2="{bx0 + bw + s * 0.06:.0f}" y2="{by0 + bh:.0f}" '
                 f'stroke="{gold}" stroke-width="3" opacity="0.7"/>')
    g.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" '
             f'stroke="{rgb(ink)}" stroke-width="3"/>')
    return "".join(g)


# ---------------------------------------------------------------- 部件

def _stars(x_right, y, n, r=11) -> str:
    if not n:
        return ""
    pts = []
    for i in range(n):
        cx = x_right - i * (r * 2 + 4)
        d = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = r if k % 2 == 0 else r * 0.44
            d.append(f"{cx + rr * math.cos(a):.1f},{y + rr * math.sin(a):.1f}")
        pts.append(f'<polygon points="{" ".join(d)}" fill="#FFE27A" stroke="#3A2A0C" stroke-width="1.4"/>')
    return "".join(pts)


def _kind_row(x, y, w, text, st) -> str:
    fr = st["frame"]
    return (f'<rect x="{x}" y="{y}" width="{w}" height="34" fill="{rgb(mix(fr["bg"], fr["ink"], 0.10))}"/>'
            f'<text x="{x + 12}" y="{y + 24}" font-family="{FONT}" font-size="18" '
            f'fill="{rgb(mix(fr["ink"], (0, 0, 0), 0.35))}">{esc(text)}</text>')


def _effect_box(x, y, w, h, data, st) -> str:
    fr = st["frame"]
    ink = rgb(mix(fr["ink"], (0, 0, 0), 0.25))
    paper = rgb(mix(fr["glow"], (255, 255, 255), 0.6))
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{paper}" '
           f'stroke="{ink}" stroke-width="2"/>']
    yy = y + 30
    maxw = w - 32
    for tag, body in data.get("effects", []):
        if tag:
            out.append(f'<text x="{x + 16}" y="{yy}" font-family="{FONT}" font-size="18" '
                       f'font-weight="500" fill="#962E24">{esc(tag)}</text>')
            yy += 24
        s, yy = text_block(x + 16, yy, body, 18, ink, maxw)
        out.append(s)
        yy += 10
    if data.get("flavor"):
        fy = y + h - 22
        out.append(f'<line x1="{x + 16}" y1="{fy - 18}" x2="{x + w - 16}" y2="{fy - 18}" '
                   f'stroke="{rgb(mix(fr["ink"], fr["bg"], 0.6))}" stroke-width="1"/>')
        out.append(f'<text x="{x + w / 2}" y="{fy}" font-family="{FONT}" font-size="14" '
                   f'fill="{rgb(mix(fr["ink"], fr["bg"], 0.3))}" text-anchor="middle">'
                   f'{esc(data["flavor"])}</text>')
    return "".join(out)


def _stats(x, y, w, stats, st, row_h: int = 38) -> str:
    fr = st["frame"]
    ink = rgb(mix(fr["ink"], (0, 0, 0), 0.3))
    out = []
    for i, (cn, lat, val, unit, ratio) in enumerate(stats):
        cy = y + i * row_h
        out.append(f'<text x="{x}" y="{cy + 14}" font-family="{FONT}" font-size="17" fill="{ink}">{esc(cn)}</text>')
        out.append(f'<text x="{x + 52}" y="{cy + 14}" font-family="{FONT}" font-size="11" '
                   f'fill="{rgb(mix(fr["ink"], fr["bg"], 0.25))}" letter-spacing="1.2">{esc(lat)}</text>')
        bx, bw = x + 150, w - 150 - 110
        out.append(f'<rect x="{bx}" y="{cy + 4}" width="{bw}" height="10" fill="none" '
                   f'stroke="{rgb(mix(fr["ink"], fr["bg"], 0.5))}" stroke-width="1"/>')
        out.append(f'<rect x="{bx}" y="{cy + 4}" width="{max(1, bw * ratio):.0f}" height="10" fill="#962E24" opacity="0.75"/>')
        out.append(f'<text x="{x + w}" y="{cy + 14}" font-family="{FONT}" font-size="17" '
                   f'fill="{ink}" text-anchor="end">{esc(val)} {esc(unit)}</text>')
    return "".join(out)


def _footer(x, y, w, data, st) -> str:
    fr = st["frame"]
    ink = rgb(mix(fr["ink"], (0, 0, 0), 0.2))
    out = [f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" '
           f'stroke="{rgb(mix(fr["ink"], fr["bg"], 0.5))}" stroke-width="1"/>']
    out.append(f'<text x="{x}" y="{y + 26}" font-family="{FONT}" font-size="13" '
               f'fill="{ink}" letter-spacing="1.6">NO. {esc(data.get("serial", ""))}</text>')
    out.append(f'<text x="{x + w}" y="{y + 26}" font-family="{FONT}" font-size="13" '
               f'fill="{rgb(mix(fr["ink"], fr["bg"], 0.25))}" text-anchor="end">'
               f'{esc(data.get("provenance", ""))}</text>')
    if data.get("verify"):
        out.append(f'<text x="{x + w}" y="{y + 52}" font-family="{FONT}" font-size="12" '
                   f'fill="#962E24" text-anchor="end" letter-spacing="1.4">'
                   f'V {esc(data["verify"])}</text>')
    out.append(f'<text x="{x + w / 2}" y="{y + 26}" font-family="{FONT}" font-size="11" '
               f'fill="{rgb(mix(fr["ink"], fr["bg"], 0.45))}" text-anchor="middle" '
               f'letter-spacing="1.2">非官方 · 粉丝二创</text>')
    return "".join(out)


# ---------------------------------------------------------------- 主入口

def render(data: dict, st: dict, out: str | None = None) -> str:
    fr = st["frame"]
    ink = mix(fr["ink"], (0, 0, 0), 0.25)
    paper = mix(fr["glow"], (255, 255, 255), 0.62)
    x0, w = 64, W - 128
    seed = int(str(st.get("_seed", "7"))[:12] or 7)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="#FCFAF6"/>',
           f'<rect x="{OUT}" y="{OUT}" width="{W - 2 * OUT}" height="{H - 2 * OUT}" rx="20" '
           f'fill="{rgb(fr["bg"])}" stroke="{rgb(mix(fr["ink"], (0, 0, 0), 0.15))}" stroke-width="3"/>',
           f'<rect x="{OUT + 10}" y="{OUT + 10}" width="{W - 2 * OUT - 20}" height="{H - 2 * OUT - 20}" rx="14" '
           f'fill="{rgb(paper)}" stroke="{rgb(mix(fr["ink"], fr["bg"], 0.45))}" stroke-width="1"/>']

    # 卡名
    name = data.get("name", "")
    size = 42 if len(name) <= 7 else 34
    svg.append(f'<text x="{x0}" y="{OUT + 62}" font-family="{FONT}" font-size="{size}" '
               f'font-weight="500" fill="{rgb(ink)}" stroke="{rgb(mix(fr["bg"], (255,255,255),0.5))}" '
               f'stroke-width="3" paint-order="stroke">{esc(name)}</text>')

    # 属性盘
    cx, cy = W - OUT - 72, OUT + 66
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="32" fill="#1A181E" stroke="#C79A3A" stroke-width="2"/>')
    svg.append(f'<text x="{cx}" y="{cy + 2}" font-family="{FONT}" font-size="26" fill="#F3E7C8" '
               f'text-anchor="middle" dominant-baseline="middle">{esc(data.get("attr", "·"))}</text>')
    lat = str(data.get("attr_lat", ""))
    if len(lat) <= 4:
        svg.append(f'<text x="{cx}" y="{cy + 26}" font-family="{FONT}" font-size="8" fill="#C79A3A" '
                   f'text-anchor="middle" letter-spacing="1">{esc(lat)}</text>')

    # 画面窗
    ay = OUT + 118
    kind = st.get("layout", "monster")
    ratio = {"monster": 0.60, "relic": 0.52, "rite": 0.46, "field": 0.34}[kind]
    ah = int(w * ratio)
    svg.append(_art(kind, x0, ay, w, ah, st, seed))
    lv = data.get("level", 0)
    if lv:                                   # 星级压在窗口上沿，必须在窗口之后画
        svg.append(_stars(W - OUT - 12, ay - 16, lv, r=10))
    aby = ay + ah

    svg.append(_kind_row(x0, aby + 12, w, data.get("kind_line", ""), st))
    y = aby + 12 + 34 + 12

    # 版式分支
    foot_y = H - OUT - 92
    if kind == "relic":
        eff_h = 110
        svg.append(_effect_box(x0, y, w, eff_h, data, st))
        sy = y + eff_h + 16
        row_h = max(34, min(52, (foot_y - 16 - sy) // 6))
        svg.append(_stats(x0 + 6, sy, w - 12, data.get("stats", []), st, row_h=row_h))
        svg.append(_footer(x0, foot_y, w, data, st))
    elif kind == "rite":
        eff_h = foot_y - 18 - y
        svg.append(_effect_box(x0, y, w, eff_h, data, st))
        svg.append(_footer(x0, foot_y, w, data, st))
    elif kind == "field":
        eff_h = foot_y - 18 - y
        svg.append(_effect_box(x0, y, w, eff_h, data, st))
        svg.append(_footer(x0, foot_y, w, data, st))
    else:
        eff_h = foot_y - 96 - y
        svg.append(_effect_box(x0, y, w, eff_h, data, st))
        # 攻守
        svg.append(f'<text x="{x0}" y="{foot_y - 44}" font-family="{FONT}" font-size="15" '
                   f'fill="{rgb(ink)}" letter-spacing="1.6">虔 PIETAS</text>')
        svg.append(f'<text x="{x0 + w}" y="{foot_y - 44}" font-family="{FONT}" font-size="15" '
                   f'fill="{rgb(ink)}" letter-spacing="1.6" text-anchor="end">守 IEIUNIUM</text>')
        svg.append(f'<text x="{x0}" y="{foot_y - 8}" font-family="{FONT}" font-size="34" '
                   f'fill="{rgb(ink)}">{data.get("atk", 0)}</text>')
        svg.append(f'<text x="{x0 + w}" y="{foot_y - 8}" font-family="{FONT}" font-size="34" '
                   f'fill="{rgb(ink)}" text-anchor="end">{data.get("def", 0)}</text>')
        svg.append(_footer(x0, foot_y + 26, w, data, st))

    svg.append("</svg>")
    doc = "\n".join(svg)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(doc)
    return doc
