#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_demo_site.py —— 生成参赛落地页 index.html（含离线交互 Demo）

做法：跑三份人设的 demo，把 SVG/PNG 复制进 docs/demo/，把三个人设 × 四种卡 ×
三种体裁的数据内联进 index.html。这样双击 index.html 也能用（不走 fetch，免 CORS）。

跑法：python scripts/gen_demo_site.py
产物：index.html（仓库根，GitHub Pages 选 root 即可）
"""
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "demo"
PY = sys.executable

sys.path.insert(0, str(ROOT / "src"))

from PIL import Image  # noqa: E402

from mcd_ordination import canon as C, deck as D, features as F, piety as P, sign as SG  # noqa: E402

PERSONAS = [
    ("night_owl", "夜祷老客", "深圳"),
    ("pilgrim", "跨城巡礼者", "成都"),
    ("beginner", "初闻道者", "哈尔滨"),
]
ROLES = [("effect", "人物卡"), ("item", "食物卡"), ("spell", "行为卡"), ("field", "地点卡")]
GENRES = ["greet", "ask", "story"]


def run(profile: str):
    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["MCD_STORY_DIR"] = str(ROOT / "out" / "_story")
    subprocess.run([PY, "-m", "mcd_ordination", "demo", "--profile", profile,
                    "--engine", "both"], cwd=ROOT, env=env, check=True,
                   stdout=subprocess.DEVNULL)


def signs_for(profile: str) -> dict:
    payload = F.load_mock(profile)
    feats = F.build(payload)
    uid = payload["uid"]
    cr = C.faith_extract(feats, uid)
    top = cr["printed"][0]
    menu = [v["name"] for k, v in D.load_nutrition().items() if not k.startswith("_")]
    out = {}
    for g in GENRES:
        s = SG.compile_sign(feats, uid, date.today(), menu,
                            grace_id=top["id"], grace_creed=top["creed"], kind=g)
        out[g] = {"short": s["short"], "long": s["long"],
                  "label": s["kind_cn"], "code": s["code"],
                  "note": (f"第 {s['story_chapter']} 章 · 待续" if g == "story"
                           else (f"{s['ask_tier']} · 求圣物" if g == "ask"
                                 else "不求任何东西"))}
    return out


def main():
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)

    data = []
    for profile, label, city in PERSONAS:
        run(profile)
        src = ROOT / "out" / profile
        dst = DOCS / profile
        dst.mkdir(parents=True)
        for role, _cn in ROLES:
            shutil.copy(src / f"card_{role}.svg", dst / f"{role}.svg")
            # 页面展示用缩到 620 宽的 PNG（成品卡），体积每张 ~150KB
            im = Image.open(src / f"card_{role}.png").convert("RGB")
            w, h = im.size
            # 卡面没有透明通道，用 JPEG：同样清晰，体积是 PNG 的 1/5
            im.resize((620, int(620 * h / w)), Image.LANCZOS).save(
                dst / f"{role}.jpg", quality=88, optimize=True)

        feats = F.build(F.load_mock(profile))
        pi = P.piety(feats, F.load_cohort())
        data.append({
            "id": profile, "label": label, "city": city,
            "rank": pi["rank"]["cn"], "rank_lat": pi["rank"]["lat"],
            "halo": pi["rank"]["halo"],
            "cards": {r: f"docs/demo/{profile}/{r}.jpg" for r, _ in ROLES},
            "signs": signs_for(profile),
            "facts": {"orders": feats["total_orders"], "stores": feats["store_count"],
                      "cities": feats["cross_city"], "purity": round(feats["purity"] * 100)},
        })

    tpl = (ROOT / "scripts" / "site_template.html").read_text(encoding="utf-8")
    repo = __import__("os").environ.get("REPO_URL", "https://github.com/Lychee848/mcd-ordination")
    html = (tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
               .replace("__REPO__", repo))
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print("wrote index.html  |  personas:", len(data),
          "| demo assets:", sum(1 for _ in DOCS.rglob("*") if _.is_file()))


if __name__ == "__main__":
    main()
