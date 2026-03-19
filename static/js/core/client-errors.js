/**
 * Global client-side error capture
 *
 * Logs JS runtime errors + unhandled promise rejections to the server.
 * This helps detect when something broke in production.
 *
 * NOTE: No user PII should be logged.
 */

(function() {
  'use strict';

  const ENDPOINT = '/api/client-error/';
  const RATE_LIMIT_MS = 3000;
  let lastSentAt = 0;

  function safeString(value, maxLen = 1500) {
    try {
      const str = String(value ?? '');
      return str.length > maxLen ? str.slice(0, maxLen) + '…' : str;
    } catch (_) {
      return '';
    }
  }

  function getCsrfToken() {
    // Django's default CSRF cookie name
    const name = 'csrftoken=';
    const parts = document.cookie ? document.cookie.split(';') : [];
    for (let i = 0; i < parts.length; i++) {
      const c = parts[i].trim();
      if (c.startsWith(name)) {
        return decodeURIComponent(c.substring(name.length));
      }
    }
    return null;
  }

  function send(payload) {
    const now = Date.now();
    if (now - lastSentAt < RATE_LIMIT_MS) return;
    lastSentAt = now;

    const body = {
      ...payload,
      url: safeString(window.location.href, 2048),
      userAgent: safeString(navigator.userAgent, 512),
      timestamp: new Date().toISOString(),
    };

    try {
      const headers = { 'Content-Type': 'application/json' };
      const csrf = getCsrfToken();
      if (csrf) headers['X-CSRFToken'] = csrf;

      // Prefer sendBeacon when available (doesn't block page unload)
      if (navigator.sendBeacon) {
        const blob = new Blob([JSON.stringify(body)], { type: 'application/json' });
        navigator.sendBeacon(ENDPOINT, blob);
        return;
      }

      fetch(ENDPOINT, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        credentials: 'same-origin',
        keepalive: true,
      }).catch(() => {
        // Intentionally ignore network errors
      });
    } catch (_) {
      // Intentionally ignore
    }
  }

  window.addEventListener('error', function(event) {
    // event.error may be null for script errors
    const err = event && event.error;

    send({
      type: 'window_error',
      message: safeString(event && event.message),
      filename: safeString(event && event.filename, 512),
      lineno: Number(event && event.lineno) || null,
      colno: Number(event && event.colno) || null,
      stack: safeString(err && err.stack),
    });
  });

  window.addEventListener('unhandledrejection', function(event) {
    const reason = event && event.reason;
    send({
      type: 'unhandledrejection',
      message: safeString(reason && (reason.message || reason)),
      stack: safeString(reason && reason.stack),
    });
  });
})();
