#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
piety.py —— 修持百分位 → 九阶品秩

三项刻意决定（改一条就翻车，见设计文档 §3.3）：
  1. 金额类字段一律不进公式（客单价 / 累计金额 / 增长率）。
  2. 券使用率不进公式（它属于教义摘录，不属于虔诚）。
  3. 人群样本不足时向先验收缩，宁可"不太准"，也不假装精确。

输出里 **不带任何排名数字给前端**：卡面只印九阶名，不印百分位。
"""
from __future__ import annotations

import math
import statistics

PRIOR_N = 40.0

# 先验：无样本时的兜底分布（均来自公开可观察的量级，不是拍脑袋的"用户画像"）
PRIOR = {
    "orders_per_year": {"mu": 24.0,  "sigma": 18.0},
    "stores":          {"mu": 8.0,   "sigma": 7.0},
    "purity":          {"mu": 0.35,  "sigma": 0.18},
    "night":           {"mu": 0.18,  "sigma": 0.15},
}

# 四项加权。金额类刻意缺席。
PIETY_WEIGHTS = {
    "orders_per_year": 0.40,   # 你来得有多勤
    "stores":          0.25,   # 你走得有多远
    "purity":          0.20,   # 你有多专一
    "night":           0.15,   # 你守夜有多深
}

# 特征名 → 公式里的名字
_KEY_MAP = {
    "orders_per_year": "orders_per_year",
    "stores": "store_count",
    "purity": "purity",
    "night": "night_ratio",
}


def percentile(value: float, key: str, samples: list | None) -> float:
    """弱先验 + 收缩：n 小时信先验，n 大时信真实分布"""
    p = PRIOR[key]
    samples = samples or []
    if len(samples) < 2:
        mu, sd = p["mu"], p["sigma"]
    else:
        n = len(samples)
        w = n / (n + PRIOR_N)
        mu = w * statistics.mean(samples) + (1 - w) * p["mu"]
        sd = w * statistics.pstdev(samples) + (1 - w) * p["sigma"]
    sd = max(sd, 1e-6)
    z = (value - mu) / sd
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def piety(features: dict, cohort: dict | None = None) -> dict:
    """
    cohort: {"orders_per_year": [...], "stores": [...], "purity": [...], "night": [...]}
            没有就传 None（纯先验，README 里必须标注 n=0）
    """
    parts, total = {}, 0.0
    for key, w in PIETY_WEIGHTS.items():
        raw = features.get(_KEY_MAP[key], 0) or 0
        samp = (cohort or {}).get(key)
        p = percentile(float(raw), key, samp)
        parts[key] = {"value": raw, "pct": round(p, 4), "w": w}
        total += w * p
    return {
        "pct": round(total, 4),
        "parts": parts,
        "rank": rank_of(total),
        "n": len((cohort or {}).get("orders_per_year", []) or []),
    }


# ---------------------------------------------------------------- 九阶

# (下界, 教阶中文, 拉丁, 卡面主色, 光环, 头饰, 金属)
RANKS = [
    (0.995, "麦门在世", "Summus Maimen", "金",     "全幅圣光 + 彩窗", "三重冠",   "虹彩"),
    (0.970, "枢机主教", "Cardinalis",    "绛红",   "红金环 + 放射线", "红帽",     "金 + 绛红"),
    (0.900, "主教",     "Episcopus",     "紫",     "金环 + 多重同心环", "主教冠",  "金"),
    (0.800, "司铎",     "Presbyter",     "深蓝",   "完整金环 + 细射线", "无",      "银"),
    (0.650, "执事",     "Diaconus",      "青",     "分段（开口）金环", "无",       "银"),
    (0.500, "传道员",   "Praedicator",   "绿",     "分段（开口）金环", "无",       "黄铜"),
    (0.250, "门徒",     "Discipulus",    "灰",     "细金线圈",        "无",       "黄铜"),
    (0.100, "望教者",   "Catechumenus",  "浅灰",   "仅一道细弧",      "粗布头巾", "铁"),
    (0.000, "慕道者",   "Auditor",       "白",     "无",              "粗布头巾", "铁"),
]

LEVEL = {  # 卡面星级：1–9 星，与品秩一一对应
    "慕道者": 1, "望教者": 2, "门徒": 3, "传道员": 4, "执事": 5,
    "司铎": 6, "主教": 7, "枢机主教": 8, "麦门在世": 9,
}


def rank_of(pct: float) -> dict:
    for lo, cn, lat, color, halo, head, metal in RANKS:
        if pct >= lo:
            return {"cn": cn, "lat": lat, "color": color, "halo": halo,
                    "head": head, "metal": metal, "level": LEVEL[cn],
                    "lower": lo}
    return rank_of(0.0)


def explain(res: dict) -> str:
    """给 CLI / README 用的一行解释，不印百分位数字（§1.2 第 3 条）"""
    r = res["rank"]
    return f"你的修持轨迹指向「{r['cn']}」（{r['lat']}）· 光环：{r['halo']}"
