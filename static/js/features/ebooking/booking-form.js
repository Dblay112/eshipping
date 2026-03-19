/**
 * Booking Form (ebooking) — extracted from booking_form.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.BOOKING_FORM_CONFIG || {};
  const bookingDataUrl = config.bookingDataUrl || '';
  const bookingEditUrlTemplate = config.bookingEditUrlTemplate || '';
  const sdSearchUrl = config.sdSearchUrl || '/api/sd-search/';
  const bookingData = config.bookingData || null;

  let sdCounter = 0;
  let bookingRowCounter = 0;
  let isEditMode = false;  // Flag to prevent auto-fetch in edit mode

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

  function addSdBlock() {
    const container = document.getElementById('sdBlocksContainer');
    const sdIndex = sdCounter++;

    const sdBlock = document.createElement('div');
    sdBlock.className = 'booking-sd-block';
    sdBlock.dataset.sdIndex = sdIndex;
    sdBlock.innerHTML = `
      <div class="booking-sd-header">
        <div class="booking-sd-input">
          <label class="sdt-si-label">SD Number <span class="sdt-required">*</span></label>
          <div class="bf-sd-input-wrapper">
            <input type="text" name="sd_number_${sdIndex}" class="sdt-si-input sdt-si-input-bold sd-number-input"
                   placeholder="SD100" data-sd-index="${sdIndex}" required autocomplete="off">
            <div class="bf-sd-suggestions" id="sdSuggestions_${sdIndex}"></div>
          </div>
        </div>
        <div class="booking-sd-remove-wrap">
          <div class="booking-sd-remove-label"></div>
          <button type="button" class="booking-sd-remove" onclick="removeSdBlock(${sdIndex})" title="Remove SD">
            <svg viewBox="0 0 16 16" fill="none" width="16" height="16">
              <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="booking-contracts-container" id="contractsContainer_${sdIndex}">
        <div class="bf-empty-state">
          Enter an SD number to load contracts
        </div>
      </div>
    `;

    container.appendChild(sdBlock);

    // Add event listener for SD number input (only in create mode)
    const sdInput = sdBlock.querySelector('.sd-number-input');
    const suggestionsDiv = document.getElementById(`sdSuggestions_${sdIndex}`);

    const debounce = window.cmcDebounce || function(func, wait) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    };

    // AJAX search for SD suggestions
    const debouncedSearch = debounce((query) => {
      if (!query || query.length < 2) {
        suggestionsDiv.classList.remove('bf-sd-suggestions-visible');
        return;
      }

      fetch(`${sdSearchUrl}?q=${encodeURIComponent(query)}`)
        .then(r => r.json())
        .then(data => {
          if (data.results && data.results.length > 0) {
            suggestionsDiv.innerHTML = data.results.map(sd =>
              `<div class="bf-sd-suggestion-item" data-sd="${sd.sd_number}">
                <strong>${sd.sd_number}</strong> — ${sd.vessel || 'N/A'} — ${sd.agent || 'N/A'}
              </div>`
            ).join('');
            suggestionsDiv.classList.add('bf-sd-suggestions-visible');

            // Add click handlers to suggestions
            suggestionsDiv.querySelectorAll('.bf-sd-suggestion-item').forEach(item => {
              item.addEventListener('click', function() {
                const sdNum = this.dataset.sd;
                sdInput.value = sdNum;
                suggestionsDiv.classList.remove('bf-sd-suggestions-visible');
                loadContractsForSd(sdIndex, sdNum);
              });
            });
          } else {
            suggestionsDiv.classList.remove('bf-sd-suggestions-visible');
          }
        })
        .catch(err => {
          console.error('SD search error:', err);
          suggestionsDiv.classList.remove('bf-sd-suggestions-visible');
        });
    }, 300);

    const debouncedLoadContracts = debounce((value) => {
      loadContractsForSd(sdIndex, value.trim());
    }, 800);

    sdInput.addEventListener('input', function() {
      // Don't auto-load in edit mode
      if (isEditMode) return;

      const query = this.value.trim();
      debouncedSearch(query);
      debouncedLoadContracts(query);
    });

    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
      if (!sdInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
        suggestionsDiv.classList.remove('bf-sd-suggestions-visible');
      }
    });
  }

  function removeSdBlock(sdIndex) {
    const block = document.querySelector(`[data-sd-index="${sdIndex}"]`);
    if (block) block.remove();
  }

  function loadContractsForSd(sdIndex, sdNumber) {
    const container = document.getElementById(`contractsContainer_${sdIndex}`);

    if (!sdNumber) {
      container.innerHTML = '<div class="bf-empty-state">Enter an SD number to load contracts</div>';
      return;
    }

    // Find SD record by number
    fetch(`/api/sd-details/?sd_number=${encodeURIComponent(sdNumber)}`)
      .then(r => r.json())
      .then(data => {
        if (!data.exists || !data.id) {
          container.innerHTML = '<div class="bf-error-state-bold">⚠ SD not found in operations records. Please create the SD first.</div>';
          return;
        }

        // Load allocations
        fetch(`/operations/${data.id}/allocations/`)
          .then(r => r.json())
          .then(allocData => {
            if (allocData.allocations && allocData.allocations.length > 0) {
              container.innerHTML = '';
              allocData.allocations.forEach((alloc, contractIdx) => {
                addContractSection(sdIndex, contractIdx, alloc);
              });
            } else {
              container.innerHTML = '<div class="bf-empty-state">No contracts found for this SD</div>';
            }
          });
      })
      .catch(err => {
        console.error('Error:', err);
        container.innerHTML = '<div class="bf-error-state">Error loading contracts</div>';
      });
  }

  function addContractSection(sdIndex, contractIdx, alloc) {
    const container = document.getElementById(`contractsContainer_${sdIndex}`);

    const section = document.createElement('div');
    section.className = 'booking-contract-section';
    section.dataset.contractIdx = contractIdx;
    section.innerHTML = `
      <div class="booking-contract-header">
        <span>${alloc.label || 'Contract'} — ${alloc.contract_number}</span>
        <span class="bf-contract-header-info">
          Allocated: ${cleanDecimal(alloc.allocated_tonnage)} MT |
          Balance: <span id="balance_${sdIndex}_${contractIdx}" class="bf-balance-display" data-current-balance="${alloc.balance}" data-allocated="${alloc.allocated_tonnage}">${cleanDecimal(alloc.balance)}</span> MT
        </span>
      </div>
      <div class="booking-contract-rows" id="contractRows_${sdIndex}_${contractIdx}">
        <input type="hidden" name="contract_number_${sdIndex}_${contractIdx}" value="${alloc.contract_number}">
      </div>
    `;

    container.appendChild(section);

    // Add first booking row
    addBookingRow(sdIndex, contractIdx);
  }

  function addBookingRow(sdIndex, contractIdx) {
    const container = document.getElementById(`contractRows_${sdIndex}_${contractIdx}`);
    const rowIndex = bookingRowCounter++;

    const row = document.createElement('div');
    row.className = 'booking-row';
    row.dataset.rowIndex = rowIndex;
    row.innerHTML = `
      <div class="booking-row-field">
        <label>Booking Number</label>
        <input type="text" name="booking_number_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input" placeholder="BKG-2025-001">
      </div>
      <div class="booking-row-field">
        <label>Bill of Lading No.</label>
        <input type="text" name="bill_number_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input" placeholder="BL-2025-001">
      </div>
      <div class="booking-row-field">
        <label>Agent</label>
        <input type="text" name="agent_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input" placeholder="MSC">
      </div>
      <div class="booking-row-field">
        <label>Vessel</label>
        <input type="text" name="vessel_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input" placeholder="MSC IKARIA VI">
      </div>
      <div class="booking-row-field">
        <label>Tonnage (MT)</label>
        <input type="text" inputmode="decimal" name="tonnage_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input tonnage-input" placeholder="0" data-sd-index="${sdIndex}" data-contract-idx="${contractIdx}" oninput="updateBookingBalance(${sdIndex}, ${contractIdx})">
      </div>
      <div class="booking-row-field">
        <label>File</label>
        <div class="bf-file-wrapper">
          <label class="booking-file-btn bf-file-label" for="file_${sdIndex}_${contractIdx}_${rowIndex}">
            <svg viewBox="0 0 16 16" fill="none" width="12" height="12">
              <path d="M8 2v8M5 5l3-3 3 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Attach
          </label>
          <span id="fileName_${sdIndex}_${contractIdx}_${rowIndex}" class="bf-file-name">No file</span>
          <input type="file" name="file_${sdIndex}_${contractIdx}_${rowIndex}" id="file_${sdIndex}_${contractIdx}_${rowIndex}" accept=".pdf" class="bf-file-input-hidden" onchange="updateBookingFileName(${sdIndex}, ${contractIdx}, ${rowIndex})">
        </div>
      </div>
      <div>
        <button type="button" class="booking-row-remove" onclick="removeBookingRow(${rowIndex})" title="Remove row">
          <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
            <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    `;

    container.appendChild(row);

    // Add blur event to tonnage input to clean decimal display
    const tonnageInput = row.querySelector('.tonnage-input');
    if (tonnageInput) {
      tonnageInput.addEventListener('blur', function() {
        if (this.value) {
          this.value = cleanDecimal(this.value);
        }
      });
    }

    // Add "Add Row" button if it doesn't exist
    if (!container.querySelector('.booking-add-row-btn')) {
      const addBtn = document.createElement('button');
      addBtn.type = 'button';
      addBtn.className = 'booking-add-row-btn';
      addBtn.innerHTML = `
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
        Add another booking for this contract
      `;
      addBtn.onclick = () => addBookingRow(sdIndex, contractIdx);
      container.appendChild(addBtn);
    }
  }

  function removeBookingRow(rowIndex) {
    const row = document.querySelector(`[data-row-index="${rowIndex}"]`);
    if (row) {
      // Get the contract info before removing
      const tonnageInput = row.querySelector('.tonnage-input');
      if (tonnageInput) {
        const sdIndex = tonnageInput.dataset.sdIndex;
        const contractIdx = tonnageInput.dataset.contractIdx;
        row.remove();
        // Update balance after removing row
        updateBookingBalance(sdIndex, contractIdx);
      } else {
        row.remove();
      }
    }
  }

  function updateBookingBalance(sdIndex, contractIdx) {
    const balanceSpan = document.getElementById(`balance_${sdIndex}_${contractIdx}`);
    if (!balanceSpan) return;

    const allocated = parseFloat(balanceSpan.dataset.allocated) || 0;
    const currentBalance = parseFloat(balanceSpan.dataset.currentBalance) || 0;

    // Find all tonnage inputs for this contract
    const container = document.getElementById(`contractRows_${sdIndex}_${contractIdx}`);
    if (!container) return;

    const tonnageInputs = container.querySelectorAll('.tonnage-input');
    let totalBooked = 0;
    let hasError = false;

    tonnageInputs.forEach(input => {
      let value = parseFloat(input.value) || 0;

      // Enforce: 0 <= tonnage <= allocated (per contract)
      if (value < 0) {
        value = 0;
        input.value = '0';
        hasError = true;
      }

      totalBooked += value;
    });

    // Check if total exceeds allocated
    if (totalBooked > allocated) {
      // Find the input that was just changed and clamp it
      tonnageInputs.forEach(input => {
        if (document.activeElement === input) {
          const otherTotal = totalBooked - (parseFloat(input.value) || 0);
          const maxAllowed = allocated - otherTotal;
          if (maxAllowed < 0) {
            input.value = '0';
          } else {
            input.value = String(maxAllowed.toFixed(4));
          }
        }
      });
      // Recalculate after clamping
      totalBooked = 0;
      tonnageInputs.forEach(input => {
        totalBooked += parseFloat(input.value) || 0;
      });
    }

    // Calculate new balance: current balance - total booked
    const newBalance = currentBalance - totalBooked;

    // Update the balance display with clean decimal formatting
    balanceSpan.textContent = cleanDecimal(newBalance);

    // Visual feedback: red if negative, orange if zero, green if positive
    if (newBalance < 0) {
      balanceSpan.style.color = '#c62828';
    } else if (newBalance === 0) {
      balanceSpan.style.color = '#e65100';
    } else {
      balanceSpan.style.color = '#2e7d32';
    }
  }

  function updateBookingFileName(sdIndex, contractIdx, rowIndex) {
    const fileInput = document.getElementById(`file_${sdIndex}_${contractIdx}_${rowIndex}`);
    const fileNameSpan = document.getElementById(`fileName_${sdIndex}_${contractIdx}_${rowIndex}`);

    if (fileInput && fileNameSpan) {
      if (fileInput.files && fileInput.files.length > 0) {
        fileNameSpan.textContent = fileInput.files[0].name;
        fileNameSpan.style.color = '#1565c0';
        fileNameSpan.style.fontWeight = '600';
      } else {
        // Don't change the text if no new file selected (preserve existing file name)
        // Only reset if it was showing "No file"
        if (fileNameSpan.textContent === 'No file') {
          fileNameSpan.textContent = 'No file';
          fileNameSpan.style.color = '#888';
          fileNameSpan.style.fontWeight = '400';
        }
      }
    }
  }

  // Booking form prepopulation feature
  const debounceCheckExistingBooking = window.cmcDebounce || function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  };

  const debouncedCheckExistingBooking = debounceCheckExistingBooking((sdNumber) => {
    fetch(`${bookingDataUrl}?sd_number=${encodeURIComponent(sdNumber)}`)
      .then(response => response.json())
      .then(data => {
        if (data.exists) {
          // Redirect to edit page for existing booking
          window.location.href = bookingEditUrlTemplate.replace('0', data.booking_id);
        }
      })
      .catch(error => {
        console.error('Error checking existing booking:', error);
      });
  }, 800);

  function checkExistingBooking(sdInput, sdIndex) {
    const sdNumber = sdInput.value.trim();

    if (!sdNumber) return;

    debouncedCheckExistingBooking(sdNumber);
  }

  function prepopulateBookingForm(sdIndex, bookingData) {
    console.log('Prepopulating form with data:', bookingData);

    // Find the contracts container for this SD
    const contractsContainer = document.getElementById(`contractsContainer_${sdIndex}`);
    if (!contractsContainer) {
      console.error('Contracts container not found for SD index:', sdIndex);
      return;
    }

    // Clear existing contracts
    contractsContainer.innerHTML = '';

    // Prepopulate each contract
    bookingData.contracts.forEach((contract, contractIdx) => {
      console.log('Adding contract:', contract.contract_number);

      // Add contract section with proper parameters
      addContractSection(sdIndex, contractIdx, {
        contract_number: contract.contract_number,
        allocated_tonnage: 0,
        balance: 0,
        label: 'Contract'
      });

      // Wait for DOM to update, then populate booking rows
      setTimeout(() => {
        contract.bookings.forEach((booking, bookingIdx) => {
          console.log('Processing booking:', booking.booking_number);

          if (bookingIdx > 0) {
            // Add additional rows if needed
            addBookingRow(sdIndex, contractIdx);
          }

          // Wait for row to be added, then populate
          setTimeout(() => {
            const container = document.getElementById(`contractRows_${sdIndex}_${contractIdx}`);
            if (container) {
              const rows = container.querySelectorAll('.booking-row');
              const row = rows[bookingIdx];

              if (row) {
                // Populate fields
                const bookingNumberInput = row.querySelector('input[name*="booking_number"]');
                const billNumberInput = row.querySelector('input[name*="bill_number"]');
                const agentInput = row.querySelector('input[name*="agent"]');
                const vesselInput = row.querySelector('input[name*="vessel"]');
                const tonnageInput = row.querySelector('input[name*="tonnage"]');

                if (bookingNumberInput) bookingNumberInput.value = booking.booking_number || '';
                if (billNumberInput) billNumberInput.value = booking.bill_number || '';
                if (agentInput) agentInput.value = booking.agent || bookingData.agent || '';
                if (vesselInput) vesselInput.value = booking.vessel || bookingData.vessel || '';
                if (tonnageInput) tonnageInput.value = booking.tonnage || '';

                console.log('Populated row with:', booking);
              } else {
                console.error('Row not found at index:', bookingIdx);
              }
            } else {
              console.error('Container not found:', `contractRows_${sdIndex}_${contractIdx}`);
            }
          }, 50 * bookingIdx); // Stagger the population
        });
      }, 100);
    });
  }

  // Load existing booking data for edit mode
  function loadExistingBookingData(bookingData) {
    console.log('Loading booking data for edit mode:', bookingData);

    // Use the same addSdBlock function as create mode
    addSdBlock();

    // Get the SD index that was just created
    const sdIndex = sdCounter - 1;

    // Set the SD number value
    const sdInput = document.querySelector(`input[name="sd_number_${sdIndex}"]`);
    if (sdInput) {
      sdInput.value = bookingData.sd_number;
      sdInput.readOnly = true; // Make it readonly in edit mode
    }

    // Hide the remove button in edit mode
    const removeBtn = document.querySelector(`[data-sd-index="${sdIndex}"] .booking-sd-remove`);
    if (removeBtn) {
      removeBtn.classList.add('bf-hidden');
    }

    // Load contracts using the same function as create mode
    loadContractsForSd(sdIndex, bookingData.sd_number);

    // Wait for contracts to load, then populate booking data
    setTimeout(() => {
      populateBookingData(sdIndex, bookingData);
    }, 1000);
  }

  // Populate booking data into loaded contract sections
  function populateBookingData(sdIndex, bookingData) {
    console.log('Populating booking data into contracts');

    bookingData.contracts.forEach((contract, contractIdx) => {
      const rowsContainer = document.getElementById(`contractRows_${sdIndex}_${contractIdx}`);
      if (!rowsContainer) {
        console.error(`Container not found: contractRows_${sdIndex}_${contractIdx}`);
        return;
      }

      // Remove the default first row that was added by addContractSection
      const existingRows = rowsContainer.querySelectorAll('.booking-row');
      existingRows.forEach(row => row.remove());

      // Add booking rows with data
      contract.bookings.forEach((booking, bookingIdx) => {
        const rowIndex = bookingRowCounter++;

        const row = document.createElement('div');
        row.className = 'booking-row';
        row.dataset.rowIndex = rowIndex;

        row.innerHTML = `
          <input type="hidden" name="detail_id_${sdIndex}_${contractIdx}_${rowIndex}" value="${booking.detail_id || ''}">
          <div class="booking-row-field">
            <label>Booking Number</label>
            <input type="text" name="booking_number_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input" placeholder="BKG-2025-001" value="${booking.booking_number || ''}">
          </div>
          <div class="booking-row-field">
            <label>Bill of Lading No.</label>
            <input type="text" name="bill_number_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input" placeholder="BL-2025-001" value="${booking.bill_number || ''}">
          </div>
          <div class="booking-row-field">
            <label>Agent</label>
            <input type="text" name="agent_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input" placeholder="MSC" value="${booking.agent || bookingData.agent || ''}">
          </div>
          <div class="booking-row-field">
            <label>Vessel</label>
            <input type="text" name="vessel_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input" placeholder="MSC IKARIA VI" value="${booking.vessel || bookingData.vessel || ''}">
          </div>
          <div class="booking-row-field">
            <label>Tonnage (MT)</label>
            <input type="text" inputmode="decimal" name="tonnage_${sdIndex}_${contractIdx}_${rowIndex}" class="booking-row-input tonnage-input" placeholder="0" value="${cleanDecimal(booking.tonnage)}" data-sd-index="${sdIndex}" data-contract-idx="${contractIdx}">
          </div>
          <div class="booking-row-field">
            <label>File</label>
            <div class="bf-file-wrapper-relative">
              <label class="booking-file-btn" for="file_${sdIndex}_${contractIdx}_${rowIndex}">
                <svg viewBox="0 0 16 16" fill="none" width="12" height="12">
                  <path d="M8 2v8M5 5l3-3 3 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </label>
              <input type="file" name="file_${sdIndex}_${contractIdx}_${rowIndex}" id="file_${sdIndex}_${contractIdx}_${rowIndex}" accept=".pdf" class="bf-file-input-hidden" onchange="updateBookingFileName(${sdIndex}, ${contractIdx}, ${rowIndex})">
              <div class="bf-file-name-edit" id="fileName_${sdIndex}_${contractIdx}_${rowIndex}">${booking.file_name || 'No file'}</div>
            </div>
          </div>
          <div>
            <button type="button" class="booking-row-remove" onclick="removeBookingRow(${rowIndex})" title="Remove row">
              <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
                <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        `;

        rowsContainer.appendChild(row);

        // Add event listener for tonnage input
        const tonnageInput = row.querySelector('.tonnage-input');
        if (tonnageInput) {
          tonnageInput.addEventListener('input', function() {
            updateBookingBalance(sdIndex, contractIdx);
          });

          // Clean decimal display on blur
          tonnageInput.addEventListener('blur', function() {
            if (this.value) {
              this.value = cleanDecimal(this.value);
            }
          });
        }
      });

      // Update balance after loading all rows
      setTimeout(() => updateBookingBalance(sdIndex, contractIdx), 0);
    });
  }

  // Expose functions used by inline onclick handlers
  window.addSdBlock = addSdBlock;
  window.removeSdBlock = removeSdBlock;
  window.loadContractsForSd = loadContractsForSd;
  window.addContractSection = addContractSection;
  window.addBookingRow = addBookingRow;
  window.removeBookingRow = removeBookingRow;
  window.updateBookingBalance = updateBookingBalance;
  window.updateBookingFileName = updateBookingFileName;
  window.checkExistingBooking = checkExistingBooking;
  window.prepopulateBookingForm = prepopulateBookingForm;
  window.loadExistingBookingData = loadExistingBookingData;
  window.populateBookingData = populateBookingData;

  // Add initial SD block on page load
  document.addEventListener('DOMContentLoaded', function() {
    if (bookingData) {
      // Edit mode - load existing booking data
      isEditMode = true;  // Set flag to prevent auto-fetch
      loadExistingBookingData(bookingData);
    } else {
      // Create mode - add empty SD block
      addSdBlock();
    }
  });

  const addBtn = document.getElementById('addSdBtn');
  if (addBtn) {
    addBtn.addEventListener('click', function() {
      addSdBlock();
    });
  }

  // Add event listeners to SD number inputs when they're created (only in create mode)
  document.addEventListener('input', function(e) {
    // Don't trigger in edit mode
    if (isEditMode) return;

    if (e.target && e.target.name && e.target.name.startsWith('sd_number_')) {
      const sdIndex = e.target.name.split('_')[2];
      checkExistingBooking(e.target, sdIndex);
    }
  });
})();
