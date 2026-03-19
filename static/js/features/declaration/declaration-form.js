/**
 * Declaration Form (declaration) — extracted from declaration_form.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.DECLARATION_FORM_CONFIG || {};
  const declarationData = config.declarationData || null;

  let isEditMode = false;

  // Helper function to clean decimal display (remove trailing zeros)
  function cleanDecimal(value) {
    if (value === null || value === undefined || value === '') return '';
    const num = parseFloat(value);
    if (isNaN(num)) return '';
    // Convert to string and remove trailing zeros after decimal point
    let str = num.toFixed(4);
    if (str.includes('.')) {
      str = str.replace(/\.?0+$/, '');
    }
    return str;
  }

  const fetchWithTimeout = (url, timeout = 10000) => {
    return Promise.race([
      fetch(url, {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      }),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout')), timeout)
      )
    ]);
  };

  function updateFileName(idx, input) {
    const fileName = input.files[0]?.name || 'No file';
    document.getElementById(`fileName_${idx}`).textContent = fileName;
  }

  function updateBalance(idx) {
    const tonnageInput = document.getElementById(`tonnage_${idx}`);
    const balanceInput = document.getElementById(`balance_${idx}`);
    const errEl = document.getElementById(`tonnageError_${idx}`);

    if (!tonnageInput || !balanceInput) return;

    const allocated = parseFloat(balanceInput.dataset.allocated) || 0;
    const currentBalance = parseFloat(balanceInput.dataset.currentBalance) || 0;
    let tonnageDeclared = parseFloat(tonnageInput.value);

    // Handle empty input
    if (isNaN(tonnageDeclared)) {
      tonnageDeclared = 0;
      if (errEl) {
        errEl.style.display = 'none';
        errEl.textContent = '';
      }
    }

    // Enforce: 0 <= tonnage <= allocated (per contract)
    if (tonnageDeclared < 0) {
      tonnageDeclared = 0;
      tonnageInput.value = '0';
      if (errEl) {
        errEl.textContent = 'Tonnage cannot be negative.';
        errEl.style.display = 'block';
      }
    } else if (tonnageDeclared > allocated) {
      tonnageDeclared = allocated;
      tonnageInput.value = String(allocated);
      if (errEl) {
        errEl.textContent = `Cannot declare more than allocated (${cleanDecimal(allocated)} MT).`;
        errEl.style.display = 'block';
      }
    } else if (errEl) {
      errEl.style.display = 'none';
      errEl.textContent = '';
    }

    // Calculate new balance display: current balance - tonnage
    // (this is display only; server-side validation enforces allocated rule)
    const newBalance = currentBalance - tonnageDeclared;

    balanceInput.value = cleanDecimal(newBalance);

    if (newBalance < 0) {
      balanceInput.style.color = '#c62828';
      balanceInput.style.fontWeight = '700';
    } else if (newBalance === 0) {
      balanceInput.style.color = '#e65100';
      balanceInput.style.fontWeight = '700';
    } else {
      balanceInput.style.color = '#2e7d32';
      balanceInput.style.fontWeight = '700';
    }
  }

  function loadExistingDeclarationData(declarationData) {
    const sdInput = document.getElementById('id_sd_number');
    const allocCard = document.getElementById('allocationsCard');
    const allocList = document.getElementById('allocationsList');
    const submitBtn = document.getElementById('submitBtn');

    // Set SD number
    sdInput.value = declarationData.sd_number;

    // Show loading indicator
    allocList.innerHTML = '<div class="sdt-empty-state"><p class="sdt-empty-text" style="color:#7d5a3b;">Loading allocations...</p></div>';
    allocCard.style.display = 'block';

    // Fetch allocations for this SD
    fetchWithTimeout(`/operations/${declarationData.sd_id}/allocations/`)
      .then(r => {
        if (!r.ok) throw new Error('Failed to load allocations');
        return r.json();
      })
      .then(data => {
        if (data.allocations && data.allocations.length > 0) {
          allocList.innerHTML = '';

          data.allocations.forEach((alloc, idx) => {
            // Find existing declaration for this allocation
            const existingDecl = declarationData.declarations[idx] || {};

            // Balance = Allocated - Current Declaration Tonnage (simple, no summing)
            // API returns allocated tonnage as balance, we just use it directly
            const currentBalance = parseFloat(alloc.balance);

            const block = document.createElement('div');
            block.className = 'sdt-alloc-block' + (idx > 0 ? ' sdt-alloc-block-extra' : '');
            block.innerHTML = `
              <div class="sdt-alloc-block-header">
                <span class="sdt-alloc-block-badge">${alloc.label || (idx + 1)}</span>
                <span class="sdt-alloc-block-preview">${alloc.contract_number || 'Contract ' + (idx + 1)}</span>
              </div>

              <!-- Band A: Contract Info (Read-only) -->
              <div class="sdt-si-band">
                <div class="sdt-si-band-label"><span>Contract Info</span></div>
                <div class="sdt-si-fields">
                  <div class="sdt-si-field" style="flex:0 0 70px;">
                    <label class="sdt-si-label">Label</label>
                    <input type="text" value="${alloc.label || '—'}" class="sdt-si-input" readonly>
                  </div>
                  <div class="sdt-si-field" style="flex:1.5;">
                    <label class="sdt-si-label">Contract No.</label>
                    <input type="text" value="${alloc.contract_number || '—'}" class="sdt-si-input sdt-si-mono" readonly>
                  </div>
                  <div class="sdt-si-field" style="flex:0 0 120px;">
                    <label class="sdt-si-label">Allocated (MT)</label>
                    <input type="text" value="${cleanDecimal(alloc.allocated_tonnage)}" class="sdt-si-input sdt-si-num" readonly>
                  </div>
                  <div class="sdt-si-field" style="flex:0 0 120px;">
                    <label class="sdt-si-label">Balance (MT)</label>
                    <input type="text" value="${cleanDecimal(currentBalance)}" class="sdt-si-input sdt-si-num" id="balance_${idx}" readonly data-allocated="${alloc.allocated_tonnage}" data-current-balance="${currentBalance}">
                  </div>
                </div>
              </div>

              <!-- Band B: Declaration Details -->
              <div class="sdt-si-band sdt-si-band-last">
                <div class="sdt-si-band-label"><span>Declaration Details</span></div>
                <div class="sdt-si-fields">
                  <div class="sdt-si-field" style="flex:1;">
                    <label class="sdt-si-label">Agent</label>
                    <input type="text" name="agent_${idx}" class="sdt-si-input sdt-si-upper" placeholder="MSC" value="${existingDecl.agent || alloc.agent || ''}">
                  </div>
                  <div class="sdt-si-field" style="flex:1.5;">
                    <label class="sdt-si-label">Declaration Number</label>
                    <input type="text" name="declaration_number_${idx}" class="sdt-si-input sdt-si-mono" placeholder="DECL-2025-001" value="${existingDecl.declaration_number || ''}">
                  </div>
                  <div class="sdt-si-field" style="flex:0 0 140px;">
                    <label class="sdt-si-label">Tonnage Declared (MT)</label>
                    <input type="number" name="tonnage_${idx}" class="sdt-si-input sdt-si-num" min="0" max="${cleanDecimal(alloc.allocated_tonnage)}" placeholder="0" id="tonnage_${idx}" value="${existingDecl.tonnage || ''}" oninput="updateBalance(${idx})">
                    <p class="sdt-form-error" id="tonnageError_${idx}" style="display:none;"></p>
                  </div>
                  <div class="sdt-si-field sdt-si-field-doc">
                    <label class="sdt-si-label">Declaration PDF <span class="sdt-si-optional">optional</span></label>
                    <div class="sdt-si-file-row">
                      <label class="sdt-si-file-btn" for="declaration_pdf_${idx}">
                        <svg viewBox="0 0 16 16" fill="none"><path d="M8 2v8M5 5l3-3 3 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 12h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
                        ${existingDecl.has_file ? 'Replace' : 'Attach'}
                      </label>
                      <span class="sdt-si-file-name" id="fileName_${idx}">${existingDecl.has_file ? 'File attached' : 'No file'}</span>
                      <input type="file" name="declaration_pdf_${idx}" id="declaration_pdf_${idx}" accept=".pdf" style="display:none" onchange="updateFileName(${idx}, this)">
                    </div>
                  </div>
                </div>
                <input type="hidden" name="allocation_id_${idx}" value="${alloc.id}">
                <input type="hidden" name="contract_number_${idx}" value="${alloc.contract_number}">
                ${existingDecl.declaration_id ? `<input type="hidden" name="declaration_id_${idx}" value="${existingDecl.declaration_id}">` : ''}
              </div>
            `;
            allocList.appendChild(block);

            // Trigger balance calculation after adding the block to show correct initial balance
            setTimeout(() => updateBalance(idx), 0);
          });

          document.getElementById('allocCount').textContent = `(${data.allocations.length})`;
          allocCard.style.display = 'block';
          submitBtn.disabled = false;
        }
      })
      .catch(err => {
        console.error('Error loading allocations:', err);
        let errorMsg = 'Error loading allocations. ';
        if (err.message === 'Request timeout') {
          errorMsg += 'Request timed out. Please check your internet connection and try again.';
        } else if (err.message === 'Failed to fetch') {
          errorMsg += 'Network error. Please check your internet connection.';
        } else {
          errorMsg += 'Please try again or contact support.';
        }
        allocList.innerHTML = `<div class="sdt-empty-state"><p class="sdt-empty-text" style="color:#c62828;">${errorMsg}</p></div>`;
        allocCard.style.display = 'block';
        submitBtn.disabled = true;
      });
  }

  const sdInput = document.getElementById('id_sd_number');
  if (sdInput) {
    sdInput.addEventListener('change', function() {
      // Prevent fetching allocations if we're in edit mode
      if (isEditMode) return;

      const sdNumber = this.value.trim();
      const allocCard = document.getElementById('allocationsCard');
      const allocList = document.getElementById('allocationsList');
      const submitBtn = document.getElementById('submitBtn');

      if (!sdNumber) {
        allocCard.style.display = 'none';
        submitBtn.disabled = true;
        return;
      }

      // Show loading indicator
      allocList.innerHTML = '<div class="sdt-empty-state"><p class="sdt-empty-text" style="color:#7d5a3b;">Loading allocations...</p></div>';
      allocCard.style.display = 'block';
      submitBtn.disabled = true;

      // First, fetch SD details to get the ID
      fetchWithTimeout(`/api/sd-details/?sd_number=${encodeURIComponent(sdNumber)}`)
        .then(r => {
          if (!r.ok) throw new Error('Network response was not ok');
          return r.json();
        })
        .then(sdData => {
          if (!sdData.exists || !sdData.id) {
            allocList.innerHTML = '<div class="sdt-empty-state"><p class="sdt-empty-text" style="color:#c62828;">SD not found in operations records.</p></div>';
            allocCard.style.display = 'block';
            submitBtn.disabled = true;
            return null;
          }

          // Now fetch allocations for this SD
          return fetchWithTimeout(`/operations/${sdData.id}/allocations/`);
        })
        .then(r => {
          if (!r) return null;
          if (!r.ok) throw new Error('Failed to load allocations');
          return r.json();
        })
        .then(data => {
          if (!data) return;

          if (data.allocations && data.allocations.length > 0) {
            allocList.innerHTML = '';
            data.allocations.forEach((alloc, idx) => {
              const block = document.createElement('div');
              block.className = 'sdt-alloc-block' + (idx > 0 ? ' sdt-alloc-block-extra' : '');
              block.innerHTML = `
                <div class="sdt-alloc-block-header">
                  <span class="sdt-alloc-block-badge">${alloc.label || (idx + 1)}</span>
                  <span class="sdt-alloc-block-preview">${alloc.contract_number || 'Contract ' + (idx + 1)}</span>
                </div>

                <!-- Band A: Contract Info (Read-only) -->
                <div class="sdt-si-band">
                  <div class="sdt-si-band-label"><span>Contract Info</span></div>
                  <div class="sdt-si-fields">
                    <div class="sdt-si-field" style="flex:0 0 70px;">
                      <label class="sdt-si-label">Label</label>
                      <input type="text" value="${alloc.label || '—'}" class="sdt-si-input" readonly>
                    </div>
                    <div class="sdt-si-field" style="flex:1.5;">
                      <label class="sdt-si-label">Contract No.</label>
                      <input type="text" value="${alloc.contract_number || '—'}" class="sdt-si-input sdt-si-mono" readonly>
                    </div>
                    <div class="sdt-si-field" style="flex:0 0 120px;">
                      <label class="sdt-si-label">Allocated (MT)</label>
                      <input type="text" value="${cleanDecimal(alloc.allocated_tonnage)}" class="sdt-si-input sdt-si-num" readonly>
                    </div>
                    <div class="sdt-si-field" style="flex:0 0 120px;">
                      <label class="sdt-si-label">Balance (MT)</label>
                      <input type="text" value="${cleanDecimal(alloc.balance)}" class="sdt-si-input sdt-si-num" id="balance_${idx}" readonly data-allocated="${alloc.allocated_tonnage}" data-current-balance="${alloc.balance}">
                    </div>
                  </div>
                </div>

                <!-- Band B: Declaration Details -->
                <div class="sdt-si-band sdt-si-band-last">
                  <div class="sdt-si-band-label"><span>Declaration Details</span></div>
                  <div class="sdt-si-fields">
                    <div class="sdt-si-field" style="flex:1;">
                      <label class="sdt-si-label">Agent</label>
                      <input type="text" name="agent_${idx}" class="sdt-si-input sdt-si-upper" placeholder="MSC" value="${alloc.agent || ''}">
                    </div>
                    <div class="sdt-si-field" style="flex:1.5;">
                      <label class="sdt-si-label">Declaration Number</label>
                      <input type="text" name="declaration_number_${idx}" class="sdt-si-input sdt-si-mono" placeholder="DECL-2025-001">
                    </div>
                    <div class="sdt-si-field" style="flex:0 0 140px;">
                      <label class="sdt-si-label">Tonnage Declared (MT)</label>
                      <input type="number" name="tonnage_${idx}" class="sdt-si-input sdt-si-num" min="0" max="${cleanDecimal(alloc.allocated_tonnage)}" placeholder="0" id="tonnage_${idx}" oninput="updateBalance(${idx})">
                      <p class="sdt-form-error" id="tonnageError_${idx}" style="display:none;"></p>
                    </div>
                    <div class="sdt-si-field sdt-si-field-doc">
                      <label class="sdt-si-label">Declaration PDF <span class="sdt-si-optional">optional</span></label>
                      <div class="sdt-si-file-row">
                        <label class="sdt-si-file-btn" for="declaration_pdf_${idx}">
                          <svg viewBox="0 0 16 16" fill="none"><path d="M8 2v8M5 5l3-3 3 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 12h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
                          Attach
                        </label>
                        <span class="sdt-si-file-name" id="fileName_${idx}">No file</span>
                        <input type="file" name="declaration_pdf_${idx}" id="declaration_pdf_${idx}" accept=".pdf" style="display:none" onchange="updateFileName(${idx}, this)">
                      </div>
                    </div>
                  </div>
                  <input type="hidden" name="allocation_id_${idx}" value="${alloc.id}">
                  <input type="hidden" name="contract_number_${idx}" value="${alloc.contract_number}">
                </div>
              `;
              allocList.appendChild(block);
            });

            document.getElementById('allocCount').textContent = `(${data.allocations.length})`;
            allocCard.style.display = 'block';
            submitBtn.disabled = false;
          } else {
            allocList.innerHTML = '<div class="sdt-empty-state"><p class="sdt-empty-text">No contract allocations found for this SD.</p></div>';
            allocCard.style.display = 'block';
            submitBtn.disabled = true;
          }
        })
        .catch(err => {
          console.error('Error loading allocations:', err);
          let errorMsg = 'Error loading allocations. ';
          if (err.message === 'Request timeout') {
            errorMsg += 'Request timed out. Please check your internet connection and try again.';
          } else if (err.message === 'Failed to fetch') {
            errorMsg += 'Network error. Please check your internet connection.';
          } else {
            errorMsg += 'Please try again or contact support.';
          }
          allocList.innerHTML = `<div class="sdt-empty-state"><p class="sdt-empty-text" style="color:#c62828;">${errorMsg}</p></div>`;
          allocCard.style.display = 'block';
          submitBtn.disabled = true;
        });
    });
  }

  // Expose functions used by inline oninput/onchange handlers
  window.updateFileName = updateFileName;
  window.updateBalance = updateBalance;
  window.loadExistingDeclarationData = loadExistingDeclarationData;

  // Trigger on page load
  window.addEventListener('DOMContentLoaded', function() {
    if (declarationData) {
      // Edit mode - load existing declaration data
      isEditMode = true;
      loadExistingDeclarationData(declarationData);
    } else {
      // Create mode - trigger change if SD is pre-selected
      const sdSelect = document.getElementById('id_sd_record');
      if (sdSelect && sdSelect.value) {
        sdSelect.dispatchEvent(new Event('change'));
      }
    }
  });
})();
