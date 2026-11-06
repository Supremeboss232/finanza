/**
 * Finanza Bank — Institutional Admin Guard, RBAC Matrix Helper & Fetch Authenticator
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

window.DEFAULT_ROLE_MATRIX = {
    SUPER_ADMIN: {
        role: "SUPER_ADMIN",
        title: "Super Administrator",
        badge_color: "#e74c3c",
        summary: "Unrestricted executive authority across all users, treasury, compliance, payment rails, vendor gateways, and admin governance.",
        can_do: [
            "Create, promote, change roles, reset passwords, and revoke other Administrators",
            "Override granular permissions and manage Admin MFA / 2FA security",
            "Create, edit, suspend, freeze, unfreeze, and permanently delete user accounts",
            "Fund, credit, debit, adjust, and reconcile user and institutional reserve balances",
            "Approve or reject KYC submissions, loans, mobile deposits, and high-value wires",
            "Configure bank gateways, vendor API credentials, webhooks, and system settings"
        ],
        cannot_do: [
            "Cannot bypass immutable Audit Log recording (all Super Admin actions are logged)"
        ],
        permissions: ["*"]
    },
    ADMIN: {
        role: "ADMIN",
        title: "Operations Administrator",
        badge_color: "#3498db",
        summary: "Day-to-day banking operations across customer accounts, KYC verification, lending, deposits, cards, and support.",
        can_do: [
            "View, create, edit, suspend, freeze, and unfreeze customer accounts",
            "Review, approve, and reject KYC identity verification submissions",
            "Review and approve/reject loan applications, mobile check deposits, and cards",
            "View transactions, approve pending transfers, and execute bulk user operations",
            "Access Advanced Search, Activity Dashboard, and operational reports"
        ],
        cannot_do: [
            "Cannot create, revoke, or change roles of other Admin accounts",
            "Cannot modify institutional Treasury reserves or global Risk Parameters",
            "Cannot permanently delete user accounts or alter core system/vendor API keys"
        ],
        permissions: [
            "users:view", "user:view", "users:create", "user:create", "users:edit", "user:edit",
            "users:suspend", "users:freeze", "users:bulk_actions",
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            "transactions:view", "transaction:view", "transactions:create", "transactions:approve", "transaction:approve",
            "deposits:view", "deposits:approve", "loans:view", "loans:approve", "loans:reject",
            "investments:view", "cards:view", "cards:manage", "reports:view", "audit:view", "aml:view", "admin:view"
        ]
    },
    TREASURY: {
        role: "TREASURY",
        title: "Treasury & Settlement Officer",
        badge_color: "#2ecc71",
        summary: "Controls institutional liquidity, customer balance funding/adjustments, ACH/Wire/FedNow settlement, FX rates, and investments.",
        can_do: [
            "Credit, debit, and adjust customer account balances and manage account holds",
            "Manage institutional Treasury portfolios, liquidity pools, and risk parameters",
            "Process ACH batches, Wire settlements, FedNow/RTP clearing, and NSF fee actions",
            "Manage live FX exchange rates, currency exchange, and blockchain settlement",
            "Approve deposits, disburse approved loans, and generate financial/treasury reports"
        ],
        cannot_do: [
            "Cannot create, modify, or revoke Admin accounts or change role permissions",
            "Cannot approve or reject customer KYC identity documents",
            "Cannot delete customer accounts or edit system-wide vendor secrets"
        ],
        permissions: [
            "users:view", "user:view", "users:adjust_balance", "balance:adjust", "balance:reconcile", "fund:transfer",
            "transactions:view", "transaction:view", "transactions:create", "transactions:approve", "transaction:approve",
            "transactions:reject", "transaction:reject", "transactions:reverse", "transaction:reverse",
            "treasury:view", "treasury:manage", "settlement:manage", "ach:manage", "fx:manage",
            "deposits:view", "deposits:approve", "investments:view", "investments:manage",
            "loans:view", "cards:view", "reports:view", "reports:generate", "audit:view"
        ]
    },
    COMPLIANCE: {
        role: "COMPLIANCE",
        title: "Compliance & AML Officer",
        badge_color: "#f39c12",
        summary: "Oversees KYC/KYB verification, OFAC sanctions screening, fraud detection, HMDA/lending compliance, and regulatory reporting.",
        can_do: [
            "Review, verify, approve, and reject customer KYC/KYB identity submissions",
            "Run OFAC SDN sanctions checks, PEP screening, and international compliance reviews",
            "Investigate Fraud Detection alerts and freeze/flag high-risk accounts",
            "Audit HMDA LAR records, Lending Compliance, and immutable Admin Audit Logs",
            "Generate and export regulatory, AML, and compliance reports"
        ],
        cannot_do: [
            "Cannot credit, debit, or adjust customer or treasury monetary balances",
            "Cannot create, edit, or revoke Admin accounts",
            "Cannot process ACH/Wire settlement batches or change vendor API keys"
        ],
        permissions: [
            "users:view", "user:view", "users:freeze",
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            "transactions:view", "transaction:view", "deposits:view", "loans:view",
            "compliance:view", "compliance:manage", "compliance:report", "aml:view", "fraud:manage",
            "reports:view", "reports:generate", "audit:view"
        ]
    },
    SUPPORT: {
        role: "SUPPORT",
        title: "Customer Support Specialist",
        badge_color: "#9b59b6",
        summary: "Read-only customer service access across profiles, balances, transactions, and KYC status, plus customer password/lockout assistance.",
        can_do: [
            "Search and view customer profiles, account status, and verification progress",
            "View transaction history, card status, bill pay records, and deposit status",
            "Assist customers with password resets and account lockout recovery",
            "View activity logs and basic operational dashboards"
        ],
        cannot_do: [
            "Cannot credit, debit, or adjust any customer or institutional balances",
            "Cannot approve or reject KYC documents, loans, or transactions",
            "Cannot suspend, freeze, or delete user accounts",
            "Cannot create or manage Admin accounts, Treasury, or System Settings"
        ],
        permissions: [
            "users:view", "user:view", "kyc:view", "transactions:view", "transaction:view",
            "deposits:view", "loans:view", "investments:view", "cards:view", "reports:view", "audit:view"
        ]
    }
};

window.FinanzaAdminRBAC = {
    getRole: function () {
        return (window.__finanzaAdminUser && window.__finanzaAdminUser.admin_role) ||
               localStorage.getItem('admin_role') || 'SUPER_ADMIN';
    },
    getPermissions: function () {
        if (window.__finanzaAdminUser && Array.isArray(window.__finanzaAdminUser.permissions)) {
            return window.__finanzaAdminUser.permissions;
        }
        try {
            const stored = JSON.parse(localStorage.getItem('admin_permissions') || 'null');
            if (Array.isArray(stored)) return stored;
        } catch (e) {}
        const role = this.getRole();
        const matrix = this.getRoleMatrix();
        return (matrix[role] && matrix[role].permissions) || ['*'];
    },
    hasPermission: function (perm) {
        const role = this.getRole();
        if (role === 'SUPER_ADMIN') return true;
        const perms = this.getPermissions();
        return perms.includes('*') || perms.includes(perm);
    },
    getRoleMatrix: function () {
        return window.__finanzaRoleMatrix || window.DEFAULT_ROLE_MATRIX;
    },
    getRoleInfo: function (roleName) {
        const r = (roleName || this.getRole() || 'ADMIN').toUpperCase();
        const matrix = this.getRoleMatrix();
        return matrix[r] || matrix.ADMIN;
    }
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
                window.location.href = '/signin?logged_out=1';
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
                const role = data.admin_role || user.admin_role || 'SUPER_ADMIN';
                const permsList = data.permissions_list || user.permissions || ['*'];
                localStorage.setItem('admin_role', role);
                localStorage.setItem('admin_permissions', JSON.stringify(permsList));
                if (data.role_matrix) {
                    window.__finanzaRoleMatrix = data.role_matrix;
                }
                user.admin_role = role;
                user.permissions = permsList;
                user.role_info = data.role_info || window.FinanzaAdminRBAC.getRoleInfo(role);
                window.__finanzaAdminUser = user;
                window.dispatchEvent(new CustomEvent('finanza:admin-ready', { detail: user }));
            }
        } catch (err) {
            console.warn('Admin session check warning:', err);
        }
    }

    verifyAdminSession();

    window.executeAdminLogout = function (e) {
        if (e && e.preventDefault) e.preventDefault();
        try {
            fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' }).catch(function(){});
            fetch('/user/logout', { method: 'GET', credentials: 'include' }).catch(function(){});
        } catch (err) {}
        localStorage.clear();
        sessionStorage.clear();
        document.cookie = 'access_token=; Max-Age=0; path=/';
        document.cookie = 'token=; Max-Age=0; path=/';
        window.location.href = '/logout';
    };

    document.addEventListener('click', function (e) {
        const link = e.target && e.target.closest ? e.target.closest('a[href="/logout"], a[href="/user/logout"], a[href="/auth/logout"], [data-action="admin-logout"]') : null;
        if (link) {
            window.executeAdminLogout(e);
        }
    });
})();
