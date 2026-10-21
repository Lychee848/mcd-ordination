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

import hashlib
import math
import os
import random
import shlex
import subprocess
from pathlib import Path

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


# ---------------------------------------------------------------- 底图来源与变体
#
# 底图只有"画面窗里的那一张画"这一层，文字/星级/六维/编号永远是代码画的。
# 三级来源，优先级从高到低：
#   ① users/ 下这个用户自己的独版图（有就用，最贵但最独特）
#   ② assets/plates/ 里按画派+卡种共享的底图（+ 确定性构图变体）
#   ③ 程序化底图（plates.procedural_plate，零素材也能出卡）
#
# 为什么需要"变体"：共享底图意味着同画派的几百人会拿到同一张画。
# 变体只改裁切/缩放/镜像，不改内容 —— 能拉开观感，但不能替代"每人一张"。

REPO = Path(__file__).resolve().parent.parent.parent
PLATE_DIR = REPO / "assets" / "plates"
USER_DIR = PLATE_DIR / "users"

ALIAS = {"item": "still", "spell": "still"}


def _safe(s: str) -> str:
    return "".join(c for c in str(s) if c.isalnum() or c in "-_") or "anon"


def resolve(art_key: str, role: str, uid: str | None = None):
    """返回 (路径, 来源)，来源 ∈ user / shared / None"""
    if uid:
        u = USER_DIR / f"{_safe(uid)}_{role}.png"
        if u.exists():
            return u, "user"
    names = [f"plate_{art_key}_{role}.png"]
    if role in ALIAS:
        names.append(f"plate_{art_key}_{ALIAS[role]}.png")
    names.append(f"plate_{art_key}.png")
    for n in names:
        p = PLATE_DIR / n
        if p.exists():
            return p, "shared"
    return None, None


def vary(src: Path, uid: str, out_dir: Path, version: int = 1) -> Path:
    """同一张底图，按用户做确定性的构图变体：缩放 1.00–1.12、偏移 ±25%、50% 镜像。
    同一用户永远同一版；换用户换一版。零成本，不调用任何模型。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{src.stem}__{_safe(uid)[:14]}.png"
    if dst.exists():
        return dst

    seed = int(hashlib.sha256(f"{uid}|plate-var-v{version}".encode()).hexdigest()[:8], 16)
    rnd = random.Random(seed)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    zoom = 1.0 + rnd.random() * 0.12
    cw, ch = int(w / zoom), int(h / zoom)
    ox = int((w - cw) * (0.5 + (rnd.random() - 0.5) * 0.5))
    oy = int((h - ch) * (0.5 + (rnd.random() - 0.5) * 0.5))
    im = im.crop((ox, oy, ox + cw, oy + ch)).resize((w, h), Image.LANCZOS)
    if rnd.random() < 0.5:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    im.save(dst, quality=94)
    return dst


def generate(prompt: str, out_path: Path, timeout: int = 180) -> bool:
    """
    可选：把"出图"交给外部命令。设置环境变量后，本函数会用
        {prompt} / {out} 两个占位符调用它。
    例：
        export MCD_PLATE_CMD='your-image-cli --prompt "{prompt}" --out "{out}"'
    返回值只表示"命令是否成功"，不做内容检查。
    """
    cmd = os.environ.get("MCD_PLATE_CMD")
    if not cmd:
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    full = cmd.replace("{prompt}", shlex.quote(prompt)).replace("{out}", shlex.quote(str(out_path)))
    try:
        r = subprocess.run(full, shell=True, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return r.returncode == 0 and out_path.exists()
    except Exception:
        return False
