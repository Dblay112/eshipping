/**
 * Form Auto-Save Utility
 * Automatically saves form data to localStorage to prevent data loss
 * from internet issues, errors, or page refreshes
 */

(function() {
  'use strict';

  const AUTOSAVE_PREFIX = 'form_autosave_';
  const SAVE_DELAY = 1000; // Debounce delay in milliseconds

  class FormAutoSave {
    constructor(formElement) {
      this.form = formElement;
      this.storageKey = this.getStorageKey();
      this.saveTimeout = null;
      this.attachedInputs = new WeakSet(); // Track which inputs already have listeners
      this.init();
    }

    getStorageKey() {
      // Use form ID or action URL as unique key
      const formId = this.form.id || this.form.action || window.location.pathname;
      return AUTOSAVE_PREFIX + formId.replace(/[^a-zA-Z0-9]/g, '_');
    }

    init() {
      // Skip auto-save on list/view pages
      const isListPage = window.location.pathname.includes('/pending/') ||
                         window.location.pathname.includes('/approved/') ||
                         window.location.pathname.includes('/my_tallies') ||
                         window.location.pathname.includes('/view/') ||
                         window.location.pathname.includes('/list/') ||
                         window.location.pathname.includes('/operations/');

      if (isListPage) {
        // Don't run auto-save on list/view pages
        return;
      }

      // Check if this is an "add" page (not edit) - clear saved data for fresh start
      const isAddPage = window.location.pathname.includes('/add') ||
                        window.location.pathname.endsWith('/create/') ||
                        this.form.action.includes('/add') ||
                        this.form.action.includes('/create/');

      if (isAddPage) {
        // Clear any saved data for add pages - user wants to create NEW record
        this.clearSavedData();
      } else {
        // Restore saved data on edit pages or other forms
        this.restoreSavedData();

        // Show notification if data was restored
        if (this.hasSavedData()) {
          this.showRestoreNotification();
        }
      }

      // Attach save listeners to form inputs
      this.attachSaveListeners();

      // Watch for dynamically added form fields (for formsets, "Add" buttons, etc.)
      this.observeDynamicFields();

      // Clear saved data on successful submission
      this.form.addEventListener('submit', () => {
        // Small delay to ensure submission goes through
        setTimeout(() => {
          this.clearSavedData();
        }, 100);
      });
    }

    observeDynamicFields() {
      // Use MutationObserver to detect when new form fields are added
      const observer = new MutationObserver((mutations) => {
        let hasNewInputs = false;

        mutations.forEach(mutation => {
          mutation.addedNodes.forEach(node => {
            // Check if the added node is an input or contains inputs
            if (node.nodeType === 1) { // Element node
              if (this.isFormInput(node)) {
                hasNewInputs = true;
              } else if (node.querySelectorAll) {
                const inputs = node.querySelectorAll('input, select, textarea');
                if (inputs.length > 0) {
                  hasNewInputs = true;
                }
              }
            }
          });
        });

        // If new inputs were added, attach listeners to them
        if (hasNewInputs) {
          this.attachSaveListeners();
        }
      });

      // Start observing the form for changes
      observer.observe(this.form, {
        childList: true,
        subtree: true
      });

      // Store observer reference for cleanup if needed
      this.observer = observer;
    }

    isFormInput(element) {
      const tagName = element.tagName ? element.tagName.toLowerCase() : '';
      return tagName === 'input' || tagName === 'select' || tagName === 'textarea';
    }

    attachSaveListeners() {
      // Get all form inputs
      const inputs = this.form.querySelectorAll('input, select, textarea');

      inputs.forEach(input => {
        // Skip if listener already attached to this input
        if (this.attachedInputs.has(input)) return;

        // Skip file inputs (can't save files to localStorage)
        if (input.type === 'file') return;

        // Skip CSRF tokens and hidden management form fields
        if (input.name === 'csrfmiddlewaretoken') return;
        if (input.name && input.name.includes('TOTAL_FORMS')) return;
        if (input.name && input.name.includes('INITIAL_FORMS')) return;
        if (input.name && input.name.includes('MIN_NUM_FORMS')) return;
        if (input.name && input.name.includes('MAX_NUM_FORMS')) return;

        // Attach appropriate event listener
        if (input.type === 'checkbox' || input.type === 'radio') {
          input.addEventListener('change', () => this.debouncedSave());
        } else {
          input.addEventListener('input', () => this.debouncedSave());
        }

        // Mark this input as having a listener attached
        this.attachedInputs.add(input);
      });
    }

    debouncedSave() {
      clearTimeout(this.saveTimeout);
      this.saveTimeout = setTimeout(() => {
        this.saveFormData();
      }, SAVE_DELAY);
    }

    saveFormData() {
      const formData = {};
      const inputs = this.form.querySelectorAll('input, select, textarea');

      inputs.forEach(input => {
        // Skip file inputs, CSRF tokens, and management form fields
        if (input.type === 'file') return;
        if (input.name === 'csrfmiddlewaretoken') return;
        if (input.name && (
          input.name.includes('TOTAL_FORMS') ||
          input.name.includes('INITIAL_FORMS') ||
          input.name.includes('MIN_NUM_FORMS') ||
          input.name.includes('MAX_NUM_FORMS')
        )) return;

        const name = input.name || input.id;
        if (!name) return;

        if (input.type === 'checkbox') {
          formData[name] = input.checked;
        } else if (input.type === 'radio') {
          if (input.checked) {
            formData[name] = input.value;
          }
        } else {
          formData[name] = input.value;
        }
      });

      // Save to localStorage
      try {
        localStorage.setItem(this.storageKey, JSON.stringify({
          data: formData,
          timestamp: new Date().toISOString()
        }));
      } catch (e) {
        console.warn('Failed to save form data:', e);
      }
    }

    restoreSavedData() {
      try {
        const saved = localStorage.getItem(this.storageKey);
        if (!saved) return;

        const { data, timestamp } = JSON.parse(saved);

        // Check if saved data is older than 7 days
        const savedDate = new Date(timestamp);
        const daysDiff = (new Date() - savedDate) / (1000 * 60 * 60 * 24);
        if (daysDiff > 7) {
          this.clearSavedData();
          return;
        }

        // Restore form values
        Object.keys(data).forEach(name => {
          const input = this.form.querySelector(`[name="${name}"], #${name}`);
          if (!input) return;

          if (input.type === 'checkbox') {
            input.checked = data[name];
          } else if (input.type === 'radio') {
            if (input.value === data[name]) {
              input.checked = true;
            }
          } else {
            input.value = data[name];

            // Trigger change event for any dependent logic
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
          }
        });

      } catch (e) {
        console.warn('Failed to restore form data:', e);
      }
    }

    hasSavedData() {
      return localStorage.getItem(this.storageKey) !== null;
    }

    clearSavedData() {
      localStorage.removeItem(this.storageKey);
    }

    showRestoreNotification() {
      // Create notification element
      const notification = document.createElement('div');
      notification.className = 'autosave-notification';
      notification.innerHTML = `
        <div class="autosave-notification-content">
          <svg viewBox="0 0 20 20" fill="none" width="18" height="18">
            <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 12a1 1 0 110-2 1 1 0 010 2zm1-4a1 1 0 01-2 0V6a1 1 0 012 0v4z" fill="currentColor"/>
          </svg>
          <span>Your previous form data has been restored</span>
          <button type="button" class="autosave-dismiss" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
      `;

      // Add styles if not already present
      if (!document.getElementById('autosave-styles')) {
        const style = document.createElement('style');
        style.id = 'autosave-styles';
        style.textContent = `
          .autosave-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            animation: slideIn 0.3s ease-out;
          }
          .autosave-notification-content {
            display: flex;
            align-items: center;
            gap: 12px;
            background: #3d2817;
            color: #fff;
            padding: 14px 18px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            font-size: 13px;
            font-weight: 500;
          }
          .autosave-notification svg {
            flex-shrink: 0;
            color: #fbbf24;
          }
          .autosave-dismiss {
            background: none;
            border: none;
            color: #fff;
            font-size: 24px;
            line-height: 1;
            cursor: pointer;
            padding: 0;
            margin-left: 8px;
            opacity: 0.7;
            transition: opacity 0.2s;
          }
          .autosave-dismiss:hover {
            opacity: 1;
          }
          @keyframes slideIn {
            from {
              transform: translateX(400px);
              opacity: 0;
            }
            to {
              transform: translateX(0);
              opacity: 1;
            }
          }
          @media (max-width: 600px) {
            .autosave-notification {
              top: 10px;
              right: 10px;
              left: 10px;
            }
          }
        `;
        document.head.appendChild(style);
      }

      document.body.appendChild(notification);

      // Auto-dismiss after 5 seconds
      setTimeout(() => {
        notification.remove();
      }, 5000);
    }
  }

  // Initialize auto-save for all forms on the page
  function initAutoSave() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
      // Skip search forms and other non-data forms
      if (form.classList.contains('sdt-search-form')) return;
      if (form.method.toLowerCase() === 'get') return;

      // Skip tally forms (they have their own specialized auto-save)
      if (form.id && form.id.includes('Tally')) return;
      if (form.querySelector('[id*="Tally"]')) return;

      new FormAutoSave(form);
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAutoSave);
  } else {
    initAutoSave();
  }

})();
