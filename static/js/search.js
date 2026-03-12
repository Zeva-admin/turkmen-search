/**
 * Turkmen Search — Search Module
 * Live search functionality across the platform
 */

const Search = {
    debounceTimer: null,
    minChars: 2,
    isOpen: false,

    init() {
        this._setupHeaderSearch();
    },

    _setupHeaderSearch() {
        const btn = document.getElementById('headerSearchBtn');
        if (!btn) return;

        btn.addEventListener('click', () => {
            this.openSearchOverlay();
        });

        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.openSearchOverlay();
            }
            if (e.key === 'Escape' && this.isOpen) {
                this.closeSearchOverlay();
            }
        });
    },

    openSearchOverlay() {
        if (this.isOpen) return;
        this.isOpen = true;

        const overlay = document.createElement('div');
        overlay.id = 'searchOverlay';
        overlay.className = 'search-overlay';
        overlay.innerHTML = `
            <div class="search-overlay-backdrop" id="searchBackdrop"></div>
            <div class="search-overlay-dialog">
                <div class="search-overlay-input-wrap">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="search-overlay-icon"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                    <input type="text" id="searchOverlayInput" class="search-overlay-input" placeholder="Поиск вакансий, компаний..." autocomplete="off" autofocus>
                    <button class="search-overlay-close" id="searchOverlayClose">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>
                <div class="search-overlay-results" id="searchOverlayResults">
                    <div class="search-overlay-hint">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                        Начните вводить для поиска
                    </div>
                </div>
                <div class="search-overlay-footer">
                    <span class="search-kbd">Enter</span> перейти
                    <span class="search-kbd">↑↓</span> навигация
                    <span class="search-kbd">Esc</span> закрыть
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';

        this._injectSearchStyles();

        const input = document.getElementById('searchOverlayInput');
        const backdrop = document.getElementById('searchBackdrop');
        const closeBtn = document.getElementById('searchOverlayClose');

        if (input) {
            input.focus();
            input.addEventListener('input', (e) => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.performSearch(e.target.value.trim());
                }, 300);
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    const query = input.value.trim();
                    if (query) {
                        this.closeSearchOverlay();
                        window.location.href = `/jobs?q=${encodeURIComponent(query)}`;
                    }
                }
            });
        }

        if (backdrop) backdrop.addEventListener('click', () => this.closeSearchOverlay());
        if (closeBtn) closeBtn.addEventListener('click', () => this.closeSearchOverlay());
    },

    closeSearchOverlay() {
        const overlay = document.getElementById('searchOverlay');
        if (overlay) overlay.remove();
        document.body.style.overflow = '';
        this.isOpen = false;
    },

    async performSearch(query) {
        const results = document.getElementById('searchOverlayResults');
        if (!results) return;

        if (!query || query.length < this.minChars) {
            results.innerHTML = `
                <div class="search-overlay-hint">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                    Начните вводить для поиска
                </div>`;
            return;
        }

        results.innerHTML = `<div class="search-loading"><div class="spinner" style="width:24px;height:24px;border-width:2px;"></div></div>`;

        try {
            const [jobsData, companiesData] = await Promise.all([
                API.get(`/api/jobs?q=${encodeURIComponent(query)}&per_page=5`),
                API.get(`/api/companies?q=${encodeURIComponent(query)}&per_page=3`),
            ]);

            const jobs = jobsData.jobs || [];
            const companies = companiesData.companies || [];

            if (jobs.length === 0 && companies.length === 0) {
                results.innerHTML = `
                    <div class="search-no-results">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                        <p>Ничего не найдено по запросу «${escapeHtmlSearch(query)}»</p>
                    </div>`;
                return;
            }

            let html = '';

            if (jobs.length > 0) {
                html += `<div class="search-section-title">Вакансии</div>`;
                html += jobs.map(job => `
                    <a href="/jobs/${job.id}" class="search-result-item" onclick="Search.closeSearchOverlay()">
                        <div class="search-result-icon search-icon-job">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                        </div>
                        <div class="search-result-info">
                            <span class="search-result-title">${job.title}</span>
                            <span class="search-result-sub">${job.company?.name || ''} · ${job.city} · ${job.salary}</span>
                        </div>
                        <svg class="search-result-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </a>
                `).join('');

                if (jobsData.total > 5) {
                    html += `<a href="/jobs?q=${encodeURIComponent(query)}" class="search-see-all" onclick="Search.closeSearchOverlay()">
                        Показать все ${jobsData.total} вакансий →
                    </a>`;
                }
            }

            if (companies.length > 0) {
                html += `<div class="search-section-title">Компании</div>`;
                html += companies.map(c => `
                    <a href="/companies/${c.id}" class="search-result-item" onclick="Search.closeSearchOverlay()">
                        <div class="search-result-icon search-icon-company">
                            ${c.logo
                                ? `<img src="/uploads/logos/${c.logo}" alt="${c.name}" style="width:100%;height:100%;object-fit:contain;border-radius:4px;">`
                                : `<span style="font-weight:700;font-size:14px;color:var(--primary);">${c.name[0]}</span>`}
                        </div>
                        <div class="search-result-info">
                            <span class="search-result-title">${c.name}</span>
                            <span class="search-result-sub">${c.city || ''} · ${c.active_jobs} вакансий</span>
                        </div>
                        <svg class="search-result-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </a>
                `).join('');
            }

            results.innerHTML = html;

        } catch (e) {
            results.innerHTML = `<div class="search-overlay-hint">Ошибка поиска. Попробуйте ещё раз.</div>`;
        }
    },

    _injectSearchStyles() {
        if (document.getElementById('searchOverlayStyles')) return;

        const style = document.createElement('style');
        style.id = 'searchOverlayStyles';
        style.textContent = `
            .search-overlay {
                position: fixed;
                inset: 0;
                z-index: 9999;
                display: flex;
                align-items: flex-start;
                justify-content: center;
                padding-top: 80px;
                padding: 80px 16px 16px;
            }
            .search-overlay-backdrop {
                position: absolute;
                inset: 0;
                background: rgba(0,0,0,0.5);
                backdrop-filter: blur(4px);
            }
            .search-overlay-dialog {
                position: relative;
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 16px;
                width: 100%;
                max-width: 640px;
                box-shadow: 0 25px 50px rgba(0,0,0,0.25);
                overflow: hidden;
                animation: modalSlideIn 0.2s ease;
            }
            .search-overlay-input-wrap {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 16px 20px;
                border-bottom: 1px solid var(--border);
            }
            .search-overlay-icon { color: var(--text-tertiary); flex-shrink: 0; }
            .search-overlay-input {
                flex: 1;
                border: none;
                outline: none;
                font-size: 17px;
                color: var(--text-primary);
                background: transparent;
                font-family: var(--font);
            }
            .search-overlay-input::placeholder { color: var(--text-tertiary); }
            .search-overlay-close {
                background: none;
                border: none;
                color: var(--text-tertiary);
                cursor: pointer;
                display: flex;
                align-items: center;
                padding: 4px;
                border-radius: 6px;
                transition: all 0.15s;
            }
            .search-overlay-close:hover {
                background: var(--bg-secondary);
                color: var(--text-primary);
            }
            .search-overlay-results {
                max-height: 420px;
                overflow-y: auto;
                padding: 8px;
            }
            .search-overlay-hint {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 24px;
                text-align: center;
                color: var(--text-tertiary);
                font-size: 14px;
                justify-content: center;
            }
            .search-loading {
                display: flex;
                justify-content: center;
                padding: 24px;
            }
            .search-no-results {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 10px;
                padding: 32px;
                color: var(--text-tertiary);
                font-size: 14px;
                text-align: center;
            }
            .search-no-results svg { opacity: 0.4; }
            .search-section-title {
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                color: var(--text-tertiary);
                padding: 12px 12px 6px;
            }
            .search-result-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 12px;
                border-radius: 10px;
                text-decoration: none;
                transition: background 0.15s;
                cursor: pointer;
            }
            .search-result-item:hover { background: var(--bg-secondary); }
            .search-result-icon {
                width: 36px;
                height: 36px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                overflow: hidden;
            }
            .search-icon-job { background: var(--primary-light); color: var(--primary); }
            .search-icon-company { background: var(--bg-secondary); border: 1px solid var(--border); }
            .search-result-info { flex: 1; min-width: 0; }
            .search-result-title {
                display: block;
                font-size: 14px;
                font-weight: 600;
                color: var(--text-primary);
                margin-bottom: 2px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .search-result-sub {
                display: block;
                font-size: 12px;
                color: var(--text-tertiary);
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .search-result-arrow { color: var(--text-tertiary); flex-shrink: 0; }
            .search-see-all {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 10px;
                color: var(--primary);
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
                text-decoration: none;
                transition: background 0.15s;
                margin: 4px 0;
            }
            .search-see-all:hover { background: var(--primary-light); }
            .search-overlay-footer {
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 10px 20px;
                border-top: 1px solid var(--border);
                font-size: 12px;
                color: var(--text-tertiary);
                background: var(--bg-secondary);
            }
            .search-kbd {
                display: inline-flex;
                align-items: center;
                padding: 2px 6px;
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                color: var(--text-secondary);
                margin-right: 4px;
            }
        `;
        document.head.appendChild(style);
    },
};

function escapeHtmlSearch(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// Initialize search
document.addEventListener('DOMContentLoaded', () => {
    Search.init();
});