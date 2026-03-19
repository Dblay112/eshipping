/**
 * Schedule Form (operations) — extracted from schedule_form.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  (function() {
    const list = document.getElementById('entriesList');
    const addBtn = document.getElementById('addEntryBtn');
    const countEl = document.getElementById('entryCount');

    // Works with any Django formset prefix
    const totalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');
    if (!list || !addBtn || !totalForms) return;

    // e.g. "scheduleentry_set-TOTAL_FORMS" -> "scheduleentry_set"
    const prefix = totalForms.name.replace(/-TOTAL_FORMS$/, '');
    const indexRe = new RegExp(prefix + '-\\d+', 'g');

    const getRows = () => {
      return Array.from(list.querySelectorAll('.sdt-entry-form-row'));
    };

    const isRowDeleted = (row) => {
      return row.classList.contains('is-deleted');
    };

    const isRowEmpty = (row) => {
      const inputs = Array.from(row.querySelectorAll('input, select, textarea'));
      for (const el of inputs) {
        if (el.type === 'hidden') continue;
        if (el.name && el.name.endsWith('-DELETE')) continue;
        if (el.name && el.name.endsWith('-id')) continue;

        if (el.type === 'checkbox' || el.type === 'radio') {
          if (el.checked) return false;
        } else {
          if ((el.value || '').trim() !== '') return false;
        }
      }
      return true;
    };

    const updateNumbers = () => {
      let visible = 0;
      getRows().forEach(row => {
        const num = row.querySelector('.sdt-entry-form-number');
        if (!num) return;
        if (isRowDeleted(row)) return;

        visible += 1;
        num.textContent = visible;
      });
      if (countEl) countEl.textContent = '(' + visible + ')';
    };

    const markDeleted = (row) => {
      if (!row) return;

      const idx = parseInt(row.getAttribute('data-form-idx') || '0', 10);
      if (idx === 0) return;

      const del = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (del) del.checked = true;

      row.classList.add('is-deleted');
      updateNumbers();
    };

    const wireRemoveButtons = () => {
      getRows().forEach(row => {
        const idx = parseInt(row.getAttribute('data-form-idx') || '0', 10);
        const btn = row.querySelector('.sdt-entry-remove-btn');
        if (!btn) return;

        if (idx === 0) {
          btn.setAttribute('disabled', 'disabled');
          return;
        }

        if (btn.dataset.wired === '1') return;
        btn.dataset.wired = '1';

        btn.addEventListener('click', () => {
          markDeleted(row);
        });
      });
    };

    const collapseExtraEmptyRowsOnLoad = () => {
      getRows().forEach((row, i) => {
        const idx = parseInt(row.getAttribute('data-form-idx') || String(i), 10);
        if (idx === 0) return;
        if (isRowEmpty(row)) markDeleted(row);
      });
    };

    const initOfficerTypeahead = (root) => {
      if (!root) return;

      const input = root.querySelector('[data-officer-input]');
      const select = root.querySelector('select[name$="-assigned_officer"]');
      if (!input || !select) return;

      // Prevent double-wiring
      if (input.dataset.wired === '1') return;
      input.dataset.wired = '1';

      const getUserIdFromOptionValue = (val) => {
        const list = document.getElementById('sch-officer-suggest');
        if (!list) return '';

        const options = Array.from(list.options || []);
        const match = options.find(o => (o.value || '') === (val || ''));
        if (!match) return '';

        return match.getAttribute('data-user-id') || '';
      };

      const setInputFromSelect = () => {
        const selected = select.options[select.selectedIndex];
        if (!selected || !select.value) {
          input.value = '';
          input.classList.remove('is-valid');
          return;
        }

        // Match format used in datalist values
        const staffNo = selected.getAttribute('data-staff-number') || '';
        const first = selected.getAttribute('data-first-name') || '';
        const last = selected.getAttribute('data-last-name') || '';
        const rank = selected.getAttribute('data-rank') || '';

        if (staffNo && first && last) {
          input.value = staffNo + ' — ' + first + ' ' + last + (rank ? ' (' + rank + ')' : '');
        } else {
          input.value = (selected.textContent || '').trim();
        }

        input.classList.add('is-valid');
      };

      // Build data attributes for quick mapping (no extra requests)
      Array.from(select.options).forEach(opt => {
        const txt = (opt.textContent || '').trim();
        // Default Django label usually is "First Last" or similar.
        // We can’t reliably parse it, so leave unless we can find staff_number in dataset.
        // (Template datalist already includes staff_number+name+rank; we map by datalist selection.)
        opt.setAttribute('data-option-text', txt);
      });

      // If editing an existing schedule entry, populate input from selected value.
      // (We can’t derive full label reliably; fallback to select option text.)
      if (select.value) {
        input.value = (select.options[select.selectedIndex].textContent || '').trim();
        input.classList.add('is-valid');
      }

      const syncToSelect = () => {
        const userId = getUserIdFromOptionValue((input.value || '').trim());
        if (!userId) {
          select.value = '';
          input.classList.remove('is-valid');
          return;
        }

        select.value = userId;
        input.classList.add('is-valid');
      };

      input.addEventListener('change', syncToSelect);
      input.addEventListener('blur', syncToSelect);
      select.addEventListener('change', setInputFromSelect);
    };

    // Init existing rows
    const initAllOfficerFields = () => {
      getRows().forEach(row => {
        const wrap = row.querySelector('.sch-officer-field');
        initOfficerTypeahead(wrap);
      });
    };

    addBtn.addEventListener('click', () => {
      const rows = getRows();
      const idx = rows.length;
      const template = rows[0].cloneNode(true);

      template.setAttribute('data-form-idx', idx);

      template.querySelectorAll('[name],[id],[for]').forEach(el => {
        ['name','id','for'].forEach(attr => {
          const val = el.getAttribute(attr);
          if (!val) return;
          el.setAttribute(attr, val.replace(indexRe, prefix + '-' + idx));
        });

        if (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') {
          if (el.type === 'checkbox' || el.type === 'radio') {
            el.checked = false;
          } else {
            el.value = '';
          }
        }
      });

      const idField = template.querySelector('input[type="hidden"][name$="-id"]');
      if (idField) idField.value = '';

      const del = template.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (del) del.checked = false;

      const removeWrap = template.querySelector('.sdt-entry-form-remove');
      if (removeWrap && removeWrap.classList.contains('sdt-entry-form-remove-disabled')) {
        const deleteField = template.querySelector('input[type="checkbox"][name$="-DELETE"]');

        removeWrap.classList.remove('sdt-entry-form-remove-disabled');
        removeWrap.removeAttribute('aria-hidden');
        removeWrap.innerHTML = '';

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'sdt-entry-remove-btn';
        btn.title = 'Remove SD Entry';
        btn.setAttribute('aria-label', 'Remove SD Entry');
        btn.innerHTML = '<svg viewBox="0 0 20 20" fill="none"><path d="M5 5l10 10M15 5L5 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';
        removeWrap.appendChild(btn);

        const hidden = document.createElement('div');
        hidden.className = 'sdt-hidden-delete';
        if (deleteField) hidden.appendChild(deleteField);
        removeWrap.appendChild(hidden);
      }

      template.classList.remove('is-deleted');

      list.appendChild(template);
      totalForms.value = idx + 1;

      // Officer typeahead: clear input and rewire
      const officerWrap = template.querySelector('.sch-officer-field');
      if (officerWrap) {
        const inp = officerWrap.querySelector('[data-officer-input]');
        if (inp) {
          inp.value = '';
          inp.classList.remove('is-valid');
          inp.dataset.wired = '0';
        }
      }

      wireRemoveButtons();
      initAllOfficerFields();
      updateNumbers();
    });

    wireRemoveButtons();
    collapseExtraEmptyRowsOnLoad();
    initAllOfficerFields();
    updateNumbers();
  })();
})();
