/* ============================================================
   SmartBin - WStudio behaviour layer
   Reusable: scroll-reveal observer, chart polish, micro helpers.
   Loaded last on every page. Safe to include anywhere/anytime.
   ============================================================ */
(function () {
  'use strict';
  if (window.__wsInit) return;
  window.__wsInit = true;

  /* ============================================================
     Dashboard theme (Light / Dark)
     Shares the 'lg-theme' key + data-lg-theme attribute with the
     auth pages. The attribute is set synchronously at load so
     charts and inline styles read the correct theme. Defaults to
     light unless the user toggled dark (e.g. on the login page).
     ============================================================ */
  const THEME_KEY = 'lg-theme';
  const themeRoot = document.documentElement;
  let themeName = 'light';
  try {
    themeName = localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light';
  } catch (e) { /* storage unavailable */ }
  themeRoot.setAttribute('data-lg-theme', themeName);

  function themeIcon(name) {
    return name === 'dark'
      ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  }

  function setTheme(name, persist, target) {
    const next = name === 'dark' ? 'dark' : 'light';
    themeName = next;
    const root = target || themeRoot;
    root.setAttribute('data-lg-theme', next);
    if (persist) {
      try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* ignore */ }
    }
    const btn = doc.getElementById('dashThemeToggle');
    if (btn) btn.innerHTML = themeIcon(next);
    if (typeof window.CustomEvent === 'function') {
      try {
        window.dispatchEvent(new CustomEvent('smb:theme', { detail: { theme: next } }));
      } catch (e) { /* ignore */ }
    }
  }

  function initThemeToggle() {
    if (doc.getElementById('dashThemeToggle')) return;
    const host = doc.querySelector('.topbar-actions');
    if (!host) return;
    if (doc.querySelector('.lg-theme')) return;
    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.id = 'dashThemeToggle';
    btn.className = 'theme-toggle';
    btn.setAttribute('aria-label', 'Switch theme');
    btn.setAttribute('data-tip', 'Theme');
    btn.innerHTML = themeIcon(themeName);
    btn.addEventListener('click', function () {
      setTheme(themeName === 'dark' ? 'light' : 'dark', true);
    });
    host.insertBefore(btn, host.firstChild);
  }

  const reduceMedia = window.matchMedia('(prefers-reduced-motion: reduce)');
  const reduced = reduceMedia.matches;
  const doc = document;
  const body = doc.body;

  /* ============================================================
     Scroll-reveal system
     Arming only when motion is allowed guarantees content is
     never unintentionally hidden (JS-fail / reduced-motion safe).
     ============================================================ */
  const AUTO_TARGETS = [
    '.kpi-card', '.chart-card', '.panel', '.card', '.c-ccard', '.mini-stat',
    '.stat-card', '.insight-card', '.alert-card', '.cc-card', '.list-card',
    '.hub-card', '.c-kpi', '.d-kpi', '.c-welcome', '.d-welcome'
  ].join(',');
  const STAGGER = 60;
  const STAGGER_CAP = 6;

  const wsState = { armed: false, io: null };
  const tagged = new WeakSet();

  function arm() {
    if (reduced || wsState.armed) return;
    wsState.armed = true;
    body.classList.add('ws-armed');
    wsState.io = new IntersectionObserver(onEnter, {
      rootMargin: '0px 0px -8% 0px',
      threshold: 0.12
    });
  }

  function onEnter(entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      const el = e.target;
      el.classList.add('ws-in');
      wsState.io.unobserve(el);
      setTimeout(function () { el.style.transitionDelay = ''; }, 1200);
    });
  }

  function staggerIndex(host, el) {
    let i = 0;
    const sibs = host === el ? [] : host.children;
    for (let k = 0; k < sibs.length; k++) {
      if (sibs[k] === el) return Math.min(i, STAGGER_CAP - 1);
      if (tagged.has(sibs[k])) i++;
    }
    return 0;
  }

  function insideTaggedReveal(el) {
    if (el.hasAttribute('data-ws-reveal')) return false;
    return !!el.closest('[data-ws-reveal]');
  }

  function revealEl(el, idx) {
    if (!el || tagged.has(el)) return;
    if (el.closest('.ws-in')) return;
    if (insideTaggedReveal(el)) return;
    tagged.add(el);
    el.style.transitionDelay = Math.min(idx, STAGGER_CAP - 1) * STAGGER + 'ms';
    wsState.io.observe(el);
  }

  function scan(root) {
    const host = root && root.nodeType === 1 ? root : doc;
    if (!wsState.io) arm();
    if (!wsState.armed) return;

    host.querySelectorAll(AUTO_TARGETS).forEach(function (el) {
      if (tagged.has(el)) return;
      const grp = el.parentElement || el;
      revealEl(el, staggerIndex(grp, el));
    });

    host.querySelectorAll('[data-ws-reveal]').forEach(function (el, i) {
      if (tagged.has(el)) return;
      revealEl(el, i % STAGGER_CAP);
    });
  }

  /* Watch dynamically injected content (customers, complaints, dustbins…). */
  function watchMutations() {
    if (!window.MutationObserver || reduced) return;
    let pending = null;
    new MutationObserver(function () {
      if (pending) return;
      pending = requestAnimationFrame(function () {
        pending = null;
        scan(doc);
      });
    }).observe(doc.body, { childList: true, subtree: true });
  }

  /* ============================================================
     Page transitions on pages without animations.js
     ============================================================ */
  function initPageTransitions() {
    if (reduced || body.dataset.wsTrans === '1') return;
    body.dataset.wsTrans = '1';
    body.classList.add('page-entering');
    doc.addEventListener('click', function (e) {
      const a = e.target.closest && e.target.closest('a[href]');
      if (!a) return;
      const href = a.getAttribute('href');
      if (!href || href.charAt(0) === '#' || /^(https?:|javascript:|mailto:)/.test(href)) return;
      if (a.target && a.target !== '_self') return;
      if (!/\.html?($|\?)/.test(href) && href.slice(-1) !== '/') return;
      e.preventDefault();
      body.classList.add('page-leaving');
      setTimeout(function () { window.location.href = a.href; }, 230);
    });
  }

  /* ============================================================
     Chart.js polish (visual consistency across all charts)
     ============================================================ */
  function polishCharts() {
    if (typeof window.Chart === 'undefined') return;
    const D = window.Chart.defaults;
    D.animation = Object.assign({}, D.animation, {
      duration: 900,
      easing: 'easeOutQuart'
    });
    D.color = '#64748b';
    D.borderColor = 'rgba(148, 163, 184, .14)';
    D.font = Object.assign({}, D.font, {
      family: "'Inter', system-ui, sans-serif",
      size: 12
    });
    if (D.plugins && D.plugins.tooltip) {
      Object.assign(D.plugins.tooltip, {
        backgroundColor: '#0f172a',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        padding: 12,
        cornerRadius: 10,
        boxPadding: 6,
        usePointStyle: true
      });
    }
    if (D.plugins && D.plugins.legend && D.plugins.legend.labels) {
      Object.assign(D.plugins.legend.labels, {
        usePointStyle: true,
        pointStyleWidth: 10,
        padding: 16
      });
    }
  }

  /* ============================================================
     Micro helpers
     ============================================================ */
  function btnLoading(btn, on, label) {
    if (!btn) return;
    if (on) {
      if (!btn.dataset.wsOri) btn.dataset.wsOri = btn.innerHTML;
      btn.classList.add('is-loading');
      btn.innerHTML = '<span class="btn-spin"></span>' + (label === undefined ? '' : label);
      btn.disabled = true;
    } else {
      btn.classList.remove('is-loading');
      if (btn.dataset.wsOri) { btn.innerHTML = btn.dataset.wsOri; delete btn.dataset.wsOri; }
      btn.disabled = false;
    }
  }

  /* ============================================================
     Mobile navigation (municipality sidebar) — off-canvas toggle
     ============================================================ */
  function initMobileNav() {
    const sb = doc.querySelector('.sidebar');
    if (!sb || doc.getElementById('wsNavBtn')) return;
    const btn = doc.createElement('button');
    btn.className = 'ws-nav-btn';
    btn.id = 'wsNavBtn';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Toggle navigation');
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('data-tip', 'Menu');
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>';
    const host = doc.querySelector('.topbar-left');
    if (host && host.parentNode) host.parentNode.insertBefore(btn, host);
    const overlay = doc.createElement('div');
    overlay.className = 'ws-nav-overlay';
    overlay.id = 'wsNavOverlay';
    overlay.addEventListener('click', closeNav);
    doc.body.appendChild(overlay);
    function closeNav() {
      sb.classList.remove('open');
      doc.body.classList.remove('ws-nav-open');
      btn.setAttribute('aria-expanded', 'false');
    }
    btn.addEventListener('click', function () {
      const open = sb.classList.toggle('open');
      doc.body.classList.toggle('ws-nav-open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    doc.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeNav();
    });
  }

  /* ============================================================
     Init
     ============================================================ */
  function init() {
    arm();
    scan(doc);
    watchMutations();
    initPageTransitions();
    polishCharts();
    initMobileNav();
    initThemeToggle();
  }

  if (doc.readyState === 'loading') {
    doc.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  if (window.SmartCity) {
    window.SmartCity.wsScan = scan;
    window.SmartCity.btnLoading = btnLoading;
    window.SmartCity.setTheme = setTheme;
  }
})();