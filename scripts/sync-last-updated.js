const fs = require("fs");
const path = require("path");
const {
  ROOT,
  parseArgs,
  toBeijingTimestamp,
  toDateKey
} = require("./lib/brandpulse-core");

const MARKERS = {
  brandsStart: "// <BRANDPULSE-DATA-BRANDS-START>",
  brandsEnd: "// <BRANDPULSE-DATA-BRANDS-END>",
  productsStart: "// <BRANDPULSE-DATA-PRODUCTS-START>",
  productsEnd: "// <BRANDPULSE-DATA-PRODUCTS-END>"
};

function replaceBetween(content, startMarker, endMarker, replacement) {
  const startIdx = content.indexOf(startMarker);
  const endIdx = content.indexOf(endMarker);
  if (startIdx === -1) {
    throw new Error(`Start marker not found: ${startMarker}`);
  }
  if (endIdx === -1) {
    throw new Error(`End marker not found: ${endMarker}`);
  }
  if (endIdx <= startIdx) {
    throw new Error(`End marker appears before start marker: ${startMarker}`);
  }
  const before = content.substring(0, startIdx + startMarker.length);
  const after = content.substring(endIdx);
  return before + "\n" + replacement + "\n" + after;
}

function syncFile(filePath, timestamp, dryRun) {
  const before = fs.readFileSync(filePath, "utf8");
  const recentPath = path.join(ROOT, "products", "recent.json");
  const brandsPath = path.join(ROOT, "brands.json");
  const recent = JSON.parse(fs.readFileSync(recentPath, "utf8"));
  const brands = JSON.parse(fs.readFileSync(brandsPath, "utf8"));

  // Update timestamp
  if (!/window\.lastUpdated\s*=\s*'[^']+';/.test(before)) {
    throw new Error(`window.lastUpdated not found in ${filePath}`);
  }
  let after = before.replace(/window\.lastUpdated\s*=\s*'[^']+';/, `window.lastUpdated = '${timestamp}';`);

  // Replace brands data between markers
  const embeddedBrands = `let brandsData = ${JSON.stringify(brands, null, 2)};`;
  after = replaceBetween(after, MARKERS.brandsStart, MARKERS.brandsEnd, embeddedBrands);

  // Replace products data between markers
  const embeddedProducts = `let productsData = ${JSON.stringify(recent, null, 2)}\n;\n  defaultProductsData = productsData;\n  console.log('[BrandPulse] Using embedded product data');`;
  after = replaceBetween(after, MARKERS.productsStart, MARKERS.productsEnd, embeddedProducts);

  if (!dryRun) fs.writeFileSync(filePath, after, "utf8");
  return before !== after;
}

function main() {
  const args = parseArgs(process.argv);
  const dateKey = args.date || toDateKey();
  const time = args.time || "22:00";
  const dryRun = Boolean(args["dry-run"]);
  const timestamp = toBeijingTimestamp(dateKey, time);
  const filePairs = [
    { src: path.join(ROOT, "index.html"), dest: null },  // primary
    { src: path.join(ROOT, "brand-pulse-vis.html"), dest: null }  // auto-copied from primary
  ];

  // Sync primary file only
  const primary = filePairs[0];
  const primaryChanged = syncFile(primary.src, timestamp, dryRun);

  // Auto-copy primary to secondary (brand-pulse-vis.html)
  if (!dryRun && primaryChanged) {
    const secondaryPath = filePairs[1].src;
    const primaryContent = fs.readFileSync(primary.src, "utf8");
    fs.writeFileSync(secondaryPath, primaryContent, "utf8");
    console.log(JSON.stringify({
      timestamp, dryRun,
      primary: primary.src,
      synced: primaryChanged,
      copied_to: secondaryPath
    }, null, 2));
    return;
  }

  // Fallback: sync both independently for dry-run or no-change cases
  const changed = [primary].concat(filePairs.slice(1)).map((f) => ({
    file: f.src,
    changed: f.src === primary.src ? primaryChanged : syncFile(f.src, timestamp, dryRun)
  }));
  console.log(JSON.stringify({ timestamp, dryRun, changed }, null, 2));
}

main();
