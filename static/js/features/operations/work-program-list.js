/**
 * Work Program List (operations) — extracted from work_program_list.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.WORK_PROGRAM_LIST_CONFIG || {};
  const wpDates = config.wpDates || [];
  const calYear = config.calYear;
  const calMonth = config.calMonth;

  // Mark days that have work programs with a dot indicator
  (function() {
    document.querySelectorAll('.sdt-cal-day:not(.sdt-cal-empty)').forEach(function(el) {
      const day = parseInt(el.textContent.trim());
      const mm = String(calMonth).padStart(2, '0');
      const dd = String(day).padStart(2, '0');
      const iso = `${calYear}-${mm}-${dd}`;
      if (wpDates.includes(iso)) {
        const dot = document.createElement('span');
        dot.className = 'sdt-cal-dot';
        el.appendChild(dot);
      }
    });
  })();
})();
