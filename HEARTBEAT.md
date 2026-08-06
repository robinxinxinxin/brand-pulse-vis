# HEARTBEAT.md · 健康检查清单（跑批前后必读）

> 本文件是 **人工** 心跳检查清单；机器可读状态写在 `heartbeat-state.json`。两者不一致时以 JSON 为准并回写本文件 `人工复核` 栏。
> 频率：每次跑批前后按清单逐项打勾。连续 3 次 FAILED → 熔断（暂停自动推送 1 期）。

---

## 一 · 状态机定义

| lastStatus | 含义 | 是否允许进入下一次 Git 推送 |
|---|---|---|
| `INIT` | 首次初始化（BOOTSTRAP 未完成） | 否，必须先 BOOTSTRAP PASSED |
| `RUNNING` | 本批次正在执行 | — |
| `SUCCESS` | 上一批次 6 步全绿 | 是 |
| `PARTIAL` | 归档/记忆有缺口，已推送 JSON 但 md 不完整 | 否，先补齐 md |
| `FAILED` | 自检/权重/Git 任一硬失败 | 否，先修根因 |
| `SKIP_NOT_SCHEDULED` | 非跑批日被触发，静默跳过 | —（不消耗配额）|
| `CIRCUIT_BROKEN` | 连续 3 次 FAILED → 熔断中 | 否，必须人工介入后手动改状态 |

---

## 二 · 跑批前检查（必须全勾）

| # | 检查项 | 核对方法 | 通过？ | 备注 |
|---|---|---|---|---|
| H1 | 今天是周一或周四 或 已明确 `--force` | `date` 星期 ∈ {1,4} | ☐ | 非跑批日别手贱 |
| H2 | 工作目录正确 | `cd 'D:\robin-skills\trae solo\brand-pulse-vis'; pwd` | ☐ | |
| H3 | 自检脚本 PASSED | 跑 `.\scripts\validate-brandpulse.ps1` | ☐ | 红项必须先修 |
| H4 | Git 工作区干净 | `git status` 显示 clean 或只含上次未 commit 的预期改动 | ☐ | 有未预期改动先 stash/commit |
| H5 | config.json 版本 = 2.0 | `jq '.version' vis-scoring-config.json` → `"2.0"` | ☐ | 核心中的核心 |
| H6 | brands.json 长度 = 60 | `jq '.brands | length' brands.json` → 60 | ☐ | 暂停 VEOUT 仍计入 |
| H7 | 配额未超期 | 上周 quotaUsed ≤ 10（或新周期已清零） | ☐ | 配额跨周不累加 |
| H8 | 熔断未触发 | heartbeat `consecutiveFailures < 3` | ☐ | 熔断中不许自动推送 |

**H1-H8 全勾才允许进入 WORKFLOWS §步骤 0**。缺一项 → 人工修，修好手动跑一次自检 PASSED。

---

## 三 · 跑批后检查（必须全勾）

| # | 检查项 | 核对方法 | 通过？ | 备注 |
|---|---|---|---|---|
| T1 | candidates.json 存在 | `ls products/candidates.json` + JSON 合法 | ☐ | 历史路径：自检脚本/HTML 页面读 products/，不是 data/ |
| T2 | recent.json 存在 + Top20 长度 > 0 | `jq '.top20 | length' products/recent.json` ≥ 1 | ☐ | 允许只有 1 条（严格过滤不为过）|
| T3 | 强信号 ≥ 75 都带 imageUrl | `jq '.top20[] | select(.strongSignal) | .imageUrl'` 全非空 | ☐ | 强信号无图 = 不完整交付 |
| T4 | brand-pulse-runs 当期 md 存在 | `ls brand-pulse-runs/YYYY-MM-DD.md` | ☐ | G4 完整性闸门 |
| T5 | memory 当期 md 存在 | `ls memory/YYYY-MM-DD.md` | ☐ | G4 完整性闸门 |
| T6 | discardReason 有分布 | candidates.json 中 discardReason 覆盖率 > 90% | ☐ | 便于审计过滤规则 |
| T7 | Git push 成功 | `git log --oneline -n 1` 是本次 pulse(YYYY-MM-DD) 且 remote 同步 | ☐ | |
| T8 | heartbeat SUCCESS | `jq '.lastStatus' heartbeat-state.json` → "SUCCESS" | ☐ | |

---

## 四 · 熔断与人工介入规则

| 触发条件 | 自动动作 | 人工介入必须做 |
|---|---|---|
| 单次 FAILED | heartbeat 记录 errors[]，不推送 | 打开本清单 H1-H8 逐项复核，找到根因修 |
| 连续 2 次 FAILED | 下次启动自动 WARNING | 在下一批次开始前 **必须** 先修根因，不能硬推 |
| **连续 3 次 FAILED** | 状态改 `CIRCUIT_BROKEN`；下次自动停掉 git push（只跑 1-4 步） | ① 写 memory/ 复盘 ② 至少 1 次手动 `/force-run` 并人工审计通过 ③ 手动 heartbeat `consecutiveFailures = 0; lastStatus = "PARTIAL"` |
| Git push 冲突 2 次以上 | 不重试 | 手动 `git pull --rebase`，解决冲突，commit 后再 push |
| 权重版本不匹配（≠ 2.0）| 立即 exit 1 | 手动打开 config.json 确认版本号；若被误改 → git revert 回正确版本 |

---

## 五 · 最近状态留痕（人工填写，JSON 自动写）

| 日期（YYYY-MM-DD） | 星期 | 类型（SCHEDULED/FORCE） | lastStatus | quotaUsed / 10 | 入池数 | 强信号数 | Top1 名称 @ 分数 | 人工签字 |
|---|---|---|---|---|---|---|---|---|
| 2026-08-01 | 六 | INIT（身份层重建） | INIT | 0 | — | — | — | Agent v2.0 |
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |

> 状态留痕最多保留 20 行，超出 20 行时旧行搬入 memory/ 对应日期归档。
