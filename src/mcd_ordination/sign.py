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

# ---------------------------------------------------------------- 三体裁
# 暗号不只有一种用途。三条体裁，用户可显式选择，也可交给 auto 按行为决定。
KINDS = {
    "greet": {"cn": "问候", "lat": "Salutatio",
              "desc": "向门店打个招呼，不求任何东西"},
    "ask":   {"cn": "请求", "lat": "Petitio",
              "desc": "说清要什么，再补一句玩笑；照做是彩蛋，不照做也成立"},
    "story": {"cn": "接龙", "lat": "Continuatio",
              "desc": "门店本就有一卷传说，你来求取下一段；下次带来的是续篇"},
}

# S5a 问候：完全不索要，只做人际连接
BLESSINGS = [
    "今天也辛苦你们了",
    "愿这个点还站着的人都有热的东西吃",
    "路过进来看看，不为别的",
    "你们几点收工？我下次算着时间来",
    "这一带的灯，就你们这几盏还亮着",
]

# S5b 请求：**这一格的目标不是"绕"，是"说得清楚还很好笑"。**
#
# v3.7 重写（用户反馈：看不出到底在请求什么）：
#   · 每一句都必须让店员**一眼知道你要什么**：多一块麦乐鸡 / 写一句批注 / 画个勾
#   · 笑点加在"要什么"之后，而不是替代"要什么"
#   · 请求式默认走 T1（真的开口要，量级上限=一块鸡块），想只要零成本用 --soft 降级
ASKS_T1 = [
    "若今日还有余量，可否多给我一块麦乐鸡？我想把它写进行传",
    "可否多给一块麦乐鸡？我拿它当今日的圣物",
    "若锅底还剩，可否多抓一把薯条？我今晚靠这个续命",
    "可否多给一包甜酸酱？我要拿它蘸我的信仰",
    "若正好方便，可否把薯条装满一点？我会记你一功",
]
# T0：零成本，但同样必须说清"要什么动作"
ASKS_T0 = [
    "可否在我的纸袋上写一句「已阅」？我今天很需要这个批示",
    "可否在杯套上画个勾？我拿回去当圣痕",
    "可否在袋上写「此人已尽力」？我今天撑得很勉强",
    "可否用红笔圈一下我的名字？像教皇批文件那样",
]
# T1 结尾不再挂「若不方便，完全不必为难」——它占字数，而且店员看到的只是一个
# 陌生人的免责声明。改成 skill 署名：店员一眼知道「这是有人用工具生成的一句话」，
# 既知道该往哪看，也知道不必当成投诉。
# 礼貌用语下沉到语料本身（"若今日还有余量""若锅底还剩"），比末尾补一句更自然。
SIGN_ASK = "【麦门暗号skill】"
# 接龙的收尾把"求一句"和来路并成一个印记：既表明这是求取下一段，也说明词出自哪个 skill。
# 单独一个「敢请续墨」会被读成文学腔，单独一个 skill 名又看不出要做什么，合起来刚好。
SIGN_STORY = "【敢请续墨·麦门传说skill】"

# S5c 接龙：留半句话。半句必须"可被任意店员接着写"，不能要求对方懂梗
STORY_OPEN = {
    "noct": ["凌晨两点的店里，灯是唯一没睡的东西，",
             "这个点还开门的地方，一定有自己的道理，",
             "我把今天的最后一句话留在这里，"],
    "matut": ["七点十分，城市还没醒，",
              "一天里最先热起来的是你们这台机器，",
              "我在上班前绕了一段路，"],
    "cross": ["我在这座城只认得这一扇门，",
              "换了个城市，先找同一个拱门，",
              "行李箱还在手上，我先来了这里，"],
    "one": ["我几乎每次都点同一样东西，",
            "整条街我只进这一家，",
            "这扇门认识我，我也认识它，"],
    "unitas": ["我又点了同样的东西，",
               "重复这件事，对我来说是有意义的，"],
    "returned": ["隔了 {days} 天，我又站在这里，",
                 "我以为我不会再来了，但我还是来了，"],
    "novice": ["第一次来，我还没记住这里的规矩，",
               "我刚搬来这一带，",
               "我是被门口那盏灯引进来的，"],
}

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


def pick_ask(f: dict, uid: str, period: str, friendly: bool = False,
             allow_t1: bool = True, user_asks: list | None = None,
             soft: bool = False) -> tuple:
    """
    返回 (文本, 档位)。规则：
      · 默认 T0（零成本）
      · T1 必须由用户显式选择，或命中生日/里程碑/友好门店
      · T1 一律带免责短句；上限是"一块鸡块"这个量级，不许要免单/套餐
    """
    unlock = (allow_t1 or f.get("birthday_today") or f.get("milestone")
              or friendly) and not soft
    if unlock:
        return ASKS_T1[h(uid, "t1", period) % len(ASKS_T1)], "T1"
    # 自己写的句子，命中率给到 45%：既看得到，也不会把内置语料挤没
    pool = user_asks or []
    if pool and h(uid, "uas", period) % 100 < 45:
        return pool[h(uid, "uap", period) % len(pool)], "T0"
    return ASKS_T0[h(uid, "t0", period) % len(ASKS_T0)], "T0"


def pick_kind(f: dict, uid: str, period: str, want: str = "auto") -> str:
    """auto 的取向：久别/生日 → 问候或请求；日常 → 接龙（接龙最能带来二次互动）"""
    if want in KINDS:
        return want
    if f.get("birthday_today") or f.get("days_since_last", 0) >= 30:
        return "greet"
    return "story"


# ---------------------------------------------------------------- 用户投稿（UGC）
#
# 语料会磨损（见 DESIGN §5.10.2），扩池子最便宜的办法是让用户自己写。
# 但投稿内容会被印进**店员真的会看到的备注**，所以校验必须比"能存下"更严：
#   · 只收 T0（零成本）：不许要免单、套餐、赠品，不许出现阿拉伯数字（防电话/订单号）
#   · 不出现链接、社交账号、地址
#   · 长度 6–28 字：超过这个长度，加上自陈就会顶破备注栏
# 校验不通过**不写入**，并把原因原样返回——默默吞掉比拒绝更糟。

MIN_ASK_LEN, MAX_ASK_LEN = 6, 28

BANNED = ("免单", "免费", "白送", "白拿", "套餐", "玩具", "退款", "折现", "现金",
          "红包", "加菜", "免配送", "多送一份", "微信", "电话", "地址", "http",
          "www.", "@", "二维码")


def _asks_path():
    import os
    from pathlib import Path
    p = os.environ.get("MCD_ASKS_FILE")
    if p:
        return Path(p)
    base = Path(os.environ.get("MCD_STORY_DIR", Path.home() / ".mcd-ordination"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "asks_user.json"


def load_user_asks() -> list:
    import json
    path = _asks_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("asks") if isinstance(data, dict) else data
    return [x["text"] if isinstance(x, dict) else str(x) for x in (items or [])]


def validate_ask(text: str) -> tuple:
    t = " ".join(str(text).split())
    if not t:
        return False, "空内容"
    # 先查禁令再查长度：用户更需要知道"为什么不合适"，而不是"字太少"
    hit = next((b for b in BANNED if b in t), None)
    if hit:
        return False, f"含「{hit}」：这一体裁只收零成本请求，不许要实物或留联系方式"
    if any(ch.isdigit() for ch in t):
        return False, "不要出现阿拉伯数字（防止电话号码/订单号被印进备注）"
    if len(t) < MIN_ASK_LEN:
        return False, f"太短（至少 {MIN_ASK_LEN} 字，否则不像一句话）"
    if len(t) > MAX_ASK_LEN:
        return False, f"太长（上限 {MAX_ASK_LEN} 字，加上自陈会顶破备注栏）"
    if t in ASKS_T0 or t in ASKS_T1:
        return False, "和内置语料重复了"
    if t in load_user_asks():
        return False, "你已经投过这一句"
    return True, t


def add_user_ask(text: str) -> dict:
    import json
    from datetime import datetime
    ok, msg = validate_ask(text)
    if not ok:
        return {"ok": False, "reason": msg}
    path = _asks_path()
    asks = load_user_asks()
    asks.append(msg)
    payload = {"asks": [{"text": a, "added": datetime.now().isoformat(timespec="minutes")}
                        for a in asks]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "text": msg, "total": len(asks), "path": str(path)}


# ---------------------------------------------------------------- 编译

def compile_sign(f: dict, uid: str, today: date, menu_today: list,
                 grace_id: str = "laicus", grace_creed: str = "",
                 period: str | None = None, mode: str = "weekly",
                 friendly: bool = False, version: int = 1,
                 kind: str = "auto", allow_t1: bool = True,
                 story: dict | None = None,
                 user_asks: list | None = None, soft: bool = False) -> dict:
    """
    mode:
      weekly    常规暗号，按 ISO 周更 —— 同一周内稳定，跨周换一枚（保持新鲜）
      festival  节庆暗号，种子含当天日期与活动 id，当天内全网共享同一句圣历
      limited   限定暗号，里程碑触发（生日/首店/第 N 次礼拜/久别回归），永久有效

    kind:
      greet / ask / story，或 auto（按行为替你选）
    allow_t1:
      True 表示用户显式勾选了「愿意问一句能不能多给一点」。仍会带免责短句。
    story:
      本地接龙账本 {"chapter": n, "last": "店员上次写的半句"}；不传就是第一章
    """
    period = period or (iso_week(today) if mode == "weekly" else today.isoformat())
    axis = f.get("dominant_axis") or dominant_axis(f, uid)
    f = dict(f, dominant_axis=axis)

    v_pool = VOCATION[axis]
    vocation = v_pool[h(uid, "voc", period) % len(v_pool)]
    vocation = vocation.format(city=f.get("cross_city", 0), days=f.get("days_since_last", 0))

    deeds = pick_deeds(f, uid, k=2, axis=axis)
    relic = f.get("top_item", "本命圣物")
    response = RESPONSES[h(uid, "rsp", period) % len(RESPONSES)]
    blessing = BLESSINGS[h(uid, "bls", period) % len(BLESSINGS)]

    kind = pick_kind(f, uid, period, kind)
    # 请求式的笑点按【每一单】轮换：同一个笑话挂一周，笑点就死了。
    # 种子取这一单的时间戳，所以同一单永远同一句，下一单必换。
    ask_salt = f.get("last_order_at") or period if kind == "ask" else period
    pool_user = load_user_asks() if user_asks is None else user_asks
    ask, ask_tier = pick_ask(f, uid, ask_salt, friendly, allow_t1, pool_user, soft)
    ask_source = "t1" if ask_tier == "T1" else ("mine" if ask in pool_user else "builtin")

    # 接龙：章节号只由本地账本决定，不参与哈希，避免"账本一改短码就变"
    story = story or {}
    chapter = int(story.get("chapter", 0)) + 1
    last_line = (story.get("last") or "").strip()
    open_pool = STORY_OPEN[axis]
    opening = open_pool[h(uid, "st", period) % len(open_pool)].format(
        days=f.get("days_since_last", 0))
    prompt = "敢请续墨"

    feast = ""
    if menu_today:
        item = menu_today[h(today.isoformat(), "saint") % len(menu_today)]
        feast = FEAST_TPL.format(item=item)

    claims = claims_of(f, grace_id, period)
    code = verify_code(claims, version)

    def build(with_deed: bool, with_feast: bool, short_relic: bool) -> str:
        parts = [f"麦门 {code}"]
        parts.append(vocation)
        parts.append(relic if not short_relic else relic[:4])
        if with_deed and deeds:
            parts.append(deeds[0])
        if with_feast and feast:
            parts.append(feast)
        return "｜".join(parts)

    # ---- 三体裁各自组装短版（备注栏）。都遵守 REMARK_LIMIT。
    if kind == "story":
        # opening 收尾是逗号，直接接【】会像断句错误；统一换成句号再接印记
        body = opening.rstrip("，,。 ")
        if chapter > 1 and last_line:
            short = f"第 {chapter} 章·承「{last_line[:8]}」：{body}。{SIGN_STORY}"
        else:
            short = f"第 {chapter} 章：{body}。{SIGN_STORY}"
    elif kind == "greet":
        short = f"{vocation}｜{blessing}，麦门永生。"
    else:
        # 请求式刻意只保留"自陈 + 笑点"两个槽：
        # 加圣物/行迹会让句子变成清单，笑点被稀释。短码仍然承担可复算。
        tail = f"{ask}。{SIGN_ASK}"
        short = f"{vocation}｜{tail}"
        if len(short) > REMARK_LIMIT:          # 极端长自陈时，只留笑点
            short = tail

    # 接龙超长：先缩引文，再丢「第 N 章·承…」前缀——署名比章节号重要
    if kind == "story" and len(short) > REMARK_LIMIT and chapter > 1 and last_line:
        short = f"第 {chapter} 章：{body}。{SIGN_STORY}"

    # 极端情况下仍超限：截到上限，但**保住结尾的 skill 署名**，否则店员看不出这是什么
    if len(short) > REMARK_LIMIT:
        sig = next((x for x in (SIGN_ASK, SIGN_STORY) if short.endswith(x)), "")
        body = short[: len(short) - len(sig)]
        short = body[: REMARK_LIMIT - len(sig) - 1] + "…" + sig

    long_lines = ["— 麦门行传 · 我的这一卷 —", f"[{code}]  {vocation}"]
    if kind == "story":
        long_lines.append(f"第 {chapter} 章")
        if chapter > 1 and last_line:
            long_lines.append(f"上一章，你续的那一句：「{last_line}」")
        long_lines.append(f"{body}。{SIGN_STORY}")
        long_lines.append(f"（本命圣物：{relic}）")
    elif kind == "greet":
        long_lines.append(f"本命圣物：{relic}")
        long_lines.append(" · ".join(deeds) if deeds else "")
        long_lines.append(f"{blessing}。{response}")
    else:
        long_lines.append(f"本命圣物：{relic}")
        long_lines.append(" · ".join(deeds) if deeds else "")
        long_lines.append(f"{ask}。{response}")
    if grace_creed:
        long_lines.append(f"教义：{grace_creed}")
    if feast:
        long_lines.append(feast)
    long_ = "\n".join(x for x in long_lines if x)

    return {
        "mode": mode, "period": period, "code": code, "claims": claims,
        "kind": kind, "kind_cn": KINDS[kind]["cn"],
        "axis": axis, "vocation": vocation, "relic": relic, "deeds": deeds,
        "blessing": blessing, "ask": ask, "ask_tier": ask_tier,
        "ask_source": ask_source,
        "response": response, "feast": feast,
        "story_chapter": chapter, "story_open": opening,
        "story_prompt": prompt, "story_last": last_line,
        "short": short, "long": long_,
        "len": len(short), "overflow": len(short) > REMARK_LIMIT,
        "expires": "本周日 23:59" if mode == "weekly" else
                   ("今日 23:59" if mode == "festival" else "永久"),
    }


# ---------------------------------------------------------------- 接龙账本（只存本地）
#
# 为什么不放服务器：接龙的连续性属于用户自己的记忆，一旦上云就变成"平台在写你的故事"。
# 目录可用 MCD_STORY_DIR 覆盖；默认 ~/.mcd-ordination/，不进仓库。

def _story_path(uid: str):
    import os
    from pathlib import Path
    base = Path(os.environ.get("MCD_STORY_DIR", Path.home() / ".mcd-ordination"))
    base.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in uid if c.isalnum() or c in "-_") or "anon"
    return base / f"story_{safe}.json"


def load_story(uid: str) -> dict:
    import json
    path = _story_path(uid)
    if not path.exists():
        return {"chapter": 0, "last": "", "history": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"chapter": 0, "last": "", "history": []}


def append_story(uid: str, sign: dict, wrote_back: str) -> dict:
    """把店员写回来的那半句记进本地账本，下一次 compile_sign 会自动接上"""
    import json
    led = load_story(uid)
    led["chapter"] = max(int(led.get("chapter", 0)), int(sign.get("story_chapter", 1)))
    led["last"] = (wrote_back or "").strip()
    led.setdefault("history", []).append({
        "chapter": sign.get("story_chapter"),
        "code": sign.get("code"),
        "opening": sign.get("story_open"),
        "wrote_back": led["last"],
    })
    _story_path(uid).write_text(json.dumps(led, ensure_ascii=False, indent=1),
                                encoding="utf-8")
    return led


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
