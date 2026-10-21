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

    def make(kind, allow_t1=True, story=True):
        return SG.compile_sign(feats, uid, date.today(), menu,
                               grace_id=top["id"], grace_creed=top["creed"],
                               kind=kind, allow_t1=allow_t1,
                               story=SG.load_story(uid) if story else None)

    g = make("greet")

    def collect(soft: bool, want: int = 3):
        """按不同的下单时间扫出互不相同的句子（同单必同句，换单才换句）"""
        seen, out = set(), []
        for i in range(200):
            f2 = dict(feats, last_order_at=f"2026-{1 + i % 9:02d}-{1 + i % 27:02d}"
                                             f"T{i % 24:02d}:{(i * 7) % 60:02d}:00+08:00")
            s2 = SG.compile_sign(f2, uid, date.today(), menu,
                                 grace_id=top["id"], grace_creed=top["creed"],
                                 kind="ask", soft=soft, story=SG.load_story(uid))
            if s2["ask"] in seen:
                continue
            seen.add(s2["ask"])
            out.append(s2)
            if len(out) >= want:
                break
        return out

    asks_t1 = collect(soft=False, want=3)
    asks_t0 = collect(soft=True, want=2)
    a1 = asks_t1[0]
    s1 = make("story")
    SG.append_story(uid, s1, "灯是给晚归的人留的")
    s2 = make("story")

    md = f"""# 暗号样例（三种体裁 · 真实输出）

> 由 `python scripts/gen_sign_examples.py` 生成，不是手抄。
> 「今日圣体」随当天在售菜单变化，所以这一行会和你在本地跑出来的略有不同；
> 短码由卡面 7 项公开量决定，同一份数据永远算出同一串。
> **短码不进备注正文**（店员看不懂），它印在卡面右下角、也出现在社交版首行。

人设：`night_owl`（深圳，夜祷为主，执事 Diaconus）。备注栏上限按 `REMARK_LIMIT = 60` 计算。

## 1. 问候 `greet`（{g['len']} 字）

什么都不求，只做人际连接：

```text
{g['short']}
```

## 2. 请求 `ask` · 默认（T1，真要一块鸡块）（{asks_t1[0]['len']} 字）

主句必须让人**一眼知道你要什么**，笑点加在"要什么"后面，而不是替代它：

```text
{chr(10).join(a['short'] for a in asks_t1)}
```

## 3. 请求 `ask` · `--soft`（T0，只要一个动作）（{asks_t0[0]['len']} 字）

不想开口要实物时降级到这一档：请对方写一句、画个勾，成本为零：

```text
{chr(10).join(a['short'] for a in asks_t0)}
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

社交版（发帖用，带上一章的那句；短码在这里作为署名）：

```text
{s2['long']}
```
"""
    out = ROOT / "docs" / "samples" / "sign_examples.md"
    out.write_text(md, encoding="utf-8")
    print("wrote", out.relative_to(ROOT))

if __name__ == "__main__":
    main()
