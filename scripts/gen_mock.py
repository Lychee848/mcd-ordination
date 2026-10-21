#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_mock.py —— 生成 data/mock/ 下的示例人设与人群样本

为什么要有 mock：
  1. 评委 clone 下来必须能 30 秒看到卡，不能要求他先申请 Token（这是同类作品 7/7 全 0 星的死因）。
  2. 回归测试需要固定输入：同一份 mock 必须永远产出同一张卡。
  3. 真人数据包含位置与时间，不可能进仓库。

生成的三份人设刻意覆盖三个极端：夜祷老客 / 跨城巡礼者 / 刚入门。
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "mock"
NUT = json.loads((ROOT / "data" / "nutrition.json").read_text(encoding="utf-8"))
SKUS = [(k, v["name"]) for k, v in NUT.items() if not k.startswith("_")]

# 权重：主力单品 + 长尾
WEIGHT = {"M001": 40, "M004": 26, "M011": 12, "M002": 8, "M005": 6,
          "M006": 4, "M007": 3, "M003": 1}

STORES = {
    "深圳": [("SZ-0412", "深圳华强北店"), ("SZ-0231", "深圳车公庙店"),
             ("SZ-0775", "深圳南山书城店")],
    "成都": [("CD-0088", "成都春熙路店"), ("CD-0102", "成都天府三街店")],
    "哈尔滨": [("HRB-0031", "哈尔滨中央大街店")],
    "重庆": [("CQ-0044", "重庆解放碑店"), ("CQ-0051", "重庆观音桥店")],
    "西安": [("XA-0019", "西安钟楼店")],
    "广州": [("GZ-0107", "广州天河城店"), ("GZ-0112", "广州北京路店")],
    "武汉": [("WH-0022", "武汉江汉路店"), ("WH-0030", "武汉光谷店")],
    "长沙": [("CS-0008", "长沙五一广场店")],
    "南京": [("NJ-0045", "南京新街口店")],
}


def gen(profile: str, *, uid: str, city: str, n: int, hours: list,
        purity_sku: str, purity: float, store_pool: list, city_pool: list,
        birthday: str, tries: int, wins: int, issued: int, used: int,
        expiring: int, seed: int) -> dict:
    rnd = random.Random(seed)
    now = datetime(2026, 10, 18, 20, 0, 0)
    orders = []
    for i in range(n):
        # 时间：越近越密
        back = int((rnd.random() ** 1.6) * 365)
        day = now - timedelta(days=back)
        hour = rnd.choice(hours)
        at = day.replace(hour=hour, minute=rnd.randrange(60), second=0)
        cu = rnd.choice(city_pool)
        sid, sname = rnd.choice(STORES[cu]) if cu in STORES else ("XX-0001", "示例门店")
        if cu == city:
            sid, sname = rnd.choice(STORES.get(city, [("XX-0001", "示例门店")]))

        items = []
        if rnd.random() < purity:
            sku, name = purity_sku, NUT[purity_sku]["name"]
            items.append({"sku": sku, "name": name, "qty": 1,
                          "unitCents": 2250 if sku == "M001" else 1300})
        else:
            picks = rnd.sample(SKUS, k=min(3, len(SKUS)))
            for sku, name in picks:
                items.append({"sku": sku, "name": name, "qty": 1,
                              "unitCents": 900 + rnd.randrange(1800)})

        orders.append({
            "orderId": f"{profile[:2].upper()}{at:%Y%m%d%H%M}{i:04d}",
            "storeId": sid, "storeName": sname, "city": cu,
            "placedAt": at.isoformat(),
            "isHoliday": rnd.random() < 0.06,
            "isFirstDay": rnd.random() < 0.02,
            "items": items,
        })
    orders.sort(key=lambda o: o["placedAt"])

    return {
        "uid": uid,
        "profile": {"birthday": birthday, "city": city},
        "account": {"points": 1200 + seed % 800, "expiringPoints": expiring},
        "coupons": {"issued": issued, "used": used},
        "prizes": {"tries": tries, "wins": wins},
        "orders": orders,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    night = gen("night_owl", uid="u_night_owl", city="深圳", n=188,
                hours=[0, 1, 2, 2, 23, 23, 22, 12, 19], purity_sku="M001",
                purity=0.95, store_pool=[], city_pool=["深圳"],
                birthday="1996-04-12", tries=14, wins=0, issued=40, used=4,
                expiring=1200, seed=20260101)

    pilgrim = gen("pilgrim", uid="u_pilgrim", city="成都", n=412,
                  hours=[7, 8, 11, 12, 12, 13, 18, 19, 21], purity_sku="M004",
                  purity=0.28, store_pool=[], city_pool=["成都", "重庆", "西安"],
                  birthday="1991-11-03", tries=27, wins=3, issued=60, used=59,
                  expiring=40, seed=20260202)

    beginner = gen("beginner", uid="u_beginner", city="哈尔滨", n=9,
                   hours=[7, 7, 8, 12, 19], purity_sku="M006",
                   purity=0.66, store_pool=[], city_pool=["哈尔滨"],
                   birthday="2003-07-21", tries=1, wins=0, issued=3, used=3,
                   expiring=0, seed=20260303)

    for name, data in (("night_owl", night), ("pilgrim", pilgrim), ("beginner", beginner)):
        (OUT / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{name}.json  orders={len(data['orders'])}")

    # 人群样本：只放四项指标，不含任何可反查字段
    rnd = random.Random(7)
    cohort = {"orders_per_year": [], "stores": [], "purity": [], "night": []}
    for _ in range(300):
        cohort["orders_per_year"].append(int(max(1, rnd.gauss(26, 20))))
        cohort["stores"].append(int(max(1, rnd.gauss(9, 8))))
        cohort["purity"].append(round(min(1, max(0, rnd.gauss(0.36, 0.19))), 3))
        cohort["night"].append(round(min(1, max(0, rnd.gauss(0.19, 0.15))), 3))
    (OUT / "cohort.json").write_text(json.dumps(cohort, indent=0), encoding="utf-8")
    print("cohort.json  n=300")


if __name__ == "__main__":
    main()
