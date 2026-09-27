// API host resolves automatically: localhost connects to port 8000;
// on cloud HTTPS deployments (e.g. Vercel), it safely uses origin or custom API_BASE.
(function () {
    var stored = null;
    try { stored = localStorage.getItem('API_BASE'); } catch (e) {}
    if (stored) {
        window.API_BASE = stored;
        return;
    }
    var isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocal) {
        window.API_BASE = 'http://' + window.location.hostname + ':8000';
    } else {
        window.API_BASE = window.location.origin;
    }
})();
const API_BASE = window.API_BASE;

function escapeHtml(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const MOCK_STORAGE = {
    '/dashboard/summary': {
        total_dustbins: 8,
        filled_count: 2,
        ready_count: 2,
        empty_count: 4,
        total_employees: 5,
        total_points: 430,
        pending_complaints: 1,
        active_drivers: 2
    },
    '/dustbins/': [
        { id: 1, dustbin_id: "DB001", location: "Main Lobby", fill_level: 45, status: "EMPTY", latitude: 12.9716, longitude: 77.5946 },
        { id: 2, dustbin_id: "DB002", location: "Cafeteria", fill_level: 92, status: "FILLED", latitude: 12.9720, longitude: 77.5950 },
        { id: 3, dustbin_id: "DB003", location: "Parking Lot A", fill_level: 15, status: "EMPTY", latitude: 12.9710, longitude: 77.5930 },
        { id: 4, dustbin_id: "DB004", location: "Office Floor 2", fill_level: 88, status: "FILLED", latitude: 12.9730, longitude: 77.5960 },
        { id: 5, dustbin_id: "DB005", location: "Library", fill_level: 5, status: "EMPTY", latitude: 12.9715, longitude: 77.5955 },
        { id: 6, dustbin_id: "DB006", location: "Gym", fill_level: 78, status: "READY", latitude: 12.9725, longitude: 77.5940 },
        { id: 7, dustbin_id: "DB007", location: "Reception", fill_level: 95, status: "READY", latitude: 12.9705, longitude: 77.5945 },
        { id: 8, dustbin_id: "DB008", location: "Workshop", fill_level: 30, status: "EMPTY", latitude: 12.9735, longitude: 77.5935 }
    ],
    '/leaderboard/weekly': [
        { name: "Alice Johnson", points: 150, role: "admin", employee_id: "EMP001" },
        { name: "Bob Kumar", points: 120, role: "employee", employee_id: "EMP002" },
        { name: "Charlie Singh", points: 90, role: "employee", employee_id: "EMP003" },
        { name: "Diana Patel", points: 80, role: "employee", employee_id: "EMP004" },
        { name: "Eve Sharma", points: 60, role: "employee", employee_id: "EMP005" }
    ],
    '/complaints/': [
        { id: 101, dustbin_id: 2, reporter_name: "John Doe", description: "Bin overflowing near cafeteria entrance", status: "OPEN", created_at: new Date().toISOString() }
    ],
    '/collections/': [],
    '/tasks/': []
};

const api = {
    async get(path) {
        try {
            const resp = await fetch(API_BASE + path);
            if (!resp.ok) throw new Error(await resp.text());
            return await resp.json();
        } catch (e) {
            // Check for mock fallback in demo mode
            const baseKey = path.split('?')[0];
            if (MOCK_STORAGE[baseKey] !== undefined) {
                return JSON.parse(JSON.stringify(MOCK_STORAGE[baseKey]));
            }
            throw e;
        }
    },
    async post(path, body) {
        try {
            const resp = await fetch(API_BASE + path, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(err.detail || 'Request failed');
            }
            return await resp.json();
        } catch (e) {
            // Simulated response when offline
            if ((e.message || '').indexOf('fetch') !== -1 || (e.message || '').indexOf('Failed') !== -1) {
                return { success: true, message: 'Simulated in Demo Mode', id: Date.now() };
            }
            throw e;
        }
    },
    async put(path, body) {
        try {
            const resp = await fetch(API_BASE + path, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!resp.ok) throw new Error(await resp.text());
            return await resp.json();
        } catch (e) {
            if ((e.message || '').indexOf('fetch') !== -1 || (e.message || '').indexOf('Failed') !== -1) {
                return { success: true, message: 'Updated in Demo Mode' };
            }
            throw e;
        }
    },
    async del(path) {
        try {
            const resp = await fetch(API_BASE + path, { method: 'DELETE' });
            if (!resp.ok) throw new Error(await resp.text());
            return true;
        } catch (e) {
            if ((e.message || '').indexOf('fetch') !== -1 || (e.message || '').indexOf('Failed') !== -1) {
                return true;
            }
            throw e;
        }
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
