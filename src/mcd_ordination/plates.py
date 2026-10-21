#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plates.py —— 程序化底图（L1.5）

降级链：L0 纯 SVG（默认） → L1.5 程序化底图（本文件，PIL） → L2 AI 出图（assets/plates）

为什么需要它：AI 出图只有 7 个画派，但用户的画派是 hash 出来的，
不可能为每个人预先生成一张。没有对应画派的 plate 时，不能让卡面开天窗——
所以用同一套几何语言（光芒 / 光环 / 剪影）现画一张，色板取自该画派的 grade。
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

from . import render_svg as RS


def procedural_plate(st: dict, kind: str = "effect", size: int = 1024) -> Image.Image:
    fr = st["frame"]
    glow = tuple(int(v) for v in fr["glow"])
    bg = tuple(int(v) for v in fr["bg"])
    base = RS.mix(glow, bg, 0.30)
    img = Image.new("RGB", (size, size), base)
    d = ImageDraw.Draw(img, "RGBA")

    gold = (199, 154, 58)
    ink = RS.mix(fr["ink"], (0, 0, 0), 0.25)
    cx, cy = size / 2, size * 0.60
    rnd = random.Random(abs(hash((str(st.get("_seed", "1")), kind))) % 10 ** 6)

    # 光晕：由外向内逐圈加深，避免出现"渐变器依赖"
    for i in range(26):
        r = size * (0.52 - i * 0.018)
        a = int(10 + i * 3)
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  fill=RS.mix(base, (255, 255, 255), 0.01 * i) + (a,), outline=None)

    rays = rnd.choice([12, 16, 20])
    for i in range(rays):
        a = (i / rays) * math.tau
        d.line([cx, cy, cx + math.cos(a) * size, cy + math.sin(a) * size],
               fill=gold + (70,), width=max(2, size // 520))

    for r, w in ((size * 0.36, 4), (size * 0.30, 2)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=gold + (170,), width=w)

    s = size
    if kind in ("monster", "effect", "ritual", "fusion", "xyz", "link", "synchro"):
        hr = s * 0.048
        hy = cy - s * 0.175
        d.ellipse([cx - hr, hy - hr, cx + hr, hy + hr], fill=ink + (238,))
        d.ellipse([cx - s * 0.062, hy + s * 0.015, cx + s * 0.062, hy + s * 0.115], fill=ink + (238,))
        d.polygon([(cx - s * 0.062, hy + s * 0.065),
                   (cx + s * 0.062, hy + s * 0.065),
                   (cx + s * 0.115, cy + s * 0.145),
                   (cx - s * 0.115, cy + s * 0.145)], fill=ink + (238,))
        rr = hr * 2.0
        d.ellipse([cx - rr, hy - rr, cx + rr, hy + rr], outline=gold + (240,), width=max(3, s // 380))
        d.line([cx - s * 0.155, cy + s * 0.148, cx + s * 0.155, cy + s * 0.148],
               fill=gold + (180,), width=max(2, s // 520))
    elif kind == "item":
        r = s * 0.12
        d.ellipse([cx - r, cy - r - s * 0.06, cx + r, cy + r - s * 0.06],
                  outline=ink + (235,), width=int(s * 0.035))
        d.line([cx, cy + s * 0.06, cx, cy + s * 0.26], fill=ink + (235,), width=int(s * 0.03))
        d.arc([cx - s * 0.11, cy + s * 0.20, cx + s * 0.11, cy + s * 0.32], 0, 180,
              fill=ink + (235,), width=int(s * 0.03))
    elif kind in ("spell", "rite", "trap"):
        d.rectangle([cx - s * 0.16, cy - s * 0.22, cx + s * 0.16, cy + s * 0.20], fill=ink + (225,))
        d.rectangle([cx - s * 0.12, cy - s * 0.18, cx + s * 0.12, cy + s * 0.16],
                    outline=RS.mix(glow, (255, 255, 255), 0.75) + (255,), width=3)
        d.line([cx, cy - s * 0.10, cx, cy + s * 0.10], fill=(255, 250, 236, 240), width=6)
        d.line([cx - s * 0.06, cy - s * 0.03, cx + s * 0.06, cy - s * 0.03], fill=(255, 250, 236, 240), width=6)
    else:  # field：一间有拱门的店
        bw, bh = s * 0.58, s * 0.30
        bx0, by0 = cx - bw / 2, cy - s * 0.08
        d.rectangle([bx0, by0, bx0 + bw, by0 + bh], fill=ink + (222,))
        dw = bw * 0.32
        d.rectangle([cx - dw / 2, by0 + bh * 0.44, cx + dw / 2, by0 + bh], fill=base + (255,))
        d.pieslice([cx - dw / 2, by0 + bh * 0.44 - dw / 2, cx + dw / 2, by0 + bh * 0.44 + dw / 2],
                   180, 360, fill=base + (255,))
        d.arc([cx - bw * 0.44, by0 - s * 0.035, cx + bw * 0.44, by0 + s * 0.085],
              180, 360, fill=gold + (225,), width=max(4, s // 260))
        d.ellipse([cx - s * 0.032, by0 - s * 0.105, cx + s * 0.032, by0 - s * 0.041],
                  outline=gold + (235,), width=max(3, s // 400))
        d.line([bx0 - s * 0.06, by0 + bh, bx0 + bw + s * 0.06, by0 + bh],
               fill=gold + (200,), width=max(3, s // 380))

    # 边缘压暗，让贴进画面窗后不抢文字
    edge = Image.new("L", (size, size), 0)
    de = ImageDraw.Draw(edge)
    for i in range(28):
        de.rectangle([i, i, size - i, size - i], outline=min(255, 8 + i * 6))
    img = Image.composite(Image.new("RGB", (size, size), RS.mix(bg, (0, 0, 0), 0.18)), img, edge)
    return img
