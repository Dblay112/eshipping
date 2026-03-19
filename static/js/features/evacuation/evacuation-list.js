/**
 * Evacuation List — extracted from evacuation_list.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.EVACUATION_LIST_CONFIG || {};
  const evacuationDates = config.evacuationDates || [];
  const calYear = config.calYear;
  const calMonth = config.calMonth;

  // Toggle SD group expansion (Desktop)
  const toggleSDGroup = (header) => {
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

  // Toggle SD group expansion (Mobile)
  const toggleSDGroupMobile = (header) => {
    const content = header.nextElementSibling;
    const icon = header.querySelector('.expand-icon-mobile');

    if (content.style.display === 'none' || content.style.display === '') {
      content.style.display = 'block';
      icon.style.transform = 'rotate(90deg)';
    } else {
      content.style.display = 'none';
      icon.style.transform = 'rotate(0deg)';
    }
  };

  // expose for inline onclick handlers
  window.toggleSDGroup = toggleSDGroup;
  window.toggleSDGroupMobile = toggleSDGroupMobile;

  // Mark days that have evacuations with a dot indicator
  (function() {
    document.querySelectorAll('.sdt-cal-day:not(.sdt-cal-empty)').forEach(el => {
      const day = parseInt(el.textContent.trim());
      const mm = String(calMonth).padStart(2, '0');
      const dd = String(day).padStart(2, '0');
      const iso = `${calYear}-${mm}-${dd}`;
      if (evacuationDates.includes(iso)) {
        const dot = document.createElement('span');
        dot.className = 'sdt-cal-dot';
        el.appendChild(dot);
      }
    });
  })();
})();
