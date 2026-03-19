/**
 * SD Number Validation
 *
 * When a user enters an SD number, this script:
 * 1. Validates the SD exists in Operations desk records
 * 2. Shows visual feedback with icons only (green tick/red X)
 * 3. Does NOT auto-fill any other fields - only validates and creates link
 * 4. Handles multiple SD fields (for formsets like evacuation)
 */

(function() {
    'use strict';

    // Debounce helper (shared via static/js/form-helpers.js)
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

    // Fetch SD details from API
    async function validateSD(sdNumber) {
        try {
            const response = await fetch(`/api/sd-details/?sd_number=${encodeURIComponent(sdNumber)}`, {
                credentials: 'same-origin',  // Include authentication cookies
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            const data = await response.json();

            if (response.ok && data.exists) {
                return { exists: true, data: data };
            } else {
                return { exists: false };
            }
        } catch (error) {
            console.error('Error validating SD:', error);
            return { exists: false };
        }
    }

    // Show SD validation status with icon only
    function showSDStatus(inputElement, status) {
        if (!inputElement) return;

        // Find the wrapper container (autocomplete wrap or field container)
        const wrapper = inputElement.closest('.bk-sd-autocomplete-wrap, .sch-sd-autocomplete-wrap') || inputElement.parentElement;

        // Remove existing status indicators
        const existingStatus = wrapper.querySelector('.sd-status-icon');
        if (existingStatus) {
            existingStatus.remove();
        }

        // Don't show anything for "checking" status
        if (status === 'checking') return;

        // Create status icon positioned right next to the input border
        const iconEl = document.createElement('span');
        iconEl.className = `sd-status-icon sd-status-${status}`;

        if (status === 'valid') {
            iconEl.innerHTML = '✓';
            iconEl.style.cssText = `
                position: absolute;
                right: 12px;
                top: 50%;
                transform: translateY(-50%);
                color: #0f5132;
                font-size: 20px;
                font-weight: bold;
                pointer-events: none;
                z-index: 100;
                line-height: 1;
            `;
        } else if (status === 'invalid') {
            iconEl.innerHTML = '✗';
            iconEl.style.cssText = `
                position: absolute;
                right: 12px;
                top: 50%;
                transform: translateY(-50%);
                color: #842029;
                font-size: 20px;
                font-weight: bold;
                pointer-events: none;
                z-index: 100;
                line-height: 1;
            `;
        }

        // Ensure wrapper has position relative
        if (window.getComputedStyle(wrapper).position === 'static') {
            wrapper.style.position = 'relative';
        }

        wrapper.appendChild(iconEl);

        // Auto-remove success icon after 3 seconds
        if (status === 'valid') {
            setTimeout(() => iconEl.remove(), 3000);
        }
    }

    // Handle SD number input for a specific field
    function createSDInputHandler(inputElement) {
        return debounce(async function(event) {
            const sdNumber = inputElement.value.trim();

            // Clear status if empty
            if (!sdNumber) {
                const existingStatus = inputElement.parentElement.querySelector('.sd-status-icon');
                if (existingStatus) existingStatus.remove();
                return;
            }

            // Check if there's an autocomplete dropdown open (don't validate while dropdown is active)
            const parent = inputElement.parentElement;
            const dropdown = parent.querySelector('.bk-sd-dropdown, .sch-sd-dropdown');
            if (dropdown && dropdown.classList.contains('open')) {
                // Dropdown is open, don't show validation yet
                return;
            }

            // Show checking status (no visual indicator)
            showSDStatus(inputElement, 'checking');

            // Validate SD
            const result = await validateSD(sdNumber);

            // Double-check dropdown isn't open now (race condition)
            if (dropdown && dropdown.classList.contains('open')) {
                return;
            }

            if (result.exists) {
                // SD exists - show green tick
                showSDStatus(inputElement, 'valid');
            } else {
                // SD not found - show red X
                showSDStatus(inputElement, 'invalid');
            }
        }, 800); // Wait 800ms after user stops typing
    }

    // Attach validation to a single SD input field
    function attachValidation(inputElement) {
        if (!inputElement || inputElement.dataset.sdValidationAttached) return;

        const handler = createSDInputHandler(inputElement);
        inputElement.addEventListener('input', handler);
        inputElement.addEventListener('blur', handler);

        // Mark as attached to avoid duplicate listeners
        inputElement.dataset.sdValidationAttached = 'true';
    }

    // Find and attach validation to all SD number fields
    function attachToAllSDFields() {
        // Find all SD number input fields (handles single fields and formsets)
        const sdInputs = document.querySelectorAll(
            '[name="sd_number"], ' +
            '[name*="sd_number"], ' +
            '#id_sd_number, ' +
            '#sd_number, ' +
            'input[id*="sd_number"]'
        );

        sdInputs.forEach(attachValidation);
    }

    // Initialize on page load
    function init() {
        attachToAllSDFields();

        // Watch for dynamically added rows (for formsets)
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    attachToAllSDFields();
                }
            });
        });

        // Observe the document for new SD fields
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
