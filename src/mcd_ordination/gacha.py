#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抽卡机制 —— 用真实交易行为驱动，不卖币、不看金额、可复算

三条硬线（改任何一条，这个项目就从"有趣"变成"有问题"）：
  1. 一单 = 一抽。抽的次数由交易笔数决定，与金额无关。
  2. 概率只由"行为稀有度"决定，与消费金额、优惠券、点单数量无关。
     否则就是诱导消费，和之前定的"反消费主义阀门"直接冲突。
  3. 结果可复算。抽取种子 = hash(订单号 + 用户盐 + 版本号)，
     任何人拿同一份数据都能算出一模一样的卡 —— 没有服务器暗箱。

"盲盒感"从哪来：
  用户在下单那一刻不知道结果（种子里有当次订单号，事前不可预测），
  但事后任何人都能复算验证 —— 这是"可验证随机"，不是"信任我"。
"""
import hashlib

from .styles import h

# ---------------------------------------------------------------- 六档卡池

POOL = ["common", "rare", "super", "ultra", "secret", "mythic"]
POOL_CN = {"common": "平卡", "rare": "银字", "super": "面闪",
           "ultra": "金闪", "secret": "全息", "mythic": "圣髑闪"}

# ---------------------------------------------------------------- 行为稀有度

# 判定只用"这件事有多特别"，不用"花了多少钱"
BEHAVIOR = ["routine", "notable", "uncommon", "rare", "legendary"]
BEHAVIOR_CN = {"routine": "例行", "notable": "值得一提", "uncommon": "少见",
               "rare": "稀有", "legendary": "传说"}


def behavior_bucket(o: dict) -> str:
    """
    o 需要这些字段（全部来自官方 MCP，不含金额）：
      is_new_store  首次到访的门店
      is_new_sku    首次点的单品
      hour          下单小时 0-23
      is_holiday    当天是节日 / 活动日
      is_cross_city 与上一单不同城市
      is_first_day  门店开业首日 / 新品上市首日
      is_birthday   生日当天
    """
    score = 0
    if o.get("is_first_day"):   score += 4          # 开业首日 / 新品首日
    if o.get("is_birthday"):    score += 4          # 生日当天
    if o.get("is_cross_city"):  score += 2          # 跨城朝圣
    if o.get("is_holiday"):     score += 1
    if o.get("is_new_sku"):     score += 1
    if o.get("is_new_store"):   score += 1
    hour = o.get("hour", 12)
    if 3 <= hour <= 5:          score += 3          # 凌晨三点到五点
    elif hour >= 22 or hour <= 6: score += 1        # 夜祷 / 晨祷
    elif 14 <= hour <= 16:      score += 1          # 午后三点（申时经）

    if score >= 6:  return "legendary"
    if score >= 4:  return "rare"
    if score >= 2:  return "uncommon"
    if score >= 1:  return "notable"
    return "routine"


# ---------------------------------------------------------------- 权重表

#          common  rare  super  ultra  secret  mythic
WEIGHTS = {
    "routine":   [760,  170,   50,    14,     5,     1],
    "notable":   [640,  220,   95,    32,    10,     3],
    "uncommon":  [500,  250,  150,    70,    24,     6],
    "rare":      [360,  250,  200,   120,    55,    15],
    "legendary": [200,  230,  240,   180,   110,    40],
}
# 保底：连续 N 抽都没出 ultra 及以上，第 N+1 抽强制抬权
PITY_N = 12


def _apply_pity(w, pity):
    """pity = 连续未出 ultra+ 的次数"""
    if pity < PITY_N:
        return w
    boost = 6.0 if pity < PITY_N + 4 else 20.0
    out = list(w)
    out[0] = int(out[0] / boost)
    out[1] = int(out[1] / (boost / 2))
    out[3] = int(out[3] * boost)
    out[4] = int(out[4] * boost)
    out[5] = int(out[5] * boost)
    return out


# ---------------------------------------------------------------- 抽取

SALT_VERSION = "draw-v1"


def _apply_piety(w, piety_pct):
    """
    虔诚度不直接给卡，只提高"出好卡的概率"。
    这是"努力而非运气"和"盲盒感"能共存的地方：
      长期地位 -> 更高概率；但每一次仍然要抽。
    """
    mult = 1.0 + (piety_pct - 0.5) * 1.2      # 0.4 ~ 1.6
    out = list(w)
    for i in (3, 4, 5):
        out[i] = max(1, int(out[i] * mult))
    return out


def draw(order_id: str, user_salt: str, o: dict, pity: int = 0,
         piety_pct: float = 0.5) -> dict:
    """
    返回这一抽的结果。同输入永远同输出。
    pity 由客户端本地维护（连续未出 ultra+ 的计数），不上传。
    piety_pct 只调整权重，不直接决定稀有度。
    """
    bucket = behavior_bucket(o)
    w = _apply_piety(_apply_pity(WEIGHTS[bucket], pity), piety_pct)
    total = sum(w)
    x = h(order_id, user_salt, SALT_VERSION, bucket, pity) % total
    for i, wi in enumerate(w):
        if x < wi:
            rank = POOL[i]
            break
        x -= wi
    else:
        rank = POOL[0]

    return {
        "rank": rank,
        "rank_cn": POOL_CN[rank],
        "tier": i,
        "behavior": bucket,
        "behavior_cn": BEHAVIOR_CN[bucket],
        "pity_hit": pity >= PITY_N,
        "anim": min(3, max(0, i - 1)),
        "verify": verify_code(order_id, user_salt),
        "odds": [round(wi / total * 100, 2) for wi in w],
    }


def verify_code(order_id: str, user_salt: str, n: int = 5) -> str:
    """卡面右下角那串验真码：别人拿订单号能复算出同一串，伪造不出来"""
    alpha = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    v = h(order_id, user_salt, "verify")
    return "".join(alpha[(v >> (5 * k)) % len(alpha)] for k in range(n))


def odds_table():
    print(f"{'行为':<10}" + "".join(f"{POOL_CN[p]:>9}" for p in POOL))
    for b in BEHAVIOR:
        tot = sum(WEIGHTS[b])
        row = "".join(f"{w / tot * 100:8.2f}%" for w in WEIGHTS[b])
        print(f"{BEHAVIOR_CN[b]:<10}" + row)


if __name__ == "__main__":
    odds_table()
    print()
    demo = {"hour": 2, "is_new_sku": True, "is_cross_city": True}
    print("示例：凌晨 2 点 · 跨城 · 新品首点 ->",
          draw("A2026031102143902", "salt-88231", demo))
    print("同一单再算一遍   ->", draw("A2026031102143902", "salt-88231", demo)["rank"])
    print("换一个用户盐     ->", draw("A2026031102143902", "salt-10427", demo)["rank"])
