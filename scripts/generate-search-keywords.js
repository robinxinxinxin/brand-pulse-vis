const path = require("path");
const {
  DATA_DIR,
  loadBrands,
  parseArgs,
  toDateKey,
  uniqueBy,
  writeJson
} = require("./lib/brandpulse-core");

const CATEGORY_TERMS = {
  car: ["外观设计", "车身颜色", "座舱材质", "concept design"],
  phone: ["工业设计", "CMF", "材质", "transparent design", "hinge design"],
  wearable: ["无屏", "材料", "佩戴形态", "screenless wearable"],
  audio: ["开放式", "佩戴形态", "透明外壳", "open-ear design"],
  smart: ["工业设计", "新形态", "材质", "product design"],
  robot: ["结构设计", "基站形态", "材料工艺", "robot design"],
  lawn: ["无边界", "结构设计", "户外材质", "robot mower design"],
  pool: ["泳池机器人", "结构设计", "防水材质", "pool robot design"],
  power: ["便携储能", "外观设计", "模块化", "portable power design"],
  projector: ["光机结构", "家居化设计", "投影形态", "projector design"],
  gaming: ["电竞设计", "散热结构", "透明", "gaming CMF"],
  mobility: ["电动车", "外观设计", "车身材质", "mobility design"],
  accessory: ["Qi2", "折叠", "透明", "CMF", "charging station design"],
  camera: ["模块化", "云台", "影像形态", "camera industrial design"]
};

const BASE_TEMPLATES = [
  "{brand} 新品发布 {monthCn} 设计 材质 工艺",
  "{brand} 外观设计 CMF 配色 材质 {year}",
  "{brand} 工业设计 创新 透明 钛 折叠 {year}",
  "{brandEn} new product {year} design material CMF",
  "{brandEn} industrial design material process {year}"
];

function format(template, brand, dateKey) {
  const [year, month] = dateKey.split("-");
  return template
    .replace(/\{brand\}/g, brand.name)
    .replace(/\{brandEn\}/g, brand.nameEn || brand.name)
    .replace(/\{year\}/g, year)
    .replace(/\{monthCn\}/g, `${Number(month)}月`);
}

function officialQueries(brand) {
  return (brand.officialSources || [])
    .map((source) => {
      try {
        const host = new URL(source).hostname;
        return [
          `site:${host} ${brand.name} 新品 设计 材质`,
          `site:${host} ${brand.nameEn || brand.name} new product design`
        ];
      } catch {
        return [];
      }
    })
    .flat();
}

function brandQueries(brand, dateKey) {
  const categoryTerms = CATEGORY_TERMS[brand.category] || ["设计", "材质", "工艺"];
  const scripted = BASE_TEMPLATES.map((template) => format(template, brand, dateKey));
  const categorySpecific = categoryTerms.map((term) => `${brand.name} ${term} 新品 ${dateKey.slice(0, 7)}`);
  const official = officialQueries(brand);
  return uniqueBy([...official, ...scripted, ...categorySpecific], (query) => query.toLowerCase());
}

function main() {
  const args = parseArgs(process.argv);
  const dateKey = args.date || toDateKey();
  const brands = loadBrands().brands.filter((brand) => brand.monitored !== false);
  const limitPerBrand = Number(args.limitPerBrand || 10);

  const plan = {
    date: dateKey,
    generatedAt: new Date().toISOString(),
    mode: "scripted-keyword-plan",
    notes: [
      "These queries provide stable coverage. Let the model add only incremental, brand-specific queries.",
      "Prioritize official site: queries before general media searches."
    ],
    brands: brands.map((brand) => ({
      name: brand.name,
      nameEn: brand.nameEn || brand.name,
      category: brand.category,
      type: brand.type || "",
      queries: brandQueries(brand, dateKey).slice(0, limitPerBrand)
    }))
  };

  const output = args.output || path.join(DATA_DIR, `search-keywords-${dateKey}.json`);
  writeJson(output, plan);
  console.log(`Generated ${plan.brands.length} brand keyword plans -> ${output}`);
}

main();
