import { useState, useEffect, useCallback } from "react";

// ── SIMULATED API DATA (mirrors real scraper output) ─────
const MOCK_DB = {
  laptop: [
    { name:"HP Laptop 15s-eq2144AU Ryzen 5", price:72000, store:"Daraz", link:"https://daraz.com.np/hp-15s" },
    { name:"Lenovo IdeaPad Slim 3 Ryzen 5", price:68500, store:"Hukut", link:"https://hukut.com/lenovo-slim3" },
    { name:"Dell Inspiron 15 Core i5 12th Gen", price:89000, store:"Daraz", link:"https://daraz.com.np/dell-inspiron" },
    { name:"Asus VivoBook 15 Core i5", price:79000, store:"Hukut", link:"https://hukut.com/asus-vivobook" },
    { name:"Acer Aspire 5 Ryzen 7", price:95000, store:"Daraz", link:"https://daraz.com.np/acer-aspire5" },
    { name:"MacBook Air M1 8GB 256GB", price:155000, store:"Hukut", link:"https://hukut.com/macbook-air-m1" },
    { name:"HP Pavilion 15 Core i7", price:115000, store:"Daraz", link:"https://daraz.com.np/hp-pavilion" },
    { name:"Lenovo ThinkPad E14 Core i5", price:98000, store:"Hukut", link:"https://hukut.com/thinkpad-e14" },
  ],
  phone: [
    { name:"Samsung Galaxy A54 5G 8GB 256GB", price:42999, store:"Daraz", link:"https://daraz.com.np/samsung-a54" },
    { name:"iPhone 15 128GB Black", price:149900, store:"Daraz", link:"https://daraz.com.np/iphone15" },
    { name:"Xiaomi Redmi Note 12 Pro 5G", price:32500, store:"Hukut", link:"https://hukut.com/redmi-note12" },
    { name:"Realme 11 Pro+ 5G 12GB", price:38000, store:"Daraz", link:"https://daraz.com.np/realme11" },
    { name:"OnePlus Nord CE 3 Lite", price:29999, store:"Hukut", link:"https://hukut.com/oneplus-nord-ce3" },
    { name:"Samsung Galaxy S23 FE 8GB", price:79000, store:"Daraz", link:"https://daraz.com.np/s23fe" },
    { name:"Vivo V29 5G 8GB 256GB", price:44500, store:"Hukut", link:"https://hukut.com/vivo-v29" },
  ],
  headphones: [
    { name:"Sony WH-1000XM5 Noise Cancelling", price:38000, store:"Daraz", link:"https://daraz.com.np/sony-xm5" },
    { name:"Bose QuietComfort 45 Bluetooth", price:44000, store:"Hukut", link:"https://hukut.com/bose-qc45" },
    { name:"JBL Tune 770NC Wireless", price:9800, store:"Daraz", link:"https://daraz.com.np/jbl-770nc" },
    { name:"Sennheiser HD 450BT", price:14500, store:"Hukut", link:"https://hukut.com/sennheiser-hd450" },
    { name:"Apple AirPods Pro 2nd Gen", price:42000, store:"Daraz", link:"https://daraz.com.np/airpods-pro2" },
  ],
  camera: [
    { name:"Canon EOS M50 Mark II Mirrorless", price:92000, store:"Daraz", link:"https://daraz.com.np/canon-m50" },
    { name:"Sony Alpha ZV-E10 Mirrorless", price:85000, store:"Hukut", link:"https://hukut.com/sony-zve10" },
    { name:"Nikon Z30 Mirrorless Camera", price:98000, store:"Daraz", link:"https://daraz.com.np/nikon-z30" },
    { name:"GoPro Hero 12 Black Action", price:62000, store:"Hukut", link:"https://hukut.com/gopro12" },
  ],
  gaming: [
    { name:"Logitech G502 Hero Gaming Mouse", price:8500, store:"Daraz", link:"https://daraz.com.np/g502" },
    { name:"Razer DeathAdder V3 Gaming Mouse", price:12000, store:"Hukut", link:"https://hukut.com/deathadder-v3" },
    { name:"PlayStation 5 Slim Disc Edition", price:110000, store:"Daraz", link:"https://daraz.com.np/ps5-slim" },
    { name:"Xbox Series X 1TB Console", price:105000, store:"Hukut", link:"https://hukut.com/xbox-series-x" },
    { name:"Nintendo Switch OLED Model", price:72000, store:"Daraz", link:"https://daraz.com.np/switch-oled" },
  ],
  tablet: [
    { name:"iPad Air 5th Gen 64GB WiFi", price:96000, store:"Daraz", link:"https://daraz.com.np/ipad-air5" },
    { name:"Samsung Galaxy Tab S9 FE", price:68000, store:"Hukut", link:"https://hukut.com/tab-s9fe" },
    { name:"Lenovo Tab P12 Pro 12.6\"", price:78000, store:"Daraz", link:"https://daraz.com.np/lenovo-p12" },
  ],
};

function mockSearch(query) {
  const q = query.toLowerCase();
  let results = [];
  for (const [key, items] of Object.entries(MOCK_DB)) {
    if (q.includes(key) || items.some(p => p.name.toLowerCase().includes(q))) {
      results = [...results, ...items.filter(p =>
        p.name.toLowerCase().includes(q) || q.includes(key)
      )];
    }
  }
  if (results.length === 0) {
    // fallback: return all
    results = Object.values(MOCK_DB).flat().filter(p =>
      p.name.toLowerCase().split(' ').some(w => q.includes(w) && w.length > 2)
    );
  }
  return [...new Map(results.map(p => [p.link, p])).values()]
    .sort((a,b) => a.price - b.price);
}

// ── COLORS ───────────────────────────────
const C = {
  crimson:'#c0392b', crimsonDark:'#96281b', gold:'#f39c12',
  sand:'#fdf6ec', ink:'#1a1208', inkSoft:'#4a3f2f',
  muted:'#8b7d6b', border:'#e8ddd0', white:'#ffffff',
  cardBg:'#fffdf9', success:'#27ae60',
};

// ── HELPERS ──────────────────────────────
const fmt = n => 'Rs. ' + Number(n).toLocaleString('en-IN');
const esc = s => String(s);

function StoreTag({ store }) {
  const colors = {
    Daraz: { bg:'rgba(255,127,0,0.12)', color:'#e67e00' },
    Hukut: { bg:'rgba(39,174,96,0.12)', color:'#27ae60' },
  };
  const s = colors[store] || { bg:'rgba(192,57,43,0.1)', color:C.crimson };
  return (
    <span style={{ background:s.bg, color:s.color, fontSize:'0.68rem', fontWeight:600, letterSpacing:'1px', textTransform:'uppercase', borderRadius:999, padding:'3px 10px' }}>
      {store}
    </span>
  );
}

// ── PRODUCT CARD ─────────────────────────
function ProductCard({ p, isCheapest, onView }) {
  const emoji = p.store === 'Daraz' ? '🛒' : '🏪';
  return (
    <div onClick={() => onView(p)}
      style={{ background:C.cardBg, border:`1px solid ${C.border}`, borderRadius:18, overflow:'hidden', cursor:'pointer', transition:'transform 0.2s, box-shadow 0.2s', display:'flex', flexDirection:'column' }}
      onMouseEnter={e => { e.currentTarget.style.transform='translateY(-5px)'; e.currentTarget.style.boxShadow='0 14px 40px rgba(26,18,8,0.1)'; }}
      onMouseLeave={e => { e.currentTarget.style.transform=''; e.currentTarget.style.boxShadow=''; }}>
      <div style={{ background:'linear-gradient(135deg,#f0e8dc,#e8d8c8)', height:140, display:'flex', alignItems:'center', justifyContent:'center', fontSize:'2.8rem', position:'relative' }}>
        {emoji}
        {isCheapest && (
          <span style={{ position:'absolute', bottom:8, left:8, fontSize:'0.65rem', fontWeight:700, background:C.crimson, color:'#fff', borderRadius:999, padding:'3px 9px' }}>✅ Cheapest</span>
        )}
      </div>
      <div style={{ padding:16, flex:1, display:'flex', flexDirection:'column' }}>
        <div style={{ marginBottom:6 }}><StoreTag store={p.store} /></div>
        <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'0.92rem', fontWeight:700, color:C.ink, marginBottom:10, lineHeight:1.35, flex:1 }}>{p.name}</div>
        <div style={{ fontWeight:700, fontSize:'1.05rem', marginBottom:12 }}>{fmt(p.price)}</div>
        <div style={{ textAlign:'center', background:C.sand, border:`1.5px solid ${C.border}`, borderRadius:999, padding:'8px', fontSize:'0.82rem', fontWeight:500, color:C.inkSoft }}>
          View on {p.store === 'Daraz' ? 'Drz' : p.store} →
        </div>
      </div>
    </div>
  );
}

// ── SEARCH BAR ───────────────────────────
function SearchBar({ value, onChange, onSearch, placeholder, size='md' }) {
  return (
    <div style={{ display:'flex', alignItems:'center', background:C.white, border:`2px solid ${C.border}`, borderRadius:999, padding: size==='lg' ? '6px 6px 6px 22px' : '5px 5px 5px 16px', gap:10, boxShadow:'0 4px 24px rgba(26,18,8,0.07)', transition:'border-color 0.2s' }}
      onFocus={e => e.currentTarget.style.borderColor=C.crimson}
      onBlur={e => e.currentTarget.style.borderColor=C.border}>
      <svg fill="none" viewBox="0 0 24 24" stroke={C.muted} strokeWidth="2" width={size==='lg'?18:15} height={size==='lg'?18:15} style={{ flexShrink:0 }}>
        <circle cx="11" cy="11" r="8"/><path strokeLinecap="round" d="m21 21-4.35-4.35"/>
      </svg>
      <input value={value} onChange={e => onChange(e.target.value)}
        onKeyDown={e => e.key==='Enter' && onSearch()}
        placeholder={placeholder}
        style={{ flex:1, border:'none', outline:'none', fontFamily:"'DM Sans',sans-serif", fontSize: size==='lg' ? '1rem' : '0.875rem', background:'transparent', color:C.ink, minWidth:0 }} />
      <button onClick={onSearch}
        style={{ background:C.crimson, color:'#fff', border:'none', borderRadius:999, padding: size==='lg' ? '11px 26px' : '8px 18px', fontFamily:"'DM Sans',sans-serif", fontSize: size==='lg' ? '0.9rem':'0.82rem', fontWeight:500, cursor:'pointer', whiteSpace:'nowrap' }}>
        Search
      </button>
    </div>
  );
}

// ── SPINNER ──────────────────────────────
function Spinner({ label }) {
  return (
    <div style={{ textAlign:'center', padding:'60px 20px' }}>
      <div style={{ width:48, height:48, border:`4px solid ${C.border}`, borderTopColor:C.crimson, borderRadius:'50%', animation:'spin 0.8s linear infinite', margin:'0 auto' }} />
      <p style={{ marginTop:20, color:C.muted, fontSize:'0.95rem' }}>{label}</p>
      <p style={{ color:C.muted, fontSize:'0.8rem', marginTop:6 }}>This may take 10–20 seconds with the real backend</p>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

// ── TOAST ────────────────────────────────
function Toast({ msg, visible, type }) {
  const bg = type==='success' ? C.success : type==='error' ? C.crimson : C.ink;
  return (
    <div style={{ position:'fixed', bottom:24, right:24, zIndex:9999, background:bg, color:'#fff', borderRadius:12, padding:'13px 20px', fontSize:'0.875rem', fontWeight:500, boxShadow:'0 8px 32px rgba(0,0,0,0.2)', transform: visible?'translateY(0)':'translateY(80px)', opacity: visible?1:0, transition:'all 0.3s ease', pointerEvents:'none' }}>
      {msg}
    </div>
  );
}

// ── NAV ──────────────────────────────────
function Nav({ page, onNav, navSearch, onNavSearch, onNavSearchGo }) {
  return (
    <div style={{ position:'sticky', top:0, zIndex:100, background:'rgba(253,246,236,0.95)', backdropFilter:'blur(12px)', borderBottom:`1px solid ${C.border}` }}>
      <div style={{ maxWidth:1200, margin:'0 auto', padding:'13px 24px', display:'flex', alignItems:'center', justifyContent:'space-between', gap:12 }}>
        <span onClick={() => onNav('home')}
          style={{ fontFamily:"'Playfair Display',serif", fontSize:'1.5rem', fontWeight:900, color:C.crimson, cursor:'pointer', letterSpacing:'-0.5px', flexShrink:0 }}>
          Price<span style={{ color:C.ink }}>Nepal</span>
        </span>
        <div style={{ flex:1, maxWidth:380, margin:'0 16px' }}>
          <SearchBar value={navSearch} onChange={onNavSearch} onSearch={onNavSearchGo} placeholder="Search products…" />
        </div>
        <div style={{ display:'flex', gap:8, flexShrink:0 }}>
          {[
            { id:'search',   label:'Search',   icon:<><circle cx="11" cy="11" r="8"/><path strokeLinecap="round" d="m21 21-4.35-4.35"/></> },
          ].map(b => (
            <button key={b.id} onClick={() => onNav(b.id)}
              style={{ display:'flex', alignItems:'center', gap:6, background:'none', border:`1.5px solid ${page===b.id?C.crimson:C.border}`, borderRadius:999, padding:'8px 16px', fontFamily:"'DM Sans',sans-serif", fontSize:'0.875rem', fontWeight:500, color: page===b.id?C.crimson:C.inkSoft, cursor:'pointer', position:'relative' }}>
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" width="14" height="14">{b.icon}</svg>
              {b.label}
              {b.badge > 0 && (
                <span style={{ position:'absolute', top:-6, right:-6, background:C.crimson, color:'#fff', borderRadius:'50%', width:17, height:17, display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.6rem', fontWeight:700 }}>{b.badge}</span>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── HOME PAGE ─────────────────────────────
function HomePage({ onSearchGo }) {
  const [q, setQ] = useState('');
  const cats = [
    { name:'Smartphones', emoji:'📱', q:'phone' },
    { name:'Laptops',     emoji:'💻', q:'laptop' },
    { name:'Audio',       emoji:'🎧', q:'headphones' },
    { name:'Cameras',     emoji:'📷', q:'camera' },
    { name:'Tablets',     emoji:'📟', q:'tablet' },
    { name:'Gaming',      emoji:'🎮', q:'gaming' },
  ];
  return (
    <div>
      {/* Hero */}
      <div style={{ position:'relative', overflow:'hidden', padding:'76px 24px 86px', background:'linear-gradient(135deg,#fff8f0,#fdf6ec 50%,#fce8d8)' }}>
        <div style={{ position:'absolute', top:-60, right:-80, width:500, height:500, background:'radial-gradient(circle,rgba(192,57,43,0.08),transparent 70%)', pointerEvents:'none' }} />
        <div style={{ maxWidth:860, margin:'0 auto', textAlign:'center', position:'relative', zIndex:1 }}>
          <div style={{ display:'inline-block', fontSize:'0.75rem', fontWeight:500, letterSpacing:'2px', textTransform:'uppercase', color:C.crimson, border:`1px solid rgba(192,57,43,0.3)`, borderRadius:999, padding:'5px 16px', marginBottom:22 }}>
            🕷️ Powered by Live Python Scrapers
          </div>
          <h1 style={{ fontFamily:"'Playfair Display',serif", fontSize:'clamp(2.4rem,5.5vw,4.2rem)', fontWeight:900, lineHeight:1.1, letterSpacing:'-1.5px', color:C.ink, marginBottom:18 }}>
            Find the Best Prices<br/>
            <em style={{ fontStyle:'normal', color:C.crimson }}>Across Nepal's Top Stores</em>
          </h1>
          <p style={{ fontSize:'1.05rem', color:C.muted, maxWidth:540, margin:'0 auto 32px', fontWeight:300, lineHeight:1.7 }}>
            Real-time prices scraped from <strong style={{ color:C.ink }}>Daraz</strong> & <strong style={{ color:C.ink }}>Hukut</strong> using headless Chrome + BeautifulSoup. No stale data, ever.
          </p>
          <div style={{ maxWidth:600, margin:'0 auto 36px' }}>
            <SearchBar value={q} onChange={setQ} onSearch={() => onSearchGo(q)} placeholder="Search for phones, laptops, cameras…" size="lg" />
          </div>
          <div style={{ display:'flex', justifyContent:'center', gap:48 }}>
            {[['2','Live Stores'],['Real','Time Data'],['24/7','Updated']].map(([n,l]) => (
              <div key={l} style={{ textAlign:'center' }}>
                <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'1.9rem', fontWeight:700, color:C.crimson }}>{n}</div>
                <div style={{ fontSize:'0.72rem', color:C.muted, textTransform:'uppercase', letterSpacing:'1px' }}>{l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* How it works */}
      <div style={{ padding:'60px 24px', background:C.white, borderTop:`1px solid ${C.border}` }}>
        <div style={{ maxWidth:1200, margin:'0 auto' }}>
          <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'2rem', fontWeight:700, textAlign:'center', marginBottom:36 }}>How It Works</div>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(240px,1fr))', gap:22 }}>
            {[
              { icon:'🕷️', bg:'rgba(192,57,43,0.1)', title:'Live Scraping', desc:'Your Python scrapers hit Daraz (Selenium) and Hukut (requests) in real time on every search.' },
              { icon:'⚡', bg:'rgba(243,156,18,0.1)', title:'Flask API',     desc:'A Flask backend runs the scrapers and exposes GET /api/search?q= returning sorted JSON.' },
              { icon:'✅', bg:'rgba(39,174,96,0.1)',  title:'Fresh Results', desc:'Results sorted by price. Cheapest deal highlighted. Cached in memory to avoid re-scraping.' },
            ].map(f => (
              <div key={f.title} style={{ background:C.cardBg, border:`1px solid ${C.border}`, borderRadius:18, padding:'30px 26px', textAlign:'center' }}>
                <div style={{ width:52, height:52, borderRadius:14, background:f.bg, display:'flex', alignItems:'center', justifyContent:'center', margin:'0 auto 16px', fontSize:'1.4rem' }}>{f.icon}</div>
                <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'1.1rem', fontWeight:700, marginBottom:10 }}>{f.title}</div>
                <div style={{ fontSize:'0.875rem', color:C.muted, lineHeight:1.65 }}>{f.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Categories */}
      <div style={{ background:'linear-gradient(to bottom,#fff8ef,#fdf6ec)', padding:'52px 24px' }}>
        <div style={{ maxWidth:1200, margin:'0 auto' }}>
          <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'2rem', fontWeight:700, textAlign:'center', marginBottom:36 }}>Quick Search by Category</div>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))', gap:14 }}>
            {cats.map(c => (
              <div key={c.name} onClick={() => onSearchGo(c.q)}
                style={{ background:C.white, border:`1px solid ${C.border}`, borderRadius:14, padding:'22px 14px', textAlign:'center', cursor:'pointer', transition:'all 0.2s' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor=C.crimson; e.currentTarget.style.transform='scale(1.05)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor=C.border; e.currentTarget.style.transform=''; }}>
                <div style={{ fontSize:'1.8rem', marginBottom:8 }}>{c.emoji}</div>
                <div style={{ fontWeight:500, fontSize:'0.875rem' }}>{c.name}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA */}
      <div style={{ background:C.crimson, padding:'68px 24px', textAlign:'center', position:'relative', overflow:'hidden' }}>
        <div style={{ maxWidth:640, margin:'0 auto', position:'relative', zIndex:1 }}>
          <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'clamp(1.8rem,4vw,3rem)', fontWeight:900, color:'#fff', marginBottom:12 }}>Start Saving Today</div>
          <p style={{ color:'rgba(255,255,255,0.8)', marginBottom:30, fontWeight:300 }}>Type any product and get live scraped prices from Nepal's top stores</p>
          <div style={{ maxWidth:500, margin:'0 auto' }}>
            <SearchBar value={q} onChange={setQ} onSearch={() => onSearchGo(q)} placeholder="e.g. gaming mouse, iPhone 15…" size="lg" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── SEARCH PAGE ───────────────────────────
function SearchPage({ initialQuery, onViewProduct }) {
  const [query, setQuery]   = useState(initialQuery || '');
  const [input, setInput]   = useState(initialQuery || '');
  const [status, setStatus] = useState('idle'); // idle | loading | results | none | error
  const [results, setResults] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [stores, setStores] = useState([]);
  const [minP, setMinP]     = useState('');
  const [maxP, setMaxP]     = useState('');
  const [sort, setSort]     = useState('price-asc');

  // Run "search" when query changes
  useEffect(() => {
    if (!query) return;
    setStatus('loading');
    setResults([]);
    // Simulate API delay (real backend takes 10-20s)
    setTimeout(() => {
      const r = mockSearch(query);
      setResults(r);
      setStatus(r.length > 0 ? 'results' : 'none');
    }, 1800);
  }, [query]);

  // Apply filters whenever results or filters change
  useEffect(() => {
    let f = results.filter(p => {
      const ms = stores.length === 0 || stores.includes(p.store);
      const min = parseFloat(minP) || 0;
      const max = parseFloat(maxP) || Infinity;
      return ms && p.price >= min && p.price <= max;
    });
    if (sort === 'price-asc')  f = [...f].sort((a,b) => a.price - b.price);
    if (sort === 'price-desc') f = [...f].sort((a,b) => b.price - a.price);
    if (sort === 'name')       f = [...f].sort((a,b) => a.name.localeCompare(b.name));
    setFiltered(f);
  }, [results, stores, minP, maxP, sort]);

  const toggleStore = s => setStores(prev => prev.includes(s) ? prev.filter(x=>x!==s) : [...prev,s]);
  const minPrice = filtered.length ? Math.min(...filtered.map(p=>p.price)) : 0;

  const storeCount = s => results.filter(p=>p.store===s).length;

  return (
    <div>
      <div style={{ background:'linear-gradient(to bottom,#fff8f0,#fdf6ec)', padding:'28px 24px', borderBottom:`1px solid ${C.border}` }}>
        <div style={{ maxWidth:700, margin:'0 auto' }}>
          <SearchBar value={input} onChange={setInput} onSearch={() => setQuery(input)} placeholder="Search products…" size="lg" />
        </div>
      </div>

      <div style={{ maxWidth:1200, margin:'0 auto', padding:'28px 24px 60px', display:'grid', gridTemplateColumns:'240px 1fr', gap:28, alignItems:'start' }}>
        {/* Sidebar */}
        <div style={{ position:'sticky', top:80, background:C.cardBg, border:`1px solid ${C.border}`, borderRadius:18, padding:22 }}>
          <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'1.05rem', fontWeight:700, marginBottom:18, paddingBottom:14, borderBottom:`1px solid ${C.border}` }}>Filters</div>

          <div style={{ marginBottom:18 }}>
            <div style={{ fontSize:'0.72rem', fontWeight:600, letterSpacing:'1px', textTransform:'uppercase', color:C.muted, marginBottom:10 }}>Store</div>
            {['Daraz','Hukut'].map(s => (
              <label key={s} style={{ display:'flex', alignItems:'center', gap:8, fontSize:'0.875rem', color:C.inkSoft, marginBottom:8, cursor:'pointer' }}>
                <input type="checkbox" checked={stores.includes(s)} onChange={() => toggleStore(s)} style={{ accentColor:C.crimson }} />
                {s} {results.length > 0 && <span style={{ color:C.muted, fontSize:'0.78rem' }}>({storeCount(s)})</span>}
              </label>
            ))}
          </div>

          <div style={{ marginBottom:18 }}>
            <div style={{ fontSize:'0.72rem', fontWeight:600, letterSpacing:'1px', textTransform:'uppercase', color:C.muted, marginBottom:10 }}>Price Range (Rs.)</div>
            <div style={{ display:'flex', gap:8, alignItems:'center' }}>
              {[['Min',minP,setMinP],['Max',maxP,setMaxP]].map(([ph,v,set]) => (
                <input key={ph} type="number" placeholder={ph} value={v} onChange={e=>set(e.target.value)}
                  style={{ flex:1, border:`1.5px solid ${C.border}`, borderRadius:8, padding:'7px 10px', fontFamily:"'DM Sans',sans-serif", fontSize:'0.85rem', color:C.ink, background:C.white, outline:'none', width:0 }} />
              ))}
            </div>
          </div>

          <div style={{ marginBottom:18 }}>
            <div style={{ fontSize:'0.72rem', fontWeight:600, letterSpacing:'1px', textTransform:'uppercase', color:C.muted, marginBottom:10 }}>Sort By</div>
            <select value={sort} onChange={e=>setSort(e.target.value)}
              style={{ width:'100%', border:`1.5px solid ${C.border}`, borderRadius:8, padding:'8px 10px', fontFamily:"'DM Sans',sans-serif", fontSize:'0.875rem', color:C.ink, background:C.white, outline:'none' }}>
              <option value="price-asc">Price: Low → High</option>
              <option value="price-desc">Price: High → Low</option>
              <option value="name">Name A–Z</option>
            </select>
          </div>

          <button onClick={() => { setStores([]); setMinP(''); setMaxP(''); setSort('price-asc'); }}
            style={{ width:'100%', background:'none', border:`1.5px solid ${C.border}`, borderRadius:999, padding:'9px', fontFamily:"'DM Sans',sans-serif", fontSize:'0.875rem', fontWeight:500, color:C.inkSoft, cursor:'pointer' }}>
            Clear Filters
          </button>
        </div>

        {/* Results */}
        <div>
          {/* Bar */}
          {status === 'results' && (
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:18, flexWrap:'wrap', gap:10 }}>
              <span style={{ fontSize:'0.875rem', color:C.muted }}>{filtered.length} product{filtered.length!==1?'s':''} found for "<strong style={{ color:C.ink }}>{query}</strong>"</span>
              <div style={{ display:'flex', gap:8 }}>
                {['Daraz','Hukut'].filter(s => results.some(p=>p.store===s)).map(s => (
                  <span key={s} style={{ background: s==='Daraz'?'rgba(255,127,0,0.12)':'rgba(39,174,96,0.12)', color: s==='Daraz'?'#e67e00':'#27ae60', fontSize:'0.75rem', fontWeight:600, borderRadius:999, padding:'4px 12px' }}>
                    {s} ({storeCount(s)})
                  </span>
                ))}
              </div>
            </div>
          )}

          {status === 'idle' && (
            <div style={{ textAlign:'center', padding:'80px 20px' }}>
              <div style={{ fontSize:'3rem', marginBottom:14 }}>🔍</div>
              <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'1.5rem', fontWeight:700, marginBottom:8 }}>Search for a product</div>
              <div style={{ color:C.muted }}>Type above and hit Search to get live prices</div>
            </div>
          )}

          {status === 'loading' && <Spinner label={`Scraping Daraz & Hukut for "${query}"…`} />}

          {status === 'none' && (
            <div style={{ textAlign:'center', padding:'60px 20px' }}>
              <div style={{ fontSize:'3rem', marginBottom:12 }}>🔍</div>
              <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'1.4rem', fontWeight:700, marginBottom:8 }}>No products found</div>
              <div style={{ color:C.muted }}>Try a different search term</div>
            </div>
          )}

          {status === 'results' && (
            <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(200px,1fr))', gap:18 }}>
              {filtered.map(p => (
                <ProductCard key={p.link} p={p} isCheapest={p.price===minPrice} onView={onViewProduct} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── PRODUCT PAGE ──────────────────────────
function ProductPage({ product, allResults, onNav }) {
  if (!product) return null;
  const storeEmoji = product.store === 'Daraz' ? '🛒' : '🏪';

  const similar = allResults.filter(x =>
    x.link !== product.link &&
    (x.name.toLowerCase().includes(product.name.split(' ')[0].toLowerCase()))
  ).slice(0, 3);

  const comparisons = [product, ...similar.filter(s => s.store !== product.store).slice(0,2)]
    .sort((a,b) => a.price - b.price);

  return (
    <div>
      {/* Breadcrumb */}
      <div style={{ background:C.white, borderBottom:`1px solid ${C.border}`, padding:'12px 24px' }}>
        <div style={{ maxWidth:1200, margin:'0 auto', display:'flex', gap:8, fontSize:'0.85rem', color:C.muted, alignItems:'center' }}>
          <span style={{ cursor:'pointer' }} onClick={() => onNav('home')}>Home</span>
          <span>›</span>
          <span style={{ cursor:'pointer' }} onClick={() => onNav('search')}>Search</span>
          <span>›</span>
          <span style={{ color:C.ink }}>{product.name.substring(0,40)}…</span>
        </div>
      </div>

      <div style={{ maxWidth:1200, margin:'0 auto', padding:'36px 24px' }}>
        {/* Detail grid */}
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:48, marginBottom:48, alignItems:'start' }}>
          <div style={{ background:'linear-gradient(135deg,#f0e8dc,#e8d8c8)', borderRadius:24, aspectRatio:'1', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'8rem', border:`1px solid ${C.border}` }}>
            {storeEmoji}
          </div>
          <div>
            <div style={{ marginBottom:10 }}><StoreTag store={product.store} /></div>
            <h1 style={{ fontFamily:"'Playfair Display',serif", fontSize:'clamp(1.4rem,2.5vw,2rem)', fontWeight:700, lineHeight:1.25, marginBottom:16 }}>{product.name}</h1>
            <div style={{ fontFamily:"'Playfair Display',serif", fontSize:'2rem', fontWeight:700, marginBottom:22 }}>{fmt(product.price)}</div>
            <div style={{ display:'flex', gap:12, flexWrap:'wrap', marginBottom:24 }}>
              <a href={product.link} target="_blank" rel="noreferrer"
                style={{ display:'inline-flex', alignItems:'center', gap:7, background:C.crimson, color:'#fff', border:'none', borderRadius:999, padding:'11px 24px', fontFamily:"'DM Sans',sans-serif", fontSize:'0.9rem', fontWeight:500, cursor:'pointer', textDecoration:'none' }}>
                View on {product.store === 'Daraz' ? 'Drz' : product.store} →
              </a>
            </div>
            <div style={{ background:C.cardBg, border:`1px solid ${C.border}`, borderRadius:14, padding:18 }}>
              {[['Store',product.store],['Price',fmt(product.price)],['In Stock','✅ Available']].map(([k,v]) => (
                <div key={k} style={{ fontSize:'0.875rem', color:C.inkSoft, marginBottom:8 }}><strong style={{ color:C.ink }}>{k}:</strong> {v}</div>
              ))}
            </div>
          </div>
        </div>

        {/* Price comparison */}
        <h2 style={{ fontFamily:"'Playfair Display',serif", fontSize:'1.6rem', fontWeight:700, marginBottom:16 }}>Price Comparison</h2>
        <div style={{ background:C.cardBg, border:`1px solid ${C.border}`, borderRadius:18, overflow:'hidden', marginBottom:48 }}>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr style={{ background:C.sand }}>
                {['Store','Price','Best to Choose','Action'].map(h => (
                  <th key={h} style={{ padding:'14px 20px', textAlign:'left', fontSize:'0.72rem', fontWeight:600, letterSpacing:'1px', textTransform:'uppercase', color:C.muted, borderBottom:`1px solid ${C.border}` }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparisons.map((s,i) => (
                <tr key={s.link} style={{ background: i===0?'rgba(192,57,43,0.04)':'transparent' }}>
                  <td style={{ padding:'16px 20px', borderBottom:i<comparisons.length-1?`1px solid ${C.border}`:'none', borderLeft:i===0?`3px solid ${C.crimson}`:'none' }}>
                    <strong>{s.store}</strong>
                    {i===0 && <span style={{ marginLeft:8, fontSize:'0.63rem', fontWeight:700, background:C.crimson, color:'#fff', borderRadius:999, padding:'2px 8px', textTransform:'uppercase' }}>Best</span>}
                  </td>
                  <td style={{ padding:'16px 20px', borderBottom:i<comparisons.length-1?`1px solid ${C.border}`:'none' }}><strong>{fmt(s.price)}</strong></td>
                  <td style={{ padding:'16px 20px', borderBottom:i<comparisons.length-1?`1px solid ${C.border}`:'none' }}>
                    <span style={{ color: i===0?C.success:C.muted, fontSize:'0.875rem' }}>
                      {i===0 ? '✅ Best Choice' : i===1 ? 'Good option' : 'Higher price'}
                    </span>
                  </td>
                  <td style={{ padding:'16px 20px', borderBottom:i<comparisons.length-1?`1px solid ${C.border}`:'none' }}>
                    <a href={s.link} target="_blank" rel="noreferrer"
                      style={{ display:'inline-flex', alignItems:'center', gap:5, background:'none', border:`1.5px solid ${C.border}`, borderRadius:999, padding:'6px 14px', fontFamily:"'DM Sans',sans-serif", fontSize:'0.78rem', fontWeight:500, color:C.inkSoft, cursor:'pointer', textDecoration:'none' }}>
                      View on {s.store === 'Daraz' ? 'Drz' : s.store}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── FOOTER ───────────────────────────────
function Footer({ onNav }) {
  return (
    <div style={{ borderTop:`1px solid ${C.border}`, background:C.white, padding:'36px 24px 20px' }}>
      <div style={{ maxWidth:1200, margin:'0 auto', display:'grid', gridTemplateColumns:'2fr 1fr 1fr', gap:36, marginBottom:24 }}>
        <div>
          <span onClick={() => onNav('home')} style={{ fontFamily:"'Playfair Display',serif", fontSize:'1.4rem', fontWeight:900, color:C.crimson, cursor:'pointer', letterSpacing:'-0.5px' }}>
            Price<span style={{ color:C.ink }}>Nepal</span>
          </span>
          <p style={{ fontSize:'0.85rem', color:C.muted, maxWidth:260, lineHeight:1.7, marginTop:10 }}>
            Powered by real-time Python scrapers. Flask backend + Selenium + BeautifulSoup.
          </p>
        </div>
        {[['Stores',['Daraz ↗','Hukut ↗']],['Pages',['Home','Search']]].map(([title, links]) => (
          <div key={title}>
            <div style={{ fontSize:'0.75rem', fontWeight:600, letterSpacing:'1px', textTransform:'uppercase', color:C.muted, marginBottom:12 }}>{title}</div>
            {links.map(l => (
              <div key={l} onClick={() => !l.includes('↗') && onNav(l.toLowerCase())}
                style={{ fontSize:'0.875rem', color:C.muted, marginBottom:8, cursor:'pointer' }}>{l}</div>
            ))}
          </div>
        ))}
      </div>
      <div style={{ maxWidth:1200, margin:'0 auto', borderTop:`1px solid ${C.border}`, paddingTop:16, display:'flex', justifyContent:'space-between', fontSize:'0.78rem', color:C.muted, flexWrap:'wrap', gap:8 }}>
        <span>© 2024 PriceNepal. Powered by Python scrapers.</span>
        <span>Real prices. Real savings.</span>
      </div>
    </div>
  );
}

// ── APP ───────────────────────────────────
export default function App() {
  const [page, setPage]         = useState('home');
  const [searchQ, setSearchQ]   = useState('');
  const [navQ, setNavQ]         = useState('');
  const [product, setProduct]   = useState(null);
  const [allRes, setAllRes]     = useState([]);
  const [toast, setToast]       = useState({ msg:'', visible:false, type:'' });

  const showToast = useCallback((msg, type='') => {
    setToast({ msg, visible:true, type });
    setTimeout(() => setToast(t => ({...t, visible:false})), 2800);
  }, []);

  const navTo = p => { setPage(p); window.scrollTo(0,0); };

  const searchGo = q => {
    if (!q.trim()) return;
    setSearchQ(q);
    setNavQ(q);
    setAllRes(mockSearch(q));
    navTo('search');
  };

  const viewProduct = p => {
    setProduct(p);
    navTo('product');
  };

  return (
    <div style={{ fontFamily:"'DM Sans',sans-serif", background:C.sand, color:C.ink, minHeight:'100vh', overflowX:'hidden' }}>
      <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet" />

      <Nav page={page} onNav={navTo} navSearch={navQ} onNavSearch={setNavQ} onNavSearchGo={() => searchGo(navQ)} />

      {page === 'home'     && <HomePage onSearchGo={searchGo} />}
      {page === 'search'   && <SearchPage initialQuery={searchQ} onViewProduct={viewProduct} />}
      {page === 'product'  && <ProductPage product={product} allResults={allRes} onNav={navTo} />}
      <Footer onNav={navTo} />
      <Toast {...toast} />
    </div>
  );
}
