const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const DATA_DIR = path.join(ROOT, "data");
const PRODUCTS_DIR = path.join(ROOT, "products");
const ARCHIVE_DIR = path.join(PRODUCTS_DIR, "archive");

function readText(filePath) {
  return fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, "");
}

function readJson(filePath, fallback) {
  if (!fs.existsSync(filePath)) return fallback;
  return JSON.parse(readText(filePath));
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function loadBrands() {
  return readJson(path.join(ROOT, "brands.json"), { brands: [], categories: {} });
}

function loadProducts() {
  return readJson(path.join(PRODUCTS_DIR, "recent.json"), []);
}

function loadScoringConfig() {
  return readJson(path.join(ROOT, "vis-scoring-config.json"), { dimensions: [] });
}

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const part = argv[i];
    if (!part.startsWith("--")) continue;
    const key = part.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
    } else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

function toDateKey(date = new Date()) {
  const value = typeof date === "string" ? new Date(`${date}T00:00:00+08:00`) : date;
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function toBeijingTimestamp(dateKey, hourMinute = "22:00") {
  return `${dateKey} ${hourMinute}`;
}

function isoBeijing(dateKey, hourMinute = "22:00") {
  return `${dateKey}T${hourMinute}:00+08:00`;
}

function normalizeText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/https?:\/\/\S+/g, "")
    .replace(/[\s\-_—–|:：,，.。/\\()[\]【】"'“”]+/g, "");
}

function normalizeUrl(value) {
  if (!value) return "";
  try {
    const url = new URL(value);
    url.hash = "";
    const removable = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"];
    removable.forEach((key) => url.searchParams.delete(key));
    return url.toString().replace(/\/$/, "");
  } catch {
    return String(value).trim();
  }
}

function hostFromUrl(value) {
  try {
    return new URL(value).hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function productDate(product) {
  const raw = product.createdAt || product.time || "";
  const key = String(raw).slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(key) ? key : null;
}

function monthKey(dateKey) {
  return dateKey.slice(0, 7);
}

function uniqueBy(items, keyFn) {
  const seen = new Set();
  const output = [];
  items.forEach((item) => {
    const key = keyFn(item);
    if (!key || seen.has(key)) return;
    seen.add(key);
    output.push(item);
  });
  return output;
}

module.exports = {
  ROOT,
  DATA_DIR,
  PRODUCTS_DIR,
  ARCHIVE_DIR,
  readJson,
  writeJson,
  loadBrands,
  loadProducts,
  loadScoringConfig,
  parseArgs,
  toDateKey,
  toBeijingTimestamp,
  isoBeijing,
  normalizeText,
  normalizeUrl,
  hostFromUrl,
  slugify,
  escapeHtml,
  productDate,
  monthKey,
  uniqueBy
};
