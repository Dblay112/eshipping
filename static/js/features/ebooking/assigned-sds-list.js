/**
 * Assigned SDs List (ebooking) — extracted from assigned_sds_list.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.ASSIGNED_SDS_LIST_CONFIG || {};
  const bookingDates = config.bookingDates || [];
  const calYear = config.calYear;
  const calMonth = config.calMonth;

  // Mark days that have bookings with a dot indicator
  (function() {
    document.querySelectorAll('.sdt-cal-day:not(.sdt-cal-empty)').forEach(function(el) {
      const day = parseInt(el.textContent.trim());
      const mm = String(calMonth).padStart(2, '0');
      const dd = String(day).padStart(2, '0');
      const iso = `${calYear}-${mm}-${dd}`;
      if (bookingDates.includes(iso)) {
        const dot = document.createElement('span');
        dot.className = 'sdt-cal-dot';
        el.appendChild(dot);
      }
    });
  })();

  // Mobile card expand/collapse functionality
  document.querySelectorAll('.sdt-mobile-card-header').forEach(function(header) {
    header.addEventListener('click', function(e) {
      const card = this.closest('.sdt-mobile-card');
      card.classList.toggle('expanded');
    });
  });

  // Toggle row expansion
  function toggleRow(pk) {
    const icon = document.getElementById('expandIcon_' + pk);
    const detailRow = document.getElementById('detailRow_' + pk);
    const mainRow = document.querySelector('[data-pk="' + pk + '"]');

    if (!detailRow) return;

    const isOpen = detailRow.classList.contains('open');

    // Close all other rows first
    document.querySelectorAll('.sdt-detail-row.open').forEach(function(r) { r.classList.remove('open'); });
    document.querySelectorAll('.sdt-main-row.sdt-row-open').forEach(function(r) { r.classList.remove('sdt-row-open'); });

    // Toggle current row
    if (!isOpen) {
      detailRow.classList.add('open');
      mainRow.classList.add('sdt-row-open');
    }
  }

  // expose for any inline usage
  window.toggleRow = toggleRow;

  // Add click/touch support - ENTIRE ROW is clickable
  (function() {
    document.querySelectorAll('.sdt-main-row').forEach(function(row) {
      const pk = row.getAttribute('data-pk');
      if (!pk) return;

      // Make row look clickable
      row.style.cursor = 'pointer';

      // Click event for desktop
      row.addEventListener('click', function(e) {
        // Don't toggle if clicking on a link, button, or input
        if (e.target.closest('a') || e.target.closest('button') || e.target.closest('input')) {
          return;
        }
        e.preventDefault();
        toggleRow(pk);
      });

      // Touch event for mobile
      row.addEventListener('touchend', function(e) {
        // Don't toggle if touching a link, button, or input
        if (e.target.closest('a') || e.target.closest('button') || e.target.closest('input')) {
          return;
        }
        e.preventDefault();
        toggleRow(pk);
      });
    });
  })();
})();
