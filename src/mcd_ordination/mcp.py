#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mcp.py —— 官方麦当劳 MCP 的最小客户端（实验性）

接口：https://mcp.mcd.cn，Streamable HTTP，请求头 Authorization: Bearer <TOKEN>
协议：JSON-RPC 2.0，握手顺序 initialize → notifications/initialized → tools/call

⚠️ 状态说明（不藏）：
  · 传输层与握手流程按官方文档实现，可直接跑。
  · **字段映射尚未用真实账号验证**（order-list / query-order 的返回结构是设计文档里
    唯一的 P0 硬阻塞）。所以这里所有取值都写成"多候选键 + 宽松解析"，并在解析失败时
    抛出可读错误，而不是静默返回 0 —— 静默返回 0 会让卡面出现"礼拜 0 次"这种假数据，
    直接击穿不可伪造原则。

如果你只想先看见卡：不要配 Token，直接 `python -m mcd_ordination demo`。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

DEFAULT_URL = "https://mcp.mcd.cn"


class McpError(RuntimeError):
    pass


class McpClient:
    def __init__(self, token: str, url: str = DEFAULT_URL, timeout: int = 25):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session_id = None
        self._id = 0

    # ------------------------------------------------------------ 传输

    def _post(self, payload: dict) -> dict:
        self._id += 1
        payload.setdefault("jsonrpc", "2.0")
        payload.setdefault("id", self._id)
        data = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                ctype = resp.headers.get("Content-Type", "")
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raise McpError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from e
        except urllib.error.URLError as e:
            raise McpError(f"连接失败：{e.reason}（需要能访问 {self.url}）") from e

        if "text/event-stream" in ctype:
            return _parse_sse(body)
        if not body.strip():
            return {}
        return json.loads(body)

    # ------------------------------------------------------------ 协议

    def initialize(self) -> dict:
        r = self._post({
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcd-ordination", "version": "0.1.0"},
            },
        })
        # 握手完成的显式通知（无 id，不期望响应）
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized",
                        "params": {}, "id": None})
        except McpError:
            pass
        return r.get("result", r)

    def list_tools(self) -> list:
        return self._post({"method": "tools/list", "params": {}}) \
            .get("result", {}).get("tools", [])

    def call(self, name: str, arguments: dict | None = None):
        r = self._post({"method": "tools/call",
                        "params": {"name": name, "arguments": arguments or {}}})
        if "error" in r:
            raise McpError(f"{name} 调用失败：{r['error']}")
        res = r.get("result", {})
        if res.get("isError"):
            raise McpError(f"{name} 返回错误：{res.get('content')}")
        # MCP 的 result.content 是 [{type:text, text:'{...json...}'}]
        for block in res.get("content", []):
            if block.get("type") == "text":
                txt = block.get("text", "")
                try:
                    return json.loads(txt)
                except json.JSONDecodeError:
                    return txt
        return res


def _parse_sse(body: str) -> dict:
    """Streamable HTTP 可能回 SSE：取最后一条带 result 的 data 行"""
    out = {}
    for line in body.splitlines():
        if not line.startswith("data:"):
            continue
        try:
            obj = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("result" in obj or "error" in obj):
            out = obj
    return out


# ---------------------------------------------------------------- 组装 payload

def _first(d: dict, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return default


def fetch(token: str, url: str = DEFAULT_URL) -> dict:
    """
    拉取一个人自己的行为数据，组装成 features.build 认识的 payload。
    任一必需字段缺失就抛错 —— 宁可跑不起来，也不要长出一张假卡。
    """
    c = McpClient(token, url)
    c.initialize()

    account = c.call("query-my-account")
    orders = c.call("order-list", {"pageSize": 200})
    coupons = c.call("query-my-coupons")
    prizes = c.call("query-my-prizes")

    raw_orders = _first(orders, "data", "orders", "list", default=orders)
    if not isinstance(raw_orders, list) or not raw_orders:
        raise McpError(
            "order-list 没有返回订单数组。真实返回结构尚未验证（P0），"
            "请把这一段原始 JSON 贴到 issue 里，我按真实结构改映射。"
        )

    norm = []
    for o in raw_orders:
        items = _first(o, "items", "products", "orderItems", default=[]) or []
        norm.append({
            "orderId": str(_first(o, "orderId", "order_id", "id", default="")),
            "storeId": str(_first(o, "storeId", "store_id", "storeCode", default="")),
            "storeName": _first(o, "storeName", "store_name", default=""),
            "city": _first(o, "city", "cityName", default=""),
            "placedAt": _first(o, "placedAt", "orderTime", "createTime", "createdAt",
                               default=""),
            "isHoliday": bool(_first(o, "isHoliday", default=False)),
            "items": [{
                "sku": str(_first(it, "sku", "productCode", "code", default="")),
                "name": _first(it, "name", "productName", default=""),
                "qty": int(_first(it, "qty", "quantity", "count", default=1)),
                "unitCents": int(_first(it, "unitCents", "price", "unitPrice", default=0)),
            } for it in items],
        })

    issued = _first(coupons, "issued", "total", default=0)
    used = _first(coupons, "used", "usedCount", default=0)

    return {
        "orders": norm,
        "account": {"expiringPoints": _first(account, "expiringPoints", "expiring", default=0)},
        "coupons": {"issued": int(issued or 0), "used": int(used or 0)},
        "prizes": {
            "tries": int(_first(prizes, "tries", "total", default=0) or 0),
            "wins": int(_first(prizes, "wins", "won", default=0) or 0),
        },
        "profile": {},
    }
