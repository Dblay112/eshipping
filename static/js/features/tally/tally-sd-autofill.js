/**
 * Tally SD Auto-Population
 *
 * When a user enters an SD number in a tally form, this script:
 * 1. Validates the SD exists in Operations desk records
 * 2. Auto-populates fields: crop_year, vessel, agent, mk_number, destination, cocoa_type
 * 3. Shows visual feedback with icons (green tick/red X)
 * 4. Links the tally to the SD record in the database
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
    async function fetchSDDetails(sdNumber) {
        try {
            const response = await fetch(`/api/sd-details/?sd_number=${encodeURIComponent(sdNumber)}`, {
                credentials: 'same-origin',
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
            console.error('Error fetching SD details:', error);
            return { exists: false };
        }
    }

    // Show SD validation status with icon
    function showSDStatus(inputElement, status) {
        if (!inputElement) return;

        const wrapper = inputElement.parentElement;

        // Remove existing status indicators
        const existingStatus = wrapper.querySelector('.sd-status-icon');
        if (existingStatus) {
            existingStatus.remove();
        }

        // Don't show anything for "checking" status
        if (status === 'checking') return;

        // Create status icon
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
                z-index: 5;
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
                z-index: 5;
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

    // Auto-populate tally form fields from SD data
    function populateTallyFields(sdData) {
        // Populate crop year
        const cropYearField = document.getElementById('id_crop_year');
        if (cropYearField && sdData.crop_year) {
            cropYearField.value = sdData.crop_year;
        }

        // Populate vessel
        const vesselField = document.getElementById('id_vessel');
        if (vesselField && sdData.vessel_name) {
            vesselField.value = sdData.vessel_name;
        }

        // Populate agent
        const agentField = document.getElementById('id_agent');
        if (agentField && sdData.agent) {
            agentField.value = sdData.agent;
        }

        // Populate destination (from port_of_discharge)
        const destinationField = document.getElementById('id_destination');
        if (destinationField && sdData.port_of_discharge) {
            destinationField.value = sdData.port_of_discharge;
        }

        // If there are allocations, use the first one for mk_number and cocoa_type
        if (sdData.allocations && sdData.allocations.length > 0) {
            const firstAllocation = sdData.allocations[0];

            // Populate MK number
            const mkNumberField = document.getElementById('id_mk_number');
            if (mkNumberField && firstAllocation.mk_number) {
                mkNumberField.value = firstAllocation.mk_number;
            }

            // Populate cocoa type
            const cocoaTypeField = document.getElementById('id_cocoa_type');
            if (cocoaTypeField && firstAllocation.cocoa_type) {
                cocoaTypeField.value = firstAllocation.cocoa_type;
            }
        }

        // Show a brief success message
        console.log('Tally fields auto-populated from SD:', sdData.sd_number);
    }

    // Handle SD number input
    function createSDInputHandler(inputElement) {
        return debounce(async function(event) {
            const sdNumber = inputElement.value.trim();

            // Clear status if empty
            if (!sdNumber) {
                const existingStatus = inputElement.parentElement.querySelector('.sd-status-icon');
                if (existingStatus) existingStatus.remove();
                return;
            }

            // Show checking status
            showSDStatus(inputElement, 'checking');

            // Fetch SD details
            const result = await fetchSDDetails(sdNumber);

            if (result.exists) {
                // SD exists - show green tick and auto-populate fields
                showSDStatus(inputElement, 'valid');
                populateTallyFields(result.data);
            } else {
                // SD not found - show red X
                showSDStatus(inputElement, 'invalid');
            }
        }, 800); // Wait 800ms after user stops typing
    }

    // Attach auto-population to SD input field
    function attachAutoPopulation() {
        const sdInput = document.getElementById('id_sd_number');
        if (!sdInput || sdInput.dataset.tallyAutofillAttached) return;

        const handler = createSDInputHandler(sdInput);
        sdInput.addEventListener('input', handler);
        sdInput.addEventListener('blur', handler);

        // Mark as attached to avoid duplicate listeners
        sdInput.dataset.tallyAutofillAttached = 'true';
    }

    // Initialize on page load
    function init() {
        attachAutoPopulation();
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
