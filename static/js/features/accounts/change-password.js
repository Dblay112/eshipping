/**
 * Change Password (accounts)
 * Extracted from templates/accounts/change_password.html
 */

(function() {
  'use strict';

  window.togglePw = function(evt, inputId) {
    const input = document.getElementById(inputId);
    const btn = evt.target;
    const hidden = input.type === 'password';
    input.type = hidden ? 'text' : 'password';
    btn.textContent = hidden ? 'HIDE' : 'SHOW';
  };

  // Prevent browser autofill/prepopulate on this page:
  // readonly until focus blocks autofill on load (page-only behavior)
  document.querySelectorAll('input.chpw-input[readonly]').forEach((input) => {
    input.addEventListener('focus', () => {
      input.removeAttribute('readonly');
    }, { once: true });
  });

  // Clear any autofilled values on load (page-only)
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('input.chpw-input').forEach((input) => {
      input.value = '';
    });
  });

  // Also clear if bfcache restores the page
  window.addEventListener('load', () => {
    document.querySelectorAll('input.chpw-input').forEach((input) => {
      input.value = '';
    });
  });

})();
