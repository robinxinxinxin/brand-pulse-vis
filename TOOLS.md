# TOOLS.md · 工具与脚本索引

> 所有入口按「日常高频 → 配置维护 → 异常处理」排序。脚本路径相对仓库根 `D:\robin-skills\trae solo\brand-pulse-vis`。

---

## 一 · 日常跑批工具（高频率）

| 工具 | 路径 | 作用 | 必跑频率 |
|---|---|---|---|
| 自检脚本 | `scripts/validate-brandpulse.ps1` | 跑批前 9 项自检，通过才允许继续 | **每次** |
| JS 评分器 | `scripts/score-candidates.js` | 读 `vis-scoring-config.json` + 候选 → 算 v2.0 总分 → 输出 `recent.json` Top20 | 每次步骤 3 |
| KS 辅助评分器 | `scripts/ks_vis_scoring.py` | KS 候选项目的 VIS 五维启发式评分（注释已同步 v2.0；**计算仍以 config.json 为基准**） | KS 专用辅助 |
| 可视化页 | `index.html` | 加载 `vis-scoring-config.json` + `recent.json` → 展示权重条 + 强信号卡片 | 人工读档 |
| KS 可视化页 | `ks-visibility-scan.html` | KS 项目的 v2.0 评分可视化 | KS 专项读档 |

## 二 · 配置文件（低频率，改动需提 PR）

| 文件 | 作用 | 版本 | 改动审核 |
|---|---|---|---|
| `brands.json` | 60 品牌 16 品类 4 层分级 + 信源优先级 + blockList | 2026-06-29 | 必须 PR + 跑一次自检 |
| `vis-scoring-config.json` | v2.0 权重表 + 三道阈值 | 2.0（2026-05-28） | **权威源**，改动必须同步改 MEMORY.md §二历史错误记录表 + 跑完整回归 |
| `AGENTS.md` | 自动化执行手册（7 章 + Session Startup 7 步） | v2.0 2026-08-01 | 与 config.json / WORKFLOWS / MEMORY 联动审查 |
| `MEMORY.md` | 长期记忆（品牌池概览 + 权重历史 + 信源映射 + 踩坑库） | 初始化 2026-08-01 | 追加式，不删旧条目 |
| `heartbeat-state.json` | 运行状态（lastRun / status / errors / quotaUsed） | 运行时 | 只允许 Agent 自己写 |

## 三 · 配额与搜索约束（硬限制，不允许突破）

| 项 | 值 | 备注 |
|---|---|---|
| WebSearch 每周上限 | **10 次** | 用完即停，剩余品牌顺延下一批次 |
| site: 语法优先 | 是 | 官方域名 → T1 权威 → T2 垂直的降级链 |
| 单品牌单批次搜索次数上限 | 1 次 | 防止同一品牌刷配额 |
| blockList 平台数 | 5 个 | 今日头条自媒体 / 百家号 / 搜狐号 / 网易号 / 企鹅号 |

## 四 · Git 操作规范（任何提交必走）

```powershell
# 0. 切目录
cd 'D:\robin-skills\trae solo\brand-pulse-vis'

# 1. 自检 PASSED（没通过不许加文件）
powershell -ExecutionPolicy Bypass -File .\scripts\validate-brandpulse.ps1

# 2. 只加该加的（以下模式以外禁止 git add 其他）
git add AGENTS.md SOUL.md IDENTITY.md USER.md TOOLS.md WORKFLOWS.md HEARTBEAT.md MEMORY.md BOOTSTRAP.md
git add brands.json vis-scoring-config.json heartbeat-state.json
git add data/*.json scripts/* brand-pulse-runs/*.md memory/*.md canvas/*.canvas workspace/
git add ~/.qclaw/skills/brand-pulse-*/SKILL.md   # 若改了 skills

# 3. 提交信息格式
git commit -m "pulse(YYYY-MM-DD): N candidates · Top=<Name>@<score>"
# 示例：git commit -m "pulse(2026-07-29): 5 candidates · Top=三星Galaxy Z Fold8@73"

# 4. 推送前必须再次自检 PASSED
# 5. 不允许 git push --force；冲突走 rebase / revert
```

## 五 · 异常处理工具箱

| 场景 | 工具 / 命令 | 说明 |
|---|---|---|
| 自检 FAILED | 跑 validate 脚本看具体哪项红 | 修复后再跑；连续 3 次 FAILED 触发熔断 |
| 权重版本错 | 打开 `vis-scoring-config.json` 查 version 字段 | ≠ 2.0 → exit 1，等待人工修复 config |
| 配额用尽 | 读 `heartbeat-state.json.quotaUsed / quotaMax` | 记录品牌顺延清单，下一批次优先搜 |
| 某次提交误收噪音 | `git log --oneline -n 10` 找 hash → `git revert <hash>` | revert 完成后必须写一条 memory 踩坑库 |
| 非跑批日被 cron 误触发 | 读 heartbeat `SKIP_NOT_SCHEDULED` 标记 | 正常退出 0，不发告警 |
| 连续 3 次 FAILED | heartbeat `consecutiveFailures ≥ 3` | 暂停自动推送 1 期，人工介入 |
