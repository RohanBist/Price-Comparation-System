/* ═══════════════════════════════════════════
   PriceNepal — Frontend JS (API-connected)
   ═══════════════════════════════════════════ */

const API_BASE = window.location.origin; // same Flask server

// ── STATE ─────────────────────────────────
let currentPage     = 'home';
let allResults      = [];   // raw API results for current search
let wishlist        = JSON.parse(localStorage.getItem('pn_wishlist') || '[]');
let currentProduct  = null;

// ── PAGE ROUTING ──────────────────────────
function showPage(page) {
  ['home','search','product','wishlist'].forEach(p => {
    const el = document.getElementById('page-' + p);
    if (el) el.style.display = (p === page) ? '' : 'none';
  });

  // Update nav active state
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const navEl = document.getElementById('nav-' + page);
  if (navEl) navEl.classList.add('active');

  currentPage = page;
  window.scrollTo(0, 0);

  if (page === 'wishlist') renderWishlist();
}

// ── SEARCH ────────────────────────────────
function doSearch(inputId) {
  const val = document.getElementById(inputId)?.value.trim();
  if (!val) return;
  doSearchDirect(val);
}

async function doSearchDirect(query) {
  showPage('search');

  // Sync search input
  const si = document.getElementById('search-input');
  if (si) si.value = query;

  // Reset UI
  setResultsState('loading');
  allResults = [];

  // Render simple recommendations (accessories / related queries)
  renderRecommendations(query);

  try {
    const res  = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || 'Server error');

    allResults = data.results || [];

    if (allResults.length === 0) {
      setResultsState('none');
    } else {
      setResultsState('results');
      applyFilters();

      // Show cache notice
      if (data.cached) showToast('⚡ Results loaded from cache', '');
      else showToast(`✅ Found ${allResults.length} products from ${data.errors.length > 0 ? 'some' : 'all'} stores`, 'success');

      // Show any scraper errors as warnings
      if (data.errors && data.errors.length > 0) {
        console.warn('Scraper warnings:', data.errors);
      }
    }

    // Save search history for personalized recommendations (keep last 10 unique)
    try {
      const sh = JSON.parse(localStorage.getItem('pn_search_history') || '[]');
      // push to front if new, keep unique
      const ql = query.trim();
      if (ql) {
        const idx = sh.indexOf(ql);
        if (idx !== -1) sh.splice(idx, 1);
        sh.unshift(ql);
        if (sh.length > 10) sh.length = 10;
        localStorage.setItem('pn_search_history', JSON.stringify(sh));
      }
    } catch (e) {
      // ignore
    }

  } catch (err) {
    setResultsState('error', err.message);
  }
}

// Render recommendation pills (smart category-aware accessory suggestions)
function renderRecommendations(query) {
  const el = document.getElementById('recommendations');
  if (!el) return;
  const ql = query.toLowerCase().trim();

  // Category detection with accessories map
  const categoryMap = [
    {
      keywords: ['phone', 'iphone', 'samsung', 'redmi', 'xiaomi', 'oppo', 'vivo', 'realme', 'oneplus', 'mobile', 'smartphone'],
      accessories: ['charger', 'case', 'screen protector', 'earphones', 'power bank', 'cable', 'tempered glass']
    },
    {
      keywords: ['laptop', 'notebook', 'macbook', 'chromebook'],
      accessories: ['laptop bag', 'mouse', 'charger', 'cooling pad', 'keyboard cover', 'external ssd', 'hdmi adapter']
    },
    {
      keywords: ['keyboard'],
      accessories: ['mouse', 'mousepad', 'usb hub', 'wrist rest', 'keyboard cleaner', 'monitor stand']
    },
    {
      keywords: ['mouse'],
      accessories: ['mousepad', 'keyboard', 'usb hub', 'mouse bungee', 'wrist rest']
    },
    {
      keywords: ['monitor', 'display', 'screen'],
      accessories: ['hdmi cable', 'monitor stand', 'display port cable', 'monitor light', 'vesa mount']
    },
    {
      keywords: ['camera', 'dslr', 'mirrorless'],
      accessories: ['camera bag', 'tripod', 'memory card', 'lens filter', 'extra battery', 'cleaning kit']
    },
    {
      keywords: ['headphone', 'earphone', 'earbuds', 'airpods', 'tws'],
      accessories: ['carrying case', 'ear tips', 'audio cable', 'headphone stand', 'amplifier']
    },
    {
      keywords: ['tablet', 'ipad'],
      accessories: ['tablet case', 'stylus', 'screen protector', 'keyboard case', 'stand', 'charger']
    },
    {
      keywords: ['tv', 'television', 'smart tv'],
      accessories: ['hdmi cable', 'wall mount', 'remote cover', 'soundbar', 'streaming stick']
    },
    {
      keywords: ['printer'],
      accessories: ['ink cartridge', 'toner', 'printer paper', 'usb cable', 'printer stand']
    },
    {
      keywords: ['router', 'wifi'],
      accessories: ['ethernet cable', 'range extender', 'network switch', 'cable organizer']
    },
    {
      keywords: ['case', 'cover', 'screen protector'],
      accessories: [] // Don't show accessories for accessories themselves
    }
  ];

  // Find best matching category (check if any keyword appears in query)
  let matched = null;
  for (const cat of categoryMap) {
    if (cat.keywords.some(kw => ql.includes(kw))) {
      matched = cat;
      break;
    }
  }

  // If no category matched OR accessories list is empty, show nothing
  if (!matched || matched.accessories.length === 0) {
    el.innerHTML = '';
    return;
  }

  // Collect ALL accessory terms across all categories to strip them from query
  const allAccessoryTerms = categoryMap.flatMap(c => c.accessories);

  // Strip any existing accessory terms from the base query
  let baseQuery = ql;
  for (const term of allAccessoryTerms) {
    const termRegex = new RegExp(`\\s*\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
    baseQuery = baseQuery.replace(termRegex, '');
  }
  baseQuery = baseQuery.trim();

  const pills = matched.accessories.map(term => {
    const q = `${baseQuery} ${term}`;
    const safeQ = q.replace(/'/g, "\\'");
    return `<button class="outline-btn" style="padding:6px 10px;font-size:0.85rem" onclick="doSearchDirect('${safeQ}')">${escHtml(q)}</button>`;
  }).join(' ');

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px;">
      <strong style="color:var(--muted);font-size:0.95rem">Related searches:</strong>
      ${pills}
    </div>`;
}

function setResultsState(state, msg = '') {
  document.getElementById('loading-state').style.display = state === 'loading'  ? '' : 'none';
  document.getElementById('error-state').style.display   = state === 'error'    ? '' : 'none';
  document.getElementById('no-results').style.display    = state === 'none'     ? '' : 'none';
  document.getElementById('results-grid').style.display  = state === 'results'  ? '' : 'none';
  document.getElementById('result-count').textContent    = '';
  document.getElementById('store-pills').innerHTML       = '';
  if (state === 'error') document.getElementById('error-msg').textContent = msg;
}

// ── FILTERS ───────────────────────────────
function applyFilters() {
  const storeFilters = ['Daraz','Hukut'].filter(s => document.getElementById('f-' + s.toLowerCase())?.checked);
  const minP  = parseFloat(document.getElementById('f-min')?.value) || 0;
  const maxP  = parseFloat(document.getElementById('f-max')?.value) || Infinity;
  const sort  = document.getElementById('f-sort')?.value || 'relevance';

  let filtered = allResults.filter(p => {
    const matchS = storeFilters.length === 0 || storeFilters.includes(p.store);
    const matchP = p.price >= minP && p.price <= maxP;
    return matchS && matchP;
  });

  if (sort === 'price-asc')  filtered.sort((a,b) => a.price - b.price);
  if (sort === 'price-desc') filtered.sort((a,b) => b.price - a.price);
  if (sort === 'name')       filtered.sort((a,b) => a.name.localeCompare(b.name));
  if (sort === 'popularity') filtered.sort((a,b) => (b.popularity || 0) - (a.popularity || 0));
  if (sort === 'rating')     filtered.sort((a,b) => {
    // prefer explicit rating, otherwise fall back to popularity
    const ra = (a.rating !== undefined && a.rating !== null) ? a.rating : (a.popularity || 0);
    const rb = (b.rating !== undefined && b.rating !== null) ? b.rating : (b.popularity || 0);
    return rb - ra;
  });
  if (sort === 'relevance') {
    filtered.sort((a, b) => {
      const rd = (b.relevance || 0) - (a.relevance || 0);
      if (rd !== 0) return rd;           // higher relevance first
      return a.price - b.price;          // tie-break by price
    });
  }

  // Result count
  document.getElementById('result-count').textContent =
    `${filtered.length} product${filtered.length !== 1 ? 's' : ''} found`;

  // Store pills
  const stores = [...new Set(filtered.map(p => p.store))];
  document.getElementById('store-pills').innerHTML = stores.map(s =>
    `<span class="store-pill ${s.toLowerCase()}">${s} (${filtered.filter(p=>p.store===s).length})</span>`
  ).join('');

  // Mark cheapest
  const minPrice = filtered.length ? Math.min(...filtered.map(p => p.price)) : 0;

  // Render grid
  const grid = document.getElementById('results-grid');
  if (filtered.length === 0) {
    grid.innerHTML = '';
    document.getElementById('no-results').style.display = '';
  } else {
    document.getElementById('no-results').style.display = 'none';
    grid.innerHTML = filtered.map(p => renderProductCard(p, p.price === minPrice)).join('');
  }
}

function clearFilters() {
  document.getElementById('f-daraz').checked = false;
  document.getElementById('f-hukut').checked = false;
  document.getElementById('f-min').value = '';
  document.getElementById('f-max').value = '';
  document.getElementById('f-sort').value = 'relevance';
  applyFilters();
}

// ── RENDER PRODUCT CARD ───────────────────
function renderProductCard(p, isCheapest = false) {
  const wished = wishlist.includes(p.link); // use link as unique ID
  const storeEmoji = p.store === 'Daraz' ? '🛒' : '🏪';

  return `
    <div class="product-card" onclick="viewProduct(${JSON.stringify(p).replace(/"/g, '&quot;')})">
     <div class="product-img">
       <img src="${p.image ? p.image : ''}" 
            alt="${escHtml(p.name)}" 
            style="width:100%;height:160px;object-fit:contain;padding:10px;">
       
        <button class="wish-btn ${wished ? 'wished' : ''}"
         onclick="event.stopPropagation();toggleWish(${JSON.stringify(p).replace(/"/g, '&quot;')}, this)"
         title="${wished ? 'Remove from wishlist' : 'Add to wishlist'}">
         <svg viewBox="0 0 24 24" fill="${wished ? 'currentColor':'none'}" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
         </svg>
       </button>
      </div>
      <div class="product-body">
        <div class="product-store">${p.store}</div>
        <div class="product-name">${escHtml(p.name)}</div>
        <div class="product-footer">
          <span class="product-price">Rs. ${p.price.toLocaleString('en-IN')}</span>
          ${p.rating ? ('<span style="margin-left:10px;color:var(--muted);font-size:0.85rem">★ ' + p.rating + '</span>') : ''}
          ${p.popularity ? '<span style="margin-left:8px;color:var(--muted);font-size:0.85rem">' + p.popularity + ' users</span>' : ''}
          ${isCheapest ? '<span class="product-badge cheapest">✅ Cheapest</span>' : ''}
        </div>
        <button class="view-btn" onclick="event.stopPropagation();window.open('${p.link}','_blank')">
          View on ${p.store === 'Daraz' ? 'Drz' : p.store} →
        </button>
      </div>
    </div>`;
}

// ── PRODUCT DETAIL ────────────────────────
function viewProduct(p) {
  currentProduct = p;
  showPage('product');

  document.getElementById('bc-name').textContent = p.name.substring(0, 50);

  const storeEmoji = p.store === 'Daraz' ? '🛒' : '🏪';
  const wished = wishlist.includes(p.link);

  // Find same product across stores (by meaningful token similarity)
  // Build meaningful tokens from product name (skip short/generic words)
  const stopWords = new Set(['with','and','the','for','new','pro','max','plus','gen','series','edition','pack','set','in','of','by','to']);
  const nameTokens = p.name.toLowerCase()
    .split(/\W+/)
    .filter(t => t.length >= 3 && !stopWords.has(t));

  // Score each candidate by how many tokens it shares
  const similar = allResults
    .filter(x => x.link !== p.link)
    .map(x => {
      const xName = x.name.toLowerCase();
      const matchCount = nameTokens.filter(t => xName.includes(t)).length;
      const score = nameTokens.length > 0 ? matchCount / nameTokens.length : 0;
      return { ...x, _simScore: score };
    })
    .filter(x => x._simScore >= 0.5)   // at least 50% token overlap
    .sort((a, b) => b._simScore - a._simScore)
    .slice(0, 5);

  // Build store comparison rows
  const compRows = [p, ...similar.filter(s => s.store !== p.store).slice(0,2)]
    .sort((a,b) => a.price - b.price)
    .map((s, i) => `
      <tr class="${i === 0 ? 'best-row' : ''}">
        <td>
          <strong>${escHtml(s.store)}</strong>
          ${i === 0 ? '<span class="badge-best">Best</span>' : ''}
        </td>
        <td><strong>Rs. ${s.price.toLocaleString('en-IN')}</strong></td>
        <td>
          <span style="color:${i===0?'var(--success)':i===1?'var(--muted)':'var(--muted)'}">
            ${i===0 ? '✅ Best Choice' : i===1 ? 'Good option' : 'Higher price'}
          </span>
        </td>
        <td>
          <a href="${s.link}" target="_blank" class="outline-btn" style="font-size:0.78rem;padding:5px 14px">
            View on ${s.store === 'Daraz' ? 'Drz' : s.store}
          </a>
        </td>
      </tr>`).join('');

  document.getElementById('product-detail-content').innerHTML = `
    <div class="detail-grid" style="margin-bottom:40px">
      <div class="detail-img-box">
        <img src="${p.image ? p.image : ''}" 
             alt="${escHtml(p.name)}"
             style="max-width:100%;max-height:300px;object-fit:contain;">
      </div>
      <div>
        <div class="detail-store">${p.store}</div>
        <h1 class="detail-name">${escHtml(p.name)}</h1>
        <div style="margin-top:14px;margin-bottom:14px">
          <strong>Price history</strong>
          <div id="price-history-container" style="margin-top:10px">
            <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
              <label style="color:var(--muted);font-size:0.9rem">View:</label>
              <select id="price-agg" style="padding:6px;border-radius:8px;border:1px solid var(--border)">
                <option value="raw">Raw (per scrape)</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
              <div style="margin-left:auto;color:var(--muted);font-size:0.9rem">Prediction horizon: <span id="pred-horizon">1 period</span></div>
            </div>
            <canvas id="price-chart" width="800" height="240"></canvas>
            <div style="display:flex;gap:12px;align-items:center;margin-top:8px">
              <div id="price-pred" style="color:var(--muted)"></div>
              <div id="price-change" style="font-weight:600"></div>
            </div>
          </div>
        </div>
        <div class="detail-price">Rs. ${p.price.toLocaleString('en-IN')}</div>
        <div class="detail-actions">
          <a href="${p.link}" target="_blank" class="primary-btn">View on ${p.store === 'Daraz' ? 'Drz' : p.store} →</a>
          <button class="outline-btn wish-toggle ${wished?'wished':''}"
            onclick="toggleWishDetail(this)"
            style="color:${wished?'var(--crimson)':'var(--ink-soft)'};border-color:${wished?'var(--crimson)':'var(--border)'}">
            <svg viewBox="0 0 24 24" fill="${wished?'currentColor':'none'}" stroke="currentColor" stroke-width="2" width="15" height="15">
              <path stroke-linecap="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
            </svg>
            ${wished ? 'Saved' : 'Save'}
          </button>
        </div>
        <ul class="detail-meta">
          <li><strong>Store:</strong> ${p.store}</li>
          <li><strong>Price:</strong> Rs. ${p.price.toLocaleString('en-IN')}</li>
          <li><strong>Direct link:</strong> <a href="${p.link}" target="_blank" style="color:var(--crimson);word-break:break-all">${p.link.substring(0,60)}…</a></li>
        </ul>
      </div>
    </div>

    <h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;margin-bottom:4px;">Price Comparison</h2>
    <p style="color:var(--muted);font-size:0.875rem;margin-bottom:16px;">Comparing across available stores for similar products</p>

    <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:18px;overflow:hidden;">
      <table class="compare-table">
        <thead>
          <tr>
            <th>Store</th>
            <th>Price</th>
            <th>Best to Choose</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>${compRows || '<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:20px">Only one listing found</td></tr>'}</tbody>
      </table>
    </div>
  `;

  // After DOM inserted, fetch price history and render chart + simple prediction
  (async () => {
    try {
      if (!p.product_id) return; // no DB id available
      const res = await fetch(`${API_BASE}/api/history?product_id=${p.product_id}`);
      const data = await res.json();
      if (!data || !data.history) return;
      const hist = data.history; // array of [iso, price]
      if (!hist.length) return;

      // Clean obvious outliers in the history before aggregation (median-based).
      // This filters values that are likely parsing/concatenation errors (e.g. 362995 vs 36299).
      function cleanHistoryRaw(hist) {
        const numeric = hist.map(h => Number(h[1])).filter(v => !isNaN(v) && isFinite(v));
        if (!numeric.length) return hist;
        // compute median
        const sorted = numeric.slice().sort((a,b)=>a-b);
        const mid = Math.floor(sorted.length/2);
        const median = (sorted.length % 2 === 1) ? sorted[mid] : (sorted[mid-1] + sorted[mid]) / 2;
        if (!isFinite(median) || median <= 0) return hist;
        // keep points within 10x and 0.1x median. If this filters out everything, return original hist.
        const filtered = hist.filter(h => {
          const v = Number(h[1]);
          if (!isFinite(v)) return false;
          return v >= median * 0.1 && v <= median * 10;
        });
        return filtered.length >= Math.max(2, Math.floor(hist.length/2)) ? filtered : hist;
      }

      const cleanedHist = cleanHistoryRaw(hist);

      // helper: aggregate history
      function aggregateHistory(hist, mode) {
        // hist: [[iso, price], ...]
  const items = cleanedHist.map(h => ({d: new Date(h[0]), v: h[1]})).sort((a,b)=>a.d-b.d);
        if (mode === 'raw') {
          return { labels: items.map(i=>i.d.toLocaleString()), values: items.map(i=>i.v) };
        }

        // Build a period series for weekly/monthly with continuous periods (last 12 periods)
        const now = new Date();
        const periods = [];
        if (mode === 'weekly') {
          // compute last 12 week start dates (Sunday-start)
          const cur = new Date(now);
          // align to week start
          cur.setHours(0,0,0,0);
          cur.setDate(cur.getDate() - cur.getDay());
          for (let i = 11; i >= 0; i--) {
            const wk = new Date(cur);
            wk.setDate(cur.getDate() - (i * 7));
            periods.push(wk.toISOString().slice(0,10));
          }
        } else if (mode === 'monthly') {
          // last 12 months (year-month keys)
          const y = now.getFullYear();
          const m = now.getMonth();
          for (let i = 11; i >= 0; i--) {
            const d = new Date(y, m - i, 1);
            periods.push(d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0'));
          }
        }

        // group items into period map (use last observed price in period)
        const groups = {};
        items.forEach(it => {
          const d = it.d;
          let key;
          if (mode === 'weekly') {
            const wkStart = new Date(d);
            wkStart.setHours(0,0,0,0);
            wkStart.setDate(d.getDate() - d.getDay());
            key = wkStart.toISOString().slice(0,10);
          } else if (mode === 'monthly') {
            key = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0');
          }
          // keep the last observed (by time) value for the period
          if (!groups[key] || groups[key].ts < it.d.getTime()) {
            groups[key] = { val: it.v, ts: it.d.getTime() };
          }
        });

        // Build values aligned to `periods`; fill missing by carrying last known price forward
        const labels = [];
        const values = [];
        let lastKnown = null;
        periods.forEach(k => {
          labels.push(mode === 'weekly' ? new Date(k).toLocaleDateString() : (new Date(k + '-01')).toLocaleString(undefined, {month:'short', year:'numeric'}));
          if (groups[k]) {
            lastKnown = groups[k].val;
            values.push(groups[k].val);
          } else {
            // carry forward last known price if any, otherwise push null for now
            values.push(lastKnown !== null ? lastKnown : null);
          }
        });

        // If there are leading nulls (no historical price yet), fill them with the first known value
        const firstKnownIdx = values.findIndex(v => v !== null && v !== undefined && !isNaN(v));
        if (firstKnownIdx > 0) {
          const fillVal = values[firstKnownIdx];
          for (let i = 0; i < firstKnownIdx; i++) values[i] = fillVal;
        }

        // If all values are null (no data), convert to zeros so Chart.js draws an axis
        const hasAnyNumeric = values.some(v => v !== null && v !== undefined && !isNaN(v));
        if (!hasAnyNumeric) {
          for (let i = 0; i < values.length; i++) values[i] = 0;
        }

        return { labels, values };
      }

      // function to draw chart for a given aggregation mode
      function drawAgg(mode) {
        const ag = aggregateHistory(hist, mode);
        const ctx = document.getElementById('price-chart');
        if (!ctx) return;
        if (window._priceChart) window._priceChart.destroy();
        window._priceChart = new Chart(ctx.getContext('2d'), {
          type: 'line',
          data: { labels: ag.labels, datasets: [{ label: 'Price (Rs.)', data: ag.values, borderColor: '#c0392b', backgroundColor: 'rgba(192,57,43,0.06)', tension:0.25, pointRadius:3, spanGaps:true }] },
          options: { scales: { y: { beginAtZero: false } } }
        });

  // prediction: next 1 period (use only numeric values)
  const numericVals = ag.values.filter(v => v !== null && v !== undefined && !isNaN(v));
  const pred = numericVals.length >= 2 ? simplePolyPredict(numericVals) : null;
        const ph = document.getElementById('pred-horizon');
        if (ph) ph.textContent = mode === 'raw' ? 'next scrape' : (mode === 'weekly' ? 'next week' : 'next month');
        if (pred !== null) {
          document.getElementById('price-pred').textContent = `Simple prediction (${ph.textContent}): Rs. ${pred.toLocaleString('en-IN')}`;
        } else {
          document.getElementById('price-pred').textContent = 'Not enough data to predict';
        }

        // Do not show percentage change as requested; keep the element empty
        const changeEl = document.getElementById('price-change');
        if (changeEl) changeEl.textContent = '';
      }

      // initial draw with raw data
      drawAgg('raw');

      // Save current displayed price as an observation (best-effort)
      try {
        await fetch(`${API_BASE}/api/save_price`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: p.name, price: p.price, store: p.store, link: p.link, image: p.image })
        });
      } catch (e) {
        console.warn('Failed to save displayed price:', e);
      }

      // hook selector
      const sel = document.getElementById('price-agg');
      if (sel) {
        sel.addEventListener('change', (ev) => drawAgg(ev.target.value));
      }

      // Also load recommendations for this product and based on search history
      (async () => {
        try {
          // Fetch recommendations for current product (pass price hint)
          const rres = await fetch(`${API_BASE}/api/recommendations?q=${encodeURIComponent(p.name)}&price=${encodeURIComponent(p.price)}&limit=30`);
          const rdata = await rres.json();

          // Also fetch recommendations for recent search history (client-side stored)
          const history = JSON.parse(localStorage.getItem('pn_search_history') || '[]');
          const historyTerms = history.slice(0,4).filter(h => h && h.toLowerCase() !== p.name.toLowerCase());
          const histPromises = historyTerms.map(t => fetch(`${API_BASE}/api/recommendations?q=${encodeURIComponent(t)}&limit=12`).then(r=>r.json()).catch(()=>({recommendations:[]})));
          const histResults = await Promise.all(histPromises);

          // Combine recommendation lists: start with product recs, then history recs
          let combined = [];
          if (rdata && rdata.recommendations) combined = combined.concat(rdata.recommendations);
          histResults.forEach(hr => { if (hr && hr.recommendations) combined = combined.concat(hr.recommendations); });

          // Normalize and deduplicate by product_url or product_id
          const seen = new Set();
          const cards = [];
          for (const r of combined) {
            const pid = r.product_id || null;
            const url = r.product_url || r.link || null;
            const key = url || pid || JSON.stringify(r);
            if (key && seen.has(key)) continue;
            seen.add(key);

            const name = r.product_name || r.name || '';
            const price = (r.latest_price !== undefined && r.latest_price !== null) ? r.latest_price : (r.price !== undefined ? r.price : null);
            const link = r.product_url || r.link || '#';
            const image = r.image || '';
            const store = r.store || '';
            const popularity = r.popularity || 0;
            const obj = { name, price, link, image, store, product_id: pid, popularity };
            cards.push(obj);
            if (cards.length >= 24) break;
          }

          if (cards.length) {
            const html = cards.map(obj => `
              <div class="product-card" style="cursor:pointer" onclick='viewProduct(${JSON.stringify(obj).replace(/"/g,'&quot;')})'>
                <div class="product-img"><img src="${obj.image||''}" style="width:100%;height:100px;object-fit:contain;padding:8px"></div>
                <div class="product-body">
                  <div class="product-store">${escHtml(obj.store)}</div>
                  <div class="product-name">${escHtml(obj.name)}</div>
                  <div class="product-footer">
                    <span class="product-price">${obj.price !== null ? ('Rs. ' + obj.price.toLocaleString('en-IN')) : ''}</span>
                    ${obj.popularity ? ('<span class="product-popularity" style="margin-left:8px;color:var(--muted);font-size:0.85rem">' + obj.popularity + ' users</span>') : ''}
                  </div>
                </div>
              </div>
            `).join('');
            const container = document.createElement('div');
            container.innerHTML = `
              <h3 style="margin-top:26px;margin-bottom:8px">You may also like</h3>
              <div class="products-grid" style="gap:12px">${html}</div>
            `;
            document.getElementById('product-detail-content').appendChild(container);
          }
        } catch (e) {
          console.warn('Recommendations failed', e);
        }
      })();

    } catch (err) {
      console.warn('History load failed', err);
    }
  })();
}

// Predict next value using simple polynomial regression (degree 2 when possible)
function simplePolyPredict(values) {
  if (!values || values.length < 2) return null;
  const n = values.length;
  // x values 0..n-1
  const xs = Array.from({length: n}, (_, i) => i);
  const ys = values.map(v => Number(v));

  // If only two points, fallback to linear prediction
  if (n === 2) {
    const x0 = xs[0], x1 = xs[1];
    const y0 = ys[0], y1 = ys[1];
    const slope = (y1 - y0) / (x1 - x0);
    const pred = y1 + slope; // next x = x1 + 1
    return Math.round(pred);
  }

  // Fit quadratic model y = a*x^2 + b*x + c using normal equations
  // Build sums
  let Sx = 0, Sx2 = 0, Sx3 = 0, Sx4 = 0, Sy = 0, Sxy = 0, Sx2y = 0;
  for (let i = 0; i < n; i++) {
    const x = xs[i];
    const y = ys[i];
    const x2 = x * x;
    const x3 = x2 * x;
    const x4 = x2 * x2;
    Sx += x; Sx2 += x2; Sx3 += x3; Sx4 += x4;
    Sy += y; Sxy += x * y; Sx2y += x2 * y;
  }

  // Normal equations matrix A and vector B for [a, b, c]
  // [Sx4 Sx3 Sx2][a]   [Sx2y]
  // [Sx3 Sx2 Sx ][b] = [Sxy ]
  // [Sx2 Sx  n  ][c]   [Sy  ]
  const A = [
    [Sx4, Sx3, Sx2],
    [Sx3, Sx2, Sx],
    [Sx2, Sx,  n]
  ];
  const B = [Sx2y, Sxy, Sy];

  // Solve 3x3 linear system using Cramer's rule (simple and acceptable for small sizes)
  function det3(m) {
    return m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1]) - m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0]) + m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]);
  }

  const D = det3(A);
  if (!isFinite(D) || Math.abs(D) < 1e-12) {
    // Ill-conditioned matrix; fallback to linear prediction using last two points
    const last = ys[n-1], prev = ys[n-2];
    const slope = last - prev;
    return Math.round(last + slope);
  }

  // build matrices A_a, A_b, A_c with B replacing respective column
  const A_a = [ [B[0], A[0][1], A[0][2]], [B[1], A[1][1], A[1][2]], [B[2], A[2][1], A[2][2]] ];
  const A_b = [ [A[0][0], B[0], A[0][2]], [A[1][0], B[1], A[1][2]], [A[2][0], B[2], A[2][2]] ];
  const A_c = [ [A[0][0], A[0][1], B[0]], [A[1][0], A[1][1], B[1]], [A[2][0], A[2][1], B[2]] ];

  const Da = det3(A_a), Db = det3(A_b), Dc = det3(A_c);
  const a = Da / D, b = Db / D, c = Dc / D;

  const nextX = n;
  const pred = a * nextX * nextX + b * nextX + c;
  if (!isFinite(pred)) {
    const last = ys[n-1], prev = ys[n-2];
    return Math.round(last + (last - prev));
  }
  return Math.round(pred);
}

function toggleWishDetail(btn) {
  if (!currentProduct) return;
  toggleWish(currentProduct, btn);
  const wished = wishlist.includes(currentProduct.link);
  btn.innerHTML = btn.innerHTML.replace(/Saved|Save/, wished ? 'Saved' : 'Save');
  btn.style.color = wished ? 'var(--crimson)' : 'var(--ink-soft)';
  btn.style.borderColor = wished ? 'var(--crimson)' : 'var(--border)';
}

// ── WISHLIST ──────────────────────────────
function toggleWish(p, btn) {
  const key = p.link;
  const inList = wishlist.includes(key);

  if (inList) {
    wishlist = wishlist.filter(x => x !== key);
    // Remove from stored products
    const stored = JSON.parse(localStorage.getItem('pn_wish_products') || '[]');
    localStorage.setItem('pn_wish_products', JSON.stringify(stored.filter(x => x.link !== key)));
    showToast('🗑 Removed from wishlist', '');
  } else {
    wishlist.push(key);
    // Store full product data
    const stored = JSON.parse(localStorage.getItem('pn_wish_products') || '[]');
    stored.push(p);
    localStorage.setItem('pn_wish_products', JSON.stringify(stored));
    showToast('❤️ Added to wishlist', 'success');
  }

  localStorage.setItem('pn_wishlist', JSON.stringify(wishlist));
  updateWishBadge();

  if (btn) {
    const wished = wishlist.includes(key);
    btn.classList.toggle('wished', wished);
    btn.querySelector('svg').setAttribute('fill', wished ? 'currentColor' : 'none');
  }
}

function renderWishlist() {
  const stored = JSON.parse(localStorage.getItem('pn_wish_products') || '[]');
  const items  = stored.filter(p => wishlist.includes(p.link));

  document.getElementById('wish-sub').textContent = `${items.length} saved item${items.length !== 1 ? 's' : ''}`;

  if (items.length === 0) {
    document.getElementById('wishlist-grid').innerHTML = '';
    document.getElementById('wishlist-empty').style.display = '';
  } else {
    document.getElementById('wishlist-empty').style.display = 'none';
    document.getElementById('wishlist-grid').innerHTML = items.map(p => renderProductCard(p)).join('');
  }
  updateWishBadge();
}

function updateWishBadge() {
  const badge = document.getElementById('wish-badge');
  const count = wishlist.length;
  badge.textContent = count;
  badge.style.display = count > 0 ? 'flex' : 'none';
}

// ── UTILS ─────────────────────────────────
function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function showToast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type} show`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 2800);
}

// ── KEYBOARD SEARCH ───────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    const focused = document.activeElement;
    if (focused && focused.tagName === 'INPUT') {
      const id = focused.id;
      if (id === 'hero-input' || id === 'cta-input') doSearch(id);
      else if (id === 'search-input') doSearch('search-input');
    }
  }
});

// ── INIT ──────────────────────────────────
updateWishBadge();
showPage('home');
