const path = require("path");
const {
  DATA_DIR,
  escapeHtml,
  hostFromUrl,
  isoBeijing,
  loadBrands,
  loadScoringConfig,
  normalizeUrl,
  parseArgs,
  readJson,
  slugify,
  toDateKey,
  writeJson
} = require("./lib/brandpulse-core");

const SIGNAL_RULES = [
  { dimension: "cmfInnovation", weight: 3, terms: ["钛", "titanium", "液态金属", "liquid metal", "陶瓷", "ceramic", "生物基", "bio-based", "再生材料", "涂层", "coating", "cmf"] },
  { dimension: "paradigmShift", weight: 3, terms: ["透明", "transparent", "无屏", "screenless", "三折", "tri-fold", "折叠", "foldable", "模块化", "modular", "概念", "concept"] },
  { dimension: "recognition", weight: 2, terms: ["家族化", "设计语言", "glyph", "iconic", "signature", "辨识度", "去logo", "视觉系统"] },
  { dimension: "transferability", weight: 2, terms: ["下放", "普及", "量产", "mass production", "供应链", "scale", "跨品类", "平台化"] },
  { dimension: "diffusionPotential", weight: 3, terms: ["国补", "入门", "主流", "大众", "低价", "affordable", "mid-range", "mass-market"] }
];

const NEGATIVE_TERMS = [
  "骁龙", "天玑", "处理器", "芯片升级", "跑分", "性能提升", "续航提升",
  "内存", "容量", "降价", "促销", "仅配置", "spec bump", "processor upgrade"
];

const MEDIA_TIERS = [
  { tier: "tier1_media", names: ["36kr.com", "ifanr.com", "ithome.com", "theverge.com", "wired.com", "engadget.com"] },
  { tier: "tier2_vertical", names: ["chongdiantou.com", "52audio.com", "dronedj.com", "notebookcheck.net"] }
];

function containsAny(text, terms) {
  return terms.some((term) => text.includes(term.toLowerCase()));
}

function sourceTier(candidate, brandsConfig) {
  const host = hostFromUrl(candidate.url || candidate.sourceUrl || "");
  const brand = brandsConfig.brands.find((item) => item.name === candidate.brand || item.nameEn === candidate.brand);
  const officialHosts = (brand?.officialSources || []).map(hostFromUrl).filter(Boolean);

  if (officialHosts.some((official) => host.endsWith(official))) {
    return { tier: "tier0_official", bonus: 12 };
  }

  const media = MEDIA_TIERS.find((item) => item.names.some((domain) => host.endsWith(domain)));
  if (media) return { tier: media.tier, bonus: media.tier === "tier1_media" ? 8 : 5 };

  const blockList = brandsConfig.sourcePriority?.blockList || [];
  if (blockList.some((name) => String(candidate.sourceName || "").includes(name))) {
    return { tier: "blocked", bonus: -40 };
  }

  return { tier: "unknown", bonus: 0 };
}

function scoreCandidate(candidate, scoringConfig, brandsConfig, dateKey, reviewThreshold) {
  const fullText = [
    candidate.title,
    candidate.summary,
    candidate.description,
    candidate.snippet,
    candidate.tags?.join(" ")
  ].filter(Boolean).join(" ").toLowerCase();

  const dimensions = Object.fromEntries(scoringConfig.dimensions.map((dimension) => [dimension.name, 0]));
  const matched = [];

  SIGNAL_RULES.forEach((rule) => {
    rule.terms.forEach((term) => {
      if (fullText.includes(term.toLowerCase())) {
        dimensions[rule.dimension] = Math.min(10, dimensions[rule.dimension] + rule.weight);
        matched.push(term);
      }
    });
  });

  const negativeMatches = NEGATIVE_TERMS.filter((term) => fullText.includes(term.toLowerCase()));
  const tier = sourceTier(candidate, brandsConfig);
  const weighted = {};
  const signalTermBonus = Math.min(32, matched.length * 8);
  const specPenalty = negativeMatches.length * 12;
  let total = tier.bonus + signalTermBonus;

  scoringConfig.dimensions.forEach((dimension) => {
    const value = dimensions[dimension.name] || 0;
    weighted[dimension.name] = Number((value * dimension.weight).toFixed(2));
    total += value * dimension.weight * 10;
  });

  total -= specPenalty;
  const score = Math.max(0, Math.min(100, Math.round(total)));
  const hasCoreSignal = scoringConfig.dimensions.some((dimension) => (dimensions[dimension.name] || 0) >= (scoringConfig.thresholds?.coreDimensionMin || 6));
  const shouldReview = score >= reviewThreshold && hasCoreSignal && tier.tier !== "blocked";

  return {
    ...candidate,
    title: escapeHtml(candidate.title || ""),
    summary: escapeHtml(candidate.summary || candidate.description || candidate.snippet || ""),
    url: normalizeUrl(candidate.url || candidate.sourceUrl || ""),
    score,
    confidence: Math.max(30, Math.min(95, 50 + tier.bonus + matched.length * 4 - negativeMatches.length * 8)),
    reviewStatus: tier.tier === "blocked" ? "rejected" : "needs_review",
    ruleScore: {
      sourceTier: tier.tier,
      sourceBonus: tier.bonus,
      signalTermBonus,
      specPenalty,
      matchedSignals: [...new Set(matched)],
      negativeMatches,
      dimensions,
      weighted,
      shouldReview,
      reasons: [
        matched.length ? `matched signal terms: ${[...new Set(matched)].join(", ")}` : "no strong visual-signal terms",
        negativeMatches.length ? `negative spec-only terms: ${negativeMatches.join(", ")}` : "no spec-only penalty",
        `source tier: ${tier.tier}`
      ]
    },
    candidateId: candidate.candidateId || `${slugify(candidate.brand || "unknown")}-${slugify(candidate.title || "candidate")}-${dateKey.replace(/-/g, "")}`,
    capturedAt: isoBeijing(dateKey)
  };
}

function main() {
  const args = parseArgs(process.argv);
  const dateKey = args.date || toDateKey();
  const input = args.input || path.join(DATA_DIR, "candidates.raw.json");
  const output = args.output || path.join(DATA_DIR, "candidates.scored.json");
  const candidates = readJson(input, []);
  const brandsConfig = loadBrands();
  const scoringConfig = loadScoringConfig();
  const reviewThreshold = Number(args.reviewThreshold || 40);

  if (!Array.isArray(candidates)) {
    throw new Error(`Expected array input: ${input}`);
  }

  const scored = candidates.map((candidate) => scoreCandidate(candidate, scoringConfig, brandsConfig, dateKey, reviewThreshold));
  writeJson(output, scored);
  console.log(`Scored ${scored.length} candidates -> ${output}`);
}

main();
