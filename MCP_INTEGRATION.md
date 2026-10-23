# 麦当劳 MCP 集成说明

本文说明本项目**实际调用了哪些麦当劳 MCP Server 与 Tool、按什么顺序调用、换来了什么业务价值**。
只写已经写进代码的部分；未经真实账号验证的地方会明确标注，不把"设计"写成"已实现"。

---

## 1. 接入的 Server

| 项 | 值 |
|---|---|
| Server | 麦当劳中国官方托管 MCP Server（非自建、非第三方代理） |
| 接入地址 | `https://mcp.mcd.cn`（可用环境变量 `MCD_MCP_URL` 覆盖） |
| 传输方式 | Streamable HTTP，JSON-RPC 2.0 |
| 鉴权 | `Authorization: Bearer <用户自己的 MCP Token>`，只从环境变量 `MCD_MCP_TOKEN` 读取 |
| 握手顺序 | `initialize` → `notifications/initialized` → `tools/call` |
| 客户端实现 | [`src/mcd_ordination/mcp.py`](src/mcd_ordination/mcp.py)，标准库 `urllib`，无第三方依赖 |

我们只接入**官方 Server**。没有自建中间层、没有缓存他人数据、没有把 Token 写进仓库或日志。

---

## 2. 调用的 Tool

| # | Tool | 取什么字段 | 用在哪里 | 状态 |
|---|---|---|---|---|
| 1 | `query-my-account` | 入会时间、生日、账户标识 | 九阶品秩的"入门第 N 年"、生日加成 | 已接，字段待真机核对 |
| 2 | `order-list` | 订单时间、门店、城市、单品、数量 | 行为向量的主干：礼拜次数、时辰分布、门店数、跨城数、信仰纯度 | 已接，**返回结构待真机验证** |
| 3 | `query-order` | 单笔订单详情 | 稀有度判定（是否节日/首店/新品首日） | 已接，同上 |
| 4 | `query-my-coupons` | 券数量、使用情况 | 教义摘录「散财异端 / 神恩会计师」 | 已接 |
| 5 | `query-my-prizes` | 抽奖次数、中奖次数 | 教义摘录「未被拣选者」 | 已接 |
| 6 | `list-nutrition-foods` | 能量/蛋白/脂肪/碳水/钠/钙 | 食物卡的六维条形图，**一克都不编** | 已接，字段已确认 |
| 7 | `query-nearby-stores` | 附近门店与门店信息 | 地点卡、门店覆盖度 | 已接 |
| 8 | `campaign-calendar` | 活动日、节日 | 节庆暗号的"今日圣体"、稀有度加成 | 已接 |
| 9 | `create-order` | `inputSchema` 里是否存在备注字段 | 暗号写入订单备注的**能力探测**（不代下单） | 只读探测，不调用下单 |

**没做的事，也说清楚：**

- 不调用 `create-order` 真正下单，不调用任何支付相关接口；
- 不调用 `delivery-*`（配送地址）相关工具，也不保存地址；
- 不碰商城订单 `mall-*`。

---

## 3. 调用流程

```text
用户授权（贴自己的 Token，仅存于环境变量）
        │
        ├─ query-my-account ──┐
        ├─ order-list ────────┤
        ├─ query-my-coupons ──┼─→ features.build()  ──→ 行为向量（20 项标量）
        ├─ query-my-prizes ───┤        │
        ├─ query-nearby-stores┤        ├─→ piety.py   → 九阶品秩 + 光环
        └─ campaign-calendar ─┘        ├─→ canon.py   → 教义摘录（0–3 条信条）
                                       ├─→ sign.py    → 专属暗号（备注版 / 社交版）
                                       └─→ gacha.py   → 稀有度（可复算）
                                                    │
                            list-nutrition-foods ───┴─→ 食物卡六维
                                                    │
                                            deck.py → 渲染数据
                                                    │
                            render_svg.py（零依赖） / render_png.py（成品卡）
                                                    │
                                            create-order.inputSchema 探测
                                                    │
                                        有备注字段 → 自动写入；无 → 手动复制
```

两个关键设计：

1. **只读优先**：前 8 步全是只读查询，写操作只有最后可选的一步，且必须先探测字段是否存在。
2. **失败即报错**：任一必需字段缺失就抛可读错误，绝不静默返回 0——否则会生成"礼拜 0 次"的假卡，直接击穿项目的"不可伪造"原则。

---

## 4. 业务价值

| 价值 | 说明 |
|---|---|
| 把"消费记录"翻译成"可表达的东西" | 用户拿到的不是报表，而是一张能发出去的卡和一句能写进备注的暗号 |
| 让订单数据产生线下互动 | 暗号进备注 → 店员回应 → 用户回报 → 友好门店地图，数据回流但不含个人信息 |
| 数据可对账 | 卡面每个数字都能追溯到某一次 `order-list`/`list-nutrition-foods` 的返回；短码由 7 项公开量复算 |
| 不诱导消费 | 金额、客单价、金额增长**不进任何公式**；稀有度只看"这一单有多特别" |
| 零 Key 也能用 | 没有 Token 时走本地合成人设，完整卡面照样生成（评审无需申请账号即可验收） |

---

## 5. 数据与隐私

- Token 只从环境变量读，不落盘、不进仓库、不进日志；
- 所有计算在本机完成，**不上传任何订单、账户或位置数据**；
- 仓库内只有合成人设（`data/mock/`），没有任何真实账号数据；
- 接龙账本只存本地 `~/.mcd-ordination/`，记录章节与店员写回的一句话，不含个人信息。

---

## 6. 复现方式

```bash
# 不配 Token：用合成人设看完整效果（评审推荐路径）
pip install -e .
python -m mcd_ordination demo

# 配自己的 Token：拉真实数据
export MCD_MCP_TOKEN="<你自己的 Token>"
python -m mcd_ordination demo --mcp     # sign / order 子命令同样支持 --mcp
```

---

## 7. 已知限制（不藏）

1. `mcp.mcd.cn` 的**可达性与鉴权头格式已验证**：用一个无效 Token 请求，服务端返回 `HTTP 401 当前鉴权码不存在或已失效`，说明地址、传输方式、`Authorization: Bearer` 头都能走到业务层；有效 Token 下的工具返回尚未验证。
2. `order-list` / `query-order` 的**真实返回结构尚未用真实账号逐字段核对**。`mcp.py` 采用"多候选键 + 宽松解析"，解析失败会抛错并提示贴原始 JSON，不猜、不填假值。
3. `create-order` 是否支持备注字段，取决于运行时 `tools/list` 返回的 `inputSchema`；不支持时只生成可复制文本，界面明确说明"未写入"。
4. `query-meals`（当前在售菜单）未在代码中强依赖：拿不到时，"今日圣体"退化为不含单品名的通用句。
