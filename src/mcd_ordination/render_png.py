#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_card_v2.py —— 交换卡板式（游戏王读法）+ 每用户换脸 + 四种卡种版式

版式分支（st["layout"]）：
  monster 人物卡  名栏 / 属性盘 / 星级 / 画面窗 / 种属行 / 效果框 / 攻守 / 卡号
  relic   食物·道具卡  名栏 / 属性盘 / 画面窗 / 种属行 / 效果框 / 营养六维 / 卡号
  rite    行为·事件卡  徽记 / 名栏 / 画面窗 / 种属行 / 大效果框 / 卡号（无攻守无星级）
  field   地点卡  横幅画面窗 / 名栏 / 种属行 / 效果框 / 卡号

同一份订单 -> 同一张脸（styles.resolve_style 保证）
AI 只负责画面；文字、数值、星级、编号一律代码画。
"""
import colorsys
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from . import styles as S

W, H = 750, 1100
OUT = 26

from .fonts import resolve as _resolve_font

F_LAT_CAP = _resolve_font("display")   # 西文大写标题（Copperplate / DejaVu Serif）
F_LAT_SER = _resolve_font("serif")     # 西文衬线
F_LAT_GEO = _resolve_font("numeral")   # 数字
F_CN      = _resolve_font("cjk")       # 中文（Songti / Noto Sans CJK / msyh）


def font(path, size, index=0):
    """找不到字体时不抛异常：退回 Pillow 默认字体（西文可读，中文会缺字）。
    跨平台部署请装一个 CJK 字体，或设置 MCD_FONT_CJK 环境变量。"""
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()


def letter(d, xy, text, fnt, fill, tr=0.0):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += d.textlength(ch, font=fnt) + tr
    return x


def tw(d, text, fnt, tr=0.0):
    return sum(d.textlength(c, font=fnt) for c in text) + tr * max(0, len(text) - 1)


NO_START = "」』）】》〉、。，．：；？！%‰℃…·"
NO_END   = "「『（【《〈"


def wrap_cn(d, text, fnt, width):
    """中文断行 + 简易禁则处理：标点不许出现在行首，前括号不许留在行尾"""
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if d.textlength(cur + ch, font=fnt) > width and cur:
            if ch in NO_START and len(cur) > 1:
                lines.append(cur[:-1]); cur = cur[-1] + ch
            elif cur[-1] in NO_END:
                lines.append(cur[:-1]); cur = cur[-1] + ch
            else:
                lines.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def hue_frame(st):
    """把框色按用户色相旋一下：同为效果怪兽的两个人也不会是同一块橙"""
    fr = dict(st["frame"])
    if st.get("hue"):
        for key in ("bg", "glow"):
            r, g, b = [v / 255 for v in fr[key]]
            hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
            r, g, b = colorsys.hls_to_rgb((hh + st["hue"] / 360.0) % 1.0, ll, ss)
            fr[key] = (int(r * 255), int(g * 255), int(b * 255))
    return fr


# ------------------------------------------------------------------ 底 & 框

def build_base(st):
    fr = st["frame"]
    img = Image.new("RGB", (W, H), (252, 250, 246))
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = OUT, OUT, W - OUT, H - OUT
    g = S.h(st.get("_seed", "?"), "grad") % 3
    for i in range(y1 - y0):
        t = i / max(1, (y1 - y0))
        if g == 0:
            c = mix(fr["glow"], fr["bg"], t)
        elif g == 1:
            c = mix(fr["bg"], fr["glow"], (math.sin(t * math.pi * 1.2) + 1) / 2)
        else:
            c = mix(fr["glow"], fr["bg"], t ** 0.7)
        d.line([x0, y0 + i, x1, y0 + i], fill=c)

    if st["art"]["grade"]["grain"] > 0:
        n = Image.effect_noise((W, H), int(st["art"]["grade"]["grain"] * 90)).convert("L")
        img = Image.blend(img, Image.merge("RGB", (n, n, n)), st["art"]["grade"]["grain"] * 0.55)
    return _pattern(img, st, fr)


def _pattern(img, st, fr):
    pat = st.get("pattern", "none")
    if pat == "none":
        return img
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    col = mix(fr["bg"], (0, 0, 0), 0.34) + (26,)
    cx, cy = W // 2, 880
    if pat == "rays":
        for a in range(0, 360, 6):
            r = 1400
            d.line([cx, cy, cx + r * math.cos(math.radians(a)),
                    cy + r * math.sin(math.radians(a))], fill=col, width=2)
    elif pat == "rings":
        for i in range(9):
            r = 60 + i * 46
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=2)
    elif pat == "dots":
        for yy in range(OUT, H - OUT, 11):
            for xx in range(OUT, W - OUT, 11):
                d.point((xx, yy), fill=mix(fr["bg"], (0, 0, 0), 0.28) + (40,))
    elif pat == "grid":
        for xx in range(OUT, W - OUT, 26):
            d.line([xx, OUT, xx, H - OUT], fill=col, width=1)
        for yy in range(OUT, H - OUT, 26):
            d.line([OUT, yy, W - OUT, yy], fill=col, width=1)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def outer_edge(img, st):
    f = st["foil"]
    if not f["edge"]:
        return img
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    col = (214, 176, 96, 235) if f["gold_name"] else (206, 214, 222, 220)
    for i, a in ((0, 255), (1, 120)):
        d.rectangle([OUT + i, OUT + i, W - OUT - 1 - i, H - OUT - 1 - i],
                    outline=col[:3] + (int(a * 0.9),), width=1)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


# ------------------------------------------------------------------ 画面窗

def paste_plate(img, st, plate_path, box, crop_top=0.05):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    p = Image.open(plate_path).convert("RGB")
    w, h = p.size
    dx, dy = int(w * 0.034), int(h * 0.034)
    p = p.crop((dx, dy, w - dx, h - dy))
    pw, ph = p.size
    tgt = bw / bh
    if pw / ph > tgt:
        nw = int(ph * tgt); p = p.crop(((pw - nw) // 2, 0, (pw + nw) // 2, ph))
    else:
        nh = int(pw / tgt); top = int(ph * crop_top)
        p = p.crop((0, top, pw, min(ph, top + nh)))
    p = p.resize((bw, bh), Image.LANCZOS)

    g = st["art"]["grade"]
    p = ImageEnhance.Color(p).enhance(g["sat"])
    p = ImageEnhance.Contrast(p).enhance(g["contrast"])
    p = ImageEnhance.Brightness(p).enhance(g.get("bright", 1.0))
    wr, wg, wb, wa = g["warmth"]
    p = Image.blend(p, Image.new("RGB", (bw, bh), (wr, wg, wb)), wa)

    img.paste(p, (x0, y0))
    d = ImageDraw.Draw(img)
    d.rectangle([x0 - 1, y0 - 1, x1, y1], outline=(28, 22, 16), width=2)
    d.rectangle([x0 - 4, y0 - 4, x1 + 3, y1 + 3], outline=(250, 246, 238), width=2)
    d.rectangle([x0 - 6, y0 - 6, x1 + 5, y1 + 5], outline=(28, 22, 16), width=1)
    _holo(img, st, box)


def _holo(img, st, box):
    f = st["foil"]
    if f["holo"] <= 0:
        return
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cols = [(255, 255, 255), (255, 214, 130), (160, 226, 255), (255, 168, 226),
            (206, 255, 196), (255, 236, 160)]
    step = 22 if f["tint"] in ("rainbow", None) else 26
    for i in range(-bh, bw + bh, step):
        c = cols[i // step % len(cols)]
        a = int(f["holo"] * 255 * (0.35 + 0.4 * ((i // step) % 3) / 2))
        d.line([i, bh, i + bh, 0], fill=c + (a,), width=4)
    layer = layer.filter(ImageFilter.GaussianBlur(2.2))
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * 0.55)))
    img.paste(Image.alpha_composite(img.crop(box).convert("RGBA"), layer).convert("RGB"), box)


# ------------------------------------------------------------------ 小组件

def star(d, cx, cy, r, fill, outline=None):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.44
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    if outline:
        big = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = (r + 2.2) if i % 2 == 0 else (r * 0.44 + 1.4)
            big.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        d.polygon(big, fill=outline)
    d.polygon(pts, fill=fill)


def attribute_badge(d, cx, cy, R, ch, lat, bright=False):
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(24, 20, 16),
              outline=(240, 226, 194) if bright else (228, 214, 186), width=2)
    d.ellipse([cx - R + 4, cy - R + 4, cx + R - 4, cy + R - 4],
              outline=(150, 136, 112), width=1)
    fc = font(F_CN, 30)
    d.text((cx - d.textlength(ch, font=fc) / 2, cy - 18), ch, font=fc, fill=(250, 244, 230))
    fl = font(F_LAT_CAP, 8)
    lw = tw(d, lat, fl, 0.8)
    if lw <= 2 * R - 24:            # 放不下就省略，宁可没有，也不要压到圆边
        letter(d, (cx - lw / 2, cy + 15), lat, fl, (200, 188, 164), tr=0.8)


def draw_name(d, st, x, y, name, size=44):
    f = font(F_CN, size)
    if st["foil"]["gold_name"]:
        # 亮框（圣髑/同调）上金名会糊，按框的明度换墨色
        lum = sum(st["frame"]["bg"]) / 3
        if lum > 180:
            d.text((x, y), name, font=f, fill=(158, 112, 36),
                   stroke_width=2, stroke_fill=(255, 250, 236))
        else:
            d.text((x, y), name, font=f, fill=(238, 206, 130),
                   stroke_width=2, stroke_fill=(64, 42, 12))
    else:
        d.text((x + 1, y + 1), name, font=f, fill=(150, 140, 124))
        d.text((x, y), name, font=f, fill=(24, 18, 12))


def kind_row(d, st, y, text, dark):
    fr = st["frame"]
    d.rectangle([62, y, W - 62, y + 42], fill=mix(fr["bg"], (0, 0, 0), 0.16),
                outline=dark, width=1)
    d.text((74, y + 10), text, font=font(F_CN, 19), fill=(30, 26, 20))


def eff_box(d, st, y, h, data, dark, paper):
    fr = st["frame"]
    d.rectangle([62, y, W - 62, y + h], fill=paper, outline=dark, width=2)
    d.rectangle([66, y + 4, W - 66, y + h - 4], outline=mix(dark, paper, 0.5), width=1)
    maxw = W - 2 * 78
    avail = h - 22
    chosen = None
    for fs_ in (18, 17, 16, 15, 14):
        f_ = font(F_CN, fs_)
        plan, hh = [], 0
        for tag, body in data["effects"]:
            if tag:
                hh += fs_ + 8
            ls = wrap_cn(d, body, f_, maxw)
            plan.append((tag, ls)); hh += len(ls) * (fs_ + 7) + 6
        if hh <= avail:
            chosen = (fs_, plan); break
    if chosen is None:
        chosen = (fs_, plan)
    fs_, plan = chosen
    fd = font(F_CN, fs_)
    tx, yy = 78, y + 12
    for tag, ls in plan:
        if tag:
            d.text((tx, yy), tag, font=fd, fill=(150, 46, 36))
            yy += fs_ + 8
        for ln in ls:
            d.text((tx, yy), ln, font=fd, fill=(26, 22, 18))
            yy += fs_ + 7
        yy += 6
    # 底部风味判词：真卡的斜体 flavor text，用来填满大文本框
    if data.get("flavor") and (y + h - 34) > yy + 12:
        fy_ = y + h - 34
        d.line([78, fy_ - 8, W - 78, fy_ - 8], fill=mix(dark, paper, 0.62), width=1)
        ff = font(F_CN, 14)
        fw = d.textlength(data["flavor"], font=ff)
        d.text(((W - fw) / 2, fy_), data["flavor"], font=ff,
               fill=mix(dark, paper, 0.42))
    return y + h


def stat_grid(d, x, y, w, stats, ink, accent, rows=3, cols=2, row_h=46):
    """营养六维：中文名 + 拉丁缩写 + 细条 + 数值（食物卡/道具卡专用）"""
    col_w = (w - 30) // cols
    f_lab, f_sub, f_val = font(F_CN, 17), font(F_LAT_CAP, 10), font(F_LAT_GEO, 17)
    for i, (cn, lat, val, unit, ratio) in enumerate(stats):
        cx = x + (i % cols) * (col_w + 30)
        cy = y + (i // cols) * row_h
        d.text((cx, cy), cn, font=f_lab, fill=ink)
        lw = d.textlength(cn, font=f_lab)
        letter(d, (cx + lw + 7, cy + 5), lat, f_sub, accent, tr=1.1)
        bx0, bx1 = cx, cx + col_w - 96
        by = cy + row_h - 18
        d.line([bx0, by, bx1, by], fill=(196, 180, 152), width=1)
        d.line([bx0, by, bx0 + max(3, (bx1 - bx0) * ratio), by], fill=accent, width=3)
        for k in range(1, 5):
            tx = bx0 + (bx1 - bx0) * k / 5
            d.line([tx, by + 4, tx, by + 7], fill=(200, 186, 160), width=1)
        # 数值与单位必须分开算宽度：原来单位固定在 cx+col_w-30，
        # 三位数时数值会压到单位上，看起来像 "337kcal" 糊在一起
        f_unit = font(F_LAT_SER, 11)
        vs = f"{val}"
        uw = d.textlength(unit, font=f_unit)
        vw = d.textlength(vs, font=f_val)
        d.text((cx + col_w - uw, cy + 17), unit, font=f_unit, fill=(120, 108, 92))
        d.text((cx + col_w - uw - vw - 6, cy + 12), vs, font=f_val, fill=ink)


def footer(d, st, y, data, dark):
    fr = st["frame"]
    d.line([62, y, W - 62, y], fill=mix(dark, fr["bg"], 0.35), width=1)
    fs = font(F_LAT_CAP, 11)
    letter(d, (62, y + 10), f"NO. {data['serial']}", fs, dark, tr=2.0)
    fcn = font(F_CN, 13)
    pv = data["provenance"]
    d.text((W - 62 - d.textlength(pv, font=fcn), y + 9), pv, font=fcn,
           fill=mix(dark, fr["bg"], 0.18))
    fsm = font(F_LAT_CAP, 9)
    ed = f"{st['edition']} · {st['foil']['lat'].upper()}"
    letter(d, (62, y + 31), ed, fsm, mix(dark, fr["bg"], 0.30), tr=1.4)
    # 验真码：占据真卡镭射标的位置 —— 别人拿订单号能复算出同一串
    if data.get("verify"):
        vc = f"V {data['verify']}"
        fv_ = font(F_LAT_CAP, 10)
        vw = tw(d, vc, fv_, 1.8)
        letter(d, (W - 62 - vw, y + 30), vc, fv_,
               (150, 46, 36) if not st["foil"]["edge"] else mix(dark, (150, 46, 36), 0.35), tr=1.8)



# ------------------------------------------------------------------ 版式

def render(plate, out, data, st=None):
    st = st or S.resolve_style("demo", 0.5)
    st["frame"] = hue_frame(st)
    if "_seed" not in st:
        st["_seed"] = str(S.h(data.get("serial", "x"), data.get("name", "y")))
    layout = st.get("layout", "monster")
    fn = {"monster": _monster, "relic": _relic, "rite": _rite, "field": _field}[layout]
    img = fn(plate, data, st)
    img = outer_edge(img, st)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=46, threshold=2))
    img.save(out, quality=96)
    print("saved", os.path.basename(out), f"[{layout}]")
    return img


def _monster(plate, data, st):
    fr, dark = st["frame"], None
    dark = mix(fr["ink"], (0, 0, 0), 0.25)
    paper = mix(fr["glow"], (255, 255, 255), 0.55)
    img = build_base(st)
    d = ImageDraw.Draw(img)

    draw_name(d, st, 48, 44, data["name"], size=42 if len(data["name"]) <= 6 else 36)
    attribute_badge(d, W - 48 - 34, 78, 34, data["attr"], data["attr_lat"])
    lv = data.get("level", 0)
    if lv:
        for i in range(lv):
            star(d, W - 74 - i * 26, 126, 12, (255, 226, 118), outline=(48, 32, 8))

    ay = 146
    aw = W - 2 * 62
    ah = int(aw * 0.72)
    paste_plate(img, st, plate, (62, ay, 62 + aw, ay + ah), data.get("crop_top", 0.05))
    d = ImageDraw.Draw(img)

    ty = ay + ah + 18
    kind_row(d, st, ty, data["kind_line"], dark)

    # 效果框高度按内容算：三大块（信条/行迹/风味）塞进固定 186 会压到判词
    footer_y = H - OUT - 92
    need = 20
    for tag, body in data["effects"]:
        if tag:
            need += 26
        need += len(wrap_cn(d, body, font(F_CN, 18), W - 2 * 78)) * 25 + 6
    if data.get("flavor"):
        need += 34
    avail = footer_y - 92 - (ty + 56)
    end = eff_box(d, st, ty + 56, max(150, min(avail, max(186, need + 22))),
                  data, dark, paper)

    # 攻 / 守（右对齐 inline）：钉在底部，避免框变高后整行上浮
    fy = footer_y - 84
    fv = font(F_LAT_GEO, 30)
    items = [("虔", "PIETAS", data["atk"]), ("守", "IEIUNIUM", data["def"])]
    widths, parts = [], []
    for cn, lat, val in items:
        wcn = d.textlength(cn, font=font(F_CN, 22))
        wlat = tw(d, lat, font(F_LAT_CAP, 15), 1.6)
        wval = d.textlength(str(val), font=fv)
        widths.append(wcn + 5 + wlat + 10 + wval)
        parts.append((cn, lat, val, wcn, wlat))
    x = (W - 62) - (sum(widths) + 56)
    for i, (cn, lat, val, wcn, wlat) in enumerate(parts):
        d.text((x, fy + 8), cn, font=font(F_CN, 22), fill=(26, 22, 18))
        letter(d, (x + wcn + 5, fy + 6), lat, font(F_LAT_CAP, 15), dark, tr=1.6)
        d.text((x + wcn + 5 + wlat + 10, fy), str(val), font=fv, fill=(26, 22, 18))
        x += widths[i] + 56

    footer(d, st, footer_y, data, dark)
    return img


def _relic(plate, data, st):
    """食物卡 / 道具卡：没有星级和攻守，营养六维是主角"""
    fr = st["frame"]
    dark = mix(fr["ink"], (0, 0, 0), 0.25)
    paper = mix(fr["glow"], (255, 255, 255), 0.55)
    img = build_base(st)
    d = ImageDraw.Draw(img)

    draw_name(d, st, 48, 44, data["name"], size=40 if len(data["name"]) <= 6 else 34)
    attribute_badge(d, W - 48 - 34, 78, 34, data["attr"], data["attr_lat"])
    # 右上角属性盘下方放"份量"，替代星级
    if data.get("weight"):
        # 这一行含汉字，必须用中文字体：Copperplate 没有汉字，会印成豆腐块
        fw_ = font(F_CN, 12)
        wtxt = data["weight"]
        d.text((W - 62 - d.textlength(wtxt, font=fw_), 116), wtxt, font=fw_,
               fill=mix(dark, fr["bg"], 0.25))

    ay = 146
    aw = W - 2 * 62
    ah = int(aw * 0.76)
    paste_plate(img, st, plate, (62, ay, 62 + aw, ay + ah), data.get("crop_top", 0.05))
    d = ImageDraw.Draw(img)

    ty = ay + ah + 16
    kind_row(d, st, ty, data["kind_line"], dark)
    need = 20
    for tag, body in data["effects"]:
        if tag:
            need += 26
        need += len(wrap_cn(d, body, font(F_CN, 18), W - 2 * 78)) * 25 + 6
    if data.get("flavor"):
        need += 34
    end = eff_box(d, st, ty + 56, max(96, min(190, need + 18)), data, dark, paper)

    footer_y = H - OUT - 108
    sy = end + 16
    row_h = max(42, (footer_y - 10 - sy) // 3)
    stat_grid(d, 74, sy, W - 2 * 74, data["stats"], (26, 22, 18), (150, 46, 36), row_h=row_h)
    footer(d, st, footer_y, data, dark)
    return img


def _rite(plate, data, st):
    """行为卡 / 事件卡：左侧一个方形徽记，没有星级没有攻守"""
    fr = st["frame"]
    dark = mix(fr["ink"], (0, 0, 0), 0.25)
    paper = mix(fr["glow"], (255, 255, 255), 0.55)
    img = build_base(st)
    d = ImageDraw.Draw(img)

    # 左上徽记（圣礼 = 十字票记；异端审判 = 倒置的叉）
    ix, iy, s = 48, 46, 30
    d.rectangle([ix, iy, ix + s, iy + s], fill=(24, 20, 16))
    d.rectangle([ix + 4, iy + 4, ix + s - 4, iy + s - 4], outline=(228, 214, 186), width=1)
    mk = data.get("mark", "cross")
    if mk == "cross":
        d.line([ix + s / 2, iy + 8, ix + s / 2, iy + s - 8], fill=(245, 238, 224), width=3)
        d.line([ix + 8, iy + s * 0.42, ix + s - 8, iy + s * 0.42], fill=(245, 238, 224), width=3)
    elif mk == "judge":
        d.line([ix + 8, iy + 8, ix + s - 8, iy + s - 8], fill=(245, 238, 224), width=3)
        d.line([ix + s - 8, iy + 8, ix + 8, iy + s - 8], fill=(245, 238, 224), width=3)
    fl = font(F_LAT_CAP, 9)
    letter(d, (ix, iy + s + 6), data.get("mark_lat", "RITE"), fl, dark, tr=1.4)

    draw_name(d, st, ix + s + 16, 44, data["name"], size=40 if len(data["name"]) <= 6 else 34)

    ay = 132
    aw = W - 2 * 62
    ah = int(aw * 0.86)
    paste_plate(img, st, plate, (62, ay, 62 + aw, ay + ah), data.get("crop_top", 0.05))
    d = ImageDraw.Draw(img)

    ty = ay + ah + 16
    kind_row(d, st, ty, data["kind_line"], dark)
    need = 24
    for tag, body in data["effects"]:
        if tag:
            need += 26
        need += len(wrap_cn(d, body, font(F_CN, 18), W - 2 * 78)) * 25 + 6
    footer_y = H - OUT - 108
    if data.get("flavor"):
        need += 34
    eh_ = max(150, min(footer_y - 42 - (ty + 56), need + 40))
    end = eff_box(d, st, ty + 56, eh_, data, dark, paper)
    footer(d, st, max(end + 26, footer_y), data, dark)
    return img


def _field(plate, data, st):
    """地点卡：横幅画面窗，下面只有一小段说明"""
    fr = st["frame"]
    dark = mix(fr["ink"], (0, 0, 0), 0.25)
    paper = mix(fr["glow"], (255, 255, 255), 0.55)
    img = build_base(st)
    d = ImageDraw.Draw(img)

    draw_name(d, st, 48, 44, data["name"], size=40 if len(data["name"]) <= 6 else 34)
    fl = font(F_LAT_CAP, 9)
    letter(d, (W - 62 - tw(d, "FIELD", fl, 1.6), 52), "FIELD", fl, dark, tr=1.6)

    ay = 132
    aw = W - 2 * 62
    ah = int(aw * 0.80)
    paste_plate(img, st, plate, (62, ay, 62 + aw, ay + ah), data.get("crop_top", 0.05))
    d = ImageDraw.Draw(img)

    ty = ay + ah + 16
    kind_row(d, st, ty, data["kind_line"], dark)
    footer_y = H - OUT - 108
    need = 24
    for tag, body in data["effects"]:
        if tag:
            need += 26
        need += len(wrap_cn(d, body, font(F_CN, 18), W - 2 * 78)) * 25 + 6
    if data.get("flavor"):
        need += 34
    end = eff_box(d, st, ty + 56,
                  max(170, min(footer_y - 42 - (ty + 56), need + 40)), data, dark, paper)
    footer(d, st, max(end + 26, footer_y), data, dark)
    return img
