/* ============================================================
   SmartBin AI Assistant — reusable floating chat component
   ------------------------------------------------------------
   Standalone & reusable. Can be dropped onto any page:

       <link rel="stylesheet" href="assets/css/ai-assistant.css">
       <script src="assets/js/ai-assistant.js"></script>
       SmartBinAI.init({ mode: 'customer' | 'driver', ...opts });

   The answer engine lives in a single function (getAnswer) so a
   real AI API can be connected later without touching the UI.
   No auth tokens or sensitive data are ever sent to the engine.
   ============================================================ */
(function () {
  'use strict';

  var ENGINE = { local: 'local-rule-engine' }; // hook point for future AI provider

  /* ------------------------------------------------------------------
     Answer engine (customer).
     Rule-based for now. Swap getAnswer with a real AI API later by
     providing a remote resolver via SmartBinAI.init({ resolver }).
  ------------------------------------------------------------------ */
  var CUSTOMER_RULES = [
    { keys: ['report a complaint', 'report complaint', 'file a complaint', 'how do i report', 'complain'],
      html: '<b>How to report a complaint</b><br>1. Log in to your SmartBin customer account.<br>2. Open the <b>Complaints</b> section.<br>3. Choose the related smart bin / location, add a description, and submit.<br>Our team reviews it and updates the status. You can track it from the same section.' },
    { keys: ['track my complaint', 'track complaint', 'complaint status', 'my complaint', 'complaint update'],
      html: '<b>Tracking your complaint</b><br>Once submitted, your complaint shows a status like <b>Open</b> or <b>Resolved</b>.<br>Open the <b>Complaints</b> tab in your dashboard to see live updates and resolution confirmations.' },
    { keys: ['how does smartbin work', 'how it works', 'how does smartbin', 'what is smartbin', 'about smartbin', 'smartbin work'],
      html: '<b>How SmartBin works</b><br>Smart bins use IoT sensors to monitor their fill level in real time.<br>The system flags bins that are ready or full, plans optimised collector routes, and lets you report issues — all in one dashboard.' },
    { keys: ['request waste collection', 'waste collection', 'report a full bin', 'full bin', 'collect waste', 'pickup'],
      html: '<b>Requesting waste collection</b><br>If a bin near you is full, report it via the <b>Complaints</b> or <b>Smart Bins</b> section.<br>The system notifies your municipality so a driver can be routed to collect it.' },
    { keys: ['bin status mean', 'bin status', 'what does bin status', 'fill level', 'status of bin'],
      html: '<b>Bin status</b><br>A bin can be <b>Empty</b>, <b>Ready</b>, or <b>Full</b> based on its fill level:<br>• Empty — plenty of room<br>• Ready — getting full, collection planned<br>• Full — needs collection soon<br>You can see live status of bins in the <b>Smart Bins</b> section.' },
    { keys: ['help with login', 'login help', 'can\'t login', 'forgot password', 'reset password', 'sign in issue'],
      html: '<b>Login help</b><br>Use the email or mobile number you registered with, plus your password.<br>If you forgot your password, use the <b>Forgot password?</b> link on the sign-in page to reset it.' },
    { keys: ['qrcode', 'qr code', 'scan qr', 'qr'],
      html: '<b>QR codes</b><br>Each smart bin has a unique QR code. You can scan it to view that bin\'s details, check its status, or report an issue for that specific bin.' },
    { keys: ['notification', 'alert', 'notify'],
      html: '<b>Notifications</b><br>SmartBin keeps you informed about collection schedules, bin status changes, and the resolution of your complaints — all shown in your notifications area.' },
    { keys: ['account', 'profile', 'my details', 'update my'],
      html: '<b>Your account</b><br>You can view and update your profile details such as name, mobile, and address from the account settings in your dashboard.' }
  ];

  /* ------------------------------------------------------------------
     Answer engine (driver).
  ------------------------------------------------------------------ */
  var DRIVER_RULES = [
    { keys: ['start my route', 'start route', 'route', 'begin my route', 'start collection'],
      html: '<b>Starting your route</b><br>Open your dashboard and tap <b>Start Route</b> on today\'s collection.<br>Your assigned bins for the day are shown in order. Begin by navigating to the first assigned bin and scanning it.' },
    { keys: ['scan a dustbin', 'scan dustbin', 'scan a bin', 'scan bin', 'scan qr', 'qr scanner'],
      html: '<b>Scanning a dustbin</b><br>Use the <b>Scan</b> feature in your driver app.<br>Point the camera at the bin\'s QR code. Once recognised, the bin is added to your current collection and its status is updated.' },
    { keys: ['record an unload', 'record unload', 'record a collection', 'log unload', 'mark collected'],
      html: '<b>Recording an unload</b><br>After collecting from a scanned bin, confirm the <b>unload</b> and the type of waste.<br>This logs the collection on the dump, resets the bin\'s fill level, and updates your total collections.' },
    { keys: ['enable gps', 'gps', 'location permission', 'turn on gps', 'enable location'],
      html: '<b>Enabling GPS</b><br>SmartBin uses your phone\'s GPS to track live collection routes.<br>Allow <b>Location</b> permission for the app and make sure GPS / location services are turned on.' },
    { keys: ['location not updating', 'location not update', 'gps not working', 'location stuck', 'not updating'],
      html: '<b>Location not updating?</b><br>Check that:<br>• GPS / location services are turned on<br>• Location permission is granted to the app<br>• You\'re in an open area with good signal<br>• The app has a data / internet connection<br>Pull to refresh and your live position should update.' },
    { keys: ['complete a collection', 'complete collection', 'finish route', 'finish collection', 'end route', 'complete route'],
      html: '<b>Completing a collection</b><br>Scan each assigned bin, record the unload, then finish the route when all bins are done.<br>Your route is marked complete and your collections for the day are saved.' },
    { keys: ['driver login', 'login help', 'can\'t login', 'forgot password', 'sign in issue', 'reset password', 'driver account'],
      html: '<b>Driver login help</b><br>Sign in with the mobile number / email and password you registered with.<br>If you forgot your password, use the <b>Forgot password?</b> link.<br>If your account is <b>pending</b>, it must be approved by the municipality before you can log in.' },
    { keys: ['my status', 'driver status', 'account status', 'suspended', 'approved'],
      html: '<b>Driver status</b><br>Your account can be <b>Active</b>, <b>Pending</b>, <b>Suspended</b>, or <b>Rejected</b>.<br>If suspended or pending approval, contact your municipality to resolve it before you can log in.' },
    { keys: ['assigned bins', 'assigned area', 'my bins', 'my assignment', 'assigned route', 'area'],
      html: '<b>Assigned bins & area</b><br>Your municipality assigns you a collection area and route.<br>View your assigned bins and route from the driver dashboard before starting your collection.' },
    { keys: ['notification', 'alert', 'notify', 'schedule'],
      html: '<b>Driver notifications</b><br>You\'ll receive alerts about your schedule, new assignments, and any changes to your route — shown in the notifications area of your dashboard.' }
  ];

  var FALLBACK = 'I can help with SmartBin features, complaints, collections, bins, routes and account-related questions.';

  function normalize(q) { return String(q || '').toLowerCase().replace(/\s+/g, ' ').trim(); }

  function ruleMatch(rules, q) {
    var n = normalize(q);
    for (var i = 0; i < rules.length; i++) {
      for (var j = 0; j < rules[i].keys.length; j++) {
        if (n.indexOf(rules[i].keys[j]) > -1) return rules[i].html;
      }
    }
    return null;
  }

  /* Default local resolver. Override via SmartBinAI.init({ resolver: fn }).
     fn(mode, question) => Promise<string html>  (swap with real AI API) */
  function localResolver(mode, question) {
    var rules = mode === 'driver' ? DRIVER_RULES : CUSTOMER_RULES;
    return new Promise(function (resolve) {
      setTimeout(function () {
        resolve(ruleMatch(rules, question) || FALLBACK);
      }, 500 + Math.floor(Math.random() * 450));
    });
  }

  /* ------------------------------------------------------------------
     Component
  ------------------------------------------------------------------ */
  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function SmartBinAIApp(initialConfig) {
    var conf = Object.assign({}, {
      mode: 'customer',
      fontSize: 13,
      launcherLabel: 'SmartBin AI',
      headerTitle: 'SmartBin Assistant',
      resolver: null,
      welcome: null,
      quick: null,
      greetName: null,
    }, initialConfig || {});

    var root, launcher, panel, body, input, sendBtn, open = false, busy = false;

    function getUserName() {
      try {
        var s = (window.Auth && typeof window.Auth.session === 'function') ? window.Auth.session() : null;
        if (s && s.name) return s.name;
      } catch (e) {}
      return conf.greetName || null;
    }

    function customerQuick() { return [
      'How do I report a complaint?',
      'How can I track my complaint?',
      'How does SmartBin work?',
      'How do I request waste collection?',
      'What does bin status mean?',
      'Help with login',
    ]; }
    function driverQuick() { return [
      'How do I start my route?',
      'How do I scan a dustbin?',
      'How do I record an unload?',
      'How do I enable GPS?',
      'Why is my location not updating?',
      'How do I complete a collection?',
      'Help with driver login',
    ]; }
    function getQuick() { return conf.quick || (conf.mode === 'driver' ? driverQuick() : customerQuick()); }

    function getWelcome() {
      if (conf.welcome) return conf.welcome;
      var name = getUserName();
      if (name) {
        return conf.mode === 'driver'
          ? 'Hi ' + name + ' 🚛<br>How can I help you with today\'s collection route?'
          : 'Hi ' + name + ' 👋<br>How can I help you with your SmartBin account?';
      }
      return 'Hi! 👋 I\'m the SmartBin Assistant.<br>How can I help you today?';
    }

    function buildDom() {
      root = document.createElement('div');
      root.className = 'sbi-ai';
      root.style.fontSize = conf.fontSize + 'px';

      launcher = document.createElement('button');
      launcher.className = 'sbi-ai__launcher';
      launcher.type = 'button';
      launcher.setAttribute('aria-label', 'Open ' + conf.headerTitle + ' chat');
      launcher.setAttribute('aria-expanded', 'false');
      launcher.innerHTML =
        '<span class="sbi-ai__halo" aria-hidden="true"></span>' +
        '<span class="sbi-ai__ic" aria-hidden="true">' +
          '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<rect x="4" y="8" width="16" height="12" rx="3"/>' +
            '<path d="M12 4v3M9 3.5h6"/>' +
            '<circle cx="9" cy="14" r="1" fill="currentColor"/><circle cx="15" cy="14" r="1" fill="currentColor"/>' +
            '<path d="M9 18h6"/>' +
          '</svg>' +
        '</span>' +
        '<span class="sbi-ai__tip">' + escapeHtml(conf.launcherLabel) + '</span>';

      panel = document.createElement('div');
      panel.className = 'sbi-ai__panel';
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-label', conf.headerTitle + ' chat');

      panel.innerHTML =
        '<div class="sbi-ai__head">' +
          '<div class="sbi-ai__head-ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="11" rx="2"/><path d="M9 3h6M9 3v5M15 3v5"/><circle cx="8.5" cy="13" r=".5" fill="currentColor"/><circle cx="15.5" cy="13" r=".5" fill="currentColor"/></svg></div>' +
          '<div class="sbi-ai__head-tit"><b>' + escapeHtml(conf.headerTitle) + '</b><span><span class="on-dot"></span> Online</span></div>' +
          '<button class="sbi-ai__head-close" type="button" aria-label="Close chat"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg></button>' +
        '</div>' +
        '<div class="sbi-ai__body" aria-live="polite"></div>' +
        '<div class="sbi-ai__foot">' +
          '<input class="sbi-ai__input" type="text" placeholder="Type your question..." aria-label="Type your question" maxlength="300">' +
          '<button class="sbi-ai__send" type="button" aria-label="Send message"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></button>' +
        '</div>';

      document.body.appendChild(launcher);
      document.body.appendChild(panel);
      body = panel.querySelector('.sbi-ai__body');
      input = panel.querySelector('.sbi-ai__input');
      sendBtn = panel.querySelector('.sbi-ai__send');

      launcher.addEventListener('click', toggle);
      panel.querySelector('.sbi-ai__head-close').addEventListener('click', close);
      sendBtn.addEventListener('click', onSend);
      input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); onSend(); } });
    }

    function addMessage(kind, html) {
      var m = document.createElement('div');
      m.className = 'sbi-ai__msg sbi-ai__msg--' + kind;
      if (kind === 'bot') {
        m.innerHTML = '<div class="sbi-ai__avatar">🤖</div><div class="sbi-ai__bubble">' + html + '</div>';
      } else {
        m.innerHTML = '<div class="sbi-ai__bubble">' + html + '</div>';
      }
      body.appendChild(m);
      body.scrollTop = body.scrollHeight;
      return m;
    }

    function showTyping() {
      var t = document.createElement('div');
      t.className = 'sbi-ai__msg sbi-ai__msg--bot';
      t.innerHTML = '<div class="sbi-ai__avatar">🤖</div><div class="sbi-ai__bubble sbi-ai__typing"><i></i><i></i><i></i></div>';
      body.appendChild(t);
      body.scrollTop = body.scrollHeight;
      return t;
    }

    function resetChat() {
      body.innerHTML = '';
      addMessage('bot', getWelcome());
      appendQuick();
    }

    function appendQuick() {
      var q = document.createElement('div');
      q.className = 'sbi-ai__quick';
      q.innerHTML = getQuick().map(function (t) {
        return '<button type="button" class="sbi-ai__quick-btn" data-q="' + escapeHtml(t) + '">' + escapeHtml(t) + '</button>';
      }).join('');
      q.addEventListener('click', function (e) {
        var b = e.target.closest('.sbi-ai__quick-btn');
        if (b) send(b.getAttribute('data-q'));
      });
      body.appendChild(q);
      body.scrollTop = body.scrollHeight;
    }

    function onSend() {
      var v = input.value.trim();
      if (!v || busy) return;
      input.value = '';
      send(v);
    }

    function send(question) {
      if (busy) return;
      addMessage('user', escapeHtml(question));
      var typing = showTyping();
      busy = true;
      sendBtn.disabled = true;

      var resolver = (typeof conf.resolver === 'function') ? conf.resolver : localResolver;
      Promise.resolve(resolver(conf.mode, question)).then(function (answer) {
        typing.remove();
        addMessage('bot', String(answer));
        busy = false;
        sendBtn.disabled = false;
        input.focus();
      }).catch(function () {
        typing.remove();
        addMessage('bot', FALLBACK);
        busy = false;
        sendBtn.disabled = false;
        input.focus();
      });
    }

    function openChat() {
      if (!panel.classList.contains('sbi-ai--open')) {
        if (body.querySelectorAll('.sbi-ai__msg').length === 0) resetChat();
      }
      panel.classList.add('sbi-ai--open');
      launcher.setAttribute('aria-expanded', 'true');
      open = true;
      setTimeout(function () { if (input) input.focus(); }, 240);
    }
    function closeChat() {
      panel.classList.remove('sbi-ai--open');
      launcher.setAttribute('aria-expanded', 'false');
      open = false;
    }
    function toggle() { if (open) { closeChat(); } else { openChat(); } }

    function setMode(mode) {
      conf.mode = mode;
      resetChat();
    }
    function setGreeting(name) { conf.greetName = name; resetChat(); }
    function configure(o) { Object.assign(conf, o || {}); resetChat(); }

    buildDom();
    resetChat();

    return {
      open: openChat,
      close: closeChat,
      toggle: toggle,
      setMode: setMode,
      setGreeting: setGreeting,
      configure: configure,
      getElement: function () { return root; },
    };
  }

  var instance = null;
  var initCfg = null;

  window.SmartBinAI = {
    ENGINE: ENGINE,
    init: function (cfg) {
      initCfg = cfg || {};
      if (!instance) instance = SmartBinAIApp(initCfg);
      else instance.configure(initCfg);
      return instance;
    },
    get: function () { return instance; },
    setMode: function (m) { if (instance) instance.setMode(m); },
    setGreeting: function (n) { if (instance) instance.setGreeting(n); },
    rulesFor: function (m) { return m === 'driver' ? DRIVER_RULES : CUSTOMER_RULES; },
    fallback: function () { return FALLBACK; },
  };

  /* Auto-init on pages that opt in via <body data-ai="customer|driver">.
     Only initializes for a logged-in user so the assistant never appears
     on pre-auth surfaces (e.g. a redirect through the login page). */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { autoInit(); });
  } else {
    autoInit();
  }
  function hasSession() {
    try {
      var s = (window.Auth && typeof window.Auth.session === 'function') ? window.Auth.session() : null;
      return !!(s && s.token);
    } catch (e) { return false; }
  }
  function autoInit() {
    var role = document.body.getAttribute('data-ai');
    if ((role === 'customer' || role === 'driver') && hasSession()) {
      window.SmartBinAI.init({ mode: role });
    }
  }
})();
