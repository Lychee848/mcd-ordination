#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把三种体裁的真实输出写进 docs/samples/sign_examples.md（可复现，别手抄）"""
import os
import tempfile
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mcd_ordination import canon as C, deck as D, features as F, piety as P, sign as SG

def main():
    tmp = tempfile.mkdtemp(prefix="mcdstory_")
    os.environ["MCD_STORY_DIR"] = tmp
    payload = F.load_mock("night_owl")
    feats = F.build(payload)
    uid = payload["uid"]
    pi = P.piety(feats, F.load_cohort())
    cr = C.faith_extract(feats, uid)
    top = cr["printed"][0]
    menu = [v["name"] for k, v in D.load_nutrition().items() if not k.startswith("_")]

    def make(kind, allow_t1=False, story=True):
        return SG.compile_sign(feats, uid, date.today(), menu,
                               grace_id=top["id"], grace_creed=top["creed"],
                               kind=kind, allow_t1=allow_t1,
                               story=SG.load_story(uid) if story else None)

    g = make("greet")
    a0 = make("ask")
    a1 = make("ask", allow_t1=True)
    s1 = make("story")
    SG.append_story(uid, s1, "灯是给晚归的人留的")
    s2 = make("story")

    md = f"""# 暗号样例（三种体裁 · 真实输出）

> 由 `python scripts/gen_sign_examples.py` 生成，不是手抄。
> 「今日圣体」随当天在售菜单变化，所以这一行会和你在本地跑出来的略有不同；
> 短码由卡面 7 项公开量决定，同一份数据永远算出同一串。

人设：`night_owl`（深圳，夜祷为主，执事 Diaconus）。备注栏上限按 `REMARK_LIMIT = 60` 计算。

## 1. 问候 `greet`（{g['len']} 字）

什么都不求，只做人际连接：

```text
{g['short']}
```

## 2. 请求 `ask` · T0 零成本（{a0['len']} 字）

默认档位，请求的是象征性动作：

```text
{a0['short']}
```

## 3. 请求 `ask` · T1 小成本（{a1['len']} 字）

只有用户显式勾选（或生日/里程碑/友好门店）才出现，且必须带免责句：

```text
{a1['short']}
```

## 4. 接龙 `story` · 第 1 章（{s1['len']} 字）

```text
{s1['short']}
```

## 5. 接龙 `story` · 第 2 章（{s2['len']} 字）

店员在袋上写了「灯是给晚归的人留的」，记进本地账本后重新编译：

```text
{s2['short']}
```

社交版（发帖用，带上一章的那句）：

```text
{s2['long']}
```
"""
    out = ROOT / "docs" / "samples" / "sign_examples.md"
    out.write_text(md, encoding="utf-8")
    print("wrote", out.relative_to(ROOT))

if __name__ == "__main__":
    main()
