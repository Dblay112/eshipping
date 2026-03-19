/**
 * SD Form (operations) — extracted from sd_form.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.SD_FORM_CONFIG || {};
  const savedTonnageLoaded = config.savedTonnageLoaded || {};

  // Escape HTML helper used by TT table builder
  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  (function () {

    // ── SD Number auto-populate on blur ──────────────────────────
    const sdNumberInput = document.getElementById('id_sd_number');
    if (sdNumberInput && !sdNumberInput.value) {
      // Only on create (empty field)
      sdNumberInput.addEventListener('blur', function () {
        const val = this.value.trim();
        if (!val) return;
        fetch('/operations/autofill/?sd_number=' + encodeURIComponent(val), {
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (!data || data.error) return;
          // Populate fields
          const setVal = (id, v) => { const el = document.getElementById(id); if (el && v !== undefined) el.value = v; };
          setVal('id_vessel_name',   data.vessel_name   || '');
          setVal('id_eta',           data.eta           || '');
          setVal('id_crop_year',     data.crop_year     || '');
          setVal('id_tonnage',       data.tonnage       || '');
          setVal('id_agent',         data.agent         || '');
          setVal('id_port_of_loading', data.port_of_loading || '');
          setVal('id_port_of_discharge', data.port_of_discharge || '');
          setVal('id_container_size',  data.container_size  || '');
          setVal('id_si_ref',          data.si_ref          || '');
          setVal('id_stock_allocation_notes', data.stock_allocation_notes || '');
          // show a note
          const hint = document.createElement('p');
          hint.className = 'sdt-form-hint sdt-autofill-notice';
          hint.textContent = '✓ Details pre-filled from saved draft — all fields are editable.';
          sdNumberInput.parentElement.appendChild(hint);
        });
      });
    }

    // ── Add alloc block (clones the first block) ─────────────────
    const addAllocBtn = document.getElementById('addAllocBtn');
    if (addAllocBtn) {
      addAllocBtn.addEventListener('click', () => {
        const list  = document.getElementById('allocList');
        const total = document.getElementById('id_allocs-TOTAL_FORMS');
        if (!list || !total) return;

        const blocks = list.querySelectorAll('.sdt-alloc-block');
        const idx    = blocks.length;
        const tmpl   = blocks[0].cloneNode(true);

        tmpl.setAttribute('data-form-idx', idx);
        tmpl.classList.add('sdt-alloc-block-extra');

        // Update preview id
        const preview = tmpl.querySelector('.sdt-alloc-block-preview');
        if (preview) preview.id = 'allocPreview_' + idx;

        // Show remove button (not first anymore)
        const removeBtn = tmpl.querySelector('.sdt-alloc-block-remove');
        if (removeBtn) {
          removeBtn.classList.remove('sdt-remove-first-alloc');
          removeBtn.setAttribute('onclick', 'removeAllocRow(this)');
        }

        // Update all name/id/for attrs
        tmpl.querySelectorAll('[name],[id],[for]').forEach(el => {
          ['name', 'id', 'for'].forEach(attr => {
            let v = el.getAttribute(attr);
            if (v) el.setAttribute(attr, v.replace(/allocs-\d+/, 'allocs-' + idx));
          });
          if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) {
            el.value = '';
            if (el.type === 'checkbox') el.checked = false;
          }
        });

        // Fix data-alloc-idx attrs
        tmpl.querySelectorAll('[data-alloc-idx]').forEach(el => {
          el.setAttribute('data-alloc-idx', idx);
        });

        // Fix oninput handlers to use correct index
        tmpl.querySelectorAll('[oninput*="updateAllocPreview"]').forEach(el => {
          el.setAttribute('oninput', 'updateAllocPreview(' + idx + ')');
        });

        // Fix container size select name
        const cSelect = tmpl.querySelector('select[name^="alloc_container_size_"]');
        if (cSelect) cSelect.name = 'alloc_container_size_' + idx;

        list.appendChild(tmpl);
        total.value = idx + 1;

        // Update badge numbers
        renumberAllocBlocks();
        updateAllocCount();
        updateMultipleRowsClass('allocList');
        wireAllocInputListeners();
        buildTTTable();
      });
    }

    // ── Generic add-row for clerks ────────────────────────────────
    document.querySelectorAll('.sdt-add-entry-btn[data-list]').forEach(btn => {
      btn.addEventListener('click', () => {
        const listId  = btn.dataset.list;
        const prefix  = btn.dataset.prefix;
        const countId = btn.dataset.count;
        const list    = document.getElementById(listId);
        const total   = document.getElementById('id_' + prefix + '-TOTAL_FORMS');
        if (!list || !total) return;

        const rows = list.querySelectorAll('.sdt-entry-form-row');
        const idx  = rows.length;
        const tmpl = rows[0].cloneNode(true);

        tmpl.setAttribute('data-form-idx', idx);
        tmpl.classList.add('sdt-extra-row');

        if (!tmpl.querySelector('.sdt-remove-row-btn')) {
          const removeBtn2 = document.createElement('button');
          removeBtn2.type = 'button';
          removeBtn2.className = 'sdt-remove-row-btn';
          removeBtn2.setAttribute('onclick', 'removeClerkRow(this)');
          removeBtn2.setAttribute('title', 'Remove');
          removeBtn2.innerHTML = '<svg viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';
          tmpl.insertBefore(removeBtn2, tmpl.firstChild);
        }

        tmpl.querySelectorAll('[name],[id],[for]').forEach(el => {
          ['name', 'id', 'for'].forEach(attr => {
            let v = el.getAttribute(attr);
            if (v) el.setAttribute(attr, v.replace(new RegExp(prefix + '-\\d+'), prefix + '-' + idx));
          });
          if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) {
            el.value = '';
            if (el.type === 'checkbox') el.checked = false;
          }
        });

        list.appendChild(tmpl);
        total.value = idx + 1;
        renumberRows(list, '.sdt-entry-form-number');
        const countEl = document.getElementById(countId);
        if (countEl) countEl.textContent = '(' + (idx + 1) + ')';
        updateMultipleRowsClass(listId);
      });
    });


  // ── Contract Allocations: keep only 1 visible blank row on load ──────────
  // If the formset renders extra empty rows, we remove the empty ones on load.
  // We keep:
  //   - the first row always
  //   - any row that has an existing DB id (editing)
  //   - any row that already has user-entered values (e.g., validation errors)
  (function pruneEmptyAllocRowsOnLoad() {
    const list  = document.getElementById('allocList');
    const total = document.getElementById('id_allocs-TOTAL_FORMS');
    if (!list || !total) return;

    const blocks = Array.prototype.slice.call(list.querySelectorAll('.sdt-alloc-block'));
    if (blocks.length <= 1) return;

    const hasExistingId = (block) => {
      const idInput = block.querySelector('input[type="hidden"][name$="-id"]');
      return !!(idInput && (idInput.value || '').trim());
    };

    const hasUserData = (block) => {
      const fields = block.querySelectorAll('input, select, textarea');
      for (let i = 0; i < fields.length; i++) {
        const el = fields[i];
        if (!el.name) continue;
        // ignore management-ish fields and delete/id
        if (/-DELETE$/.test(el.name) || /-id$/.test(el.name)) continue;
        if (el.type === 'checkbox') { if (el.checked) return true; continue; }
        // For selects, only count as user data if the value differs from the first option
        if (el.tagName === 'SELECT') {
          const firstOpt = el.options[0];
          if (firstOpt && el.value !== firstOpt.value) return true;
          continue;
        }
        if ((el.value || '').trim() !== '') return true;
      }
      return false;
    };

    // Always keep first block
    const keep = [blocks[0]];

    for (let i = 1; i < blocks.length; i++) {
      if (hasExistingId(blocks[i]) || hasUserData(blocks[i])) {
        keep.push(blocks[i]);
      } else {
        blocks[i].remove();
      }
    }

    total.value = keep.length;
    // After pruning, ensure numbering and counts are correct
    if (typeof renumberAllocBlocks === 'function') renumberAllocBlocks();
    if (typeof updateAllocCount === 'function') updateAllocCount();
    if (typeof updateMultipleRowsClass === 'function') updateMultipleRowsClass('allocList');
  })();

  // ── Initial counts ───────────────────────────────────────────
    updateAllocCount();
    const clerkList = document.getElementById('clerksList');
    const clerkCountEl = document.getElementById('clerkCount');
    if (clerkList && clerkCountEl) {
      clerkCountEl.textContent = '(' + clerkList.querySelectorAll('.sdt-entry-form-row').length + ')';
    }

    // ── SD document file label ───────────────────────────────────
    const sdDocInput = document.getElementById('id_sd_document');
    if (sdDocInput) {
      sdDocInput.addEventListener('change', function () {
        const nameEl = document.getElementById('sdDocName');
        if (nameEl && this.files[0]) {
          // Show new file name when user selects a file
          nameEl.innerHTML = '<span style="color:#2e7d32;font-weight:600;">' + this.files[0].name + '</span> <span style="color:#888;font-size:11px;">(New file selected)</span>';
        }
      });
    }

    // Container List file input
    const containerListInput = document.getElementById('id_container_list');
    if (containerListInput) {
      containerListInput.addEventListener('change', function() {
        const nameEl = document.getElementById('containerListName');
        if (nameEl && this.files[0]) {
          // Show new file name when user selects a file
          nameEl.innerHTML = '<span style="color:#2e7d32;font-weight:600;">' + this.files[0].name + '</span> <span style="color:#888;font-size:11px;">(New file selected)</span>';
        }
      });
    }

    // ══════════════════════════════════════════════════════════════
    //  TONNAGE TRACKING — table builder
    // ══════════════════════════════════════════════════════════════

    // Helper function to clean decimal display (remove trailing zeros)
    const cleanDecimal = (value) => {
      if (value === null || value === undefined || value === '') return '';
      const num = parseFloat(value);
      if (isNaN(num)) return '';
      // Convert to string and remove trailing zeros after decimal point
      let str = num.toFixed(4);
      if (str.includes('.')) {
        str = str.replace(/\.?0+$/, '');
      }
      return str;
    };

    function buildTTTable() {
      const container = document.getElementById('ttContractRows');
      if (!container) return;

      // Preserve existing loaded values
      const prevLoaded = {};
      container.querySelectorAll('.sdt-tt-data-row').forEach(row => {
        const inp = row.querySelector('.sdt-tt-loaded-input');
        if (inp) prevLoaded[row.dataset.allocIdx] = inp.value;
      });

      container.innerHTML = '';

      const contractInputs = document.querySelectorAll('.alloc-contract-number');
      const tonnageInputs  = document.querySelectorAll('.alloc-tonnage-input');
      let hasAny = false;

      contractInputs.forEach((cInput, i) => {
        const block = cInput.closest('.sdt-alloc-block');
        if (block && block.style.display === 'none') return; // hidden/deleted

        const contractNo = (cInput.value || '').trim();
        const tInput     = tonnageInputs[i];
        const allocated  = tInput ? (parseFloat(tInput.value) || 0) : 0;
        if (!contractNo && allocated === 0) return;

        // Use prevLoaded if available (user just edited), otherwise use saved value from database
        const loadedVal  = prevLoaded[i] || savedTonnageLoaded[i] || '';
        const label      = block ? (block.querySelector('input[name$="-allocation_label"]') || {}).value || (i+1) : (i+1);
        const displayName = contractNo || ('Contract ' + (i+1));
        hasAny = true;

        const row = document.createElement('div');
        row.className = 'sdt-tt-data-row';
        row.dataset.allocIdx = i;
        row.dataset.allocated = allocated;

        row.innerHTML =
          '<div class="sdt-tt-td sdt-tt-col-contract">' +
            '<span class="sdt-tt-badge">' + escHtml(String(label)) + '</span>' +
            '<span class="sdt-tt-contract-name">' + escHtml(displayName) + '</span>' +
            (allocated ? '<span class="sdt-tt-alloc-chip">' + cleanDecimal(allocated) + ' MT</span>' : '') +
          '</div>' +
          '<div class="sdt-tt-td sdt-tt-col-loaded">' +
            '<input type="number" class="sdt-tt-loaded-input" name="tt_loaded_' + i + '" ' +
                   'min="0" ' +
                   (allocated ? ('max="' + escHtml(String(allocated)) + '" ') : '') +
                   'placeholder="0" value="' + escHtml(loadedVal) + '">' +
            (allocated ? ('<div class="sdt-tt-hint" style="font-size:11px;color:#9a7b64;margin-top:6px;">0 – ' + cleanDecimal(allocated) + ' MT</div>') : '') +
          '</div>' +
          '<div class="sdt-tt-td sdt-tt-col-balance">' +
            '<div class="sdt-balance-display sdt-tt-balance-chip" id="ttBal_' + i + '">—</div>' +
          '</div>';

        container.appendChild(row);

        // Wire live calc
        const loadedInp = row.querySelector('.sdt-tt-loaded-input');
        (function(r, rowIdx) {
          loadedInp.addEventListener('input', () => {
            recalcTTRow(r, rowIdx);
            recalcGrand();
            syncHiddenTonnageLoaded();
          });
        })(row, i);

        if (loadedVal) recalcTTRow(row, i);
      });

      if (!hasAny) {
        container.innerHTML = '<div class="sdt-tt-empty">Enter contract details above to begin tracking tonnage.</div>';
      }

      recalcGrand();
    }

    const recalcTTRow = (row, idx) => {
      const allocated = parseFloat(row.dataset.allocated) || 0;
      const loadedInp = row.querySelector('.sdt-tt-loaded-input');
      const chip      = document.getElementById('ttBal_' + idx);
      if (!chip) return;

      let loaded = parseFloat(loadedInp ? loadedInp.value : '') || 0;

      // Clamp: loaded must be within 0..allocated (if allocated is set)
      if (loaded < 0) loaded = 0;
      if (allocated > 0 && loaded > allocated) loaded = allocated;
      if (loadedInp && String(loadedInp.value || '') !== String(loaded)) {
        loadedInp.value = loaded ? String(loaded) : '';
      }

      if (allocated > 0 || loaded > 0) {
        const bal = allocated - loaded;
        if (bal <= 0) {
          // Complete — rich green
          chip.textContent    = cleanDecimal(bal) + ' MT';
          chip.style.background  = '#d1fae5';
          chip.style.color       = '#065f46';
          chip.style.borderColor = '#6ee7b7';
        } else {
          // Still loading — warm amber
          chip.textContent    = cleanDecimal(bal) + ' MT';
          chip.style.background  = '#fff8ed';
          chip.style.color       = '#9a5000';
          chip.style.borderColor = '#f0c070';
        }
      } else {
        chip.textContent = '—';
        chip.style.background = chip.style.color = chip.style.borderColor = '';
      }
    };

    const recalcGrand = () => {
      let grandTonnage = 0;
      let grandLoaded  = 0;
      let hasTonnage   = false;

      // Use main SD tonnage field as the authoritative total
      const mainTonnageEl = document.getElementById('id_tonnage');
      if (mainTonnageEl && mainTonnageEl.value) {
        grandTonnage = parseFloat(mainTonnageEl.value) || 0;
        if (grandTonnage > 0) hasTonnage = true;
      }
      if (!hasTonnage) {
        document.querySelectorAll('.alloc-tonnage-input').forEach(inp => {
          const v = parseFloat(inp.value) || 0;
          grandTonnage += v;
          if (v > 0) hasTonnage = true;
        });
      }

      document.querySelectorAll('.sdt-tt-loaded-input').forEach(inp => {
        grandLoaded += parseFloat(inp.value) || 0;
      });

      const gtEl = document.getElementById('grandTotalTonnage');
      const glEl = document.getElementById('grandTotalLoaded');
      const gbEl = document.getElementById('grandTotalBalance');
      const gbalEl = document.getElementById('grandBalanceDisplay');

      if (gtEl) gtEl.textContent = hasTonnage ? (cleanDecimal(grandTonnage) + ' MT') : '—';
      if (glEl) glEl.textContent = grandLoaded ? (cleanDecimal(grandLoaded) + ' MT') : '—';

      const applyBalStyle = (el, bal) => {
        if (!el) return;
        el.textContent = cleanDecimal(bal) + ' MT';
        if (bal <= 0) {
          el.style.background  = '#d1fae5';
          el.style.color       = '#065f46';
          el.style.borderColor = '#6ee7b7';
        } else {
          el.style.background  = '#fff8ed';
          el.style.color       = '#9a5000';
          el.style.borderColor = '#f0c070';
        }
      };

      if (hasTonnage || grandLoaded) {
        const bal = grandTonnage - grandLoaded;
        applyBalStyle(gbEl, bal);
        applyBalStyle(gbalEl, bal);
      } else {
        if (gbEl) {
          gbEl.textContent = '—';
          gbEl.style.background = gbEl.style.color = gbEl.style.borderColor = '';
        }
        if (gbalEl) {
          gbalEl.textContent = '—';
          gbalEl.style.background = gbalEl.style.color = gbalEl.style.borderColor = '';
        }
      }
    };

    const syncHiddenTonnageLoaded = () => {
      // Keep hidden tonnage_loaded inputs in alloc formset in sync with TT table
      document.querySelectorAll('.sdt-tt-data-row').forEach(row => {
        const idx = row.dataset.allocIdx;
        const loadedInp = row.querySelector('.sdt-tt-loaded-input');
        const hidden = document.querySelector('input[name="allocs-' + idx + '-tonnage_loaded"]');
        if (hidden && loadedInp) hidden.value = loadedInp.value;
      });
    };

    const wireAllocInputListeners = () => {
      // Hook TT rebuild on contract/tonnage input changes
      document.querySelectorAll('.alloc-contract-number, .alloc-tonnage-input').forEach(inp => {
        inp.removeEventListener('input', buildTTTable);
        inp.addEventListener('input', buildTTTable);
      });
    };

    function renumberAllocBlocks() {
      const blocks = Array.from(document.querySelectorAll('#allocList .sdt-alloc-block'))
        .filter(b => window.getComputedStyle(b).display !== 'none');
      blocks.forEach((b, i) => {
        const badge = b.querySelector('.sdt-alloc-block-badge');
        if (badge) badge.textContent = String(i + 1);
      });
    }

    function updateAllocCount() {
      const blocks = Array.from(document.querySelectorAll('#allocList .sdt-alloc-block'))
        .filter(b => window.getComputedStyle(b).display !== 'none');
      const countEl = document.getElementById('allocCount');
      if (countEl) countEl.textContent = '(' + blocks.length + ')';
    }

    function renumberRows(list, selector) {
      const rows = Array.from(list.querySelectorAll('.sdt-entry-form-row'))
        .filter(r => window.getComputedStyle(r).display !== 'none');
      rows.forEach((row, i) => {
        const el = row.querySelector(selector);
        if (el) el.textContent = String(i + 1);
      });
    }

    function updateMultipleRowsClass(listId) {
      const list = document.getElementById(listId);
      if (!list) return;
      const rows = Array.from(list.children).filter(r => window.getComputedStyle(r).display !== 'none');
      if (rows.length > 1) list.classList.add('sdt-has-multiple');
      else list.classList.remove('sdt-has-multiple');
    }

    function updateAllocPreview(idx) {
      const input = document.querySelector('#id_allocs-' + idx + '-contract_number');
      const preview = document.getElementById('allocPreview_' + idx);
      if (input && preview) preview.textContent = input.value;
    }

    function removeAllocRow(btn) {
      const block = btn.closest('.sdt-alloc-block');
      if (!block) return;
      const del = block.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (del) {
        del.checked = true;
        block.style.display = 'none';
      } else {
        block.remove();
      }
      renumberAllocBlocks();
      updateAllocCount();
      updateMultipleRowsClass('allocList');
      buildTTTable();
    }

    function removeClerkRow(btn) {
      const row = btn.closest('.sdt-entry-form-row');
      if (!row) return;
      const del = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (del) {
        del.checked = true;
        row.style.display = 'none';
      } else {
        row.remove();
      }
      const clerksList = document.getElementById('clerksList');
      if (clerksList) renumberRows(clerksList, '.sdt-entry-form-number');
    }

    function setAction(action) {
      const el = document.getElementById('actionInput');
      if (el) el.value = action;
    }

    // expose for inline handlers
    window.buildTTTable = buildTTTable;
    window.wireAllocInputListeners = wireAllocInputListeners;
    window.renumberAllocBlocks = renumberAllocBlocks;
    window.updateAllocCount = updateAllocCount;
    window.renumberRows = renumberRows;
    window.updateMultipleRowsClass = updateMultipleRowsClass;
    window.updateAllocPreview = updateAllocPreview;
    window.removeAllocRow = removeAllocRow;
    window.removeClerkRow = removeClerkRow;
    window.setAction = setAction;

    // initial wiring
    wireAllocInputListeners();
    buildTTTable();
  })();
})();
