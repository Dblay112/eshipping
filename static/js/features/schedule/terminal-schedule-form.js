/**
 * Terminal Schedule Form (operations) — extracted from terminal_schedule_form.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  (function () {
    // ── 1. elements
    const hiddenSelect = document.getElementById('id_supervisors');
    const chipsEl      = document.getElementById('supChips');
    const searchEl     = document.getElementById('supSearch');
    const dropEl       = document.getElementById('supDropdown');

    if (!hiddenSelect || !chipsEl || !searchEl || !dropEl) return;

    // ── 2. build list of users from <option>
    const allUsers = Array.from(hiddenSelect.options).map(function (opt) {
      return {
        id: opt.value,
        num: (opt.textContent || '').trim().split(' — ')[0] || '',
        name: (opt.textContent || '').trim().split(' — ').slice(1).join(' — ') || (opt.textContent || '').trim(),
      };
    });

    // ── 3. chips helpers
    function selectedIds() {
      return Array.from(hiddenSelect.options).filter(o => o.selected).map(o => o.value);
    }

    function renderChips() {
      chipsEl.innerHTML = '';
      const current = selectedIds();
      current.forEach(function (id) {
        const u = allUsers.find(x => x.id === id);
        if (!u) return;

        const chip = document.createElement('span');
        chip.className = 'sup-chip';
        chip.innerHTML =
          '<span class="sup-chip-num">' + u.num + '</span>' +
          '<span class="sup-chip-name">' + u.name + '</span>' +
          '<button type="button" class="sup-chip-remove" aria-label="Remove">×</button>';

        chip.querySelector('.sup-chip-remove').addEventListener('click', function () {
          removeUser(id);
        });

        chipsEl.appendChild(chip);
      });
    }

    function addUser(id) {
      const opt = hiddenSelect.querySelector('option[value="' + id + '"]');
      if (opt) opt.selected = true;
      renderChips();
      searchEl.value = '';
      closeDropdown();
    }

    function removeUser(id) {
      const opt = hiddenSelect.querySelector('option[value="' + id + '"]');
      if (opt) opt.selected = false;
      renderChips();
    }

    // ── 4. dropdown helpers
    function openDropdown(items) {
      dropEl.innerHTML = '';
      if (items.length === 0) {
        dropEl.innerHTML = '<div class="sup-dd-empty">No staff found</div>';
      } else {
        items.slice(0, 10).forEach(function (u) {
          const div = document.createElement('div');
          div.className = 'sup-dd-item';
          div.innerHTML =
            '<span class="staff-no">' + u.num + '</span>' +
            '<span class="staff-name">' + u.name + '</span>';
          div.addEventListener('mousedown', function (e) {
            e.preventDefault(); // prevent blur firing before click
            addUser(u.id);
          });
          dropEl.appendChild(div);
        });
      }
      dropEl.classList.add('open');
    }

    function closeDropdown() { dropEl.classList.remove('open'); }

    // ── 5. search input events
    searchEl.addEventListener('input', function () {
      const q = this.value.trim().toLowerCase();
      if (q.length < 1) { closeDropdown(); return; }
      const current = selectedIds();
      const matches = allUsers.filter(function (u) {
        if (current.includes(u.id)) return false; // already added
        return u.num.includes(q) || u.name.toLowerCase().includes(q);
      });
      openDropdown(matches);
    });

    searchEl.addEventListener('focus', function () {
      if (this.value.trim().length > 0) {
        this.dispatchEvent(new Event('input'));
      }
    });

    searchEl.addEventListener('blur', function () {
      setTimeout(closeDropdown, 150);
    });

    // ── 6. initialise chips from any pre-selected options (edit mode)
    renderChips();
  })();
})();
