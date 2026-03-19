/**
 * Auto-prefix for SD and MK number fields
 *
 * Automatically adds "SD" prefix to SD number fields when user types only numbers
 * Automatically adds "MK " prefix to MK number fields when user types only numbers
 *
 * Examples:
 * - User types "444" in SD field → becomes "SD444"
 * - User types "042519" in MK field → becomes "MK 042519"
 */

(function() {
    'use strict';

    /**
     * Format SD number - add "SD" prefix if missing
     */
    function formatSDNumber(value) {
        // Remove whitespace
        value = value.trim();

        // If empty, return as is
        if (!value) return value;

        // If already starts with "SD" (case insensitive), return as is
        if (/^SD/i.test(value)) {
            // Ensure "SD" is uppercase
            return value.replace(/^sd/i, 'SD');
        }

        // If it's just numbers, add "SD" prefix
        if (/^\d+/.test(value)) {
            return 'SD' + value;
        }

        // Otherwise return as is (user might be typing something custom)
        return value;
    }

    /**
     * Format MK number - add "MK " prefix if missing
     */
    function formatMKNumber(value) {
        // Remove extra whitespace
        value = value.trim();

        // If empty, return as is
        if (!value) return value;

        // If already starts with "MK" (case insensitive), return as is
        if (/^MK\s*/i.test(value)) {
            // Ensure "MK " is uppercase with space
            return value.replace(/^mk\s*/i, 'MK ');
        }

        // If it's just numbers, add "MK " prefix
        if (/^\d+/.test(value)) {
            return 'MK ' + value;
        }

        // Otherwise return as is
        return value;
    }

    /**
     * Attach auto-prefix to SD number fields
     */
    function attachSDPrefix(inputElement) {
        if (!inputElement || inputElement.dataset.sdPrefixAttached) return;

        inputElement.addEventListener('blur', function() {
            const formatted = formatSDNumber(this.value);
            if (formatted !== this.value) {
                this.value = formatted;
                // Trigger change event for any listeners
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });

        inputElement.dataset.sdPrefixAttached = 'true';
    }

    /**
     * Attach auto-prefix to MK number fields
     */
    function attachMKPrefix(inputElement) {
        if (!inputElement || inputElement.dataset.mkPrefixAttached) return;

        inputElement.addEventListener('blur', function() {
            const formatted = formatMKNumber(this.value);
            if (formatted !== this.value) {
                this.value = formatted;
                // Trigger change event for any listeners
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });

        inputElement.dataset.mkPrefixAttached = 'true';
    }

    /**
     * Find and attach to all SD and MK fields
     */
    function attachToAllFields() {
        // SD number fields
        const sdInputs = document.querySelectorAll(
            '[name="sd_number"], ' +
            '[name*="sd_number"], ' +
            '#id_sd_number, ' +
            '#sd_number, ' +
            'input[id*="sd_number"]'
        );
        sdInputs.forEach(attachSDPrefix);

        // MK number fields
        const mkInputs = document.querySelectorAll(
            '[name="mk_number"], ' +
            '[name*="mk_number"], ' +
            '#id_mk_number, ' +
            '#mk_number, ' +
            'input[id*="mk_number"]'
        );
        mkInputs.forEach(attachMKPrefix);
    }

    /**
     * Initialize on page load
     */
    function init() {
        attachToAllFields();

        // Watch for dynamically added fields (formsets)
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    attachToAllFields();
                }
            });
        });

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
