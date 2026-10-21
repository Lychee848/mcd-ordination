#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_assets.py —— 生成 README 里的样张（拼版 + 稀有卡动效）

跑法：
    python scripts/make_assets.py

产物：
    docs/samples/four_layouts.png    四种版式并排（人物/食物/行为/地点）
    docs/samples/three_personas.png  三个人设的人物卡并排（证明"每人不一样"）
    docs/samples/holo_demo.gif       扫光动效示意（< 1MB，微信里不会被压坏）
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
DOCS = ROOT / "docs" / "samples"
PY = sys.executable

sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from mcd_ordination import animate as A  # noqa: E402
from mcd_ordination import canon as C, deck as D, features as F, fonts, piety as P  # noqa: E402

ROLE_RANK = {"effect": 0, "item": 1, "spell": 2, "field": 3}
ART_BOX = {"effect": (0.083, 0.132, 0.917, 0.600),
           "item": (0.083, 0.132, 0.917, 0.568),
           "spell": (0.083, 0.120, 0.917, 0.520),
           "field": (0.083, 0.120, 0.917, 0.560)}


def run(profile: str):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    subprocess.run([PY, "-m", "mcd_ordination", "demo", "--profile", profile,
                    "--engine", "both"], cwd=ROOT, env=env, check=True,
                   stdout=subprocess.DEVNULL)


def sheet(paths, labels, out, tw=340, pad=26, cap=52):
    th = int(tw * 1100 / 750)
    img = Image.new("RGB", (pad + (tw + pad) * len(paths), th + cap + pad * 2),
                    (246, 243, 237))
    d = ImageDraw.Draw(img)
    fp = fonts.resolve("cjk")
    f = ImageFont.truetype(fp, 18) if fp else ImageFont.load_default()
    for i, (p, lab) in enumerate(zip(paths, labels)):
        im = Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS)
        x = pad + i * (tw + pad)
        img.paste(im, (x, pad))
        w = d.textlength(lab, font=f)
        d.text((x + (tw - w) / 2, pad + th + 16), lab, font=f, fill=(60, 52, 44))
    img.save(out, quality=95)
    print("sheet ->", out.relative_to(ROOT))


def best_rare():
    """在三个人设里找一张真的抽到稀有卡的，返回 (路径, 档位, 版式)"""
    best, level, role = None, 0, "effect"
    for p in ("night_owl", "pilgrim", "beginner"):
        payload = F.load_mock(p)
        feats = F.build(payload)
        pi = P.piety(feats, F.load_cohort())
        cr = C.faith_extract(feats, payload["uid"])
        for c in D.build_deck(feats, cr, pi, payload["orders"], D.load_nutrition(),
                              uid=payload["uid"]):
            if (c["anim"], -ROLE_RANK[c["role"]]) > (level, -ROLE_RANK[role]):
                level, role = c["anim"], c["role"]
                best = OUT / p / f"card_{c['role']}.png"
    return best, level, role


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    for p in ("night_owl", "pilgrim", "beginner"):
        run(p)

    n = OUT / "night_owl"
    sheet([n / "card_effect.png", n / "card_item.png",
           n / "card_spell.png", n / "card_field.png"],
          ["人物卡 · monster", "食物卡 · relic", "行为卡 · rite", "地点卡 · field"],
          DOCS / "four_layouts.png")

    sheet([OUT / p / "card_effect.png" for p in ("night_owl", "pilgrim", "beginner")],
          ["夜祷老客 · 深圳", "跨城巡礼者 · 成都", "初闻道者 · 哈尔滨"],
          DOCS / "three_personas.png")

    shutil.copy(OUT / "pilgrim" / "card_effect.png", DOCS / "card_pilgrim.png")
    shutil.copy(OUT / "night_owl" / "card_item.png", DOCS / "card_item.png")

    # 动效：优先用真的抽到稀有卡的那张；都没有就用一张人物卡做档位 3 的示意
    path, level, role = best_rare()
    if level >= 2:
        note = f"真实抽取 · 档位 {level}"
    else:
        path, level, role = n / "card_effect.png", 3, "effect"
        note = "动效示意 · 档位 3"

    gif = None
    for frames in (16, 12, 9):
        gif = A.animate(str(path), str(DOCS), level=level, frames=frames,
                        art_box=ART_BOX[role])[0]
        if Path(gif).stat().st_size < 1_000_000:
            break

    final = DOCS / "holo_demo.gif"
    shutil.move(gif, final)
    webp = Path(gif).with_suffix(".webp")
    if webp.exists():
        shutil.move(str(webp), str(DOCS / "holo_demo.webp"))
    print(f"holo  -> {final.name}（{final.stat().st_size // 1024} KB，{note}）")


if __name__ == "__main__":
    main()
