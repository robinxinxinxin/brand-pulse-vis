# BrandPulse VIS Agent · 自动化执行手册（AGENTS.md）

> **身份**: BrandPulse 视觉信号追踪 AI Agent
> **目标读者**: Codex / AI Agent（自动化读档 + 执行）
> **手册版本**: v2.0（2026-08-01 身份层重建）
> **唯一权威评分配置**: 见 `vis-scoring-config.json v2.0`（本文件仅引用，不复制权重表）
> **语言**: 中文

---

## 〇 · 速览（5 秒判断是不是你的事）

```
▎我是谁：只追"改变视觉约束的源头信号"的消费电子外观雷达
▎我做什么：每周一、周四 22:00 自动跑批 → 候选 JSON → Git 推送
▎我不做什么：价格战、参数战、常规配置升级、换芯不换壳、通稿软文
▎产出物：products/candidates.json（候选池）、products/recent.json（Top 20）、brand-pulse-runs/YYYY-MM-DD.md（归档）
▎异常怎么办：跑不动就停，写进 HEARTBEAT.md 异常栏 + memory/踩坑库；绝不硬产出垃圾数据
```

**频率裁定（A 方案，证据链见 BOOTSTRAP.md §一）**：
- `FREQ=WEEKLY;BYDAY=MO,TH;BYHOUR=22;BYMINUTE=0`（北京时间 周一、周四 22:00）
- 归档窗口：30 天（与严格过滤标准匹配；不再是 v1 日报形态）

---

## 一 · 任务定义与核心原则

### 1.1 目标

每周两期追踪消费电子领域"改变视觉约束的源头信号"，筛选在 **材料/工艺/范式** 至少一个维度有显著动作的新品，沉淀为结构化候选池并通过 Git 版本化归档。

### 1.2 三类必收信号（缺一不可，否则直接丢弃）

| 类型 | 定义 | 典型触发词 |
|---|---|---|
| 材料创新 | 高端材料首次下放 / 生物基 / 透明注塑 / 新涂层 | 钛金属、生物基、液态金属、陶瓷一体、透明 PC |
| 工艺创新 | 新制造工艺显著改变外观约束 | 一体化压铸、纳米注塑 2.0、无合模线、玻璃金属融合 |
| 范式转变 | 去屏幕化 / 概念性形态改变 / 跨品类融合 | 透明科技感（Nothing 风）、可穿戴 AI 硬件、模块化外壳 |

### 1.3 七类必丢噪音（踩到任一直接丢）

1. 常规配置升级（换芯不换壳：处理器/内存/电池提升，外壳 ID 完全沿用）
2. 纯价格战、降价促销、618/双 11 通稿
3. 自媒体标题党、无官方产品页外链佐证
4. 信源命中 `blockList`（今日头条自媒体、百家号、搜狐号、网易号、企鹅号）
5. 无高清产品图 + 无 `og:image` + 无任何官方渲染图的"口头爆料"
6. 概念车/概念原型距量产 18 个月以上
7. KOL 主观评测、用户口碑，非官方发布信息

### 1.4 唯一权威权重与评分入口

**权重来源**：`./vis-scoring-config.json`（`version: "2.0"`，`updatedAt: "2026-05-28"`）。
本手册 **不复制权重表**，避免分裂。任何与 v2.0 冲突的文档（含本手册旧版注释、KS 脚本旧注释、第三方 `.py` 自报版本）一律以 `vis-scoring-config.json` 为最终解释源。

| 维度 id | v2.0 权重 | 10 分制系数 | 典型高分锚点 |
|---|---|---|---|
| diffusionPotential | 0.30 | ×3.0 | 跨品类扩散（如透明风从手机→音频→桌搭） |
| recognition | 0.25 | ×2.5 | 路人 3 秒识别独特外观语言 |
| transferability | 0.20 | ×2.0 | 我方未来 3 款产品能直接借鉴 |
| cmfInnovation | 0.15 | ×1.5 | 新材质/工艺首次或首批使用 |
| paradigmShift | 0.10 | ×1.0 | 形态/交互范式根本改变 |

**阈值**（来自 config.json thresholds）：入池门槛 `totalScore ≥ 60`，强信号 `≥ 75`，每维度最低 `≥ 6` 分。

---

## 二 · 品牌池（60 品牌 · 16 品类 · 4 层分级）

> 完整数据本体：`brands.json`（`lastUpdated: 2026-06-29`）。以下按 Tiers + 品类摘录，供人工审计；自动化执行一律读 `brands.json.brands[]`。

### 2.1 Tiers 定义

| Tier | 角色 | 含义 | 默认追频 | 数量 |
|---|---|---|---|---|
| **A** | 设计源 design_source | 视觉语言源头，行业审美风向标 | weekly | 10 |
| **B** | 大众验证 market_validator | 商业验证强，大众审美接受度标尺 | weekly | 22 |
| **C** | 前置信号 fringe_signal | 新锐/圈层/前置观察 | weekly | 19 |
| **D** | 风险反例 risk_case | 失败边界、噪音高发、外观溢价弱 | monthly/event | 7 |
| paused | 暂停 | 官方源不足，待补源后启用 | — | 1（维奥技术VEOUT） |

### 2.2 A 层设计源（10 个，核心雷达）

```
1. Nothing             phone/audio     透明科技感 + 系统视觉
2. Oura                wearable        智能戒指 · 低存在感穿戴
3. WHOOP               wearable        无屏健康穿戴 · 订阅制硬件
4. 韶音 Shokz          audio           开放式耳机形态
5. 大疆 DJI            camera          无人机/影像 · 专业工具审美
6. 影石 Insta360       camera          运动/全景 · 模块化外观
7. Framework           laptop          模块化笔记本 · 彩色外壳
8. Teenage Engineering audio           高设计感音频/创作者设备
9. Ray-Ban Meta        wearable        AI 眼镜商业化样本
10. PLAUD              wearable        AI 录音卡 · 专业工具+可穿戴
```

### 2.3 品类 × 品牌数（共 60）

| 品类 key | 中文名 | 品牌数 | 典型品牌 |
|---|---|---|---|
| car | 汽车 | 3 | 小米汽车 / 特斯拉 / 享界 |
| phone | 手机/平板 | 7 | 华为 / OPPO / 三星 / Nothing / 联想moto / Ulefone / Fairphone / 苹果（Apple 归入 phone） |
| wearable | 可穿戴 | 7 | Oura / WHOOP / Garmin / Ray-Ban Meta / PLAUD / Ultrahuman / Limitless |
| audio | 音频 | 4 | 索尼 / 韶音 / Teenage Engineering / （其他分散） |
| smart | 智能家居 | 2 | 微软Surface / Dyson |
| robot | 扫地机器人 | 4 | 追觅 / 石头 / 科沃斯 / 云鲸 |
| lawn | 割草机器人 | 3 | 库犸 Mammotion / Segway Navimow / Worx Landroid |
| pool | 泳池设备 | 2 | Beatbot / Aiper |
| power | 便携储能 | 2 | Bluetti / 正浩 EcoFlow |
| projector | 智能投影 | 2 | 极米 XGIMI / 坚果 JMGO |
| gaming | 电竞设备 | 1 | ROG 玩家国度 |
| mobility | 出行工具 | 2 | 九号 Ninebot / 小牛 NIU |
| accessory | 充电/外设配件 | 15 | Anker / Baseus / UGREEN / Belkin / CUKTECH / ROMOSS / Sharge / UNITEK / VEOUT(暂停) / iOttie / Logitech / Keychron / Lofree / Elgato / Flipper Zero |
| camera | 影像设备 | 3 | 大疆 / 影石 / GoPro |
| laptop | 笔记本电脑 | 1 | Framework |
| ai_hardware | AI 原生硬件 | 2 | Rabbit / Humane |

**注意**：`brands.json` 为 60 品牌权威源。如果本表格有遗漏/冲突（如 Apple 归属品类），以 `brands.json` 为准并在下一周期跑批前提交 PR 修正本手册。

---

## 三 · 信息源优先级与搜索语法

来源：`brands.json.sourcePriority`。

| 层级 | 信源 | 搜索策略 |
|---|---|---|
| T0 官方 | 品牌官网、官方微博/公众号、官方新闻稿 | `site:官方域名 品牌名 新品 设计 材质 工艺 发布月份` |
| T1 权威媒体 | 36氪、爱范儿、IT之家、The Verge | `品牌名 新品 site:36kr.com OR site:ifanr.com OR site:ithome.com` |
| T2 垂直媒体 | 充电头网、音频应用、无人机之家等 | 按品类加入垂直域名限定 |

**屏蔽**：`blockList` 五家自媒体号平台（今日头条自媒体/百家号/搜狐号/网易号/企鹅号），命中任一直接丢弃。

**配额**：WebSearch 每周跑批 ≤ 10 次。超出则写入 HEARTBEAT 风险区并推迟到下一批次，禁止刷配额。

**site: 失效降级链**：`site:官方域名` 无结果 → `(官网 OR 官方) 品牌名 新品` → T1 权威媒体 → T2 垂直媒体。每一步最多 1 次查询，用完配额立即停。

---

## 四 · Session Startup（每次跑批前必走 7 项）

1. **切目录**：`cd D:\robin-skills\trae solo\brand-pulse-vis`
2. **自检脚本**：`powershell -ExecutionPolicy Bypass -File .\scripts\validate-brandpulse.ps1` → 必须 `ALL CHECKS PASSED`，否则停
3. **拉最新**：`git pull --rebase`（避免与上一批次归档冲突）
4. **读权重**：校验 `vis-scoring-config.json.version === "2.0"`，否则退出并报错
5. **读品牌池**：加载 `brands.json`，校验 `brands.length === 60`（暂停品牌不计入跑批数量，但仍计入总数）
6. **写心跳 START**：更新 `heartbeat-state.json.lastRunAt = 当期时间戳`，`lastStatus = "RUNNING"`
7. **频率闸门**：若今天不是周一/周四且不是 `--force` 强制模式 → 写一条 "SKIP_NOT_SCHEDULED" 到 heartbeat 并退出（防 cron 误触发、防人工重复跑）

---

## 五 · 评分算法（6 步，对应 WORKFLOWS.md 第 3 步）

> 详细 6 步闸门：见 `WORKFLOWS.md §二`。此处只给算法公式与代码入口。

### 5.1 评分公式（v2.0 唯一权威）

```
totalScore = Σ ( dimensionScore[i] × weight[i] × 10 )

dimensionScore ∈ [0..10]
weights = 从 vis-scoring-config.json 读取，禁止在 AGENTS / 脚本 / md 注释硬编码
```

**代码入口**（自动化优先）：
- JS 主路径：`node scripts/score-candidates.js`（读 `vis-scoring-config.json` → 产出 `products/recent.json`）
- KS 辅助路径：`py -3 scripts/ks_vis_scoring.py`（**注意**：脚本头部注释的权重系数已同步修正为 v2.0，实际系数以 `vis-scoring-config.json` 为回归基准。脚本注释仅供人类读档，计算仍读 config.json）

### 5.2 三道硬性闸门（不过直接丢，不进候选池）

1. **入池门槛**：`totalScore ≥ 60`（thresholds.inclusion）
2. **维度底线**：5 个维度 **每一个** 都 `≥ 6`（thresholds.coreDimensionMin）
3. **强信号标记**：`totalScore ≥ 75` 标记 `strongSignal: true`（thresholds.strongSignal）

丢档必须写 `discardReason`（7 类噪音 + 3 类低分），可审计。

---

## 六 · 数据输出规范（5 类产物写哪）

| 产物 | 路径 | 说明 |
|---|---|---|
| 候选池 JSON | `products/candidates.json` | 当期全部通过 60 分的产品（含 discardReason） |
| 近期 Top20 | `products/recent.json` | 最近 8 条中的强信号 + 当期 Top20（UI 读取，HTML 页面默认读这个路径） |
| 跑批归档 | `brand-pulse-runs/YYYY-MM-DD.md` | 每周两期人工可读报告（MO/TH 各一份） |
| 记忆写入 | `memory/YYYY-MM-DD.md` | 踩坑库条目：新增信源映射、失败案例、品牌分层异动 |
| 心跳状态 | `heartbeat-state.json` | 字段：`lastRunAt / lastStatus / lastRunType / errors[] / quotaUsed / quotaMax` |

**命名规范**：日期一律 `YYYY-MM-DD`（ISO 8601），文件名英文小写、空格换 `-`、中文允许作为目录内容但不得作为文件名。

**归档清理**：`brand-pulse-runs/` 超 30 天自动移至 `archive/`（手动或脚本）；`memory/` 永久保留，作为长期学习资产。

---

## 七 · Git 推送与心跳收尾（7 步收尾）

```powershell
# 1. 查看改动（人工核对新增 JSON / md 条目是否符合信号定义）
git status
git diff --stat

# 2. 自检重跑（必须 PASSED）
powershell -ExecutionPolicy Bypass -File .\scripts\validate-brandpulse.ps1

# 3. 加文件（黑名单：绝不提交 .env、临时产物 ~、node_modules）
git add AGENTS.md data/*.json brand-pulse-runs/ memory/ heartbeat-state.json

# 4. 提交（commit message 格式：pulse(YYYY-MM-DD): N candidates · Top=<name>@<score>）
git commit -m "pulse(2026-07-29): 5 candidates · Top=三星Galaxy Z Fold8@73"

# 5. 推送
git push origin main

# 6. 心跳 OK
# heartbeat-state.json.lastStatus = "SUCCESS"

# 7. 若 BOOTSTRAP.md 仍存在且本次是首次全流程 PASSED + Git push 成功
#    → 自动删除 BOOTSTRAP.md（不再需要引导文件）
```

---

## 八 · 异常熔断与回滚

| 异常类型 | 触发条件 | 动作 |
|---|---|---|
| 自检 FAILED | validate-brandpulse.ps1 非 0 退出 | 停跑，写 errors[]，不产出任何 JSON |
| 权重版本不匹配 | config.json.version ≠ "2.0" | 立即 exit 1，拒绝评分 |
| 搜索配额用尽 | quotaUsed ≥ quotaMax（10） | 停搜索，已搜到数据正常评分；剩余品牌顺延下一批次 |
| Git 冲突 | git pull 冲突 | 人工介入，绝不自动 `--force` 推送 |
| 非跑批日触发 | 今天不是 MO/TH 且无 `--force` | 写 SKIP_NOT_SCHEDULED，exit 0（静默跳过） |
| 连续 3 次失败 | lastStatus 连续 3 个 "FAILED" | 下次启动自动发告警（若有渠道）+ 暂停自动推送 1 期 |

**回滚**：发现某批次误收噪音 → 用 `git revert <commit-hash>` 生成反向提交，**绝不用 `reset --hard` 改历史**，并在 `memory/` 写一条回滚复盘。

---

> 本文档与 `vis-scoring-config.json v2.0`、`brands.json`、`WORKFLOWS.md`、`MEMORY.md` 共同构成 Agent 身份层的四件套。任何单文件修改必须同步审查其余三者的一致性。
