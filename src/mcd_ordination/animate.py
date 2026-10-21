#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
animate.py —— 稀有卡的动态眩光

等级（由 gacha.draw() 的 anim 字段决定，不是手动指定）：
  0  静图，不出动效
  1  一道暖金扫光横过画面窗（面闪 / 金闪）
  2  扫光 + 虹彩流动 + 星点闪烁（全息）
  3  圣髑闪：扫光 + 虹彩 + 星点 + 金边呼吸

关键实现约束：**只动画面窗，不动文字。**
上一版整卡扫光把效果框文字洗白了 —— 卡再闪，字读不出来就是废卡。
所以这里先 crop 出画面窗，在窗内合成，再贴回原卡。

输出：GIF（兼容性最好）+ WebP（体积约 1/3，微信/iOS 都认）
零 AI 成本 —— 全部数学合成，不调用任何模型。
"""
import math
import os

from PIL import Image, ImageDraw, ImageChops, ImageFilter

W_OUT = 480      # 分享尺寸；原图 750x1100 直接发太重


def _sweep(w, h, center, band_w, slope=0.55):
    """一条窄的斜向软光带：逐行平移 1px 高的渐变条（整体旋转会把带子摊宽）"""
    half = band_w // 2
    g = Image.linear_gradient("L").resize((half, 1))
    strip = Image.new("L", (band_w, 1))
    strip.paste(g, (0, 0))
    strip.paste(g.transpose(Image.FLIP_LEFT_RIGHT), (half, 0))
    m = Image.new("L", (w, h), 0)
    for y in range(h):
        m.paste(strip, (int(center + y * slope) - half, y))
    return m


def _rainbow(w, h):
    img = Image.new("RGB", (64, 1))
    px = img.load()
    for x in range(64):
        px[x, 0] = (int(200 + 55 * math.sin(x / 64 * math.pi * 2)),
                    int(200 + 55 * math.sin(x / 64 * math.pi * 2 + 2.09)),
                    int(200 + 55 * math.sin(x / 64 * math.pi * 2 + 4.18)))
    return img.resize((w, h), Image.BICUBIC)


def _sparkles(w, h, n, t, level):
    lay = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(n):
        sx = 0.14 + ((i * 0.371) % 0.72)
        sy = 0.12 + ((i * 0.583) % 0.74)
        a = max(0.0, math.sin(((t / 14.0) + i * 0.31) * math.pi * 2)) ** 3
        if a < 0.08:
            continue
        r = int(3 + 6 * a)
        cx, cy, c = int(sx * w), int(sy * h), int(255 * a)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(c, c, c))
        if level >= 3:
            d.line([cx - r * 3, cy, cx + r * 3, cy], fill=(int(c * .6),) * 3, width=1)
            d.line([cx, cy - r * 3, cx, cy + r * 3], fill=(int(c * .6),) * 3, width=1)
    return lay.filter(ImageFilter.GaussianBlur(1.2))


def animate(card_path, out_dir, level=2, frames=16, fps=24,
            warm=(255, 238, 196), art_box=(0.083, 0.132, 0.917, 0.600)):
    """art_box 用归一化坐标（x0,y0,x1,y1），与渲染器里的画面窗一致"""
    base = Image.open(card_path).convert("RGB")
    W0, H0 = base.size
    x0, y0 = int(art_box[0] * W0), int(art_box[1] * H0)
    x1, y1 = int(art_box[2] * W0), int(art_box[3] * H0)
    art = base.crop((x0, y0, x1, y1))
    aw, ah = art.size

    band_w = int(aw * 0.30)
    rainbow = _rainbow(aw, ah)
    gold = Image.new("RGB", (aw, ah), warm)
    layer = gold if level == 1 else rainbow

    gold_edge = Image.new("RGB", (W0, H0), (0, 0, 0))
    ImageDraw.Draw(gold_edge).rectangle([2, 2, W0 - 3, H0 - 3],
                                        outline=(206, 164, 72), width=5)

    outs = []
    for f in range(frames):
        t = f / frames
        span = aw + band_w * 2 + int(ah * 0.55)
        center = int(-band_w + t * span)
        mask = _sweep(aw, ah, center, band_w).point(lambda v: int(v * 0.55))

        scr = ImageChops.screen(art, layer)
        art_f = Image.composite(scr, art, mask)

        if level >= 2:
            art_f = ImageChops.screen(art_f, _sparkles(aw, ah, 7, f, level))

        frame = base.copy()
        frame.paste(art_f, (x0, y0))

        if level >= 3:
            pulse = 0.30 + 0.30 * math.sin(t * math.pi * 2)
            em = gold_edge.convert("L").point(lambda v: int(v * pulse))
            frame = Image.composite(ImageChops.screen(frame, gold_edge), frame, em)

        w_out = W_OUT
        h_out = int(W_OUT * H0 / W0)
        outs.append(frame.resize((w_out, h_out), Image.LANCZOS)
                    .convert("P", palette=Image.ADAPTIVE, colors=160))

    os.makedirs(out_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(card_path))[0]
    tag = f"holo{level}"
    gif = os.path.join(out_dir, f"{name}_{tag}.gif")
    webp = os.path.join(out_dir, f"{name}_{tag}.webp")
    outs[0].save(gif, save_all=True, append_images=outs[1:],
                 duration=int(1000 / fps), loop=0, optimize=True)
    try:
        outs[0].convert("RGB").save(
            webp, save_all=True,
            append_images=[o.convert("RGB") for o in outs[1:]],
            duration=int(1000 / fps), loop=0, quality=70)
    except Exception:
        webp = None
    print("gif  ->", os.path.basename(gif), f"{os.path.getsize(gif)/1024:.0f} KB")
    if webp:
        print("webp ->", os.path.basename(webp), f"{os.path.getsize(webp)/1024:.0f} KB")
    return gif, webp


if __name__ == "__main__":
    import sys
    src = sys.argv[1]
    lv = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    animate(src, os.path.join(os.path.dirname(src), "anim"), level=lv)
