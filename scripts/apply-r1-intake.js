const path = require("path");
const {
  DATA_DIR,
  ROOT,
  loadBrands,
  parseArgs,
  readJson,
  writeJson
} = require("./lib/brandpulse-core");

function main() {
  const args = parseArgs(process.argv);
  const input = args.input || path.join(DATA_DIR, "r1-intake.review.json");
  const dryRun = Boolean(args["dry-run"]);
  const reviewed = readJson(input, []);
  const brandsConfig = loadBrands();
  const existingNames = new Set(brandsConfig.brands.map((brand) => brand.name));
  const additions = [];

  reviewed.forEach((item) => {
    if (item.r1Decision?.action !== "add_to_watchlist") return;
    if (!item.brand || existingNames.has(item.brand)) return;

    const scoring = item.r1Scoring || {};
    const decision = item.r1Decision || {};

    additions.push({
      name: item.brand,
      nameEn: item.nameEn || item.brand,
      category: item.category || "unknown",
      type: item.type || "R1新增观察品牌",
      monitored: true,
      officialSources: item.officialSources || [],
      aestheticTags: item.aestheticTags || [],
      addedBy: "r1-intake-filter-v2",
      addedReason: decision.explanation || "",
      r1Scoring: {
        designScore: scoring.designScore,
        trackLine: decision.trackLine,
        regionScore: scoring.regionScore,
        commercialScore: scoring.commercialScore,
        weightedTotal: scoring.weightedTotal
      },
      addedAt: new Date().toISOString()
    });
    existingNames.add(item.brand);
  });

  if (!dryRun && additions.length) {
    brandsConfig.brands.push(...additions);
    brandsConfig.lastUpdated = new Date().toISOString().slice(0, 10);
    writeJson(path.join(ROOT, "brands.json"), brandsConfig);
  }

  console.log(JSON.stringify({
    dryRun,
    additions: additions.map((brand) => ({
      name: brand.name,
      category: brand.category,
      trackLine: brand.r1Scoring?.trackLine,
      designScore: brand.r1Scoring?.designScore,
      reason: brand.addedReason
    }))
  }, null, 2));
}

main();
