/**
 * Finanza Bank — Institutional Admin Guard, RBAC Matrix Helper & Fetch Authenticator
 * Supports both HttpOnly Cookie sessions and JWT Bearer tokens across all 29 Admin pages.
 * Enforces the 5-Tier Admin Role & Privilege Matrix (SUPER_ADMIN, ADMIN, TREASURY, COMPLIANCE, SUPPORT).
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

window.DEFAULT_ROLE_MATRIX = {
    SUPER_ADMIN: {
        role: "SUPER_ADMIN",
        title: "Super Administrator",
        default_account: "admin@admin.com",
        badge_color: "#dc2626",
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
            "Cannot bypass immutable Audit Log recording (all Super Admin actions are logged)",
            "Cannot revoke own SUPER_ADMIN status or delete own root account (self-lockout protection)"
        ],
        allowed_pages: ["*"],
        restricted_pages: [],
        permissions: ["*"]
    },
    ADMIN: {
        role: "ADMIN",
        title: "Operations Administrator",
        default_account: "admin@finanza.com",
        badge_color: "#2563eb",
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
        allowed_pages: [
            "/user/admin/dashboard", "/user/admin/users", "/user/admin/kyc",
            "/user/admin/transactions", "/user/admin/fund", "/user/admin/lending",
            "/user/admin/lending_compliance", "/user/admin/hmda", "/user/admin/bill_pay",
            "/user/admin/mobile_deposit", "/user/admin/bulk_operations", "/user/admin/advanced_search",
            "/user/admin/reporting", "/user/admin/activity_dashboard", "/user/admin/monitoring",
            "/user/admin/profile", "/user/admin/mfa_setup"
        ],
        restricted_pages: [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/treasury", "/user/admin/bank_connect", "/user/admin/webhooks"
        ],
        permissions: [
            "users:view", "user:view", "users:create", "user:create", "users:edit", "user:edit",
            "users:suspend", "user:suspend", "users:freeze", "user:freeze", "users:bulk_actions",
            "ledger:adjust", "balance:adjust", "users:adjust_balance", "balance:limit_change",
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            "transactions:view", "transaction:view", "transactions:create", "transaction:create",
            "transactions:approve", "transaction:approve", "transactions:reject", "transaction:reject",
            "transactions:reverse", "transaction:reverse", "transaction:cancel", "payments:settle",
            "deposits:view", "deposits:approve", "loans:view", "loans:approve", "loans:reject",
            "loans:credit_decision", "loans:underwrite", "loans:disburse",
            "investments:view", "investments:manage", "cards:view", "cards:approve", "cards:manage",
            "treasury:view", "reports:view", "reporting:view", "audit:view", "aml:view", "admin:view", "support:manage"
        ]
    },
    TREASURY: {
        role: "TREASURY",
        title: "Treasury & Settlement Officer",
        default_account: "treasury@finanza.com",
        badge_color: "#059669",
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
        allowed_pages: [
            "/user/admin/dashboard", "/user/admin/treasury", "/user/admin/settlement",
            "/user/admin/ach_management", "/user/admin/bank_connect", "/user/admin/fund",
            "/user/admin/currency_exchange", "/user/admin/blockchain", "/user/admin/transactions",
            "/user/admin/lending", "/user/admin/mobile_deposit", "/user/admin/bill_pay",
            "/user/admin/reporting", "/user/admin/monitoring", "/user/admin/profile",
            "/user/admin/mfa_setup"
        ],
        restricted_pages: [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/kyc", "/user/admin/bulk_operations", "/user/admin/fraud_detection",
            "/user/admin/international_compliance"
        ],
        permissions: [
            "users:view", "user:view", "ledger:adjust", "balance:adjust", "users:adjust_balance",
            "balance:reconcile", "balance:limit_change", "fund:transfer",
            "transactions:view", "transaction:view", "transactions:create", "transaction:create",
            "transactions:approve", "transaction:approve", "transactions:reject", "transaction:reject",
            "transactions:reverse", "transaction:reverse", "payments:settle",
            "treasury:view", "treasury:manage", "settlement:manage", "ach:manage", "fx:manage",
            "deposits:view", "deposits:approve", "investments:view", "investments:manage",
            "loans:view", "loans:disburse", "cards:view", "reports:view", "reports:generate",
            "reporting:view", "audit:view", "admin:view"
        ]
    },
    COMPLIANCE: {
        role: "COMPLIANCE",
        title: "Compliance & AML Officer",
        default_account: "compliance@finanza.com",
        badge_color: "#d97706",
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
        allowed_pages: [
            "/user/admin/dashboard", "/user/admin/kyc", "/user/admin/fraud_detection",
            "/user/admin/international_compliance", "/user/admin/lending_compliance",
            "/user/admin/hmda", "/user/admin/activity_dashboard", "/user/admin/reporting",
            "/user/admin/users", "/user/admin/transactions", "/user/admin/advanced_search",
            "/user/admin/monitoring", "/user/admin/profile", "/user/admin/mfa_setup"
        ],
        restricted_pages: [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/treasury", "/user/admin/fund", "/user/admin/settlement",
            "/user/admin/ach_management", "/user/admin/blockchain", "/user/admin/currency_exchange",
            "/user/admin/bulk_operations"
        ],
        permissions: [
            "users:view", "user:view", "users:suspend", "user:suspend", "users:freeze", "user:freeze",
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            "transactions:view", "transaction:view", "deposits:view", "loans:view",
            "compliance:view", "compliance:manage", "compliance:report", "aml:view", "fraud:manage",
            "reports:view", "reports:generate", "reporting:view", "audit:view", "audit:export", "admin:view"
        ]
    },
    SUPPORT: {
        role: "SUPPORT",
        title: "Customer Support Specialist",
        default_account: "support@finanza.com",
        badge_color: "#7c3aed",
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
        allowed_pages: [
            "/user/admin/dashboard", "/user/admin/users", "/user/admin/transactions",
            "/user/admin/advanced_search", "/user/admin/activity_dashboard",
            "/user/admin/monitoring", "/user/admin/profile", "/user/admin/mfa_setup"
        ],
        restricted_pages: [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/treasury", "/user/admin/fund", "/user/admin/settlement",
            "/user/admin/ach_management", "/user/admin/kyc", "/user/admin/bulk_operations",
            "/user/admin/lending", "/user/admin/lending_compliance", "/user/admin/hmda",
            "/user/admin/fraud_detection", "/user/admin/international_compliance",
            "/user/admin/blockchain", "/user/admin/currency_exchange", "/user/admin/bank_connect",
            "/user/admin/webhooks"
        ],
        permissions: [
            "users:view", "user:view", "kyc:view", "transactions:view", "transaction:view",
            "deposits:view", "loans:view", "investments:view", "cards:view",
            "reports:view", "reporting:view", "audit:view", "admin:view", "support:manage"
        ]
    }
};

function normalizeAdminPath(path) {
    if (!path) return "/user/admin/dashboard";
    let clean = path.split("?")[0].replace(/\/+$/, "");
    if (!clean || clean === "/user/admin" || clean === "/user/superadmin/dashboard") {
        return "/user/admin/dashboard";
    }
    if (clean.endsWith(".html")) clean = clean.slice(0, -5);
    const parts = clean.split("/");
    let slug = (parts[parts.length - 1] || "dashboard").replace(/-/g, "_");
    if (slug.startsWith("admin_") && slug !== "admin_management_panel") {
        slug = slug.slice("admin_".length);
    }
    const aliases = {
        dashboard_hub: "dashboard",
        superadmin_dashboard: "dashboard",
        overview: "monitoring",
        executive_dashboard: "monitoring",
        reports: "reporting",
        submissions: "kyc",
        compliance: "international_compliance",
        wire_transfer: "settlement"
    };
    slug = aliases[slug] || slug;
    return "/user/admin/" + slug;
}

window.FinanzaAdminRBAC = {
    getActualRole: function () {
        return (window.__finanzaAdminUser && window.__finanzaAdminUser.admin_role) ||
               localStorage.getItem('admin_role') || 'SUPER_ADMIN';
    },
    getPreviewRole: function () {
        return sessionStorage.getItem('finanza_preview_role') || null;
    },
    setPreviewRole: function (roleName) {
        if (!roleName || roleName === this.getActualRole()) {
            sessionStorage.removeItem('finanza_preview_role');
        } else {
            sessionStorage.setItem('finanza_preview_role', roleName.toUpperCase());
        }
        window.dispatchEvent(new CustomEvent('finanza:role-changed', {
            detail: { role: this.getRole(), isPreview: Boolean(this.getPreviewRole()) }
        }));
        this.enforcePageAndActions();
    },
    getRole: function () {
        const preview = this.getPreviewRole();
        if (preview) return preview;
        return this.getActualRole();
    },
    getPermissions: function () {
        const preview = this.getPreviewRole();
        const matrix = this.getRoleMatrix();
        if (preview && matrix[preview]) {
            return matrix[preview].permissions || [];
        }
        if (window.__finanzaAdminUser && Array.isArray(window.__finanzaAdminUser.permissions)) {
            return window.__finanzaAdminUser.permissions;
        }
        try {
            const stored = JSON.parse(localStorage.getItem('admin_permissions') || 'null');
            if (Array.isArray(stored)) return stored;
        } catch (e) {}
        const role = this.getRole();
        return (matrix[role] && matrix[role].permissions) || ['*'];
    },
    hasPermission: function (perm) {
        const role = this.getRole();
        if (role === 'SUPER_ADMIN') return true;
        const perms = this.getPermissions();
        if (perms.includes('*') || perms.includes(perm)) return true;
        const alt = perm.replace('users:', 'user:').replace('transactions:', 'transaction:');
        const alt2 = perm.replace('user:', 'users:').replace('transaction:', 'transactions:');
        return perms.includes(alt) || perms.includes(alt2);
    },
    getRoleMatrix: function () {
        return window.__finanzaRoleMatrix || window.DEFAULT_ROLE_MATRIX;
    },
    getRoleInfo: function (roleName) {
        const r = (roleName || this.getRole() || 'ADMIN').toUpperCase();
        const matrix = this.getRoleMatrix();
        return matrix[r] || matrix.ADMIN;
    },
    canAccessPage: function (pagePath, roleOverride) {
        const role = (roleOverride || this.getRole() || 'SUPER_ADMIN').toUpperCase();
        if (role === 'SUPER_ADMIN') return true;
        const canonical = normalizeAdminPath(pagePath || window.location.pathname);
        if (['/user/admin/dashboard', '/user/admin/profile', '/user/admin/mfa_setup'].includes(canonical)) {
            return true;
        }
        const info = this.getRoleInfo(role);
        const restricted = (info.restricted_pages || []).map(normalizeAdminPath);
        if (restricted.includes(canonical)) {
            return false;
        }
        const allowed = info.allowed_pages || ['*'];
        if (allowed.includes('*')) return true;
        return allowed.map(normalizeAdminPath).includes(canonical);
    },
    enforcePageAndActions: function () {
        if (!window.location.pathname.startsWith('/user/admin')) return;
        const role = this.getRole();
        const roleInfo = this.getRoleInfo(role);
        const isPreview = Boolean(this.getPreviewRole());

        // 1. Preview Banner if Super Admin is previewing another tier
        let previewBar = document.getElementById('finanzaRolePreviewBanner');
        if (isPreview) {
            if (!previewBar) {
                previewBar = document.createElement('div');
                previewBar.id = 'finanzaRolePreviewBanner';
                previewBar.style.cssText = 'background:#1e293b;color:#f8fafc;padding:8px 20px;font-size:0.86rem;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #f59e0b;z-index:9998;';
                const nav = document.getElementById('finanzaUnifiedAdminNav');
                if (nav && nav.nextSibling) {
                    nav.parentNode.insertBefore(previewBar, nav.nextSibling);
                } else {
                    document.body.prepend(previewBar);
                }
            }
            previewBar.innerHTML = `
                <div>
                    <span style="background:#f59e0b;color:#0f172a;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:8px;">ROLE PREVIEW MODE</span>
                    Viewing Admin Portal as <strong style="color:#38bdf8;">${role} (${roleInfo.title})</strong> — restricted pages & prohibited actions are locked according to the Role Matrix.
                </div>
                <div style="display:flex;gap:8px;">
                    <button type="button" onclick="window.openAdminRolesMatrixModal && window.openAdminRolesMatrixModal()" style="background:#334155;color:#fff;border:1px solid #475569;padding:3px 10px;border-radius:5px;font-size:0.8rem;cursor:pointer;">Switch Tier</button>
                    <button type="button" onclick="window.FinanzaAdminRBAC.setPreviewRole(null)" style="background:#ef4444;color:#fff;border:none;padding:3px 10px;border-radius:5px;font-size:0.8rem;font-weight:600;cursor:pointer;">Exit Preview (Restore ${this.getActualRole()})</button>
                </div>
            `;
        } else if (previewBar) {
            previewBar.remove();
        }

        // 2. Check if current page is restricted for this role
        const allowedOnPage = this.canAccessPage(window.location.pathname, role);
        let restrictedBanner = document.getElementById('finanzaRoleRestrictedBanner');
        if (!allowedOnPage) {
            if (!restrictedBanner) {
                restrictedBanner = document.createElement('div');
                restrictedBanner.id = 'finanzaRoleRestrictedBanner';
                restrictedBanner.style.cssText = 'margin:18px auto;max-width:1180px;background:#fef2f2;border:2px solid #ef4444;border-radius:12px;padding:20px 24px;color:#7f1d1d;box-shadow:0 8px 24px rgba(239,68,68,0.12);';
                const nav = document.getElementById('finanzaUnifiedAdminNav');
                if (nav && nav.nextSibling) {
                    nav.parentNode.insertBefore(restrictedBanner, nav.nextSibling);
                } else {
                    document.body.prepend(restrictedBanner);
                }
            }
            const cannotListHtml = (roleInfo.cannot_do || []).map(c => `<li>${c}</li>`).join('');
            restrictedBanner.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:14px;">
                    <div>
                        <h5 style="margin:0 0 6px 0;font-weight:700;color:#991b1b;">
                            <i class="fas fa-lock me-2"></i>Restricted Module for Role: <span style="background:${roleInfo.badge_color};color:#fff;padding:2px 10px;border-radius:12px;font-size:0.82rem;">${role}</span>
                        </h5>
                        <p style="margin:0 0 8px 0;font-size:0.9rem;">
                            Your active tier (<strong>${roleInfo.title}</strong>) does not have operational clearance to execute changes in this module.
                        </p>
                        <ul style="margin:0;padding-left:18px;font-size:0.84rem;color:#991b1b;">${cannotListHtml}</ul>
                    </div>
                    <div style="display:flex;gap:10px;align-items:center;">
                        <a href="/user/admin/dashboard" class="btn btn-sm btn-danger" style="text-decoration:none;font-weight:600;">
                            <i class="fas fa-arrow-left me-1"></i> Return to Dashboard
                        </a>
                        <button type="button" class="btn btn-sm btn-outline-dark" onclick="window.openAdminRolesMatrixModal && window.openAdminRolesMatrixModal()">
                            <i class="fas fa-shield-alt me-1"></i> View Role Matrix
                        </button>
                    </div>
                </div>
            `;
        } else if (restrictedBanner) {
            restrictedBanner.remove();
        }

        // 3. Enforce button-level restrictions based on role
        document.querySelectorAll('[data-rbac-locked="1"]').forEach(el => {
            el.disabled = false;
            el.style.opacity = '';
            el.style.pointerEvents = '';
            el.removeAttribute('data-rbac-locked');
            if (el.getAttribute('data-orig-title') !== null) {
                el.title = el.getAttribute('data-orig-title');
            }
        });

        if (role === 'SUPER_ADMIN') return;

        const lockButton = (btn, reason) => {
            if (!btn || btn.id === 'admRoleMatrixBtn' || btn.id === 'admMegaToggleBtn') return;
            if (btn.closest('#finanzaAdminRolesModal') || btn.closest('#finanzaRolePreviewBanner') || btn.closest('#finanzaRoleRestrictedBanner')) return;
            btn.setAttribute('data-orig-title', btn.title || '');
            btn.setAttribute('data-rbac-locked', '1');
            btn.disabled = true;
            btn.style.opacity = '0.45';
            btn.style.cursor = 'not-allowed';
            btn.title = `Restricted for ${role}: ${reason}`;
        };

        const allButtons = document.querySelectorAll('button, input[type="submit"]');
        allButtons.forEach(btn => {
            const txt = (btn.textContent || btn.value || '').toLowerCase().trim();
            const onclick = (btn.getAttribute('onclick') || '').toLowerCase();
            if (!txt && !onclick) return;
            if (txt.includes('close') || txt.includes('cancel') || txt.includes('refresh') || txt.includes('search') || txt.includes('filter') || txt.includes('view')) {
                return;
            }

            if (!allowedOnPage) {
                lockButton(btn, `Module restricted for ${role}`);
                return;
            }

            if (role === 'SUPPORT') {
                // Support can only view and assist with password reset / lockout
                const isAllowedSupport = txt.includes('password') || txt.includes('unlock') || onclick.includes('resetpassword') || onclick.includes('unlock');
                const isMutating = txt.includes('approve') || txt.includes('reject') || txt.includes('deny') ||
                    txt.includes('delete') || txt.includes('suspend') || txt.includes('freeze') ||
                    txt.includes('fund') || txt.includes('credit') || txt.includes('debit') ||
                    txt.includes('adjust') || txt.includes('create') || txt.includes('originate') ||
                    txt.includes('process') || txt.includes('revoke') || txt.includes('save');
                if (isMutating && !isAllowedSupport) {
                    lockButton(btn, 'SUPPORT tier is read-only (except password/lockout assistance)');
                }
            } else if (role === 'COMPLIANCE') {
                // Compliance cannot credit/debit/adjust balances, create/delete users, or manage admins
                if (txt.includes('fund') || txt.includes('credit') || txt.includes('debit') || txt.includes('adjust balance') ||
                    onclick.includes('fund') || onclick.includes('adjustbalance') ||
                    txt.includes('delete user') || onclick.includes('deleteuser') ||
                    txt.includes('create user') || onclick.includes('createuser')) {
                    lockButton(btn, 'COMPLIANCE tier cannot modify balances or create/delete accounts');
                }
            } else if (role === 'TREASURY') {
                // Treasury cannot approve/reject KYC or create/suspend/delete users
                if (onclick.includes('kyc') || txt.includes('approve kyc') || txt.includes('reject kyc') ||
                    txt.includes('delete user') || onclick.includes('deleteuser') ||
                    txt.includes('suspend') || onclick.includes('suspend')) {
                    lockButton(btn, 'TREASURY tier cannot approve KYC or suspend/delete users');
                }
            } else if (role === 'ADMIN') {
                // Operations Admin cannot permanently delete users or manage other admins
                if (txt.includes('delete user') || onclick.includes('deleteuser') ||
                    onclick.includes('revokeadmin') || onclick.includes('changerole')) {
                    lockButton(btn, 'ADMIN tier cannot permanently delete users or modify Admin roles');
                }
            }
        });
    }
};

window.checkAdminAccess = async function () {
    return window.FinanzaAdminRBAC.canAccessPage(window.location.pathname);
};

window.checkAdminAccessWithRole = async function (requiredRole) {
    if (!requiredRole) return true;
    const active = window.FinanzaAdminRBAC.getRole();
    if (active === 'SUPER_ADMIN') return true;
    return active === requiredRole.toUpperCase();
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
                window.FinanzaAdminRBAC.enforcePageAndActions();
            }
        } catch (err) {
            console.warn('Admin session check warning:', err);
        }
    }

    verifyAdminSession();

    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(function () {
            window.FinanzaAdminRBAC.enforcePageAndActions();
        }, 300);
    });

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
