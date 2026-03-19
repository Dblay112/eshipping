/**
 * My Tallies (tally) — extracted from my_tallies.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.MY_TALLIES_CONFIG || {};
  const tallyDates = config.tallyDates || [];
  const calYear = config.calYear;
  const calMonth = config.calMonth;
  const qVal = config.qVal || '';
  const periodVal = config.periodVal || '';
  const myTalliesUrl = config.myTalliesUrl || '';

  // Mobile card expand/collapse functionality with improved scroll detection
  (function() {
    try {
      document.querySelectorAll('.sdt-mobile-card-header').forEach(header => {
        let touchStartY = 0;
        let touchStartX = 0;
        let touchStartTime = 0;
        let isScrolling = false;

        // Track touch start position and time
        header.addEventListener('touchstart', function(e) {
          touchStartY = e.touches[0].clientY;
          touchStartX = e.touches[0].clientX;
          touchStartTime = Date.now();
          isScrolling = false;
        }, { passive: true });

        // Detect if user is scrolling
        header.addEventListener('touchmove', function(e) {
          const touchMoveY = e.touches[0].clientY;
          const touchMoveX = e.touches[0].clientX;
          const deltaY = Math.abs(touchMoveY - touchStartY);
          const deltaX = Math.abs(touchMoveX - touchStartX);

          // If moved more than 5px, consider it scrolling
          if (deltaY > 5 || deltaX > 5) {
            isScrolling = true;
          }
        }, { passive: true });

        // Only toggle if it was a tap, not a scroll
        header.addEventListener('touchend', function(e) {
          const touchEndY = e.changedTouches[0].clientY;
          const touchEndX = e.changedTouches[0].clientX;
          const deltaY = Math.abs(touchEndY - touchStartY);
          const deltaX = Math.abs(touchEndX - touchStartX);
          const touchDuration = Date.now() - touchStartTime;

          // Only toggle if:
          // 1. Not scrolling
          // 2. Movement is less than 15px
          // 3. Touch duration is less than 300ms (quick tap)
          if (!isScrolling && deltaY < 15 && deltaX < 15 && touchDuration < 300) {
            e.preventDefault();
            const card = this.closest('.sdt-mobile-card');
            if (card) {
              card.classList.toggle('expanded');
            }
          }
        }, { passive: false });
      });
    } catch (err) {
      console.error('Error initializing mobile cards:', err);
    }
  })();

  // Sort dropdown functionality
  const sortSelect = document.getElementById('sortSelect');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      const params = new URLSearchParams();
      if (qVal) params.set('q', qVal);
      if (periodVal) params.set('period', periodVal);
      params.set('sort', sortSelect.value);
      params.set('cal_year', calYear);
      params.set('cal_month', calMonth);
      window.location.href = myTalliesUrl + '?' + params.toString();
    });
  }

  // Mark days that have tallies with a dot indicator
  (function() {
    try {
      document.querySelectorAll('.sdt-cal-day:not(.sdt-cal-empty)').forEach(el => {
        const day = parseInt(el.textContent.trim());
        const mm = String(calMonth).padStart(2, '0');
        const dd = String(day).padStart(2, '0');
        const iso = `${calYear}-${mm}-${dd}`;
        if (tallyDates.includes(iso)) {
          const dot = document.createElement('span');
          dot.className = 'sdt-cal-dot';
          el.appendChild(dot);
        }
      });
    } catch (err) {
      console.error('Error marking calendar dates:', err);
    }
  })();

  // PC Table: SD Group Expand/Collapse functionality
  document.addEventListener('DOMContentLoaded', function() {
    try {
      document.querySelectorAll('.sd-group-header').forEach(header => {
        header.addEventListener('click', function(e) {
          e.preventDefault();
          const sdGroup = this.getAttribute('data-sd-group');
          const arrow = this.querySelector('.sd-arrow');
          const tallyRows = document.querySelectorAll(`.sd-tally-row[data-sd-group="${sdGroup}"]`);

          // Toggle visibility
          tallyRows.forEach(row => {
            if (row.style.display === 'none' || row.style.display === '') {
              row.style.display = 'table-row';
            } else {
              row.style.display = 'none';
            }
          });

          // Rotate arrow
          if (arrow) {
            const currentTransform = arrow.style.transform || 'rotate(0deg)';
            if (currentTransform.includes('90deg')) {
              arrow.style.transform = 'rotate(0deg)';
            } else {
              arrow.style.transform = 'rotate(90deg)';
            }
          }
        });
      });
    } catch (err) {
      console.error('Error initializing SD group toggle:', err);
    }
  });

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
