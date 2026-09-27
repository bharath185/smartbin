/* ============================================================
   SmartBin Auth page helpers (login / register / forgot)
   ============================================================ */
(function () {
  function setMessage(el, text, type) {
    if (!el) return;
    el.textContent = text || '';
    el.className = 'form-msg ' + (type === 'error' ? 'err' : type === 'success' ? 'ok' : 'err');
  }

  /* inline per-field validation helpers for the light login.css UI */
  function setFieldError(input, message) {
    const field = input.closest('.lg-field');
    if (!field) return;
    const err = field.querySelector('.lg-err');
    if (err) err.textContent = message || '';
    field.classList.toggle('has-err', !!message);
    const control = field.querySelector('.lg-control');
    if (control) control.classList.toggle('invalid', !!message);
    if (!message) {
      const next = input.closest('.lg-field').querySelector('.lg-control');
      if (next) next.classList.remove('invalid');
    }
  }
  function clearAllFieldErrors(scope) {
    var root = (scope || document);
    root.querySelectorAll('.lg-field.has-err').forEach(function (f) {
      f.classList.remove('has-err');
      var c = f.querySelector('.lg-control'); if (c) c.classList.remove('invalid');
    });
  }
  function fieldValue(id) {
    var el = document.getElementById(id);
    return el ? el.value.trim() : '';
  }
  /* card transition when swapping views (fade up + slide) */
  function swapView(card) {
    if (!card) return;
    card.style.transition = 'opacity .28s ease, transform .28s var(--lg-ease, cubic-bezier(.22,.8,.24,1))';
    card.style.opacity = '0';
    card.style.transform = 'translateY(14px)';
    setTimeout(function () {
      card.style.opacity = '1';
      card.style.transform = 'none';
    }, 30);
  }
  /* clear a field's error state when the user types/selects */
  function liveClear(errors) {
    (errors || []).forEach(function (input) {
      if (!input) return;
      var handler = function () { setFieldError(input, ''); };
      input.addEventListener('input', handler);
      input.addEventListener('change', handler);
    });
  }

  function togglePass(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
    btn.innerHTML = input.type === 'password'
      ? '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>'
      : '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19M14.12 14.12a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
  }

  function passwordStrength(pw) {
    let score = 0;
    if (pw.length >= 8) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    if (pw.length >= 11) score++;
    return score;
  }

  function bindRolePicker(containerId, onChange) {
    const host = document.getElementById(containerId);
    if (!host) return function () { return 'customer'; };
    function sync() {
      host.querySelectorAll('input[name="authRole"]').forEach(function (inp) {
        const lbl = inp.closest('label');
        if (lbl) lbl.classList.toggle('checked', inp.checked);
      });
      const checked = host.querySelector('input[name="authRole"]:checked');
      if (onChange) onChange(checked ? checked.value : 'customer');
    }
    host.addEventListener('change', sync);
    host.querySelectorAll('label').forEach(function (l) {
      l.addEventListener('click', function () {
        const inp = l.querySelector('input');
        if (inp) { inp.checked = true; sync(); }
      });
    });
    sync();
    return function () {
      const checked = host.querySelector('input[name="authRole"]:checked');
      return checked ? checked.value : 'customer';
    };
  }

  window.AuthPage = {
    setMessage: setMessage,
    togglePass: togglePass,
    passwordStrength: passwordStrength,
    bindRolePicker: bindRolePicker,
    setFieldError: setFieldError,
    clearAllFieldErrors: clearAllFieldErrors,
    fieldValue: fieldValue,
    swapView: swapView,
    liveClear: liveClear,
    REGEX_EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    REGEX_MOBILE: /^[0-9]{10,12}$/,
    REGEX_VEHICLE: /[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,2}[-\s]?\d{4}/i,
    REGEX_LICENSE: /^[A-Z]{2}[-\s]?\d{1,2}[-\s]?\d{4}[-\s]?\d{7}$/i,
  };
})();