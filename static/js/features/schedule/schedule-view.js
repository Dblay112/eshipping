/**
 * Schedule View (operations) — extracted from schedule.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.SCHEDULE_VIEW_CONFIG || {};
  const scheduledDates = config.scheduledDates || [];
  const calYear = config.calYear;
  const calMonth = config.calMonth;

  // Mobile card expand/collapse functionality
  document.querySelectorAll('.sdt-mobile-card-header').forEach(header => {
    header.addEventListener('click', function(e) {
      const card = this.closest('.sdt-mobile-card');
      card.classList.toggle('expanded');
    });
  });

  // Mark days that have schedules with a dot indicator
  (function() {
    document.querySelectorAll('.sdt-cal-day:not(.sdt-cal-empty)').forEach(el => {
      const day = parseInt(el.textContent.trim());
      const mm = String(calMonth).padStart(2, '0');
      const dd = String(day).padStart(2, '0');
      const iso = `${calYear}-${mm}-${dd}`;
      if (scheduledDates.includes(iso)) {
        const dot = document.createElement('span');
        dot.className = 'sdt-cal-dot';
        el.appendChild(dot);
      }
    });
  })();

  // Touch event handling for mobile expandable rows
  (function() {
    let touchHandled = false;

    document.querySelectorAll('.sdt-entry-row').forEach(row => {
      // Touch events for mobile
      row.addEventListener('touchstart', (e) => {
        // Don't expand if clicking on a link or button
        if (e.target.closest('a') || e.target.closest('button')) {
          return;
        }
        touchHandled = true;
      }, { passive: true });

      // Click events for desktop
      row.addEventListener('click', (e) => {
        // Don't expand if clicking on a link or button
        if (e.target.closest('a') || e.target.closest('button')) {
          return;
        }

        if (touchHandled) {
          touchHandled = false;
          return;
        }
      });
    });
  })();
})();
