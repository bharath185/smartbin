/**
 * SmartBin IoT Alerts & Real-Time WebSocket Engine
 * Listens for:
 *   - FIRE_ALERT (Pops up flashing emergency window with GPS, audio siren, map link)
 *   - BIN_FULL_ALERT (Shows high-priority notification toast & updates gauges)
 *   - TELEMETRY_UPDATE (Live updates map markers and counters)
 */
(function () {
    let ws = null;
    let reconnectTimer = null;
    let audioContext = null;
    let sirenOsc = null;
    let sirenGain = null;
    let sirenInterval = null;

    // Determine correct WebSocket URL
    function getWsUrl() {
        const isHttps = window.location.protocol === 'https:';
        const wsProto = isHttps ? 'wss:' : 'ws:';
        const host = window.location.hostname || '127.0.0.1';
        
        // If frontend is on localhost:3000, backend is on localhost:8000
        if (host === 'localhost' || host === '127.0.0.1') {
            return `${wsProto}//${host}:8000/iot/ws`;
        }
        // If deployed to production / cloud
        return `${wsProto}//${window.location.host}/iot/ws`;
    }

    // Play synthesized emergency siren using Web Audio API (Zero external assets needed)
    function playSiren() {
        try {
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioContext.state === 'suspended') {
                audioContext.resume();
            }
            stopSiren(); // reset if already playing

            sirenGain = audioContext.createGain();
            sirenGain.gain.setValueAtTime(0.15, audioContext.currentTime);
            sirenGain.connect(audioContext.destination);

            sirenOsc = audioContext.createOscillator();
            sirenOsc.type = 'sawtooth';
            sirenOsc.frequency.setValueAtTime(650, audioContext.currentTime);
            sirenOsc.connect(sirenGain);
            sirenOsc.start();

            let high = false;
            sirenInterval = setInterval(() => {
                if (!sirenOsc || !audioContext) return;
                const freq = high ? 650 : 950;
                sirenOsc.frequency.setTargetAtTime(freq, audioContext.currentTime, 0.1);
                high = !high;
            }, 300);
        } catch (e) {
            console.warn('[IoT Alerts] Web Audio Siren unavailable:', e);
        }
    }

    function stopSiren() {
        if (sirenInterval) {
            clearInterval(sirenInterval);
            sirenInterval = null;
        }
        if (sirenOsc) {
            try { sirenOsc.stop(); sirenOsc.disconnect(); } catch (e) {}
            sirenOsc = null;
        }
        if (sirenGain) {
            try { sirenGain.disconnect(); } catch (e) {}
            sirenGain = null;
        }
    }

    // Inject CSS for Emergency Fire Modal & Alerts
    function injectStyles() {
        if (document.getElementById('iot-alert-styles')) return;
        const style = document.createElement('style');
        style.id = 'iot-alert-styles';
        style.textContent = `
            @keyframes pulseRedRing {
                0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.8), 0 10px 40px rgba(0,0,0,0.6); }
                70% { box-shadow: 0 0 0 25px rgba(239, 68, 68, 0), 0 10px 40px rgba(0,0,0,0.6); }
                100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0), 0 10px 40px rgba(0,0,0,0.6); }
            }
            @keyframes flashSiren {
                0%, 100% { background-color: #ef4444; color: #fff; }
                50% { background-color: #fee2e2; color: #b91c1c; }
            }
            .fire-modal-overlay {
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(15, 23, 42, 0.85);
                backdrop-filter: blur(8px);
                z-index: 999999;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 16px;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.25s ease;
            }
            .fire-modal-overlay.active {
                opacity: 1;
                pointer-events: auto;
            }
            .fire-modal {
                background: #111827;
                border: 3px solid #ef4444;
                border-radius: 16px;
                width: 100%;
                max-width: 540px;
                color: #f3f4f6;
                box-shadow: 0 20px 50px rgba(239, 68, 68, 0.3);
                animation: pulseRedRing 2s infinite;
                overflow: hidden;
            }
            .fire-modal-header {
                background: linear-gradient(135deg, #dc2626, #991b1b);
                padding: 18px 24px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .fire-modal-title {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 20px;
                font-weight: 800;
                letter-spacing: 0.5px;
                color: #fff;
                margin: 0;
            }
            .fire-badge-siren {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 13px;
                animation: flashSiren 0.8s infinite;
                font-weight: 900;
            }
            .fire-modal-body {
                padding: 24px;
            }
            .fire-info-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin: 16px 0;
            }
            .fire-info-card {
                background: #1f2937;
                border: 1px solid #374151;
                padding: 12px 14px;
                border-radius: 10px;
            }
            .fire-info-card label {
                display: block;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #9ca3af;
                margin-bottom: 4px;
            }
            .fire-info-card value {
                display: block;
                font-size: 16px;
                font-weight: 700;
                color: #f9fafb;
            }
            .fire-coords-box {
                background: rgba(239, 68, 68, 0.1);
                border: 1px dashed #ef4444;
                padding: 14px;
                border-radius: 10px;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .fire-coords-text {
                font-family: monospace;
                font-size: 15px;
                font-weight: 700;
                color: #f87171;
            }
            .fire-modal-actions {
                display: flex;
                gap: 10px;
                justify-content: flex-end;
            }
            .btn-fire-map {
                background: #ef4444;
                color: #fff;
                border: none;
                padding: 10px 18px;
                border-radius: 8px;
                font-weight: 700;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                transition: background 0.2s;
            }
            .btn-fire-map:hover {
                background: #dc2626;
            }
            .btn-fire-dismiss {
                background: #374151;
                color: #e5e7eb;
                border: 1px solid #4b5563;
                padding: 10px 16px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
            }
            .btn-fire-dismiss:hover {
                background: #4b5563;
            }
            /* Floating IoT Sim Bar */
            .iot-sim-pill {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 99999;
                display: flex;
                gap: 8px;
                background: rgba(17, 24, 39, 0.92);
                border: 1px solid #374151;
                padding: 8px 12px;
                border-radius: 30px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.5);
                backdrop-filter: blur(6px);
            }
            .iot-sim-btn {
                background: transparent;
                border: 1px solid #4b5563;
                color: #e5e7eb;
                font-size: 11px;
                font-weight: 700;
                padding: 6px 12px;
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .iot-sim-btn.fire {
                border-color: #ef4444;
                color: #f87171;
            }
            .iot-sim-btn.fire:hover {
                background: #ef4444;
                color: #fff;
            }
            .iot-sim-btn.bin {
                border-color: #f59e0b;
                color: #fbbf24;
            }
            .iot-sim-btn.bin:hover {
                background: #f59e0b;
                color: #000;
            }
        `;
        document.head.appendChild(style);
    }

    // Build or get the Fire Emergency Modal in DOM
    function getFireModal() {
        let overlay = document.getElementById('iotFireModalOverlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'iotFireModalOverlay';
            overlay.className = 'fire-modal-overlay';
            overlay.innerHTML = `
                <div class="fire-modal" role="dialog" aria-modal="true">
                    <div class="fire-modal-header">
                        <h2 class="fire-modal-title">
                            <span>🔥</span>
                            <span>CRITICAL FIRE ALERT</span>
                        </h2>
                        <span class="fire-badge-siren">SIREN ACTIVE</span>
                    </div>
                    <div class="fire-modal-body">
                        <div style="font-size: 14px; color: #fca5a5; margin-bottom: 12px; font-weight: 600;">
                            Thermal / flame sensors have triggered an emergency alarm in your managed area!
                        </div>
                        <div class="fire-info-grid">
                            <div class="fire-info-card">
                                <label>Target Dustbin</label>
                                <value id="fireDustbinId">DB002</value>
                            </div>
                            <div class="fire-info-card">
                                <label>Location</label>
                                <value id="fireLocation">Cafeteria</value>
                            </div>
                            <div class="fire-info-card">
                                <label>Sensor Temp</label>
                                <value id="fireTemp">84.5 °C</value>
                            </div>
                            <div class="fire-info-card">
                                <label>Detected At</label>
                                <value id="fireTime">Just now</value>
                            </div>
                        </div>
                        <div class="fire-coords-box">
                            <div>
                                <div style="font-size: 11px; text-transform: uppercase; color: #9ca3af; margin-bottom: 2px;">GPS Coordinates</div>
                                <div class="fire-coords-text" id="fireCoords">12.972000, 77.595000</div>
                            </div>
                            <a id="fireGoogleMapsBtn" href="#" target="_blank" class="btn-fire-map" style="padding: 6px 12px; font-size: 12px; text-decoration: none;">
                                📍 Open Maps
                            </a>
                        </div>
                        <div class="fire-modal-actions">
                            <button type="button" class="btn-fire-dismiss" id="fireDismissBtn">Acknowledge & Silence</button>
                            <a id="fireNavigateBtn" href="bin-map.html" class="btn-fire-map" style="text-decoration: none;">
                                🗺️ Live Map Tracking
                            </a>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            document.getElementById('fireDismissBtn').addEventListener('click', () => {
                stopSiren();
                overlay.classList.remove('active');
            });
        }
        return overlay;
    }

    // Trigger the Emergency Fire Popup Window
    function showFireAlert(data) {
        injectStyles();
        const modal = getFireModal();

        const dustbinId = data.dustbin_id || 'UNKNOWN';
        const location = data.location || 'Municipal Sensor Zone';
        const lat = parseFloat(data.latitude || 12.9720).toFixed(6);
        const lng = parseFloat(data.longitude || 77.5950).toFixed(6);
        const temp = data.temperature ? `${data.temperature} °C` : 'Flame Detected';
        const time = new Date().toLocaleTimeString();

        document.getElementById('fireDustbinId').textContent = dustbinId;
        document.getElementById('fireLocation').textContent = location;
        document.getElementById('fireTemp').textContent = temp;
        document.getElementById('fireTime').textContent = time;
        document.getElementById('fireCoords').textContent = `${lat}, ${lng}`;

        const gmapsUrl = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
        document.getElementById('fireGoogleMapsBtn').href = gmapsUrl;
        
        const navBtn = document.getElementById('fireNavigateBtn');
        if (window.location.pathname.includes('map')) {
            navBtn.textContent = '📍 Focus on Map';
            navBtn.href = '#';
            navBtn.onclick = (e) => {
                e.preventDefault();
                stopSiren();
                modal.classList.remove('active');
                if (window.focusMapCoordinates) {
                    window.focusMapCoordinates(parseFloat(lat), parseFloat(lng), dustbinId);
                }
            };
        } else {
            navBtn.href = `bin-map.html?focus=${dustbinId}&lat=${lat}&lng=${lng}`;
        }

        modal.classList.add('active');
        playSiren();

        // Plot directly on Leaflet Map if present on page
        try {
            const mapObj = window.map || (window.L && document.querySelector('.leaflet-container')?._leaflet_map);
            if (mapObj && window.L) {
                const fireMarker = window.L.marker([lat, lng], {
                    icon: window.L.divIcon({
                        className: 'fire-leaflet-marker',
                        html: '<div style="font-size:36px; filter: drop-shadow(0 0 12px #ef4444); cursor:pointer;">🔥</div>',
                        iconSize: [42, 42],
                        iconAnchor: [21, 21]
                    }),
                    zIndexOffset: 10000
                }).addTo(mapObj);

                window.L.circle([lat, lng], {
                    radius: 70,
                    color: '#ef4444',
                    fillColor: '#ef4444',
                    fillOpacity: 0.38,
                    weight: 3
                }).addTo(mapObj);

                fireMarker.bindPopup(`
                    <div style="font-family:system-ui,sans-serif;color:#0f172a;min-width:180px;">
                        <div style="display:flex;align-items:center;gap:6px;font-weight:800;color:#dc2626;font-size:13px;margin-bottom:4px;">
                            <span>🚨</span><span>FIRE EMERGENCY</span>
                        </div>
                        <div style="font-size:12px;font-weight:700;">Dustbin: ${dustbinId}</div>
                        <div style="font-size:11px;color:#475569;">${location}</div>
                        <div style="margin-top:6px;font-family:monospace;font-size:11px;color:#dc2626;font-weight:700;">${lat}, ${lng}</div>
                    </div>
                `).openPopup();

                mapObj.flyTo([lat, lng], 16, { duration: 1.2 });
            }
        } catch (mapErr) {
            console.warn('[IoT Alerts] Map marker auto-plot note:', mapErr);
        }

        // Also trigger desktop browser notification if permitted
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('🚨 FIRE ALERT: ' + dustbinId, {
                body: `Fire detected at ${location} (${lat}, ${lng})!`,
                icon: 'assets/css/fire-icon.png'
            });
        }
    }

    // Trigger Dustbin Full Toast Alert
    function showBinFullAlert(data) {
        injectStyles();
        const bid = data.dustbin_id || 'DB001';
        const loc = data.location || 'Location';
        const fill = data.fill_level || 95;

        if (window.showToast) {
            window.showToast(`🗑️ ${bid} is FULL (${fill}%) at ${loc}`, 'error');
        } else if (window.Auth && window.Auth.toast) {
            window.Auth.toast(`🗑️ ${bid} is FULL (${fill}%) at ${loc}`, 'error');
        } else {
            alert(`🗑️ SmartBin Alert: Dustbin ${bid} at ${loc} reached ${fill}% fill level!`);
        }

        // Auto update UI elements on dashboard if present
        const badge = document.querySelector(`[data-bin-id="${bid}"]`);
        if (badge) {
            badge.textContent = 'FULL';
            badge.className = 'badge badge-filled';
        }

        if (typeof window.loadDashboard === 'function') {
            window.loadDashboard();
        }
    }

    // Connect WebSocket
    function connect() {
        const url = getWsUrl();
        const statusEl = document.getElementById('iotWsStatusText');
        try {
            ws = new WebSocket(url);
            ws.onopen = function () {
                console.log('[IoT Alerts] WebSocket connected to:', url);
                if (statusEl) statusEl.innerHTML = '<span style="color:#4ade80">● Live IoT Connected</span>';
                if (reconnectTimer) clearTimeout(reconnectTimer);
            };
            ws.onmessage = function (event) {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[IoT Alerts] Event received:', data);

                    if (data.type === 'FIRE_ALERT' || data.fire_detected) {
                        showFireAlert(data);
                    } else if (data.type === 'BIN_FULL_ALERT') {
                        showBinFullAlert(data);
                    } else if (data.type === 'TELEMETRY_UPDATE') {
                        if (typeof window.loadDashboard === 'function') {
                            window.loadDashboard();
                        }
                    }
                } catch (err) {
                    console.error('[IoT Alerts] Parse error:', err);
                }
            };
            ws.onclose = function () {
                if (statusEl) statusEl.innerHTML = '<span style="color:#fbbf24">● Offline / Demo Sim</span>';
                reconnectTimer = setTimeout(connect, 5000);
            };
            ws.onerror = function () {
                ws.close();
            };
        } catch (e) {
            if (statusEl) statusEl.innerHTML = '<span style="color:#fbbf24">● Demo Mode Sim</span>';
            console.warn('[IoT Alerts] WebSocket initialization notice:', e);
        }
    }

    // Floating Simulation Pill (Allows testing directly from the UI anytime)
    function injectSimPill() {
        if (document.getElementById('iotSimPill')) return;
        const pill = document.createElement('div');
        pill.id = 'iotSimPill';
        pill.className = 'iot-sim-pill';
        pill.innerHTML = `
            <span id="iotWsStatusText" style="font-size:11px;font-weight:700;display:flex;align-items:center;padding:0 6px;"><span style="color:#4ade80">● IoT Live</span></span>
            <button class="iot-sim-btn fire" id="testFireBtn" type="button">🔥 Test Fire Alert</button>
            <button class="iot-sim-btn bin" id="testBinBtn" type="button">🗑️ Test Bin Full</button>
        `;
        document.body.appendChild(pill);

        document.getElementById('testFireBtn').addEventListener('click', () => {
            showFireAlert({
                dustbin_id: 'DB002',
                location: 'Cafeteria Main Hall',
                latitude: 12.9720,
                longitude: 77.5950,
                temperature: 87.2,
                smoke_ppm: 340
            });
        });

        document.getElementById('testBinBtn').addEventListener('click', () => {
            showBinFullAlert({
                dustbin_id: 'DB001',
                location: 'Main Lobby Entrance',
                fill_level: 96
            });
        });
    }

    // Public API
    window.IoTAlerts = {
        showFireAlert,
        showBinFullAlert,
        stopSiren,
        simulateFire: () => document.getElementById('testFireBtn')?.click(),
        simulateBinFull: () => document.getElementById('testBinBtn')?.click()
    };

    // Auto-init on DOM Ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            injectStyles();
            injectSimPill();
            connect();
        });
    } else {
        injectStyles();
        injectSimPill();
        connect();
    }
})();
