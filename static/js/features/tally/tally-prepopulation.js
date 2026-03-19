/**
 * Tally Form - SD Prepopulation
 * Auto-populates tally form fields when SD number is entered
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

  // Fetch SD details and prepopulate fields
  async function prepopulateTallyFields(sdNumber) {
    if (!sdNumber || sdNumber.trim().length < 2) {
      return;
    }

    try {
      const response = await fetch(`/api/sd-details/?sd_number=${encodeURIComponent(sdNumber.trim())}`);
      const data = await response.json();

      if (data.exists) {
        // Prepopulate fields from SD record
        const cropYearField = document.getElementById('crop_year');
        const agentField = document.getElementById('agent');
        const vesselField = document.getElementById('vessel');
        const mkNumberField = document.getElementById('mk_number');
        const destinationField = document.getElementById('destination');
        const cocoaTypeField = document.getElementById('cocoa_type');

        // Crop year
        if (cropYearField && data.crop_year) {
          cropYearField.value = data.crop_year;
        }

        // Agent
        if (agentField && data.agent) {
          agentField.value = data.agent;
        }

        // Vessel
        if (vesselField && data.vessel_name) {
          vesselField.value = data.vessel_name;
        }

        // Destination (port of discharge)
        if (destinationField && data.port_of_discharge) {
          destinationField.value = data.port_of_discharge;
        }

        // If SD has allocations, use first allocation for MK number and cocoa type
        if (data.allocations && data.allocations.length > 0) {
          const firstAlloc = data.allocations[0];

          // MK Number
          if (mkNumberField && firstAlloc.mk_number) {
            mkNumberField.value = firstAlloc.mk_number;
          }

          // Cocoa Type
          if (cocoaTypeField && firstAlloc.cocoa_type) {
            cocoaTypeField.value = firstAlloc.cocoa_type;
          }
        }

        // Show success indicator
        console.log('Tally fields prepopulated from SD:', sdNumber);
      }
    } catch (error) {
      console.error('Error fetching SD details for prepopulation:', error);
    }
  }

  // Initialize when DOM is ready
  function init() {
    const sdNumberField = document.getElementById('sd_number');

    if (!sdNumberField) {
      return;
    }

    // Debounced prepopulation (wait 1 second after user stops typing)
    const debouncedPrepopulate = debounce((value) => {
      prepopulateTallyFields(value);
    }, 1000);

    // Listen for SD number input
    sdNumberField.addEventListener('input', function(e) {
      const sdNumber = e.target.value;
      debouncedPrepopulate(sdNumber);
    });

    // Also trigger on blur (when user leaves the field)
    sdNumberField.addEventListener('blur', function(e) {
      const sdNumber = e.target.value;
      if (sdNumber && sdNumber.trim().length >= 2) {
        prepopulateTallyFields(sdNumber);
      }
    });
  }

  // Run init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
