// API host resolves automatically: same machine uses localhost, remote devices
// (phone/tablet) use the LAN address the page was loaded from.
(function () {
    var stored = null;
    try { stored = localStorage.getItem('API_BASE'); } catch (e) {}
    var auto = 'http://' + (window.location.hostname || '127.0.0.1') + ':8000';
    window.API_BASE = stored && stored.indexOf('127.0.0.1') === -1 ? stored : auto;
})();
const API_BASE = window.API_BASE;

function escapeHtml(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const api = {
    async get(path) {
        const resp = await fetch(API_BASE + path);
        if (!resp.ok) throw new Error(await resp.text());
        return resp.json();
    },
    async post(path, body) {
        const resp = await fetch(API_BASE + path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(err.detail || 'Request failed');
        }
        return resp.json();
    },
    async put(path, body) {
        const resp = await fetch(API_BASE + path, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error(await resp.text());
        return resp.json();
    },
    async del(path) {
        const resp = await fetch(API_BASE + path, { method: 'DELETE' });
        if (!resp.ok) throw new Error(await resp.text());
        return true;
    },
};

function showToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

function statusBadge(status) {
    const cls = status === 'FILLED' ? 'badge-filled' : status === 'READY' ? 'badge-ready' : 'badge-empty';
    const pulse = status === 'FILLED' ? 'pulse-red' : status === 'READY' ? 'pulse-yellow' : 'pulse-green';
    return '<span class="badge ' + cls + ' status-badge"><span class="status-dot ' + pulse + '"></span>' + status + '</span>';
}

function fillBar(level) {
    const cls = level >= 80 ? 'high' : level >= 40 ? 'medium' : 'low';
    return '<div class=\"fill-bar-bg\"><div class=\"fill-bar ' + cls + '\" style=\"width:' + level + '%\"></div></div>';
}

function rankBadge(rank) {
    const cls = rank === 1 ? 'rank-1' : rank === 2 ? 'rank-2' : rank === 3 ? 'rank-3' : 'rank-default';
    return '<span class="rank-badge ' + cls + '">' + rank + '</span>';
}
