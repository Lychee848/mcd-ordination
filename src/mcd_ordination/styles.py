#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
styles.py —— 「同一套票流程，不同一套脸」的风格解析器

设计前提（很重要）：
  风格必须 100% 由数据决定，不能让用户手动选，
  否则"这是真实订单炼出来的"这个卖点就废了。
  => 所有随机都是 hash 出来的伪随机：同一份订单永远得到同一张脸。

三条轴分工不同，不要混：
  ART   画派        —— 用户级：由订单摘要 hash 决定 => 每个用户一套面貌
  FOIL  闪艺        —— 用户级：由虔诚度百分位决定 => 稀有度是真·成绩，不是抽奖
  FRAME 卡框/卡种   —— 卡级：由这一单本身的性质决定 => 同一套卡内部有编排感

2026-10-20 修订：全画派阳光化。
  上一版有"双色木刻""褪色宝丽来"这类暗调画派，宗教感有了，但太阴。
  宗教感不等于阴郁——参考的是彩色玻璃窗被阳光穿透、乔托湿壁画的粉彩金底、
  1940s 黄金时代广告插画里的暖阳，不是墓室壁画。
  实现手段：每个画派都必须带 LIGHT 槽位（暖阳 / 透光 / 金辉），
  并在 NEGATIVE 里硬性禁止阴郁。
"""
import hashlib

# ---------------------------------------------------------------- 基础工具

def h(*parts) -> int:
    s = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:12], 16)


def pick(seed: int, dist):
    """dist = [(value, weight), ...]  稳定抽样"""
    total = sum(w for _, w in dist)
    x = seed % total
    for v, w in dist:
        if x < w:
            return v
        x -= w
    return dist[-1][0]


# ---------------------------------------------------------------- 阳光基线

# 所有画派共用：先定"光"，再定"画法"。这一段不许被覆盖。
LIGHT = ("warm sunlight raking from upper left, bright open daylight, "
         "gentle golden holy glow, clean luminous shadows, "
         "cheerful reverent mood, the light of a stained-glass window at noon")

MOOD = "uplifting, kindly, quietly joyful, devotional but never somber"

NEGATIVE = ("no gloom, no horror, no grim atmosphere, no dark moody lighting, "
            "no muddy desaturation, no graveyard, no decay, no skulls, "
            "no religious fanaticism, no blood, no smoke, no night-noir, "
            "no text, no lettering, no border, no frame, no watermark")


# ---------------------------------------------------------------- 轴 1：画派

ART_SCHOOLS = {
    "stained": {
        "lat": "Stained Glass",
        "cn": "彩色玻璃窗",
        "prompt_medium": "stained glass window design, jewel-toned glass panes divided by "
                         "warm lead lines, light shining through from behind",
        "prompt_render": "translucent gem colors, cobalt and ruby and amber glass, "
                         "glowing halo of light behind the figure",
        "prompt_palette": "cobalt blue, ruby red, amber gold, emerald, cream",
        "grade": dict(sat=1.18, contrast=1.02, bright=1.10, warmth=(255, 238, 206, 0.10), grain=0.04),
    },
    "fresco": {
        "lat": "Giotto Fresco",
        "cn": "湿壁画",
        "prompt_medium": "Italian trecento fresco, matte plaster surface, soft pastel modeling, "
                         "flat gold ground, gentle rounded volumes",
        "prompt_render": "chalky fresco texture, thin painted shadow, no cast shadow, "
                         "halo rendered as a flat gold disc",
        "prompt_palette": "rose pink, sky blue, leaf green, gold leaf, plaster white",
        "grade": dict(sat=1.06, contrast=1.00, bright=1.12, warmth=(255, 244, 222, 0.10), grain=0.05),
    },
    "goldage": {
        "lat": "Golden Age Illustration",
        "cn": "黄金时代插画",
        "prompt_medium": "1940s American golden age illustration, clean confident line, "
                         "rounded forms, sunlit saturate color",
        "prompt_render": "soft outdoor light, warm skin tones, crisp clean highlights, "
                         "cheerful advertising warmth",
        "prompt_palette": "corn yellow, tomato red, robin egg blue, cream",
        "grade": dict(sat=1.10, contrast=1.04, bright=1.08, warmth=(255, 246, 228, 0.07), grain=0.03),
    },
    "chromo": {
        "lat": "Chromolithograph",
        "cn": "石版套色宣传画",
        "prompt_medium": "1890s chromolithograph poster, six-stone color separation, "
                         "dense crosshatch overprint, rich register buildup",
        "prompt_render": "clean paper, warm inks, slightly off-register halftone dots, "
                         "decorative border ornaments",
        "prompt_palette": "deep carmine, olive, chrome yellow, warm ink",
        "grade": dict(sat=1.05, contrast=1.06, bright=1.10, warmth=(255, 236, 202, 0.09), grain=0.07),
    },
    "enamel": {
        "lat": "Vitreous Enamel Sign",
        "cn": "珐琅招牌画",
        "prompt_medium": "vitreous enamel advertising sign, kiln-fired glossy surface, "
                         "bold flat color, crisp linework",
        "prompt_render": "specular gloss streaks, bright clean ground, porcelain sheen",
        "prompt_palette": "cobalt blue, cream, signal red, oxford grey",
        "grade": dict(sat=1.20, contrast=1.04, bright=1.10, warmth=(255, 250, 238, 0.04), grain=0.03),
    },
    "icon": {
        "lat": "Tempera Panel Icon",
        "cn": "蛋彩圣像画",
        "prompt_medium": "panel icon in egg tempera on gessoed wood, fine hatching highlights, "
                         "gold leaf ground catching daylight",
        "prompt_render": "flat bright gold ground, deliberate stylization, "
                         "luminous rather than dark, no cast shadow",
        "prompt_palette": "byzantine gold, cinnabar, ultramarine, verdigris, egg white",
        "grade": dict(sat=1.14, contrast=1.02, bright=1.12, warmth=(255, 240, 200, 0.11), grain=0.05),
    },
    "poster": {
        "lat": "Festival Poster",
        "cn": "节庆宣传画",
        "prompt_medium": "mid-century festival poster, flat lithograph color blocks, "
                         "bold silhouette shapes, confetti and ribbon ornament",
        "prompt_render": "flat bright ground, celebratory composition, "
                         "sunburst rays behind the subject",
        "prompt_palette": "sunny yellow, vermilion, mint, cream white",
        "grade": dict(sat=1.16, contrast=1.06, bright=1.12, warmth=(255, 248, 226, 0.06), grain=0.04),
    },
}

# 权重：七种拉平，再略微偏向"彩色玻璃/湿壁画"这两种最有宗教感又最亮的
ART_DIST = [("stained", 18), ("fresco", 17), ("goldage", 15), ("chromo", 13),
            ("enamel", 13), ("icon", 12), ("poster", 12)]

# 签名笔触：同一画派再抽一个手法，制造二级差异（全部偏亮，不许阴）
SIGNATURE = [
    "sunburst rays radiating behind the subject",
    "doves or swallows in the upper corners",
    "a wreath of wheat ears framing the figure",
    "gold leaf disc halo with punched ornament",
    "soft cloud bank at the bottom of the frame",
    "rays of light rendered as thin gold lines",
    "flower garland along the lower edge",
    "halftone dot screen 12% visible, warm ink",
]


# ---------------------------------------------------------------- 轴 2：闪艺（稀有度）

FOILS = {
    "common": {"cn": "平卡",     "lat": "Common",         "gold_name": False, "holo": 0.00, "edge": False, "tint": None,      "anim": 0},
    "rare":   {"cn": "银字",     "lat": "Rare",           "gold_name": False, "holo": 0.00, "edge": True,  "tint": None,      "anim": 0},
    "super":  {"cn": "面闪",     "lat": "Super Rare",     "gold_name": False, "holo": 0.14, "edge": True,  "tint": None,      "anim": 1},
    "ultra":  {"cn": "金闪",     "lat": "Ultra Rare",     "gold_name": True,  "holo": 0.16, "edge": True,  "tint": "gold",    "anim": 1},
    "secret": {"cn": "全息",     "lat": "Ghost Rare",     "gold_name": True,  "holo": 0.22, "edge": True,  "tint": "silver",  "anim": 2},
    "mythic": {"cn": "圣髑闪",   "lat": "Relic Rare",     "gold_name": True,  "holo": 0.30, "edge": True,  "tint": "rainbow", "anim": 3},
}

# 注意：稀有度不再由虔诚度直接决定。
# 链路是  gacha.draw() 出 rank  ->  resolve_style(digest, rank) 只负责"长什么样"。
# 旧的 foil_by_piety() 因 FOILS 键名变更已失效且无人调用，2026-10-20 删除。
# 虔诚度现在只通过 gacha._apply_piety() 调整抽取权重，不直接发卡。


# ---------------------------------------------------------------- 轴 3：卡框 / 卡种

FRAMES = {
    "normal_monster": {"cn": "通常怪兽", "lat": "NORMAL MONSTER", "bg": (255, 216, 105), "ink": (60, 44, 20),   "glow": (255, 240, 176)},
    "effect":         {"cn": "效果怪兽", "lat": "EFFECT MONSTER", "bg": (246, 152, 62),  "ink": (66, 34, 12),   "glow": (255, 214, 160)},
    "ritual":         {"cn": "仪式怪兽", "lat": "RITUAL MONSTER", "bg": (58, 150, 208),  "ink": (10, 40, 66),   "glow": (184, 226, 248)},
    "fusion":         {"cn": "融合怪兽", "lat": "FUSION MONSTER", "bg": (166, 96, 224),  "ink": (34, 12, 56),   "glow": (226, 200, 250)},
    "synchro":        {"cn": "同调怪兽", "lat": "SYNCHRO MONSTER","bg": (246, 244, 238), "ink": (32, 32, 32),   "glow": (226, 226, 220)},
    "xyz":            {"cn": "超量怪兽", "lat": "XYZ MONSTER",    "bg": (26, 24, 30),    "ink": (236, 232, 226),"glow": (112, 108, 120)},
    "link":           {"cn": "连接怪兽", "lat": "LINK MONSTER",   "bg": (16, 58, 150),   "ink": (226, 232, 246),"glow": (118, 158, 224)},
    "spell":          {"cn": "圣礼",     "lat": "SPELL CARD",     "bg": (34, 152, 120),  "ink": (8, 44, 36),    "glow": (168, 232, 214)},
    "trap":           {"cn": "异端审判", "lat": "TRAP CARD",      "bg": (188, 84, 128),  "ink": (48, 12, 30),   "glow": (246, 194, 218)},
    "item":           {"cn": "圣髑",     "lat": "RELIC CARD",     "bg": (212, 168, 74),  "ink": (52, 34, 10),   "glow": (246, 224, 176)},
    "field":          {"cn": "圣地",     "lat": "FIELD CARD",     "bg": (96, 168, 96),   "ink": (14, 44, 14),   "glow": (196, 232, 196)},
}

# 卡种 -> 版式。新增的四种卡（圣髑/圣礼/异端审判/圣地）走不同版式分支。
LAYOUTS = {
    "normal_monster": "monster", "effect": "monster", "ritual": "monster",
    "fusion": "monster", "synchro": "monster", "xyz": "monster", "link": "monster",
    "item":  "relic",        # 食物卡 / 道具卡：带营养六维
    "spell": "rite",         # 行为卡
    "trap":  "rite",         # 事件卡
    "field": "field",        # 地点卡：横幅画面窗
}


def frame_by_role(role: str) -> dict:
    return FRAMES.get(role, FRAMES["effect"])


# ---------------------------------------------------------------- 解析器

def resolve_style(digest: str, rank: str = "rare", season: int = 0) -> dict:
    """
    digest    : 订单摘要（建议 = sorted(order_ids) 拼串后再 sha256 的前 16 位）
    rank      : 抽卡结果（gacha.draw 的 rank）—— 决定闪艺。
                注意：稀有度不在这里算，这里只负责"长什么样"。
    season    : 第几版。同一份数据重跑默认完全一致；
                只有当你想要"周年重制版"时才 +1（会让画派重新掷一次）
    """
    school = ART_SCHOOLS[pick(h(digest, "art", season), ART_DIST)]
    foil = FOILS.get(rank, FOILS["rare"])
    sig    = SIGNATURE[h(digest, "sig", season) % len(SIGNATURE)]
    touch  = ["fine linework", "medium bristle", "bold flat shapes"][
        h(digest, "touch") % 3]
    era    = ["1920s", "1940s", "1950s"][h(digest, "era") % 3]
    pat    = ["none", "rays", "rings", "dots", "grid"][h(digest, "pat", season) % 5]
    # 色相微旋：框色 ±8°，让"同为效果怪兽"的两个人也不会撞成同一块橙
    hue    = (h(digest, "hue", season) % 17) - 8
    return {
        "art": school, "foil": foil, "signature": sig,
        "touch": touch, "era": era, "pattern": pat, "hue": hue,
        "edition": f"E{h(digest,'ed',season)%89+10:02d}",
    }


def full_style(digest: str, rank: str = "rare", frame_role: str = "effect",
               season: int = 0) -> dict:
    """resolve_style + 卡框。渲染器和提示词编译器都应该只拿这一个 dict。"""
    st = resolve_style(digest, rank, season)
    st["frame"] = FRAMES.get(frame_role, FRAMES["effect"])
    st["frame_role"] = frame_role
    st["layout"] = LAYOUTS.get(frame_role, "monster")
    return st


def style_prompt_block(st: dict) -> str:
    """喂进生图模型那一段。注意：只描述画法、光和情绪，不描述主体。"""
    a = st["art"]
    return (f"{a['prompt_medium']}, {st['touch']}, {st['signature']}, "
            f"{a['prompt_render']}, palette of {a['prompt_palette']}, "
            f"{st['era']} advertising-art sensibility, {LIGHT}, mood: {MOOD}")


def negative_block() -> str:
    return NEGATIVE


if __name__ == "__main__":
    for uid in ["u_00005", "u_00000", "u_00034", "u_91234", "u_777"]:
        st = resolve_style(hashlib.sha256(uid.encode()).hexdigest()[:16], "super")
        print(f"{uid:9s} -> {st['art']['cn']:8s} "
              f"{st['foil']['cn']:5s} {st['touch']:16s} {st['era']} {st['edition']}")
