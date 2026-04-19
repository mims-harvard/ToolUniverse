// Force the Shibuya theme switcher into a simple light/dark toggle.
(function() {
    'use strict';

    function getEffectiveMode() {
        const root = document.documentElement;
        if (root.classList.contains('dark')) return 'dark';
        if (root.classList.contains('light')) return 'light';
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    function applyMode(mode) {
        if (typeof window.setColorMode === 'function') {
            window.setColorMode(mode);
        } else {
            const root = document.documentElement;
            root.setAttribute('data-color-mode', mode);
            root.classList.remove('light', 'dark');
            root.classList.add(mode);
        }

        try {
            localStorage._theme = mode;
        } catch (error) {
            // Ignore storage failures in restricted contexts.
        }
    }

    function updateAria(button, mode) {
        const aria = button.getAttribute('data-aria-' + mode);
        if (aria) {
            button.setAttribute('aria-label', aria);
        }
    }

    function bindThemeToggle() {
        const button = document.querySelector('.js-theme');
        if (!button || button.dataset.tuThemeFixBound === 'true') {
            return;
        }

        button.dataset.tuThemeFixBound = 'true';
        updateAria(button, document.documentElement.getAttribute('data-color-mode') || getEffectiveMode());

        button.addEventListener('click', function(event) {
            event.preventDefault();
            event.stopImmediatePropagation();

            const nextMode = getEffectiveMode() === 'dark' ? 'light' : 'dark';
            applyMode(nextMode);
            updateAria(button, nextMode);
        }, true);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindThemeToggle);
    } else {
        bindThemeToggle();
    }
})();
