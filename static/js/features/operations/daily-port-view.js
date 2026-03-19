/**
 * Daily Port View (operations) — extracted from daily_port.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.DAILY_PORT_VIEW_CONFIG || {};
  const portDates = config.portDates || [];
  const calYear = config.calYear;
  const calMonth = config.calMonth;

  (function() {
    document.querySelectorAll('.sdt-cal-day:not(.sdt-cal-empty)').forEach(function(el) {
      const day = parseInt(el.textContent.trim());
      const mm = String(calMonth).padStart(2, '0');
      const dd = String(day).padStart(2, '0');
      const iso = `${calYear}-${mm}-${dd}`;
      if (portDates.includes(iso)) {
        const dot = document.createElement('span');
        dot.className = 'sdt-cal-dot';
        el.appendChild(dot);
      }
    });
  })();
})();
