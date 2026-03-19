/**
 * Evacuation Form (evacuation) — extracted from evacuation_form.html
 * NOTE: Logic and variable/function names preserved.
 */

(function() {
  'use strict';

  const config = window.EVACUATION_FORM_CONFIG || {};
  let lineIndex = Number(config.lineIndex) || 0;

  function updateLinePreview(idx) {
    const sdInput = document.querySelector(`input[name="form-${idx}-sd_number"]`);
    const preview = document.getElementById(`linePreview_${idx}`);
    if (sdInput && preview) {
      preview.textContent = sdInput.value;
    }
  }

  function removeLineRow(btn) {
    const block = btn.closest('.sdt-alloc-block');
    if (block) {
      const deleteInput = block.querySelector('input[name$="-DELETE"]');
      if (deleteInput) {
        deleteInput.checked = true;
        block.style.display = 'none';
      } else {
        block.remove();
      }
    }
    updateLineCount();
  }

  function updateLineCount() {
    // Get all SD line blocks
    const allBlocks = Array.from(document.querySelectorAll('.sdt-alloc-block'));
    let visibleIndex = 0;

    // Loop through each block and renumber visible ones
    allBlocks.forEach(function(block) {
      // Check if block is hidden (has display:none set)
      const computedStyle = window.getComputedStyle(block);
      const isHidden = computedStyle.display === 'none' || block.style.display === 'none';

      if (isHidden) {
        return; // Skip hidden blocks
      }

      // Increment counter for visible blocks
      visibleIndex++;

      // Update the badge number
      const badge = block.querySelector('.sdt-alloc-block-badge');
      if (badge) {
        badge.textContent = String(visibleIndex);
      }
    });

    // Update the count in the header
    const countEl = document.getElementById('lineCount');
    if (countEl) {
      countEl.textContent = '(' + visibleIndex + ')';
    }
  }

  function addLineRow() {
    const container = document.getElementById('linesList');
    if (!container) return;

    const firstBlock = container.querySelector('.sdt-alloc-block');
    if (!firstBlock) return;

    const template = firstBlock.cloneNode(true);
    template.classList.add('sdt-alloc-block-extra');
    template.style.display = '';

    // Remove any status icons from cloned template (prevents green checkmark inheritance)
    const statusIcons = template.querySelectorAll('.sd-status-icon');
    statusIcons.forEach(icon => icon.remove());

    // Remove first-alloc class from delete button
    const removeBtn = template.querySelector('.sdt-alloc-block-remove');
    if (removeBtn) removeBtn.classList.remove('sdt-remove-first-alloc');

    // Update all inputs with new index and clear values
    template.querySelectorAll('input, select, textarea').forEach(input => {
      input.name = input.name.replace(/lines-\d+-/, `lines-${lineIndex}-`);
      input.id = input.id.replace(/id_lines-\d+-/, `id_lines-${lineIndex}-`);

      // Clear values appropriately
      if (input.type === 'checkbox') {
        input.checked = false;
      } else if (input.type === 'hidden') {
        // Clear both 'id' (primary key) and 'evacuation' (foreign key) fields
        if (input.name.match(/lines-\d+-(id|evacuation)$/)) {
          input.value = '';
        }
      } else if (input.type !== 'file') {
        // Clear visible inputs but not file inputs
        input.value = '';
      }
    });

    // Update labels
    template.querySelectorAll('label').forEach(label => {
      if (label.htmlFor) {
        label.htmlFor = label.htmlFor.replace(/id_lines-\d+-/, `id_lines-${lineIndex}-`);
      }
    });

    // Update preview span
    const preview = template.querySelector('.sdt-alloc-block-preview');
    if (preview) {
      preview.id = `linePreview_${lineIndex}`;
      preview.textContent = '';
    }

    // Update SD input
    const sdInput = template.querySelector('input[name$="-sd_number"]');
    if (sdInput) {
      sdInput.setAttribute('oninput', `updateLinePreview(${lineIndex})`);
    }

    // Update file name span
    const fileSpan = template.querySelector('.sdt-si-file-name');
    if (fileSpan) {
      fileSpan.id = `fileName_${lineIndex}`;
      fileSpan.textContent = 'No file chosen';
    }

    // Remove inline script if present
    const inlineScript = template.querySelector('script');
    if (inlineScript) inlineScript.remove();

    // Update badge
    const badge = template.querySelector('.sdt-alloc-block-badge');
    if (badge) {
      const visibleCount = Array.from(document.querySelectorAll('.sdt-alloc-block')).filter(b =>
        window.getComputedStyle(b).display !== 'none'
      ).length;
      badge.textContent = String(visibleCount + 1);
    }

    container.appendChild(template);

    // Update management form
    const totalFormsInput = document.querySelector('input[name="lines-TOTAL_FORMS"]');
    if (totalFormsInput) {
      totalFormsInput.value = String(lineIndex + 1);
    }

    lineIndex++;

    updateLineCount();
  }

  // Expose functions used by inline handlers
  window.updateLinePreview = updateLinePreview;
  window.removeLineRow = removeLineRow;

  // Initialize
  updateLineCount();

  document.getElementById('addLineBtn')?.addEventListener('click', function() {
    addLineRow();
  });

  // Global file input handler using event delegation
  document.body.addEventListener('change', function(e) {
    if (e.target.type === 'file' && e.target.name && e.target.name.includes('container_file')) {
      console.log('File input detected:', e.target.name);
      const match = e.target.name.match(/lines-(\d+)-container_file/);
      console.log('Regex match:', match);
      if (match) {
        const idx = match[1];
        console.log('Looking for span: fileName_' + idx);
        const span = document.getElementById('fileName_' + idx);
        console.log('Found span:', span);
        if (span) {
          if (e.target.files && e.target.files.length > 0) {
            console.log('Setting filename:', e.target.files[0].name);
            span.textContent = e.target.files[0].name;
            span.style.color = '#2563eb';
            span.style.fontStyle = 'italic';
            span.style.fontSize = '11px';
          } else {
            span.textContent = 'No file chosen';
            span.style.color = '';
            span.style.fontStyle = '';
          }
        } else {
          console.error('Span not found for index:', idx);
        }
      } else {
        console.error('Regex did not match:', e.target.name);
      }
    }
  });

  // Form submission debugging
  document.getElementById('evacForm')?.addEventListener('submit', function(e) {
    console.log('=== FORM SUBMISSION ===');
    const totalForms = document.querySelector('input[name="lines-TOTAL_FORMS"]')?.value;
    console.log('TOTAL_FORMS:', totalForms);

    // Log all form data
    const formData = new FormData(this);
    console.log('All form data:');
    for (let [key, value] of formData.entries()) {
      if (key.includes('sd_number') || key.includes('-id') || key.includes('-evacuation') || key.includes('TOTAL_FORMS')) {
        console.log(`  ${key} = ${value}`);
      }
    }

    // Count visible rows
    const visibleRows = document.querySelectorAll('.sdt-alloc-block:not([style*="display: none"])');
    console.log('Visible rows:', visibleRows.length);
  });

  // Add SD input listeners for preview
  document.querySelectorAll('input[name$="-sd_number"]').forEach((input, idx) => {
    input.addEventListener('input', function() {
      updateLinePreview(idx);
    });
  });
})();
