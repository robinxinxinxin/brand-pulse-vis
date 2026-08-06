# WORKFLOWS.md · 6 步完整跑批流程（含闸门）

> 频率：**每周一、周四 北京时间 22:00**。
> 触发：cron（推荐）或人工 `/run`。非跑批日除非 `--force` 一律跳过。
> 本文件是「执行剧本」，每一步必须按顺序。任何闸门未通过 → 停在该步并写 heartbeat errors。

---

## 〇 · 频率闸门（前置检查）

```
IF 今天星期 ∈ {1, 4} OR args.includes('--force') → 继续
ELSE → heartbeat.SKIP_NOT_SCHEDULED; exit 0（静默跳过）
```

---

## 完整流程 6 步

### 步骤 0 · Startup 7 项（AGENTS.md §四 同款 7 步）

| # | 检查 | 通过条件 | 失败动作 |
|---|---|---|---|
| 0.1 | 切目录 | `cd 'D:\robin-skills\trae solo\brand-pulse-vis'` 成功 | exit 1，报路径错 |
| 0.2 | 自检脚本 | `.\scripts\validate-brandpulse.ps1` 输出 `ALL CHECKS PASSED` | exit 1，errors += [validate_failed] |
| 0.3 | git 最新 | `git pull --rebase` 无冲突 | 有冲突 → exit 1，报 git_conflict |
| 0.4 | 权重版本 | `vis-scoring-config.json.version === "2.0"` | ≠ → exit 1，报 weight_version_mismatch |
| 0.5 | 品牌池 | `brands.json.brands.length === 60`（暂停 VEOUT 仍计入） | ≠ → WARNING 但继续，写 memory 异动待审 |
| 0.6 | 心跳初始化 | heartbeat.lastStatus = "RUNNING"; lastRunAt = now | — |
| 0.7 | 配额初始化 | quotaUsed = 0; quotaMax = 10 | — |

**输出**：heartbeat-state.json 写 START 快照。

---

### 步骤 1 · 搜索（分 4 层，配额 ≤ 10）

按 Tier 顺序搜：**A 层 10 → B 层 22 → C 层 19 → D 层 7**（paused 品牌跳过，含 VEOUT）。

#### 1.1 搜索语法（品牌按品类差异化关键词）

```
通用模板："品牌名" 新品发布 YYYY年MM月 设计 材质 工艺 外观
A 层模板："品牌名" (新品｜新配色｜新材料｜工艺｜限量｜联名) 设计
D 层模板："品牌名" 风险案例 失败 评测 佩戴尴尬
```

#### 1.2 site: 降级链（每步最多 1 次查询）

```
1. site:<官方域名> + 关键词    → 优先（官方源命中率最高）
2. (官网 OR 官方) + 关键词     → site 失效降级 1
3. site:36kr.com OR site:ifanr.com OR site:ithome.com + 关键词 → T1 权威降级 2
4. 品类垂直域名（充电头网 / 音频应用 / 无人机之家）+ 关键词 → T2 垂直降级 3
```

#### 1.3 闸门（必查）

| 闸门 | 条件 | 动作 |
|---|---|---|
| G1.1 blockList 命中 | 结果域名 ∈ {今日头条自媒体/百家号/搜狐号/网易号/企鹅号} | 丢弃该结果，不占配额 |
| G1.2 配额上限 | quotaUsed >= 10 | 剩余品牌写入 `postponedBrands[]`，顺延下一批次 |
| G1.3 每品牌 1 次 | 同品牌本批次 > 1 次搜索 | 跳过重复，配额不扣 |
| G1.4 7 类噪音 | 标题/摘要命中 AGENTS.md §一·1.3 任一 | discardReason 记噪音类，不进步骤 2 |

**输出**：`data/candidates.raw.json`（原始搜索命中 + discardReason 噪音条目）。

---

### 步骤 2 · 提取（图片 + 结构化字段）

对 G1.4 通过的每一条命中：

| 字段 | 提取规则 | 缺失处理 |
|---|---|---|
| `title` | 官方产品名（英文保留品牌，品名翻译按 KS_ZH_MAP） | 允许空，用 `<品牌> 新品占位` |
| `brand` | 对应 brands.json.name | 必填 |
| `category` | 对应 brands.json.category | 必填（不存在则按 16 品类兜底映射） |
| `releaseDate` | 官方发布日期（YYYY-MM-DD），没有填发现日期 | 允许当月近似 |
| `summary` | 3 行内：材料 / 工艺 / 范式 任一有实质内容 | 无实质内容 → discardReason=NO_SIGNAL |
| `imageUrl` | `og:image` 优先 → 页面第一张高清官方渲染图 → 媒体实拍 | 允许空（占位图兜底机制开启），但必须写 sourceNote |
| `sourceUrl` | 官方产品页或权威媒体 URL（**必须**） | 缺失 → 丢弃，discardReason=NO_SOURCE |
| `sourceTier` | T0_official / T1_media / T2_vertical | 按 brands.json.sourcePriority 标注 |

#### 闸门 G2

- **G2.1 NO_SOURCE**：sourceUrl 缺失 → 丢（信源是底线，绝不放水）
- **G2.2 NO_SIGNAL**：summary 全是参数堆砌、没有任何材料/工艺/范式实质描述 → 丢

**输出**：`data/candidates.extracted.json`（结构化候选 + discardReason）。

---

### 步骤 3 · 评分（v2.0 唯一权威）

#### 3.1 5 维度 1-10 分打分

**代码入口**：`node scripts/score-candidates.js`（**推荐主路径**，直接读 config.json）。
人工辅助打分按如下锚点：

| 维度 | 6 分（及格线）锚点 | 9-10 分（高分）锚点 |
|---|---|---|
| diffusionPotential 0.30 | 本品类内可扩散 | 跨 ≥ 3 品类，且与我方品类重叠 ≥ 1 |
| recognition 0.25 | 业内能认出是哪品牌 | 路人 3 秒识别独特外观语言 |
| transferability 0.20 | 1 款产品可借鉴 | 我方未来 3 款产品可直接借鉴 |
| cmfInnovation 0.15 | 已知材质新用法 | 新材质/新工艺首次或首批量产 |
| paradigmShift 0.10 | 局部交互改变 | 去屏化 / 形态 / 佩戴方式根本改变 |

#### 3.2 闸门 G3（三道硬门槛）

| 闸门 | 公式 | 未通过 → |
|---|---|---|
| G3.1 入池门槛 | `totalScore = Σ d[i] × w[i] × 10 ≥ 60` | discardReason=SCORE_BELOW_60 |
| G3.2 维度底线 | `min(d[i]) ≥ 6`（5 维每个都 ≥ 6） | discardReason=DIMENSION_BELOW_6 |
| G3.3 强信号标记 | `totalScore ≥ 75 → strongSignal=true` | 不丢，标记为强信号 |

**输出**：
- `products/candidates.json`（通过 G3 的正式候选池，保留 discardReason 便于审计）
- `products/recent.json`（最近 8 条 + 当期 Top20，供 UI 读，与历史系统/HTML/自检脚本对齐）

---

### 步骤 4 · 写记忆与归档

| 产物 | 写哪里 | 内容要求 |
|---|---|---|
| 跑批归档 | `brand-pulse-runs/YYYY-MM-DD.md` | ① 概览表（N 入池 / M 强信号 / 丢弃分布）② 强信号 Top3 卡片（title + score + imageUrl + 1 句建议）③ discardReason 分类饼 |
| 记忆条目 | `memory/YYYY-MM-DD.md` | ① 新信源映射（命中率 > 50% 的域名）② 失败案例复盘（NO_SOURCE/NO_SIGNAL/SCORE_BELOW_60 的共性）③ 品牌分层异动（若 brands.json 有更新）④ 任何规则升级 |
| 心跳更新 | `heartbeat-state.json` | `lastStatus = SUCCESS / PARTIAL / FAILED`；`errors[]` 清零（成功）或保留；`quotaUsed` 终值；`postponedBrands[]` 下周期预告 |

#### 闸门 G4

- **G4 归档完整性**：brand-pulse-runs + memory 两份 md 任一缺失 → heartbeat 标 PARTIAL，不允许进入 Git 推送阶段。

---

### 步骤 5 · 自检重跑 + Git 推送

按 TOOLS.md §四 规范 5 步走：

```
5.1 git status → 核对变更文件清单（只允许白名单）
5.2 git diff --stat → 确认没有意外大改动
5.3 重跑 validate-brandpulse.ps1 → 必须再次 PASSED
5.4 git add 白名单 + git commit -m "pulse(YYYY-MM-DD): N candidates · Top=<Name>@<Score>"
5.5 git push origin main（绝不 --force）
```

#### 闸门 G5

- **G5.1 自检 FAILED** → 退回步骤 4 修，不得 commit
- **G5.2 push 失败** → heartbeat.errors += [git_push_failed]，下次启动自动先 pull --rebase 重试一次

---

### 步骤 6 · 收尾与熔断检查

| 检查项 | 结果 | 动作 |
|---|---|---|
| 6.1 本次状态 | SUCCESS | heartbeat.consecutiveFailures = 0 |
| 6.1 本次状态 | FAILED | consecutiveFailures += 1 |
| 6.2 熔断 | consecutiveFailures ≥ 3 | 下周期自动暂停自动推送 1 期（保留搜索+评分+归档，仅停 git push） |
| 6.3 BOOTSTRAP 收尾 | BOOTSTRAP.md 存在 且 本次为首次 SUCCESS + push 成功 | **自动删除 BOOTSTRAP.md**（身份层已转正，不再需要引导） |

---

## 附 · 1 个完整 `/run` 示例（伪代码时序）

```
STARTUP 7 CHECKS → PASSED
  └─ Monday 22:00 Beijing time, proceed.

STEP1 SEARCH (Quota 10)
  A10→B22→C19→D7: 搜 10 个品牌，quotaUsed=8, postponed=[9 个 B 尾+ 全 C+ 全 D]
  噪音丢弃 17 条 → G1.4 通过 23 条.

STEP2 EXTRACT
  NO_SOURCE 丢 3 条 → G2.1
  NO_SIGNAL 丢 12 条 → G2.2
  结构化候选 8 条.

STEP3 SCORE (score-candidates.js, config v2.0)
  候选 1: 三星 Fold8 → 5 维 [8,9,7,8,6] → 79.0 → strongSignal ✅
  候选 2-5: 62~70 分 → 入池 ✅
  候选 6-8: <60 或 某维<6 → 丢 ❌
  → final candidates = 5

STEP4 WRITE
  brand-pulse-runs/2026-07-29.md  ✅
  memory/2026-07-29.md           ✅
  heartbeat SUCCESS               ✅
  G4 完整性 → PASSED.

STEP5 GIT PUSH
  validate PASSED → commit → push success.

STEP6 FINAL
  consecutiveFailures = 0 → OK.
  BOOTSTRAP.md 不存在 → 无需删除.
  END.
```
