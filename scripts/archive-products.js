const fs = require("fs");
const path = require("path");
const {
  ARCHIVE_DIR,
  PRODUCTS_DIR,
  monthKey,
  parseArgs,
  productDate,
  readJson,
  toDateKey,
  writeJson
} = require("./lib/brandpulse-core");

function main() {
  const args = parseArgs(process.argv);
  const dateKey = args.date || toDateKey();
  const dryRun = Boolean(args["dry-run"]);
  const cutoff = new Date(`${dateKey}T00:00:00+08:00`);
  cutoff.setDate(cutoff.getDate() - Number(args.days || 30));

  const recentPath = path.join(PRODUCTS_DIR, "recent.json");
  const products = readJson(recentPath, []);
  const keep = [];
  const archives = new Map();

  products.forEach((product) => {
    const createdKey = productDate(product);
    if (!createdKey) {
      keep.push(product);
      return;
    }
    const created = new Date(`${createdKey}T00:00:00+08:00`);
    if (created < cutoff || created > new Date(`${dateKey}T23:59:59+08:00`)) {
      const key = monthKey(createdKey);
      if (!archives.has(key)) archives.set(key, []);
      archives.get(key).push(product);
    } else {
      keep.push(product);
    }
  });

  const summary = {
    date: dateKey,
    dryRun,
    kept: keep.length,
    archived: [...archives.entries()].map(([month, items]) => ({ month, count: items.length }))
  };

  if (!dryRun) {
    writeJson(recentPath, keep);
    fs.mkdirSync(ARCHIVE_DIR, { recursive: true });
    archives.forEach((items, month) => {
      const archivePath = path.join(ARCHIVE_DIR, `archive_${month}.json`);
      const existing = readJson(archivePath, []);
      const byId = new Map([...existing, ...items].map((item) => [item.id, item]));
      const merged = [...byId.values()].sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)));
      writeJson(archivePath, merged);
    });
  }

  console.log(JSON.stringify(summary, null, 2));
}

main();
