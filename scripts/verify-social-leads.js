// ============================================
// verify-social-leads.js — 小众上新链接可达性检测
// ============================================
// 用途：对 products/social-leads.json 中每条 lead 的 sourceUrl 跑一次
//       HTTP 探测，识别"无来源"或"链接失效/占位假链接"的条目。
// 规则：
//   - sourceUrl 为空  → linkVerified=false  （无来源链接）
//   - HTTP 4xx/5xx    → linkVerified=false  （链接已失效）
//   - HTTP 2xx + 命中平台占位模式 → linkVerified=false
//   - HTTP 2xx + 真实页面         → linkVerified=true
//
// 占位模式（明显的假数据/示例 ID）：
//   - xiaohongshu.com/explore/{纯数字≤12位}
//   - weibo.com/u/{数字}/{纯字母≤8位}
//   - detail.tmall.com/item.htm?id={纯数字≤12位}
//
// 用法：
//   node scripts/verify-social-leads.js
//   node scripts/verify-social-leads.js --strict   (未通过的条目从数据中删除)
//
// 默认行为：只更新 linkVerified 字段，保留原条目，由前端决定是否渲染。
// --strict 行为：移除无来源/不可达条目并写回。
// ============================================

const fs = require('fs');
const path = require('path');

const LEADS_PATH = path.resolve(__dirname, '..', 'products', 'social-leads.json');
const TIMEOUT_MS = 8000;

const PLACEHOLDER_PATTERNS = [
  { name: 'xhs-explore-numeric', re: /xiaohongshu\.com\/explore\/(\d+)/, validate: m => m[1].length <= 12 },
  { name: 'weibo-placeholder',    re: /weibo\.com\/(\d+)\/([A-Za-z0-9]+)/, validate: m => m[2].length <= 8 && /^[a-z]+$/.test(m[2]) },
  { name: 'tmall-numeric',        re: /tmall\.com[^?#]*[?&]id=(\d+)/, validate: m => m[1].length <= 12 }
];

function checkUrl(url) {
  return new Promise(resolve => {
    if (!url || !url.trim()) return resolve({ ok: false, reason: 'empty' });
    let parsed;
    try { parsed = new URL(url); } catch (e) { return resolve({ ok: false, reason: 'invalid-url' }); }
    if (!/^https?:$/.test(parsed.protocol)) return resolve({ ok: false, reason: 'non-http' });

    let settled = false;
    const done = (r) => { if (!settled) { settled = true; resolve(r); } };

    const headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' };
    let req;
    try {
      req = require(parsed.protocol === 'https:' ? 'https' : 'http').get(url, { timeout: TIMEOUT_MS, headers }, (res) => {
        const code = res.statusCode || 0;
        if (code >= 400) {
          res.resume();
          return done({ ok: false, reason: `http-${code}` });
        }
        // 命中占位模式直接判 false
        for (const p of PLACEHOLDER_PATTERNS) {
          const m = url.match(p.re);
          if (m && p.validate(m)) return done({ ok: false, reason: `placeholder:${p.name}` });
        }
        // 小红书 explore 命中 2xx 但 body 短 / 含 404 提示 → 不可信
        if (/xiaohongshu\.com/.test(url)) {
          let buf = '';
          res.setEncoding('utf-8');
          res.on('data', c => { if (buf.length < 4000) buf += c; });
          res.on('end', () => {
            if (buf.length < 1500 || /页面不存在|笔记已被删除|not found/i.test(buf)) {
              return done({ ok: false, reason: 'xhs-body-invalid' });
            }
            return done({ ok: true, reason: 'verified' });
          });
        } else {
          res.resume();
          return done({ ok: true, reason: 'verified' });
        }
      });
    } catch (e) {
      return done({ ok: false, reason: 'request-failed' });
    }
    req.on('timeout', () => { try { req.destroy(); } catch (e) {} done({ ok: false, reason: 'timeout' }); });
    req.on('error', e => done({ ok: false, reason: 'request-error:' + (e.code || e.message || 'unknown') }));
  });
}

async function main() {
  const strict = process.argv.includes('--strict');
  const raw = fs.readFileSync(LEADS_PATH, 'utf-8');
  const leads = JSON.parse(raw);

  console.log(`[verify] 扫描 ${leads.length} 条小众上新线索...`);
  let pass = 0, fail = 0;
  const updated = [];
  for (const lead of leads) {
    const r = await checkUrl(lead.sourceUrl);
    if (r.ok) {
      lead.linkVerified = true;
      pass++;
    } else {
      lead.linkVerified = false;
      lead._verifyReason = r.reason;
      fail++;
    }
    console.log(`  [${r.ok ? '✓' : '✗'}] ${lead.id}  ${r.reason}  ${(lead.sourceUrl || '').slice(0, 60)}`);
    updated.push(lead);
  }
  console.log(`[verify] 通过 ${pass} / 失败 ${fail}`);

  if (strict) {
    const keep = updated.filter(l => l.linkVerified);
    console.log(`[verify] --strict: 保留 ${keep.length} / 删除 ${updated.length - keep.length}`);
    fs.writeFileSync(LEADS_PATH, JSON.stringify(keep, null, 2) + '\n', 'utf-8');
  } else {
    fs.writeFileSync(LEADS_PATH, JSON.stringify(updated, null, 2) + '\n', 'utf-8');
  }
  console.log(`[verify] 已写回 ${LEADS_PATH}`);
}

main().catch(e => { console.error('[verify] 异常:', e); process.exit(1); });
