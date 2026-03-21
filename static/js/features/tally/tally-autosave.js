/**
 * Tally Auto-Save System
 * Prevents data loss by automatically saving form data to localStorage
 * and restoring it when the page reloads.
 */

(function() {
    'use strict';

    // Configuration
    const AUTOSAVE_DELAY = 2000; // 2 seconds after last input
    const INDICATOR_DURATION = 2000; // Show "Auto-saved" for 2 seconds

    // Detect tally type from form ID or page title
    function getTallyType() {
        const formId = document.querySelector('form[id*="Tally"]')?.id || '';
        const title = document.title.toLowerCase();

        if (formId.includes('bulk') || title.includes('bulk')) return 'bulk';
        if (title.includes('japan')) return 'japan';
        if (title.includes('20ft') || title.includes('20 ft')) return '20ft';
        if (title.includes('40ft') || title.includes('40 ft')) return '40ft';

        return 'default';
    }

    const TALLY_TYPE = getTallyType();
    const STORAGE_KEY = `tally_autosave_${TALLY_TYPE}`;

    // Check if we're in edit mode (don't auto-save when editing existing tallies)
    if (window.EDIT_MODE === true) {
        console.log('[Tally Auto-Save] Edit mode detected - auto-save disabled');
        return;
    }

    let saveTimeout = null;
    let indicatorTimeout = null;

    // Create auto-save indicator
    function createIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'autosave-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: #4caf50;
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 9999;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        `;
        indicator.textContent = '✓ Auto-saved';
        document.body.appendChild(indicator);
        return indicator;
    }

    const indicator = createIndicator();

    // Show auto-save indicator
    function showIndicator() {
        indicator.style.opacity = '1';

        clearTimeout(indicatorTimeout);
        indicatorTimeout = setTimeout(() => {
            indicator.style.opacity = '0';
        }, INDICATOR_DURATION);
    }

    // Get all header field values
    function getHeaderData() {
        const data = {};
        const form = document.querySelector('form[id*="Tally"]');
        if (!form) return data;

        // Get all input, select, and textarea fields (except files and CSRF)
        const fields = form.querySelectorAll('input:not([type="file"]):not([name="csrfmiddlewaretoken"]), select, textarea');

        fields.forEach(field => {
            const name = field.name;
            const id = field.id;

            // Skip container fields (they're handled separately)
            if (name && name.includes('containers[')) return;

            // Skip hidden fields that are part of name chips (we'll save the visible chips instead)
            if (field.type === 'hidden' && (name === 's_name' || name === 'clerk_name')) return;

            // Use ID as key if available, otherwise use name
            const key = id || name;
            if (!key) return;

            if (field.type === 'checkbox') {
                data[key] = field.checked;
            } else if (field.type === 'radio') {
                if (field.checked) data[key] = field.value;
            } else {
                data[key] = field.value;
            }
        });

        return data;
    }

    // Get superintendent and clerk names from chips
    function getNameChipsData() {
        const data = {
            superintendent_names: [],
            clerk_names: []
        };

        // Get superintendent names
        const superChips = document.querySelectorAll('#superintendentChips .name-box');
        superChips.forEach(chip => {
            const text = chip.querySelector('.name-box-text')?.textContent || '';
            const name = text.replace(/^\d+\.\s*/, '').trim(); // Remove "1. " prefix
            if (name) data.superintendent_names.push(name);
        });

        // Get clerk names
        const clerkChips = document.querySelectorAll('#clerkChips .name-box');
        clerkChips.forEach(chip => {
            const text = chip.querySelector('.name-box-text')?.textContent || '';
            const name = text.replace(/^\d+\.\s*/, '').trim();
            if (name) data.clerk_names.push(name);
        });

        return data;
    }

    // Get container rows data
    function getContainersData() {
        // Access the global inMemory or inMemoryContainers variable that stores container data
        const containerData = typeof inMemory !== 'undefined' ? inMemory :
                             typeof inMemoryContainers !== 'undefined' ? inMemoryContainers : null;

        if (containerData && Array.isArray(containerData)) {
            return containerData.filter(row => {
                // Only save rows that have some data
                if (!row) return false;
                const hasData = row.container_number || row.seal_number ||
                               row.bags || row.tonnage || row.bags_cut;
                return hasData;
            });
        }
        return [];
    }

    // Save all form data to localStorage
    function saveToLocalStorage() {
        try {
            const data = {
                timestamp: new Date().toISOString(),
                header: getHeaderData(),
                nameChips: getNameChipsData(),
                containers: getContainersData()
            };

            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
            showIndicator();
            console.log('[Tally Auto-Save] Data saved:', data);
        } catch (error) {
            console.error('[Tally Auto-Save] Failed to save:', error);
        }
    }

    // Debounced save function
    function scheduleSave() {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(saveToLocalStorage, AUTOSAVE_DELAY);
    }

    // Restore header fields
    function restoreHeaderData(headerData) {
        Object.keys(headerData).forEach(key => {
            const field = document.getElementById(key) || document.querySelector(`[name="${key}"]`);
            if (!field) return;

            const value = headerData[key];

            if (field.type === 'checkbox') {
                field.checked = value;
            } else if (field.type === 'radio') {
                if (field.value === value) field.checked = true;
            } else {
                field.value = value;
            }
        });
    }

    // Restore name chips
    function restoreNameChips(nameChipsData) {
        // Restore superintendent names
        if (nameChipsData.superintendent_names && nameChipsData.superintendent_names.length > 0) {
            const superInput = document.getElementById('superintendentInput');
            const addBtn = document.getElementById('addSuperintendentBtn');

            if (superInput && addBtn) {
                nameChipsData.superintendent_names.forEach(name => {
                    superInput.value = name;
                    addBtn.click();
                });
                superInput.value = '';
            }
        }

        // Restore clerk names
        if (nameChipsData.clerk_names && nameChipsData.clerk_names.length > 0) {
            const clerkInput = document.getElementById('clerkInput');
            const addBtn = document.getElementById('addClerkBtn');

            if (clerkInput && addBtn) {
                nameChipsData.clerk_names.forEach(name => {
                    clerkInput.value = name;
                    addBtn.click();
                });
                clerkInput.value = '';
            }
        }
    }

    // Restore container rows
    function restoreContainers(containersData) {
        if (!Array.isArray(containersData) || containersData.length === 0) return;

        // Determine which global variable to use (different templates use different names)
        if (typeof inMemory !== 'undefined') {
            window.inMemory = containersData;
        } else if (typeof inMemoryContainers !== 'undefined') {
            window.inMemoryContainers = containersData;
        } else {
            console.warn('[Tally Auto-Save] Container storage variable not found');
            return;
        }

        // Trigger re-render if renderContainers function exists
        if (typeof renderContainers === 'function') {
            renderContainers(true);
        }
    }

    // Restore all saved data
    function restoreFromLocalStorage() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (!saved) return false;

            const data = JSON.parse(saved);
            const savedDate = new Date(data.timestamp);
            const now = new Date();
            const hoursSince = (now - savedDate) / (1000 * 60 * 60);

            // Don't restore data older than 24 hours
            if (hoursSince > 24) {
                localStorage.removeItem(STORAGE_KEY);
                return false;
            }

            // Show confirmation dialog
            const timeAgo = hoursSince < 1
                ? `${Math.round(hoursSince * 60)} minutes ago`
                : `${Math.round(hoursSince)} hours ago`;

            const message = `Auto-saved data found from ${timeAgo}.\n\nWould you like to restore it?`;

            if (confirm(message)) {
                // Restore data
                if (data.header) restoreHeaderData(data.header);
                if (data.nameChips) restoreNameChips(data.nameChips);
                if (data.containers) restoreContainers(data.containers);

                console.log('[Tally Auto-Save] Data restored:', data);

                // Show success message
                const successMsg = document.createElement('div');
                successMsg.style.cssText = `
                    position: fixed;
                    top: 80px;
                    right: 20px;
                    background: #2196f3;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: 500;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                    z-index: 9999;
                `;
                successMsg.textContent = '✓ Auto-saved data restored';
                document.body.appendChild(successMsg);

                setTimeout(() => {
                    successMsg.style.opacity = '0';
                    successMsg.style.transition = 'opacity 0.3s ease';
                    setTimeout(() => successMsg.remove(), 300);
                }, 3000);

                return true;
            } else {
                // User declined - clear the saved data
                localStorage.removeItem(STORAGE_KEY);
                return false;
            }
        } catch (error) {
            console.error('[Tally Auto-Save] Failed to restore:', error);
            localStorage.removeItem(STORAGE_KEY);
            return false;
        }
    }

    // Clear saved data on successful submission
    function clearSavedData() {
        localStorage.removeItem(STORAGE_KEY);
        console.log('[Tally Auto-Save] Saved data cleared');
    }

    // Initialize auto-save
    function init() {
        const form = document.querySelector('form[id*="Tally"]');
        if (!form) {
            console.warn('[Tally Auto-Save] Form not found');
            return;
        }

        console.log(`[Tally Auto-Save] Initialized for ${TALLY_TYPE} tally`);

        // Try to restore saved data on page load
        setTimeout(() => {
            restoreFromLocalStorage();
        }, 500); // Small delay to ensure all scripts are loaded

        // Listen for input events on the entire form
        form.addEventListener('input', scheduleSave);
        form.addEventListener('change', scheduleSave);

        // Listen for clicks on ADD/REMOVE buttons (for name chips and containers)
        form.addEventListener('click', (e) => {
            const btn = e.target.closest('button');
            if (btn && (btn.textContent.includes('ADD') || btn.textContent.includes('REMOVE'))) {
                scheduleSave();
            }
        });

        // Clear saved data when CANCEL button is clicked
        const cancelBtn = document.querySelector('a[href*="my_tallies"], a[href*="tally_view"]');
        if (cancelBtn && cancelBtn.textContent.includes('CANCEL')) {
            cancelBtn.addEventListener('click', (e) => {
                // Clear saved data immediately
                clearSavedData();
                console.log('[Tally Auto-Save] Data cleared - user clicked CANCEL');
            });
        }

        // Clear saved data ONLY on successful submission (when redirected to success page)
        // Don't clear on submit - wait to see if validation passes
        // The success page will clear the data instead
    }

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
