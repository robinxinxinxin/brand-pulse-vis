/**
 * R1 入库筛选脚本 v2 — 高级设计感导向的结构化评分
 *
 * 评分模型：
 *   - 高级设计感 60%（6 子维度，10 分制，≥6 分准入）
 *   - 地域成立度 20%（10 分制）
 *   - 年龄/人群适配 10%（10 分制）
 *   - 商业与传播验证 10%（10 分制）
 *
 * 三级分类：
 *   - 商业追踪线：设计感 ≥4 且 地域 ≥3 且 商业 ≥3
 *   - 设计启发线：设计感 ≥4 但 地域或商业 <3
 *   - 观察线：设计感 2-4
 *   - 剔除：设计感 <2
 */

const path = require("path");
const {
  DATA_DIR,
  loadBrands,
  parseArgs,
  readJson,
  writeJson
} = require("./lib/brandpulse-core");

// ============================================================
// 评分维度定义 — 信号词 + 评分逻辑
// ============================================================

const DESIGN_DIMENSIONS = [
  {
    id: "premiumFeel",
    name: "高级感/精致克制",
    weight: 0.30,
    maxScore: 10,
    positive: [
      { terms: ["克制", " restrained", "减法", "less is more", "留白", "breathing"], points: 2 },
      { terms: ["精致", " refined", "精致感", "完成度高", "polished", "精密", "精致化"], points: 2 },
      { terms: ["秩序感", "order", "秩序", "逻辑清晰", "structured", "工业设计", "标杆"], points: 1.5 },
      { terms: ["品质感", "quality", "premium", "高级", "mature", "成熟", "品质", "高级感"], points: 1.5 },
      { terms: ["品牌气质", "brand identity", "品牌调性", "品牌语言", "稳定", "品牌影响力"], points: 1 }
    ],
    negative: [
      { terms: ["堆砌", "overdesigned", "过度设计", "元素过多", "杂乱"], points: -2 },
      { terms: ["廉价", "cheap", "塑料感", "粗糙", "low-end"], points: -2 },
      { terms: ["无印式", "muji style", "日系简约", "无印良品"], points: -3 }
    ]
  },
  {
    id: "designIdentity",
    name: "设计识别度",
    weight: 0.20,
    maxScore: 10,
    positive: [
      { terms: ["识别度高", "iconic", "标志性", "轮廓独特", "distinctive silhouette", "高识别度", "极致", "标杆品牌", "教科书"], points: 3 },
      { terms: ["设计语言", "design language", "家族化", "系列化", "一致性", "家族化设计", "统一设计", "设计标杆"], points: 2 },
      { terms: ["差异化", "differentiated", "区别于", "独特", "unique", "独创", "独树一帜", "罕见"], points: 2 },
      { terms: ["记忆点", "visual anchor", "视觉焦点", "signature", "跨品类", "跨品类迁移", "迁移价值", "影响力"], points: 1.5 }
    ],
    negative: [
      { terms: ["公模", "OEM", "generic", "同质化", "千篇一律"], points: -3 },
      { terms: ["猎奇", "gimmicky", "噱头", "夸张造型"], points: -2 },
      { terms: ["透明", "赛博朋克", "cyberpunk", "透明外壳"], points: -2 }
    ]
  },
  {
    id: "proportionControl",
    name: "比例与形体控制",
    weight: 0.167,
    maxScore: 10,
    positive: [
      { terms: ["比例", "proportion", "体块", "形体", "厚薄", "轮廓", "造型", "小巧", "体积", "极小体积", "腔体", "腔体设计", "声学腔体"], points: 2 },
      { terms: ["圆角", "fillet", "边界", "过渡", "transition", "曲面", "曲面玻璃", "过渡"], points: 2 },
      { terms: ["多视角", "multi-angle", "各角度", "360度", "内外壳"], points: 1.5 },
      { terms: ["视觉重心", "visual center", "稳定", "balanced", "分量感", "统一"], points: 1.5 }
    ],
    negative: [
      { terms: ["头重脚轻", "比例失调", "笨重", "bulky", "臃肿"], points: -2 },
      { terms: ["幼稚", "childish", "玩具感", "toy-like"], points: -2 }
    ]
  },
  {
    id: "cmfQuality",
    name: "材质与CMF质感",
    weight: 0.133,
    maxScore: 10,
    positive: [
      { terms: ["cmf", "材质", "material", "钛", "titanium", "陶瓷", "ceramic", "皮革", "编织", "铝合金", "皮革纹理", "编织材料", "编织网"], points: 2 },
      { terms: ["表面处理", "surface finish", "哑光", "matte", "亮面", "anodized", "阳极氧化", "涂层", "coating", "cnc", "硬质阳极氧化"], points: 2 },
      { terms: ["材质搭配", "material mix", "金属", "metal", "织物", "fabric", "材料对比", "材料选择"], points: 1.5 },
      { terms: ["触感", "tactile", "手感", "grain", "硅胶", "工程塑料"], points: 1 }
    ],
    negative: [
      { terms: ["廉价色", "过度饱和", "garish", "撞色", "clashing colors"], points: -2 },
      { terms: ["渐变色", "gradient"], points: -1 }
    ]
  },
  {
    id: "structuralDetail",
    name: "结构表达与细节完成度",
    weight: 0.117,
    maxScore: 10,
    positive: [
      { terms: ["结构", "structure", "分件线", "parting line", "装配", "assembly", "结构拆件", "拆件逻辑", "拆件方式", "结构创新", "结构表达", "结构可视化"], points: 2 },
      { terms: ["按键", "button", "接口", "port", "细节设计", "detail design", "按键布局", "传感器布局", "开孔位置"], points: 2 },
      { terms: ["工艺", "craftsmanship", "量产可行", "manufacturable", "可实现", "模块化", "标准化模块", "模块化电池", "防水密封", "防水连接"], points: 1.5 },
      { terms: ["扎实", "solid", "可信", "credible build", "成熟", "精密", "顶级"], points: 1 }
    ],
    negative: [
      { terms: ["概念图", "concept only", "渲染", "rendering only", "无法落地"], points: -2 },
      { terms: ["缝隙", "gap", "装配差", "poor fit"], points: -1 }
    ]
  },
  {
    id: "timelessness",
    name: "长期耐看性/可沉淀性",
    weight: 0.083,
    maxScore: 10,
    positive: [
      { terms: ["经典", "classic", " timeless", "耐看", "enduring", "复古", "经典视觉", "经典元素"], points: 2 },
      { terms: ["可沉淀", "方法论", "methodology", "可复用", "reusable", "参考价值", "直接参考", "直接迁移"], points: 2 },
      { terms: ["迭代", "iterative", "可发展", "evolvable", "延展", "产品线", "持续创新"], points: 1.5 },
      { terms: ["多场景", "versatile", "cross-scene", "跨产品线", "参考"], points: 1 }
    ],
    negative: [
      { terms: ["追热点", "trend-chasing", "短期", "short-lived", "快消"], points: -2 },
      { terms: ["网红", "viral", "爆款", "fad"], points: -1 }
    ]
  }
];

const REGION_DIMENSION = {
  id: "region", name: "地域成立度", maxScore: 10,
  positive: [
    { terms: ["中国", "china", "一二线", "一线城市", "上海", "北京", "深圳", "杭州"], points: 3 },
    { terms: ["欧美", "europe", "america", "us", "uk", "germany", "北欧", "nordic", "scandinavian"], points: 2 },
    { terms: ["新一线", "成都", "武汉", "南京", "苏州", "下沉"], points: 1.5 },
    { terms: ["日韩", "japan", "korea", "亚太", "asia pacific"], points: 0.5 }
  ]
};

const AUDIENCE_DIMENSION = {
  id: "audience", name: "年龄/人群适配", maxScore: 10,
  positive: [
    { terms: ["25-40", "成熟消费", "mature consumer", "中产", "middle class", "白领"], points: 3 },
    { terms: ["18-24", "年轻", "youth", "趋势", "trend"], points: 1.5 },
    { terms: ["40-55", "品质消费", "quality conscious", "家居", "home"], points: 1.5 },
    { terms: ["设计师", "designer", "创意人群", "creative", "专业"], points: 1 }
  ]
};

const COMMERCIAL_DIMENSION = {
  id: "commercial", name: "商业与传播验证", maxScore: 10,
  positive: [
    { terms: ["电商", "e-commerce", "热销", "bestseller", "持续出现", "持续曝光"], points: 2.5 },
    { terms: ["用户好评", "user review", "接受度高", "well received"], points: 2.5 },
    { terms: ["品牌带动", "industry influence", "影响其他品牌", "trendsetter"], points: 1.5 },
    { terms: ["可转化", "transferable", "可提案", "proposal ready"], points: 1.5 }
  ]
};

const HARD_NEGATIVE_RULES = [
  { name: "纯参数导向", terms: ["跑分", "处理器", "芯片升级", "续航提升", "内存", "容量", "刷新率", "性能提升", "spec bump"] },
  { name: "明确不擅长品类", terms: ["家具", "大型钣金", "医疗"] },
  { name: "成本失控风险", terms: ["奢华", "高定", "限量珠宝"] }
];

// ============================================================
// 评分引擎
// ============================================================

function textOf(item) {
  return [
    item.brand, item.nameEn, item.category, item.type,
    item.reason, item.whyRelevant, item.designNotes,
    item.aestheticTags?.join(" "), item.signals?.join(" "),
    item.regionNotes, item.audienceNotes, item.commercialNotes
  ].filter(Boolean).join(" ").toLowerCase();
}

function scoreDimension(text, dim) {
  let score = 0;
  const hits = [];
  if (dim.positive) {
    dim.positive.forEach((rule) => {
      const matched = rule.terms.filter((t) => text.includes(t.toLowerCase()));
      if (matched.length > 0) {
        const pts = Math.min(rule.points, matched.length * rule.points * 0.6);
        score += pts;
        hits.push({ type: "positive", matched, points: pts });
      }
    });
  }
  if (dim.negative) {
    dim.negative.forEach((rule) => {
      const matched = rule.terms.filter((t) => text.includes(t.toLowerCase()));
      if (matched.length > 0) {
        score += rule.points;
        hits.push({ type: "negative", matched, points: rule.points });
      }
    });
  }
  score = Math.max(0, Math.min(dim.maxScore, score));
  return { score: Math.round(score * 10) / 10, hits };
}

function computeDesignTotal(subScores) {
  // 加权平均：每个子维度 0-10 分，按权重求加权平均，总分 0-10
  let weightedSum = 0;
  let weightSum = 0;
  subScores.forEach((s) => { weightedSum += s.score * s.weight; weightSum += s.weight; });
  const avg = weightSum > 0 ? weightedSum / weightSum : 0;
  return { totalScore: Math.round(avg * 10) / 10, subScores };
}

function checkHardNegatives(text) {
  return HARD_NEGATIVE_RULES.filter((rule) =>
    rule.terms.some((t) => text.includes(t.toLowerCase()))
  ).map((r) => r.name);
}

// ============================================================
// 决策引擎
// ============================================================

function evaluateItem(item, brandsConfig) {
  const text = textOf(item);
  const hardNegatives = checkHardNegatives(text);

  const designSubScores = DESIGN_DIMENSIONS.map((dim) => {
    const { score, hits } = scoreDimension(text, dim);
    return { id: dim.id, name: dim.name, weight: dim.weight, score, hits };
  });
  const { totalScore: designScore, subScores } = computeDesignTotal(designSubScores);
  const { score: regionScore } = scoreDimension(text, REGION_DIMENSION);
  const { score: audienceScore } = scoreDimension(text, AUDIENCE_DIMENSION);
  const { score: commercialScore } = scoreDimension(text, COMMERCIAL_DIMENSION);

  const weightedTotal = Math.round(
    designScore * 0.6 + regionScore * 0.2 + audienceScore * 0.1 + commercialScore * 0.1
  ) / 10 * 100;

  const existingBrand = brandsConfig.brands.some((b) =>
    b.name === item.brand || b.nameEn === item.brand
  );

  let trackLine, action;
  if (hardNegatives.length > 0) {
    trackLine = "reject"; action = "reject";
  } else if (designScore < 2) {
    trackLine = "reject"; action = "reject";
  } else if (designScore >= 4 && regionScore >= 3 && commercialScore >= 3) {
    trackLine = "commercial_track"; action = existingBrand ? "already_tracked" : "add_to_watchlist";
  } else if (designScore >= 4) {
    trackLine = "design_inspiration"; action = existingBrand ? "already_tracked" : "add_to_watchlist";
  } else {
    trackLine = "observe"; action = "observe";
  }

  return {
    ...item,
    r1Scoring: {
      version: "v2",
      designScore: Math.round(designScore * 10) / 10,
      designSubScores: subScores.map((s) => ({ id: s.id, name: s.name, score: s.score, weight: s.weight })),
      regionScore: Math.round(regionScore * 10) / 10,
      audienceScore: Math.round(audienceScore * 10) / 10,
      commercialScore: Math.round(commercialScore * 10) / 10,
      weightedTotal: Math.round(weightedTotal * 10) / 10
    },
    r1Decision: {
      version: "v2", action, trackLine, existingBrand, hardNegatives,
      requiresRobinFinalReview: action !== "reject",
      explanation: explainDecision(trackLine, designScore, regionScore, commercialScore, hardNegatives, subScores)
    }
  };
}

function explainDecision(trackLine, designScore, regionScore, commercialScore, hardNegatives, subScores) {
  const topDims = subScores.sort((a, b) => b.score - a.score).slice(0, 2)
    .map((s) => `${s.name}(${s.score})`).join("、");
  if (hardNegatives.length > 0) return `触发硬性否决：${hardNegatives.join("、")}，直接剔除。`;
  if (trackLine === "reject") return `设计感 ${designScore}/10 未达准入门槛（≥6），剔除。${topDims ? `最强维度：${topDims}` : ""}`;
  if (trackLine === "commercial_track") return `设计感 ${designScore}/10 + 地域 ${regionScore}/10 + 商业 ${commercialScore}/10 → 商业追踪线，建议重点录入。核心设计价值：${topDims}`;
  if (trackLine === "design_inspiration") return `设计感 ${designScore}/10 较强，但地域(${regionScore})或商业(${commercialScore})验证不足 → 设计启发线，录入为设计参考。核心设计价值：${topDims}`;
  return `设计感 ${designScore}/10 达到观察门槛，但证据不够充分，建议先观察。${topDims ? `参考维度：${topDims}` : ""}`;
}

// ============================================================
// 主流程
// ============================================================

function main() {
  const args = parseArgs(process.argv);
  const input = args.input || path.join(DATA_DIR, "r1-intake.raw.json");
  const output = args.output || path.join(DATA_DIR, "r1-intake.review.json");
  const rejectedOutput = args.rejected || path.join(DATA_DIR, "r1-intake.rejected.json");
  const items = readJson(input, []);
  const brandsConfig = loadBrands();

  if (!Array.isArray(items)) throw new Error(`Expected array input: ${input}`);

  const reviewed = items.map((item) => evaluateItem(item, brandsConfig));
  const accepted = reviewed.filter((item) => item.r1Decision.action !== "reject");
  const rejected = reviewed.filter((item) => item.r1Decision.action === "reject");

  const commercialTrack = accepted.filter((i) => i.r1Decision.trackLine === "commercial_track");
  const designInspiration = accepted.filter((i) => i.r1Decision.trackLine === "design_inspiration");
  const observe = accepted.filter((i) => i.r1Decision.trackLine === "observe");

  writeJson(output, accepted);
  writeJson(rejectedOutput, rejected);

  console.log("=".repeat(60));
  console.log("R1 上游入口筛选结果（v2 高级设计感模型）");
  console.log("=".repeat(60));
  console.log(`候选总数: ${items.length}`);
  console.log(`  商业追踪线: ${commercialTrack.length}`);
  console.log(`  设计启发线: ${designInspiration.length}`);
  console.log(`  观察线:     ${observe.length}`);
  console.log(`  剔除:       ${rejected.length}`);
  console.log("-".repeat(60));
  console.log(`通过: ${output}`);
  console.log(`剔除: ${rejectedOutput}`);
  console.log("=".repeat(60));

  try {
    const { generateReport } = require("./r1-report.js");
    generateReport();
  } catch (err) {
    console.error("Report generation failed:", err.message);
  }
}

main();
