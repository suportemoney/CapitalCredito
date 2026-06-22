/**
 * Tema claro/escuro do módulo Plus (persistido em localStorage).
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'plus-theme';
  var root = document.querySelector('.esteira-page, .ger-page');
  if (!root) return;

  var toggle = document.getElementById('plus-theme-toggle');
  var labelEl = toggle ? toggle.querySelector('.plus-theme-toggle__label') : null;

  function resolveInitialTheme() {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  function updateToggleLabel(theme) {
    if (!labelEl) return;
    labelEl.textContent = theme === 'dark' ? 'Tema escuro' : 'Tema claro';
  }

  function applyTheme(theme) {
    root.setAttribute('data-plus-theme', theme);
    document.documentElement.setAttribute('data-plus-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    updateToggleLabel(theme);
  }

  applyTheme(resolveInitialTheme());

  if (toggle) {
    toggle.addEventListener('click', function () {
      var next = root.getAttribute('data-plus-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
    });
  }
})();
