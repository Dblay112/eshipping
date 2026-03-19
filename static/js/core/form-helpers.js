/**
 * Form helpers (shared utilities)
 *
 * NOTE:
 * - Global uppercasing is handled by static/js/uppercase-inputs.js
 * - SD/MK auto-prefixing is handled by static/js/auto-prefix.js
 * This file intentionally avoids duplicating those behaviors.
 */

(function () {
  'use strict';

  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func.apply(this, args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Expose for other page scripts (reduces duplication)
  window.cmcDebounce = window.cmcDebounce || debounce;

  function initFormPersistence(formSelector) {
    const form = document.querySelector(formSelector || 'form');
    if (!form) return;

    const formId = 'form_data_' + window.location.pathname;

    function saveFormData() {
      const formData = {};
      const inputs = form.querySelectorAll(
        'input:not([type="hidden"]):not([type="file"]):not([type="password"]), select, textarea'
      );

      inputs.forEach(function (input) {
        if (!input.name) return;

        if (input.type === 'checkbox') {
          formData[input.name] = input.checked;
        } else if (input.type === 'radio') {
          if (input.checked) formData[input.name] = input.value;
        } else {
          formData[input.name] = input.value;
        }
      });

      try {
        localStorage.setItem(formId, JSON.stringify(formData));
      } catch (e) {
        console.warn('Could not save form data to localStorage:', e);
      }
    }

    function restoreFormData() {
      try {
        const savedData = localStorage.getItem(formId);
        if (!savedData) return;

        const formData = JSON.parse(savedData);

        Object.keys(formData).forEach(function (name) {
          const input = form.querySelector('[name="' + name + '"]');
          if (!input) return;

          if (input.type === 'checkbox') {
            input.checked = formData[name];
          } else if (input.type === 'radio') {
            if (input.value === formData[name]) input.checked = true;
          } else {
            input.value = formData[name];
          }
        });

        const event = new Event('change', { bubbles: true });
        form.querySelectorAll('input, select, textarea').forEach(function (el) {
          if (el.name && formData[el.name] !== undefined) {
            el.dispatchEvent(event);
          }
        });
      } catch (e) {
        console.warn('Could not restore form data from localStorage:', e);
      }
    }

    function clearFormData() {
      try {
        localStorage.removeItem(formId);
      } catch (e) {
        console.warn('Could not clear form data from localStorage:', e);
      }
    }

    restoreFormData();

    const saveDebounced = window.cmcDebounce(saveFormData, 300);
    form.addEventListener('input', saveDebounced);
    form.addEventListener('change', saveFormData);

    form.addEventListener('submit', function () {
      setTimeout(function () {
        const hasErrors = document.querySelector(
          '.sdt-form-error, .sdt-alert-error, .error, .alert-danger'
        );
        if (!hasErrors) {
          clearFormData();
        }
      }, 2000);
    });

    window.clearSavedFormData = clearFormData;
  }

  function init() {
    initFormPersistence();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Re-init hook for pages that dynamically add form inputs
  window.reinitFormHelpers = function () {
    initFormPersistence();
  };
})();
