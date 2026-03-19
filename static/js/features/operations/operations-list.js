/**
 * Operations List (SD records) — extracted from operations_list.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const toggleRow = (pk) => {
    const detailRow  = document.getElementById('detailRow_'  + pk);
    const expandIcon = document.getElementById('expandIcon_' + pk);
    const mainRow    = document.querySelector('[data-pk="' + pk + '"]');
    if (!detailRow) return;
    const isOpen = detailRow.classList.contains('open');
    // Close all others
    document.querySelectorAll('.sdt-detail-row.open').forEach(r => { r.classList.remove('open'); });
    document.querySelectorAll('.sdt-main-row.sdt-row-open').forEach(r => { r.classList.remove('sdt-row-open'); });
    if (!isOpen) {
      detailRow.classList.add('open');
      mainRow.classList.add('sdt-row-open');
    }
  };

  // expose for inline usage if any
  window.toggleRow = toggleRow;

  // Mobile card expand/collapse functionality
  document.querySelectorAll('.sdt-mobile-card-header').forEach(header => {
    header.addEventListener('click', function(e) {
      const card = this.closest('.sdt-mobile-card');
      card.classList.toggle('expanded');
    });
  });

  // Add touch support for mobile devices
  (function() {
    let touchHandled = false;
    let touchStartTime = 0;
    let touchStartX = 0;
    let touchStartY = 0;
    let touchMoved = false;

    document.querySelectorAll('.sdt-main-row').forEach(row => {
      // Touch events for mobile
      row.addEventListener('touchstart', (e) => {
        // Don't toggle if touching a button or link
        if (e.target.closest('a, button')) {
          return;
        }
        touchStartTime = Date.now();
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        touchMoved = false;
        touchHandled = true;
      }, { passive: true });

      row.addEventListener('touchmove', (e) => {
        if (!touchHandled) return;

        const touchX = e.touches[0].clientX;
        const touchY = e.touches[0].clientY;
        const deltaX = Math.abs(touchX - touchStartX);
        const deltaY = Math.abs(touchY - touchStartY);

        // If finger moved more than 10px, it's a scroll gesture
        if (deltaX > 10 || deltaY > 10) {
          touchMoved = true;
        }
      }, { passive: true });

      row.addEventListener('touchend', function(e) {
        // Don't toggle if touching a button or link
        if (e.target.closest('a, button')) {
          touchHandled = false;
          touchMoved = false;
          return;
        }

        // Only toggle if it was a quick tap AND didn't move (not a scroll)
        const touchDuration = Date.now() - touchStartTime;
        if (touchHandled && touchDuration < 300 && !touchMoved) {
          e.preventDefault();
          const pk = this.getAttribute('data-pk');
          if (pk) {
            toggleRow(pk);
          }
        }
        touchHandled = false;
        touchMoved = false;
      });

      // Click events for desktop (only fire if touch wasn't handled)
      row.addEventListener('click', function(e) {
        // Don't toggle if clicking a button or link
        if (e.target.closest('a, button')) {
          return;
        }

        if (touchHandled) {
          touchHandled = false;
          return;
        }
        const pk = this.getAttribute('data-pk');
        if (pk) {
          toggleRow(pk);
        }
      });
    });
  })();
})();
