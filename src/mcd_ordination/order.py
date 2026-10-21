#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
order.py —— 把暗号挂到「这一单」的备注上

难点不在拼字符串，在于：**官方 create-order 到底有没有备注字段，我们不确定。**
所以这里不做假设，而是做两步：

  1. 能力探测：读 tools/list 里 create-order 的 inputSchema，找备注类字段
     （remark / note / comment / memo / instruction …）以及它的 maxLength
  2. 按探测结果二选一：
     · 有字段 → 直接写进 payload，用户勾选即生效（auto 模式）
     · 没有   → 生成一段可一键复制的文本 + 三步指引（manual 模式），
                绝不假装"已经帮你写进去了"

宁可承认限制，也不要让用户以为备注已经进了订单 —— 那会直接击穿"不可伪造"。
"""
from __future__ import annotations

from datetime import datetime

# 备注字段在各个 API 里的常见叫法，按优先级排
REMARK_KEYS = ("remark", "remarks", "note", "notes", "comment", "comments",
               "memo", "instruction", "instructions", "customerNote",
               "orderRemark", "buyerMessage", "备注")

DEFAULT_STEPS = [
    "复制下面这句暗号",
    "在官方 App 结算页找到「备注 / 口味偏好」，粘贴进去",
    "下单后凭短码回报，帮这张「友好门店地图」多一个点",
]


def probe(tools: list) -> dict:
    """
    tools: mcp.list_tools() 的返回
    返回 {"field": 字段名或 None, "max_len": int 或 None, "checked": bool}
    """
    for t in tools or []:
        name = t.get("name") or t.get("tool") or ""
        if "create-order" not in name and "create_order" not in name:
            continue
        props = ((t.get("inputSchema") or t.get("input_schema") or {})
                 .get("properties") or {})
        for k in REMARK_KEYS:
            if k in props:
                spec = props[k] or {}
                return {"field": k, "max_len": spec.get("maxLength"),
                        "checked": True, "tool": name}
        return {"field": None, "max_len": None, "checked": True, "tool": name}
    return {"field": None, "max_len": None, "checked": False, "tool": None}


def build_draft(orders: list, features: dict, dining: str = "pickup") -> dict:
    """用最近一单做骨架：同一家店、同样的东西，备注换成你今天的暗号"""
    if not orders:
        raise ValueError("没有订单可复用")
    last = orders[-1]
    items = [{"sku": it["sku"], "qty": it.get("qty", 1)} for it in last.get("items", [])]
    return {
        "storeId": last["storeId"],
        "storeName": last.get("storeName", ""),
        "diningType": dining,
        "items": items,
        "_sourceOrder": last["orderId"],
    }


def attach(draft: dict, sign: dict, caps: dict | None = None) -> dict:
    """
    返回一个可直接展示的结果字典。
    mode = auto   -> payload 里已经带 remark 字段
    mode = manual -> payload 不含 remark，另给一段复制文本与三步指引
    """
    caps = caps or {"field": None, "max_len": None, "checked": False}
    text = sign["short"]
    max_len = caps.get("max_len")
    clipped = False
    if max_len and len(text) > int(max_len):
        text = text[: int(max_len) - 1] + "…"
        clipped = True

    if caps.get("field"):
        payload = dict(draft)
        payload[caps["field"]] = text
        return {
            "mode": "auto", "field": caps["field"], "text": text,
            "payload": payload, "clipped": clipped, "steps": [],
            "checked": True,
        }

    return {
        "mode": "manual", "field": None, "text": text,
        "payload": dict(draft), "clipped": clipped, "steps": DEFAULT_STEPS,
        "checked": caps.get("checked", False),
        "reason": ("create-order 的 inputSchema 里没有备注字段" if caps.get("checked")
                   else "还没探测过 create-order 的字段（未连 MCP）"),
        "at": datetime.now().isoformat(timespec="minutes"),
    }


def render(result: dict) -> str:
    """给终端看的版本"""
    lines = [f"备注文本（{len(result['text'])} 字）：", "  " + result["text"], ""]
    if result["mode"] == "auto":
        lines.append(f"已写入 create-order 的 `{result['field']}` 字段，勾选即生效。")
    else:
        lines.append(f"不能自动写入：{result.get('reason', '')}")
        lines.append("请按三步走：")
        for i, s in enumerate(result["steps"], 1):
            lines.append(f"  {i}. {s}")
    if result["clipped"]:
        lines.append("（已按字段 maxLength 截断，短码保留在末尾前）")
    return "\n".join(lines)
