# MEMORY.md · BrandPulse VIS 长期记忆库

> **用途**：Agent 跨批次保留的结构化经验。每次跑批后追加，只读不改旧条目。
> **最后初始化**：2026-08-01（身份层重建日）
> **数据域**：品牌池概览 · v2.0 权重速查 · 信源映射 · 踩坑库 · 信号黑名单 · 品牌分层异动

---

## 一 · 品牌池概览（60 品牌 · 16 品类 · 4 层）

初始化自 `brands.json` 2026-06-29 快照。**运行时只读 `brands.json`，本章节仅为人工审计用**。

### 1.1 Tiers × 数量

| Tier | 角色 | 数量 | 默认追频 |
|---|---|---|---|
| A 设计源 | 视觉语言源头 | **10** | weekly |
| B 大众验证 | 商业审美基准 | **22** | weekly |
| C 前置信号 | 新锐/圈层观察 | **19** | weekly |
| D 风险反例 | 失败边界/噪音高发 | **7** | monthly 或 event |
| paused | 官方源待补 | **1** | — |
| — 合计 — | — | **59+1(暂停)** | — |

### 1.2 16 品类 × 品牌清单（按品类字母序）

| # | 品类 key | 中文名 | 品牌数 | 品牌名 |
|---|---|---|---|---|
| 1 | accessory | 充电/外设配件 | 15 | Anker、Baseus、UGREEN、Belkin、CUKTECH、ROMOSS、Sharge、UNITEK、VEOUT(暂停)、iOttie、Logitech、Keychron、Lofree、Elgato、Flipper Zero |
| 2 | ai_hardware | AI 原生硬件 | 2 | Rabbit、Humane |
| 3 | audio | 音频 | 4 | 索尼、韶音 Shokz、Teenage Engineering、（GoPro 归入 camera） |
| 4 | camera | 影像设备 | 3 | 大疆 DJI、影石 Insta360、GoPro |
| 5 | car | 汽车 | 3 | 小米汽车、特斯拉、享界 Stelato |
| 6 | gaming | 电竞设备 | 1 | ROG 玩家国度 |
| 7 | laptop | 笔记本电脑 | 1 | Framework |
| 8 | lawn | 割草机器人 | 3 | 库犸 Mammotion、Segway Navimow、Worx Landroid |
| 9 | mobility | 出行工具 | 2 | 九号 Ninebot、小牛 NIU |
| 10 | phone | 手机/平板 | 8(含 Apple) | 华为、OPPO、三星、联想 moto、Nothing、Ulefone、Fairphone、苹果 Apple |
| 11 | pool | 泳池设备 | 2 | Beatbot、Aiper |
| 12 | power | 便携储能 | 2 | Bluetti、正浩 EcoFlow |
| 13 | projector | 智能投影 | 2 | 极米 XGIMI、坚果 JMGO |
| 14 | robot | 扫地机器人 | 4 | 追觅 Dreame、石头 Roborock、科沃斯 Ecovacs、云鲸 Narwal |
| 15 | smart | 智能家居 | 2 | 微软 Surface、Dyson |
| 16 | wearable | 可穿戴 | 7 | Oura、WHOOP、佳明 Garmin、Ray-Ban Meta、PLAUD、Ultrahuman、Limitless |

**校验**：15+2+4+3+3+1+1+3+2+8+2+2+2+4+2+7 = **60** ✅

### 1.3 A 层设计源 10 个（核心雷达）

```
Nothing（phone/audio）· Oura（wearable）· WHOOP（wearable）· 韶音 Shokz（audio）
大疆 DJI（camera）· 影石 Insta360（camera）· Framework（laptop）
Teenage Engineering（audio）· Ray-Ban Meta（wearable）· PLAUD（wearable）
```

---

## 二 · VIS v2.0 评分权重速查（唯一权威：vis-scoring-config.json）

**权重表（v2.0）**：

| 维度 id | 中文名 | 权重 | 10 分制系数 | 高分锚点示例 |
|---|---|---|---|---|
| diffusionPotential | 扩散潜力 | **0.30** | ×3.0 | 透明风跨 3+ 品类扩散（手机→音频→桌搭） |
| recognition | 识别度 | **0.25** | ×2.5 | 路人 3 秒识别独特外观语言 |
| transferability | 可迁移性 | **0.20** | ×2.0 | 我方未来 3 款产品可直接借鉴 |
| cmfInnovation | CMF 创新 | **0.15** | ×1.5 | 新材质/工艺首次或首批使用 |
| paradigmShift | 范式转变 | **0.10** | ×1.0 | 形态/交互范式根本改变 |

**校验**：0.30 + 0.25 + 0.20 + 0.15 + 0.10 = **1.00** ✅

**阈值（thresholds）**：

| 名称 | 值 | 含义 |
|---|---|---|
| inclusion | 60 | 入池门槛（totalScore ≥ 60） |
| strongSignal | 75 | 强信号标记（≥ 75 → strongSignal=true） |
| coreDimensionMin | 6 | 每维度底线（任一维度 < 6 → 丢弃） |

**历史错误记录（防重蹈）**：

| 发生时间 | 错误权重源 | 扩散潜力 | 识别度 | 可迁移 | CMF | 范式 | 状态 |
|---|---|---|---|---|---|---|---|
| ~2026-06-07 | 旧 AGENTS.md §4.3（日报口径） | 0.12 | 0.10 | 0.08 | 0.06 | 0.04 | ❌ 已废弃 |
| ~2026-05（自报 v5.0） | ks_vis_scoring.py 注释 | 0.10 | 0.30 | 0.15 | 0.20 | 0.25 | ⚠️ 2026-08-01 注释同步修正为 v2.0；**脚本仍读 config.json** |
| 2026-05-28 至今 | **vis-scoring-config.json v2.0** | **0.30** | **0.25** | **0.20** | **0.15** | **0.10** | ✅ **唯一权威** |

---

## 三 · 信源映射（brand → 推荐域名）

初始化为空。每次跑批若发现某品牌的稳定官方域名/垂直媒体渠道命中率高，在此追加一行。格式：

```
# 示例（运行时追加）
# 2026-08-05 | Framework | frame.work + community.frame.work 论坛 | 命中率 60%
# 2026-08-08 | 韶音 Shokz | shokz.com.cn（中文站）比 shokz.com（全球站）新品早 48h | 命中率 75%
```

---

## 四 · 踩坑库（每次失败/回滚必写）

**格式**：`日期 | 品牌 | 问题分类 | 根因 | 修复/规避 | 操作人`

```
# 2026-08-01 初始化（身份层重建）
# 001 | 全品牌 | 评分权重三套分裂（AGENTS.md / ks_vis_scoring.py 注释 / config.json 互相冲突）
#     | 根因：v1 日报迁移 v2 周跑时只改了 config.json，AGENTS.md 和 KS 注释没同步
#     | 修复：统一 config.json v2.0 为唯一权威，AGENTS.md 不再复制权重表，
#           KS 脚本注释同步改为 v2.0 并标注"注释仅供人读，计算仍读 config.json"
#     | 操作人：Agent 身份层重建 v2.0
#
# 002 | 维奥技术 VEOUT | officialSources=[] → 品牌命中暂停状态仍被纳入搜索
#     | 根因：v1 代码未过滤 paused=true
#     | 规避：WORKFLOWS §2.2 加 paused 过滤门；MEMORY 本条目做回归案例
```

**后续追加行从本线以下开始，上方初始化内容不删除**：

---
（本线以下由 Agent 在每次跑批后自动追加）
