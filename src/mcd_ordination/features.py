#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
features.py —— 把「麦当劳用户行为」归一化成一份特征向量

整条流水线只有这一个入口。卡面、教阶、教义摘录、暗号、抽卡全部读它，
所以任何一处口径不一致，都会立刻在卡面上自相矛盾（P1 不可伪造会当场破功）。

输入：官方 MCP 的原始返回（order-list / query-order / query-my-account /
      query-my-coupons / query-my-prizes / query-my-stores）
输出：一个扁平 dict，键名见 FEATURE_DOC

明确排除：金额不进虔诚公式。avg_ticket 只保留给「苦修士 / 铺张派」两条
教义摘录用，且不进加权（见设计文档 §3.3 的两条刻意决定）。
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------- 路径

PKG_DIR = Path(__file__).resolve().parent
REPO_DIR = PKG_DIR.parent.parent
DATA_DIR = REPO_DIR / "data"
MOCK_DIR = DATA_DIR / "mock"


FEATURE_DOC = {
    "total_orders":     "近一年礼拜次数（判决与暗号都用它）",
    "orders_per_year":  "同 total_orders，进虔诚公式的那一项",
    "night_ratio":      "22:00–05:59 订单占比 —— 夜祷率",
    "breakfast_ratio":  "06:00–09:59 订单占比 —— 晨祷率",
    "store_count":      "去重门店数 —— 朝圣门店数",
    "cross_city":       "去重城市数 —— 走过几座城",
    "purity":           "TOP1 单品占比 —— 信仰纯度",
    "top_item":         "TOP1 单品名 —— 本命圣物",
    "top_sku":          "TOP1 单品 SKU（查营养用）",
    "avg_ticket":       "客单价（只给苦修士/铺张派用，不进虔诚公式）",
    "coupon_use_rate":  "券使用率（只给恩宠典用，不进虔诚公式）",
    "expiring_points":  "即将过期积分",
    "lottery_tries":    "抽奖次数",
    "lottery_wins":     "中奖次数",
    "days_since_last":  "距上次礼拜天数",
    "years_since_first": "受洗第几年",
    "birthday_today":   "今天是否生日（解锁 T1 请求档）",
    "home_store":       "最常去的门店名",
    "home_city":        "最常去的城市",
    "first_order_at":   "受洗日",
    "last_order_at":    "最后一次礼拜时间",
}


# ---------------------------------------------------------------- 读取

def load_mock(profile: str = "night_owl") -> dict:
    """读取 data/mock/<profile>.json。仓库里自带三份人设，保证零 Key 可跑。"""
    path = MOCK_DIR / f"{profile}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"找不到人设 {profile!r}，可用：" +
            ", ".join(sorted(p.stem for p in MOCK_DIR.glob("*.json")
                             if p.stem != "cohort"))
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_cohort() -> dict | None:
    """人群样本（用于贝叶斯收缩求百分位）。没有就返回 None，走纯先验。"""
    path = MOCK_DIR / "cohort.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 归一化

def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def build(payload: dict, now: datetime | None = None) -> dict:
    """
    payload 结构（与官方 MCP 字段一一对应，见 README §数据契约）：
      {
        "orders":   [...],          # order-list 的条目
        "account":  {...},          # query-my-account
        "coupons":  {"issued": n, "used": n},
        "prizes":   {"tries": n, "wins": n},
        "profile":  {"birthday": "1998-10-21"}
      }
    """
    orders = payload.get("orders") or []
    account = payload.get("account") or {}
    coupons = payload.get("coupons") or {}
    prizes = payload.get("prizes") or {}
    profile = payload.get("profile") or {}

    if not orders:
        raise ValueError("orders 为空：没有行为数据就长不出卡面，这不是可以兜底的情况")

    stamps = sorted(_parse(o["placedAt"]) for o in orders)
    first, last = stamps[0], stamps[-1]
    now = now or last

    horizon = now - timedelta(days=365)
    recent = [o for o in orders if _parse(o["placedAt"]) >= horizon]

    hours = [_parse(o["placedAt"]).hour for o in recent]
    night = sum(1 for h in hours if h >= 22 or h <= 5)
    breakfast = sum(1 for h in hours if 6 <= h <= 9)

    sku_counter = Counter()
    item_name = {}
    for o in recent:
        for it in o.get("items", []):
            sku_counter[it["sku"]] += it.get("qty", 1)
            item_name[it["sku"]] = it.get("name", it["sku"])

    total_items = sum(sku_counter.values()) or 1
    top_sku = sku_counter.most_common(1)[0][0] if sku_counter else ""
    purity = (sku_counter[top_sku] / total_items) if top_sku else 0.0

    stores = {o["storeId"] for o in recent}
    cities = {o.get("city") or o["storeId"][:2] for o in recent}
    store_counter = Counter(o["storeId"] for o in recent)
    home_id = store_counter.most_common(1)[0][0] if store_counter else ""
    home_store = next((o.get("storeName", home_id) for o in recent
                       if o["storeId"] == home_id), home_id)
    home_city = next((o.get("city", "") for o in recent
                      if o["storeId"] == home_id), "")

    cents = [sum(it.get("unitCents", 0) * it.get("qty", 1) for it in o.get("items", []))
             for o in recent]
    avg_ticket = round(sum(cents) / len(cents) / 100, 2) if cents else 0.0

    issued = coupons.get("issued", 0)
    coupon_use_rate = (coupons.get("used", 0) / issued) if issued else 1.0

    birthday = profile.get("birthday")
    birthday_today = bool(birthday) and _parse(f"{now.date()}T00:00:00+08:00").strftime("%m-%d") \
        == birthday[5:10]

    return {
        "total_orders": len(recent),
        "orders_per_year": len(recent),
        "night_ratio": round(night / max(1, len(recent)), 3),
        "breakfast_ratio": round(breakfast / max(1, len(recent)), 3),
        "store_count": len(stores),
        "cross_city": len(cities),
        "purity": round(purity, 3),
        "top_item": item_name.get(top_sku, "本命圣物"),
        "top_sku": top_sku,
        "avg_ticket": avg_ticket,
        "coupon_use_rate": round(coupon_use_rate, 3),
        "expiring_points": int(account.get("expiringPoints", 0)),
        "lottery_tries": int(prizes.get("tries", 0)),
        "lottery_wins": int(prizes.get("wins", 0)),
        "days_since_last": max(0, (now.date() - last.date()).days),
        "years_since_first": max(0, (now.date() - first.date()).days / 365.25),
        "birthday_today": birthday_today,
        "home_store": home_store,
        "home_city": home_city,
        "first_order_at": first.isoformat(),
        "last_order_at": last.isoformat(),
    }


def order_flags(order: dict, history: list, now: datetime | None = None) -> dict:
    """
    给抽卡器算「这一单有多特别」。只判性质，不看金额。
    见 gacha.behavior_bucket 的入参说明。
    """
    at = _parse(order["placedAt"])
    prev = [o for o in history if _parse(o["placedAt"]) < at]
    prev_skus = {it["sku"] for o in prev for it in o.get("items", [])}
    prev_stores = {o["storeId"] for o in prev}
    prev_city = _parse(prev[-1]["placedAt"]) if prev else None
    last_city = next((o.get("city") for o in reversed(prev)), None)

    return {
        "hour": at.hour,
        "is_new_store": order["storeId"] not in prev_stores,
        "is_new_sku": any(it["sku"] not in prev_skus for it in order.get("items", [])),
        "is_cross_city": bool(prev_city and last_city and order.get("city")
                              and order.get("city") != last_city),
        "is_holiday": bool(order.get("isHoliday")),
        "is_first_day": bool(order.get("isFirstDay")),
        "is_birthday": bool(order.get("isBirthday")),
    }
