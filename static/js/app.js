/**
 * Turkmen Search — Main App JavaScript
 * Core functionality: auth UI, navigation, toasts, utilities
 */

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    updateAuthUI();
    setupUserMenu();
    setupMobileMenu();
    setupNotificationsPanel();
    setupHeaderScroll();

    if (Auth.isLoggedIn()) {
        loadUnreadCounts();
        setInterval(loadUnreadCounts, 30000);
    }
}

/* ============================================
   AUTH UI
   ============================================ */
function updateAuthUI() {
    const isLoggedIn = Auth.isLoggedIn();
    const user = Auth.getUser();

    const authOnlyEls = document.querySelectorAll('.auth-only');
    const guestOnlyEls = document.querySelectorAll('.guest-only');

    authOnlyEls.forEach(el => {
        if (isLoggedIn) {
            el.classList.remove('hidden');
        } else {
            el.classList.add('hidden');
        }
    });

    guestOnlyEls.forEach(el => {
        if (isLoggedIn) {
            el.classList.add('hidden');
        } else {
            el.classList.remove('hidden');
        }
    });

    if (isLoggedIn && user) {
        const navUserName = document.getElementById('navUserName');
        const dropdownName = document.getElementById('dropdownName');
        const dropdownRole = document.getElementById('dropdownRole');

        if (navUserName) navUserName.textContent = user.name.split(' ')[0];
        if (dropdownName) dropdownName.textContent = user.name;
        if (dropdownRole) {
            const roleLabels = {
                jobseeker: 'Соискатель',
                employer: 'Работодатель',
                admin: 'Администратор',
            };
            dropdownRole.textContent = roleLabels[user.role] || user.role;
        }

        if (user.avatar) {
            const navAvatar = document.getElementById('navAvatar');
            if (navAvatar) {
                navAvatar.innerHTML = `<img src="/uploads/avatars/${user.avatar}" alt="${user.name}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
            }
        }

        // Role-specific elements
        if (user.role === 'employer' || user.role === 'admin') {
            document.querySelectorAll('.employer-only').forEach(el => el.classList.remove('hidden'));
            document.querySelectorAll('.jobseeker-only').forEach(el => el.classList.add('hidden'));
        } else {
            document.querySelectorAll('.jobseeker-only').forEach(el => el.classList.remove('hidden'));
            document.querySelectorAll('.employer-only').forEach(el => el.classList.add('hidden'));
        }

        // Hide resumes nav for employers
        const navResumes = document.getElementById('navResumes');
        if (navResumes && user.role === 'employer') {
            navResumes.textContent = 'База резюме';
        }
    }
}

/* ============================================
   USER MENU
   ============================================ */
function setupUserMenu() {
    const wrapper = document.getElementById('userMenuWrapper');
    const btn = document.getElementById('userMenuBtn');
    const dropdown = document.getElementById('userDropdown');
    const logoutBtn = document.getElementById('logoutBtn');
    const mobileLogout = document.getElementById('mobileLogoutBtn');

    if (btn) {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            wrapper.classList.toggle('open');
        });
    }

    document.addEventListener('click', (e) => {
        if (wrapper && !wrapper.contains(e.target)) {
            wrapper.classList.remove('open');
        }
    });

    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }

    if (mobileLogout) {
        mobileLogout.addEventListener('click', handleLogout);
    }
}

async function handleLogout() {
    try {
        await API.post('/api/auth/logout', {}, true);
    } catch (e) {}

    Auth.logout();
    showToast('Вы вышли из системы', 'info');
    setTimeout(() => window.location.href = '/', 600);
}

/* ============================================
   MOBILE MENU
   ============================================ */
function setupMobileMenu() {
    const toggle = document.getElementById('mobileMenuToggle');
    const menu = document.getElementById('mobileMenu');

    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => {
        const isOpen = menu.classList.toggle('open');
        document.body.style.overflow = isOpen ? 'hidden' : '';
        toggle.classList.toggle('active', isOpen);
    });

    // Close on link click
    menu.querySelectorAll('.mobile-nav-link').forEach(link => {
        link.addEventListener('click', () => {
            menu.classList.remove('open');
            document.body.style.overflow = '';
            toggle.classList.remove('active');
        });
    });
}

/* ============================================
   NOTIFICATIONS PANEL
   ============================================ */
function setupNotificationsPanel() {
    const btn = document.getElementById('notificationBtn');
    const panel = document.getElementById('notificationsPanel');
    const markAllBtn = document.getElementById('markAllReadBtn');
    const overlay = document.getElementById('overlay');

    if (!btn || !panel) return;

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden')) {
            loadNotifications();
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    });

    document.addEventListener('click', (e) => {
        if (!panel.contains(e.target) && !btn.contains(e.target)) {
            panel.classList.add('hidden');
            overlay.classList.add('hidden');
        }
    });

    if (markAllBtn) {
        markAllBtn.addEventListener('click', async () => {
            try {
                await API.post('/api/auth/notifications/read-all', {}, true);
                loadNotifications();
                updateNotificationBadge(0);
                showToast('Все уведомления прочитаны', 'success');
            } catch (e) {}
        });
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            panel.classList.add('hidden');
            overlay.classList.add('hidden');
        });
    }
}

async function loadNotifications() {
    const list = document.getElementById('notificationsList');
    if (!list || !Auth.isLoggedIn()) return;

    try {
        const data = await API.get('/api/auth/notifications?limit=10', true);
        const notifications = data.notifications || [];

        if (notifications.length === 0) {
            list.innerHTML = '<div class="notifications-empty"><p>Нет новых уведомлений</p></div>';
            return;
        }

        list.innerHTML = notifications.slice(0, 10).map(n => `
            <div class="notification-item ${n.is_read ? '' : 'unread'}" onclick="handleNotificationClick(${n.id}, '${n.link || ''}')">
                <div class="notification-item-content">
                    <div class="notification-item-title">${n.title}</div>
                    <div class="notification-item-text">${n.text}</div>
                    <span class="notification-item-time">${formatTimeAgoShort(n.created_at)}</span>
                </div>
            </div>
        `).join('');

        const unread = notifications.filter(n => !n.is_read).length;
        updateNotificationBadge(unread);

    } catch (e) {
        if (list) {
            list.innerHTML = '<div class="notifications-empty"><p>Ошибка загрузки</p></div>';
        }
    }
}

async function handleNotificationClick(id, link) {
    try {
        await API.put(`/api/auth/notifications/${id}/read`, {}, true);
    } catch (e) {}

    document.getElementById('notificationsPanel').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');

    if (link) window.location.href = link;
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notifBadge');
    if (!badge) return;

    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

/* ============================================
   UNREAD COUNTS
   ============================================ */
async function loadUnreadCounts() {
    if (!Auth.isLoggedIn()) return;

    try {
        // Messages
        const msgData = await API.get('/api/messages/unread-count', true);
        const msgBadge = document.getElementById('msgBadge');
        if (msgBadge) {
            const count = msgData.unread_count || 0;
            if (count > 0) {
                msgBadge.textContent = count > 99 ? '99+' : count;
                msgBadge.classList.remove('hidden');
            } else {
                msgBadge.classList.add('hidden');
            }
        }

        // Notifications
        const notifData = await API.get('/api/auth/notifications?limit=1', true);
        const unread = (notifData.notifications || []).filter(n => !n.is_read).length;
        updateNotificationBadge(unread);

    } catch (e) {}
}

/* ============================================
   HEADER SCROLL BEHAVIOR
   ============================================ */
function setupHeaderScroll() {
    const header = document.getElementById('mainHeader');
    if (!header) return;

    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const current = window.scrollY;

        if (current > 80) {
            header.style.boxShadow = 'var(--shadow-md)';
        } else {
            header.style.boxShadow = 'var(--shadow-xs)';
        }

        lastScroll = current;
    }, { passive: true });
}

/* ============================================
   TOAST NOTIFICATIONS
   ============================================ */
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`,
        error: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
        info: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
        warning: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => {
            if (toast.parentNode === container) {
                container.removeChild(toast);
            }
        }, 300);
    }, duration);
}

/* ============================================
   RENDER HELPERS (shared across pages)
   ============================================ */
function renderJobCard(job) {
    const company = job.company || {};
    const logoHtml = company.logo
        ? `<img src="/uploads/logos/${company.logo}" alt="${company.name}" class="company-logo-img">`
        : `<div class="company-logo-placeholder">${(company.name || 'C')[0]}</div>`;

    return `
        <a href="/jobs/${job.id}" class="job-card">
            ${job.is_hot ? '<span class="badge badge-hot" style="position:absolute;top:12px;right:12px;">🔥 Горячая</span>' : ''}
            <div class="job-card-top">
                <div class="job-card-logo">${logoHtml}</div>
                <div class="job-card-info">
                    <div class="job-card-title">${job.title}</div>
                    <div class="job-card-company">${company.name || ''}</div>
                </div>
                <div class="job-card-salary">${job.salary}</div>
            </div>
            <div class="job-card-tags">
                <span class="job-tag">${job.employment_display || ''}</span>
                ${job.remote ? '<span class="job-tag">Удалённо</span>' : ''}
                ${job.experience_display ? `<span class="job-tag">${job.experience_display}</span>` : ''}
            </div>
            <div class="job-card-footer">
                <span class="job-card-city">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                    ${job.city}
                </span>
                <span class="job-card-date">${formatDate(job.created_at)}</span>
            </div>
        </a>`;
}

function renderJobListItem(job) {
    const company = job.company || {};
    const logoHtml = company.logo
        ? `<img src="/uploads/logos/${company.logo}" alt="${company.name}" class="company-logo-img">`
        : `<div class="company-logo-placeholder" style="font-size:16px;">${(company.name || 'C')[0]}</div>`;

    return `
        <a href="/jobs/${job.id}" class="job-list-item">
            <div class="job-list-logo">${logoHtml}</div>
            <div class="job-list-info">
                <span class="job-list-title">${job.title}${job.is_hot ? ' 🔥' : ''}</span>
                <span class="job-list-company">${company.name || ''}</span>
                <div class="job-list-tags">
                    <span class="job-tag">${job.city}</span>
                    <span class="job-tag">${job.employment_display || ''}</span>
                    ${job.experience_display ? `<span class="job-tag">${job.experience_display}</span>` : ''}
                    ${job.remote ? '<span class="job-tag">Удалённо</span>' : ''}
                </div>
            </div>
            <div class="job-list-right">
                <span class="job-list-salary">${job.salary}</span>
                <span class="job-list-date">${formatDate(job.created_at)}</span>
            </div>
        </a>`;
}

function renderCompanyCard(company) {
    const logoHtml = company.logo
        ? `<img src="/uploads/logos/${company.logo}" alt="${company.name}" style="width:56px;height:56px;object-fit:contain;border-radius:8px;">`
        : `<div style="width:56px;height:56px;border-radius:8px;background:var(--primary-light);display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;color:var(--primary);">${company.name[0]}</div>`;

    return `
        <a href="/companies/${company.id}" class="company-card">
            ${logoHtml}
            <div style="font-size:14px;font-weight:700;color:var(--text-primary);text-align:center;">${company.name}</div>
            ${company.city ? `<div style="font-size:12px;color:var(--text-tertiary);">${company.city}</div>` : ''}
            <div style="font-size:12px;color:var(--primary);font-weight:600;">
                ${company.active_jobs} ${pluralize(company.active_jobs, 'вакансия', 'вакансии', 'вакансий')}
            </div>
        </a>`;
}

/* ============================================
   DATE & NUMBER FORMATTERS
   ============================================ */
function formatDate(isoString) {
    if (!isoString) return '';
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        if (diff < 3600) return 'только что';
        if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
        if (diff < 172800) return 'вчера';
        if (diff < 2592000) return `${Math.floor(diff / 86400)} дн назад`;

        return date.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
        });
    } catch (e) {
        return '';
    }
}

function formatTimeAgoShort(isoString) {
    if (!isoString) return '';
    try {
        const date = new Date(isoString);
        const diff = Math.floor((new Date() - date) / 1000);

        if (diff < 60) return 'сейчас';
        if (diff < 3600) return `${Math.floor(diff / 60)}м`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}ч`;
        if (diff < 604800) return `${Math.floor(diff / 86400)}д`;
        return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
    } catch (e) {
        return '';
    }
}

function formatNumber(num) {
    if (!num && num !== 0) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toLocaleString('ru-RU');
}

function pluralize(n, one, few, many) {
    const abs = Math.abs(n);
    const mod10 = abs % 10;
    const mod100 = abs % 100;

    if (mod100 >= 11 && mod100 <= 14) return many;
    if (mod10 === 1) return one;
    if (mod10 >= 2 && mod10 <= 4) return few;
    return many;
}

/* ============================================
   NOTIFICATION ROUTES (needed by routes)
   ============================================ */

// These endpoints need to be added to auth_routes.py
// Appending to auth_routes blueprint:
const _notifRoutes = `
# These are implemented in auth_routes.py:
# GET  /api/auth/notifications
# POST /api/auth/notifications/read-all
# PUT  /api/auth/notifications/<id>/read
`;