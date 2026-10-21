#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cli.py —— 三个子命令：demo / sign / doctor"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import canon as C
from . import deck as D
from . import features as F
from . import order as O
from . import piety as P
from . import sign as SG

REPO = Path(__file__).resolve().parent.parent.parent


def _menu_names() -> list:
    nut = D.load_nutrition()
    return [v["name"] for k, v in nut.items() if not k.startswith("_")]


def _pipeline(profile: str):
    payload = F.load_mock(profile)
    feats = F.build(payload)
    uid = payload.get("uid") or profile
    co = F.load_cohort()
    pi = P.piety(feats, co)
    cr = C.faith_extract(feats, uid)
    return payload, feats, uid, pi, cr


def cmd_demo(args) -> int:
    payload, feats, uid, pi, cr = _pipeline(args.profile)
    cards = D.build_deck(feats, cr, pi, payload["orders"], D.load_nutrition(), uid=uid)

    today = date.today()
    top = cr["printed"][0]
    sg = SG.compile_sign(feats, uid, today, _menu_names(),
                         grace_id=top["id"], grace_creed=top["creed"],
                         kind=getattr(args, "kind", "auto"),
                         allow_t1=getattr(args, "allow_t1", False),
                         story=SG.load_story(uid))

    out = Path(args.out) / args.profile
    out.mkdir(parents=True, exist_ok=True)

    print(f"\n人设 {args.profile} · {feats['home_city']} · {feats['home_store']}")
    print(f"  {P.explain(pi)}")
    caveat = "  ← n<200，百分位含先验成分，仅供参考" if pi["n"] < 200 else ""
    print(f"  样本 n={pi['n']}{caveat}\n")

    made = []
    for c in cards:
        st, data = c["style"], c["data"]
        role = c["role"]
        svg_path = out / f"card_{role}.svg"
        st.setdefault("_seed", str(abs(hash((uid, role))) % 10 ** 9))
        SVG_RENDER(data, st, str(svg_path))
        made.append((role, "svg", svg_path, st, c))

        if args.engine in ("png", "both"):
            try:
                png_path = _render_png(out, uid, c, data, st)
                made.append((role, "png", png_path, st, c))
            except ImportError:
                print("  ! 没装 Pillow，跳过 PNG（L0 已生成，不影响可用）")

    print("  卡面：")
    for role, kind, path, st, c in made:
        if kind == "svg":
            print(f"    {role:6s} {st['frame']['cn']:5s} {st['foil']['cn']:4s} "
                  f"{st['art']['cn']:6s} -> {path.relative_to(REPO) if str(path).startswith(str(REPO)) else path}")

    print(f"\n  ── 暗号 · 备注版（体裁：{sg['kind_cn']}"
          + (f" · 第 {sg['story_chapter']} 章" if sg["kind"] == "story" else "")
          + (f" · {sg['ask_tier']}" if sg["kind"] == "ask" else "")
          + "）──")
    print(f"    {sg['short']}")
    print(f"    长度 {sg['len']} / 上限 {SG.REMARK_LIMIT}｜短码 {sg['code']}｜{sg['expires']}")
    print("\n  ── 暗号（社交版）──")
    for ln in sg["long"].split("\n"):
        print(f"    {ln}")

    (out / "sign.json").write_text(json.dumps(sg, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "features.json").write_text(json.dumps(feats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  产物目录：{out}\n")
    return 0


def _render_png(out: Path, uid: str, card: dict, data: dict, st: dict) -> Path:
    from . import plates, render_png

    art_key = next((k for k, v in _art_items() if v is st["art"]), "stained")
    asset = _pick_plate(art_key, card["role"])
    if asset:
        plate = str(asset)
    else:
        plate_dir = out / "_plates"
        plate_dir.mkdir(exist_ok=True)
        plate_path = plate_dir / f"proc_{art_key}_{card['role']}.png"
        plates.procedural_plate(st, card["role"]).save(plate_path, quality=92)
        plate = str(plate_path)

    dst = out / f"card_{card['role']}.png"
    render_png.render(plate, str(dst), dict(data), st)
    return dst


# 同一画派，不同卡种可以配不同主体：人物卡要有人，食物/行为卡要有一眼认得的物
_PLATE_ALIAS = {"item": "still", "spell": "still"}


def _pick_plate(art_key: str, role: str):
    """按 > 具体到角色 > 同画派泛指 > 无 的顺序找底图；都没有就交给程序化底图"""
    names = [f"plate_{art_key}_{role}.png"]
    if role in _PLATE_ALIAS:
        names.append(f"plate_{art_key}_{_PLATE_ALIAS[role]}.png")
    names.append(f"plate_{art_key}.png")
    for n in names:
        p = REPO / "assets" / "plates" / n
        if p.exists():
            return p
    return None


def _art_items():
    from . import styles as S
    return list(S.ART_SCHOOLS.items())


def SVG_RENDER(data, st, out):
    from . import render_svg
    return render_svg.render(data, st, out)


def _sign(profile: str, kind: str = "auto", allow_t1: bool = False):
    payload, feats, uid, pi, cr = _pipeline(profile)
    top = cr["printed"][0]
    sg = SG.compile_sign(feats, uid, date.today(), _menu_names(),
                         grace_id=top["id"], grace_creed=top["creed"],
                         kind=kind, allow_t1=allow_t1,
                         story=SG.load_story(uid))
    return payload, feats, uid, pi, sg


def cmd_sign(args) -> int:
    payload, feats, uid, pi, sg = _sign(args.profile, args.kind, args.allow_t1)

    print(f"\n{pi['rank']['cn']}（{pi['rank']['lat']}）")
    print(f"体裁：{sg['kind_cn']}（{SG.KINDS[sg['kind']]['desc']}）"
          + (f" · 第 {sg['story_chapter']} 章" if sg["kind"] == "story" else "")
          + (f" · 请求档位 {sg['ask_tier']}" if sg["kind"] == "ask" else ""))
    print("\n备注版（一键复制，可挂到订单备注）：\n  " + sg["short"])
    print(f"\n社交版：\n{sg['long']}")
    print(f"\n短码 {sg['code']}｜公开复算一致 = "
          f"{SG.verify_code(sg['claims']) == sg['code']}｜{sg['expires']}")

    if args.wrote:
        led = SG.append_story(uid, sg, args.wrote)
        print(f"\n已记入本地接龙账本（第 {led['chapter']} 章）。"
              f"下次运行会自动接上：「{led['last']}」")
    return 0


def cmd_order(args) -> int:
    payload, feats, uid, pi, sg = _sign(args.profile, args.kind, args.allow_t1)
    draft = O.build_draft(payload["orders"], feats)

    tools = []
    if args.tools:
        tools = json.loads(Path(args.tools).read_text(encoding="utf-8"))
    caps = O.probe(tools) if tools else {"field": None, "max_len": None, "checked": False}

    res = O.attach(draft, sg, caps)
    print(f"\n订单草稿：{draft['storeName']} · {len(draft['items'])} 件商品"
          f"（复用 {draft['_sourceOrder']}）")
    print(O.render(res))
    if args.json:
        print("\n" + json.dumps(res, ensure_ascii=False, indent=2))
    return 0


def cmd_doctor(args) -> int:
    from . import fonts
    print("\n字体：")
    for k, v in fonts.report().items():
        print(f"  {k:8s} {v}")
    try:
        import PIL
        print(f"\nPillow {PIL.__version__}（PNG / GIF 可用）")
    except ImportError:
        print("\nPillow 未安装：只出 L0 SVG（这仍然是一张完整可看的卡）")
    people = sorted(p.stem for p in F.MOCK_DIR.glob("*.json") if p.stem != "cohort")
    print("\n可用人设：" + ", ".join(people))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mcd-ordination",
                                 description="把麦当劳用户行为编译成一套麦门卡证")
    sub = ap.add_subparsers(dest="cmd")

    d = sub.add_parser("demo", help="跑一份人设，出全套卡 + 暗号")
    d.add_argument("--profile", default="night_owl")
    d.add_argument("--out", default="out")
    d.add_argument("--engine", choices=["svg", "png", "both"], default="both")
    d.add_argument("--kind", default="auto",
                   choices=["auto", "greet", "ask", "story"])
    d.add_argument("--allow-t1", action="store_true")
    d.set_defaults(func=cmd_demo)

    s = sub.add_parser("sign", help="只出暗号（三种体裁）")
    s.add_argument("--profile", default="night_owl")
    s.add_argument("--kind", default="auto",
                   choices=["auto", "greet", "ask", "story"],
                   help="greet 问候 / ask 请求 / story 接龙 / auto 按行为选")
    s.add_argument("--allow-t1", action="store_true",
                   help="允许问一句能不能多给一点（仍带「若不方便」）")
    s.add_argument("--wrote", default="",
                   help="店员在袋上写回来的那半句，记进本地账本供下次接龙")
    s.set_defaults(func=cmd_sign)

    o = sub.add_parser("order", help="把暗号挂到订单备注（能力探测 + 降级）")
    o.add_argument("--profile", default="night_owl")
    o.add_argument("--kind", default="auto",
                   choices=["auto", "greet", "ask", "story"])
    o.add_argument("--allow-t1", action="store_true")
    o.add_argument("--tools", default="",
                   help="tools/list 的 JSON 文件；给了就据此探测 create-order 是否有备注字段")
    o.add_argument("--json", action="store_true", help="同时打印完整 payload")
    o.set_defaults(func=cmd_order)

    doc = sub.add_parser("doctor", help="检查字体与依赖")
    doc.set_defaults(func=cmd_doctor)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
