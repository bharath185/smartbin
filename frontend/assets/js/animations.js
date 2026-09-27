/* ============================================================
   SmartBin - Smart City Animation System (shared behavior)
   Loaded after api.js on every page.
   ============================================================ */

(function () {
  'use strict';

  const reduceMedia = window.matchMedia('(prefers-reduced-motion: reduce)');
  const reduced = reduceMedia.matches;
  const isMobile = window.innerWidth < 768;

  /* ---------------- Loading screen ---------------- */
  function buildLoader() {
    if (document.getElementById('smartLoader')) return;
    const d = document.createElement('div');
    d.className = 'smart-loader' + (reduced ? ' reduced' : '');
    d.id = 'smartLoader';
    d.innerHTML =
      '<div class="loader-inner">' +
      '  <div class="loader-ring">' +
      '    <div class="loader-sweep"></div>' +
      '    <div class="loader-core">' +
      '      <svg viewBox="0 0 32 32" fill="none"><rect width="32" height="32" rx="8" fill="#2563eb"/>' +
      '      <path d="M8 12h16v2H8zm2 4h12v8H10z" fill="#fff"/><path d="M12 10h8v2h-8z" fill="#fff" opacity=".6"/></svg>' +
      '    </div>' +
      '  </div>' +
      '  <div class="loader-text" id="smartLoaderText">Connecting to Smart City Network...</div>' +
      '  <div class="loader-dots"><span></span><span></span><span></span></div>' +
      '</div>';
    document.body.appendChild(d);
  }

  function revealLoader() {
    buildLoader();
    const overlay = document.getElementById('smartLoader');
    if (!overlay) return;
    const text = document.getElementById('smartLoaderText');
    const dots = overlay.querySelector('.loader-dots');

    const finish = () => {
      overlay.classList.add('done');
      setTimeout(() => overlay.remove(), 550);
    };

    if (reduced) {
      setTimeout(() => {
        if (text) { text.textContent = 'System Online'; text.classList.add('system-online'); }
        if (dots) dots.classList.add('online');
      }, 60);
      setTimeout(finish, 750);
      return;
    }

    setTimeout(() => {
      if (text) { text.textContent = 'System Online'; text.classList.add('system-online'); }
      if (dots) dots.classList.add('online');
    }, 1050);
    setTimeout(finish, 1700);
  }

  /* ---------------- Page transitions ---------------- */
  function initPageTransitions() {
    if (reduced) return;
    document.body.classList.add('page-entering');
    document.addEventListener('click', function (e) {
      const a = e.target.closest('a[href]');
      if (!a) return;
      const href = a.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('javascript:')) return;
      if (a.target && a.target !== '_self') return;
      const isHtml = /\.html?($|\?)/.test(href) || href.endsWith('/');
      if (!isHtml) return;
      e.preventDefault();
      document.body.classList.add('page-leaving');
      setTimeout(function () { window.location.href = a.href; }, 260);
    });
  }

  /* ---------------- Background network canvas ---------------- */
  function initNetwork() {
    if (!document.body.hasAttribute('data-network')) return;
    if (reduced) return;

    const canvas = document.createElement('canvas');
    canvas.id = 'networkCanvas';
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    let w, h;
    const count = isMobile ? 14 : 30;
    const particles = [];

    function size() {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    }
    size();

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.28,
        vy: (Math.random() - 0.5) * 0.28,
        r: Math.random() * 1.7 + 0.7,
        node: Math.random() < 0.2
      });
    }

    let running = true;
    function tick() {
      if (!running) return;
      ctx.clearRect(0, 0, w, h);

      for (const p of particles) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;

        if (p.node) {
          ctx.fillStyle = 'rgba(37,99,235,.4)';
          ctx.beginPath(); ctx.arc(p.x, p.y, p.r + 2, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = 'rgba(37,99,235,.05)';
          ctx.beginPath(); ctx.arc(p.x, p.y, p.r + 6, 0, Math.PI * 2); ctx.fill();
        }
        ctx.fillStyle = p.node ? 'rgba(37,99,235,.5)' : 'rgba(99,102,241,.16)';
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
      }

      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(37,99,235,.07)';
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i], b = particles[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < 120) {
            ctx.globalAlpha = 1 - d / 120;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
      }
      ctx.globalAlpha = 1;
      requestAnimationFrame(tick);
    }
    tick();

    window.addEventListener('resize', size);
    document.addEventListener('visibilitychange', function () {
      running = !document.hidden;
      if (running) tick();
    });
  }

  /* ---------------- Notifications ---------------- */
  const notchIcons = {
    success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M5 13l4 4L19 7"/></svg>',
    warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    danger: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01"/><circle cx="12" cy="12" r="10"/></svg>',
    emergency: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>'
  };

  function notify(opts) {
    const o = opts || {};
    const type = o.type || 'info';
    const sticky = !!o.sticky;

    let container = document.querySelector('.smart-notify-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'smart-notify-container';
      document.body.appendChild(container);
    }

    const el = document.createElement('div');
    el.className = 'smart-notify ' + type;
    el.innerHTML =
      '<div class="smart-notify-icon">' + (notchIcons[type] || notchIcons.info) + '</div>' +
      '<div class="smart-notify-body">' +
      '  <div class="smart-notify-title">' + (o.title || '') + '</div>' +
      (o.body ? '<div class="smart-notify-text">' + o.body + '</div>' : '') +
      '</div>' +
      (sticky ? '<button class="smart-notify-close" aria-label="Dismiss">&times;</button>' : '');

    if (sticky) {
      el.querySelector('.smart-notify-close').addEventListener('click', function () { remove(); });
    }
    container.appendChild(el);

    function remove() {
      if (el.classList.contains('leaving')) return;
      el.classList.add('leaving');
      setTimeout(function () { el.remove(); }, 380);
    }

    if (!sticky && o.duration !== 0) {
      setTimeout(remove, o.duration || 5200);
    }
    return el;
  }

  /* ---------------- Fill-level entrance animation ---------------- */
  function animateFillBars(root) {
    const host = root || document;
    host.querySelectorAll('.fill-bar-bg').forEach(function (bg, i) {
      const bar = bg.querySelector('.fill-bar');
      if (!bar) return;
      const target = parseFloat(bar.style.width) || 0;
      bar.style.width = '0%';
      setTimeout(function () {
        bar.style.width = target + '%';
      }, 40 + i * 45);
    });
  }

  /* ---------------- Dashboard bin fullness tiles ---------------- */
  function animateFillStatus(root) {
    const host = root || document;
    host.querySelectorAll('.bs-tile').forEach(function (tile, i) {
      const fill = tile.querySelector('.bs-fill');
      if (!fill) return;
      const target = parseInt(tile.querySelector('.bs-fill').dataset.fill, 10) || 0;
      fill.style.transition = 'none';
      fill.style.height = '0%';
      void fill.offsetWidth;
      fill.style.transition = '';
      setTimeout(function () {
        fill.style.height = target + '%';
      }, 90 + i * 60);
    });
  }

  /* ---------------- Live smart-city alerts (once per session) ---------------- */
  function runLiveAlerts(bins) {
    const key = 'smartbin:alerts';
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, '1');

    const queue = bins.map(function (b) { return { b: b }; }).sort(function (a, c) { return c.b.fill_level - a.b.fill_level; })
      .slice(0, 3)
      .filter(function (x) { return x.b.fill_level >= 60; });

    queue.forEach(function (item, i) {
      const b = item.b;
      const delay = 2000 + i * 900;
      if (b.fill_level >= 85) {
        setTimeout(function () {
          notify({
            title: 'BIN FULL',
            body: 'Bin ' + b.dustbin_id + ' (' + (b.location || 'unknown') + ') requires collection.',
            type: 'danger', duration: 9000
          });
        }, delay);
      } else if (b.fill_level >= 60) {
        setTimeout(function () {
          notify({
            title: 'BIN NEARLY FULL',
            body: 'Bin ' + b.dustbin_id + ' has reached ' + b.fill_level.toFixed(0) + '%.',
            type: 'warning'
          });
        }, delay);
      }
    });
  }

  /* ---------------- AI waste detection scan ---------------- */
  function aiScan() {
    return new Promise(function (resolve) {
      if (reduced) return resolve();

      const ov = document.createElement('div');
      ov.className = 'ai-scan-overlay';
      ov.innerHTML =
        '<div class="ai-camera">' +
        '  <div class="ai-cam-corners"></div>' +
        '  <div class="ai-scan-grid"></div>' +
        '  <div class="ai-scanline"></div>' +
        '  <div class="ai-frame-label">ESP32-CAM · AI Vision</div>' +
        '</div>' +
        '<div class="ai-status"><span class="ai-status-dot"></span><span>AI Analysing...</span></div>';
      document.body.appendChild(ov);

      setTimeout(function () {
        const st = ov.querySelector('.ai-status');
        st.className = 'ai-status result';
        st.innerHTML = '<span class="ai-status-dot"></span><span>Waste Detected</span>';
        const rec = document.createElement('div');
        rec.className = 'ai-recommend';
        rec.innerHTML = '<span style="font-weight:800">Rec:</span> Dry Recyclable Bin';
        ov.appendChild(rec);
      }, 1000);

      setTimeout(function () {
        ov.classList.add('out');
        setTimeout(function () { ov.remove(); resolve(); }, 430);
      }, 1900);
    });
  }

  /* ---------------- Complaint status timeline ---------------- */
  function showComplaintTimeline(refId) {
    const holder = document.getElementById('smartTimeline');
    if (!holder) return;
    holder.innerHTML =
      '<div class="timeline">' +
      '  <div class="tl-step done"><div class="tl-dot">&#10003;</div>' +
      '    <div class="tl-body"><strong>Complaint Submitted</strong><small>Reference #' + refId + '</small></div></div>' +
      '  <div class="tl-step active"><div class="tl-dot">&#8226;</div>' +
      '    <div class="tl-body"><strong>Under Review</strong><small>Our team is triaging your issue</small></div></div>' +
      '  <div class="tl-step"><div class="tl-dot">3</div>' +
      '    <div class="tl-body"><strong>Driver Assigned</strong><small>Nearest collection driver will be assigned</small></div></div>' +
      '  <div class="tl-step"><div class="tl-dot">4</div>' +
      '    <div class="tl-body"><strong>Issue Resolved</strong><small>Confirmation shared once complete</small></div></div>' +
      '</div>';
  }

  /* ---------------- Shared sidebar: municipality navigation ---------------- */
  const navIcons = {
    dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    dustbins: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M5 6v14a2 2 0 002 2h10a2 2 0 002-2V6"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>',
    map: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 4L3.5 6v14L9 18l6 2 5.5-2V4L15 6 9 4z"/><path d="M9 4v14M15 6v14"/></svg>',
    analytics: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    alerts: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
    collections: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 17l2-8h14l2 8M5 17h14v3H5zM7 17v-2h10v2"/><circle cx="8" cy="8" r="2"/><circle cx="16" cy="8" r="2"/></svg>',
    employees: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0113 0"/><path d="M17 8.5a3 3 0 010 5M21.5 20a6 6 0 00-4.5-5.8"/></svg>',
    customers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0116 0"/></svg>',
    complaints: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    reports: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/></svg>',
    solar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="2" width="16" height="3" rx="1"/><path d="M6 5v6h12V5M4 11h16v2H4zM7 8h10M9 17l-2 3M15 17l2 3M12 13v7"/></svg>',
    impact: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2l9 5-9 5-9-5 9-5z"/><path d="M3 12l9 5 9-5M3 17l9 5 9-5"/></svg>',
    scan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="3" height="3"/><path d="M20 14v3h-3M20 20h-3"/></svg>',
    leaderboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 15l-4 5h8l-4-5z"/><circle cx="12" cy="9" r="6"/><path d="M9 9l2 2 4-4"/></svg>',
    settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1L7 17M17 7l2.1-2.1"/></svg>'
  };

  const SIDEBAR_ITEMS = [
    { id: 'nav-dashboard',  href: 'index.html',     label: 'Dashboard',       icon: 'dashboard',  key: 'dashboard' },
    { id: 'nav-dustbins',   href: 'dustbins.html',  label: 'Smart Bins',      icon: 'dustbins',   key: 'dustbins' },
    { id: 'nav-map',        href: 'map.html',       label: 'Live Map',        icon: 'map',        key: 'map' },
    { id: 'nav-analytics',  href: 'analytics.html', label: 'Waste Analytics', icon: 'analytics',  key: 'analytics' },
    { id: 'nav-alerts',     href: 'alerts.html',    label: 'Alerts',          icon: 'alerts',     key: 'alerts' },
    { id: 'nav-collections', href: 'collections.html', label: 'Collections',     icon: 'collections', key: 'collections' },
    { id: 'nav-employees',  href: 'drivers.html', label: 'Drivers',         icon: 'employees',  key: 'drivers' },
    { id: 'nav-customers',  href: 'customers.html', label: 'Customers',       icon: 'customers',  key: 'customers' },
    { id: 'nav-complaints', href: 'complaints.html',label: 'Complaints',      icon: 'complaints', key: 'complaints' },
    { id: 'nav-reports',    href: 'reports.html',   label: 'Reports',         icon: 'reports',    key: 'reports' },
    { id: 'nav-impact',     href: 'impact.html',    label: 'Environmental Impact', icon: 'impact', key: 'impact' },
    { id: 'nav-leaderboard',href: 'leaderboard.html',label: 'Leaderboard',    icon: 'leaderboard',key: 'leaderboard' },
    { id: 'nav-settings',   href: 'settings.html',  label: 'Settings',        icon: 'settings',   key: 'settings' }
  ];

  function currentPageKey() {
    const file = (window.location.pathname.split('/').pop() || 'index.html').replace(/\.html?$/, '');
    const key = (document.body && document.body.dataset.page) || file;
    return key === 'index' ? 'dashboard' : key;
  }

  function augmentNav() {
    const nav = document.querySelector('.sidebar-nav');
    if (!nav) return;
    const pageKey = currentPageKey();
    nav.innerHTML = SIDEBAR_ITEMS.map(function (it) {
      return '<a href="' + it.href + '" id="' + it.id + '"' +
        (it.key === pageKey ? ' class="active"' : '') + '>' +
        navIcons[it.icon] + '<span>' + it.label + '</span></a>';
    }).join('');
  }

  /* ---------------- Count-up numbers ---------------- */
  function animateCountUp(el, end, opts) {
    const o = opts || {};
    const dur = o.duration || 1400;
    const decimals = o.decimals || 0;
    const start = performance.now();
    function frame(now) {
      const t = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = (end * eased).toFixed(decimals);
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function countUp(delays) {
    document.querySelectorAll('[data-count]').forEach(function (el) {
      const end = parseFloat(el.getAttribute('data-count')) || 0;
      const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
      const delay = (delays && delays[el.dataset.countKey]) || 200;
      setTimeout(function () { animateCountUp(el, end, { decimals: decimals }); }, delay);
    });
  }

  /* ---------------- Deterministic hash -> pseudo map coords ---------------- */
  function seedHash(str) {
    let h = 2166136261;
    const s = String(str || 'bin');
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return (h >>> 0) / 4294967295;
  }

  /* ---------------- Init ---------------- */
  function init() {
    revealLoader();
    initPageTransitions();
    initNetwork();
    augmentNav();
    countUp();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.SmartCity = {
    notify: notify,
    animateFillBars: animateFillBars,
    animateFillStatus: animateFillStatus,
    runLiveAlerts: runLiveAlerts,
    aiScan: aiScan,
    showComplaintTimeline: showComplaintTimeline,
    reducedMotion: reduced,
    countUp: countUp,
    seedHash: seedHash
  };
})();