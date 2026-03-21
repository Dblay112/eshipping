/**
 * Pending Tallies (tally) — extracted from pending_tallies.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.PENDING_TALLIES_CONFIG || {};
  const pendingDates = config.pendingDates || [];
  const calYear = config.calYear;
  const calMonth = config.calMonth;

  // Toggle SD group expansion (Desktop)
  window.toggleSDGroup = (header) => {
    const content = header.nextElementSibling;
    const icon = header.querySelector('.expand-icon');

    if (content.style.display === 'none' || content.style.display === '') {
      content.style.display = 'block';
      icon.style.transform = 'rotate(90deg)';
    } else {
      content.style.display = 'none';
      icon.style.transform = 'rotate(0deg)';
    }
  };

  // Toggle SD group expansion (Mobile) with error handling
  window.toggleSDGroupMobile = (header) => {
    try {
      const card = header.closest('.pt-sd-card-mobile');

      if (card) {
        card.classList.toggle('expanded');
      }
    } catch (err) {
      console.error('Error toggling SD group:', err);
    }
  };

  // Add touch event support for mobile SD groups
  (function() {
    try {
      document.querySelectorAll('.sd-group-header-mobile').forEach(header => {
        header.addEventListener('touchend', (e) => {
          e.preventDefault();
          window.toggleSDGroupMobile(header);
        }, { passive: false });
      });
    } catch (err) {
      console.error('Error adding touch events:', err);
    }
  })();

  // Mobile card expand/collapse functionality with error handling
  (function() {
    try {
      document.querySelectorAll('.sdt-mobile-card-header').forEach(header => {
        header.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          const card = this.closest('.sdt-mobile-card');
          if (card) {
            card.classList.toggle('expanded');
          }
        });

        // Add touch event for better mobile support
        header.addEventListener('touchend', function(e) {
          e.preventDefault();
          const card = this.closest('.sdt-mobile-card');
          if (card) {
            card.classList.toggle('expanded');
          }
        }, { passive: false });
      });
    } catch (err) {
      console.error('Error initializing mobile cards:', err);
    }
  })();

  // Mark days that have pending tallies with a dot indicator
  (function() {
    try {
      document.querySelectorAll('.sdt-cal-day:not(.sdt-cal-empty)').forEach(el => {
        const day = parseInt(el.textContent.trim());
        const mm = String(calMonth).padStart(2, '0');
        const dd = String(day).padStart(2, '0');
        const iso = `${calYear}-${mm}-${dd}`;
        if (pendingDates.includes(iso)) {
          const dot = document.createElement('span');
          dot.className = 'sdt-cal-dot';
          el.appendChild(dot);
        }
      });
    } catch (err) {
      console.error('Error marking calendar dates:', err);
    }
  })();

  // Hide recall history badge after viewing modal
  document.addEventListener('DOMContentLoaded', () => {
    try {
      const viewedKey = 'recall_history_viewed';
      const viewed = JSON.parse(localStorage.getItem(viewedKey) || '{}');

      // Hide badges for already viewed tallies
      Object.keys(viewed).forEach(tallyId => {
        const badge = document.querySelector(`[data-bs-target="#recallHistoryModal${tallyId}"] span[style*="position:absolute"]`);
        if (badge) badge.style.display = 'none';
      });

      // Mark as viewed when modal is opened
      document.querySelectorAll('[id^="recallHistoryModal"]').forEach(modal => {
        modal.addEventListener('show.bs.modal', function() {
          const tallyId = this.id.replace('recallHistoryModal', '');
          viewed[tallyId] = Date.now();
          localStorage.setItem(viewedKey, JSON.stringify(viewed));

          // Hide badge immediately
          const badge = document.querySelector(`[data-bs-target="#${this.id}"] span[style*="position:absolute"]`);
          if (badge) badge.style.display = 'none';
        });
      });
    } catch (err) {
      console.error('Error handling recall history:', err);
    }
  });
})();
