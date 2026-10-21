#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sign.py —— 麦门暗号引擎（设计文档 §5）

回答一个问题：**为什么每个人的暗号不一样，而且改不了。**

旧设计（v3.0 及之前）是一句固定模板，只替换【本命圣物】和【礼拜次数】两个空：

    我是麦门信徒，本命圣物是【麦辣鸡腿堡】，
    今日已礼拜 47 次。若你也是门内人，
    可否在袋中多放一根脆脆薯？麦门永生。🍟

骨架 100% 相同 —— 一万人发出来是一万句同一句话，传播价值接近 0。
本模块把它改造成和生图提示词同构的「槽位编译器」：

    暗号 = 共同层（当天全网一致） + 个人层（你的行为向量） + 会话层（周期种子）

三条铁律（改代码前先读 design doc §5.1）：
  ① 每一个槽位都必须能追溯到一条真实行为，不得为了押韵编数据（P1）
  ② 请求档位默认是【零成本】的象征性动作，绝不给一线门店添负担（§5.4）
  ③ 短码必须【公开可复算】：拿你卡面上的数字按公布的顺序拼起来就能算出来（P1）
"""

import hashlib
from datetime import date

# 备注栏字数上限。**⚠ 待实测**：官方 App 备注栏的实际上限还没验证过。
# 60 是占位值；实测后只改这一个常量，装配阶梯（LADDER）会自动适配。
REMARK_LIMIT = 60

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # Crockford base32，去掉 I L O U


def h(*parts) -> int:
    s = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(s.encode()).hexdigest()[:12], 16)


def b32(n: int, k: int = 6) -> str:
    out = []
    for _ in range(k):
        out.append(ALPHABET[n % 32])
        n //= 32
    return "".join(reversed(out))


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}W{w:02d}"


# ---------------------------------------------------------------- 槽位池

# S1 自陈：由「主导行为轴」决定。注意这里是自述，不是被判定。
VOCATION = {
    "noct": ["我常在打烊之后受召", "我的礼拜多在人静之后", "我在夜里认这个名字"],
    "matut": ["我的一天从热香饼开始", "天刚亮我就到了门口", "我的早晨要先受召才肯开始"],
    "cross": ["我在 {city} 座城唤过这个名字",
              "我跨过 {city} 座城，只为同一扇门"],
    "one": ["我只认这一扇金拱门", "我的全部礼拜都在同一扇门下"],
    "unitas": ["我几乎不曾换过我的圣物", "我把同一件事重复成规矩"],
    "returned": ["我已 {days} 天未曾回来", "我离开过 {days} 天，如今回来了"],
    "novice": ["我刚走到门口不久", "我入门尚浅，但我确实在"],
}

# S3 行迹：每一条都带一个真实数字。cond 决定能不能用，spec 决定优先级。
DEEDS = [
    ("cities", lambda f: f.get("cross_city", 0) >= 2, 4.0,
     "跨 {n} 座城", lambda f: f["cross_city"]),
    ("years", lambda f: f.get("years_since_first", 0) >= 2, 3.0,
     "入门第 {n} 年", lambda f: int(f["years_since_first"])),
    ("stores", lambda f: f.get("store_count", 0) >= 5, 2.0,
     "走过 {n} 家门店", lambda f: f["store_count"]),
    ("returned", lambda f: f.get("days_since_last", 0) >= 30, 5.0,
     "久别 {n} 天", lambda f: f["days_since_last"]),
    ("night", lambda f: f.get("night_ratio", 0) >= 0.30, 1.2,
     "夜祷占 {n}", lambda f: f"{int(f['night_ratio'] * 100)}%"),
    ("purity", lambda f: f.get("purity", 0) >= 0.50, 1.1,
     "专一 {n}", lambda f: f"{int(f['purity'] * 100)}%"),
    ("orders", lambda f: f.get("total_orders", 0) >= 1, 0.5,
     "礼拜 {n} 次", lambda f: f["total_orders"]),
]

# S5 请求：T0 零成本是默认，T1 只在特定条件下解锁。
PETITIONS_T0 = [
    "可否在袋上画道拱门",
    "可否对我说句麦门",
    "可否把小票折个十字",
    "可否在袋上写个麦字",
    "可否在杯盖点一下",
    "可否与我同念一声麦门",
]
PETITIONS_T1 = [
    "若方便，可否多一根脆脆薯",
    "若方便，可否多一包甜酸酱",
    "若方便，可否把薯条装满一点",
]

# S6 应答：把单向索要改成双向互动 —— 这是门店愿意配合的前提
RESPONSES = [
    "你若回我一句「麦门」，我今日的礼拜便算圆满。",
    "你若画一道拱门，我会把它当作今日的神迹。",
    "你若只笑一下，也算你与我同门。",
    "你若摇头不知，也无妨，我明日还来。",
]

# S8 圣历（共同层）：当天全网一致，用真实在售单品名
FEAST_TPL = "今日圣体：{item}"


# ---------------------------------------------------------------- 短码（公开可复算）

CLAIM_KEYS = ("era", "relic", "orders", "stores", "cities", "grace", "period")


def claims_of(f: dict, grace_id: str, period: str) -> dict:
    """从真实行为里抽出 7 个【可公开】的量。
    只放卡面上本来就印着的东西 —— 短码要能被别人复算，就不能依赖隐私字段。"""
    return {
        "era": f.get("dominant_axis", "novice"),
        "relic": f.get("top_item", "本命圣物"),
        "orders": int(f.get("total_orders", 0) // 10) * 10,   # 粗化到 10，避免倒推精确值
        "stores": int(f.get("store_count", 0)),
        "cities": int(f.get("cross_city", 0)),
        "grace": grace_id,
        "period": period,
    }


def verify_code(claims: dict, version: int = 1) -> str:
    """任何人拿你卡面上的数字都能算出同一串 —— 这就是不可伪造的落点"""
    canon = "|".join(f"{k}={claims[k]}" for k in CLAIM_KEYS)
    return b32(int(hashlib.sha256(f"{canon}|v{version}".encode()).hexdigest()[:12], 16))


# ---------------------------------------------------------------- 主导行为轴

def dominant_axis(f: dict, uid: str) -> str:
    """七选一。阈值互斥的（夜祷/晨祷）不会并存；都不中的走 novice。"""
    if f.get("days_since_last", 0) >= 30:
        return "returned"
    if f.get("cross_city", 0) >= 2 and f.get("store_count", 0) >= 5:
        return "cross"
    if f.get("night_ratio", 0) >= 0.45:
        return "noct"
    if f.get("breakfast_ratio", 0) >= 0.40:
        return "matut"
    if f.get("store_count", 1) <= 1 and f.get("total_orders", 0) >= 5:
        return "one"
    if f.get("purity", 0) >= 0.70:
        return "unitas"
    return "novice"


# 自陈句已经说过的数字，行迹里不许再说一遍（否则出现「我已 47 天未曾回来｜久别 47 天」）
AXIS_BLOCKS = {"returned": {"returned"}, "cross": {"cities"}, "one": {"stores"},
               "unitas": {"purity"}, "noct": {"night"}, "matut": set(),
               "novice": set()}


def pick_deeds(f: dict, uid: str, k: int = 2, axis: str = "") -> list:
    """按 specificity 取前 k 条真实行迹；同分用 uid 打散，保证同数据同结果"""
    blocked = AXIS_BLOCKS.get(axis, set())
    cands = [(name, spec, tpl, get) for name, cond, spec, tpl, get in DEEDS
             if cond(f) and name not in blocked]
    cands.sort(key=lambda c: (-c[1], h(uid, c[0])))
    out = []
    for name, spec, tpl, get in cands[:k]:
        out.append(tpl.format(n=get(f)))
    return out


def pick_petition(f: dict, uid: str, period: str, friendly: bool = False) -> str:
    """默认只出 T0（零成本）。T1 是例外，且必须解锁 + 带免责短句。"""
    allow_t1 = bool(f.get("birthday_today")) or bool(f.get("milestone")) or friendly
    if allow_t1 and h(uid, "pet", period) % 100 < 35:
        p = PETITIONS_T1[h(uid, "t1", period) % len(PETITIONS_T1)]
        return p + "；若不方便，完全不必为难"
    return PETITIONS_T0[h(uid, "t0", period) % len(PETITIONS_T0)]


# ---------------------------------------------------------------- 编译

def compile_sign(f: dict, uid: str, today: date, menu_today: list,
                 grace_id: str = "laicus", grace_creed: str = "",
                 period: str | None = None, mode: str = "weekly",
                 friendly: bool = False, version: int = 1) -> dict:
    """
    mode:
      weekly    常规暗号，按 ISO 周更 —— 同一周内稳定，跨周换一枚（保持新鲜）
      festival  节庆暗号，种子含当天日期与活动 id，当天内全网共享同一句圣历
      limited   限定暗号，里程碑触发（生日/首店/第 N 次礼拜/久别回归），永久有效
    """
    period = period or (iso_week(today) if mode == "weekly" else today.isoformat())
    axis = f.get("dominant_axis") or dominant_axis(f, uid)
    f = dict(f, dominant_axis=axis)

    v_pool = VOCATION[axis]
    vocation = v_pool[h(uid, "voc", period) % len(v_pool)]
    vocation = vocation.format(city=f.get("cross_city", 0), days=f.get("days_since_last", 0))

    deeds = pick_deeds(f, uid, k=2, axis=axis)
    relic = f.get("top_item", "本命圣物")
    petition = pick_petition(f, uid, period, friendly)
    response = RESPONSES[h(uid, "rsp", period) % len(RESPONSES)]

    feast = ""
    if menu_today:
        item = menu_today[h(today.isoformat(), "saint") % len(menu_today)]
        feast = FEAST_TPL.format(item=item)

    claims = claims_of(f, grace_id, period)
    code = verify_code(claims, version)

    # ---- 短版（备注栏）：行迹是"不可伪造"的落点，最后一个才能丢
    #     丢弃优先级：圣历 → 圣物缩写 → 行迹
    def build(with_deed: bool, with_feast: bool, short_relic: bool) -> str:
        parts = [f"麦门 {code}"]
        parts.append(vocation)
        parts.append(relic if not short_relic else relic[:4])
        if with_deed and deeds:
            parts.append(deeds[0])
        if with_feast and feast:
            parts.append(feast)
        return "｜".join(parts) + f"。{petition}，麦门永生。"

    LADDER = [(True, False, False),   # 先试：行迹在、无圣历
              (True, False, True),    # 再试：圣物缩到 4 字
              (False, False, False),  # 最后才动行迹
              (False, False, True)]
    short = build(True, True, False)
    if len(short) > REMARK_LIMIT:
        for a, b, c in LADDER:
            short = build(a, b, c)
            if len(short) <= REMARK_LIMIT:
                break

    long_ = "\n".join(x for x in [
        "— 麦门行传 · 我的这一卷 —",
        f"[{code}]  {vocation}",
        f"本命圣物：{relic}",
        " · ".join(deeds) if deeds else "",
        f"教义：{grace_creed}" if grace_creed else "",
        feast,
        f"{petition}。{response}",
    ] if x)

    return {
        "mode": mode, "period": period, "code": code, "claims": claims,
        "axis": axis, "vocation": vocation, "relic": relic, "deeds": deeds,
        "petition": petition, "response": response, "feast": feast,
        "short": short, "long": long_,
        "len": len(short), "overflow": len(short) > REMARK_LIMIT,
        "expires": "本周日 23:59" if mode == "weekly" else
                   ("今日 23:59" if mode == "festival" else "永久"),
    }


def report_text(sign: dict, store_name: str, responded: bool | None) -> str:
    """回报文案：用户把店员反应贴回 GitHub issue。
    没有后端也能跑 —— issue 模板本身就是收集器。"""
    if responded is None:
        tail = "店员：尚未回应 / 我没来得及问"
    elif responded:
        tail = f"回应：{store_name} 认了这个暗号"
    else:
        tail = f"回应：{store_name} 暂时没懂（不怪门店）"
    return (f"暗号 {sign['code']}｜{store_name}\n"
            f"{tail}\n"
            f"周期 {sign['period']}｜模式 {sign['mode']}")


# ---------------------------------------------------------------- 自检

if __name__ == "__main__":
    today = date(2026, 10, 21)
    menu = ["麦辣鸡腿堡", "板烧鸡腿堡", "麦香鱼", "脆脆薯条", "麦旋风", "猪柳蛋麦满分"]

    users = [
        ("u_00029", dict(top_item="麦辣鸡腿堡", total_orders=188, store_count=2,
                         cross_city=1, night_ratio=.68, breakfast_ratio=.10,
                         purity=.84, days_since_last=1, years_since_first=4),
         "nocturni", "我守夜，不是为了饿，是为了那段没人打扰的安静。"),
        ("u_00006", dict(top_item="脆脆薯条", total_orders=412, store_count=37,
                         cross_city=9, night_ratio=.21, breakfast_ratio=.12,
                         purity=.31, days_since_last=2, years_since_first=7),
         "peregrinatores", "到一座城，先认它的门。"),
        ("u_00000", dict(top_item="猪柳蛋麦满分", total_orders=64, store_count=1,
                         cross_city=1, night_ratio=.05, breakfast_ratio=.62,
                         purity=.77, days_since_last=0, years_since_first=2),
         "matutini", "我的一天，要先有一段仪式才肯开始。"),
        ("u_10427", dict(top_item="麦香鱼", total_orders=9, store_count=3,
                         cross_city=1, night_ratio=.20, breakfast_ratio=.20,
                         purity=.40, days_since_last=0, years_since_first=1),
         "laicus", "我不常提起我信什么，但我从来没否认过。"),
        ("u_77777", dict(top_item="板烧鸡腿堡", total_orders=233, store_count=12,
                         cross_city=4, night_ratio=.15, breakfast_ratio=.25,
                         purity=.52, days_since_last=47, years_since_first=6),
         "reclusi", "我只认这一扇门，因为它认识我。"),
    ]

    print(f"备注栏上限 = {REMARK_LIMIT} 字（待实测）\n")
    for uid, f, gid, creed in users:
        s = compile_sign(f, uid, today, menu, gid, creed)
        print(f"── {uid}  轴={s['axis']:9s} 码={s['code']}  长度={s['len']}"
              f"{'  ⚠ 超限' if s['overflow'] else ''}")
        print(f"   短版：{s['short']}")
        print()

    print("── 长版样例（u_00006）──")
    s6 = compile_sign(users[1][1], users[1][0], today, menu,
                      users[1][2], users[1][3])
    print(s6["long"])
    print("\n── 回报文案 ──")
    print(report_text(s6, "深圳华强北店", True))

    # 同一用户跨周：应当换一枚；同周内：必须完全一样
    a = compile_sign(users[0][1], "u_00029", date(2026, 10, 21), menu)
    b = compile_sign(users[0][1], "u_00029", date(2026, 10, 22), menu)
    c = compile_sign(users[0][1], "u_00029", date(2026, 10, 28), menu)
    print(f"\n同周稳定 = {a['short'] == b['short']}；跨周变化 = {a['short'] != c['short']}")

    # 复算：同一份数据必须算出同一个码
    recomputed = verify_code(a["claims"])
    print(f"公开复算一致 = {recomputed == a['code']}（{recomputed}）")

    # ---------------------------------------------------------- 熵实测
    import random
    from collections import Counter
    random.seed(20261021)
    print("\n── 唯一性实测（合成 5000 个用户，同一周）──")
    full, skel = Counter(), Counter()
    base = ["麦辣鸡腿堡", "板烧鸡腿堡", "麦香鱼", "脆脆薯条", "麦旋风",
            "猪柳蛋麦满分", "双层吉士汉堡", "麦麦脆汁鸡", "那么大鸡排", "热香饼"]
    items10 = base
    items60 = base + [f"在售单品{i:02d}" for i in range(50)]   # 模拟真实菜单规模
    for label, items in (("10 个单品（保守）", items10),
                         ("60 个单品（真实菜单规模）", items60)):
      full.clear(); skel.clear()
      for i in range(5000):
        f = dict(
            top_item=random.choice(items),
            total_orders=random.randint(1, 600),
            store_count=random.choice([1, 1, 2, 3, 5, 9, 17, 31, 48]),
            cross_city=random.choice([1, 1, 1, 2, 3, 5, 9]),
            night_ratio=random.random(),
            breakfast_ratio=random.random(),
            purity=random.random(),
            days_since_last=random.choice([0, 0, 1, 3, 9, 40, 120]),
            years_since_first=random.randint(0, 9),
        )
        s = compile_sign(f, f"u_{i:06d}", today, menu)
        full[s["short"]] += 1
        skel[(s["axis"], s["vocation"], s["relic"], s["petition"], s["deeds"][0] if s["deeds"] else "")] += 1
      dup_full = sum(v - 1 for v in full.values() if v > 1)
      print(f"  [{label}]")
      print(f"    完整短版去重率 : {len(full) / 5000:6.2%}  （{len(full)} / 5000）")
      print(f"    骨架去重率     : {len(skel) / 5000:6.2%}  （轴+自陈+圣物+请求+行迹模板）")
      print(f"    完全撞脸对数   : {dup_full} / {5000 * 4999 // 2:,}")
