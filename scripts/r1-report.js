/**
 * R1 报告生成器 v2 — 展示设计感拆解、三级分类、审美方向
 */
const fs = require("fs");
const path = require("path");
const { DATA_DIR, readJson } = require("./lib/brandpulse-core");

const HTML_TEMPLATE = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>R1 上游入口筛选结果</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
    background: #0d1117;
    color: #c9d1d9;
    padding: 40px 20px;
    line-height: 1.6;
  }
  .container { max-width: 1100px; margin: 0 auto; }
  h1 { color: #58a6ff; font-size: 24px; margin-bottom: 8px; }
  .subtitle { color: #8b949e; font-size: 14px; margin-bottom: 32px; }
  .section { margin-bottom: 36px; }
  .section-title {
    font-size: 15px; font-weight: 600; margin-bottom: 12px;
    padding: 8px 14px; border-radius: 6px; display: inline-block;
  }
  .commercial { background: #238636; color: #fff; }
  .inspiration { background: #1f6feb; color: #fff; }
  .observe { background: #9e6a03; color: #fff; }
  .reject { background: #da3633; color: #fff; }
  .card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 20px; margin-bottom: 16px;
  }
  .card:hover { border-color: #484f58; }
  .card-header {
    display: flex; justify-content: space-between;
    align-items: flex-start; margin-bottom: 12px;
  }
  .card-brand { font-size: 18px; font-weight: 700; color: #e6edf3; }
  .card-type { font-size: 12px; color: #8b949e; margin-top: 2px; }
  .card-scores { display: flex; gap: 12px; align-items: center; flex-shrink: 0; }
  .score-badge { padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 14px; }
  .score-design { background: #1f6feb22; color: #58a6ff; border: 1px solid #1f6feb44; }
  .score-total { background: #23863622; color: #3fb950; border: 1px solid #23863644; }
  .track-badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .track-commercial { background: #238636; color: #fff; }
  .track-inspiration { background: #1f6feb; color: #fff; }
  .track-observe { background: #9e6a03; color: #fff; }
  .track-reject { background: #da3633; color: #fff; }
  .design-breakdown { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 12px 0; }
  .dim-item { background: #0d1117; border-radius: 6px; padding: 8px 10px; font-size: 12px; }
  .dim-name { color: #8b949e; margin-bottom: 4px; }
  .dim-bar { height: 4px; background: #21262d; border-radius: 2px; overflow: hidden; margin-bottom: 4px; }
  .dim-fill { height: 100%; border-radius: 2px; }
  .fill-high { background: #3fb950; }
  .fill-mid { background: #d29922; }
  .fill-low { background: #f85149; }
  .dim-score { font-weight: 700; color: #e6edf3; }
  .meta-row { display: flex; gap: 16px; margin: 8px 0; font-size: 12px; color: #8b949e; }
  .meta-item { display: flex; align-items: center; gap: 4px; }
  .meta-value { color: #e6edf3; font-weight: 600; }
  .tags { display: flex; gap: 6px; flex-wrap: wrap; margin: 8px 0; }
  .tag { padding: 2px 8px; background: #21262d; border: 1px solid #30363d; border-radius: 12px; font-size: 11px; color: #8b949e; }
  .explanation {
    background: #0d1117; border-left: 3px solid #30363d;
    padding: 8px 12px; margin-top: 10px; font-size: 13px; color: #8b949e; line-height: 1.5;
  }
  .explanation.positive { border-left-color: #3fb950; }
  .explanation.warning { border-left-color: #d29922; }
  .explanation.negative { border-left-color: #f85149; }
  a { color: #58a6ff; text-decoration: none; word-break: break-all; }
  a:hover { text-decoration: underline; }
  .card-reject .card-header { opacity: 0.7; }
  .card-reject .explanation { border-left-color: #f85149; }
  .footer { color: #8b949e; font-size: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #30363d; }
  @media (max-width: 700px) {
    .design-breakdown { grid-template-columns: repeat(2, 1fr); }
    .card-header { flex-direction: column; gap: 8px; }
  }
</style>
</head>
<body>
<div class="container">
  <h1>R1 上游入口筛选结果</h1>
  <p class="subtitle">{{summary}}</p>
  {{sections}}
  <p class="footer">
    评分模型 v2：高级设计感 60% + 地域成立度 20% + 年龄/人群 10% + 商业验证 10%<br>
    确认后告诉我批准哪些加入，我立即写入 brands.json。
  </p>
</div>
</body>
</html>`;

function escapeHtml(text) {
  return String(text || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function fillClass(score) { return score >= 7 ? "fill-high" : score >= 4 ? "fill-mid" : "fill-low"; }
function trackBadgeClass(tl) { return { commercial_track: "track-commercial", design_inspiration: "track-inspiration", observe: "track-observe", reject: "track-reject" }[tl] || "track-observe"; }
function trackLabel(tl) { return { commercial_track: "商业追踪线", design_inspiration: "设计启发线", observe: "观察线", reject: "剔除" }[tl] || tl; }
function explanationClass(tl) { return tl === "reject" ? "negative" : tl === "observe" ? "warning" : "positive"; }

function renderDesignBreakdown(subScores) {
  if (!subScores?.length) return "";
  return subScores.map((d) => `<div class="dim-item">
    <div class="dim-name">${escapeHtml(d.name)}</div>
    <div class="dim-bar"><div class="dim-fill ${fillClass(d.score)}" style="width:${Math.min(100, d.score * 10)}%"></div></div>
    <div class="dim-score">${d.score}/10</div>
  </div>`).join("");
}

function renderCard(item, isReject) {
  const s = item.r1Scoring || {}, d = item.r1Decision || {}, tl = d.trackLine || "observe";
  const url = (item.officialSources || [])[0] || "";
  const tags = (item.aestheticTags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("");
  return `<div class="card${isReject ? " card-reject" : ""}">
  <div class="card-header">
    <div>
      <div class="card-brand">${escapeHtml(item.brand)}</div>
      <div class="card-type">${escapeHtml(item.type || item.category)}</div>
      ${tags ? `<div class="tags">${tags}</div>` : ""}
    </div>
    <div class="card-scores">
      <span class="track-badge ${trackBadgeClass(tl)}">${trackLabel(tl)}</span>
      <span class="score-badge score-design">设计感 ${s.designScore || 0}/10</span>
      <span class="score-badge score-total">综合 ${s.weightedTotal || 0}</span>
    </div>
  </div>
  ${!isReject ? `<div class="design-breakdown">${renderDesignBreakdown(s.designSubScores)}</div>` : ""}
  <div class="meta-row">
    <div class="meta-item">地域 <span class="meta-value">${s.regionScore || 0}/10</span></div>
    <div class="meta-item">人群 <span class="meta-value">${s.audienceScore || 0}/10</span></div>
    <div class="meta-item">商业 <span class="meta-value">${s.commercialScore || 0}/10</span></div>
    ${url ? `<div class="meta-item"><a href="${escapeHtml(url)}" target="_blank">官网 ↗</a></div>` : ""}
  </div>
  <div class="explanation ${explanationClass(tl)}">${escapeHtml(d.explanation || "")}</div>
</div>`;
}

function renderSection(title, css, tl, items) {
  if (!items.length) return "";
  return `<div class="section"><div class="section-title ${css}">${title}（${items.length} 个）</div>${items.map((i) => renderCard(i, tl === "reject")).join("\n")}</div>`;
}

function generateReport() {
  const review = readJson(path.join(DATA_DIR, "r1-intake.review.json"), []);
  const rejected = readJson(path.join(DATA_DIR, "r1-intake.rejected.json"), []);
  const ct = review.filter((i) => i.r1Decision?.trackLine === "commercial_track");
  const di = review.filter((i) => i.r1Decision?.trackLine === "design_inspiration");
  const ob = review.filter((i) => i.r1Decision?.trackLine === "observe");
  const total = review.length + rejected.length;
  const summary = `${total} 个候选 → 商业追踪线 ${ct.length} → 设计启发线 ${di.length} → 观察线 ${ob.length} → 剔除 ${rejected.length}`;
  let sections = renderSection("商业追踪线", "commercial", "commercial_track", ct)
    + renderSection("设计启发线", "inspiration", "design_inspiration", di)
    + renderSection("观察线", "observe", "observe", ob)
    + renderSection("已剔除", "reject", "reject", rejected);
  const outputPath = path.join(DATA_DIR, "..", "brand-review.html");
  fs.writeFileSync(outputPath, HTML_TEMPLATE.replace("{{summary}}", summary).replace("{{sections}}", sections), "utf8");
  console.log(`R1 report generated: ${outputPath}`);
}

module.exports = { generateReport };
if (require.main === module) generateReport();
