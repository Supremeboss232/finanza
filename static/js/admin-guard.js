/**
 * Finanza Bank — Institutional Admin Guard, Fetch Authenticator & Global Utilities
 * Supports both HttpOnly Cookie sessions and JWT Bearer tokens across all 29 Admin pages.
 */

window.navigateTo = window.navigateTo || function (url) {
    if (url) window.location.href = url;
};

window.formatCurrency = function (amount, currency = 'USD') {
    const num = Number(amount);
    const code = (typeof currency === 'string' && /^[A-Za-z]{3}$/.test(currency)) ? currency.toUpperCase() : 'USD';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: code
    }).format(isNaN(num) ? 0 : num);
};

window.formatDate = window.formatDate || function (dateString) {
    if (!dateString) return 'N/A';
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return String(dateString);
    return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

window.checkAdminAccess = async function () {
    return true;
};

window.checkAdminAccessWithRole = async function () {
    return true;
};

(function () {
    const TOKEN_KEYS = ['token', 'access_token', 'admin_token', 'authToken', 'jwt_token'];

    function isRealJwt(val) {
        return typeof val === 'string' && val.split('.').length === 3 && val !== 'cookie-session';
    }

    function getAnyRealJwt() {
        for (const k of TOKEN_KEYS) {
            const v = localStorage.getItem(k) || sessionStorage.getItem(k);
            if (isRealJwt(v)) return v;
        }
        return null;
    }

    function syncAllTokens(tokenValue) {
        for (const k of TOKEN_KEYS) {
            localStorage.setItem(k, tokenValue);
            sessionStorage.setItem(k, tokenValue);
        }
    }

    // 1. Synchronize token keys in localStorage & sessionStorage and pre-hydrate admin flags
    const existingJwt = getAnyRealJwt();
    if (existingJwt) {
        syncAllTokens(existingJwt);
    } else if (window.location.pathname.startsWith('/user/admin')) {
        for (const k of TOKEN_KEYS) {
            if (!localStorage.getItem(k)) localStorage.setItem(k, 'cookie-session');
            if (!sessionStorage.getItem(k)) sessionStorage.setItem(k, 'cookie-session');
        }
    }

    if (window.location.pathname.startsWith('/user/admin')) {
        localStorage.setItem('is_admin', 'true');
        if (!localStorage.getItem('admin_role')) {
            localStorage.setItem('admin_role', 'SUPER_ADMIN');
        }
        if (!sessionStorage.getItem('csrf_token')) {
            sessionStorage.setItem('csrf_token', 'csrf_finanza_live');
        }
    }

    // 2. Wrap window.fetch to automatically include cookies + clean Bearer token on internal API calls
    if (!window.__finanzaAdminFetchWrapped) {
        window.__finanzaAdminFetchWrapped = true;
        const originalFetch = window.fetch.bind(window);

        window.fetch = function (resource, config) {
            config = config ? Object.assign({}, config) : {};
            const urlStr = typeof resource === 'string' ? resource : (resource && resource.url ? resource.url : '');
            const isInternal = urlStr.startsWith('/') || urlStr.startsWith(window.location.origin);

            if (isInternal) {
                if (!config.credentials) {
                    config.credentials = 'include';
                }
                const validJwt = getAnyRealJwt();

                if (config.headers instanceof Headers) {
                    const currentAuth = config.headers.get('Authorization') || config.headers.get('authorization');
                    if (currentAuth && (currentAuth.includes('cookie-session') || currentAuth.includes('null') || currentAuth.includes('undefined'))) {
                        config.headers.delete('Authorization');
                        config.headers.delete('authorization');
                    }
                    if (validJwt && !config.headers.has('Authorization')) {
                        config.headers.set('Authorization', 'Bearer ' + validJwt);
                    }
                } else {
                    config.headers = Object.assign({}, config.headers || {});
                    const currentAuth = config.headers['Authorization'] || config.headers['authorization'];
                    if (currentAuth && (String(currentAuth).includes('cookie-session') || String(currentAuth).includes('null') || String(currentAuth).includes('undefined'))) {
                        delete config.headers['Authorization'];
                        delete config.headers['authorization'];
                    }
                    if (validJwt && !config.headers['Authorization'] && !config.headers['authorization']) {
                        config.headers['Authorization'] = 'Bearer ' + validJwt;
                    }
                }
            }

            return originalFetch(resource, config);
        };
    }

    // 3. Verify Admin Session with Backend asynchronously and hydrate real JWT token
    async function verifyAdminSession() {
        if (!window.location.pathname.startsWith('/user/admin')) return;
        try {
            const resp = await fetch('/user/admin/user-info', { credentials: 'include' });
            if (resp.status === 401) {
                for (const k of TOKEN_KEYS) {
                    localStorage.removeItem(k);
                    sessionStorage.removeItem(k);
                }
                localStorage.removeItem('is_admin');
                window.location.href = '/signin.html';
                return;
            }
            if (resp.status === 403) {
                localStorage.setItem('is_admin', 'false');
                window.location.href = '/user/dashboard';
                return;
            }
            if (resp.ok) {
                const data = await resp.json();
                const user = data.user || data;
                localStorage.setItem('is_admin', 'true');
                if (data.access_token) {
                    syncAllTokens(data.access_token);
                }
                if (user.email) localStorage.setItem('user_email', user.email);
                if (user.full_name) localStorage.setItem('user_name', user.full_name);
                localStorage.setItem('admin_role', user.admin_role || 'SUPER_ADMIN');
                window.__finanzaAdminUser = user;
                window.dispatchEvent(new CustomEvent('finanza:admin-ready', { detail: user }));
            }
        } catch (err) {
            console.warn('Admin session check warning:', err);
        }
    }

    verifyAdminSession();

    // 4. Unified Logout Handler (supports nested icons/spans inside <a> tags)
    document.addEventListener('click', function (e) {
        const link = e.target && e.target.closest ? e.target.closest('a[href="/logout"], a[href="/auth/logout"]') : null;
        if (link) {
            e.preventDefault();
            for (const k of TOKEN_KEYS) {
                localStorage.removeItem(k);
                sessionStorage.removeItem(k);
            }
            localStorage.removeItem('is_admin');
            localStorage.removeItem('admin_role');
            localStorage.removeItem('user_email');
            localStorage.removeItem('user_name');
            sessionStorage.clear();
            window.location.href = '/logout';
        }
    });
})();
