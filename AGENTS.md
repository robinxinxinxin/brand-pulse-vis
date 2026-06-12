# BrandPulse 视觉信号追踪日报 — AI Agent 自动化说明文档

> **目标读者**: Codex / AI Agent（自动化执行）
> **最后更新**: 2026-06-07
> **语言**: 中文

---

## 1. 任务概述

**目标**: 每日追踪消费电子领域"改变视觉约束的源头信号"，筛选具有显著材料/工艺/范式创新意义的新品，更新数据文件并推送到 GitHub。

**执行频率**: 每日一次（建议北京时间 22:00 左右）

**核心原则**: 拒绝常规配置升级，只收录在以下至少一个维度有显著动作的产品：
- 材料/工艺（钛金属、透明注塑、生物基材料、全新CMF涂层）
- 范式转变（去屏幕化、概念性形态改变、Nothing风格透明设计）
- 供应链异动（高端前沿工艺首次下放到普及价位）

---

## 2. 品牌列表与搜索优先级

### 2.1 品牌列表（按品类）

| 品类 | 品牌 |
|------|------|
| 汽车 | 小米汽车、特斯拉、享界 |
| 手机/平板 | 华为、OPPO、三星、联想moto、Nothing、Ulefone |
| 可穿戴 | Oura、WHOOP、佳明Garmin |
| 音频 | 索尼、韶音Shokz |
| 智能家居 | 微软Surface、追觅Dreame |
| 扫地机器人 | 石头Roborock、科沃斯Ecovacs、云鲸Narwal |
| 割草机器人 | 库犸Mammotion、Segway Navimow、Worx Landroid |
| 泳池设备 | Beatbot、Aiper |
| 便携储能 | Bluetti、正浩EcoFlow |
| 智能投影 | 极米XGIMI、坚果JMGO |
| 电竞设备 | 玩家国度ROG |
| 出行工具 | 九号Ninebot、小牛NIU |
| 充电配件 | 安克Anker、倍思Baseus、绿联UGREEN、贝尔金Belkin、酷态科CUKTECH、罗马仕ROMOSS、闪极Sharge、优越者UNITEK、维奥技术VEOUT、艾欧提iOttie |
| 影像设备 | 大疆DJI、影石Insta360、GoPro |

### 2.2 信息源优先级

1. **T0 - 品牌官方**（官网、官方微博/公众号）— 优先使用 `site:` 语法限定官方域名
2. **T1 - 权威科技媒体**（36氪、爱范儿、IT之家、The Verge）
3. **T2 - 行业垂直媒体**（充电头网、音频应用、无人机之家）

**屏蔽**: 今日头条自媒体、百家号、搜狐号、网易号、企鹅号

---

## 3. 执行流程（每日必做）

### 步骤0: 自检脚本（必须执行）

```powershell
cd D:\robin-skills\trae solo\brand-pulse-vis
powershell -ExecutionPolicy Bypass -File ".\scripts\validate-brandpulse.ps1"
```

- 如果自检 **PASSED**: 继续执行
- 如果自检 **FAILED**: 先修复问题，修复完成后再继续

### 步骤1: 搜索新品

- 按品牌列表搜索，优先使用 `site:` 语法限定官方域名
- 搜索关键词示例: `"品牌名" 新品发布 2026年6月 设计 材质 工艺`
- 重点关注: 外观设计、工业设计创新、配色、材质、工艺
- **严格过滤**: 常规配置升级、仅换芯不换壳的产品 **不收录**

### 步骤2: 提取图片URL

- 访问每个新品的新闻页面或官方产品页
- 提取页面中的 `og:image` 标签内容（Open Graph封面图）
- 如果没有 `og:image`，提取页面中第一张产品高清图的URL
- 优先选择: 官方渲染图 > 媒体实拍图 > 任何高清产品图

**占位图兜底机制**: 如果遇到极高质量的源头信号但页面确实无图或抓取失败，允许使用占位图或留空。绝对不能因为找不到图片而丢弃高质量源头信号！

### 步骤3: 更新数据文件

#### 3.1 数据安全 — HTML实体转义

在将抓取到的 title 和 desc 写入 JSON 之前，必须进行标准 HTML 实体转义：
- `<` → `&lt;`
- `>` → `&gt;`
- `&` → `&amp;`
- `"` → `&quot;`

**中文引号处理**: 如果产品描述中包含中文引号（如 `"一镜双目"`），必须替换为转义的英文双引号 `\"`，否则会导致 JSON 解析失败！

#### 3.2 文件A: `products/recent.json`

- 读取现有 `recent.json`
- 将新品追加到数组 **开头**
- 检查是否有超过30天的旧数据（比较 `createdAt` 字段与当前日期）
- 将超过30天的条目移入 `products/archive/archive_YYYY-MM.json`
- **注意**: 归档路径是 `products/archive/archive_YYYY-MM.json`，不是 `products/archive-YYYY-MM.json`

#### 3.3 文件B: 同步 HTML 嵌入数据

使用同步脚本更新两个 HTML 文件中的嵌入数据和 `window.lastUpdated`：

```powershell
cd D:\robin-skills\trae solo\brand-pulse-vis
node scripts/sync-last-updated.js --date YYYY-MM-DD --time HH:MM
```

该脚本会：
1. 读取 `products/recent.json` 和 `brands.json`
2. 通过标记区 `// <BRANDPULSE-DATA-...>` 替换两个 HTML 文件中的嵌入数据
3. 更新 `window.lastUpdated` 时间戳
4. **两个文件必须同时更新**，确保时间戳一致

**不要手动编辑 HTML 中的嵌入数据**，始终通过同步脚本更新。

### 步骤4: 再次执行自检脚本（必须执行）

```powershell
cd D:\robin-skills\trae solo\brand-pulse-vis
powershell -ExecutionPolicy Bypass -File ".\scripts\validate-brandpulse.ps1"
```

- 如果自检 **PASSED**: 继续执行 Git 推送
- 如果自检 **FAILED**: 修复问题后重新执行步骤4

### 步骤5: Git 推送

```powershell
cd D:\robin-skills\trae solo\brand-pulse-vis
git add products/recent.json products/archive/archive_YYYY-MM.json brand-pulse-vis.html index.html
git commit -m "auto: 每日新品追踪更新 YYYY-MM-DD"
git config --global http.proxy http://127.0.0.1:10808
git config --global https.proxy http://127.0.0.1:10808
git push origin main
```

**注意**:
- PowerShell 使用 `;` 分隔命令，不能用 `&&`
- 如果推送被拒绝（non-fast-forward），先执行 `git pull origin main --rebase` 再推送

---

## 4. 数据格式规范

### 4.1 产品条目 JSON 结构

```json
{
  "id": "brand-product-YYYYMMDD",
  "brand": "品牌中文名",
  "category": "phone|wearable|gaming|charger|camera|vehicle|laptop|audio|robot|projector|energy|smart_home",
  "title": "产品标题 — 核心视觉约束变化",
  "summary": "一句话概括产品核心视觉/材质/工艺创新",
  "constraintChange": "具体描述改变了什么视觉约束",
  "time": "YYYY-MM-DD HH:MM",
  "score": 70.0,
  "confidence": 85,
  "reviewStatus": "verified",
  "visBreakdown": {
    "recognition": 20,
    "paradigmShift": 18,
    "cmfInnovation": 22,
    "transferability": 14,
    "diffusionPotential": 14
  },
  "visWeighted": {
    "diffusionPotential": 1.68,
    "recognition": 2.0,
    "transferability": 1.12,
    "cmfInnovation": 1.32,
    "paradigmShift": 0.72
  },
  "visTotal": 6.84,
  "facts": ["事实1", "事实2"],
  "analysis": {
    "whyItMatters": "为什么这个信号重要",
    "transferability": "可迁移性分析",
    "risk": "潜在风险"
  },
  "primarySource": {
    "tier": "tier0_official|tier1_media|tier2_ec",
    "name": "来源名称",
    "url": "https://...",
    "capturedAt": "YYYY-MM-DDTHH:MM:SS+08:00"
  },
  "evidence": [
    {
      "tier": "tier1_media",
      "name": "证据来源",
      "url": "https://...",
      "supports": ["product_exists", "design", "materials"]
    }
  ],
  "tags": ["标签1", "标签2"],
  "image": "https://...",
  "duplicateOf": null,
  "createdAt": "YYYY-MM-DDTHH:MM:SS+08:00",
  "updatedAt": "YYYY-MM-DDTHH:MM:SS+08:00",
  "url": "https://..."
}
```

### 4.2 精选口径（页面与校验脚本统一）

**精选条件**: `score >= 75` **OR** `visTotal >= 7`

页面和校验脚本使用相同口径，确保数字一致。

### 4.3 评分标准（VIS 视觉影响评分）

| 维度 | 权重 | 说明 |
|------|------|------|
| recognition | 0.10 | 视觉辨识度 |
| paradigmShift | 0.04 | 范式转变程度 |
| cmfInnovation | 0.06 | CMF创新程度 |
| transferability | 0.08 | 可迁移性 |
| diffusionPotential | 0.12 | 扩散潜力 |

**总分计算公式**: `visTotal = recognition*0.1 + paradigmShift*0.04 + cmfInnovation*0.06 + transferability*0.08 + diffusionPotential*0.12`

---

## 5. 自检脚本检查项

`validate-brandpulse.ps1` 执行以下检查：

| 检查项 | 说明 |
|--------|------|
| 必需文件存在 | SKILL.md, AGENTS.md, brands.json, vis-scoring-config.json, recent.json, 两个 HTML |
| brands.json 合法性 | 至少10个品牌 |
| 时间戳一致性 | 两个 HTML 的 `window.lastUpdated` 必须相同 |
| 前端 JS 语法 | 提取所有 `<script>` 块，通过 `node --check` 验证（需安装 Node.js） |
| 必需函数存在 | switchSection, initializeDashboard, renderBrandList, applyViewStateAndRender |
| 数据标记区 | 4个 `// <BRANDPULSE-DATA-...>` 标记在两个 HTML 中都存在 |
| 产品字段完整 | 17个必需字段 |
| ID唯一性 | 无重复 id |
| visBreakdown 完整 | 非零产品必须有完整评分 |
| 30天过期检查 | 超过30天的产品需归档 |
| 未来数据检查 | 不允许 createdAt 晚于 lastUpdated |
| 静态数字检查 | stat 元素必须使用 `-` 占位符，不能写死数字 |
| 精选口径 | score >= 75 OR visTotal >= 7 |

---

## 6. 特殊情况处理

### 6.1 今日无信号

如果某天搜索后没有发现任何符合严格过滤原则的新品，输出 `no-signal-YYYYMMDD` 条目（score=0, visTotal=0）。

### 6.2 Git 仓库异常

如果 `brand-pulse-vis` 目录下没有 `.git` 目录：

```powershell
cd D:\robin-skills\trae solo\brand-pulse-vis
git init
git remote add origin https://github.com/robinxinxinxin/brand-pulse-vis.git
git fetch origin main
git reset origin/main
```

### 6.3 图片抓取失败

允许使用占位图或留空 `image: ""`。**绝对不能因为找不到图片而丢弃高质量源头信号**。

---

## 7. 关键文件路径

| 文件 | 路径 | 说明 |
|------|------|------|
| 主页面 | `brand-pulse-vis.html` | 展示页（GitHub Pages） |
| 入口页 | `index.html` | 本地入口页 |
| 近期数据 | `products/recent.json` | 近30天产品数据 |
| 归档数据 | `products/archive/archive_YYYY-MM.json` | 按月归档 |
| 品牌配置 | `brands.json` | 监控品牌池 |
| 评分配置 | `vis-scoring-config.json` | VIS评分权重 |
| 同步脚本 | `scripts/sync-last-updated.js` | 同步数据到HTML（标记区替换） |
| 校验脚本 | `scripts/validate-brandpulse.ps1` | 全链路自检 |
| 本说明 | `AGENTS.md` | AI Agent自动化说明 |

---

## 8. 代理交接记录

| 日期 | 执行代理 | 收录信号数 | 备注 |
|------|----------|-----------|------|
| 2026-06-04 | SOLO | 3 | 华为nova16 Ultra、ROG COMPUTEX 2026 20周年系列、九号2026四款新车 |
| 2026-06-06 | SOLO | 1 | ROG Edition 20系列（Crystal Lens透明材质+Radiant Gold金色工艺） |
| 2026-06-07 | SOLO | 0 | 自动化链路优化：标记区同步、前端语法检查、精选口径统一、静态数字修复 |
| 2026-06-12 | 人工 | — | 修复一级菜单切换刷新契约：①「今日更新」不再被品牌监控过滤误杀（shouldApplyMonitoredBrandFilter 仅精选生效）；②切换菜单时 resetSectionTransientState 清空搜索词+品类筛选；③众筹加载失败显示 crowdfundingLoadError 明确文案；④allCount/todayCount 统计逻辑修正（改用 defaultProductsData.length）；⑤提取 getTodayKey/matchesMonitoredBrand/getEmptyStateMessage 等辅助函数 |

---

## 9. 常见错误与修复

### 9.1 JSON 解析失败
- **原因**: 中文引号 `"` 未替换为转义的英文双引号 `\"`
- **修复**: 全局替换中文引号为 `\"`

### 9.2 Git 推送被拒绝
- **原因**: 远程分支有本地没有的提交
- **修复**: `git pull origin main --rebase` 后再推送

### 9.3 同步脚本破坏 HTML 结构
- **原因**: 正则替换误匹配（已通过标记区机制修复）
- **修复**: 确保 HTML 中包含 `// <BRANDPULSE-DATA-...>` 标记区

### 9.4 校验报 "Static number found"
- **原因**: HTML 中 stat 元素写死了数字而非 `-` 占位符
- **修复**: 将对应元素的数字改为 `-`，页面加载时 JS 会自动填充

---

> **提示**: 本任务的核心价值在于"严格过滤"。宁可少收录，也不要降低标准。如果某天没有符合条件的信号，如实输出"今日无视觉约束变化信号"即可。
