/* ============================================================
   SmartBin Auth — session management + role-based guards
   ============================================================ */
(function () {
    const KEY = 'smb:session';
    const REMEMBER_KEY = 'smb:remember';
    const PANEL_URLS = { customer: 'customer.html', driver: 'driver.html', municipality: 'index.html' };

    function remember() {
        try { return localStorage.getItem(REMEMBER_KEY) === '1'; }
        catch (e) { return false; }
    }

    function read() {
        // persistent session (remember me) takes precedence over tab session
        try {
            const raw = localStorage.getItem(KEY);
            if (raw) return JSON.parse(raw);
        } catch (e) { /* ignore */ }
        try {
            const raw = sessionStorage.getItem(KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (e) { return null; }
    }

    function save(session, persist) {
        // if persist is provided use it; otherwise fall back to remembered preference
        const useLocal = typeof persist === 'boolean' ? persist : remember();
        try {
            if (useLocal) {
                localStorage.setItem(KEY, JSON.stringify(session));
                sessionStorage.removeItem(KEY);
            } else {
                sessionStorage.setItem(KEY, JSON.stringify(session));
                localStorage.removeItem(KEY);
            }
        } catch (e) { /* storage unavailable */ }
    }

    function clear() {
        try { localStorage.removeItem(KEY); sessionStorage.removeItem(KEY); } catch (e) {}
    }

    // fetch with a hard timeout so a stalled backend never leaves the UI stuck
    const FETCH_TIMEOUT = 15000;
    async function fetchJson(path, options) {
        options = options || {};
        const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
        const timer = controller ? setTimeout(function () { controller.abort(); }, FETCH_TIMEOUT) : null;
        let resp;
        try {
            resp = await fetch(API_BASE + path, Object.assign({}, options, {
                signal: controller ? controller.signal : undefined,
            }));
        } catch (e) {
            if (controller && controller.signal.aborted) throw new Error('Request timed out. Please check your connection and try again.');
            throw e;
        } finally {
            if (timer) clearTimeout(timer);
        }
        const data = await resp.json().catch(function () { return {}; });
        if (!resp.ok) throw new Error(data.detail || 'Request failed');
        return data;
    }

    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function toast(message, type) {
        let c = document.querySelector('.toast-container');
        if (!c) { c = document.createElement('div'); c.className = 'toast-container'; document.body.appendChild(c); }
        const t = document.createElement('div');
        t.className = 'toast toast-' + (type || 'success');
        t.textContent = message;
        c.appendChild(t);
        setTimeout(() => t.remove(), 3800);
    }

    function loader(show, label) {
        let el = document.getElementById('authLoader');
        if (show) {
            if (!el) {
                el = document.createElement('div');
                el.id = 'authLoader';
                el.className = 'auth-loader';
                el.innerHTML = '<div class="auth-loader-spin"></div><div id="authLoaderMsg">Please wait...</div>';
                document.body.appendChild(el);
            }
            el.style.display = 'flex';
            const msg = el.querySelector('#authLoaderMsg');
            if (msg) msg.textContent = label || 'Loading...';
        } else if (el) {
            el.style.display = 'none';
        }
    }

    async function login(identifier, password, persist) {
        try {
            const data = await fetchJson('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ identifier, password }),
            });
            const session = {
                token: data.access_token,
                role: data.role,
                name: data.name,
                email: data.email,
                status: data.status,
                panel: data.panel || data.role,
            };
            save(session, persist);
            return session;
        } catch (err) {
            const isNetErr = !err.status && (
                (err.message || '').indexOf('fetch') !== -1 ||
                (err.message || '').indexOf('Failed') !== -1 ||
                (err.message || '').indexOf('NetworkError') !== -1 ||
                (err.message || '').indexOf('timed out') !== -1
            );
            if (isNetErr) {
                const idNorm = (identifier || '').trim().toLowerCase();
                const demoUsers = {
                    'alice@smartbin.com': { role: 'municipality', name: 'Alice Johnson (Admin)', panel: 'municipality', pw: 'password123' },
                    'admin@smartbin.com': { role: 'municipality', name: 'Admin', panel: 'municipality', pw: 'password123' },
                    'driver@demo.com': { role: 'driver', name: 'Demo Driver', panel: 'driver', pw: 'demo1234' },
                    'customer@demo.com': { role: 'customer', name: 'Demo Customer', panel: 'customer', pw: 'demo1234' },
                };
                const demo = demoUsers[idNorm];
                if (demo && demo.pw === password) {
                    const session = {
                        token: 'demo-token-' + Date.now(),
                        role: demo.role,
                        name: demo.name,
                        email: idNorm,
                        status: 'active',
                        panel: demo.panel,
                        isDemo: true,
                    };
                    save(session, persist);
                    toast('Backend offline — signed in via Demo Mode', 'info');
                    return session;
                }
                throw new Error('Backend server is offline (' + (window.API_BASE || 'port 8000') + '). For cloud preview, please use the Demo Login credentials.');
            }
            throw err;
        }
    }

    function setRemember(on) {
        try {
            if (on) localStorage.setItem(REMEMBER_KEY, '1');
            else localStorage.removeItem(REMEMBER_KEY);
        } catch (e) {}
    }

    async function register(payload) {
        return fetchJson('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
    }

    async function forgot(email, newPassword, confirmPassword) {
        return fetchJson('/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, new_password: newPassword, confirm_password: confirmPassword }),
        });
    }

    async function me(token) {
        return fetchJson('/auth/me', {
            method: 'GET',
            headers: { 'Authorization': 'Bearer ' + token },
        });
    }

    function logout() {
        clear();
        window.location.href = 'login.html';
    }

    function session() {
        return read();
    }

    function redirectFor(panel) {
        return PANEL_URLS[panel] || 'login.html';
    }

    /* role guard — call on pages. data-role on <body> auto-enforces. */
    function guard(roles) {
        const s = read();
        const allowed = Array.isArray(roles) ? roles : [roles];
        if (!s || !s.token || allowed.indexOf(s.role) === -1) {
            window.location.href = 'login.html';
            return null;
        }
        // block access while an account is not in an active state
        if (s.role === 'driver' && s.status !== 'active' && s.status !== 'verified') {
            const msg = s.status === 'pending'
                ? 'Your account is pending municipality approval.'
                : s.status === 'suspended'
                    ? 'Your driver account has been suspended. Please contact the municipality.'
                    : 'Your driver registration request was rejected. Please contact the municipality.';
            try { toast(msg, 'error'); } catch (e) {}
            clear();
            setTimeout(function () { window.location.href = 'login.html'; }, 700);
            return null;
        }
        if (s.role === 'municipality' && s.status === 'pending' && (!s.panel || s.panel === 'municipality')) {
            // municipality real-account (non-employee) pending -> block
        }
        return s;
    }

    /* rebuild municipality sidebar? panels own their markup; this stays generic. */
    function applyTopbar(containerId, opts) {
        const s = read();
        if (!s) return null;
        const host = document.getElementById(containerId);
        if (!host) return s;
        const roleLabel = { customer: 'Customer', driver: 'Driver', municipality: 'Municipality' }[s.role] || s.role;
        opts = opts || {};
        host.innerHTML =
            '<div class="auth-topbar">' +
            '<div class="auth-topbar-brand"><span class="auth-brand-dot"></span><strong>' + (opts.brand || 'SmartBin') + '</strong></div>' +
            '<div class="auth-topbar-user">' +
            '<div class="auth-topbar-avatar">' + escapeHtml((s.name || 'U').charAt(0).toUpperCase()) + '</div>' +
            '<div class="auth-topbar-meta"><strong>' + escapeHtml(s.name || 'User') + '</strong><span>' + roleLabel + '</span></div>' +
            '<button class="auth-logout-btn" id="authLogoutBtn" title="Logout">\u23FB Logout</button>' +
            '</div></div>';
        const btn = document.getElementById('authLogoutBtn');
        if (btn) btn.addEventListener('click', function () { logout(); });
        return s;
    }

    /* auto-guard: body[data-role] */
    function init() {
        const body = document.body;
        const role = body && body.getAttribute('data-role');
        if (role) guard(role);
    }

    if (typeof window.SmartCity === 'undefined') window.SmartCity = {};
    window.Auth = {
        login, register, forgot, me, logout, session, guard, redirectFor,
        applyTopbar, toast, loader, escapeHtml, setRemember, remember, save,
    };
    window.SmartCity.Auth = window.Auth;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

/* ---------- shared page-top loader ---------- */
document.addEventListener('DOMContentLoaded', function () {
    const tray = document.getElementById('panelTopbar');
    if (tray) {
        const s = (window.Auth && window.Auth.session()) || null;
        if (s) window.Auth.applyTopbar('panelTopbar');
        else tray.innerHTML = '';
    }
});