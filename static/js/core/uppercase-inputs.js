/**
 * Global Uppercase Input Handler
 * Automatically converts all text inputs and textareas to uppercase
 * Excludes: email, password, number, date, time, url, tel, file inputs
 */

(function() {
    'use strict';

    // Input types that should NOT be converted to uppercase
    const EXCLUDED_TYPES = [
        'email',
        'password',
        'number',
        'date',
        'datetime-local',
        'time',
        'url',
        'tel',
        'file',
        'hidden'
    ];

    /**
     * Check if an input should be converted to uppercase
     */
    function shouldConvertToUppercase(input) {
        // Never convert explicitly case-sensitive fields
        if (input && input.dataset && input.dataset.caseSensitive === 'true') {
            return false;
        }

        // Get input type (default to 'text' if not specified)
        const type = (input.type || 'text').toLowerCase();

        // Exclude specific input types
        if (EXCLUDED_TYPES.includes(type)) {
            return false;
        }

        // Only convert text inputs and textareas
        if (input.tagName === 'TEXTAREA') {
            return true;
        }

        if (input.tagName === 'INPUT' && (type === 'text' || type === 'search' || !input.type)) {
            return true;
        }

        return false;
    }

    /**
     * Convert input value to uppercase
     */
    function convertToUppercase(event) {
        const input = event.target;

        if (!shouldConvertToUppercase(input)) {
            return;
        }

        // Store cursor position
        const start = input.selectionStart;
        const end = input.selectionEnd;

        // Never uppercase the navbar SD search inputs
        if (input.id === 'sdSearchInput' || input.closest('.cmc-search') || input.closest('.cmc-search-mobile')) {
            return;
        }

        // Convert to uppercase
        const originalValue = input.value;
        const uppercaseValue = originalValue.toUpperCase();

        // Only update if value changed (prevents unnecessary updates)
        if (originalValue !== uppercaseValue) {
            input.value = uppercaseValue;

            // Restore cursor position
            input.setSelectionRange(start, end);
        }
    }

    /**
     * Initialize uppercase conversion for all existing inputs
     */
    function initializeInputs() {
        // Get all text inputs and textareas
        const inputs = document.querySelectorAll('input, textarea');

        inputs.forEach(function(input) {
            const isNavSearch = input.id === 'sdSearchInput' || (input.closest && (input.closest('.cmc-search') || input.closest('.cmc-search-mobile')));
            if (!isNavSearch && shouldConvertToUppercase(input)) {
                if (input.value) {
                    input.value = input.value.toUpperCase();
                }
            }
        });
    }

    /**
     * Use event delegation for better performance and dynamic content support
     */
    document.addEventListener('input', convertToUppercase, true);

    /**
     * Initialize on page load
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeInputs);
    } else {
        initializeInputs();
    }

    /**
     * Re-initialize when new content is added (for dynamic forms)
     */
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    if (node.tagName === 'INPUT' || node.tagName === 'TEXTAREA') {
                        const isNavSearch = node.id === 'sdSearchInput' || (node.closest && (node.closest('.cmc-search') || node.closest('.cmc-search-mobile')));
                        if (!isNavSearch && shouldConvertToUppercase(node) && node.value) {
                            node.value = node.value.toUpperCase();
                        }
                    }
                    // Check children
                    const inputs = node.querySelectorAll && node.querySelectorAll('input, textarea');
                    if (inputs) {
                        inputs.forEach(function(input) {
                            const isNavSearch = input.id === 'sdSearchInput' || (input.closest && (input.closest('.cmc-search') || input.closest('.cmc-search-mobile')));
                            if (!isNavSearch && shouldConvertToUppercase(input) && input.value) {
                                input.value = input.value.toUpperCase();
                            }
                        });
                    }
                }
            });
        });
    });

    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

})();
