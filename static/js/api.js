/**
 * Turkmen Search — API Client
 * Handles all HTTP requests to the backend
 */

const API = {
    baseURL: '',

    async request(method, endpoint, data = null, requireAuth = false) {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        };

        if (requireAuth) {
            const token = Auth.getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }

        const options = {
            method,
            headers,
        };

        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(this.baseURL + endpoint, options);
            const result = await response.json();

            if (!response.ok) {
                const error = new Error(result.error || result.message || 'Ошибка запроса');
                error.status = response.status;
                error.data = result;
                throw error;
            }

            return result;

        } catch (err) {
            if (err.status === 401) {
                // Token expired or invalid
                const refreshed = await this._tryRefreshToken();
                if (refreshed && requireAuth) {
                    return this.request(method, endpoint, data, requireAuth);
                } else {
                    Auth.logout();
                    if (!window.location.pathname.includes('/login')) {
                        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
                    }
                }
            }
            throw err;
        }
    },

    async _tryRefreshToken() {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return false;

        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${refreshToken}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                Auth.setToken(data.access_token);
                return true;
            }
        } catch (e) {}
        return false;
    },

    async get(endpoint, requireAuth = false) {
        return this.request('GET', endpoint, null, requireAuth);
    },

    async post(endpoint, data, requireAuth = false) {
        return this.request('POST', endpoint, data, requireAuth);
    },

    async put(endpoint, data, requireAuth = false) {
        return this.request('PUT', endpoint, data, requireAuth);
    },

    async patch(endpoint, data, requireAuth = false) {
        return this.request('PATCH', endpoint, data, requireAuth);
    },

    async delete(endpoint, requireAuth = false) {
        return this.request('DELETE', endpoint, null, requireAuth);
    },

    async uploadFile(endpoint, formData, requireAuth = true) {
        const headers = {};
        if (requireAuth) {
            const token = Auth.getToken();
            if (token) headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(this.baseURL + endpoint, {
                method: 'POST',
                headers,
                body: formData,
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Ошибка загрузки');
            }
            return result;
        } catch (err) {
            throw err;
        }
    },
};

/**
 * Auth Manager
 */
const Auth = {
    TOKEN_KEY: 'ts_access_token',
    REFRESH_KEY: 'ts_refresh_token',
    USER_KEY: 'ts_user',

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    setToken(token) {
        localStorage.setItem(this.TOKEN_KEY, token);
    },

    getRefreshToken() {
        return localStorage.getItem(this.REFRESH_KEY);
    },

    setRefreshToken(token) {
        localStorage.setItem(this.REFRESH_KEY, token);
    },

    getUser() {
        try {
            const userData = localStorage.getItem(this.USER_KEY);
            return userData ? JSON.parse(userData) : null;
        } catch (e) {
            return null;
        }
    },

    setUser(user) {
        localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    },

    isLoggedIn() {
        return !!this.getToken();
    },

    logout() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.REFRESH_KEY);
        localStorage.removeItem(this.USER_KEY);
    },

    hasRole(role) {
        const user = this.getUser();
        return user && user.role === role;
    },

    isEmployer() {
        return this.hasRole('employer') || this.hasRole('admin');
    },

    isAdmin() {
        return this.hasRole('admin');
    },
};