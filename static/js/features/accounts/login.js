/**
 * Login (accounts)
 * Extracted from templates/accounts/login.html
 */

(function() {
  'use strict';

  document.addEventListener('DOMContentLoaded', function() {
    // Password toggle functionality - mobile Safari compatible
    document.querySelectorAll('.pw-toggle').forEach(button => {
      let touchHandled = false;

      // Handle touch events (mobile)
      button.addEventListener('touchstart', function(e) {
        e.preventDefault();
        touchHandled = true;
        togglePasswordVisibility(this);

        // Reset flag after a short delay
        setTimeout(() => { touchHandled = false; }, 300);
      });

      // Handle click events (desktop) - only if touch wasn't handled
      button.addEventListener('click', function(e) {
        e.preventDefault();
        if (!touchHandled) {
          togglePasswordVisibility(this);
        }
      });
    });

    function togglePasswordVisibility(button) {
      const inputId = button.getAttribute('data-target');
      const input = document.getElementById(inputId);
      if (!input) return;

      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      button.textContent = isPassword ? 'HIDE' : 'SHOW';
    }

    // Toggle reset password card if required
    const requirePasswordReset = !!(window.LOGIN_CONFIG && window.LOGIN_CONFIG.requirePasswordReset);
    if (requirePasswordReset) {
      const loginCard = document.getElementById('loginCard');
      const resetCard = document.getElementById('resetPasswordCard');
      if (loginCard) loginCard.style.display = 'none';
      if (resetCard) resetCard.style.display = 'block';
    }
  });
})();
