/* ============================================
   BrandPulse VIS v3.0 — 核心应用逻辑
   模块化架构：数据层 / 渲染层 / 交互层
   ============================================ */

// ==================== 全局数据 ====================
let brandsData = {
  lastUpdated: new Date().toISOString().split('T')[0],
  sourcePriority: {
    description: "信息源金字塔：约束源头 > 设计师前沿 > 范式确立 > 跟随者",
    tier0_constraint: "材料实验室/工艺创新/供应链趋势/头部品牌实验",
    tier1_designer: "Nothing/Teenage Engineering/Dyson/B&O",
    tier2_paradigm: "华为/Apple/三星（范式确立者）",
    tier3_follower: "扩散跟随者（仅保留高VIS）",
    block_list: ["今日头条自媒体", "百家号", "搜狐号", "网易号", "企鹅号"]
  },
  brands: [],
  categories: {
    "car": "🚗 汽车",
    "phone": "📱 手机/平板",
    "wearable": "⌚ 可穿戴",
    "audio": "🎧 音频",
    "smart": "🏠 智能家居",
    "mobility": "🛴 出行工具",
    "accessory": "🔌 充电配件",
    "camera": "📷 影像设备",
    "robot": "🤖 扫地机器人",
    "lawn": "🌿 割草机器人",
    "pool": "🏊 泳池设备",
    "power": "🔋 便携储能",
    "projector": "📽️ 智能投影",
    "gaming": "🎮 电竞设备",
    "charger": "⚡ 充电配件"
  }
};

let productsData = [];
let originalProductsData = []; // 保持原始数据用于重置
let currentFilter = 'all';
let currentSection = 'featured';
let currentSort = 'time';
let notificationEnabled = false;

// ==================== 品牌颜色映射 ====================
const brandColors = {
  // 汽车 (3)
  '小米汽车': '#ff6900', '特斯拉': '#e82127', '享界': '#cf0a2c',
  // 手机/平板 (6)
  '华为': '#cf0a2c', 'OPPO': '#1ba784', '三星': '#1428a0',
  '联想moto': '#4ecdc4', 'Nothing': '#333', 'Ulefone': '#ff6b35',
  // 音频 (2)
  '索尼': '#000', '韶音': '#00b4d8', '韶音Shokz': '#00b4d8',
  // 智能家居
  '微软': '#00a4ef',
  // 扫地机器人 (4)
  '追觅': '#7c3aed', '追觅Dreame': '#7c3aed',
  '石头科技': '#6366f1', '科沃斯': '#2563eb', '云鲸': '#06b6d4',
  // 割草机器人 (3)
  '库犸科技': '#22c55e', 'Segway割草机': '#f59e0b', 'Worx割草机': '#f97316',
  // 泳池设备 (2)
  'Beatbot': '#06b6d4', 'Aiper': '#3b82f6',
  // 便携储能 (2)
  'Bluetti': '#0ea5e9', '正浩': '#22c55e', '正浩EcoFlow': '#22c55e',
  // 可穿戴 (3)
  'Oura': '#a855f7', 'WHOOP': '#ef4444', '佳明': '#f59e0b', '佳明Garmin': '#f59e0b',
  // 投影 (2)
  '极米': '#ec4899', '坚果': '#f97316',
  // 电竞
  '玩家国度': '#ef4444', 'ROG': '#ef4444',
  // 出行 (2)
  '九号': '#f59e0b', '小牛': '#22c55e',
  // 充电配件 (10)
  '安克': '#0a84ff', '安克Anker': '#0a84ff',
  '倍思': '#f97316', '绿联': '#22c55e', '贝尔金': '#64748b',
  '酷态科': '#8b5cf6', '罗马仕': '#ef4444', '闪极': '#f59e0b',
  '优越者': '#6366f1', '维奥技术': '#10b981', '艾欧提': '#94a3b8',
  // 影像设备 (3)
  '大疆': '#1a86ff', '大疆DJI': '#1a86ff',
  '影石': '#ff6b35', '影石Insta360': '#ff6b35',
  'GoPro': '#000'
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', async function() {
  showSkeleton();
  try {
    await loadBrands();
    await loadProducts();
    renderBrandInlineList();
    applyStateAndRender();
    checkNewProducts();
    checkArchiveVisibility();
  } catch (e) {
    console.error('[BrandPulse] 初始化失败:', e);
    showError('数据加载失败，请刷新页面重试');
  }
});

// ==================== 数据加载 ====================
async function loadBrands() {
  try {
    const response = await fetch('./brands.json');
    if (response.ok) {
      const data = await response.json();
      if (data.brands && Array.isArray(data.brands)) {
        brandsData.brands = data.brands.map(b => ({
          name: b.name, nameEn: b.nameEn || b.name,
          category: b.category, type: b.type || '',
          monitored: b.monitored !== false,
          officialSources: b.officialSources || []
        }));
        if (data.categories) Object.assign(brandsData.categories, data.categories);
        console.log(`[BrandPulse] 已从 brands.json 加载 ${brandsData.brands.length} 个品牌`);
        return;
      }
    }
  } catch (e) {
    console.warn('[BrandPulse] 无法加载 brands.json，使用内置数据:', e.message);
  }
  loadFallbackBrands();
}

function loadFallbackBrands() {
  // 44个品牌 — 与 brands.json 保持同步
  brandsData.brands = [
    {name:"小米汽车",category:"car",type:"智能电动车",monitored:true},
    {name:"特斯拉",category:"car",type:"智能电动车",monitored:true},
    {name:"享界",category:"car",type:"华为智选智能电动车",monitored:true},
    {name:"华为",category:"phone",type:"智能手机/笔记本/可穿戴",monitored:true},
    {name:"OPPO",category:"phone",type:"智能手机",monitored:true},
    {name:"三星",category:"phone",type:"智能手机",monitored:true},
    {name:"联想moto",category:"phone",type:"折叠屏手机",monitored:true},
    {name:"Nothing",category:"phone",type:"透明设计手机/耳机",monitored:true},
    {name:"Ulefone",category:"phone",type:"三防手机/热成像手机",monitored:true},
    {name:"索尼",category:"audio",type:"头戴降噪耳机",monitored:true},
    {name:"韶音",category:"audio",type:"骨传导耳机",monitored:true},
    {name:"微软",category:"smart",type:"二合一PC",monitored:true},
    {name:"追觅",category:"robot",type:"洗地机/扫地机器人",monitored:true},
    {name:"石头科技",category:"robot",type:"扫地机器人",monitored:true},
    {name:"科沃斯",category:"robot",type:"扫地机器人",monitored:true},
    {name:"云鲸",category:"robot",type:"扫地机器人",monitored:true},
    {name:"库犸科技",category:"lawn",type:"智能割草机器人",monitored:true},
    {name:"Segway割草机",category:"lawn",type:"无边界割草机器人",monitored:true},
    {name:"Worx割草机",category:"lawn",type:"智能割草机器人",monitored:true},
    {name:"Beatbot",category:"pool",type:"泳池清洁机器人",monitored:true},
    {name:"Aiper",category:"pool",type:"泳池清洁机器人",monitored:true},
    {name:"Bluetti",category:"power",type:"户外储能电站",monitored:true},
    {name:"正浩",category:"power",type:"户外电源/储能",monitored:true},
    {name:"Oura",category:"wearable",type:"智能戒指",monitored:true},
    {name:"WHOOP",category:"wearable",type:"无屏健康手环",monitored:true},
    {name:"佳明",category:"wearable",type:"运动手表/健康穿戴",monitored:true},
    {name:"极米",category:"projector",type:"智能投影仪",monitored:true},
    {name:"坚果",category:"projector",type:"智能投影仪",monitored:true},
    {name:"玩家国度",category:"gaming",type:"电竞笔记本/显示器/外设",monitored:true},
    {name:"九号",category:"mobility",type:"电动车/电摩",monitored:true},
    {name:"小牛",category:"mobility",type:"电动车",monitored:true},
    {name:"安克",category:"accessory",type:"无线充/充电器",monitored:true},
    {name:"倍思",category:"accessory",type:"三合一无线充/伸缩线充",monitored:true},
    {name:"绿联",category:"accessory",type:"扩展坞/屏显充电器",monitored:true},
    {name:"贝尔金",category:"accessory",type:"MagSafe无线充",monitored:true},
    {name:"酷态科",category:"accessory",type:"快充充电宝",monitored:true},
    {name:"罗马仕",category:"accessory",type:"大容量充电宝",monitored:true},
    {name:"闪极",category:"accessory",type:"复古设计充电器",monitored:true},
    {name:"优越者",category:"accessory",type:"扩展坞/数据线",monitored:true},
    {name:"维奥技术",category:"accessory",type:"便携显示器",monitored:true},
    {name:"艾欧提",category:"accessory",type:"车载无线充",monitored:true},
    {name:"大疆",category:"camera",type:"无人机/手持云台",monitored:true},
    {name:"影石",category:"camera",type:"全景相机/运动相机",monitored:true},
    {name:"GoPro",category:"camera",type:"运动相机",monitored:true}
  ];
}

async function loadProducts() {
  let loadError = null;
  try {
    const response = await fetch('./products/recent.json');
    if (response.ok) {
      const data = await response.json();
      if (Array.isArray(data) && data.length > 0) {
        productsData = data;
        console.log(`[BrandPulse] 已从 recent.json 加载 ${productsData.length} 个产品`);
        window.dataSource = 'recent.json';
        return;
      }
    } else {
      loadError = `HTTP ${response.status}`;
    }
  } catch (e) {
    loadError = e.message;
    console.warn('[BrandPulse] 无法加载 recent.json:', e.message);
  }
  window.dataSource = 'fallback';
  window.dataLoadError = loadError;
  console.warn('[BrandPulse] 使用备用内嵌数据' + (loadError ? `，原因: ${loadError}` : ''));
  productsData = [];
}

// ==================== 视图状态管理 ====================
function applyStateAndRender() {
  applySection();
  applyFilter();
  updateStats();
  updateDataSourceBadge();
  updateUpdateTime();
}

function applySection() {
  let filtered = [...productsData];
  if (currentSection === 'featured') {
    filtered = filtered.filter(p => (p.visTotal || p.score || 0) >= 80);
  } else if (currentSection === 'today') {
    const today = new Date().toISOString().split('T')[0];
    filtered = filtered.filter(p => p.time.startsWith(today));
  }
  originalProductsData = [...filtered];
}

function applyFilter() {
  let filtered = [...originalProductsData];
  if (currentFilter !== 'all') {
    filtered = filtered.filter(p => p.category === currentFilter);
  }
  if (currentSort === 'score') {
    filtered.sort((a, b) => (b.visTotal || b.score) - (a.visTotal || a.score));
  } else if (currentSort === 'brand') {
    filtered.sort((a, b) => a.brand.localeCompare(b.brand, 'zh'));
  }
  renderTimeline(filtered);
}

// ==================== UI 切换 ====================
function switchSection(section, el) {
  currentSection = section;
  document.querySelectorAll('.nav-item:not(.nav-collapsible .nav-item)').forEach(n => n.classList.remove('active'));
  if (el) el.classList.add('active');
  document.getElementById('pageTitle').textContent = 
    section === 'featured' ? '精选' : section === 'all' ? '全部动态' : '今日更新';
  applyStateAndRender();
}

function filterCategory(el, category) {
  currentFilter = category;
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  applyFilter();
}

function sortProducts(type, el) {
  currentSort = type;
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
  if (el) el.classList.add('active');
  applyFilter();
}

// ==================== 搜索 ====================
let searchTimeout;
function searchContent() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    const query = document.getElementById('searchInput').value.trim().toLowerCase();
    let filtered = [...originalProductsData];
    if (currentFilter !== 'all') {
      filtered = filtered.filter(p => p.category === currentFilter);
    }
    if (query) {
      filtered = filtered.filter(p =>
        p.title.toLowerCase().includes(query) ||
        (p.summary || '').toLowerCase().includes(query) ||
        p.brand.toLowerCase().includes(query) ||
        (p.tags || []).some(t => t.toLowerCase().includes(query))
      );
    }
    if (currentSort === 'score') {
      filtered.sort((a, b) => (b.visTotal || b.score) - (a.visTotal || a.score));
    } else if (currentSort === 'brand') {
      filtered.sort((a, b) => a.brand.localeCompare(b.brand, 'zh'));
    }
    renderTimeline(filtered);
    highlightSearchResults(query);
  }, 300);
}

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', searchContent);
  }
});

function highlightSearchResults(query) {
  if (!query) return;
  document.querySelectorAll('.card-title').forEach(el => {
    const text = el.textContent;
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    el.innerHTML = text.replace(regex, '<span class="highlight">$1</span>');
  });
}

// ==================== 渲染函数 ====================
function showSkeleton() {
  const timeline = document.getElementById('timeline');
  timeline.innerHTML = Array.from({length: 3}, () => `
    <div class="skeleton-card">
      <div class="skeleton-image"></div>
      <div class="skeleton-line medium"></div>
      <div class="skeleton-line short"></div>
      <div class="skeleton-line long"></div>
      <div class="skeleton-line short"></div>
    </div>
  `).join('');
}

function showEmptyState(show, message = '暂无符合条件的产品') {
  const existing = document.querySelector('.empty-state');
  if (show && !existing) {
    const el = document.createElement('div');
    el.className = 'empty-state';
    el.innerHTML = `
      <div class="empty-state-icon">📭</div>
      <div class="empty-state-title">${message}</div>
      <div class="empty-state-desc">试试切换分类或调整筛选条件</div>
    `;
    document.getElementById('timeline').appendChild(el);
  } else if (!show && existing) {
    existing.remove();
  }
}

function renderTimeline(products) {
  const timeline = document.getElementById('timeline');
  if (!products || products.length === 0) {
    timeline.innerHTML = '';
    showEmptyState(true, '暂无符合条件的产品');
    return;
  }
  showEmptyState(false);

  const groups = {};
  products.forEach(p => {
    const date = (p.time || '').split(' ')[0];
    if (!groups[date]) groups[date] = [];
    groups[date].push(p);
  });

  const sortedDates = Object.keys(groups).sort((a, b) => {
    const parse = str => { const parts = str.split('-'); return parts[2] === '00' ? new Date(`${parts[0]}-${parts[1]}-01`) : new Date(str); };
    return parse(b) - parse(a);
  });

  timeline.innerHTML = sortedDates.map(date => `
    <div class="date-group" data-date="${date}">
      <div class="date-label">${formatDate(date)}</div>
      ${groups[date].map(p => renderProductCard(p)).join('')}
    </div>
  `).join('');

  // 重新绑定展开/收起事件
  bindExpandToggles();
}

function renderProductCard(product) {
  const time = (product.time || '').split(' ')[1] || '';
  const reviewStatus = product.reviewStatus || 'needs_review';
  const statusMap = {
    'verified': { text: '已验证', class: 'badge-verified' },
    'needs_image': { text: '待补图', class: 'badge-needs-image' },
    'needs_source': { text: '待补源', class: 'badge-needs-source' },
    'needs_review': { text: '待复核', class: 'badge-needs-review' },
    'rejected': { text: '已拒绝', class: 'badge-rejected' }
  };
  const status = statusMap[reviewStatus] || statusMap['needs_review'];
  const confidence = product.confidence || 0;
  const confidenceColor = confidence >= 80 ? '#22c55e' : confidence >= 60 ? '#fbbf24' : '#ef4444';
  const evidenceCount = (product.evidence || []).length;
  const brandColor = brandColors[product.brand] || '#22d3ee';

  return `
    <div class="card" data-category="${product.category}" data-product-id="${product.id || ''}">
      <div class="card-time-marker">${time || '--:--'}</div>
      
      <div class="card-image">
        ${product.image ? 
          `<img src="${product.image}" alt="${product.title}" loading="lazy" 
            onerror="this.parentElement.innerHTML='<div class=\\'card-image-placeholder\\'>🖼️ 图片加载失败</div>'">` :
          `<div class="card-image-placeholder" style="background:rgba(251,191,36,0.06);border:2px dashed rgba(251,191,36,0.15);">
            <div style="font-size:32px;margin-bottom:6px;">🖼️</div>
            <div style="font-size:11px;color:#fbbf24;font-weight:500;">待补图</div>
          </div>`
        }
      </div>

      <div class="card-header">
        <div class="card-avatar" style="background:linear-gradient(135deg,${brandColor},${brandColor}dd);">${(product.brand || '?')[0]}</div>
        <div class="card-source">
          <div class="card-source-name">${product.brand || '未知'}</div>
          <div class="card-source-type">${getCategoryName(product.category)}${time ? ' · ' + time : ''}</div>
        </div>
        <div class="card-badges">
          ${(product.visTotal || product.score || 0) >= 80 ? '<span class="badge badge-featured">⭐ 精选</span>' : ''}
          <span class="badge ${status.class}">${status.text}</span>
        </div>
      </div>

      <h3 class="card-title">${product.title || '无标题'}</h3>

      ${product.constraintChange ? `
        <div class="constraint-change">
          <div class="constraint-change-label">视觉约束变化</div>
          <div class="constraint-change-text">${product.constraintChange}</div>
        </div>` : ''}

      <div class="card-metrics">
        <div>
          <div class="metric-score">${product.visTotal || product.score || 0}</div>
          <div class="metric-label">VIS总分</div>
        </div>
        <div class="metric-divider"></div>
        <div>
          <div class="metric-confidence" style="color:${confidenceColor}">${confidence}</div>
          <div class="metric-label">可信度</div>
        </div>
        <div class="metric-divider"></div>
        <div style="font-size:11px;color:var(--text-muted);">${evidenceCount}条证据</div>
      </div>

      <div class="weight-hint">权重: 识别度30% | 范式25% | CMF20% | 迁移15% | 扩散10%</div>

      ${(product.tags || []).length > 0 ? `
        <div class="card-tags">
          ${product.tags.map((t, i) => {
            const tagClasses = ['tag-cyan', 'tag-green', 'tag-blue', 'tag-purple', 'tag-pink', 'tag-orange'];
            return `<span class="tag ${tagClasses[i % tagClasses.length]}">${t}</span>`;
          }).join('')}
        </div>` : ''}

      <button class="expand-toggle" onclick="toggleDetails(this)" data-product-id="${product.id || ''}">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
        查看详情
      </button>

      <div class="card-details">
        ${product.summary ? `<div class="card-desc">${product.summary}</div>` : ''}

        ${(product.facts || []).length > 0 ? `
          <div class="detail-section">
            <div class="detail-section-title">事实要点</div>
            <ul class="facts-list">
              ${product.facts.map(f => `<li>${f}</li>`).join('')}
            </ul>
          </div>` : ''}

        ${product.analysis ? `
          <div class="detail-section">
            <div class="detail-section-title">分析</div>
            ${product.analysis.whyItMatters ? `<div class="analysis-text"><strong>重要性：</strong>${product.analysis.whyItMatters}</div>` : ''}
            ${product.analysis.transferability ? `<div class="analysis-text"><strong>可迁移性：</strong>${product.analysis.transferability}</div>` : ''}
            ${product.analysis.risk ? `<div class="analysis-text"><strong>风险：</strong>${product.analysis.risk}</div>` : ''}
          </div>` : ''}

        ${(product.evidence || []).length > 0 ? `
          <div class="detail-section">
            <div class="detail-section-title">证据链 (${evidenceCount}条)</div>
            ${product.evidence.map(e => `
              <div class="evidence-item">
                <div class="evidence-header">
                  <span style="color:${(e.tier||'').includes('tier0') ? '#22c55e' : (e.tier||'').includes('tier1') ? '#3b82f6' : '#8b95a5'};">●</span>
                  <a href="${e.url}" target="_blank" class="evidence-url">${e.name}</a>
                </div>
                <div class="evidence-supports">${(e.supports || []).join(' · ')}</div>
              </div>
            `).join('')}
          </div>` : ''}

        <div class="card-footer">
          <span class="card-meta">发布时间：${product.time || '未知'}</span>
          ${product.primarySource?.url ? `<a href="${product.primarySource.url}" target="_blank" class="card-link">查看主来源 →</a>` : ''}
        </div>
      </div>
    </div>
  `;
}

function bindExpandToggles() {
  document.querySelectorAll('.expand-toggle').forEach(btn => {
    btn.onclick = function() { toggleDetails(this); };
  });
}

function toggleDetails(btn) {
  const card = btn.closest('.card');
  const details = card.querySelector('.card-details');
  const isOpen = details.style.display === 'block';
  
  if (isOpen) {
    details.style.display = 'none';
    btn.classList.remove('active');
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg> 查看详情`;
  } else {
    details.style.display = 'block';
    btn.classList.add('active');
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg> 收起详情`;
  }
}

// ==================== 品牌管理 ====================
function toggleBrandManager() {
  const content = document.getElementById('brandManagerContent');
  const arrow = document.getElementById('brandArrow');
  const isVisible = content.style.display === 'block';
  content.style.display = isVisible ? 'none' : 'block';
  arrow.classList.toggle('open', !isVisible);
  if (!isVisible) renderBrandInlineList();
}

function renderBrandInlineList(filter = '') {
  const list = document.getElementById('brandInlineList');
  if (!list) return;
  const filtered = filter ?
    brandsData.brands.filter(b =>
      b.name.toLowerCase().includes(filter.toLowerCase()) ||
      (b.nameEn || '').toLowerCase().includes(filter.toLowerCase())
    ) : brandsData.brands;
  
  list.innerHTML = filtered.map(b => {
    const color = brandColors[b.name] || '#6b7280';
    return `<div class="brand-inline-item">
      <span class="brand-dot" style="background:${color}"></span>
      <span>${b.name}</span>
      <span class="brand-remove" onclick="removeBrandInline('${b.name}')">×</span>
    </div>`;
  }).join('');
  
  const navCount = document.getElementById('brandCountNav');
  if (navCount) navCount.textContent = brandsData.brands.length;
}

function removeBrandInline(name) {
  brandsData.brands = brandsData.brands.filter(b => b.name !== name);
  renderBrandInlineList();
  renderBrandList();
  applyStateAndRender();
}

function filterBrandList() {
  const input = document.getElementById('brandSearchInline');
  renderBrandInlineList(input ? input.value : '');
}

function openAddBrandModal() {
  document.getElementById('addBrandModal').classList.add('show');
}

function closeAddBrandModal() {
  document.getElementById('addBrandModal').classList.remove('show');
}

function addBrand() {
  const name = document.getElementById('newBrandName').value.trim();
  const category = document.getElementById('newBrandCategory').value;
  const type = document.getElementById('newBrandType').value.trim();
  if (!name) { alert('请输入品牌名称'); return; }
  if (brandsData.brands.some(b => b.name === name)) { alert('该品牌已存在'); return; }
  
  brandsData.brands.push({ name, nameEn: name, category, type, monitored: true });
  renderBrandInlineList();
  renderBrandList();
  closeAddBrandModal();
  document.getElementById('newBrandName').value = '';
  document.getElementById('newBrandType').value = '';
}

function saveBrands() {
  const dataStr = JSON.stringify(brandsData, null, 2);
  const blob = new Blob([dataStr], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'brands.json';
  document.body.appendChild(a); a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ==================== 统计 ====================
function updateStats() {
  const all = productsData;
  const featured = all.filter(p => (p.visTotal || p.score || 0) >= 80);
  
  const statTotal = document.getElementById('statTotal');
  const statFeatured = document.getElementById('statFeatured');
  const statBrands = document.getElementById('statBrands');
  const statMonitored = document.getElementById('statMonitored');
  const featuredCount = document.getElementById('featuredCount');
  const allCount = document.getElementById('allCount');

  if (statTotal) statTotal.textContent = all.length;
  if (statFeatured) statFeatured.textContent = featured.length;
  if (statBrands) statBrands.textContent = brandsData.brands.length + '+';
  if (statMonitored) statMonitored.textContent = brandsData.brands.filter(b => b.monitored).length;
  if (featuredCount) featuredCount.textContent = featured.length;
  if (allCount) allCount.textContent = all.length;
}

function updateDataSourceBadge() {
  const badge = document.getElementById('dataSourceBadge');
  if (!badge) return;
  if (window.dataSource === 'fallback') {
    badge.textContent = '备用数据' + (window.dataLoadError ? `（${window.dataLoadError}）` : '');
    badge.style.background = '#ef4444'; badge.style.color = '#fff'; badge.style.display = 'inline';
  } else if (window.dataSource === 'recent.json') {
    badge.textContent = '实时数据';
    badge.style.background = '#22c55e'; badge.style.color = '#000'; badge.style.display = 'inline';
  }
}

function updateUpdateTime() {
  const updateTime = window.lastUpdated || '未知';
  const lastTime = document.getElementById('lastUpdatedTime');
  const sidebarTime = document.getElementById('sidebarUpdateTime');
  if (lastTime) lastTime.textContent = updateTime;
  if (sidebarTime) sidebarTime.textContent = '更新: ' + updateTime;
}

// ==================== 工具函数 ====================
function formatDate(dateStr) {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  const date = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2] || 1));
  const now = new Date();
  const diff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
  
  if (diff === 0) return '今天';
  if (diff === 1) return '昨天';
  if (diff < 7) return `${diff}天前`;
  return `${parts[1]}月${parts[2]}日 周${weekdays[date.getDay()]}`;
}

function getCategoryName(cat) {
  return brandsData.categories[cat] || cat || '未分类';
}

// ==================== 通知 ====================
function toggleNotification() {
  notificationEnabled = !notificationEnabled;
  const btn = document.getElementById('notifyBtn');
  btn.textContent = notificationEnabled ? '🔔 新品提醒已开启' : '🔔 开启新品提醒';
  btn.classList.toggle('enabled', notificationEnabled);
  if (notificationEnabled) {
    showToast('新品提醒已开启', '每天 21:00 将自动追踪新品');
  }
}

function checkNewProducts() {
  if (!notificationEnabled) return;
  const today = new Date().toISOString().split('T')[0];
  const newProducts = productsData.filter(p => p.time && p.time.startsWith(today));
  if (newProducts.length > 0) {
    const top = newProducts[0];
    showToast(`发现 ${newProducts.length} 个新品！`, `${top.brand} ${top.title} 评分 ${top.score || top.visTotal}`);
  }
}

function showToast(title, text) {
  const toast = document.getElementById('notificationToast');
  toast.querySelector('.notification-title').textContent = title;
  toast.querySelector('.notification-text').textContent = text;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 5000);
}

// ==================== 错误处理 ====================
function showError(message) {
  const existing = document.querySelector('.error-toast');
  if (existing) existing.remove();
  
  const toast = document.createElement('div');
  toast.className = 'error-toast';
  toast.innerHTML = `
    <span>⚠️ ${message}</span>
    <button class="retry-btn" onclick="location.reload()">重试</button>
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 8000);
}

// ==================== 归档加载 ====================
function checkArchiveVisibility() {
  const section = document.getElementById('archiveSection');
  if (section && productsData.length > 0) {
    section.style.display = 'block';
  }
}

function loadArchive() {
  const btn = document.getElementById('loadArchiveBtn');
  const status = document.getElementById('archiveStatus');
  if (btn) btn.disabled = true;
  if (status) status.textContent = '正在加载历史归档...';
  
  const months = [];
  const now = new Date();
  for (let i = 1; i <= 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    months.push(key);
  }
  
  let loaded = 0;
  Promise.all(months.map(key =>
    fetch(`./products/archive/archive_${key}.json`)
      .then(r => r.ok ? r.json() : [])
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          productsData = productsData.concat(data);
          loaded += data.length;
        }
      })
      .catch(() => {})
  )).then(() => {
    if (status) status.textContent = loaded > 0 ? `已加载 ${loaded} 条历史数据` : '暂无历史归档数据';
    if (btn) btn.disabled = false;
    applyStateAndRender();
  });
}
