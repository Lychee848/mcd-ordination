# 参赛提交清单

> 这个文件是给**你自己**看的操作手册，不是仓库正文。提交完成后可以删掉，或移入 `docs/`。

---

## 0. 三件事，按顺序做

1. 在 GitHub 建仓库 `mcd-ordination`（**Public**，不要勾模板、不要勾 README）。
2. 推上去（本目录**已经** `git init` 并有提交，分支就是 `main`，不要重复 init）。
3. 去赛事仓库提 Issue（第 3 节），标题与正文照抄。

**四个必备文件（缺一即失格，官方原文要求）**

| 文件 | 要求 | 本仓库 |
|---|---|---|
| `README.md` | 项目介绍 / 安装方法 / 使用示例 / **目标用户** | ✅ 四项齐全 |
| `CONTEST_DECLARATION.md` | **官方原文，一个字节都不能改** | ✅ 与官方文件 SHA256 一致 |
| `MCP_INTEGRATION.md` | 用了哪些 Server/Tool、调用流程、业务价值 | ✅ |
| 源代码 | 主体代码或可运行内容 | ✅ `src/` + `scripts/` |
| `workbuddy.md` | 参加 WorkBuddy 专项奖励时才需要（建议交，前 100 名可换 3000 积分） | ✅ 已备 |

> 报名窗口：**2026-10-25 23:59 截止**，10-26 00:00 采集排名。别卡点提。

---

## 1. 推仓库（三条命令）

```bash
cd mcd-ordination
git remote add origin https://github.com/Lychee848/mcd-ordination.git
git push -u origin main
```

推之前先确认工作区是干净的（应该没有任何输出）：

```bash
git status --short
```

常见两种失败：

| 报错 | 原因 | 处理 |
|---|---|---|
| `remote origin already exists` | 之前配过别的远端 | `git remote set-url origin <新地址>` |
| `Updates were rejected` | 建仓库时勾了 README/LICENSE | `git pull --rebase origin main` 后再 push |

体积参考：`.git` 约 45 MB、`assets/` 约 23 MB。首次 push 慢属于正常，之后只推增量。

---

## 2. 仓库设置（影响能不能被搜到，别跳过）

**About 栏（右上角齿轮）**

- Description：
  ```
  领取专属麦门暗号，找到你的麦乐鸡侠｜麦当劳用户行为 → 专属麦门卡证 + 可写进订单备注的暗号。零 Key 可跑。
  ```
- Website：填第 2.1 节生成的 Pages 地址（**别填无效链接**）
- Topics（GitHub 最多 20 个，按优先级）：
  ```
  mcp  mcdonalds  mcdonalds-mcp  workbuddy-skill  mcd
  generative-art  trading-card-game  python  pillow  svg
  llm  ai  prompt-engineering  data-visualization  privacy-first
  ```

> 依据：统计 744 个参赛仓库后发现，`workbuddy-skill` / `mcd` / `mcdonalds-mcp` 三个 topic 的星数中位数最高；
> `model-context-protocol` / `nutrition` / `meal-planner` 已经是红海，不建议占用 topic 位。

**社交预览图**：Settings → Social preview 上传 `docs/samples/three_personas.png`（1200×630 会自动裁切）。

### 2.1 开 GitHub Pages

1. GitHub → Settings → **Pages** → Source: *Deploy from a branch* → Branch `main`、目录 **`/ (root)`** → Save。
2. 等 1–2 分钟，访问 <https://Lychee848.github.io/mcd-ordination/>。
3. 把这个地址填回 About 的 Website。

**不用改任何代码。** 页面里的 GitHub 按钮会在运行时按当前域名反推仓库
（`xxx.github.io/mcd-ordination/` → `github.com/xxx/mcd-ordination`），所以忘了替换占位符也不会点错。

README 首屏的“在线试玩”链接已经写成 <https://Lychee848.github.io/mcd-ordination/>，无需再改。

### 2.2 上线后自查（30 秒）

| 检查 | 期望 |
|---|---|
| 首页三张卡是否显示 | 有图；若空白，多半是路径大小写或未 push `docs/` |
| 点“现场试”切人设/卡种/体裁 | 卡和图同步变，暗号可复制 |
| 右上 GitHub 按钮 | 指向 <https://github.com/Lychee848/mcd-ordination> |
| 手机打开 | 首屏能看到标题 + 一句话 + 卡（约一屏） |

---

## 3. 提 Issue（格式校验很严，逐字照抄）

仓库：<https://github.com/M-China/mcd-developer-innovation-challenge/issues/new>

### 标题

```
【参赛申请】麦门行传｜领取专属麦门暗号，找到你的麦乐鸡侠
```

### 正文（四行，**行与行之间不要空行**）

```text
【参赛申请】
项目名称：麦门行传（mcd-ordination）
项目地址：https://github.com/Lychee848/mcd-ordination
项目简介：麦门行传把「麦当劳用户行为」当作 prompt，产出两样东西：一套专属麦门卡证（九阶品秩、教义摘录、人物/食物/行为/地点四种版式的交换卡），和一枚只属于你的麦门暗号（问候、请求、接龙三种体裁）。暗号可一键写进订单备注：向店员求一件极小之物（上限一块麦乐鸡），或求取门店本就有的那卷传说的下一段（下次带来的是续篇）。卡面文字与数值全部由代码绘制，AI 只画画面；每个数字都可追溯到 MCP 返回，短码由 7 项公开量复算，他人可验证。金额不进任何公式，不代下单、不支付、不接触账号凭证；没有 Token 也能跑出完整卡面。在线试玩：https://Lychee848.github.io/mcd-ordination/
```

三条硬规则（官方 README 明确写了，踩了会被校验打回）：

1. **`【参赛申请】` 与 `项目名称` 之间不能空行**，字段与内容也写在同一行；
2. **项目地址必须是裸链接**，不能写成 `[仓库](https://...)` 这种 Markdown 链接；
3. 项目简介**不要换行**，一整段写完。

---

## 4. 提交前自检

```bash
# 0) 装包（editable，不产生第三方依赖）；不想装就在每条命令前加 PYTHONPATH=src
pip install -e .

# 1) 零依赖路径能跑（不装 Pillow 也得出完整 SVG）
python -m mcd_ordination demo --engine svg

# 2) 三种人设都能跑，且卡面不同
for p in night_owl pilgrim beginner; do python -m mcd_ordination demo --profile $p --engine svg; done

# 3) 暗号三种体裁都能出，且接龙能续章
python -m mcd_ordination sign --kind greet
python -m mcd_ordination sign --kind ask --allow-t1
python -m mcd_ordination sign --kind story --wrote "灯是给晚归的人留的"
python -m mcd_ordination sign --kind story      # 应变成第 2 章

# 3.5) 投稿：收一句、拒一句（拒的时候必须说明原因）
python -m mcd_ordination sign --add-ask "可否在袋上批注「已阅」，我回去好交差"
python -m mcd_ordination sign --add-ask "给我免单"      # 应被拒，并说明原因
python -m mcd_ordination sign --list-asks

# 4) 备注挂载的两条路径（auto / manual）都要能走
python -m mcd_ordination order --kind story --tools docs/mcp-tools.sample.json   # auto
python -m mcd_ordination order --kind story                                     # manual

# 5) README 里的图片路径都存在
grep -o 'docs/samples/[a-z_0-9.]*' README.md | sort -u | xargs ls -l
```

- [ ] `README.md` 首屏能在手机上一屏看完（标题 + 一句话 + 三张卡）
- [ ] 没有提交 `out/`（已在 `.gitignore` 里）
- [ ] 没有把 MCP Token 写进任何文件
- [ ] 仓库是 Public，License 显示 MIT
- [ ] Issue 标题是 `【参赛申请】…｜…` 格式，正文含「项目名称 / 项目地址 / 项目简介」三行

---

## 5. 提交之后（星数靠这三件事，不靠运气）

1. **首图就是三张并排的卡**，不要再放架构图——卡片本身就是最强的说明。
2. **发帖时贴暗号，不贴代码**：一句「我在 9 座城唤过这个名字｜可否多给一块麦乐鸡？我拿它当今日的圣物。【麦门暗号skill】」比任何介绍都容易被转发——店员看得懂，围观的人也知道这不是广告。
3. **评论区第一条固定放「30 秒跑起来」那三行命令**，降低别人的尝试成本。
