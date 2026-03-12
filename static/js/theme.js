/**
 * Turkmen Search — Theme Manager
 * Handles light/dark theme switching with localStorage persistence
 */

const ThemeManager = {
    STORAGE_KEY: 'theme',
    DEFAULT_THEME: 'light',

    init() {
        const saved = localStorage.getItem(this.STORAGE_KEY);
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = saved || (prefersDark ? 'dark' : this.DEFAULT_THEME);
        this.setTheme(theme, false);
        this._setupToggle();
        this._watchSystemTheme();
    },

    setTheme(theme, save = true) {
        document.documentElement.setAttribute('data-theme', theme);
        if (save) {
            localStorage.setItem(this.STORAGE_KEY, theme);
        }
        this._updateToggleIcon(theme);
        this._updateMeta(theme);
    },

    getTheme() {
        return document.documentElement.getAttribute('data-theme') || this.DEFAULT_THEME;
    },

    toggle() {
        const current = this.getTheme();
        this.setTheme(current === 'dark' ? 'light' : 'dark');
    },

    _setupToggle() {
        const btn = document.getElementById('themeToggle');
        if (!btn) return;
        btn.addEventListener('click', () => this.toggle());
    },

    _updateToggleIcon(theme) {
        const sunIcon = document.querySelector('.icon-sun');
        const moonIcon = document.querySelector('.icon-moon');

        if (sunIcon && moonIcon) {
            if (theme === 'dark') {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            } else {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            }
        }
    },

    _updateMeta(theme) {
        let meta = document.querySelector('meta[name="theme-color"]');
        if (!meta) {
            meta = document.createElement('meta');
            meta.name = 'theme-color';
            document.head.appendChild(meta);
        }
        meta.content = theme === 'dark' ? '#0F172A' : '#FFFFFF';
    },

    _watchSystemTheme() {
        const media = window.matchMedia('(prefers-color-scheme: dark)');
        media.addEventListener('change', (e) => {
            if (!localStorage.getItem(this.STORAGE_KEY)) {
                this.setTheme(e.matches ? 'dark' : 'light', false);
            }
        });
    },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
});