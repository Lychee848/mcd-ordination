#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canon.py —— 教义摘录引擎（设计文档 §4）

职责：把「麦当劳用户行为」里的离散条件，收敛成 0~3 条可印卡的【语录】。
设计要点（改代码前先读 design doc §4.3）：

  ① 七典归组：每个典最多出 1 条 → 阈值互斥对（如苦修士 vs 铺张派）永不共存
  ② 罕见优先：按 specificity = 1/p 排序，**不按严重度排序**（排序即评比，会踩 P2）
  ③ 零命中兜底：约 18% 用户一条都不中，必须给平信徒词条，不留空白
  ④ 截断 + 附录：cap=3，超出的进附录；实测只有 3% 用户会被截断

输出的每条都是【自陈】而非【判定】：
  - verdict  第二人称，印在卡面（给别人看的，负责有趣）
  - creed    第一人称，生成分享文案（给用户自己的，负责表达）
"""

import hashlib

# ---------------------------------------------------------------- 工具


def h(*parts) -> int:
    s = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(s.encode()).hexdigest()[:12], 16)


# ---------------------------------------------------------------- 七典定义
# test(f)：接受 features 字典，返回 True 表示命中
# p：人群中命中率【假设值，需用真实样本校准】；specificity = 1/p

def En(i, n, lat, cn, p, test, verdict, creed, dyn=None):
    """dyn(f) -> dict，返回该条目专属的插值槽位。
    必须逐条写：早期版本让所有条目共用同一个 {n}，
    结果「抽奖 {n} 次」拿到了 expiring_points，印成了「抽奖 1,200 次」。"""
    return {
        "id": i, "name": n, "lat": lat, "canon": cn, "p": p,
        "spec": 1.0 / p, "test": test, "verdict": verdict, "creed": creed,
        "dyn": dyn or (lambda f: {}),
    }

CANON_ORDER = ["tempus", "unitas", "gratia", "indulgentia",
               "peregrinatio", "mensura", "sors"]

CANON_CN = {
    "tempus": "时辰典", "unitas": "纯一典", "gratia": "恩宠典",
    "indulgentia": "赎罪典", "peregrinatio": "巡礼典",
    "mensura": "度用典", "sors": "机缘典",
}

_entries = [
    # ── 时辰典（阈值互斥：60% + 40% = 100%） ────────────────────────────
    En("nocturni", "夜祷修会", "Nocturni", "tempus", 0.12,
       lambda f: f.get("night_ratio", 0) > 0.60,
       "你在凌晨两点与麦麦独处。这不叫吃夜宵，这叫守夜。",
       "我守夜，不是为了饿，是为了那段没人打扰的安静。"),

    En("matutini", "晨祷派", "Matutini", "tempus", 0.22,
       lambda f: f.get("breakfast_ratio", 0) > 0.40,
       "你的早晨从猪柳蛋开始。这是最正统的起手式。",
       "我的一天，要先有一段仪式才肯开始。"),

    # ── 纯一典 ─────────────────────────────────────────────────────
    En("unici", "单一圣物派", "Unici", "unitas", 0.18,
       lambda f: f.get("purity", 0) > 0.80,
       "你点的不是{relic}，你点的是确定性。",
       "我不需要尝遍菜单，我需要确认它还在。",
       dyn=lambda f: {"{relic}": f.get("top_item", "本命圣物")}),

    # ── 恩宠典（阈值互斥：<20% vs >95%） ────────────────────────────
    En("prodigi", "散财异端", "Prodigi", "gratia", 0.30,
       lambda f: f.get("coupon_use_rate", 1.0) < 0.20,
       "教廷发下神恩，你拒领。你不是在省钱，你是在修行。",
       "恩宠可以不用，但不能不信。"),

    En("computatores", "神恩会计师", "Computatores", "gratia", 0.09,
       lambda f: f.get("coupon_use_rate", 0.0) > 0.95,
       "你把每一张券都用尽了。",
       "我相信秩序，一张券都不该浪费。"),

    # ── 赎罪典 ─────────────────────────────────────────────────────
    En("indulgentiarii", "赎罪券囤积犯", "Indulgentiarii", "indulgentia", 0.08,
       lambda f: f.get("expiring_points", 0) > 1000,
       "{n} 张赎罪券即将失效。教廷为你默哀三秒。",
       "我攒着的不是积分，是我以为还会去的那些日子。",
       dyn=lambda f: {"{n}": "{:,}".format(int(f.get("expiring_points", 0)))}),

    # ── 巡礼典（阈值互斥：>30 家 vs =1 家） ──────────────────────────
    En("peregrinatores", "巡回布道家", "Peregrinatores", "peregrinatio", 0.03,
       lambda f: f.get("store_count", 0) > 30,
       "你不是在吃饭，你是在巡礼。",
       "到一座城，先认它的门。"),

    En("reclusi", "本堂隐修士", "Reclusi", "peregrinatio", 0.14,
       lambda f: f.get("store_count", 0) == 1,
       "世界很大，你只认这一扇金拱门。",
       "我只认这一扇门，因为它认识我。"),

    # ── 度用典（阈值互斥：<¥15 vs >¥80；两端对称是 §4.2 安全阀） ────────
    En("ascetae", "苦修士", "Ascetae", "mensura", 0.20,
       lambda f: f.get("avg_ticket", 1e9) < 15,
       "别人来吃饭，你来修行。1+1 随心配是你的苦行衣。",
       "我不需要更多，够用本身就是一种规矩。"),

    En("profusi", "铺张派", "Profusi", "mensura", 0.04,
       lambda f: f.get("avg_ticket", 0) > 80,
       "账单写的是价格，不是信仰。",
       "我偶尔多点，但麦门不记这个。"),

    # ── 机缘典 ─────────────────────────────────────────────────────
    En("non_electi", "未被拣选者", "Non Electi", "sors", 0.05,
       lambda f: f.get("lottery_tries", 0) > 10 and f.get("lottery_wins", 1) == 0,
       "抽奖 {n} 次，神迹 0 次。不是你不虔诚，是时候未到。",
       "我信的是麦麦，不是概率。",
       dyn=lambda f: {"{n}": int(f.get("lottery_tries", 0))}),
]

# 零命中兜底：约 18% 用户会走到这里，不是防御性代码，是必走路径
FALLBACK = {
    "id": "laicus", "name": "平信徒", "lat": "Laicus", "canon": "laicus",
    "p": 1.0, "spec": 0.0, "test": lambda f: True,
    "verdict": "你的信不写在任何一件事上，它写在你从来没想起过它这件事上。",
    "creed": "我不常提起我信什么，但我从来没否认过。",
}

CANON = {c: [e for e in _entries if e["canon"] == c] for c in CANON_ORDER}


# ---------------------------------------------------------------- 插值

def _render(tpl: str, f: dict, e: dict) -> str:
    """只用该条目自己的 dyn 槽位做插值，绝不跨条目取值"""
    out = tpl
    for k, v in e["dyn"](f).items():
        out = out.replace(k, str(v))
    return out


# ---------------------------------------------------------------- 裁决

def faith_extract(features: dict, uid: str, cap: int = 3) -> dict:
    """四步裁决：典内互斥 -> 罕见优先 -> 零命中兜底 -> 截断 + 附录"""
    hits = []
    for c in CANON_ORDER:                                   # ① 典内只留 1 条
        cands = [e for e in CANON[c] if e["test"](features)]
        if not cands:
            continue
        cands.sort(key=lambda e: (-e["spec"], h(uid, e["id"])))
        hits.append(cands[0])

    hits.sort(key=lambda e: (-e["spec"], h(uid, e["id"])))   # ② 罕见优先

    if not hits:                                            # ③ 兜底
        hits = [FALLBACK]

    printed, appendix = hits[:cap], hits[cap:]              # ④ 截断
    for e in printed + appendix:
        e = dict(e)
    return {
        "printed": printed,
        "appendix": appendix,
        "total": len(hits) if hits[0] is not FALLBACK else 0,
    }


# ---------------------------------------------------------------- 输出

def card_block(res: dict, f: dict) -> list:
    """印在教籍卡底部的「教义摘录」栏，每行一条"""
    lines = [f"【{e['name']}】 {_render(e['verdict'], f, e)}" for e in res["printed"]]
    if res["appendix"]:
        lines.append(f"—— 另有 {len(res['appendix'])} 条，见附录 ——")
    return lines


def share_text(res: dict, f: dict) -> str:
    """发帖/对暗号用的第一人称文案"""
    body = "\n".join("· " + _render(e["creed"], f, e) for e in res["printed"])
    return f"我的麦门，我的教义：\n{body}"


# ---------------------------------------------------------------- 自检

if __name__ == "__main__":
    f = {
        "night_ratio": 0.68, "purity": 0.84, "coupon_use_rate": 0.08,
        "store_count": 2, "expiring_points": 1200,
        "lottery_tries": 14, "lottery_wins": 0,
        "breakfast_ratio": 0.10, "avg_ticket": 22.0,
        "top_item": "麦辣鸡腿堡",
    }
    r = faith_extract(f, "u_00029")

    print("逐典匹配：")
    for c in CANON_ORDER:
        got = [e["name"] for e in CANON[c] if e["test"](f)]
        print(f"  {CANON_CN[c]:6s} -> {got or '—'}")

    print("\n按罕见度排序后：")
    all_hits = [(e["name"], round(e["spec"], 2)) for e in r["printed"] + r["appendix"]]
    for n, s in all_hits:
        print(f"  {n:12s} {s}")

    print("\n卡面「教义摘录」栏：")
    for ln in card_block(r, f):
        print("  " + ln)

    print("\n分享文案：")
    print(share_text(r, f))

    # 互斥对不共存的结构性校验
    pairs = [("ascetae", "profusi"), ("prodigi", "computatores"),
             ("reclusi", "peregrinatores"), ("nocturni", "matutini")]
    print("\n互斥对检查（最后一列为 True 仅表示该输入向量本身不合法）：")
    for a, b in pairs:
        ea = next(e for e in _entries if e["id"] == a)
        eb = next(e for e in _entries if e["id"] == b)
        both = any(ea["test"](f2) and eb["test"](f2)
                   for f2 in [dict(f, **k) for k in [
                       {"avg_ticket": 5}, {"avg_ticket": 200},
                       {"coupon_use_rate": 0.1}, {"coupon_use_rate": 1.0},
                       {"store_count": 1}, {"store_count": 99},
                       {"night_ratio": .9, "breakfast_ratio": .9},
                   ]])
        ok = ea["canon"] == eb["canon"]
        print(f"  {ea['name']:6s} vs {eb['name']:8s} 同典保护={ok}  极端输入下并存={both}")
