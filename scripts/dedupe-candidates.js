const path = require("path");
const {
  DATA_DIR,
  loadProducts,
  normalizeText,
  normalizeUrl,
  parseArgs,
  readJson,
  writeJson
} = require("./lib/brandpulse-core");

function duplicateKey(item) {
  const url = normalizeUrl(item.url || item.primarySource?.url || "");
  if (url) return `url:${url}`;
  return `text:${normalizeText(`${item.brand || ""}${item.title || ""}`)}`;
}

function titleSimilarity(a, b) {
  const left = new Set(normalizeText(a).match(/[\p{Letter}\p{Number}]{2,}/gu) || []);
  const right = new Set(normalizeText(b).match(/[\p{Letter}\p{Number}]{2,}/gu) || []);
  if (!left.size || !right.size) return 0;
  const overlap = [...left].filter((token) => right.has(token)).length;
  return overlap / Math.max(left.size, right.size);
}

function main() {
  const args = parseArgs(process.argv);
  const input = args.input || path.join(DATA_DIR, "candidates.scored.json");
  const reviewOutput = args.output || path.join(DATA_DIR, "candidates.review.json");
  const rejectedOutput = args.rejected || path.join(DATA_DIR, "candidates.rejected.json");
  const candidates = readJson(input, []);
  const existing = loadProducts();
  const existingKeys = new Map(existing.map((product) => [duplicateKey(product), product.id]));
  const seen = new Map();
  const review = [];
  const rejected = [];

  candidates
    .slice()
    .sort((a, b) => (b.score || 0) - (a.score || 0))
    .forEach((candidate) => {
      const key = duplicateKey(candidate);
      const sameExistingId = existingKeys.get(key);
      const similarExisting = existing.find((product) => (
        product.brand === candidate.brand && titleSimilarity(product.title, candidate.title) >= 0.72
      ));
      const sameBatch = seen.get(key);

      if (sameExistingId || similarExisting || sameBatch) {
        rejected.push({
          ...candidate,
          rejectionReason: sameExistingId
            ? `duplicate URL of existing product ${sameExistingId}`
            : similarExisting
              ? `similar to existing product ${similarExisting.id}`
              : `duplicate of candidate ${sameBatch}`
        });
        return;
      }

      seen.set(key, candidate.candidateId || candidate.title);
      if (candidate.ruleScore?.shouldReview) {
        review.push(candidate);
      } else {
        rejected.push({ ...candidate, rejectionReason: "below scripted review threshold" });
      }
    });

  writeJson(reviewOutput, review);
  writeJson(rejectedOutput, rejected);
  console.log(`Review candidates: ${review.length} -> ${reviewOutput}`);
  console.log(`Rejected candidates: ${rejected.length} -> ${rejectedOutput}`);
}

main();
