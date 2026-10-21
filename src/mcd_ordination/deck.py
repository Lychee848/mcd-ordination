#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deck.py —— 把特征向量编译成一套卡（四种版式）

分工：
  features.py  原始行为 → 扁平特征
  canon.py     特征 → 教义摘录（0~3 条信条）
  piety.py     特征 → 九阶品秩
  gacha.py     单笔订单 → 稀有度（rank）
  deck.py      以上四者 → 可直接渲染的 data 字典（本文件）
  render_*.py  data → 卡面

一条不能破的线：**AI 只画画面，文字/数值/星级/编号一律代码画。**
所以这里产出的每个数字都必须能在 features / nutrition 里找到出处。
"""
from __future__ import annotations

import json
from datetime import datetime

from . import canon as CANON
from . import gacha as G
from . import piety as P
from . import styles as S

ATTRS = [
    (22, 23, "夜", "NOCT"),
    (0, 5, "夜", "NOCT"),
    (6, 9, "晨", "LUMEN"),
    (10, 13, "午", "MERIDIES"),
    (14, 17, "申", "HORA"),
    (18, 21, "暮", "VESPER"),
]

STAT_SIX = [
    ("圣光", "ENERGY", "energy_kcal", "kcal"),
    ("圣肉", "PROTEIN", "protein_g", "g"),
    ("圣膏", "FAT", "fat_g", "g"),
    ("圣粮", "CARB", "carb_g", "g"),
    ("圣血", "SODIUM", "sodium_mg", "mg"),
    ("圣骨", "CALCIUM", "calcium_mg", "mg"),
]


def _bucket(hour: int) -> str:
    for lo, hi, cn, _lat in ATTRS:
        if lo <= hour <= hi:
            return cn
    return "午"


def dominant_hour(orders: list) -> tuple[int, dict]:
    """属性必须取「最常出现的时辰」，而不是最后一单的时辰。
    否则会出现「午祷的第 6791 号」配一张深夜街景——卡面自己打自己。"""
    from collections import Counter
    cnt = Counter()
    for o in orders[-200:]:
        h = datetime.fromisoformat(o["placedAt"].replace("Z", "+00:00")).hour
        cnt[_bucket(h)] += 1
    want = cnt.most_common(1)[0][0] if cnt else "午"
    rep = next((o for o in reversed(orders)
                if _bucket(datetime.fromisoformat(
                    o["placedAt"].replace("Z", "+00:00")).hour) == want), orders[-1])
    hour = datetime.fromisoformat(rep["placedAt"].replace("Z", "+00:00")).hour
    return hour, rep


def attr_of(hour: int) -> tuple[str, str]:
    for lo, hi, cn, lat in ATTRS:
        if lo <= hour <= hi:
            return cn, lat
    return "午", "MERIDIES"


def serial_of(order_id: str) -> str:
    return f"{S.h(order_id) % 9999:04d}"


def _prov(order: dict) -> str:
    at = datetime.fromisoformat(order["placedAt"].replace("Z", "+00:00"))
    city = order.get("city") or "深圳"
    return f"{at:%Y-%m-%d %H:%M} · {city} · #{serial_of(order['orderId'])}"


def load_nutrition() -> dict:
    from .features import DATA_DIR
    return json.loads((DATA_DIR / "nutrition.json").read_text(encoding="utf-8"))


def _stats_for(sku: str, nutrition: dict) -> list:
    n = nutrition.get(sku) or {}
    rdi = nutrition.get("_rdi", {})
    out = []
    for cn, lat, key, unit in STAT_SIX:
        v = n.get(key, 0)
        ref = rdi.get(key, max(v, 1)) or 1
        out.append((cn, lat, round(v) if float(v).is_integer() else v,
                    unit, round(min(1.0, v / ref), 3)))
    return out


def build_deck(features: dict, canon_res: dict, piety_res: dict,
               orders: list, nutrition: dict, *, uid: str,
               season: int = 0) -> list:
    """
    返回 [{role, layout, rank, anim, data, style}, ...]
    role 决定卡框与版式：effect（人物）/ item（食物）/ spell（行为）/ field（地点）
    """
    deck = []
    last = orders[-1]
    # 代表单：主导时辰里最近的那一单。名字、属性、溯源、编号全部跟着它走
    hour, rep = dominant_hour(orders)
    attr, attr_lat = attr_of(hour)
    rank = piety_res["rank"]
    serial = serial_of(rep["orderId"])

    digest = str(S.h(uid, "deck-v1", season))

    # ---- ① 人物卡：信息重心是"这个人有多强"（星级 + 攻守）
    g1 = G.draw(rep["orderId"], uid, _flags(rep, orders), piety_pct=piety_res["pct"])
    atk = 1200 + rank["level"] * 280 + int(features["purity"] * 400)
    dfn = 900 + rank["level"] * 160 + features["store_count"] * 12
    eff = []
    for i, e in enumerate(canon_res["printed"][:2]):
        # 必须走 _render（逐条 dyn 插值）：直接印 verdict 会把 {n} 原样印上卡面
        eff.append(("【信条】" if i == 0 else "", CANON._render(e["verdict"], features, e)))
    if not eff:
        eff.append(("【信条】", CANON.FALLBACK["verdict"]))
    # 行迹：全部是真实数字，用来填满效果框，也让"这一卷"可对账
    eff.append(("【行迹】",
                f"跨 {features['cross_city']} 座城 · 走过 {features['store_count']} 家门店 · "
                f"入门第 {max(1, int(features['years_since_first']))} 年"))
    deck.append({
        "role": "effect", "layout": "monster", "rank": g1["rank"],
        "anim": g1["anim"],
        "data": {
            "name": f"{attr}祷的第 {serial} 号", "attr": attr, "attr_lat": attr_lat,
            "level": rank["level"],
            "kind_line": f"【侍者族／{rank['cn']}／{attr}祷】",
            "effects": eff,
            "atk": atk, "def": dfn, "serial": f"MM.{serial}",
            "provenance": _prov(rep),
            "verify": g1["verify"],
            "flavor": "「" + _flavor(features, rank) + "」",
        },
    })

    # ---- ② 食物卡：信息重心是"这份东西是什么"（营养六维，一克不编）
    g2 = G.draw(last["orderId"] + ":item", uid, _flags(last, orders),
                piety_pct=piety_res["pct"])
    sku = features["top_sku"]
    name = nutrition.get(sku, {}).get("name", features["top_item"])
    deck.append({
        "role": "item", "layout": "relic", "rank": g2["rank"],
        "anim": g2["anim"],
        "data": {
            "name": f"圣髑·{name}", "attr": "粮", "attr_lat": "FRUMENTUM",
            "weight": "1 份 · 按订单原文",
            "kind_line": "【圣髑／主食／可装备】",
            "effects": [("【装备】", f"装备此卡的圣徒攻击力上升 {int(features['purity'] * 300)}，"
                                    "且在夜间不会被「饥饿」破坏。")],
            "stats": _stats_for(sku, nutrition),
            "serial": f"MM.{serial_of(last['orderId'] + 'i')}",
            "provenance": _prov(last),
            "verify": g2["verify"],
            "flavor": f"「今岁 {features['total_orders']} 次礼拜里，它出现了 "
                      f"{int(features['purity'] * 100)}%。」",
        },
    })

    # ---- ③ 行为卡：信息重心是"什么时候能做一次什么"（无攻守无星级）
    g3 = G.draw(last["orderId"] + ":rite", uid, _flags(last, orders),
                piety_pct=piety_res["pct"])
    top = canon_res["printed"][0] if canon_res["printed"] else CANON.FALLBACK
    deck.append({
        "role": "spell", "layout": "rite", "rank": g3["rank"],
        "anim": g3["anim"],
        "data": {
            "name": top["name"], "attr": "光", "attr_lat": "LUMEN",
            "mark": "cross", "mark_lat": "RITE",
            "kind_line": f"【圣礼／{CANON.CANON_CN.get(top.get('canon'), '日课')}／一次性】",
            "effects": [("【效果】", CANON._render(top["verdict"], features, top)),
                        ("", top["creed"])],
            "serial": f"MM.{serial_of(last['orderId'] + 'r')}",
            "provenance": _prov(last),
            "verify": g3["verify"],
            "flavor": "「记下来，下一次才好认。」",
        },
    })

    # ---- ④ 地点卡：信息重心是"这个地方长什么样"（横幅画面窗）
    g4 = G.draw(last["orderId"] + ":field", uid, _flags(last, orders),
                piety_pct=piety_res["pct"])
    deck.append({
        "role": "field", "layout": "field", "rank": g4["rank"],
        "anim": g4["anim"],
        "data": {
            "name": features["home_store"] or "本堂", "attr": "地", "attr_lat": "LOCUS",
            "kind_line": f"【圣地／{features['home_city'] or '本城'}／常驻】",
            "effects": [("【场地效果】",
                         f"此店为你去过 {features['store_count']} 家门店中的常驻本堂；"
                         f"在此地发动的「礼拜」不会被「加班」无效化。")],
            "serial": f"MM.{serial_of(last['orderId'] + 'f')}",
            "provenance": _prov(last),
            "verify": g4["verify"],
        },
    })

    for c in deck:
        c["style"] = S.full_style(digest, c["rank"], c["role"], season)
        # 若该角色有专属 plate 就用，没有就走 L0 程序化底图
        c["style"]["_seed"] = str(S.h(uid, c["role"], season))
    return deck


def _flags(order: dict, orders: list) -> dict:
    from .features import order_flags
    return order_flags(order, orders)


def _flavor(f: dict, rank: dict) -> str:
    if f["night_ratio"] >= 0.45:
        return "灯还亮着，人就还有地方去。"
    if f["cross_city"] >= 3:
        return "换一座城，先找同一扇门。"
    if f["purity"] >= 0.7:
        return "不是不想换，是换了就不是这件事了。"
    if rank["level"] <= 3:
        return "才刚开始，不急。"
    return "日子是这样一天一天叠起来的。"
