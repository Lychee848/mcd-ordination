# 参赛提交清单

> 这个文件是给**你自己**看的操作手册，不是仓库正文。提交完成后可以删掉，或移入 `docs/`。

---

## 0. 三件必须做的事（顺序不能反）

1. 在 GitHub 建仓库 `mcd-ordination`（**Public**，不要勾选任何模板，不要勾 README）。
2. 把本目录推上去（见下方命令）。
3. 去赛事仓库提 Issue（见第 3 节），**标题和正文严格按格式**。

---

## 1. 推仓库

```bash
cd mcd-ordination
git init
git add .
git commit -m "feat: 麦门行传 —— 把麦当劳用户行为编译成一套卡证"
git branch -M main
git remote add origin https://github.com/<你的用户名>/mcd-ordination.git
git push -u origin main
```

---

## 2. 仓库设置（直接影响能不能被搜到，别跳过）

**About 栏（右上角齿轮）**

- Description：
  ```
  麦当劳用户行为 → 专属麦门卡证。九阶品秩 · 教义摘录 · 四版式交换卡 · 可复算的专属暗号。零 Key 可跑。
  ```
- Website：可填你的演示页；暂时没有就留空（**别填无效链接**）
- Topics（按优先级，GitHub 最多 20 个）：
  ```
  mcp  mcdonalds  mcdonalds-mcp  workbuddy-skill  mcd
  generative-art  trading-card-game  python  pillow  svg
  llm  ai  prompt-engineering  data-visualization  privacy-first
  ```

> 依据：统计 744 个参赛仓库后发现，`workbuddy-skill` / `mcd` / `mcdonalds-mcp` 三个 topic 的星数中位数最高；
> `model-context-protocol` / `nutrition` / `meal-planner` 已经是红海（大量 0–3 星项目），不建议占用 topic 位。

**社交预览图**：Settings → Social preview 上传 `docs/samples/three_personas.png`（1200×630 会自动裁切）。

### 2.1 开 GitHub Pages（星数高的作品都有，别省）

1. 先把你自己的仓库地址写进页面（`index.html` 里的 GitHub 链接默认是占位符）：
   ```bash
   REPO_URL="https://github.com/<你的用户名>/mcd-ordination" \
   python scripts/gen_demo_site.py
   git commit -am "chore: 指向真实仓库地址" && git push
   ```
2. GitHub → Settings → **Pages** → Source: *Deploy from a branch* → Branch: `main` / **`/ (root)`** → Save。
3. 一两分钟后访问 `https://<你的用户名>.github.io/mcd-ordination/`，把这个地址填进 About 的 Website。

页面是纯静态、零依赖：人设/卡种/暗号体裁切换、一键复制都能离线用，不请求任何接口。

---

## 3. 提 Issue（原文照抄）

仓库：<https://github.com/M-China/mcd-developer-innovation-challenge/issues/new>

### 标题

```
【参赛申请】麦门行传｜把你的麦当劳用户行为写成一卷教义，再生成一枚能写进订单备注的麦门暗号
```

### 正文

```
标题：麦门行传｜把你的麦当劳用户行为写成一卷教义，再生成一枚能写进订单备注的麦门暗号

〖参赛申请〗
项目名称：麦门行传（mcd-ordination）
项目地址：https://github.com/<你的用户名>/mcd-ordination
项目简介：麦门行传把「麦当劳用户行为」当作 prompt，产出两样东西：一套专属麦门卡证（九阶品秩、教义摘录、四种版式的交换卡），和一枚只属于你的「麦门暗号」。暗号有三种体裁——打招呼、创意地问一句能不能多给一块鸡块、或者求取本店那卷麦门传说的下一段（每家店本来就有自己的传说，你是去取，不是让店员创作；下次带来的是续篇）。勾选一下，暗号会挂到这一单的订单备注上，把一次交易变成一次真实互动。三条硬线：卡面每个数字都能追溯到真实数据（不可伪造）、金额不进任何公式（不鼓励消费）、不填任何 Key 也能看见完整卡面（零依赖可跑）。备注字段有没有、能不能自动写入，由每次运行时的 tools/list 能力探测决定：有就写进 payload，没有就给你一段可复制的文本加三步指引，绝不假装已经写进去。仓库自带三份人设数据，clone 下来 30 秒就能看到成品卡与三体裁暗号。
```

---

## 4. 提交前自检

```bash
# 0) 装包（editable，不产生第三方依赖）
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
